#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
from app import app, TaskSetting, db

def reset_task_status(task_id=None):
    """重置任务的执行状态（将last_run设为None）"""
    with app.app_context():
        if task_id:
            # 重置特定ID的任务
            task = TaskSetting.query.get(task_id)
            if not task:
                print(f"错误: 找不到ID为{task_id}的任务")
                return
            
            tasks = [task]
        else:
            # 重置所有启用的任务
            tasks = TaskSetting.query.filter_by(enabled=True).all()
        
        if not tasks:
            print("没有找到可重置的任务")
            return
        
        print(f"找到 {len(tasks)} 个任务需要重置状态")
        
        for task in tasks:
            old_last_run = task.last_run
            task.last_run = None
            print(f"重置任务: ID={task.id}, 原最后执行时间={old_last_run}, 新状态=未执行")
        
        # 提交更改
        db.session.commit()
        print("所有任务状态已重置，可以重新执行了")

if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) > 1:
        try:
            task_id = int(sys.argv[1])
            reset_task_status(task_id)
        except ValueError:
            print("错误: 任务ID必须是整数")
    else:
        # 没有提供参数，重置所有启用的任务
        reset_task_status() 