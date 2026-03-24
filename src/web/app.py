from flask import Flask, send_from_directory
import os
import sys
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入模块
import utils
import routes
from src.crawler.crawler_manager import CrawlerManager

# 配置日志，将所有日志写入一个文件
log_file = os.path.join("logs", "app.log")
logger.add(log_file, format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}", level="INFO", rotation="1 day", retention="7 days")

# 初始化日志收集器
log_collector = utils.LogCollector()
logger.add(lambda msg: log_collector.add_log(msg), format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}")

# 创建Flask应用
app = Flask(__name__, static_folder='../../frontend/dist', static_url_path='')
app.config['SECRET_KEY'] = 'your-secret-key'

# 注册路由
routes.register_routes(app, log_collector)

# 提供React构建的静态文件
@app.route('/')
def serve_index():
    return send_from_directory('../../frontend/dist', 'index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('../../frontend/dist/assets', filename)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5004)
