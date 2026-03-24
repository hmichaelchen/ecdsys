import asyncio
import json
from typing import List, Optional
from loguru import logger

from src.crawler.base_crawler import BaseCrawler
from src.models import CrawlerResult, CrawledItem


class MercariCrawler(BaseCrawler):
    """Mercari Japan网站爬虫实现"""
    chinese_name = "日本煤炉"
    
    async def crawl(self) -> CrawlerResult:
        """爬取Mercari Japan网站"""
        items = []
        
        # 如果没有关键字，返回空结果
        if not self.config.keywords:
            logger.warning("未提供关键字，无法进行搜索")
            return CrawlerResult(
                success=True,
                items=[],
                total_items=0
            )
        
        # 使用Playwright拦截API请求
        from playwright.async_api import async_playwright
        
        try:
            async with async_playwright() as p:
                # 更新进度：准备阶段
                self._current_item = f"正在启动浏览器，准备搜索关键字: {', '.join(self.config.keywords)}"
                self.monitor.update_progress(self.get_progress())
                
                # 启动浏览器
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                
                # 更新进度：浏览器已启动
                self._current_item = "浏览器启动成功，开始搜索商品..."
                self.monitor.update_progress(self.get_progress())
                
                # 存储API响应数据
                api_response = None
                # 创建事件用于通知API响应已获取
                api_event = asyncio.Event()
                
                # 设置响应拦截
                async def intercept_response(response):
                    nonlocal api_response
                    if response.url.startswith("https://api.mercari.jp/v2/entities:search"):
                        logger.info(f"收到API响应: {response.url}")
                        # 读取响应内容
                        response_text = await response.text()
                        api_response = json.loads(response_text)
                        # 设置事件，通知等待的协程
                        api_event.set()
                
                # 添加响应拦截器
                context.on("response", intercept_response)
                
                # 构建搜索URL
                keywords_str = '+'.join(self.config.keywords)
                search_url = f"https://jp.mercari.com/search?keyword={keywords_str}"
                logger.info(f"访问搜索页面: {search_url}")
                
                # 更新进度：访问搜索页面
                self._current_item = f"访问搜索页面: {search_url}"
                self.monitor.update_progress(self.get_progress())
                
                # 打开页面
                page = await context.new_page()
                await page.goto(search_url, timeout=60000)
                
                # 更新进度：等待API响应
                self._current_item = "等待API响应数据..."
                self.monitor.update_progress(self.get_progress())
                
                # 等待API响应，最多等待30秒
                try:
                    # 等待事件被设置，最多等待30秒
                    await asyncio.wait_for(api_event.wait(), timeout=30)
                    logger.info("成功获取API响应")
                    self._current_item = "API响应获取成功，开始提取商品数据..."
                    self.monitor.update_progress(self.get_progress())
                except asyncio.TimeoutError:
                    logger.error("等待API响应超时")
                    self._current_item = "等待API响应超时"
                    self.monitor.update_progress(self.get_progress())
                
                # 处理API响应数据
                if api_response:
                    items = await self.extract_items_from_api(api_response)
                    logger.info(f"从API提取到 {len(items)} 条商品数据")
                    
                    self._current_item = f"成功提取到 {len(items)} 条商品数据，开始获取详细信息..."
                    self.monitor.update_progress(self.get_progress())
                    
                    # 获取每个商品的详细信息
                    if items:
                        items = await self.get_item_details(items, page)
                        logger.info(f"获取到 {len(items)} 条商品详细信息")
                else:
                    logger.error("未获取到API响应数据")
                    self._current_item = "未获取到API响应数据"
                    self.monitor.update_progress(self.get_progress())
                
                # 更新进度：爬取完成
                self._current_item = f"爬取完成，共获取 {len(items)} 条商品数据"
                self.monitor.update_progress(self.get_progress())
                
                # 关闭浏览器
                await browser.close()
                
        except Exception as e:
            logger.error(f"爬虫执行异常: {e}")
            self._current_item = f"爬虫执行异常: {str(e)}"
            self.monitor.update_progress(self.get_progress())
            return CrawlerResult(
                success=False,
                errors=[str(e)]
            )
        
        return CrawlerResult(
            success=True,
            items=items,
            total_items=len(items)
        )
    
    async def extract_items_from_api(self, api_response: dict) -> List[CrawledItem]:
        """从API响应中提取商品数据"""
        items = []
        
        # 检查API响应结构
        if 'items' in api_response:
            for item_data in api_response['items']:
                # 提取商品信息
                item_id = str(item_data.get('id', ''))
                title = item_data.get('name', '').strip()
                url = f"https://jp.mercari.com/item/{item_id}"
                
                # 直接构造标准数据模型
                item = CrawledItem(
                    id=f'mercari-{item_id}',
                    title=title,
                    url=url,
                    source='jp.mercari.com'
                )
                items.append(item)
        
        return items
    
    async def get_item_details(self, items: List[CrawledItem], page) -> List[CrawledItem]:
        """获取商品详细信息"""
        updated_items = []
        
        # 设置总任务数
        self.set_total(len(items))
        
        for index, item in enumerate(items):
            # 获取商品ID
            item_id = item.id.replace('mercari-', '')
            
            # 更新进度：开始处理当前商品
            self._current_item = f"正在处理第 {index + 1}/{len(items)} 个商品: {item.title}"
            self.monitor.update_progress(self.get_progress())
            
            # 构建详情页面URL
            detail_url = f"https://jp.mercari.com/item/{item_id}"
            logger.info(f"访问商品详情页面: {detail_url}")
            
            # 存储详情API响应数据
            detail_api_response = None
            detail_event = asyncio.Event()
            
            # 设置响应拦截
            async def intercept_detail_response(response):
                nonlocal detail_api_response
                if response.url.startswith("https://api.mercari.jp/items/get?id="):
                    logger.info(f"收到商品详情API响应: {response.url}")
                    # 读取响应内容
                    response_text = await response.text()
                    detail_api_response = json.loads(response_text)

                    # 设置事件，通知等待的协程
                    detail_event.set()
            
            # 添加响应拦截器
            page.context.on("response", intercept_detail_response)
            
            # 更新进度：访问详情页面
            self._current_item = f"访问商品详情页面: {item.title}"
            self.monitor.update_progress(self.get_progress())
            
            # 访问详情页面
            try:
                await page.goto(detail_url, timeout=20000)
            except Exception as e:
                logger.error(f"访问详情页面失败: {detail_url}, 错误: {e}")
                self.increment_failed()
                self._current_item = f"访问详情页面失败: {item.title} ({str(e)})"
                self.monitor.update_progress(self.get_progress())
                continue
            
            try:
                # 更新进度：等待详情API响应
                self._current_item = f"等待商品详情API响应: {item.title}"
                self.monitor.update_progress(self.get_progress())
                
                # 等待详情API响应，最多等待8秒
                await asyncio.wait_for(detail_event.wait(), timeout=8)
                logger.info(f"成功获取商品详情: {item_id}")
                
                # 更新进度：处理商品详情数据
                self._current_item = f"处理商品详情数据: {item.title}"
                self.monitor.update_progress(self.get_progress())
                
                # 更新商品信息
                if detail_api_response:
                    updated_item = await self.update_item_with_details(item, detail_api_response)
                    updated_items.append(updated_item)
                    self.increment_success()
                    
                    # 更新进度：保存商品到数据库
                    self._current_item = f"保存商品到数据库: {item.title}"
                    self.monitor.update_progress(self.get_progress())
                    
                    # 立即保存到数据库
                    self.save_item(updated_item)
                    
                    # 更新进度：商品处理完成
                    self._current_item = f"商品处理完成: {item.title} (成功)"
                    self.monitor.update_progress(self.get_progress())
                else:
                    # 不添加没有详情数据的商品
                    self.increment_failed()
                    self._current_item = f"商品处理失败: {item.title} (无详情数据)"
                    self.monitor.update_progress(self.get_progress())
                    
            except asyncio.TimeoutError:
                logger.error(f"等待商品详情API响应超时: {item_id}")
                # 不添加超时的商品
                self.increment_failed()
                self._current_item = f"商品处理失败: {item.title} (API响应超时)"
                self.monitor.update_progress(self.get_progress())
            except Exception as e:
                logger.error(f"处理商品详情时出错: {item_id}, 错误: {e}")
                self.increment_failed()
                self._current_item = f"商品处理失败: {item.title} ({str(e)})"
                self.monitor.update_progress(self.get_progress())
            finally:
                # 移除响应拦截器，避免多个拦截器导致的混淆
                page.context.remove_listener("response", intercept_detail_response)
                # 更新进度计数
                self.increment_progress()
        
        return updated_items
    
    async def update_item_with_details(self, item: CrawledItem, detail_data: dict) -> CrawledItem:
        """使用详情数据更新商品信息"""
        # 提取详情信息
        item_data = detail_data.get('data', {})
        
        # 提取必要的字段到detail_data
        extracted_data = {
            'id': item_data.get('id'),
            'name': item_data.get('name'),
            'price': item_data.get('price'),
            'description': item_data.get('description'),
            'photos': item_data.get('photos'),
            'thumbnails': item_data.get('thumbnails'),
            'item_category': item_data.get('item_category'),
            'item_condition': item_data.get('item_condition'),
            'item_brand': item_data.get('item_brand'),
            'shipping_payer': item_data.get('shipping_payer'),
            'shipping_method': item_data.get('shipping_method'),
            'shipping_duration': item_data.get('shipping_duration'),
            'num_likes': item_data.get('num_likes'),
            'num_comments': item_data.get('num_comments'),
            'comments': item_data.get('comments'),
            'seller': {
                'name': item_data.get('seller', {}).get('name'),
                'num_ratings': item_data.get('seller', {}).get('num_ratings'),
                'score': item_data.get('seller', {}).get('score'),
                'star_rating_score': item_data.get('seller', {}).get('star_rating_score')
            },
            'shipping_from_area': item_data.get('shipping_from_area'),
            'status': item_data.get('status'),
            'created': item_data.get('created'),
            'updated': item_data.get('updated')
        }
        
        item.detail_data = extracted_data
        
        # 更新标题
        if item_data.get('name'):
            item.title = item_data['name']
        
        return item