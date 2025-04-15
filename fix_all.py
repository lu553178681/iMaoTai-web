#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
from pathlib import Path
import sqlite3
import time

def print_step(step, message):
    """打印彩色步骤信息"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    print(f"\n{YELLOW}步骤 {step}:{RESET} {GREEN}{message}{RESET}")

def install_dependencies():
    """安装所需的依赖包"""
    print_step(1, "安装依赖包...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("依赖包安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖包失败: {e}")
        try:
            print("尝试直接安装pycryptodome...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome==3.19.0"])
            print("pycryptodome安装成功！")
            return True
        except subprocess.CalledProcessError as e:
            print(f"安装pycryptodome失败: {e}")
            return False

def update_database():
    """更新数据库添加缺少的列"""
    print_step(2, "更新数据库结构...")
    
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

def run_app():
    """测试运行应用"""
    print_step(3, "测试启动应用...")
    try:
        # 仅启动5秒进行测试
        process = subprocess.Popen([sys.executable, "app.py"])
        print("应用启动中，5秒后将停止测试...")
        time.sleep(5)
        process.terminate()
        print("应用启动测试完成")
        return True
    except Exception as e:
        print(f"应用启动失败: {e}")
        return False

def main():
    """执行所有修复步骤"""
    print("\n===== iMaoTai-web 一键修复工具 =====\n")
    
    # 步骤1: 安装依赖
    if not install_dependencies():
        print("依赖安装失败，请手动执行: pip install -r requirements.txt")
        return False
    
    # 步骤2: 更新数据库
    if not update_database():
        print("数据库更新失败")
        return False
    
    # 步骤3: 测试启动应用
    if not run_app():
        print("应用启动测试失败")
        return False
    
    print("\n✨ 所有问题已修复！现在可以正常启动应用了：python app.py\n")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 