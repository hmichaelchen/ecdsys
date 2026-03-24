import json
from typing import Dict, Any
from loguru import logger

from src.crawler.monitor import CrawlerMonitor


class WebMonitor(CrawlerMonitor):
    """Web监控器，用于向前端推送进度信息"""
    
    def __init__(self, progress_callback=None, crawler_manager=None, crawler_name=None, instance_id=None):
        """初始化Web监控器
        
        Args:
            progress_callback: 进度回调函数，接收进度信息字典
            crawler_manager: 爬虫管理器实例，用于保存进度信息
            crawler_name: 爬虫名称
            instance_id: 实例ID
        """
        self.progress_callback = progress_callback
        self.crawler_manager = crawler_manager
        self.crawler_name = crawler_name
        self.instance_id = instance_id
        self.last_progress = None
    
    def update_progress(self, progress: Dict[str, Any]):
        """更新爬虫进度"""
        # 避免重复推送相同的进度信息
        if progress == self.last_progress:
            return
        
        self.last_progress = progress
        
        # 如果有爬虫管理器，保存进度信息
        if self.crawler_manager and self.crawler_name and self.instance_id:
            key = f"{self.crawler_name}_{self.instance_id}"
            self.crawler_manager.crawler_progress[key] = progress
        
        # 如果有回调函数，调用回调函数
        if self.progress_callback:
            self.progress_callback(progress)
        else:
            # 默认使用日志输出
            logger.info(f"进度更新: {json.dumps(progress, ensure_ascii=False)}")
    
    def log_message(self, level: str, message: str):
        """记录日志信息"""
        # 在Web环境中，日志消息可以通过回调函数或其他方式传递
        logger.info(f"[{level}] {message}")
    
    def on_start(self):
        """爬虫开始执行时调用"""
        logger.info("爬虫开始执行")
    
    def on_complete(self, success: bool, message: str = None):
        """爬虫完成时调用"""
        if success:
            logger.info(f"爬虫执行成功: {message}")
        else:
            logger.error(f"爬虫执行失败: {message}")
