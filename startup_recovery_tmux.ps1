# startup_recovery_tmux.ps1 — 开机自启动（tmux 模式）
# 注册到 Windows 任务计划程序后在登录时自动执行
# 注册命令：
#   schtasks /create /tn "Yuki-tmux" /tr "powershell -WindowStyle Hidden -File C:\Users\Violet\.claude\yukibot\startup_recovery_tmux.ps1" /sc onlogon /f

Start-Sleep -Seconds 15  # 等系统完全启动

# 启动 lt_daemon
$BASE = "C:\Users\Violet\.claude\yukibot"
$pidFile = "$BASE\daemon.pid"
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
Start-Process -FilePath "pythonw" `
    -ArgumentList "$BASE\lt_daemon.py" `
    -WorkingDirectory $BASE -WindowStyle Hidden

Start-Sleep -Seconds 3

# 启动 WSL2 tmux 会话
wsl -- bash /mnt/c/Users/Violet/.claude/yukibot/wsl_start_yuki.sh

# 启动看门狗
wsl -- bash -c "nohup bash /mnt/c/Users/Violet/.claude/yukibot/wsl_watchdog.sh > /tmp/yuki_watchdog.log 2>&1 &"
