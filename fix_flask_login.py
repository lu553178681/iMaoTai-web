#!/usr/bin/env python
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
