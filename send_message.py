import logging
import time
import json

import requests


def send_server_chan(sckey, title, desp, text_type='markdown'):
    """
    server酱推送
    :param sckey: server酱推送的key
    :param title: 标题
    :param desp: 内容
    :param text_type: 内容类型，默认为markdown
    :return: 是否成功
    """
    if not sckey:
        logging.warning("server酱 KEY 没有配置,不推送消息")
        return False
        
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    data = {
        "title": title, 
        "desp": desp,
        "channel": "9",   # 使用默认通道
        "openid": ""      # 留空使用默认openid
    }
    
    logging.info(f"正在发送Server酱推送，title: {title}")
    
    try:
        response = requests.post(url, data=data, timeout=10)
        resp_json = response.json()
        
        if response.status_code == 200 and resp_json.get('code') == 0:
            logging.info('Server酱 Turbo版推送成功')
            return True
        else:
            error_message = resp_json.get('message', '未知错误')
            logging.warning(f'Server酱 Turbo版推送失败: {error_message}')
            return False
    except Exception as e:
        logging.error(f'Server酱推送异常: {str(e)}')
        return False


def send_pushplus(token, title, content, template='markdown'):
    """
    使用pushplus推送消息
    
    Args:
        token: pushplus令牌
        title: 消息标题
        content: 消息内容
        template: 消息模板，默认为markdown
    
    Returns:
        是否成功推送
    """
    if not token:
        logging.warning("pushplus TOKEN 没有配置或为空，不推送消息")
        return False
    
    url = 'https://www.pushplus.plus/send'
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": template  # 使用markdown格式支持富文本展示
    }
    
    logging.info(f"正在发送PushPlus推送，token: {token[:4]}****{token[-4:] if len(token) > 8 else ''}")
    
    # 尝试3次
    for attempt in range(3):
        try:
            # 增加超时时间，设置连接超时10秒和读取超时15秒
            response = requests.post(url, json=data, timeout=(10, 15))
            logging.info(f'PushPlus推送结果(尝试{attempt+1}): 状态码={response.status_code}, 响应={response.text}')
            
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get('code') == 200:
                    logging.info("PushPlus推送成功!")
                    return True
                else:
                    logging.warning(f"PushPlus推送返回错误: {resp_json.get('msg', '未知错误')}")
            
            # 如果不是最后一次尝试，等待2秒后重试
            if attempt < 2:
                time.sleep(2)
                
        except requests.exceptions.Timeout:
            logging.error(f"PushPlus推送超时 (尝试{attempt+1})")
            if attempt < 2:
                time.sleep(2)
        except requests.exceptions.ConnectionError as e:
            logging.error(f"PushPlus推送连接错误: {e} (尝试{attempt+1})")
            if attempt < 2:
                time.sleep(2)
        except Exception as e:
            logging.error(f"PushPlus推送失败: {type(e).__name__}: {e} (尝试{attempt+1})")
            if attempt < 2:
                time.sleep(2)
    
    # 提供备用方案
    logging.error("PushPlus推送最终失败，已尝试3次")
    logging.info("您可以尝试访问 https://www.pushplus.plus 查看token是否有效，或直接在浏览器访问: "
                f"https://www.pushplus.plus/send?token={token[:4]}****&title=test&content=test 进行测试")
    return False


def send_webhook(webhook_url, title, content):
    """
    通过WebHook发送消息（适用于钉钉、企业微信等）
    
    :param webhook_url: WebHook URL
    :param title: 消息标题
    :param content: 消息内容
    :return: 是否成功
    """
    if not webhook_url:
        logging.warning("WebHook URL 没有配置或为空，不推送消息")
        return False
    
    # 钉钉格式消息
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"### {title}\n\n{content}"
        }
    }
    
    try:
        response = requests.post(webhook_url, json=data, timeout=(5, 5))
        logging.info(f"WebHook推送结果: 状态码={response.status_code}, 响应={response.text}")
        
        if response.status_code == 200:
            resp_json = response.json()
            if resp_json.get('errcode') == 0:
                logging.info("WebHook推送成功")
                return True
            else:
                logging.warning(f"WebHook推送失败: {resp_json.get('errmsg', '未知错误')}")
        return False
    except Exception as e:
        logging.error(f"WebHook推送失败: {e}")
        return False
