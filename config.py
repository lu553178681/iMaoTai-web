#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 推送配置
PUSH_TOKEN = os.getenv('PUSHPLUS_KEY', '')  # 推送token，从PUSHPLUS_KEY环境变量获取
# server酱 微信推送。使用参考 https://sct.ftqq.com/
SCKEY = os.environ.get('SCKEY')
# 钉钉WebHook，作为PushPlus的备用。使用参考：https://open.dingtalk.com/document/robots/custom-robot-access
DINGTALK_WEBHOOK = os.environ.get('DINGTALK_WEBHOOK')

# API配置
MAP_WEB_KEY = os.getenv('MAP_WEB_KEY', '8325164e247e15eea68b59e89200988b')  # 地图web服务key

# 文件保存路径
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH', None)  # 可以自定义凭证保存位置，默认为None

# 加密密钥
AES_KEY = os.getenv('AES_KEY', 'i_am_the_key_of_maotai')  # AES加密密钥

# HTTP代理配置
# 格式: 'http://user:pass@host:port' 或 'http://host:port'
# 如果API请求失败，系统会尝试使用此代理进行重试
HTTP_PROXY = os.getenv('HTTP_PROXY', '') 

# 茅台API配置（模拟）
MT_API_BASE = 'https://app.i-maotai.com'
MT_API_VERSION = 'v1'

# 用户代理
USER_AGENT = 'iOS/i-maotai/2.1.9'

# 日志级别
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

'''
*********** 商品配置 ***********
'''
ITEM_MAP = {
    '11318': '53%vol 500ml贵州茅台酒（乙巳蛇年）',
    '2478': '53%vol 500ml贵州茅台酒（珍品）',
    '11317': '53%vol 500ml贵州茅台酒（笙乐飞天）',
    '10941': '53%vol 500ml贵州茅台酒（笃厚飞天）',
    '11319': '53%vol 375ml×2贵州茅台酒（乙巳蛇年）',
    '11240': '53%vol 500ml茅台1935·中国国家地理文创酒（喜迎大运河）',
    '2488': '53%vol 500ml贵州茅台酒（飞天）',
    '10942': '43%vol 500ml贵州茅台酒（飞天）',
    '10056': '53%vol 500ml贵州茅台酒（黑金）'
}

# 需要预约的商品默认配置 - 每项商品可以单独设置是否启用
ITEM_CONFIG = {
    '11318': {'name': '53%vol 500ml贵州茅台酒（乙巳蛇年）', 'enabled': True},
    '2478': {'name': '53%vol 500ml贵州茅台酒（珍品）', 'enabled': False},
    '11317': {'name': '53%vol 500ml贵州茅台酒（笙乐飞天）', 'enabled': False},
    '10941': {'name': '53%vol 500ml贵州茅台酒（笃厚飞天）', 'enabled': True},
    '11319': {'name': '53%vol 375ml×2贵州茅台酒（乙巳蛇年）', 'enabled': True},
    '11240': {'name': '53%vol 500ml茅台1935·中国国家地理文创酒（喜迎大运河）', 'enabled': False},
    '2488': {'name': '53%vol 500ml贵州茅台酒（飞天）', 'enabled': True},
    '10942': {'name': '43%vol 500ml贵州茅台酒（飞天）', 'enabled': False},
    '10056': {'name': '53%vol 500ml贵州茅台酒（黑金）', 'enabled': False}
}

# 保留原有的ITEM_CODES配置，确保兼容性
ITEM_CODES = ['11318', '11319', '10941']   # 默认预约产品

'''
*********** 消息推送配置 ***********
push plus 微信推送,具体使用参考  https://www.pushplus.plus
如没有配置则不推送消息
为了安全,这里使用的环境配置.git里面请自行百度如何添加secrets.pycharm也可以自主添加.如果你实在不会,就直接用明文吧（O.o）
'''


'''
*********** 地图配置 ***********
获取地点信息,这里用的高德api,需要自己去高德开发者平台申请自己的key
'''
AMAP_KEY = os.environ.get("GAODE_KEY")


'''
*********** 个人账户认证配置 ***********
个人用户 credentials 路径
不配置,使用默认路径,在项目目录中;如果需要配置,你自己应该也会配置路径
例如： CREDENTIALS_PATH = './myConfig/credentials'
'''


'''
*********** 个人加解密密钥 ***********
为了解决credentials中手机号和token都暴露的问题,采用AES私钥加密,保障账号安全.
这里采用ECB,没有采用CBC.如果是固定iv,那加一层也没多大意义;如果是不固定iv,那每次添加账号判重的时候都认为不一样,除非你每次再把配置全部反解密,去校验去重,得不偿失.
key用了SHA-256转化,所以这里可以配置任意字符串,不用遵守AES算法要求密钥长度必须是16、24或32字节
如果不会配置环境变量(建议学习)、不care安全性、非开源运行,你可以在这里明文指定,eg:PRIVATE_AES_KEY = '666666'
ps:本来是写了判断是否配置密钥，可以自由选择明文保存的方式。但是还是为了安全性，限制了必须使用AES加密。哪怕是明文密钥。
'''
PRIVATE_AES_KEY = os.environ.get("PRIVATE_AES_KEY")


'''
*********** 预约规则配置 ************
因为目前支持代提的还是少,所以建议默认预约最近的门店
'''
_RULES = {
    'MIN_DISTANCE': 0,   # 预约你的位置最近的门店
    'MAX_SALES': 1,      # 预约本市出货量最大的门店
}
RESERVE_RULE = 0         # 在这里配置你的规则，只能选择其中一个
