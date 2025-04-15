#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import time
from app import app, TaskSetting, TaskItemMapping, real_reservation, db

def force_execute_task(task_id=None, time_str=None):
    """强制执行任务，不受时间和执行状态限制"""
    with app.app_context():
        if task_id:
            # 执行特定ID的任务
            task = TaskSetting.query.get(task_id)
            if not task:
                print(f"错误: 找不到ID为{task_id}的任务")
                return
            
            tasks = [task]
        elif time_str:
            # 获取设定时间的所有启用任务
            try:
                # 解析时间字符串，格式为HH:MM
                parts = time_str.split(':')
                if len(parts) != 2:
                    print("错误: 时间格式应为HH:MM")
                    return
                
                hour = int(parts[0])
                minute = int(parts[1])
                task_time = datetime.time(hour, minute)
                
                # 查找该时间点的任务
                tasks = []
                for task in TaskSetting.query.filter_by(enabled=True).all():
                    if task.preferred_time.hour == hour and task.preferred_time.minute == minute:
                        tasks.append(task)
                
                if not tasks:
                    print(f"没有找到设定为{time_str}的任务")
                    return
            except ValueError:
                print("错误: 无法解析时间字符串，格式应为HH:MM")
                return
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
            
            print(f"强制执行任务: ID={task.id}, 时间={task.preferred_time}, 账号={account_info}, 商品={item_codes}")
            
            # 确保账号可用
            if not task.mt_account or not task.mt_account.is_active:
                print(f"警告: 任务ID={task.id}的账号不可用，跳过执行")
                continue
                
            # 执行任务
            success, message = real_reservation(task)
            
            print(f"执行结果: 成功={success}, 消息={message}")
            
            # 确保数据库更改被提交
            db.session.commit()
            
            # 输出任务执行后信息
            print(f"最后执行时间: {task.last_run}")

def wait_and_execute(time_str):
    """等待到指定时间然后执行任务"""
    try:
        # 解析时间字符串，格式为HH:MM
        parts = time_str.split(':')
        if len(parts) != 2:
            print("错误: 时间格式应为HH:MM")
            return
        
        hour = int(parts[0])
        minute = int(parts[1])
        
        # 获取当前时间
        now = datetime.datetime.now()
        
        # 计算目标时间
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 如果目标时间已经过去，则设为明天
        if target_time < now:
            target_time = target_time + datetime.timedelta(days=1)
        
        # 计算需要等待的秒数
        wait_seconds = (target_time - now).total_seconds()
        
        print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"等待 {wait_seconds} 秒后执行...")
        
        # 等待
        time.sleep(wait_seconds)
        
        # 执行任务
        print(f"已到达目标时间 {time_str}，开始执行任务...")
        force_execute_task(time_str=time_str)
        
    except ValueError:
        print("错误: 无法解析时间字符串，格式应为HH:MM")
        return

if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) < 2:
        print("用法: python force_execute_task.py [任务ID | 时间(HH:MM) | -w 时间(HH:MM)]")
        print("示例:")
        print("  python force_execute_task.py 1                # 执行ID为1的任务")
        print("  python force_execute_task.py 16:04            # 执行设定为16:04的所有任务")
        print("  python force_execute_task.py -w 16:10         # 等待到16:10然后执行所有16:10的任务")
        print("  python force_execute_task.py --all            # 执行所有启用的任务")
    else:
        arg = sys.argv[1]
        if arg == "--all":
            # 执行所有启用的任务
            force_execute_task()
        elif arg == "-w" and len(sys.argv) > 2:
            # 等待到指定时间执行
            wait_and_execute(sys.argv[2])
        elif ":" in arg:
            # 按时间执行
            force_execute_task(time_str=arg)
        else:
            try:
                # 按ID执行
                task_id = int(arg)
                force_execute_task(task_id=task_id)
            except ValueError:
                print("错误: 参数必须是整数任务ID、时间(HH:MM)或--all") 