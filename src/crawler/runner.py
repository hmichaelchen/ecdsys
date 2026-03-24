import sys
import json
import asyncio
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, sys.path[0])

from src.crawler.crawler_manager import CrawlerManager
from src.models import CrawlerConfig


def main():
    """爬虫运行器，用于从subprocess调用"""
    if len(sys.argv) != 2:
        logger.error("参数错误: 需要一个JSON配置参数")
        sys.exit(1)
    
    try:
        # 解析JSON配置
        crawler_data = json.loads(sys.argv[1])
        
        crawler_name = crawler_data.get('crawler_name')
        instance_id = crawler_data.get('instance_id')
        keywords = crawler_data.get('keywords', [])
        description = crawler_data.get('description', '')
        
        if not crawler_name or not instance_id:
            logger.error("缺少必要参数: crawler_name 或 instance_id")
            sys.exit(1)
        
        logger.info(f"启动爬虫: {crawler_name} [{instance_id}]")
        logger.info(f"关键字: {keywords}")
        
        # 创建爬虫管理器
        crawler_manager = CrawlerManager()
        
        # 创建配置
        config = CrawlerConfig(url="", keywords=keywords)
        
        # 运行爬虫
        result = asyncio.run(crawler_manager.run_crawler(crawler_name, config, instance_id))
        
        logger.info(f"爬虫执行完成: {result.success}")
        if result.success:
            logger.info(f"成功爬取 {len(result.items)} 条数据")
            sys.exit(0)
        else:
            logger.error(f"爬虫执行失败: {result.errors}")
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"爬虫执行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
