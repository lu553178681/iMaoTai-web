#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
from app import app, db, Reservation

def add_mt_account_id_to_reservation():
    """为Reservation表添加mt_account_id字段"""
    try:
        # 获取数据库路径
        db_path = os.path.join(app.root_path, 'instance', 'site.db')
        if not os.path.exists(db_path):
            print(f"数据库文件不存在: {db_path}")
            return False

        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查是否已存在mt_account_id列
        cursor.execute("PRAGMA table_info(reservation)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'mt_account_id' not in column_names:
            print("添加 mt_account_id 列到 reservation 表...")
            cursor.execute("ALTER TABLE reservation ADD COLUMN mt_account_id INTEGER REFERENCES maotai_account(id)")
            conn.commit()
            print("列添加成功")
        else:
            print("mt_account_id 列已存在")

        # 关闭连接
        conn.close()
        
        print("数据库更新完成")
        return True
    except Exception as e:
        print(f"更新数据库时出错: {str(e)}")
        return False

if __name__ == "__main__":
    with app.app_context():
        add_mt_account_id_to_reservation() 