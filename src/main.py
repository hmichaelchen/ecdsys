import asyncio
import os
import sys
import argparse
import json
from dotenv import load_dotenv
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import CrawlerManager
from src.models import CrawlerConfig
from src.converter import DataConverter, DataTranslator
from src.database import DatabaseManager


async def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='爬虫服务')
    parser.add_argument('-k', '--keywords', type=str, help='搜索关键字，多个关键字用逗号分隔')
    parser.add_argument('--translate', action='store_true', help='启用数据翻译功能')
    args = parser.parse_args()
    
    # 处理关键字
    keywords = []
    if args.keywords:
        keywords = [keyword.strip() for keyword in args.keywords.split(',')]
    
    # 加载环境变量
    load_dotenv()
    
    # 配置日志
    logger.add("logs/crawler.log", rotation="1 day", retention="7 days", level="INFO")
    
    # 创建爬虫管理器（会自动动态加载scrapers目录下的爬虫）
    max_concurrent = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    manager = CrawlerManager(max_concurrent=max_concurrent)
    
    # 创建爬虫配置列表
    crawler_configs = []
    
    # 检查是否有注册的爬虫
    registered_crawlers = manager.get_registered_crawlers()
    if not registered_crawlers:
        logger.warning("没有注册任何爬虫，请先在scrapers目录下创建爬虫实现")
        return
    
    # 为每个爬虫创建配置（网站URL由爬虫类自行定义）
    for crawler_name in registered_crawlers:
        # 爬虫类应该在crawl方法中处理具体的网站URL
        config = CrawlerConfig(url="", keywords=keywords)
        crawler_configs.append({crawler_name: config})
    
    # 执行爬虫
    logger.info(f"开始运行 {len(registered_crawlers)} 个爬虫")
    if keywords:
        logger.info(f"搜索关键字: {', '.join(keywords)}")
    results = await manager.run_all(crawler_configs)
    
    # 处理结果
    all_items = []
    for crawler_name, result in results.items():
        if result.success:
            logger.info(f"爬虫 {crawler_name} 成功，获取 {result.total_items} 条数据")
            all_items.extend(result.items)
        else:
            logger.error(f"爬虫 {crawler_name} 失败: {result.errors}")
    
    # 保存结果
    if all_items:
        # 如果启用了翻译功能，进行数据翻译
        items_to_save = all_items
        if args.translate:
            logger.info("开始翻译数据...")
            # 将CrawledItem对象转换为字典列表进行翻译
            items_dict_list = [item.model_dump(mode='json') for item in all_items]
            translated_items_dict = DataTranslator.batch_translate(items_dict_list)
            # 将翻译后的字典转换回CrawledItem对象
            items_to_save = [DataConverter.from_json(json.dumps([item]))[0] for item in translated_items_dict]
        
        # 保存到SQLite数据库
        logger.info("开始保存数据到数据库...")
        db_manager = DatabaseManager()
        saved_count = db_manager.batch_insert(items_to_save)
        logger.info(f"成功保存 {saved_count} 条数据到数据库")
        
        # 保存为JSON
        json_path = os.path.join("output", "crawled_data.json")
        DataConverter.to_json(items_to_save, json_path)
        
        # 保存为CSV
        csv_path = os.path.join("output", "crawled_data.csv")
        DataConverter.to_csv(items_to_save, csv_path)
        
        logger.info(f"总数据量: {len(items_to_save)} 条")
    else:
        logger.warning("没有获取到任何数据")


if __name__ == "__main__":
    asyncio.run(main())