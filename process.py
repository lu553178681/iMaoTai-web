#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import json
import math
import os
import random
import re
import time
import config
from encrypt import Encrypt
import requests
import hashlib
import logging
import privateCrypt
from urllib.parse import quote
import copy
import uuid

AES_KEY = 'qbhajinldepmucsonaaaccgypwuvcjaa'
AES_IV = '2018534749963515'
SALT = '2af72f100c356273d46284f6fd1dfc08'

CURRENT_TIME = str(int(time.time() * 1000))
headers = {}

'''
# 获取茅台APP的版本号，暂时没找到接口，采用爬虫曲线救国
# 用bs获取指定的class更稳定，之前的正则可能需要经常改动
def get_mt_version():
    # apple商店 i茅台 url
    apple_imaotai_url = "https://apps.apple.com/cn/app/i%E8%8C%85%E5%8F%B0/id1600482450"
    response = requests.get(apple_imaotai_url)
    # 用网页自带的编码反解码，防止中文乱码
    response.encoding = response.apparent_encoding
    html_text = response.text
    soup = BeautifulSoup(html_text, "html.parser")
    elements = soup.find_all(class_="whats-new__latest__version")
    # 获取p标签内的文本内容
    version_text = elements[0].text
    # 这里先把没有直接替换"版本 "，因为后面不知道空格会不会在，所以先替换文字，再去掉前后空格
    latest_mt_version = version_text.replace("版本", "").strip()
    return latest_mt_version


mt_version = get_mt_version()
'''
# 通过ios应用商店的api获取最新版本
mt_version = json.loads(requests.get('https://itunes.apple.com/cn/lookup?id=1600482450').text)['results'][0]['version']


header_context = f'''
MT-Lat: 28.499562
MT-K: 1675213490331
MT-Lng: 102.182324
Host: app.moutai519.com.cn
MT-User-Tag: 0
Accept: */*
MT-Network-Type: WIFI
MT-Token: 1
MT-Team-ID: 
MT-Info: 028e7f96f6369cafe1d105579c5b9377
MT-Device-ID: 2F2075D0-B66C-4287-A903-DBFF6358342A
MT-Bundle-ID: com.moutai.mall
Accept-Language: en-CN;q=1, zh-Hans-CN;q=0.9
MT-Request-ID: 167560018873318465
MT-APP-Version: 1.3.7
User-Agent: iOS;16.3;Apple;?unrecognized?
MT-R: clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw==
Content-Length: 93
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
Content-Type: application/json
userId: 2
'''


# 初始化请求头
def init_headers(user_id: str = '1', token: str = '2', lat: str = '29.83826', lng: str = '119.74375'):
    print(f"[{datetime.datetime.now()}] 初始化API请求头...")
    
    # 清空旧的headers
    headers.clear()
    
    # 从header_context加载基本设置
    for k in header_context.strip().split("\n"):
        if not k.strip():
            continue
            
        temp_l = k.split(': ')
        if len(temp_l) < 2:
            print(f"[{datetime.datetime.now()}] ⚠️ 警告: 跳过无效的header行: {k}")
            continue
            
        header_name = temp_l[0].strip()
        header_value = temp_l[1].strip()
        dict.update(headers, {header_name: header_value})
    
    # 添加关键认证和位置信息
    if user_id:
        dict.update(headers, {"userId": user_id})
        print(f"[{datetime.datetime.now()}] 设置 userId: {user_id}")
    else:
        print(f"[{datetime.datetime.now()}] ⚠️ 警告: user_id为空")
    
    # 提取设备ID变量，默认使用时间戳生成的ID
    device_id = f'MT-{int(time.time() * 1000)}-{random.randint(1000, 9999)}'
    
    # 从令牌中提取设备ID (如果token有效)
    jwt_device_id = None
    if token and token != '2' and len(token.split('.')) == 3:
        try:
            # 尝试解析JWT令牌
            import base64
            
            token_parts = token.split('.')
            payload = token_parts[1]
            payload += '=' * (4 - len(payload) % 4) if len(payload) % 4 else ''
            
            try:
                # 尝试解码
                decoded_payload = base64.b64decode(payload).decode('utf-8')
                token_data = json.loads(decoded_payload)
                
                # 检查是否包含设备ID
                if 'deviceId' in token_data:
                    jwt_device_id = token_data['deviceId']
                    device_id = jwt_device_id
                    print(f"[{datetime.datetime.now()}] ✅ 从JWT令牌中提取到设备ID: {device_id}")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] ⚠️ JWT令牌解析失败: {str(e)}")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] ⚠️ 处理令牌时出错: {str(e)}")
        
        # 设置令牌
        dict.update(headers, {"MT-Token": token})
        print(f"[{datetime.datetime.now()}] 设置 MT-Token: {token[:4]}...{token[-4:] if len(token) > 8 else token}")
    else:
        print(f"[{datetime.datetime.now()}] ⚠️ 警告: token无效或为默认值: {token}")
        
    # 更新位置信息
    dict.update(headers, {"MT-Lat": lat})
    dict.update(headers, {"MT-Lng": lng})
    dict.update(headers, {"mt-lat": lat})  # 确保mt-lat也设置了（小写）
    dict.update(headers, {"mt-lng": lng})  # 确保mt-lng也设置了（小写）
    
    # 更新版本信息
    dict.update(headers, {"MT-APP-Version": mt_version})
    
    # 生成一致的请求ID和设备ID
    timestamp = int(time.time() * 1000)
    request_id = f'{timestamp}{random.randint(111111, 999999)}'
    
    # 茅台新版API认证所需参数
    dict.update(headers, {"MT-Request-ID": request_id})
    dict.update(headers, {"MT-Device-ID": device_id})
    
    # 添加其他必要的头信息
    dict.update(headers, {"Accept": "application/json, text/plain, */*"})
    dict.update(headers, {"Accept-Language": "zh-CN,zh-Hans;q=0.9,en;q=0.8"})
    dict.update(headers, {"Accept-Encoding": "gzip, deflate, br"})
    dict.update(headers, {"Connection": "keep-alive"})
    dict.update(headers, {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"})
    dict.update(headers, {"Content-Type": "application/json"})
    
    # 新版茅台API需要的ianus认证参数基础设置
    nonce = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
    dict.update(headers, {"MT-Timestamp": str(timestamp)})
    dict.update(headers, {"MT-Nonce": nonce})
    
    # 打印关键认证信息
    print(f"[{datetime.datetime.now()}] ✅ Headers初始化完成，关键字段: userId={headers.get('userId')}, MT-Token长度={len(headers.get('MT-Token', ''))}, 位置=[{lat},{lng}], 设备ID={device_id}")
    return headers


def signature(data: dict):
    keys = sorted(data.keys())
    temp_v = ''
    for item in keys:
        temp_v += data[item]
    text = SALT + temp_v + CURRENT_TIME
    hl = hashlib.md5()
    hl.update(text.encode(encoding='utf8'))
    md5 = hl.hexdigest()
    return md5


# 获取登录手机验证码
def get_vcode(mobile: str):
    params = {'mobile': mobile}
    md5 = signature(params)
    dict.update(params, {'md5': md5, "timestamp": CURRENT_TIME, 'MT-APP-Version': mt_version})
    responses = requests.post("https://app.moutai519.com.cn/xhr/front/user/register/vcode", json=params,
                              headers=headers)
    if responses.status_code != 200:
        logging.info(
            f'get v_code : params : {params}, response code : {responses.status_code}, response body : {responses.text}')


# 执行登录操作
def login(mobile: str, v_code: str):
    params = {'mobile': mobile, 'vCode': v_code, 'ydToken': '', 'ydLogId': ''}
    md5 = signature(params)
    dict.update(params, {'md5': md5, "timestamp": CURRENT_TIME, 'MT-APP-Version': mt_version})
    responses = requests.post("https://app.moutai519.com.cn/xhr/front/user/register/login", json=params,
                              headers=headers)
    if responses.status_code != 200:
        logging.info(
            f'login : params : {params}, response code : {responses.status_code}, response body : {responses.text}')
    dict.update(headers, {'MT-Token': responses.json()['data']['token']})
    dict.update(headers, {'userId': responses.json()['data']['userId']})
    return responses.json()['data']['token'], responses.json()['data']['userId']


# 获取当日的session id
def get_current_session_id():
    try:
        print(f"[{datetime.datetime.now()}] 开始获取茅台商城会话ID...")
        day_time = int(time.mktime(datetime.date.today().timetuple())) * 1000
        my_url = f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/index/session/get/{day_time}"
        print(f"[{datetime.datetime.now()}] 请求URL: {my_url}")
        
        responses = requests.get(my_url, timeout=15)
        
        if responses.status_code != 200:
            error_msg = f"获取会话ID失败: HTTP状态码 {responses.status_code}, 响应: {responses.text}"
            print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
            logging.warning(error_msg)
            # 失败情况下，使用随机会话ID以便于调试
            fallback_session_id = str(random.randint(10000, 99999))
            dict.update(headers, {'current_session_id': fallback_session_id})
            print(f"[{datetime.datetime.now()}] ⚠️ 使用备用会话ID: {fallback_session_id}")
            return False
        
        try:
            response_data = responses.json()
            if response_data.get('code') == 2000:  # 成功的API状态码
                current_session_id = str(response_data['data']['sessionId'])
                dict.update(headers, {'current_session_id': current_session_id})
                print(f"[{datetime.datetime.now()}] ✅ 成功获取会话ID: {current_session_id}")
                return True
            else:
                error_msg = f"获取会话ID失败: API错误 {response_data.get('code')}, 信息: {response_data.get('message', '未知错误')}"
                print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
                logging.warning(error_msg)
                
                # 失败情况下，使用随机会话ID以便于调试
                fallback_session_id = str(random.randint(10000, 99999))
                dict.update(headers, {'current_session_id': fallback_session_id})
                print(f"[{datetime.datetime.now()}] ⚠️ 使用备用会话ID: {fallback_session_id}")
                return False
        except Exception as json_err:
            error_msg = f"解析会话ID响应失败: {str(json_err)}, 响应内容: {responses.text}"
            print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
            logging.warning(error_msg)
            
            # 失败情况下，使用随机会话ID以便于调试
            fallback_session_id = str(random.randint(10000, 99999))
            dict.update(headers, {'current_session_id': fallback_session_id})
            print(f"[{datetime.datetime.now()}] ⚠️ 使用备用会话ID: {fallback_session_id}")
            return False
    except Exception as e:
        error_msg = f"获取会话ID过程异常: {str(e)}"
        print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
        logging.error(error_msg)
        
        # 失败情况下，使用随机会话ID以便于调试
        fallback_session_id = str(random.randint(10000, 99999))
        dict.update(headers, {'current_session_id': fallback_session_id})
        print(f"[{datetime.datetime.now()}] ⚠️ 使用备用会话ID: {fallback_session_id}")
        return False


# 获取最近或者出货量最大的店铺
def get_location_count(province: str,
                       city: str,
                       item_code: str,
                       p_c_map: dict,
                       source_data: dict,
                       lat: str = '29.83826',
                       lng: str = '102.182324',
                       max_retries: int = 3):
    """
    获取店铺信息，带有重试机制
    """
    print(f"[{datetime.datetime.now()}] 开始获取店铺信息: 省份={province}, 城市={city}, 商品={item_code}")
    
    day_time = int(time.mktime(datetime.date.today().timetuple())) * 1000
    session_id = headers.get('current_session_id')
    
    if not session_id:
        print(f"[{datetime.datetime.now()}] ⚠️ 警告: 会话ID缺失")
        return '0'
    
    # 构建请求URL
    url = f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/shop/list/slim/v3/{session_id}/{quote(province)}/{item_code}/{day_time}"
    print(f"[{datetime.datetime.now()}] 请求URL: {url}")
    
    # 为静态资源请求构建专用请求头
    static_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://h5.moutai519.com.cn/',
        'Origin': 'https://h5.moutai519.com.cn',
        'Host': 'static.moutai519.com.cn',
        'MT-Device-ID': headers.get('MT-Device-ID', ''),
        'MT-APP-Version': mt_version,
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'MT-Lat': lat,
        'MT-Lng': lng,
        'mt-lat': lat,
        'mt-lng': lng
    }
    
    # 使用专用请求头发送请求
    # 优先尝试不使用代理
    response = None
    try:
        print(f"[{datetime.datetime.now()}] 使用浏览器方式请求店铺数据...")
        response = requests.get(url, headers=static_headers, timeout=15)
        if response.status_code == 200:
            print(f"[{datetime.datetime.now()}] ✅ 浏览器方式请求成功")
        else:
            print(f"[{datetime.datetime.now()}] ⚠️ 浏览器方式请求返回状态码: {response.status_code}")
            response = None
    except Exception as e:
        print(f"[{datetime.datetime.now()}] ⚠️ 浏览器方式请求异常: {str(e)}")
        response = None
    
    # 如果浏览器方式失败，使用原始方式+重试机制
    if response is None:
        print(f"[{datetime.datetime.now()}] 尝试使用原始方式...")
        response = request_url_with_retry(
            url=url,
            headers=headers, 
            timeout=15,
            max_retries=max_retries
        )
    
    # 如果不使用代理失败，且配置了代理，则尝试使用代理
    if response is None and hasattr(config, 'HTTP_PROXY') and config.HTTP_PROXY:
        print(f"[{datetime.datetime.now()}] 不使用代理请求失败，尝试使用代理...")
        response = request_url_with_retry(
            url=url,
            headers=headers, 
            timeout=15,
            max_retries=max_retries,
            use_proxy=True
        )
    
    # 如果请求失败，返回0
    if response is None:
        print(f"[{datetime.datetime.now()}] ❌ 获取店铺列表最终失败")
        return '0'
    
    try:
        # 解析响应
        response_data = response.json()
        if response_data.get('code') != 2000:
            error_msg = f"获取店铺列表失败: API错误 {response_data.get('code')}, 信息: {response_data.get('message', '未知错误')}"
            print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
            logging.warning(error_msg)
            return '0'
        
        # 提取商店数据
        shops = response_data['data']['shops']
        shop_count = len(shops)
        print(f"[{datetime.datetime.now()}] ✅ 成功获取店铺列表: {shop_count}个店铺")
        
        if shop_count == 0:
            print(f"[{datetime.datetime.now()}] ⚠️ 店铺列表为空，无法选择店铺")
            return '0'
    
        # 根据配置规则选择店铺
        if config.RESERVE_RULE == 0:
            shop_id = distance_shop(city, item_code, p_c_map, province, shops, source_data, lat, lng)
            if shop_id != '0':
                print(f"[{datetime.datetime.now()}] ✅ 已选择最近的店铺: {shop_id}")
                return shop_id
                
        elif config.RESERVE_RULE == 1:
            shop_id = max_shop(city, item_code, p_c_map, province, shops)
            if shop_id != '0':
                print(f"[{datetime.datetime.now()}] ✅ 已选择库存最多的店铺: {shop_id}")
                return shop_id
                
        else:
            # 默认使用距离规则
            shop_id = distance_shop(city, item_code, p_c_map, province, shops, source_data, lat, lng)
            if shop_id != '0':
                print(f"[{datetime.datetime.now()}] ✅ 已选择最近的店铺: {shop_id}")
                return shop_id
                
        # 所有规则都没有找到合适的店铺
        print(f"[{datetime.datetime.now()}] ⚠️ 无法找到合适的店铺")
        return '0'
                
    except Exception as e:
        error_msg = f"解析店铺数据时出错: {str(e)}"
        print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
        logging.error(error_msg)
        return '0'


# 获取距离最近的店铺
def distance_shop(city,
                  item_code,
                  p_c_map,
                  province,
                  shops,
                  source_data,
                  lat: str = '28.499562',
                  lng: str = '102.182324'):
    # shop_ids = p_c_map[province][city]
    temp_list = []
    for shop in shops:
        shopId = shop['shopId']
        items = shop['items']
        item_ids = [i['itemId'] for i in items]
        # if shopId not in shop_ids:
        #     continue
        if str(item_code) not in item_ids:
            continue
        shop_info = source_data.get(shopId)
        # d = geodesic((lat, lng), (shop_info['lat'], shop_info['lng'])).km
        d = math.sqrt((float(lat) - shop_info['lat']) ** 2 + (float(lng) - shop_info['lng']) ** 2)
        # print(f"距离：{d}")
        temp_list.append((d, shopId))

    # sorted(a,key=lambda x:x[0])
    temp_list = sorted(temp_list, key=lambda x: x[0])
    # logging.info(f"所有门店距离:{temp_list}")
    if len(temp_list) > 0:
        return temp_list[0][1]
    else:
        return '0'


# 获取出货量最大的店铺
def max_shop(city, item_code, p_c_map, province, shops):
    max_count = 0
    max_shop_id = '0'
    shop_ids = p_c_map[province][city]
    for shop in shops:
        shopId = shop['shopId']
        items = shop['items']

        if shopId not in shop_ids:
            continue
        for item in items:
            if item['itemId'] != str(item_code):
                continue
            if item['inventory'] > max_count:
                max_count = item['inventory']
                max_shop_id = shopId
    logging.debug(f'item code {item_code}, max shop id : {max_shop_id}, max count : {max_count}')
    return max_shop_id


encrypt = Encrypt(key=AES_KEY, iv=AES_IV)


def act_params(shop_id: str, item_id: str):
    """
    构建预约参数，包括加密参数
    
    Args:
        shop_id: 店铺ID
        item_id: 商品ID
        
    Returns:
        构建好的预约参数字典
    """
    print(f"[{datetime.datetime.now()}] 开始构建预约参数: 店铺ID={shop_id}, 商品ID={item_id}")
    
    try:
        # 检查必要的参数
        if not shop_id or shop_id == '0':
            print(f"[{datetime.datetime.now()}] ⚠️ 警告: 店铺ID无效: {shop_id}")
            
        if 'current_session_id' not in headers or not headers['current_session_id']:
            print(f"[{datetime.datetime.now()}] ⚠️ 警告: 会话ID缺失，将使用随机ID")
            # 生成一个随机会话ID以便继续
            session_id = str(random.randint(100, 999))
        else:
            session_id = headers['current_session_id']
            
        if 'userId' not in headers or not headers['userId']:
            print(f"[{datetime.datetime.now()}] ⚠️ 警告: 用户ID缺失")
            userId = "0"
        else:
            userId = headers['userId']
        
        # 构建预约参数
        params = {
            "itemInfoList": [{"count": 1, "itemId": item_id}],
              "sessionId": int(session_id),
              "userId": userId,
              "shopId": shop_id
              }
        
        # 加密参数
        s = json.dumps(params)
        try:
            act = encrypt.aes_encrypt(s)
            print(f"[{datetime.datetime.now()}] 成功加密参数: 源长度={len(s)}字符, 加密后长度={len(act)}字符")
        except Exception as encrypt_err:
            print(f"[{datetime.datetime.now()}] ❌ 加密参数失败: {str(encrypt_err)}")
            # 生成一个假的加密参数，用于调试，实际不会成功
            act = "MOCK_ENCRYPTED_DATA_" + str(int(time.time()))
            
        # 添加加密参数到请求
        params.update({"actParam": act})
        
        print(f"[{datetime.datetime.now()}] ✅ 预约参数构建完成")
        return params
    except Exception as e:
        error_msg = f"构建预约参数失败: {str(e)}"
        print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
        logging.error(error_msg)
        
        # 返回一个基本的参数以便继续调试
        return {
            "itemInfoList": [{"count": 1, "itemId": item_id}],
            "sessionId": 999,
            "shopId": shop_id,
            "userId": "0",
            "actParam": "MOCK_ENCRYPTED_DATA_ERROR"
        }


# 消息推送
def send_msg(title, content, template='markdown'):
    """
    使用pushplus推送消息
    
    Args:
        title: 消息标题
        content: 消息内容
        template: 消息模板，默认为markdown
    """
    if config.PUSH_TOKEN is None:
        print(f"[{datetime.datetime.now()}] ⚠️ 未配置PUSH_TOKEN，无法发送通知")
        return False
    
    print(f"[{datetime.datetime.now()}] 开始推送通知: {title}")
    url = 'http://www.pushplus.plus/send'
    
    # 构建请求参数
    params = {
        'token': config.PUSH_TOKEN,
        'title': title,
        'content': content,
        'template': template  # 支持markdown格式
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            resp_json = r.json()
            if resp_json.get('code') == 200:
                print(f"[{datetime.datetime.now()}] ✅ 通知推送成功: {title}")
                logging.info(f'通知推送成功：{r.status_code}, {r.text}')
                return True
            else:
                print(f"[{datetime.datetime.now()}] ❌ 通知推送API错误: {resp_json.get('msg', '未知错误')}")
                logging.warning(f'通知推送API错误：{r.status_code}, {r.text}')
                return False
        else:
            print(f"[{datetime.datetime.now()}] ❌ 通知推送HTTP错误: {r.status_code}")
            logging.warning(f'通知推送HTTP错误：{r.status_code}, {r.text}')
            return False
    except Exception as e:
        print(f"[{datetime.datetime.now()}] ❌ 通知推送异常: {str(e)}")
        logging.error(f'通知推送异常：{str(e)}')
        return False


# 核心代码，执行预约
def reservation(params, mobile=''):
    """
    预约商品
    """
    # 深拷贝防止修改原始数据
    request_params = copy.deepcopy(params)
    
    # userId在header中，从params中移除
    if 'userId' in request_params:
        request_params.pop('userId')
    
    # 构建请求头
    headers = get_headers()
    
    # 检查device_id
    if 'deviceId' not in request_params:
        device_id = generate_device_id()
        request_params['deviceId'] = device_id
    
    print(f"[{datetime.datetime.now()}] 🔄 正在预约商品...")
    
    try:
        # 发送预约请求
        response = request_url_with_retry(
            url="https://app.moutai519.com.cn/xhr/front/mall/reservation/add",
            method="POST",
            headers=headers,
            json_data=request_params,
            max_retries=3,
            use_proxy=True
        )
        
        # 检查请求是否成功
        if isinstance(response, dict) and response.get('error'):
            # 请求失败，返回错误信息
            error_api_code = response.get('api_code', 0)
            error_message = response.get('message', '未知错误')
            status_code = response.get('status_code', 0)
            
            # 格式化详细错误信息
            detail_error = f"HTTP状态码={status_code}, API错误码={error_api_code}, 错误信息={error_message}"
            print(f"[{datetime.datetime.now()}] ❌ 预约失败: {detail_error}")
            
            # 特定错误码的友好提示
            if error_api_code == 4021:
                friendly_message = "申购已结束，请明天再来"
            elif error_api_code == 4019:
                friendly_message = "您今日已申购，请明天再来"
            elif error_api_code == 4015:
                friendly_message = "申购商品已约满，请明天再来"
            elif error_api_code == 4011 and "设备ID不一致" in error_message:
                friendly_message = "设备ID不一致，请检查配置"
            elif error_api_code == 4011:
                friendly_message = "认证失败，请检查Token是否过期"
            else:
                friendly_message = error_message or "预约失败，请检查网络和配置"
                
            # 如果提供了手机号，添加到消息中
            if mobile:
                friendly_message = f"用户 {mobile}: {friendly_message}"
                
            return False, friendly_message
        
        # 成功获取响应，解析JSON
        try:
            resp_json = response.json() if hasattr(response, 'json') else response
            
            # 检查API返回码
            if resp_json.get('code') == 2000:
                # 茅台API成功码是2000
                print(f"[{datetime.datetime.now()}] ✅ 预约成功: {resp_json.get('data', {})}")
                
                success_msg = "预约成功"
                if mobile:
                    success_msg = f"用户 {mobile}: 预约成功"
                    
                return True, success_msg
            else:
                # API业务逻辑错误
                error_code = resp_json.get('code')
                error_msg = resp_json.get('message', '未知错误')
                
                print(f"[{datetime.datetime.now()}] ❌ 预约API返回错误: 代码={error_code}, 信息={error_msg}")
                
                # 特定错误码的友好提示
                if error_code == 4021:
                    friendly_message = "申购已结束，请明天再来"
                elif error_code == 4019:
                    friendly_message = "您今日已申购，请明天再来"
                elif error_code == 4015:
                    friendly_message = "申购商品已约满，请明天再来"
                else:
                    friendly_message = error_msg
                    
                # 如果提供了手机号，添加到消息中
                if mobile:
                    friendly_message = f"用户 {mobile}: {friendly_message}"
                    
                return False, friendly_message
        except json.JSONDecodeError as e:
            print(f"[{datetime.datetime.now()}] ❌ 解析预约响应失败: {str(e)}")
            
            error_msg = "预约请求响应格式错误"
            if mobile:
                error_msg = f"用户 {mobile}: {error_msg}"
                
            return False, error_msg
            
    except Exception as e:
        error_msg = f"预约过程异常: {str(e)}"
        print(f"[{datetime.datetime.now()}] ❌ {error_msg}")
        
        if mobile:
            error_msg = f"用户 {mobile}: {error_msg}"
            
        return False, error_msg


# 用高德api获取地图信息
def select_geo(i: str):
    # 校验高德api是否配置
    if config.AMAP_KEY is None:
        logging.error("!!!!请配置config.py中AMAP_KEY(高德地图的MapKey)")
        raise ValueError
    resp = requests.get(f"https://restapi.amap.com/v3/geocode/geo?key={config.AMAP_KEY}&output=json&address={i}")
    geocodes: list = resp.json()['geocodes']
    return geocodes


def get_map(lat: str, lng: str, max_retries: int = 3):
    """
    获取茅台店铺地图信息，支持重试和代理
    
    Args:
        lat: 纬度
        lng: 经度
        max_retries: 最大重试次数
        
    Returns:
        (p_c_map, source_data): 省市地图及店铺数据
    """
    print(f"[{datetime.datetime.now()}] 开始获取地图信息: 经度={lng}, 纬度={lat}")
    
    p_c_map = {}
    url = 'https://static.moutai519.com.cn/mt-backend/xhr/front/mall/resource/get'
    
    # 创建一个新的请求头字典，基于全局headers
    map_headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': headers.get('User-Agent', 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0_1 like Mac OS X)'),
        'Referer': 'https://h5.moutai519.com.cn/gux/game/main?appConfig=2_1_2',
        'Client-User-Agent': headers.get('Client-User-Agent', 'iOS;16.0.1;Apple;iPhone 14 ProMax'),
        'MT-R': headers.get('MT-R', 'clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw=='),
        'Origin': 'https://h5.moutai519.com.cn',
        'MT-APP-Version': mt_version,
        'MT-Request-ID': f'{int(time.time() * 1000)}{random.randint(1111111, 999999999)}{int(time.time() * 1000)}',
        'Accept-Language': 'zh-CN,zh-Hans;q=1',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'mt-lng': f'{lng}',
        'mt-lat': f'{lat}'
    }
    
    # 保持设备ID一致性 - 使用全局headers中的设备ID
    if 'MT-Device-ID' in headers:
        map_headers['MT-Device-ID'] = headers['MT-Device-ID']
        print(f"[{datetime.datetime.now()}] 使用一致的设备ID: {headers['MT-Device-ID']}")
    else:
        # 回退到随机设备ID
        device_id = f'{int(time.time() * 1000)}{random.randint(1111111, 999999999)}{int(time.time() * 1000)}'
        map_headers['MT-Device-ID'] = device_id
        print(f"[{datetime.datetime.now()}] ⚠️ 警告: 未找到全局设备ID，使用新生成的设备ID: {device_id}")
    
    # 如果存在MT-Token，也复制过来保持一致性
    if 'MT-Token' in headers:
        map_headers['MT-Token'] = headers['MT-Token']
    
    # 使用request_url_with_retry函数获取响应
    print(f"[{datetime.datetime.now()}] 发送获取地图信息请求: URL={url}")
    response = request_url_with_retry(
        url=url, 
        headers=map_headers, 
        timeout=15,
        max_retries=max_retries
    )
    
    # 如果不使用代理失败，且配置了代理，则尝试使用代理
    if response is None and hasattr(config, 'HTTP_PROXY') and config.HTTP_PROXY:
        print(f"[{datetime.datetime.now()}] 不使用代理请求失败，尝试使用代理...")
        response = request_url_with_retry(
            url=url,
            headers=map_headers, 
            timeout=15,
            max_retries=max_retries,
            use_proxy=True
        )
    
    if response is None:
        print(f"[{datetime.datetime.now()}] ❌ 获取地图信息最终失败")
        return {}, {}
    
    try:
        mtshops = response.json().get('data', {}).get('mtshops_pc', {})
        if not mtshops:
            print(f"[{datetime.datetime.now()}] ⚠️ 地图信息中未找到门店数据")
            return {}, {}
            
        urls = mtshops.get('url')
        if not urls:
            print(f"[{datetime.datetime.now()}] ⚠️ 未找到门店URL")
            return {}, {}
        
        # 获取门店详细信息
        print(f"[{datetime.datetime.now()}] 获取门店详细信息: URL={urls}")
        shop_response = request_url_with_retry(
            url=urls, 
            headers=map_headers, 
            timeout=15,
            max_retries=max_retries
        )
        
        # 如果不使用代理失败，且配置了代理，则尝试使用代理
        if shop_response is None and hasattr(config, 'HTTP_PROXY') and config.HTTP_PROXY:
            print(f"[{datetime.datetime.now()}] 不使用代理请求门店详情失败，尝试使用代理...")
            shop_response = request_url_with_retry(
                url=urls,
                headers=map_headers, 
                timeout=15,
                max_retries=max_retries,
                use_proxy=True
            )
        
        if shop_response is None:
            print(f"[{datetime.datetime.now()}] ❌ 获取门店详细信息最终失败")
            return {}, {}
            
        shop_data = shop_response.json()
        for k, v in dict(shop_data).items():
            provinceName = v.get('provinceName')
            cityName = v.get('cityName')
            if not p_c_map.get(provinceName):
                p_c_map[provinceName] = {}
            if not p_c_map[provinceName].get(cityName, None):
                p_c_map[provinceName][cityName] = [k]
            else:
                p_c_map[provinceName][cityName].append(k)

        print(f"[{datetime.datetime.now()}] ✅ 成功获取地图信息: {len(p_c_map)}个省份, {len(shop_data)}个门店")
        return p_c_map, dict(shop_data)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] ❌ 处理地图数据时出错: {str(e)}")
        raise  # 重新抛出异常，由调用方处理


# 领取耐力和小茅运
def getUserEnergyAward(mobile: str):
    """
    领取耐力
    """
    cookies = {
        'MT-Device-ID-Wap': headers['MT-Device-ID'],
        'MT-Token-Wap': headers['MT-Token'],
        'YX_SUPPORT_WEBP': '1',
    }
    response = requests.post('https://h5.moutai519.com.cn/game/isolationPage/getUserEnergyAward', cookies=cookies,
                             headers=headers, json={})
    # response.json().get('message') if '无法领取奖励' in response.text else "领取奖励成功"
    logging.info(
        f'领取耐力 : mobile:{mobile} :  response code : {response.status_code}, response body : {response.text}')


def set_default_value(input_value, default_content):
    """
    检查输入内容是否为空，如果为空则返回默认内容。

    :param input_value: 需要检查的内容
    :param default_content: 如果输入为空，返回的默认内容
    :return: 输入内容或默认内容
    """
    return default_content if input_value is None or input_value.strip() == "" else input_value

def get_product_list(timestamp=None, max_retries=3, retry_delay=2):
    """获取可预约商品列表
    
    Args:
        timestamp: 时间戳，默认为当天0点的时间戳
        max_retries: 最大重试次数
        retry_delay: 重试间隔秒数
        
    Returns:
        商品列表数据
    """
    # 使用CommodityFetcher类获取商品列表
    from commodity_fetcher import CommodityFetcher
    import logging
    import random
    import time
    
    # 添加重试机制
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # 创建CommodityFetcher实例并获取商品列表
            fetcher = CommodityFetcher()
            products = fetcher.fetch_commodities()
            
            if products:
                # 将商品列表转换为原接口格式
                items = []
                for product in products:
                    item = {
                        'itemId': product['Code'],
                        'itemCode': product['Code'],
                        'title': product['Title'],
                        'content': product['Description'],
                        'price': product['Price']
                    }
                    items.append(item)
                
                return {
                    'success': True,
                    'session_id': fetcher.session_id,
                    'items': items
                }
            else:
                return {
                    'success': False,
                    'message': '获取商品列表失败，返回了空列表'
                }
                
        except Exception as e:
            last_error = f"处理异常: {str(e)}"
            logging.warning(f"获取商品列表失败 (尝试 {retry_count+1}/{max_retries}): {last_error}")
        
        # 增加重试延迟，并增加随机性避免同时重试
        retry_delay_with_jitter = retry_delay + random.uniform(0, 1)
        time.sleep(retry_delay_with_jitter)
        retry_count += 1
    
    # 所有重试失败后，返回错误
    return {
        'success': False,
        'message': f'获取商品列表失败，已重试{max_retries}次: {last_error}'
    }

def get_shop_list(session_id, province, item_id, timestamp=None, max_retries=3, retry_delay=2):
    """获取指定省份下可预约指定商品的店铺列表
    
    Args:
        session_id: 会话ID
        province: 省份名称(需要URL编码)
        item_id: 商品ID
        timestamp: 时间戳，默认为当天0点的时间戳
        max_retries: 最大重试次数
        retry_delay: 重试间隔秒数
        
    Returns:
        店铺列表数据
    """
    # 获取标准请求头
    base_headers = get_headers()
    
    # 如果没有提供时间戳，则使用当天0点的时间戳
    if not timestamp:
        midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        timestamp = int(midnight.timestamp() * 1000)
    
    # URL编码省份名称
    encoded_province = requests.utils.quote(province)
    
    url = f"https://static.moutai519.com.cn/mt-backend/xhr/front/mall/shop/list/slim/v3/{session_id}/{encoded_province}/{item_id}/{timestamp}"
    
    # 构建专用的浏览器方式请求头
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://h5.moutai519.com.cn/',
        'Origin': 'https://h5.moutai519.com.cn',
        'Host': 'static.moutai519.com.cn',
        'MT-Device-ID': base_headers.get('MT-Device-ID', ''),
        'MT-APP-Version': mt_version,
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # 添加重试机制
    retry_count = 0
    last_error = None
    
    # 首先尝试浏览器方式请求
    try:
        print(f"[{datetime.datetime.now()}] 尝试以浏览器方式请求店铺列表...")
        response = requests.get(url, headers=browser_headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 2000:
                print(f"[{datetime.datetime.now()}] ✅ 浏览器方式请求成功")
                return {
                    'success': True,
                    'shops': data['data']['shops']
                }
            else:
                print(f"[{datetime.datetime.now()}] ⚠️ 浏览器方式请求返回非成功代码: {data.get('code')}")
        else:
            print(f"[{datetime.datetime.now()}] ⚠️ 浏览器方式请求返回HTTP状态码: {response.status_code}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] ⚠️ 浏览器方式请求异常: {str(e)}")
    
    # 浏览器方式失败，使用标准方式重试
    print(f"[{datetime.datetime.now()}] 切换到标准方式请求...")
    
    while retry_count < max_retries:
        try:
            # 判断是否使用代理
            proxies = None
            if hasattr(config, 'HTTP_PROXY') and config.HTTP_PROXY and retry_count >= max_retries // 2:
                proxies = {
                    "http": config.HTTP_PROXY,
                    "https": config.HTTP_PROXY
                }
                print(f"[{datetime.datetime.now()}] 尝试使用代理: {config.HTTP_PROXY}")
            
            # 使用更长的超时时间
            response = requests.get(url, headers=base_headers, timeout=15, proxies=proxies)
            
            # 检查HTTP状态码
            if response.status_code != 200:
                raise Exception(f"HTTP错误: {response.status_code}")
                
            data = response.json()
            if data.get('code') == 2000:
                print(f"[{datetime.datetime.now()}] ✅ 标准方式请求成功 (尝试 {retry_count+1})")
                return {
                    'success': True,
                    'shops': data['data']['shops']
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', '获取店铺列表失败')
                }
        except requests.exceptions.RequestException as e:
            last_error = f"网络请求异常: {str(e)}"
            logging.warning(f"获取店铺列表失败 (尝试 {retry_count+1}/{max_retries}): {last_error}")
        except Exception as e:
            last_error = f"处理异常: {str(e)}"
            logging.warning(f"获取店铺列表失败 (尝试 {retry_count+1}/{max_retries}): {last_error}")
        
        # 增加重试延迟，并增加随机性避免同时重试
        retry_delay_with_jitter = retry_delay + random.uniform(0, 1)
        print(f"[{datetime.datetime.now()}] 等待 {retry_delay_with_jitter:.2f} 秒后重试...")
        time.sleep(retry_delay_with_jitter)
        retry_count += 1
    
    # 所有重试失败后，返回错误
    print(f"[{datetime.datetime.now()}] ❌ 获取店铺列表最终失败")
    return {
        'success': False,
        'message': f'获取店铺列表失败，已重试{max_retries}次: {last_error}'
    }

def get_nearest_shop(shops, lat, lng):
    """获取最近的店铺
    
    Args:
        shops: 店铺列表
        lat: 纬度
        lng: 经度
        
    Returns:
        最近的店铺ID
    """
    nearest_shop = None
    min_distance = float('inf')
    
    user_point = (float(lat), float(lng))
    
    for shop in shops:
        shop_lat = shop.get('lat')
        shop_lng = shop.get('lng')
        
        if shop_lat and shop_lng:
            shop_point = (float(shop_lat), float(shop_lng))
            distance = calculate_distance(user_point, shop_point)
            
            if distance < min_distance:
                min_distance = distance
                nearest_shop = shop
    
    return nearest_shop.get('shopId') if nearest_shop else None

def calculate_distance(point1, point2):
    """计算两点之间的距离（基于Haversine公式）
    
    Args:
        point1: (纬度, 经度)
        point2: (纬度, 经度)
        
    Returns:
        两点之间的距离（米）
    """
    # 地球半径（米）
    EARTH_RADIUS = 6378137.0
    
    lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
    lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])
    
    dLat = lat2 - lat1
    dLon = lon2 - lon1
    
    a = math.sin(dLat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS * c

def get_headers():
    """获取标准请求头
    
    Returns:
        包含必要请求头的字典
    """
    # 使用全局请求头或者构建新的请求头
    if headers and len(headers) > 0:
        request_headers = headers.copy()
        
        # 确保包含必要的通用请求头
        if 'User-Agent' not in request_headers or 'iOS;16.3;Apple;?unrecognized?' in request_headers.get('User-Agent', ''):
            request_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
        
        if 'Accept' not in request_headers:
            request_headers['Accept'] = 'application/json, text/plain, */*'
            
        if 'Accept-Language' not in request_headers:
            request_headers['Accept-Language'] = 'zh-CN,zh-Hans;q=0.9,en;q=0.8'
            
        if 'Accept-Encoding' not in request_headers:
            request_headers['Accept-Encoding'] = 'gzip, deflate, br'
            
        if 'Connection' not in request_headers:
            request_headers['Connection'] = 'keep-alive'
            
        return request_headers
    
    # 如果没有全局请求头，构建一个更完整的浏览器风格请求头
    timestamp = int(time.time() * 1000)
    device_id = f'MT-{timestamp}-{random.randint(1000, 9999)}'
    request_id = f'{timestamp}{random.randint(111111, 999999999)}'
    
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        'MT-APP-Version': mt_version,
        'MT-Request-ID': request_id,
        'MT-Device-ID': device_id,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://h5.moutai519.com.cn/',
        'Origin': 'https://h5.moutai519.com.cn',
        'MT-K': str(timestamp - random.randint(10000, 50000)),
        'MT-User-Tag': '0',
        'MT-Network-Type': 'WIFI',
        'MT-Token': '1',
        'MT-Team-ID': '',
        'MT-Info': f'{hashlib.md5(str(timestamp).encode()).hexdigest()[:32]}'
    }
    
    return browser_headers

def request_url_with_retry(url, method="GET", params=None, data=None, json_data=None, headers=None, timeout=10, max_retries=3, use_proxy=False):
    """
    发送HTTP请求，支持重试机制

    Args:
        url: 请求URL
        method: 请求方法，GET或POST
        params: URL参数 (字典)
        data: 表单数据 (字典)
        json_data: JSON数据 (字典)
        headers: 请求头 (字典)
        timeout: 超时时间 (秒)
        max_retries: 最大重试次数
        use_proxy: 是否使用代理

    Returns:
        requests.Response对象，如果所有重试都失败则返回None
    """
    if max_retries < 1:
        max_retries = 1
    
    retry_count = 0
    last_error = None
    last_response = None
    proxy = None
    
    # 设置代理
    if use_proxy and hasattr(config, 'HTTP_PROXY') and config.HTTP_PROXY:
        proxy = {
            'http': config.HTTP_PROXY,
            'https': config.HTTP_PROXY
        }
        print(f"[{datetime.datetime.now()}] 使用代理: {proxy}")
    
    while retry_count < max_retries:
        try:
            # 记录当前重试次数
            retry_count += 1
            
            # 构建请求参数
            request_kwargs = {
                'timeout': timeout
            }
            
            if params:
                request_kwargs['params'] = params
            if data:
                request_kwargs['data'] = data
            if json_data:
                request_kwargs['json'] = json_data
            if headers:
                request_kwargs['headers'] = headers
            if proxy:
                request_kwargs['proxies'] = proxy
            
            # 发送请求
            if method.upper() == "GET":
                response = requests.get(url, **request_kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, **request_kwargs)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            # 记录响应
            last_response = response
            
            # 检查响应状态
            if response.status_code >= 400:
                # 尝试解析错误响应
                try:
                    error_data = response.json()
                    error_code = error_data.get('code', 0)
                    error_msg = error_data.get('message', '未知错误')
                    print(f"[{datetime.datetime.now()}] 第{retry_count}次请求失败: HTTP状态码={response.status_code}, API错误码={error_code}, 错误信息={error_msg}")
                    
                    # 关键错误码 - 不需要重试的固定错误
                    if error_code in [4021, 4019, 4015]:  # 申购已结束、商品已约满等
                        print(f"[{datetime.datetime.now()}] 检测到固定错误，无需重试: 代码={error_code}, 信息={error_msg}")
                        return {
                            'error': True,
                            'api_code': error_code,
                            'message': error_msg,
                            'status_code': response.status_code
                        }
                except:
                    print(f"[{datetime.datetime.now()}] 第{retry_count}次请求失败: HTTP状态码={response.status_code}, 响应={response.text[:100]}")
                
                # 401错误 - 认证失败，通常是令牌问题
                if response.status_code == 401:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', '')
                        print(f"[{datetime.datetime.now()}] 检测到认证错误 (401): {error_msg}")
                        # 设备ID不一致错误 - 重要的特定错误消息
                        if 'device id' in error_msg.lower() or 'inconsistency' in error_msg.lower():
                            return {
                                'error': True,
                                'api_code': 401,
                                'message': error_msg,
                                'status_code': 401
                            }
                    except:
                        pass
                
                # 茅台特定错误码 480
                if response.status_code == 480:
                    try:
                        error_data = response.json()
                        error_code = error_data.get('code', 0)
                        error_msg = error_data.get('message', '未知错误')
                        print(f"[{datetime.datetime.now()}] 检测到茅台特定错误 (480): 代码={error_code}, 信息={error_msg}")
                        
                        # 对特定错误直接返回，无需重试
                        return {
                            'error': True,
                            'api_code': error_code,
                            'message': error_msg,
                            'status_code': 480
                        }
                    except:
                        pass
                
                # 存储最后一个错误
                last_error = f"HTTP错误: {response.status_code}"
                
                # 如果是最后一次重试，直接返回响应（即使有错误）
                if retry_count >= max_retries:
                    print(f"[{datetime.datetime.now()}] 达到最大重试次数 ({max_retries})，返回最后一个响应")
                    return response
            else:
                # 检查API级别的错误
                try:
                    resp_json = response.json()
                    api_code = resp_json.get('code')
                    
                    # 如果不是成功状态码
                    if api_code != 2000 and api_code != 200:
                        error_msg = resp_json.get('message', '未知API错误')
                        print(f"[{datetime.datetime.now()}] API返回错误: 代码={api_code}, 信息={error_msg}")
                        
                        # 特定错误码处理 - 不需要重试的错误
                        if api_code in [4021, 4019, 4015]:  # 申购已结束、商品已约满等
                            print(f"[{datetime.datetime.now()}] 检测到固定API错误，无需重试: 代码={api_code}, 信息={error_msg}")
                            return {
                                'error': True,
                                'api_code': api_code,
                                'message': error_msg,
                                'status_code': response.status_code
                            }
                            
                        last_error = f"API错误: 代码={api_code}, 信息={error_msg}"
                        
                        # 继续重试，除非是最后一次
                        if retry_count >= max_retries:
                            print(f"[{datetime.datetime.now()}] 达到最大API重试次数，返回最后一个响应")
                            return response
                    else:
                        # 成功响应
                        return response
                except Exception as json_err:
                    # JSON解析错误，但HTTP状态码正常，仍然返回响应
                    print(f"[{datetime.datetime.now()}] 响应JSON解析错误，但HTTP状态码正常: {json_err}")
                    return response
            
            # 如果需要重试，等待一段时间
            if retry_count < max_retries:
                wait_time = min(2 ** retry_count, 10)  # 指数退避，最多等待10秒
                print(f"[{datetime.datetime.now()}] 等待{wait_time}秒后重试...")
                time.sleep(wait_time)
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            last_error = str(e)
            print(f"[{datetime.datetime.now()}] 第{retry_count}次请求异常: {last_error}")
            
            if retry_count < max_retries:
                wait_time = min(2 ** retry_count, 10)
                print(f"[{datetime.datetime.now()}] 等待{wait_time}秒后重试...")
                time.sleep(wait_time)
    
    # 所有重试都失败
    if last_response and last_response.status_code >= 400:
        try:
            error_data = last_response.json()
            return {
                'error': True,
                'api_code': error_data.get('code', 0),
                'message': error_data.get('message', '未知错误'),
                'status_code': last_response.status_code
            }
        except:
            pass
    
    # 返回具有详细错误信息的字典而不是None
    print(f"[{datetime.datetime.now()}] 所有重试均失败，最后错误: {last_error}")
    return {
        'error': True,
        'api_code': 0,
        'message': last_error or '未知网络错误',
        'status_code': last_response.status_code if last_response else 0
    }

def generate_device_id():
    """
    生成设备ID
    
    Returns:
        随机生成的设备ID字符串
    """
    # 尝试使用全局headers中的device_id
    if 'MT-Device-ID' in headers:
        return headers['MT-Device-ID']
    
    # 否则生成一个新的UUID格式的设备ID
    # 格式类似于: 2F2075D0-B66C-4287-A903-DBFF6358342A
    device_id = str(uuid.uuid4()).upper()
    print(f"[{datetime.datetime.now()}] 生成新的设备ID: {device_id}")
    
    return device_id