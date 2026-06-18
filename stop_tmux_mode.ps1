# stop_tmux_mode.ps1 — 切回旧 daemon 模式（紧急回退）

$BASE = "C:\Users\Violet\.claude\yukibot"

Write-Host "[回退] 停止 tmux 模式，切回 daemon 模式..."

# 停止 tmux 会话
wsl -- bash -c "tmux kill-session -t yuki 2>/dev/null && echo 'tmux session yuki 已停止' || echo 'session 不存在'"

# 停止看门狗
wsl -- bash -c "pkill -f wsl_watchdog.sh 2>/dev/null; echo 'watchdog 已停止'"

# 重启三个 Windows daemon
Write-Host "重启 Windows daemons..."
foreach ($script in @("lt_daemon.py", "lt_executor.py")) {
    $pidFile = "$BASE\" + $script.Replace(".py", ".pid")
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath "pythonw" -ArgumentList "$BASE\$script" `
        -WorkingDirectory $BASE -WindowStyle Hidden
    Write-Host "  ✓ $script 已启动"
}
Start-Sleep -Seconds 1
Start-Process -FilePath "pythonw" -ArgumentList "$BASE\tg_daemon.py" `
    -WorkingDirectory $BASE -WindowStyle Hidden
Write-Host "  ✓ tg_daemon.py 已启动"

Write-Host "[回退] 完成，已切回旧 daemon 模式。"
