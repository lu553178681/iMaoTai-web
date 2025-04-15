#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本脚本用于修复WTForms多选字段问题
问题：ImportError: cannot import name 'MultipleCheckboxField' from 'wtforms'
"""

import os
import re

def fix_app_file():
    """修复app.py文件中的MultipleCheckboxField导入问题"""
    app_file = 'app.py'
    
    # 检查文件是否存在
    if not os.path.exists(app_file):
        print(f"错误: 找不到 {app_file} 文件")
        return False
    
    # 读取文件内容
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否存在错误的导入
    if 'MultipleCheckboxField' in content and 'from wtforms import' in content:
        print("检测到可能存在导入问题，开始修复...")
        
        # 修复导入语句
        content = re.sub(
            r'from wtforms import (.*?)MultipleCheckboxField(.*?)',
            r'from wtforms import \1SelectMultipleField, widgets\2',
            content
        )
        
        # 检查是否已有自定义MultipleCheckboxField类
        if 'class MultipleCheckboxField' not in content:
            # 添加自定义MultipleCheckboxField类
            custom_class = '''
# 创建自定义多选字段
class MultipleCheckboxField(SelectMultipleField):
    """
    自定义多选字段，渲染为一组复选框
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()
'''
            # 找到合适的位置插入自定义类（在app创建之后）
            app_init_position = content.find('app = Flask(__name__)')
            if app_init_position > 0:
                db_init_position = content.find('db = SQLAlchemy(app)', app_init_position)
                if db_init_position > 0:
                    insert_position = content.find('\n', db_init_position) + 1
                    content = content[:insert_position] + custom_class + content[insert_position:]
        
        # 写回文件
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("修复完成！")
        return True
    else:
        print("未检测到导入问题，无需修复")
        return True

if __name__ == "__main__":
    print("开始修复WTForms多选字段问题...")
    if fix_app_file():
        print("修复过程完成，请尝试重新运行应用")
    else:
        print("修复失败，请手动检查并修改代码") 