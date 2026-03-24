from abc import ABC, abstractmethod
from typing import Dict, Any


class CrawlerMonitor(ABC):
    """爬虫监控器基类，用于监控爬虫执行过程"""
    
    @abstractmethod
    def update_progress(self, progress: Dict[str, Any]):
        """更新爬虫进度
        
        Args:
            progress: 进度信息字典，包含：
                - total: 总任务数
                - completed: 已完成任务数
                - progress_percent: 进度百分比
                - success_count: 成功数
                - failed_count: 失败数
                - current_item: 当前正在处理的项目
        """
        pass
    
    @abstractmethod
    def log_message(self, level: str, message: str):
        """记录日志信息
        
        Args:
            level: 日志级别 (INFO, WARNING, ERROR)
            message: 日志消息
        """
        pass
    
    @abstractmethod
    def on_start(self):
        """爬虫开始执行时调用"""
        pass
    
    @abstractmethod
    def on_complete(self, success: bool, message: str = None):
        """爬虫完成时调用
        
        Args:
            success: 是否成功
            message: 完成消息
        """
        pass


class DefaultMonitor(CrawlerMonitor):
    """默认监控器，使用print输出进度和日志"""
    
    def update_progress(self, progress: Dict[str, Any]):
        """更新爬虫进度"""
        percent = progress.get('progress_percent', 0)
        total = progress.get('total', 0)
        completed = progress.get('completed', 0)
        success = progress.get('success_count', 0)
        failed = progress.get('failed_count', 0)
        current = progress.get('current_item', '')
        
        print(f"进度: {percent:.2f}% ({completed}/{total}) | 成功: {success} | 失败: {failed} | 当前: {current}")
    
    def log_message(self, level: str, message: str):
        """记录日志信息"""
        print(f"[{level}] {message}")
    
    def on_start(self):
        """爬虫开始执行时调用"""
        print("爬虫开始执行...")
    
    def on_complete(self, success: bool, message: str = None):
        """爬虫完成时调用"""
        if success:
            print(f"爬虫执行成功: {message}")
        else:
            print(f"爬虫执行失败: {message}")
