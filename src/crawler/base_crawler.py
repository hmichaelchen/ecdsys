import asyncio
import requests
from abc import ABC, abstractmethod
from typing import List, Optional
from loguru import logger

from src.models import CrawlerConfig, CrawlerResult, CrawledItem
from src.database.db_manager import DatabaseManager
from src.crawler.monitor import CrawlerMonitor, DefaultMonitor


class BaseCrawler(ABC):
    """爬虫基类，所有具体网站爬虫都应继承此类"""
    
    def __init__(self, config: CrawlerConfig, monitor: CrawlerMonitor = None):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)
        self._cancel_event = asyncio.Event()  # 取消事件
        self.instance_id = None  # 实例ID
        # 进度跟踪
        self._total = 0  # 总任务数
        self._completed = 0  # 已完成任务数
        self._current_item = None  # 当前正在处理的项目
        self._success_count = 0  # 成功数
        self._failed_count = 0  # 失败数
        # 数据库管理器
        self.db_manager = DatabaseManager()
        # 监控器
        self.monitor = monitor if monitor else DefaultMonitor()
    
    @abstractmethod
    async def crawl(self) -> CrawlerResult:
        """执行爬虫任务，由子类实现"""
        pass
    
    def get_source_name(self) -> str:
        """获取网站名称"""
        from urllib.parse import urlparse
        parsed = urlparse(self.config.url)
        return parsed.netloc
    
    def cancel(self):
        """取消爬虫任务"""
        self._cancel_event.set()
        logger.info(f"爬虫 {self.__class__.__name__} 已取消")
    
    def is_cancelled(self) -> bool:
        """检查爬虫是否已取消"""
        return self._cancel_event.is_set()
    
    def set_total(self, total: int):
        """设置总任务数"""
        self._total = total
    
    def update_progress(self, completed: int = None, current_item: str = None):
        """更新进度"""
        if completed is not None:
            self._completed = completed
        if current_item is not None:
            self._current_item = current_item
    
    def increment_progress(self, current_item: str = None):
        """增加进度计数"""
        self._completed += 1
        if current_item is not None:
            self._current_item = current_item
        # 通过监控器汇报进度
        self.monitor.update_progress(self.get_progress())
    
    def increment_success(self):
        """增加成功计数"""
        self._success_count += 1
        # 通过监控器汇报进度
        self.monitor.update_progress(self.get_progress())
    
    def increment_failed(self):
        """增加失败计数"""
        self._failed_count += 1
        # 通过监控器汇报进度
        self.monitor.update_progress(self.get_progress())
    
    def get_progress(self) -> dict:
        """获取当前进度"""
        progress_percent = (self._completed / self._total * 100) if self._total > 0 else 0
        return {
            'total': self._total,
            'completed': self._completed,
            'progress_percent': round(progress_percent, 2),
            'current_item': self._current_item,
            'success_count': self._success_count,
            'failed_count': self._failed_count
        }
    
    def save_item(self, item: CrawledItem) -> bool:
        """保存单个商品到数据库"""
        saved = self.db_manager.insert_item(item)
        if saved:
            logger.info(f"商品 {item.id} 已保存到数据库")
        else:
            logger.warning(f"商品 {item.id} 保存失败")
        return saved
    
    def save_items(self, items: List[CrawledItem]) -> int:
        """批量保存商品到数据库"""
        saved_count = self.db_manager.batch_insert(items)
        logger.info(f"批量保存成功，共 {saved_count} 条数据")
        return saved_count
    
    async def run(self) -> CrawlerResult:
        """运行爬虫"""
        logger.info(f"开始运行爬虫: {self.__class__.__name__}")
        try:
            # 通知监控器爬虫开始
            self.monitor.on_start()
            
            result = await self.crawl()
            
            if not self.is_cancelled():
                logger.info(f"爬虫 {self.__class__.__name__} 完成，成功获取 {result.total_items} 条数据")
                # 通知监控器爬虫完成
                self.monitor.on_complete(True, f"成功获取 {result.total_items} 条数据")
            else:
                self.monitor.on_complete(False, "爬虫被取消")
                
            return result
        except Exception as e:
            logger.error(f"爬虫 {self.__class__.__name__} 异常: {e}")
            # 通知监控器爬虫失败
            self.monitor.on_complete(False, str(e))
            return CrawlerResult(
                success=False,
                errors=[str(e)]
            )