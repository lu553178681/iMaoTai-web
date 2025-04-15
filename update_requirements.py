#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

def update_requirements():
    """更新requirements.txt文件，指定所有包的确切版本以确保兼容性"""
    
    # 兼容版本集合
    compatible_packages = [
        "Flask==2.3.3",
        "Flask-Login==0.6.2",
        "Flask-SQLAlchemy==3.0.5",
        "Flask-WTF==1.1.1",
        "pycryptodome==3.19.0",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "WTForms==3.0.1",
        "werkzeug==2.3.7",  # 这个版本对Flask-WTF兼容
        "Jinja2==3.1.2",
        "itsdangerous==2.1.2",
        "SQLAlchemy==2.0.23",
        "click==8.1.7",
        "blinker==1.6.2",
    ]
    
    # 写入新的requirements.txt
    with open("requirements.txt", "w", encoding="utf-8") as f:
        for package in compatible_packages:
            f.write(f"{package}\n")
    
    print(f"已更新requirements.txt，设置了兼容的包版本")
    
    return True

if __name__ == "__main__":
    print("\n===== 更新依赖包版本 =====\n")
    if update_requirements():
        print("\n✅ requirements.txt已更新，请运行以下命令安装依赖：")
        print("pip install -r requirements.txt")
    else:
        print("\n❌ 更新失败") 