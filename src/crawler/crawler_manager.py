import asyncio
import importlib
import os
import sys
from typing import List, Dict, Type, Optional
from loguru import logger

from src.crawler.base_crawler import BaseCrawler
from src.crawler.monitor import CrawlerMonitor
from src.models import CrawlerConfig, CrawlerResult


class CrawlerManager:
    """爬虫管理器，用于管理多个爬虫的并发运行"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.crawlers: Dict[str, Type[BaseCrawler]] = {}
        self.scrapers_dir = os.path.join(os.path.dirname(__file__), 'scrapers')
        self.running_crawlers: Dict[str, Dict[str, BaseCrawler]] = {}  # {crawler_name: {instance_id: crawler_instance}}
        self.crawler_configs: Dict[str, CrawlerConfig] = {}  # 存储每个爬虫的默认配置
        self.crawler_progress: Dict[str, Dict] = {}  # 存储爬虫进度信息 {crawler_name_instance_id: progress_data}
        # 自动加载scrapers目录下的爬虫
        self.load_scrapers()
    
    def register_crawler(self, name: str, crawler_class: Type[BaseCrawler]):
        """注册爬虫类"""
        self.crawlers[name] = crawler_class
        # 为每个爬虫创建默认配置
        self.crawler_configs[name] = CrawlerConfig(url="", keywords=["HERMES"])
        logger.info(f"注册爬虫: {name}")
    
    def set_crawler_config(self, name: str, config: CrawlerConfig):
        """设置爬虫配置"""
        if name in self.crawlers:
            self.crawler_configs[name] = config
            logger.info(f"设置爬虫 {name} 的配置")
            return True
        logger.warning(f"爬虫 {name} 未注册")
        return False
    
    def get_crawler_config(self, name: str) -> Optional[CrawlerConfig]:
        """获取爬虫配置"""
        return self.crawler_configs.get(name)
    
    def set_all_crawler_configs(self, config: CrawlerConfig):
        """设置所有爬虫的配置"""
        for name in self.crawlers:
            self.crawler_configs[name] = config
        logger.info(f"设置所有爬虫的配置")
    
    async def run_crawler(self, name: str, config: CrawlerConfig = None, instance_id: str = None, monitor: CrawlerMonitor = None) -> CrawlerResult:
        """运行单个爬虫实例"""
        if name not in self.crawlers:
            logger.error(f"爬虫 {name} 未注册")
            return CrawlerResult(
                success=False,
                errors=[f"爬虫 {name} 未注册"]
            )
        
        # 如果没有提供配置，使用存储的配置
        if config is None:
            config = self.crawler_configs.get(name, CrawlerConfig(url="", keywords=["HERMES"]))
        
        # 如果没有提供实例ID，生成一个基于关键字的ID
        if instance_id is None:
            keywords_str = "_".join(config.keywords)
            instance_id = f"{name}_{keywords_str}"
        
        crawler = self.crawlers[name](config, monitor)
        crawler.instance_id = instance_id
        
        # 存储正在运行的爬虫实例
        if name not in self.running_crawlers:
            self.running_crawlers[name] = {}
        self.running_crawlers[name][instance_id] = crawler
        
        try:
            return await crawler.run()
        finally:
            # 无论成功失败，都从运行列表中移除
            if name in self.running_crawlers and instance_id in self.running_crawlers[name]:
                del self.running_crawlers[name][instance_id]
                # 如果该爬虫没有其他实例运行，清理空字典
                if not self.running_crawlers[name]:
                    del self.running_crawlers[name]
    
    async def run_all(self, crawler_configs: List[Dict[str, CrawlerConfig]] = None) -> Dict[str, CrawlerResult]:
        """并发运行多个爬虫"""
        tasks = []
        results = {}
        
        # 如果没有提供配置，使用存储的配置
        if crawler_configs is None:
            tasks = [(name, self.run_crawler(name)) for name in self.crawlers]
        else:
            # 创建任务列表
            for config_data in crawler_configs:
                for crawler_name, config in config_data.items():
                    tasks.append((crawler_name, self.run_crawler(crawler_name, config)))
        
        # 限制并发数量
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_with_limit(crawler_name, task):
            async with semaphore:
                result = await task
                results[crawler_name] = result
        
        # 执行所有任务
        await asyncio.gather(*[run_with_limit(name, task) for name, task in tasks])
        
        return results
    
    def get_registered_crawlers(self) -> List[str]:
        """获取已注册的爬虫列表"""
        return list(self.crawlers.keys())
    
    def cancel_all(self):
        """取消所有正在运行的爬虫"""
        cancelled_count = 0
        for name, crawler in list(self.running_crawlers.items()):
            crawler.cancel()
            cancelled_count += 1
            logger.info(f"已取消爬虫: {name}")
        
        # 清空运行列表
        self.running_crawlers.clear()
        return cancelled_count
    
    def cancel_crawler(self, name: str, instance_id: str = None) -> bool:
        """取消单个爬虫实例"""
        if name in self.running_crawlers:
            if instance_id:
                # 取消特定实例
                if instance_id in self.running_crawlers[name]:
                    crawler = self.running_crawlers[name][instance_id]
                    crawler.cancel()
                    del self.running_crawlers[name][instance_id]
                    # 如果该爬虫没有其他实例运行，清理空字典
                    if not self.running_crawlers[name]:
                        del self.running_crawlers[name]
                    logger.info(f"已取消爬虫实例: {name} [{instance_id}]")
                    return True
                logger.warning(f"爬虫实例 {name} [{instance_id}] 不在运行中")
                return False
            else:
                # 取消该爬虫的所有实例
                cancelled_count = 0
                for instance_id, crawler in list(self.running_crawlers[name].items()):
                    crawler.cancel()
                    cancelled_count += 1
                    logger.info(f"已取消爬虫实例: {name} [{instance_id}]")
                del self.running_crawlers[name]
                logger.info(f"已取消爬虫 {name} 的所有实例")
                return cancelled_count > 0
        logger.warning(f"爬虫 {name} 不在运行中")
        return False
    
    def get_running_crawlers(self) -> Dict[str, List[str]]:
        """获取正在运行的爬虫实例列表
        
        Returns:
            {crawler_name: [instance_id1, instance_id2, ...]}
        """
        return {name: list(instances.keys()) for name, instances in self.running_crawlers.items()}
    
    def is_crawler_running(self, name: str, instance_id: str = None) -> bool:
        """检查爬虫实例是否正在运行"""
        if name in self.running_crawlers:
            if instance_id:
                return instance_id in self.running_crawlers[name]
            return len(self.running_crawlers[name]) > 0
        return False
    
    def get_crawler_progress(self, name: str = None, instance_id: str = None) -> dict:
        """获取爬虫进度
        
        Args:
            name: 爬虫名称，如果为None则获取所有运行中爬虫的进度
            instance_id: 实例ID，如果为None则获取该爬虫的所有实例进度
            
        Returns:
            爬虫进度字典
        """
        if name:
            if instance_id:
                # 获取特定实例的进度
                key = f"{name}_{instance_id}"
                if key in self.crawler_progress:
                    return {key: self.crawler_progress[key]}
                return {key: None}
            else:
                # 获取该爬虫的所有实例进度
                progress = {}
                for key, progress_data in self.crawler_progress.items():
                    if key.startswith(f"{name}_"):
                        progress[key] = progress_data
                return progress
        else:
            # 获取所有爬虫的所有实例进度
            return self.crawler_progress.copy()
    
    def get_all_instances(self) -> List[Dict]:
        """获取所有爬虫实例的状态"""
        instances = []
        for name, crawler_instances in self.running_crawlers.items():
            for instance_id, crawler in crawler_instances.items():
                instances.append({
                    'crawler_name': name,
                    'instance_id': instance_id,
                    'status': 'running',
                    'progress': crawler.get_progress()
                })
        return instances
    
    def load_scrapers(self):
        """动态加载scrapers目录下的爬虫"""
        if not os.path.exists(self.scrapers_dir):
            logger.warning(f"Scrapers目录不存在: {self.scrapers_dir}")
            return
        
        # 遍历scrapers目录下的所有子目录
        for website_dir in os.listdir(self.scrapers_dir):
            website_path = os.path.join(self.scrapers_dir, website_dir)
            
            # 只处理目录
            if not os.path.isdir(website_path):
                continue
            
            # 获取目录下的所有Python文件
            python_files = [f for f in os.listdir(website_path) if f.endswith('.py') and f != '__init__.py']
            
            for py_file in python_files:
                module_name = f"src.crawler.scrapers.{website_dir}.{py_file[:-3]}"
                
                try:
                    # 动态导入模块
                    module = importlib.import_module(module_name)
                    
                    # 查找模块中的爬虫类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # 检查是否是BaseCrawler的子类且不是BaseCrawler本身
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseCrawler) and 
                            attr != BaseCrawler):
                            
                            # 检查爬虫类是否定义了中文名称
                            if hasattr(attr, 'chinese_name'):
                                crawler_name = attr.chinese_name
                            else:
                                # 默认使用网站名称
                                crawler_name = website_dir.lower()
                            
                            self.register_crawler(crawler_name, attr)
                            logger.info(f"动态加载爬虫: {crawler_name} ({attr.__name__})")
                            
                except Exception as e:
                    logger.error(f"加载爬虫模块失败 {module_name}: {e}")