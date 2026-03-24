from flask import jsonify, request, Response
from src.database.db_manager import DatabaseManager
from src.crawler import CrawlerManager
from src.models import CrawlerConfig
from src.web.web_monitor import WebMonitor
import asyncio
import threading
import sys
import os
import time
import json
from loguru import logger

# 创建全局实例
db_manager = DatabaseManager()
current_crawler_manager = CrawlerManager()

# 爬虫状态跟踪
crawler_status = {
    'is_running': False,
    'completed': False,
    'count': 0,
    'error': None,
    'running_instances': []  # 正在运行的实例列表
}


def register_routes(app, log_collector):
    """注册所有路由"""

    @app.route('/api/items')
    def api_items():
        """API接口，返回商品数据"""
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = (page - 1) * limit
        
        items = db_manager.get_items(limit=limit, offset=offset)
        total_count = db_manager.get_total_count()
        
        return jsonify({
            'items': items,
            'page': page,
            'limit': limit,
            'total_count': total_count,
            'total_pages': (total_count + limit - 1) // limit
        })

    @app.route('/api/item/<item_id>')
    def api_item(item_id):
        """API接口，返回单个商品详情"""
        item = db_manager.get_item_by_id(item_id)
        if item:
            return jsonify(item)
        else:
            return jsonify({'error': '商品不存在'}), 404





    @app.route('/api/sse')
    def sse():
        """SSE端点，推送爬虫状态和进度信息"""
        def generate():
            while True:
                # 获取爬虫状态
                status_data = crawler_status
                
                # 获取所有爬虫的进度
                progress_map = {}
                registered_crawlers = current_crawler_manager.get_registered_crawlers()
                for crawler_name in registered_crawlers:
                    progress_dict = current_crawler_manager.get_crawler_progress(crawler_name)
                    progress_list = []
                    for key, progress_data in progress_dict.items():
                        if progress_data:
                            parts = key.split('_')
                            if len(parts) >= 2:
                                instance_id = parts[-1]
                                progress_list.append({
                                    'name': crawler_name,
                                    'instance_id': instance_id,
                                    'progress': progress_data.get('progress_percent', 0),
                                    'current': progress_data.get('completed', 0),
                                    'total': progress_data.get('total', 0),
                                    'message': progress_data.get('current_item', '')
                                })
                    if progress_list:
                        progress_map[crawler_name] = progress_list
                
                # 构造SSE消息
                data = {
                    'status': status_data,
                    'progress': progress_map
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(1)  # 每秒推送一次
        
        return Response(generate(), mimetype='text/event-stream')

    @app.route('/api/crawlers')
    def get_crawlers():
        """获取已注册的爬虫列表"""
        registered_crawlers = current_crawler_manager.get_registered_crawlers()
        
        crawlers_info = []
        for crawler_name in registered_crawlers:
            crawlers_info.append({
                'name': crawler_name
            })
        
        return jsonify({'crawlers': crawlers_info})



    @app.route('/api/crawler-instances')
    def get_crawler_instances():
        """获取所有已创建的爬虫实例"""
        crawler_name = request.args.get('name')
        instances = db_manager.get_crawler_instances(crawler_name)
        # 移除status字段，因为状态只在内存中跟踪，不需要从数据库读取
        processed_instances = []
        for instance in instances:
            # 创建一个新的字典，移除status字段
            processed_instance = {k: v for k, v in instance.items() if k != 'status'}
            processed_instances.append(processed_instance)
        return jsonify({'instances': processed_instances})

    @app.route('/api/create-crawler-instance', methods=['POST'])
    def create_crawler_instance():
        """创建爬虫实例但不启动"""
        data = request.get_json()
        crawler_name = data.get('name')
        instance_name = data.get('instance_name')
        keywords = data.get('keywords', [])
        description = data.get('description', '')
        
        if not crawler_name:
            return jsonify({'success': False, 'error': '爬虫名称不能为空'}), 400
        
        if not instance_name:
            return jsonify({'success': False, 'error': '实例名称不能为空'}), 400
        
        # 检查实例是否已存在
        existing_instance = db_manager.get_crawler_instance_by_name(instance_name)
        if existing_instance:
            return jsonify({'success': False, 'error': '实例名称已存在'}), 400
        
        # 创建新实例，检查关键字是否提供
        if not keywords:
            return jsonify({'success': False, 'error': '创建新实例时必须提供关键字'}), 400
        
        # 使用实例名称作为实例ID
        instance_id = instance_name
        
        # 将实例信息保存到数据库
        success = db_manager.insert_crawler_instance(instance_id, crawler_name, instance_name, keywords, description)
        
        if success:
            return jsonify({'success': True, 'message': f'爬虫实例 {instance_name} 已创建'})
        else:
            return jsonify({'success': False, 'error': '创建实例失败'}), 500

    @app.route('/api/start-crawler-instance', methods=['POST'])
    def start_crawler_instance():
        """启动爬虫实例（支持创建新实例和启动已有实例）"""
        data = request.get_json()
        crawler_name = data.get('name')
        instance_name = data.get('instance_name')
        keywords = data.get('keywords', [])
        description = data.get('description', '')
        
        if not crawler_name:
            return jsonify({'success': False, 'error': '爬虫名称不能为空'}), 400
        
        if not instance_name:
            return jsonify({'success': False, 'error': '实例名称不能为空'}), 400
        
        # 检查实例是否已存在
        existing_instance = db_manager.get_crawler_instance_by_name(instance_name)
        if existing_instance:
            # 实例已存在，使用现有配置
            keywords = existing_instance.get('keywords', [])
            description = existing_instance.get('description', '')
        else:
            # 创建新实例，检查关键字是否提供
            if not keywords:
                return jsonify({'success': False, 'error': '创建新实例时必须提供关键字'}), 400
        
        # 设置爬虫状态为运行中
        crawler_status['is_running'] = True
        crawler_status['completed'] = False
        crawler_status['error'] = None
        
        # 创建爬虫配置
        config = CrawlerConfig(url="", keywords=keywords)
        
        # 使用实例名称作为实例ID
        instance_id = instance_name
        
        # 更新运行中的实例列表
        if instance_id not in crawler_status['running_instances']:
            crawler_status['running_instances'].append(instance_id)
        
        # 将实例信息保存到数据库（不更新状态）
        db_manager.insert_crawler_instance(instance_id, crawler_name, instance_name, keywords, description)
        
        # 创建Web监控器
        def progress_callback(progress):
            logger.info(f"爬虫进度更新 - {instance_id}: {progress}")
        
        monitor = WebMonitor(
            progress_callback=progress_callback,
            crawler_manager=current_crawler_manager,
            crawler_name=crawler_name,
            instance_id=instance_id
        )
        
        # 创建线程来直接运行异步爬虫
        def run_crawler_in_thread():
            logger.info(f"开始执行爬虫任务: {crawler_name} [{instance_id}]")
            try:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # 运行异步爬虫
                loop.run_until_complete(current_crawler_manager.run_crawler(crawler_name, config, instance_id, monitor))
                
                # 关闭事件循环
                loop.close()
                
                logger.info(f"爬虫任务完成: {crawler_name} [{instance_id}]")
                
                # 从运行列表中移除
                if instance_id in crawler_status['running_instances']:
                    crawler_status['running_instances'].remove(instance_id)
                
                # 如果没有运行中的实例，重置状态
                if not crawler_status['running_instances']:
                    crawler_status['is_running'] = False
                    crawler_status['completed'] = True
                    
            except Exception as e:
                logger.error(f"爬虫执行出错: {str(e)}")
                # 更新状态为错误
                crawler_status['error'] = str(e)
        
        # 创建并启动线程
        thread = threading.Thread(target=run_crawler_in_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': f'爬虫实例 {instance_name} 已开始运行'})

    @app.route('/api/stop-crawler-instance', methods=['POST'])
    def stop_crawler_instance():
        """终止爬虫实例"""
        data = request.get_json()
        crawler_name = data.get('name')
        instance_id = data.get('instance_id')
        
        if not crawler_name:
            return jsonify({'success': False, 'error': '爬虫名称不能为空'}), 400
        
        try:
            success = current_crawler_manager.cancel_crawler(crawler_name, instance_id)
            if success:
                # 从运行列表中移除
                if instance_id in crawler_status['running_instances']:
                    crawler_status['running_instances'].remove(instance_id)
                return jsonify({'success': True, 'message': f'成功终止爬虫实例'})
            else:
                return jsonify({'success': False, 'error': '爬虫实例不在运行中'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/delete-crawler-instance', methods=['POST'])
    def delete_crawler_instance():
        """删除爬虫实例"""
        data = request.get_json()
        crawler_name = data.get('name')
        instance_name = data.get('instance_name')
        
        if not crawler_name:
            return jsonify({'success': False, 'error': '爬虫名称不能为空'}), 400
        
        if not instance_name:
            return jsonify({'success': False, 'error': '实例名称不能为空'}), 400
        
        try:
            # 检查实例是否正在运行
            running_instances = current_crawler_manager.get_running_crawlers()
            if crawler_name in running_instances and instance_name in running_instances[crawler_name]:
                return jsonify({'success': False, 'error': '实例正在运行中，无法删除'}), 400
            
            # 删除实例
            success = db_manager.delete_crawler_instance(instance_name)
            if success:
                return jsonify({'success': True, 'message': f'成功删除爬虫实例 {instance_name}'})
            else:
                return jsonify({'success': False, 'error': '实例不存在'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/clear-data', methods=['POST'])
    def clear_data():
        """清除数据库所有数据"""
        try:
            deleted_count = db_manager.clear_all_data()
            return jsonify({'success': True, 'message': f'成功清除 {deleted_count} 条数据'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
