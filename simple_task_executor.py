#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'simple_executor.log')
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger('简易茅台预约执行器')
logger.setLevel(logging.INFO)
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

def run_task_now():
    """直接从app.py导入所需功能并执行任务"""
    logger.info("===== 开始执行茅台预约任务 =====")
    
    try:
        # 导入Flask应用和相关功能
        logger.info("导入应用模块...")
        from app import app, TaskSetting, real_reservation, db
        
        with app.app_context():
            # 查询所有启用的任务
            logger.info("查询启用的任务...")
            enabled_tasks = TaskSetting.query.filter_by(enabled=True).all()
            
            if not enabled_tasks:
                logger.warning("没有找到启用的任务！")
                return
            
            logger.info(f"找到 {len(enabled_tasks)} 个启用的任务")
            
            now = datetime.datetime.now()
            
            for task in enabled_tasks:
                # 获取任务信息
                task_id = task.id
                task_time = task.preferred_time
                
                # 当前时间
                current_time = now.time()
                
                # 显示任务信息
                logger.info(f"处理任务ID: {task_id}")
                logger.info(f"  设定时间: {task_time}")
                logger.info(f"  当前时间: {current_time}")
                logger.info(f"  最后执行: {task.last_run}")
                
                # 直接执行任务，不考虑时间匹配
                try:
                    logger.info(f"强制执行任务 {task_id}")
                    success, message = real_reservation(task)
                    
                    # 确保更改保存到数据库
                    db.session.commit()
                    
                    logger.info(f"执行结果: 成功={success}, 消息={message}")
                    logger.info(f"更新后的最后执行时间: {task.last_run}")
                except Exception as e:
                    logger.error(f"执行任务 {task_id} 失败: {str(e)}", exc_info=True)
    
    except Exception as e:
        logger.error(f"执行过程出错: {str(e)}", exc_info=True)
    
    logger.info("===== 茅台预约任务执行完毕 =====")

if __name__ == "__main__":
    run_task_now() 