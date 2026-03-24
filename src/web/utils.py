import time
import re
import datetime


class LogCollector:
    def __init__(self):
        self.logs = []
        self.max_logs = 500  # 最多保存500条日志
    
    def add_log(self, message):
        """添加日志消息"""
        # 解析日志消息格式: "[2026-03-22 18:00:40.128 | INFO     | src.database.db_manager:_init_database:47] 数据库初始化完成: data/crawler.db"
        try:
            # 提取时间、级别和消息
            match = re.match(r'(.*?) \| (\w+) +\| .*? \| (.*)', message)
            if match:
                time_str = match.group(1)
                level = match.group(2)
                msg = match.group(3)
                
                # 格式化时间
                dt = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f')
                time_formatted = dt.strftime('%H:%M:%S')
                
                self.logs.append({
                    'time': time_formatted,
                    'level': level,
                    'message': msg
                })
                # 限制日志数量
                if len(self.logs) > self.max_logs:
                    self.logs = self.logs[-self.max_logs:]
        except Exception as e:
            # 如果解析失败，添加原始消息
            self.logs.append({
                'time': time.strftime('%H:%M:%S'),
                'level': 'ERROR',
                'message': f'日志解析错误: {message}'
            })
