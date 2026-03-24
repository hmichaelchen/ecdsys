import json
import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from src.models import CrawledItem


class DataConverter:
    """数据格式转换器，支持多种格式的序列化和反序列化"""
    
    @staticmethod
    def to_json(items: List[CrawledItem], output_path: Optional[str] = None) -> str:
        """将数据转换为JSON格式"""
        cleaned_data = []
        
        for item in items:
            item_dict = item.model_dump(mode='json')
            cleaned_data.append(item_dict)
        
        json_str = json.dumps(cleaned_data, ensure_ascii=False, indent=2, default=str)
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"数据已保存到: {output_path}")
        
        return json_str
    
    @staticmethod
    def to_csv(items: List[CrawledItem], output_path: str) -> None:
        """将数据转换为CSV格式"""
        if not items:
            logger.warning("没有数据可转换为CSV")
            return
        
        # 获取所有字段名
        fieldnames = ['id', 'title', 'url', 'source', 'publish_time', 'crawled_at', 'detail_data']
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in items:
                row = item.model_dump(mode='json')
                # 处理字典类型
                row['detail_data'] = json.dumps(row['detail_data'], ensure_ascii=False) if row['detail_data'] else ''
                writer.writerow(row)
        
        logger.info(f"数据已保存到: {output_path}")
    
    @staticmethod
    def from_json(json_str: str) -> List[CrawledItem]:
        """从JSON字符串加载数据"""
        data = json.loads(json_str)
        return [CrawledItem(**item) for item in data]
    
    @staticmethod
    def from_json_file(file_path: str) -> List[CrawledItem]:
        """从JSON文件加载数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()
        return DataConverter.from_json(json_str)
    
    @staticmethod
    def normalize_data(item: Dict[str, Any]) -> CrawledItem:
        """标准化数据格式"""
        # 确保所有必需字段都存在
        normalized = {
            'id': item.get('id', str(datetime.now().timestamp())),
            'title': item.get('title', '').strip(),
            'url': item.get('url', ''),
            'source': item.get('source', ''),
            'publish_time': item.get('publish_time'),
            'crawled_at': item.get('crawled_at', datetime.now()),
            'detail_data': item.get('detail_data')
        }
        
        # 类型转换
        if isinstance(normalized['publish_time'], str):
            try:
                normalized['publish_time'] = datetime.fromisoformat(normalized['publish_time'].replace('Z', '+00:00'))
            except:
                normalized['publish_time'] = None
        
        if isinstance(normalized['crawled_at'], str):
            try:
                normalized['crawled_at'] = datetime.fromisoformat(normalized['crawled_at'].replace('Z', '+00:00'))
            except:
                normalized['crawled_at'] = datetime.now()
        
        return CrawledItem(**normalized)
    
    @staticmethod
    def batch_normalize(data_list: List[Dict[str, Any]]) -> List[CrawledItem]:
        """批量标准化数据"""
        return [DataConverter.normalize_data(item) for item in data_list]