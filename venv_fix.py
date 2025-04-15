#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import shutil
import sqlite3
from pathlib import Path
import time

# 定义颜色
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_colored(text, color):
    """打印彩色文本"""
    colors = {
        "green": GREEN,
        "yellow": YELLOW,
        "red": RED,
        "reset": RESET
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 50)
    print_colored(text.center(50), "yellow")
    print("=" * 50 + "\n")

def ask_yes_no(question):
    """询问用户是/否问题"""
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        print("请输入 y 或 n")

def update_database():
    """更新数据库添加缺少的列"""
    print_header("修复数据库结构")
    
    # 检查数据库文件
    db_path = Path('instance/site.db')
    if not db_path.exists():
        print_colored("错误: 数据库文件不存在，请先运行应用创建数据库", "red")
        return False
    
    print_colored(f"连接数据库: {db_path}", "yellow")
    
    try:
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_setting'")
        if not cursor.fetchone():
            print_colored("错误: task_setting表不存在", "red")
            conn.close()
            return False
        
        # 获取表的当前结构
        cursor.execute("PRAGMA table_info(task_setting)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # 检查mt_account_id列是否已存在
        if 'mt_account_id' in columns:
            print_colored("mt_account_id列已存在，无需更新", "green")
            conn.close()
            return True
        
        # 添加新列
        print_colored("添加mt_account_id列...", "yellow")
        cursor.execute("ALTER TABLE task_setting ADD COLUMN mt_account_id INTEGER")
        
        # 提交更改
        conn.commit()
        print_colored("数据库更新成功！", "green")
        
        # 关闭连接
        conn.close()
        return True
    
    except sqlite3.Error as e:
        print_colored(f"数据库错误: {e}", "red")
        return False
    except Exception as e:
        print_colored(f"发生异常: {e}", "red")
        return False

def update_requirements():
    """更新requirements.txt文件，指定所有包的确切版本以确保兼容性"""
    print_header("更新依赖配置")
    
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
    
    try:
        # 写入新的requirements.txt
        with open("requirements.txt", "w", encoding="utf-8") as f:
            for package in compatible_packages:
                f.write(f"{package}\n")
        
        print_colored("已更新requirements.txt，设置了兼容的包版本", "green")
        return True
    except Exception as e:
        print_colored(f"更新requirements.txt失败: {e}", "red")
        return False

def install_dependencies():
    """安装依赖包"""
    print_header("安装依赖包")
    
    try:
        # 尝试安装所有依赖
        print_colored("安装依赖中...", "yellow")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print_colored("依赖安装成功！", "green")
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"安装依赖失败: {e}", "red")
        
        # 尝试单独安装关键包
        try:
            print_colored("尝试单独安装werkzeug 2.3.7版本...", "yellow")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "werkzeug==2.3.7"])
            print_colored("werkzeug安装成功！", "green")
            
            print_colored("尝试单独安装pycryptodome...", "yellow")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome==3.19.0"])
            print_colored("pycryptodome安装成功！", "green")
            
            return True
        except subprocess.CalledProcessError as e:
            print_colored(f"单独安装关键包失败: {e}", "red")
            return False

def test_imports():
    """测试关键导入是否正常"""
    print_header("测试关键导入")
    
    # 需要测试的导入
    imports_to_test = [
        "from werkzeug.urls import url_encode",
        "from flask_wtf import FlaskForm",
        "from Crypto.Cipher import AES"
    ]
    
    # 创建临时脚本
    temp_script = "__temp_test_imports.py"
    with open(temp_script, "w", encoding="utf-8") as f:
        f.write("import sys\n\n")
        
        for i, import_str in enumerate(imports_to_test):
            f.write(f"try:\n")
            f.write(f"    {import_str}\n")
            f.write(f"    print('导入 {i+1} 成功: {import_str}')\n")
            f.write(f"except Exception as e:\n")
            f.write(f"    print('导入 {i+1} 失败: {import_str} - ' + str(e))\n")
            f.write(f"    sys.exit(1)\n\n")
        
        f.write("print('所有导入测试通过！')\n")
    
    # 执行临时脚本
    try:
        subprocess.check_call([sys.executable, temp_script])
        print_colored("所有关键导入测试成功！", "green")
        success = True
    except subprocess.CalledProcessError:
        print_colored("导入测试失败，可能仍存在兼容性问题", "red")
        success = False
    
    # 删除临时脚本
    if os.path.exists(temp_script):
        os.remove(temp_script)
    
    return success

def test_app():
    """测试应用是否能正常启动"""
    print_header("测试应用启动")
    
    try:
        # 仅启动3秒进行测试
        print_colored("启动应用中...", "yellow")
        process = subprocess.Popen([sys.executable, "app.py"])
        print_colored("应用启动中，3秒后将自动停止...", "yellow")
        time.sleep(3)
        process.terminate()
        # 给进程一些时间正常退出
        process.wait(timeout=2)
        print_colored("应用启动测试通过！", "green")
        return True
    except subprocess.SubprocessError as e:
        print_colored(f"应用启动失败: {e}", "red")
        return False
    except Exception as e:
        print_colored(f"测试过程中发生错误: {e}", "red")
        return False

def rebuild_venv():
    """重建虚拟环境"""
    print_header("重建虚拟环境")
    
    venv_path = os.path.join(os.getcwd(), "venv")
    
    # 备份原虚拟环境
    if os.path.exists(venv_path):
        print_colored("备份原虚拟环境...", "yellow")
        backup_path = venv_path + "_backup_" + time.strftime("%Y%m%d%H%M%S")
        try:
            shutil.move(venv_path, backup_path)
            print_colored(f"原虚拟环境已备份到: {backup_path}", "green")
        except Exception as e:
            print_colored(f"备份虚拟环境失败，可能需要手动删除: {e}", "red")
            if not ask_yes_no("是否继续重建虚拟环境？"):
                return False
    
    # 创建新的虚拟环境
    print_colored("创建新的虚拟环境...", "yellow")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
        print_colored("虚拟环境创建成功！", "green")
        
        # 获取虚拟环境中的python和pip路径
        if os.name == 'nt':  # Windows
            python_path = os.path.join(venv_path, "Scripts", "python.exe")
            pip_path = os.path.join(venv_path, "Scripts", "pip.exe")
        else:  # Linux/Mac
            python_path = os.path.join(venv_path, "bin", "python")
            pip_path = os.path.join(venv_path, "bin", "pip")
        
        # 更新pip
        print_colored("更新pip...", "yellow")
        subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安装依赖
        print_colored("安装项目依赖...", "yellow")
        subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
        
        print_colored("虚拟环境重建并安装依赖成功！", "green")
        print_colored("\n请退出当前终端，重新打开终端后激活虚拟环境：", "yellow")
        if os.name == 'nt':  # Windows
            print_colored("venv\\Scripts\\activate", "green")
        else:  # Linux/Mac
            print_colored("source venv/bin/activate", "green")
        
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"重建虚拟环境失败: {e}", "red")
        return False

def main():
    """主函数，执行所有修复步骤"""
    print_header("iMaoTai-web 环境修复工具")
    
    # 更新requirements.txt
    update_requirements()
    
    # 询问用户是否要重建虚拟环境
    if ask_yes_no("是否要重建虚拟环境？（推荐，可解决大部分依赖问题）"):
        if rebuild_venv():
            print_colored("\n虚拟环境已重建。请关闭此终端并使用新终端激活环境后，再次运行此脚本完成数据库修复。", "green")
            return
    
    # 安装依赖
    install_dependencies()
    
    # 测试关键导入
    if not test_imports():
        print_colored("\n关键导入测试失败。请考虑重建虚拟环境解决问题。", "red")
        return
    
    # 更新数据库
    update_database()
    
    # 测试应用启动
    test_result = test_app()
    
    # 输出最终结果
    if test_result:
        print_header("修复完成")
        print_colored("所有问题已修复！现在可以正常启动应用：", "green")
        print_colored("python app.py", "yellow")
    else:
        print_header("修复未完成")
        print_colored("应用启动测试失败，可能需要进一步排查问题。", "red")
        print_colored("建议重建虚拟环境后再试。", "yellow")

if __name__ == "__main__":
    main() 