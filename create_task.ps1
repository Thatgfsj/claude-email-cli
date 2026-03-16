# Create scheduled task: clean logs daily at 3am

$scriptPath = Join-Path $PSScriptRoot "clean_logs.py"
$taskName = "EmailAI-LogCleaner"

# Check if task exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Task '$taskName' exists, removing..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create trigger: daily at 3am
$trigger = New-ScheduledTaskTrigger -Daily -At 3am

# Create action: run Python script
$action = New-ScheduledTaskAction -Execute "python" -Argument "`"$scriptPath`""

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Register task
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Description "Clean Email AI robot log files"

Write-Host "Scheduled task created: $taskName"
Write-Host "Run time: Daily at 3:00 AM"
Write-Host "Script path: $scriptPath"
