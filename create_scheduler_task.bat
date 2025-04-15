@echo off
echo 创建茅台预约Windows计划任务
echo ==========================

REM 获取脚本所在目录的绝对路径
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python
set EXECUTOR_SCRIPT=%SCRIPT_DIR%simple_task_executor.py

REM 手动设置任务时间，可以根据需要修改
set TASK_TIMES=09:00,16:04,16:09

echo 将为以下时间创建计划任务: %TASK_TIMES%

REM 为每个任务时间创建计划任务
for %%t in (%TASK_TIMES%) do (
    echo 正在创建每日%%t的计划任务...
    schtasks /create /tn "茅台预约%%t" /tr "%PYTHON_PATH% %EXECUTOR_SCRIPT%" /sc daily /st %%t /f
)

echo.
echo 计划任务创建完成！
echo 您可以在Windows任务计划程序中查看和修改这些任务。
echo 每个任务将在指定时间执行所有启用的预约。
echo.

pause 