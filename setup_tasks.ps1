# 茅台预约Windows计划任务创建脚本
Write-Host "创建茅台预约Windows计划任务" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green

# 获取脚本所在目录的绝对路径
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = "python"
$executorScript = Join-Path $scriptDir "simple_task_executor.py"

# 手动设置任务时间，可以根据需要修改
$taskTimes = @("09:00", "16:04", "16:09")

Write-Host "将为以下时间创建计划任务: $($taskTimes -join ', ')" -ForegroundColor Cyan

# 为每个任务时间创建计划任务
foreach ($time in $taskTimes) {
    Write-Host "正在创建每日 $time 的计划任务..." -ForegroundColor Yellow
    $taskName = "茅台预约$time"
    $command = "$pythonPath `"$executorScript`""
    
    # 创建计划任务
    $action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$executorScript`""
    $trigger = New-ScheduledTaskTrigger -Daily -At $time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
    
    # 注册任务(如果存在则覆盖)
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
}

Write-Host "`n计划任务创建完成！" -ForegroundColor Green
Write-Host "您可以在Windows任务计划程序中查看和修改这些任务。" -ForegroundColor Green
Write-Host "每个任务将在指定时间执行所有启用的预约。" -ForegroundColor Green

Write-Host "`n按任意键继续..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 