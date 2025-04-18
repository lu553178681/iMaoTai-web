# i茅台预约工具——Web界面版

<p align="center">
  <a href="https://hits.seeyoufarm.com">
     <img src="https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Flu553178681%2FiMaoTai-web&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false"/>
  </a>
  <a href="https://github.com/lu553178681/iMaoTai-web">
    <img src="https://img.shields.io/github/stars/lu553178681/iMaoTai-web" alt="GitHub Stars">
  </a>
  <a href="https://github.com/lu553178681/iMaoTai-web">
    <img src="https://img.shields.io/github/forks/lu553178681/iMaoTai-web" alt="GitHub Forks">
  </a>
  <a href="https://github.com/lu553178681/iMaoTai-web/issues">
    <img src="https://img.shields.io/github/issues-closed-raw/lu553178681/iMaoTai-web" alt="GitHub Closed Issues">
  </a>
  <a href="https://github.com/lu553178681/iMaoTai-web">
    <img alt="GitHub commit activity (branch)" src="https://img.shields.io/github/commit-activity/y/lu553178681/iMaoTai-web">
  </a>
  <a href="https://github.com/lu553178681/iMaoTai-web">
    <img src="https://img.shields.io/github/last-commit/lu553178681/iMaoTai-web" alt="GitHub Last Commit">
  </a>
</p>


### 功能：
- [x] 网页界面操作
- [x] 多账号管理
- [x] 自动调度任务
- [x] 多商品同时预约
- [x] 手机号加密保存
- [x] 自动获取app版本
- [x] 多种消息推送方式
- [x] 自动领取耐力和小茅运

### 原理：
```shell
1、登录获取验证码
2、输入验证码获取TOKEN
3、获取当日SESSION ID
4、根据地理位置信息预约附近门店的i茅台商品
5、自动获取最新的商品列表
6、自动执行预约任务
```


### 使用方法：

### 1、安装依赖
```shell
pip3 install --no-cache-dir -r requirements.txt
```

### 2、修改config.py或.env文件
按照你的需求修改相关配置，这里很重要，建议每个配置项都详细阅读。

### 3、启动Web服务
```shell
python3 app.py
```
启动后，访问`http://localhost:5000`即可使用Web界面进行所有操作。

### 4、Web界面功能
- **账号管理**：添加、编辑、删除i茅台账号
- **预约任务**：创建、编辑、禁用预约任务
- **预约记录**：查看历史预约记录和结果
- **消息推送**：配置多种推送方式
- **系统配置**：Web界面修改系统配置

### 5、配置消息推送
支持以下几种消息推送方式：
- PushPlus
- ServerChan
- 钉钉机器人

### 6、自动调度系统
系统内置了自动调度器，会在后台自动执行预约任务，无需额外配置。

## Web界面预览
![Web界面预览](resources/imgs/web_preview.jpg)

## 多商品选择功能
现在系统支持同时预约多个商品，您可以在Web界面上选择多个商品进行预约：

1. **创建自动预约任务**:
   - 在创建自动预约任务时，您可以选择多个商品
   - 系统会为所选商品创建预约任务

2. **账号关联**:
   - 每个预约任务都可以关联特定的i茅台账号
   - 可以为不同账号创建不同的预约任务

## 更新内容

### 多商品选择功能

现在系统支持同时预约多个商品，您可以在以下位置配置和选择多个商品：

1. **配置文件设置 (`config.py`)**:
   - `ITEM_CONFIG` 字典中可以设置每个商品是否启用
   - 通过将商品的 `enabled` 值设为 `True` 或 `False` 控制

2. **创建预约时**:
   - 在创建预约页面，您可以勾选多个商品同时提交预约

3. **自动预约任务**:
   - 在创建自动预约任务时，您可以选择多个商品
   - 系统会为每个选择的商品创建独立的预约任务

此更新极大提高了预约成功率，让您可以同时预约多款茅台产品。




