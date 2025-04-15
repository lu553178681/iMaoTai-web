#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

def print_colored(text, color):
    """打印彩色文本"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def fix_werkzeug_version():
    """降级Werkzeug版本以兼容Flask-WTF"""
    print_colored("\n===== 修复Werkzeug版本不兼容问题 =====\n", "yellow")
    
    try:
        # 先卸载当前版本
        print_colored("1. 卸载当前Werkzeug版本...", "yellow")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "werkzeug"])
        
        # 安装兼容版本
        print_colored("2. 安装兼容的Werkzeug版本(2.3.7)...", "yellow")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "werkzeug==2.3.7"])
        
        # 更新requirements.txt
        with open("requirements.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        has_werkzeug = False
        new_lines = []
        for line in lines:
            if line.strip().lower().startswith("werkzeug"):
                new_lines.append("werkzeug==2.3.7\n")
                has_werkzeug = True
            else:
                new_lines.append(line)
        
        if not has_werkzeug:
            new_lines.append("werkzeug==2.3.7\n")
        
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        print_colored("已更新requirements.txt文件", "green")
        
        # 测试导入
        try:
            print_colored("3. 测试导入...", "yellow")
            # 创建一个临时脚本来测试导入
            temp_script = "__temp_test_import.py"
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write("""
try:
    from werkzeug.urls import url_encode
    print("✓ 导入成功!")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    exit(1)
""")
            
            # 执行临时脚本
            subprocess.check_call([sys.executable, temp_script])
            
            # 删除临时脚本
            if os.path.exists(temp_script):
                os.remove(temp_script)
            
            print_colored("\n✨ Werkzeug版本问题已修复!", "green")
            return True
        except subprocess.CalledProcessError:
            print_colored("\n❌ 导入测试失败，可能需要手动解决问题", "red")
            return False
        
    except subprocess.CalledProcessError as e:
        print_colored(f"\n❌ 修复失败: {e}", "red")
        return False

if __name__ == "__main__":
    if fix_werkzeug_version():
        print_colored("\n现在可以尝试重新运行应用: python app.py", "green")
    else:
        print_colored("\n修复失败，请尝试手动安装Werkzeug 2.3.7版本:", "red")
        print_colored("pip install werkzeug==2.3.7", "yellow") 