@echo off
echo 启动茅台预约调度器
echo ===================

REM 获取脚本所在目录的绝对路径
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python
set SCHEDULER_SCRIPT=%SCRIPT_DIR%standalone_scheduler.py

echo 正在后台启动调度器...
start "茅台预约调度器" /min %PYTHON_PATH% %SCHEDULER_SCRIPT%

echo.
echo 调度器已在后台启动！
echo 日志将保存在 %SCRIPT_DIR%logs\scheduler.log
echo.

REM 等待5秒
timeout /t 5

echo 您可以关闭此窗口，调度器将继续在后台运行。 