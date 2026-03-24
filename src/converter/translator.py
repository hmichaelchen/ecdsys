from typing import List, Dict, Any, Optional
from loguru import logger
import re
import html


class DataTranslator:
    """数据翻译器，用于将爬取的数据翻译为中文信息"""
    
    @staticmethod
    def translate_text(text: Optional[str], target_language: str = 'zh') -> str:
        """翻译文本（模拟翻译，实际项目中应替换为真实翻译API）"""
        if not text:
            return ''
        
        # 移除HTML标签
        text = html.unescape(text)
        text = re.sub(r'<[^>]+>', '', text)
        
        # 模拟翻译（实际项目中应替换为真实翻译API调用）
        # 这里只是简单的示例，实际应使用Google Translate API、百度翻译API等
        translated_text = f"[翻译] {text}"
        
        return translated_text
    
    @staticmethod
    def translate_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """翻译单个商品数据"""
        translated_item = item.copy()
        
        # 翻译标题
        if 'title' in translated_item and translated_item['title']:
            translated_item['title'] = DataTranslator.translate_text(translated_item['title'])
        
        # 翻译detail_data中的字段
        if 'detail_data' in translated_item and isinstance(translated_item['detail_data'], dict):
            detail_data = translated_item['detail_data']
            
            # 翻译名称
            if 'name' in detail_data and detail_data['name']:
                detail_data['name'] = DataTranslator.translate_text(detail_data['name'])
            
            # 翻译描述
            if 'description' in detail_data and detail_data['description']:
                detail_data['description'] = DataTranslator.translate_text(detail_data['description'])
            
            # 翻译商品状态
            if 'item_condition' in detail_data and isinstance(detail_data['item_condition'], dict):
                if 'name' in detail_data['item_condition']:
                    detail_data['item_condition']['name'] = DataTranslator.translate_text(detail_data['item_condition']['name'])
                if 'subname' in detail_data['item_condition']:
                    detail_data['item_condition']['subname'] = DataTranslator.translate_text(detail_data['item_condition']['subname'])
            
            # 翻译分类
            if 'item_category' in detail_data and isinstance(detail_data['item_category'], dict):
                if 'name' in detail_data['item_category']:
                    detail_data['item_category']['name'] = DataTranslator.translate_text(detail_data['item_category']['name'])
                if 'parent_category_name' in detail_data['item_category']:
                    detail_data['item_category']['parent_category_name'] = DataTranslator.translate_text(detail_data['item_category']['parent_category_name'])
                if 'root_category_name' in detail_data['item_category']:
                    detail_data['item_category']['root_category_name'] = DataTranslator.translate_text(detail_data['item_category']['root_category_name'])
            
            # 翻译品牌
            if 'item_brand' in detail_data and isinstance(detail_data['item_brand'], dict):
                if 'name' in detail_data['item_brand']:
                    detail_data['item_brand']['name'] = DataTranslator.translate_text(detail_data['item_brand']['name'])
            
            # 翻译配送方式
            if 'shipping_method' in detail_data and isinstance(detail_data['shipping_method'], dict):
                if 'name' in detail_data['shipping_method']:
                    detail_data['shipping_method']['name'] = DataTranslator.translate_text(detail_data['shipping_method']['name'])
            
            # 翻译配送方
            if 'shipping_payer' in detail_data and isinstance(detail_data['shipping_payer'], dict):
                if 'name' in detail_data['shipping_payer']:
                    detail_data['shipping_payer']['name'] = DataTranslator.translate_text(detail_data['shipping_payer']['name'])
            
            # 翻译配送时间
            if 'shipping_duration' in detail_data and isinstance(detail_data['shipping_duration'], dict):
                if 'name' in detail_data['shipping_duration']:
                    detail_data['shipping_duration']['name'] = DataTranslator.translate_text(detail_data['shipping_duration']['name'])
            
            # 翻译卖家名称
            if 'seller' in detail_data and isinstance(detail_data['seller'], dict):
                if 'name' in detail_data['seller']:
                    detail_data['seller']['name'] = DataTranslator.translate_text(detail_data['seller']['name'])
            
            # 翻译评论
            if 'comments' in detail_data and isinstance(detail_data['comments'], list):
                for comment in detail_data['comments']:
                    if isinstance(comment, dict) and 'message' in comment:
                        comment['message'] = DataTranslator.translate_text(comment['message'])
            
            translated_item['detail_data'] = detail_data
        
        return translated_item
    
    @staticmethod
    def batch_translate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量翻译商品数据"""
        translated_items = []
        total = len(items)
        
        for i, item in enumerate(items):
            try:
                translated_item = DataTranslator.translate_item(item)
                translated_items.append(translated_item)
                if (i + 1) % 10 == 0:
                    logger.info(f"已翻译 {i + 1}/{total} 条数据")
            except Exception as e:
                logger.error(f"翻译商品 {item.get('id', 'unknown')} 时出错: {e}")
                translated_items.append(item)  # 翻译失败时保留原数据
        
        logger.info(f"翻译完成，共处理 {total} 条数据")
        return translated_items
