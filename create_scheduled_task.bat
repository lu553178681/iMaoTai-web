@echo off
echo 创建茅台预约计划任务
echo =====================

REM 获取脚本所在目录的绝对路径
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python
set TASK_SCRIPT=%SCRIPT_DIR%force_execute_task.py

REM 创建每日执行的计划任务
echo 正在创建每日16:04的计划任务...
schtasks /create /tn "茅台预约16:04" /tr "%PYTHON_PATH% %TASK_SCRIPT% 16:04" /sc daily /st 16:04 /f

REM 添加其他时间点，如果需要
REM echo 正在创建每日16:00的计划任务...
REM schtasks /create /tn "茅台预约16:00" /tr "%PYTHON_PATH% %TASK_SCRIPT% 16:00" /sc daily /st 16:00 /f

echo.
echo 计划任务创建完成！
echo 您可以在任务计划程序中查看和修改这些任务。
echo.

pause 