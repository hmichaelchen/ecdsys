from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any


class CrawledItem(BaseModel):
    """统一的数据格式模型"""
    id: str
    title: str
    url: str
    source: str
    publish_time: Optional[datetime] = None
    crawled_at: datetime = datetime.now()
    # 完整的详情API响应数据
    detail_data: Optional[Dict[str, Any]] = None


class CrawlerConfig(BaseModel):
    """爬虫配置模型"""
    url: str
    timeout: int = 30
    headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    max_retries: int = 3
    verify_ssl: bool = False
    keywords: List[str] = []


class CrawlerResult(BaseModel):
    """爬虫结果模型"""
    success: bool
    items: List[CrawledItem] = []
    errors: List[str] = []
    total_items: int = 0


class CrawlerInstance(BaseModel):
    """爬虫实例模型"""
    id: str
    crawler_name: str
    instance_name: str
    keywords: List[str]
    description: Optional[str] = None
    status: str = "created"
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()