import datetime
import logging
import sys
import json
import re

import config
import login
import process
import privateCrypt
import send_message

DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
TODAY = datetime.date.today().strftime("%Y%m%d")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s  %(filename)s : %(levelname)s  %(message)s',  # 定义输出log的格式
                    stream=sys.stdout,
                    datefmt=DATE_FORMAT)

print(r'''
**************************************
    欢迎使用i茅台自动预约工具
**************************************
''')

process.get_current_session_id()

# 校验配置文件是否存在
configs = login.config
if len(configs.sections()) == 0:
    logging.error("配置文件未找到配置")
    sys.exit(1)

aes_key = privateCrypt.get_aes_key()

s_title = '【成功】茅台预约成功'
s_content = ""
# 使用Markdown格式组织消息内容
md_content = """
## 茅台预约结果通知

### 预约时间
{}

### 预约结果
""".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

success_count = 0
fail_count = 0
error_details = []  # 用于存储详细错误信息

for section in configs.sections():
    if TODAY > configs.get(section, 'enddate'):
        continue
    mobile = privateCrypt.decrypt_aes_ecb(section, aes_key)
    province = configs.get(section, 'province')
    city = configs.get(section, 'city')
    token = configs.get(section, 'token')
    userId = privateCrypt.decrypt_aes_ecb(configs.get(section, 'userid'), aes_key)
    lat = configs.get(section, 'lat')
    lng = configs.get(section, 'lng')

    # 添加用户信息到Markdown内容
    md_content += f"\n#### 用户 `{mobile[-4:].rjust(len(mobile), '*')}`\n"
    md_content += f"- 位置：{province} {city}\n"
    
    p_c_map, source_data = process.get_map(lat=lat, lng=lng)

    process.UserId = userId
    process.TOKEN = token
    process.init_headers(user_id=userId, token=token, lng=lng, lat=lat)
    
    # 从配置中获取启用的商品ID列表
    enabled_items = []
    # 优先使用ITEM_CONFIG中配置的启用项
    if hasattr(config, 'ITEM_CONFIG'):
        for item_id, item_config in config.ITEM_CONFIG.items():
            if item_config.get('enabled', False):
                enabled_items.append(item_id)
    
    # 如果没有从ITEM_CONFIG中获取到商品，则使用ITEM_CODES作为后备
    if not enabled_items and hasattr(config, 'ITEM_CODES'):
        enabled_items = config.ITEM_CODES
    
    logging.info(f"准备预约以下商品: {enabled_items}")
    
    # 根据配置中，要预约的商品ID，城市 进行自动预约
    try:
        user_success = True  # 跟踪此用户是否所有预约都成功
        
        for item in enabled_items:
            max_shop_id = process.get_location_count(province=province,
                                                   city=city,
                                                   item_code=item,
                                                   p_c_map=p_c_map,
                                                   source_data=source_data,
                                                   lat=lat,
                                                   lng=lng)
            # print(f'max shop id : {max_shop_id}')
            if max_shop_id == '0':
                md_content += f"- 商品`{config.ITEM_MAP.get(item, f'未知商品({item})')}`: ❌ **未找到可预约门店**\n"
                user_success = False
                continue
                
            shop_info = source_data.get(str(max_shop_id))
            title = config.ITEM_MAP.get(item, f"未知商品({item})")
            shopInfo = f'商品:{title};门店:{shop_info["name"]}'
            logging.info(shopInfo)
            
            reservation_params = process.act_params(max_shop_id, item)
            # 核心预约步骤
            r_success, r_content = process.reservation(reservation_params, mobile)
            
            if r_success:
                success_count += 1
                md_content += f"- 商品`{title}`: ✅ **预约成功**\n  - 门店: {shop_info['name']}\n"
            else:
                fail_count += 1
                user_success = False
                # 提取错误原因，并格式化显示
                error_reason = "未知错误"
                
                # 首先判断是否包含明确的友好提示信息
                if ":" in r_content and "用户" in r_content:
                    # 新格式：用户 13812345678: 申购已结束，请明天再来
                    parts = r_content.split(":", 1)
                    if len(parts) > 1:
                        error_reason = parts[1].strip()
                # 如果没有找到明确的提示，则尝试根据内容分析
                elif "认证错误" in r_content or "Token失效" in r_content:
                    error_reason = "认证错误(Token失效)"
                elif "设备ID不一致" in r_content:
                    error_reason = "设备ID不一致"
                elif "ianus-token-auth" in r_content:
                    error_reason = "茅台认证机制更新"
                elif "商品已约满" in r_content or "已无库存" in r_content:
                    error_reason = "商品已约满或无库存"
                elif "已有同一商品的预约单" in r_content:
                    error_reason = "已有相同商品的预约"
                elif "申购已结束" in r_content or "请明天再来" in r_content:
                    error_reason = "申购已结束，请明天再来"
                elif "网络连接和API可用性" in r_content:
                    # 从日志中获取详细原因
                    try:
                        last_error_lines = []
                        with open("logs/app.log", "r", encoding="utf-8") as f:
                            log_lines = f.readlines()
                            for line in reversed(log_lines):
                                if "详细错误: 代码=" in line:
                                    error_parts = line.split("详细错误: 代码=")
                                    if len(error_parts) > 1:
                                        error_info = error_parts[1].strip()
                                        error_reason = f"API错误: {error_info}"
                                        break
                    except:
                        # 如果获取日志失败，使用通用错误信息
                        error_reason = "API请求失败，请检查网络"
                else:
                    # 尝试从文本中获取更多信息
                    if ":" in r_content:
                        # 简单拆分，获取冒号后面的内容
                        parts = r_content.split(":", 1)
                        if len(parts) > 1 and len(parts[1].strip()) > 0:
                            error_reason = parts[1].strip()
                    
                    # 如果还是未知错误，但包含API错误码，则提取错误码
                    if error_reason == "未知错误" and "API错误码=" in r_content:
                        match = re.search(r"API错误码=(\d+)", r_content)
                        if match:
                            error_code = match.group(1)
                            error_reason = f"API错误码: {error_code}"
                
                # 将错误详情添加到Markdown内容
                md_content += f"- 商品`{title}`: ❌ **预约失败**\n  - 门店: {shop_info['name']}\n  - 原因: {error_reason}\n"
                
                # 记录完整错误信息供调试
                error_details.append({
                    'mobile': mobile[-4:].rjust(len(mobile), '*'),
                    'item': title,
                    'shop': shop_info['name'],
                    'error': r_content
                })
            
            # 拼接普通文本内容（向后兼容）
            s_content = s_content + r_content + shopInfo + "\n"
            
            # 领取小茅运和耐力值
            process.getUserEnergyAward(mobile)
            
        # 更新用户预约结果汇总
        if not user_success:
            s_title = '【失败】茅台预约'
            
    except Exception as e:
        error_msg = str(e)
        logging.error(error_msg)
        md_content += f"- ❌ **预约异常**: {error_msg}\n"
        s_title = '【失败】茅台预约'
        fail_count += 1
        
        # 记录异常信息
        error_details.append({
            'mobile': mobile[-4:].rjust(len(mobile), '*'),
            'error': error_msg
        })

# 添加汇总信息
md_content += f"""
### 汇总统计
- 成功: {success_count} 个商品
- 失败: {fail_count} 个商品
- 总计: {success_count + fail_count} 个商品
"""

# 如果有错误，添加错误详情部分
if error_details:
    md_content += "\n### 错误详情\n"
    for i, error in enumerate(error_details, 1):
        md_content += f"**错误 {i}**:\n"
        md_content += f"- 用户: {error.get('mobile', 'Unknown')}\n"
        if 'item' in error:
            md_content += f"- 商品: {error.get('item', 'Unknown')}\n"
        if 'shop' in error:
            md_content += f"- 门店: {error.get('shop', 'Unknown')}\n"
        
        # 提取和格式化错误信息
        error_text = error.get('error', 'Unknown')
        # 检查是否包含特定错误标识
        if "申购已结束" in error_text or "请明天再来" in error_text:
            md_content += f"- 错误信息: **<font color='red'>申购已结束，请明天再来</font>**\n\n"
        elif "商品已约满" in error_text or "已无库存" in error_text:
            md_content += f"- 错误信息: **<font color='orange'>商品已约满或无库存</font>**\n\n"
        elif "认证错误" in error_text or "设备ID不一致" in error_text or "Token" in error_text:
            md_content += f"- 错误信息: **<font color='red'>认证错误，请重新登录获取Token</font>**\n\n"
        else:
            md_content += f"- 错误信息: ```{error_text}```\n\n"

# 修改标题逻辑，使其更准确反映状态
if success_count > 0 and fail_count > 0:
    s_title = '【部分成功/失败】茅台预约'
elif success_count > 0:
    s_title = '【成功】茅台预约成功'
elif fail_count > 0:
    s_title = '【失败】茅台预约'
else:
    s_title = '【通知】茅台预约结果'

# 推送消息
process.send_msg(s_title, md_content, 'markdown')
send_message.send_server_chan(config.SCKEY, s_title, md_content)
send_message.send_pushplus(config.PUSH_TOKEN, s_title, md_content)
