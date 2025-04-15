#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
from app import app, TaskSetting, TaskItemMapping, real_reservation, db

def run_task_manually(task_id=None):
    """手动执行指定任务或所有启用的任务"""
    with app.app_context():
        if task_id:
            # 执行特定ID的任务
            task = TaskSetting.query.get(task_id)
            if not task:
                print(f"错误: 找不到ID为{task_id}的任务")
                return
            
            tasks = [task]
        else:
            # 执行所有启用的任务
            tasks = TaskSetting.query.filter_by(enabled=True).all()
        
        if not tasks:
            print("没有找到可执行的任务")
            return
        
        print(f"发现 {len(tasks)} 个任务需要执行")
        
        for task in tasks:
            # 获取账号信息
            account_info = f"{task.mt_account.hidemobile}" if task.mt_account else "未知账号"
            
            # 获取商品信息
            item_mappings = TaskItemMapping.query.filter_by(task_id=task.id).all()
            if item_mappings:
                item_codes = [mapping.item_code for mapping in item_mappings]
            else:
                item_codes = [task.item_code]
            
            print(f"执行任务: ID={task.id}, 时间={task.preferred_time}, 账号={account_info}, 商品={item_codes}")
            
            # 执行任务
            success, message = real_reservation(task)
            
            print(f"执行结果: 成功={success}, 消息={message}")
            
            # 输出任务执行后信息
            print(f"最后执行时间: {task.last_run}")

if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) > 1:
        try:
            task_id = int(sys.argv[1])
            run_task_manually(task_id)
        except ValueError:
            print("错误: 任务ID必须是整数")
    else:
        # 没有提供参数，执行所有启用的任务
        run_task_manually() 