#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
from pathlib import Path
import sys

def update_database():
    """
    更新数据库结构，添加缺少的mt_account_id字段
    """
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
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_setting'")
        if not cursor.fetchone():
            print("错误: task_setting表不存在")
            conn.close()
            return False
        
        # 获取表的当前结构
        cursor.execute("PRAGMA table_info(task_setting)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # 检查mt_account_id列是否已存在
        if 'mt_account_id' in columns:
            print("mt_account_id列已存在，无需更新")
            conn.close()
            return True
        
        # 添加新列
        print("添加mt_account_id列...")
        cursor.execute("ALTER TABLE task_setting ADD COLUMN mt_account_id INTEGER")
        
        # 提交更改
        conn.commit()
        print("数据库更新成功！")
        
        # 关闭连接
        conn.close()
        return True
    
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        return False
    except Exception as e:
        print(f"发生异常: {e}")
        return False

if __name__ == "__main__":
    print("开始更新数据库...")
    if update_database():
        print("数据库更新完成")
    else:
        print("数据库更新失败")
        sys.exit(1) 