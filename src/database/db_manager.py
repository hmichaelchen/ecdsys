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
    
    def __new__(cls, *args, **kwargs):
        """单例模式，确保整个应用只有一个数据库实例"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = ":memory:"):
        """初始化数据库连接"""
        if not hasattr(self, '_initialized') or not self._initialized:
            # 完全使用内存数据库，不再创建文件
            self.db_path = ":memory:"
            logger.info("使用内存数据库")
            
            # 创建持久的数据库连接
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._cursor = self._conn.cursor()
            
            self._init_database()
            self._initialized = True
    
    def _init_database(self):
        """初始化数据库表结构"""
        # 创建商品表
        self._cursor.execute('''
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
        self._cursor.execute('''
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
        self._cursor.execute('CREATE INDEX IF NOT EXISTS idx_crawled_at ON crawled_items(crawled_at)')
        self._cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON crawled_items(source)')
        self._cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON crawled_items(created_at)')
        self._cursor.execute('CREATE INDEX IF NOT EXISTS idx_crawler_name ON crawler_instances(crawler_name)')
        self._cursor.execute('CREATE INDEX IF NOT EXISTS idx_instance_name ON crawler_instances(instance_name)')
        self._cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON crawler_instances(status)')
        
        self._conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")
    
    def insert_item(self, item: CrawledItem) -> bool:
        """插入单个商品数据"""
        try:
            self._cursor.execute('''
                INSERT OR REPLACE INTO crawled_items (
                    id, title, url, source, publish_time, crawled_at, detail_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.id,
                item.title,
                item.url,
                item.source,
                item.publish_time.isoformat() if item.publish_time else None,
                item.crawled_at.isoformat(),
                json.dumps(item.detail_data, ensure_ascii=False) if item.detail_data else '{}'
            ))
            
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"插入商品数据失败: {e}")
            return False
    
    def batch_insert(self, items: List[CrawledItem]) -> int:
        """批量插入商品数据"""
        if not items:
            return 0
        
        try:
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
            
            self._cursor.executemany('''
                INSERT OR REPLACE INTO crawled_items (
                    id, title, url, source, publish_time, crawled_at, detail_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            self._conn.commit()
            logger.info(f"批量插入成功，共 {len(items)} 条数据")
            return len(items)
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            return 0
    
    def get_items(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取商品列表"""
        try:
            self._conn.row_factory = sqlite3.Row
            
            self._cursor.execute('''
                SELECT * FROM crawled_items 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = self._cursor.fetchall()
            
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
            self._conn.row_factory = sqlite3.Row
            
            self._cursor.execute('SELECT * FROM crawled_items WHERE id = ?', (item_id,))
            row = self._cursor.fetchone()
            
            if row:
                item = dict(row)
                # 解析JSON数据
                try:
                    item['detail_data'] = json.loads(item['detail_data'])
                except:
                    item['detail_data'] = {}
                return item
            
            return None
        except Exception as e:
            logger.error(f"获取商品详情失败: {e}")
            return None
    
    def get_items_by_keyword(self, keyword: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """根据关键字搜索商品"""
        try:
            self._conn.row_factory = sqlite3.Row
            
            self._cursor.execute('''
                SELECT * FROM crawled_items 
                WHERE title LIKE ? OR detail_data LIKE ?
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (f'%{keyword}%', f'%{keyword}%', limit, offset))
            
            rows = self._cursor.fetchall()
            
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
            self._cursor.execute('SELECT COUNT(*) FROM crawled_items')
            count = self._cursor.fetchone()[0]
            
            return count
        except Exception as e:
            logger.error(f"获取商品总数失败: {e}")
            return 0
    
    def delete_old_data(self, days: int = 30):
        """删除指定天数之前的数据"""
        try:
            cutoff_date = datetime.now().strftime('%Y-%m-%d')
            self._cursor.execute('''
                DELETE FROM crawled_items 
                WHERE DATE(created_at) < DATE(?, '-' || ? || ' days')
            ''', (cutoff_date, days))
            
            deleted_count = self._cursor.rowcount
            self._conn.commit()
            
            if deleted_count > 0:
                logger.info(f"删除了 {deleted_count} 条旧数据")
            return deleted_count
        except Exception as e:
            logger.error(f"删除旧数据失败: {e}")
            return 0
    
    def clear_all_data(self):
        """清除所有数据"""
        try:
            self._cursor.execute('DELETE FROM crawled_items')
            deleted_count = self._cursor.rowcount
            
            self._conn.commit()
            
            logger.info(f"清除了所有数据，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            logger.error(f"清除数据失败: {e}")
            return 0
    
    def insert_crawler_instance(self, instance_id: str, crawler_name: str, instance_name: str, keywords: List[str], description: str = None) -> bool:
        """插入爬虫实例"""
        try:
            self._cursor.execute('''
                INSERT OR REPLACE INTO crawler_instances (
                    id, crawler_name, instance_name, keywords, description, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                instance_id,
                crawler_name,
                instance_name,
                json.dumps(keywords, ensure_ascii=False),
                description,
                'created'
            ))
            
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"插入爬虫实例失败: {e}")
            return False
    
    def get_crawler_instances(self, crawler_name: str = None) -> List[Dict[str, Any]]:
        """获取爬虫实例列表"""
        try:
            self._conn.row_factory = sqlite3.Row
            
            if crawler_name:
                self._cursor.execute('''
                    SELECT * FROM crawler_instances 
                    WHERE crawler_name = ?
                    ORDER BY created_at DESC
                ''', (crawler_name,))
            else:
                self._cursor.execute('''
                    SELECT * FROM crawler_instances 
                    ORDER BY created_at DESC
                ''')
            
            rows = self._cursor.fetchall()
            
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
            self._conn.row_factory = sqlite3.Row
            
            self._cursor.execute('SELECT * FROM crawler_instances WHERE instance_name = ?', (instance_name,))
            row = self._cursor.fetchone()
            
            if row:
                instance = dict(row)
                # 解析JSON数据
                try:
                    instance['keywords'] = json.loads(instance['keywords'])
                except:
                    instance['keywords'] = []
                return instance
            
            return None
        except Exception as e:
            logger.error(f"获取爬虫实例失败: {e}")
            return None
    
    def update_crawler_instance_status(self, instance_id: str, status: str) -> bool:
        """更新爬虫实例状态"""
        try:
            self._cursor.execute('''
                UPDATE crawler_instances 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, instance_id))
            
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"更新爬虫实例状态失败: {e}")
            return False
    
    def delete_crawler_instance(self, instance_id: str) -> bool:
        """删除爬虫实例"""
        try:
            self._cursor.execute('DELETE FROM crawler_instances WHERE id = ?', (instance_id,))
            
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除爬虫实例失败: {e}")
            return False
    
    def clear_all_instances(self):
        """清除所有爬虫实例数据"""
        try:
            self._cursor.execute('DELETE FROM crawler_instances')
            deleted_count = self._cursor.rowcount
            
            self._conn.commit()
            
            logger.info(f"清除了所有爬虫实例数据，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            logger.error(f"清除爬虫实例数据失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, '_conn'):
            self._conn.close()
            logger.info("数据库连接已关闭")
