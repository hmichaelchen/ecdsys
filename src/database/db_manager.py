import psycopg2
import psycopg2.extras
import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from src.models import CrawledItem


class DatabaseManager:
    """数据库管理器，用于存储和查询爬取的数据"""
    
    _instance = None
    
    def __new__(cls, db_url: str = None):
        """单例模式，确保整个应用使用同一个数据库连接"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            # 使用PostgreSQL数据库
            if db_url:
                cls._instance.db_url = db_url
            else:
                cls._instance.db_url = os.environ.get(
                    "DATABASE_URL",
                    "postgresql://neondb_owner:npg_Z5XNw8CHyFIa@ep-muddy-rice-a4vlmjzs-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
                )
            logger.info(f"使用PostgreSQL数据库: {cls._instance.db_url}")
            cls._instance._init_database()
        return cls._instance
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        
        # 创建商品表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawled_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                publish_time TEXT,
                crawled_at TEXT NOT NULL,
                detail_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建爬虫实例表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawler_instances (
                id TEXT PRIMARY KEY,
                crawler_name TEXT NOT NULL,
                instance_name TEXT NOT NULL,
                keywords TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_crawled_at ON crawled_items(crawled_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON crawled_items(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON crawled_items(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_crawler_name ON crawler_instances(crawler_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_instance_name ON crawler_instances(instance_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON crawler_instances(status)')
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成")
    
    def insert_item(self, item: CrawledItem) -> bool:
        """插入单个商品数据"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO crawled_items (
                    id, title, url, source, publish_time, crawled_at, detail_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    source = EXCLUDED.source,
                    publish_time = EXCLUDED.publish_time,
                    crawled_at = EXCLUDED.crawled_at,
                    detail_data = EXCLUDED.detail_data
            ''', (
                item.id,
                item.title,
                item.url,
                item.source,
                item.publish_time.isoformat() if item.publish_time else None,
                item.crawled_at.isoformat(),
                json.dumps(item.detail_data, ensure_ascii=False) if item.detail_data else '{}'
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"插入商品数据失败: {e}")
            return False
    
    def batch_insert(self, items: List[CrawledItem]) -> int:
        """批量插入商品数据"""
        if not items:
            return 0
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            data = []
            for item in items:
                data.append((
                    item.id,
                    item.title,
                    item.url,
                    item.source,
                    item.publish_time.isoformat() if item.publish_time else None,
                    item.crawled_at.isoformat(),
                    json.dumps(item.detail_data, ensure_ascii=False) if item.detail_data else '{}'
                ))
            
            args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in data)
            
            cursor.execute(f'''
                INSERT INTO crawled_items (
                    id, title, url, source, publish_time, crawled_at, detail_data
                ) VALUES {args_str}
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    source = EXCLUDED.source,
                    publish_time = EXCLUDED.publish_time,
                    crawled_at = EXCLUDED.crawled_at,
                    detail_data = EXCLUDED.detail_data
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"批量插入成功，共 {len(items)} 条数据")
            return len(items)
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            return 0
    
    def get_items(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取商品列表"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            cursor.execute('''
                SELECT * FROM crawled_items 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            items = []
            for row in rows:
                item = dict(row)
                # 解析JSON数据
                try:
                    item['detail_data'] = json.loads(item['detail_data'])
                except:
                    item['detail_data'] = {}
                
                # 提取图片URL
                if isinstance(item['detail_data'], dict):
                    photos = item['detail_data'].get('photos', [])
                    if photos and isinstance(photos, list) and photos:
                        item['image_url'] = photos[0]
                    else:
                        item['image_url'] = None
                    
                    # 提取其他有用字段
                    item['title'] = item['detail_data'].get('name', item['title'])
                    item['price'] = item['detail_data'].get('price', 'N/A')
                    item['description'] = item['detail_data'].get('description', '')
                    
                    # 安全地提取嵌套字段
                    item_brand = item['detail_data'].get('item_brand', {})
                    item['brand'] = item_brand.get('name', '') if isinstance(item_brand, dict) else ''
                    
                    item_category = item['detail_data'].get('item_category', {})
                    item['category'] = item_category.get('name', '') if isinstance(item_category, dict) else ''
                    
                    item['item_id'] = item['detail_data'].get('id', '')
                else:
                    item['image_url'] = None
                
                items.append(item)
            
            return items
        except Exception as e:
            logger.error(f"获取商品列表失败: {e}")
            return []
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取商品详情"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            cursor.execute('SELECT * FROM crawled_items WHERE id = %s', (item_id,))
            row = cursor.fetchone()
            
            if row:
                item = dict(row)
                # 解析JSON数据
                try:
                    item['detail_data'] = json.loads(item['detail_data'])
                except:
                    item['detail_data'] = {}
                conn.close()
                return item
            
            conn.close()
            return None
        except Exception as e:
            logger.error(f"获取商品详情失败: {e}")
            return None
    
    def get_items_by_keyword(self, keyword: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """根据关键字搜索商品"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            cursor.execute('''
                SELECT * FROM crawled_items 
                WHERE title LIKE %s OR detail_data LIKE %s
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            ''', (f'%{keyword}%', f'%{keyword}%', limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            items = []
            for row in rows:
                item = dict(row)
                # 解析JSON数据
                try:
                    item['detail_data'] = json.loads(item['detail_data'])
                except:
                    item['detail_data'] = {}
                
                # 提取图片URL
                if isinstance(item['detail_data'], dict):
                    photos = item['detail_data'].get('photos', [])
                    if photos and isinstance(photos, list) and photos:
                        item['image_url'] = photos[0]
                    else:
                        item['image_url'] = None
                    
                    # 提取其他有用字段
                    item['title'] = item['detail_data'].get('name', item['title'])
                    item['price'] = item['detail_data'].get('price', 'N/A')
                    item['description'] = item['detail_data'].get('description', '')
                    
                    # 安全地提取嵌套字段
                    item_brand = item['detail_data'].get('item_brand', {})
                    item['brand'] = item_brand.get('name', '') if isinstance(item_brand, dict) else ''
                    
                    item_category = item['detail_data'].get('item_category', {})
                    item['category'] = item_category.get('name', '') if isinstance(item_category, dict) else ''
                    
                    item['item_id'] = item['detail_data'].get('id', '')
                else:
                    item['image_url'] = None
                
                items.append(item)
            
            return items
        except Exception as e:
            logger.error(f"搜索商品失败: {e}")
            return []
    
    def get_total_count(self) -> int:
        """获取商品总数"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM crawled_items')
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            logger.error(f"获取商品总数失败: {e}")
            return 0
    
    def delete_old_data(self, days: int = 30):
        """删除指定天数之前的数据"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM crawled_items 
                WHERE created_at < NOW() - INTERVAL %s
            ''', (f'{days} days',))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"删除了 {deleted_count} 条旧数据")
            return deleted_count
        except Exception as e:
            logger.error(f"删除旧数据失败: {e}")
            return 0
    
    def clear_all_data(self):
        """清除所有数据"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM crawled_items')
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"清除了所有数据，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            logger.error(f"清除数据失败: {e}")
            return 0
    
    def insert_crawler_instance(self, instance_id: str, crawler_name: str, instance_name: str, keywords: List[str], description: str = None) -> bool:
        """插入爬虫实例"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO crawler_instances (
                    id, crawler_name, instance_name, keywords, description, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    crawler_name = EXCLUDED.crawler_name,
                    instance_name = EXCLUDED.instance_name,
                    keywords = EXCLUDED.keywords,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status
            ''', (
                instance_id,
                crawler_name,
                instance_name,
                json.dumps(keywords, ensure_ascii=False),
                description,
                'created'
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"插入爬虫实例失败: {e}")
            return False
    
    def get_crawler_instances(self, crawler_name: str = None) -> List[Dict[str, Any]]:
        """获取爬虫实例列表"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            if crawler_name:
                cursor.execute('''
                    SELECT * FROM crawler_instances 
                    WHERE crawler_name = %s
                    ORDER BY created_at DESC
                ''', (crawler_name,))
            else:
                cursor.execute('''
                    SELECT * FROM crawler_instances 
                    ORDER BY created_at DESC
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            instances = []
            for row in rows:
                instance = dict(row)
                # 解析JSON数据
                try:
                    instance['keywords'] = json.loads(instance['keywords'])
                except:
                    instance['keywords'] = []
                instances.append(instance)
            
            return instances
        except Exception as e:
            logger.error(f"获取爬虫实例列表失败: {e}")
            return []
    
    def get_crawler_instance_by_name(self, instance_name: str) -> Optional[Dict[str, Any]]:
        """根据实例名称获取爬虫实例"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            cursor.execute('SELECT * FROM crawler_instances WHERE instance_name = %s', (instance_name,))
            row = cursor.fetchone()
            
            if row:
                instance = dict(row)
                # 解析JSON数据
                try:
                    instance['keywords'] = json.loads(instance['keywords'])
                except:
                    instance['keywords'] = []
                conn.close()
                return instance
            
            conn.close()
            return None
        except Exception as e:
            logger.error(f"获取爬虫实例失败: {e}")
            return None
    
    def update_crawler_instance_status(self, instance_id: str, status: str) -> bool:
        """更新爬虫实例状态"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE crawler_instances 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (status, instance_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新爬虫实例状态失败: {e}")
            return False
    
    def delete_crawler_instance(self, instance_id: str) -> bool:
        """删除爬虫实例"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM crawler_instances WHERE id = %s', (instance_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"删除爬虫实例失败: {e}")
            return False
    
    def clear_all_instances(self):
        """清除所有爬虫实例数据"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM crawler_instances')
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"清除了所有爬虫实例数据，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            logger.error(f"清除爬虫实例数据失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        # SQLite会自动管理连接，这里可以添加清理逻辑
        pass
