import requests
import json
import time
import random
import logging
from datetime import datetime, timedelta, timezone
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CommodityFetcher:
    def __init__(self):
        self.session_id = None
        self.base_url = "https://static.moutai519.com.cn/mt-backend/xhr/front/mall/index/session/get/"
        self.device_id = "BB419336-6575-4539-B9A6-52E0FF6A6119"
        self.mt_version = "1.4.8"  # 与C#代码中的常量保持一致

    def get_current_milliseconds(self):
        """
        计算时间戳，与C#代码逻辑完全一致
        """
        # 获取当前日期的零点时间
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # 设置东八区时间
        epoch_start = datetime(1970, 1, 1, tzinfo=timezone(timedelta(hours=8)))
        # 减去8小时，与原代码保持一致
        midnight_minus_8h = midnight - timedelta(hours=8)
        # 计算时间差（毫秒）
        time_span = (midnight_minus_8h.timestamp() - epoch_start.timestamp()) * 1000
        return int(time_span)

    def get_headers(self):
        """
        构建请求头
        """
        return {
            "User-Agent": "iOS;16.5;Apple;iPhone XS Max",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "MT-Lat": "30.272769",
            "MT-K": str(int(time.time() * 1000)),
            "MT-Lng": "120.231099",
            "MT-User-Tag": "0",
            "MT-Network-Type": "WIFI",
            "MT-Info": "028e7f96f6369cafe1d105579c5b9377",
            "MT-Device-ID": self.device_id,
            "MT-Bundle-ID": "com.moutai.mall",
            "Accept-Language": "en-CN;q=1, zh-Hans-CN;q=0.9",
            "MT-Request-ID": str(int(time.time() * 1000)),
            "MT-APP-Version": self.mt_version,
            "MT-R": "clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw==",
            "Accept-Encoding": "gzip, deflate, br"
        }

    def fetch_commodities(self, max_retries=3, retry_delay=2):
        """
        获取可用商品列表，带有重试机制
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试间隔时间（秒）
            
        Returns:
            商品列表，失败时返回空列表
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # 计算时间戳
                milliseconds = self.get_current_milliseconds()
                url = f"{self.base_url}{milliseconds}"
                logging.info(f"请求URL: {url}")
                
                # 获取请求头
                headers = self.get_headers()
                logging.debug(f"请求头: {json.dumps(headers, ensure_ascii=False)}")
                
                # 发送请求，增加超时时间增加可靠性
                response = requests.get(
                    url, 
                    headers=headers, 
                    verify=False, 
                    timeout=15
                )
                logging.info(f"响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logging.debug(f"响应数据: {json.dumps(data, ensure_ascii=False)}")
                    
                    if data.get("code") == 2000:
                        data_obj = data.get("data", {})
                        self.session_id = data_obj.get("sessionId")
                        # 获取商品列表
                        item_list = data_obj.get("itemList", [])
                        
                        # 将商品信息转换为ProductEntity格式
                        products = []
                        for item in item_list:
                            product = {
                                "Code": item.get("itemCode", ""),
                                "Title": item.get("title", ""),
                                "Description": item.get("content", ""),
                                "Price": item.get("price", ""),
                                "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            products.append(product)
                        
                        logging.info(f"成功获取商品列表，共 {len(products)} 个商品")
                        return products
                    else:
                        error_msg = f"获取商品列表失败: {data.get('message', '未知错误')}"
                        logging.warning(error_msg)
                        last_error = error_msg
                else:
                    error_msg = f"HTTP请求失败: {response.status_code}, 响应内容: {response.text}"
                    logging.warning(error_msg)
                    last_error = error_msg
            except requests.exceptions.Timeout:
                error_msg = "请求超时，将重试"
                logging.warning(f"{error_msg} (尝试 {retry_count+1}/{max_retries})")
                last_error = error_msg
            except requests.exceptions.ConnectionError as e:
                error_msg = f"连接错误: {str(e)}"
                logging.warning(f"{error_msg} (尝试 {retry_count+1}/{max_retries})")
                last_error = error_msg
            except requests.exceptions.RequestException as e:
                error_msg = f"网络请求异常: {str(e)}"
                logging.warning(f"{error_msg} (尝试 {retry_count+1}/{max_retries})")
                last_error = error_msg
            except Exception as e:
                error_msg = f"发生错误: {str(e)}"
                logging.warning(f"{error_msg} (尝试 {retry_count+1}/{max_retries})")
                import traceback
                logging.debug(traceback.format_exc())
                last_error = error_msg
            
            # 增加重试延迟，并增加随机性避免同时重试
            retry_delay_with_jitter = retry_delay + random.uniform(0, 1)
            time.sleep(retry_delay_with_jitter)
            retry_count += 1
        
        logging.error(f"获取商品列表失败，已重试{max_retries}次: {last_error}")
        return []

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 测试获取商品列表
    logging.info("开始测试商品获取功能")
    fetcher = CommodityFetcher()
    products = fetcher.fetch_commodities()
    
    if products:
        logging.info(f"成功获取商品列表，共 {len(products)} 个商品:")
        for i, product in enumerate(products, 1):
            logging.info(f"{i}. {product['Title']} - 编码: {product['Code']} - 价格: {product['Price']}")
    else:
        logging.error("获取商品列表失败")
        
    logging.info("测试完成")