# 数据库修复指南

## 问题描述

系统启动时出现了两个错误：

1. 数据库错误：`sqlite3.OperationalError: no such column: task_setting.mt_account_id`
   - 这表明数据库中的 `task_setting` 表缺少 `mt_account_id` 字段，但代码中正在尝试使用它

2. 包依赖错误：`ModuleNotFoundError: No module named 'Crypto'`
   - 这表明缺少必要的 Python 加密库

## 解决方案

### 步骤1：安装正确的依赖包

运行以下命令更新所需的包：

```bash
pip install -r requirements.txt
```

或者直接安装缺少的包：

```bash
pip install pycryptodome==3.19.0
```

### 步骤2：修复数据库结构

执行以下命令运行提供的数据库更新脚本：

```bash
python update_database.py
```

这个脚本会为 `task_setting` 表添加缺少的 `mt_account_id` 字段。

### 步骤3：重启应用

完成上述步骤后，重新启动应用：

```bash
python app.py
```

## 注意事项

1. 如果你有重要数据，请在执行任何操作前备份你的数据库文件（`instance/site.db`）

2. 如果数据库修复脚本执行时出现其他错误，可能需要检查数据库中的其他关系或字段是否也有不匹配的问题

3. 如果仍然出现问题，可以尝试完全重建数据库（但这将删除所有数据）：
   - 删除 `instance/site.db` 文件
   - 重新启动应用，让它创建新的数据库结构 