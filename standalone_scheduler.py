#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import sqlite3
import subprocess
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'scheduler.log')
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger('茅台预约调度器')
logger.setLevel(logging.INFO)
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site.db')

def get_table_names():
    """获取数据库中的所有表名"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]
    except Exception as e:
        logger.error(f"获取表名时出错: {str(e)}", exc_info=True)
        return []

def check_tasks():
    """检查并执行需要运行的任务"""
    logger.info("开始检查任务...")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 首先获取所有表名
        tables = get_table_names()
        logger.info(f"数据库中的表: {tables}")
        
        # 判断正确的表名
        task_table = None
        if 'task_setting' in tables:
            task_table = 'task_setting'
        elif 'task' in tables:
            task_table = 'task'
        else:
            # 尝试查找包含'task'的表
            for table in tables:
                if 'task' in table.lower():
                    task_table = table
                    break
        
        if not task_table:
            logger.error("找不到任务表，无法执行调度")
            return
            
        logger.info(f"使用表: {task_table}")
        
        # 查询所有启用的任务
        query = f"SELECT id, preferred_time, last_run FROM {task_table} WHERE enabled = 1"
        cursor.execute(query)
        
        tasks = cursor.fetchall()
        logger.info(f"发现 {len(tasks)} 个已启用的任务")
        
        if not tasks:
            # 尝试不用enabled筛选
            query = f"SELECT id, preferred_time, last_run FROM {task_table}"
            cursor.execute(query)
            tasks = cursor.fetchall()
            logger.info(f"不筛选enabled，发现 {len(tasks)} 个任务")
            
            # 获取列名
            cursor.execute(f"PRAGMA table_info({task_table})")
            columns = [info[1] for info in cursor.fetchall()]
            logger.info(f"表 {task_table} 的列: {columns}")
        
        now = datetime.datetime.now()
        today = now.date()
        
        for task_id, preferred_time, last_run in tasks:
            try:
                # 解析preferred_time (格式可能是HH:MM:SS或time对象)
                if isinstance(preferred_time, str):
                    preferred_parts = preferred_time.split(':')
                    task_hour = int(preferred_parts[0])
                    task_minute = int(preferred_parts[1])
                else:
                    # SQLite可能将time作为字符串或某种对象返回
                    logger.warning(f"未知的时间格式: {type(preferred_time)}, 值: {preferred_time}")
                    continue
                
                # 解析last_run (如果有)
                last_run_date = None
                if last_run:
                    try:
                        if isinstance(last_run, str):
                            # 尝试多种日期格式
                            for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
                                try:
                                    last_run_date = datetime.datetime.strptime(last_run, fmt).date()
                                    break
                                except ValueError:
                                    continue
                        elif isinstance(last_run, datetime.datetime):
                            last_run_date = last_run.date()
                    except Exception as e:
                        logger.error(f"解析last_run时出错: {str(e)}, 值: {last_run}", exc_info=True)
                
                # 当前时间的小时和分钟
                current_hour = now.hour
                current_minute = now.minute
                
                # 计算任务时间和当前时间的分钟差
                task_total_minutes = task_hour * 60 + task_minute
                current_total_minutes = current_hour * 60 + current_minute
                minutes_diff = abs(current_total_minutes - task_total_minutes)
                
                logger.info(f"任务 {task_id}: 设定时间={task_hour}:{task_minute}, 当前时间={current_hour}:{current_minute}, 分钟差={minutes_diff}")
                logger.info(f"任务 {task_id}: 今天日期={today}, 上次运行日期={last_run_date}")
                
                # 如果时间差在1分钟内，且今天还没运行过
                if minutes_diff <= 1 and (last_run_date is None or last_run_date < today):
                    logger.info(f"触发执行任务 {task_id}")
                    
                    # 使用force_execute_task.py执行任务
                    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'force_execute_task.py')
                    
                    try:
                        # 执行命令并捕获输出
                        result = subprocess.run(
                            [sys.executable, script_path, str(task_id)],
                            capture_output=True,
                            text=True
                        )
                        
                        logger.info(f"任务 {task_id} 执行结果: {result.returncode}")
                        logger.info(f"输出: {result.stdout}")
                        
                        if result.stderr:
                            logger.error(f"错误: {result.stderr}")
                        
                    except Exception as e:
                        logger.error(f"执行任务 {task_id} 失败: {str(e)}")
            except Exception as e:
                logger.error(f"处理任务 {task_id} 时出错: {str(e)}", exc_info=True)
        
        conn.close()
    except Exception as e:
        logger.error(f"检查任务时出错: {str(e)}", exc_info=True)

def run_scheduler():
    """运行调度器主循环"""
    logger.info("茅台预约调度器已启动")
    
    try:
        while True:
            try:
                # 检查并执行任务
                check_tasks()
                
                # 等待30秒再次检查
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("调度器收到停止信号，即将退出")
                break
            except Exception as e:
                logger.error(f"调度器循环出错: {str(e)}", exc_info=True)
                # 出错后等待30秒再继续
                time.sleep(30)
    except Exception as e:
        logger.error(f"调度器主循环严重错误: {str(e)}", exc_info=True)

if __name__ == "__main__":
    run_scheduler() 