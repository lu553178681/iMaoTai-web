#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import importlib.util
import inspect

def print_colored(text, color):
    """打印彩色文本"""
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def apply_werkzeug_patch():
    """
    为werkzeug创建一个补丁，添加url_encode函数
    这是一个临时解决方案，通过monkey patching添加url_encode函数
    """
    print_colored("\n===== Werkzeug URL编码补丁 =====\n", "yellow")
    
    try:
        # 确认werkzeug已安装
        import werkzeug
        import werkzeug.urls
        
        # 检查是否已经有url_encode函数
        if hasattr(werkzeug.urls, 'url_encode'):
            print_colored("werkzeug.urls已经有url_encode函数，无需修补", "green")
            return True
        
        # 查找werkzeug.urls模块的路径
        werkzeug_url_path = os.path.abspath(inspect.getfile(werkzeug.urls))
        werkzeug_dir = os.path.dirname(werkzeug_url_path)
        
        print_colored(f"Werkzeug URLs模块路径: {werkzeug_url_path}", "yellow")
        
        # 创建补丁代码
        patch_code = """
# 此函数由iMaoTai-web修复工具添加，用于兼容Flask-WTF
def url_encode(obj, charset='utf-8', sort=False, key=None, separator='&'):
    '''URL编码一个字典或序列对象.'''
    items = []
    from urllib.parse import quote

    # 将序列转换为键值对
    if isinstance(obj, (list, tuple)):
        for k, v in obj:
            items.append((k, v))
    else:
        for k in sorted(obj) if sort else obj:
            if key is not None:
                k = key(k)
            if k is None:
                continue
            v = obj[k]
            if v is None:
                continue
            items.append((k, v))

    # 将所有键值对转换为字符串并URL编码
    tmp = []
    for k, v in items:
        if isinstance(v, (list, tuple)):
            for v2 in v:
                tmp.append(f"{quote(str(k))}={quote(str(v2))}")
        else:
            tmp.append(f"{quote(str(k))}={quote(str(v))}")

    return separator.join(tmp)
"""
        
        # 创建补丁文件
        patch_file = os.path.join(werkzeug_dir, 'url_patch.py')
        with open(patch_file, 'w', encoding='utf-8') as f:
            f.write(patch_code)
        
        print_colored(f"补丁文件已创建: {patch_file}", "green")
        
        # 打补丁到werkzeug.urls模块
        with open(werkzeug_url_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经导入了url_patch
        if 'from .url_patch import url_encode' not in content:
            with open(werkzeug_url_path, 'a', encoding='utf-8') as f:
                f.write("\n# 添加url_encode兼容函数\ntry:\n    from .url_patch import url_encode\nexcept ImportError:\n    pass\n")
            
            print_colored("已将url_encode函数导入添加到werkzeug.urls模块", "green")
        else:
            print_colored("werkzeug.urls模块已经导入了url_encode函数", "green")
        
        # 重新加载werkzeug.urls模块
        importlib.reload(werkzeug.urls)
        
        # 验证函数是否可用
        if hasattr(werkzeug.urls, 'url_encode'):
            print_colored("补丁应用成功！url_encode函数现在可用", "green")
            return True
        else:
            print_colored("补丁应用失败，url_encode函数仍然不可用", "red")
            return False
    
    except ImportError:
        print_colored("无法导入werkzeug模块，请先安装或升级werkzeug", "red")
        return False
    except Exception as e:
        print_colored(f"应用补丁时发生错误: {e}", "red")
        return False

def create_fix_flask_login_script():
    """创建一个修复Flask-Login的脚本"""
    script_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 为werkzeug创建一个url_encode补丁
from werkzeug import urls

# 如果werkzeug.urls没有url_encode函数，添加一个
if not hasattr(urls, 'url_encode'):
    def url_encode(obj, charset='utf-8', sort=False, key=None, separator='&'):
        '''URL encode a dict/sequence of two-tuples'''
        items = []
        from urllib.parse import quote

        # 将序列转换为键值对
        if isinstance(obj, (list, tuple)):
            for k, v in obj:
                items.append((k, v))
        else:
            for k in sorted(obj) if sort else obj:
                if key is not None:
                    k = key(k)
                if k is None:
                    continue
                v = obj[k]
                if v is None:
                    continue
                items.append((k, v))

        # 将所有键值对转换为字符串并URL编码
        tmp = []
        for k, v in items:
            if isinstance(v, (list, tuple)):
                for v2 in v:
                    tmp.append(f"{quote(str(k))}={quote(str(v2))}")
            else:
                tmp.append(f"{quote(str(k))}={quote(str(v))}")

        return separator.join(tmp)
    
    # 给模块添加此函数
    urls.url_encode = url_encode
    print("已添加url_encode函数到werkzeug.urls模块")

print("Flask-Login补丁已准备就绪")
"""
    
    # 写入文件
    script_path = 'fix_flask_login.py'
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print_colored(f"已创建Flask-Login修复脚本: {script_path}", "green")
    print_colored("使用方法: 在启动应用前导入此模块", "yellow")
    print_colored("例如: python -c 'import fix_flask_login' && python app.py", "yellow")
    
    return True

if __name__ == "__main__":
    if apply_werkzeug_patch():
        create_fix_flask_login_script()
        print_colored("\n补丁应用完成。现在可以尝试运行应用了: python app.py", "green")
    else:
        print_colored("\n补丁应用失败，请尝试降级werkzeug版本: pip install werkzeug==2.3.7", "red") 