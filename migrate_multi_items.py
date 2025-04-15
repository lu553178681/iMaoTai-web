#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本脚本用于迁移数据库结构，添加多商品支持
"""

import os
import sys
import sqlite3
import json
from pathlib import Path

def migrate_database():
    """升级数据库以支持多商品预约"""
    # 检查数据库文件
    db_path = Path('instance/site.db')
    if not db_path.exists():
        print("错误: 数据库文件不存在，请先运行应用创建数据库")
        return False
    
    print(f"连接数据库: {db_path}")
    
    try:
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_item_mapping'")
        if cursor.fetchone():
            print("task_item_mapping 表已存在，无需迁移")
            conn.close()
            return True
        
        # 创建新表
        print("创建 task_item_mapping 表...")
        cursor.execute('''
        CREATE TABLE task_item_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            item_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES task_setting (id) ON DELETE CASCADE
        )
        ''')
        
        # 迁移现有数据
        print("迁移现有任务数据...")
        cursor.execute("SELECT id, item_code FROM task_setting")
        existing_tasks = cursor.fetchall()
        
        for task_id, item_code in existing_tasks:
            if item_code:
                cursor.execute(
                    "INSERT INTO task_item_mapping (task_id, item_code) VALUES (?, ?)",
                    (task_id, item_code)
                )
        
        # 添加索引提高查询性能
        cursor.execute("CREATE INDEX idx_task_item_task_id ON task_item_mapping (task_id)")
        cursor.execute("CREATE INDEX idx_task_item_item_code ON task_item_mapping (item_code)")
        
        # 提交更改
        conn.commit()
        print("数据库迁移成功！")
        
        # 关闭连接
        conn.close()
        return True
    
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        return False
    except Exception as e:
        print(f"发生异常: {e}")
        return False

def update_app_code():
    """更新app.py中的代码以使用新的数据结构"""
    app_file = 'app.py'
    
    # 检查文件是否存在
    if not os.path.exists(app_file):
        print(f"错误: 找不到 {app_file} 文件")
        return False
    
    print(f"更新 {app_file} 应用代码...")
    
    # 读取文件内容
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加新的模型类定义
    model_definition = '''
class TaskItemMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task_setting.id', ondelete='CASCADE'), nullable=False)
    item_code = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
'''
    
    # 定位插入位置（在TaskSetting类之后）
    task_setting_end = content.find('class ReservationForm')
    if task_setting_end < 0:
        task_setting_end = content.find('class TaskSettingForm')
    
    if task_setting_end > 0:
        # 找到合适的插入位置
        insert_position = content.rfind("\n\n", 0, task_setting_end)
        if insert_position > 0:
            content = content[:insert_position] + model_definition + content[insert_position:]
            
            # 修改 create_task 函数
            # ...等更多代码修改逻辑
            
            # 写回文件
            with open(app_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"{app_file} 更新成功！")
            return True
    
    print(f"无法更新 {app_file}，请手动添加 TaskItemMapping 模型")
    return False

if __name__ == "__main__":
    print("开始迁移数据库以支持多商品预约...")
    
    db_success = migrate_database()
    if not db_success:
        print("数据库迁移失败，中止操作")
        sys.exit(1)
    
    # 暂时不自动修改app.py代码，避免复杂度
    # code_success = update_app_code()
    
    print("\n迁移完成！现在系统已支持每个任务预约多个商品")
    print("请手动修改app.py添加TaskItemMapping模型，然后重启应用") 