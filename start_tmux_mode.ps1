# start_tmux_mode.ps1 — 切换到 tmux 模式
# 停用 tg_daemon / lt_executor，启动 WSL2 tmux 会话

$BASE = "C:\Users\Violet\.claude\yukibot"

Write-Host "[tmux-mode] 启动中..."

# ── 1. 停用 tg_daemon ──────────────────────────────────────────
$tgPidFile = "$BASE\tg_daemon.pid"
if (Test-Path $tgPidFile) {
    $tgPid = [int](Get-Content $tgPidFile)
    $proc = Get-Process -Id $tgPid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $tgPid -Force
        Write-Host "  ✓ tg_daemon (PID $tgPid) 已停止"
    }
    Remove-Item $tgPidFile -Force
}

# ── 2. 停用 lt_executor ────────────────────────────────────────
$ltePidFile = "$BASE\lt_executor.pid"
if (Test-Path $ltePidFile) {
    $ltePid = [int](Get-Content $ltePidFile)
    $proc = Get-Process -Id $ltePid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $ltePid -Force
        Write-Host "  ✓ lt_executor (PID $ltePid) 已停止"
    }
    Remove-Item $ltePidFile -Force
}

# ── 3. lt_daemon 保持运行（继续写 pending_tick.json）──────────
$daemonPidFile = "$BASE\daemon.pid"
if (Test-Path $daemonPidFile) {
    $daemonPid = [int](Get-Content $daemonPidFile)
    $proc = Get-Process -Id $daemonPid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "  ✓ lt_daemon (PID $daemonPid) 运行中，保持"
    } else {
        Write-Host "  ! lt_daemon 未运行，重启..."
        Remove-Item $daemonPidFile -Force -ErrorAction SilentlyContinue
        Start-Process -FilePath "pythonw" `
            -ArgumentList "$BASE\lt_daemon.py" `
            -WorkingDirectory $BASE -WindowStyle Hidden
        Write-Host "  ✓ lt_daemon 已重启"
    }
}

# ── 4. 启动 WSL2 tmux 会话 ────────────────────────────────────
Write-Host "  启动 WSL2 tmux 会话..."
wsl -- bash /mnt/c/Users/Violet/.claude/yukibot/wsl_start_yuki.sh

# ── 5. 启动看门狗（后台）──────────────────────────────────────
Write-Host "  启动看门狗..."
wsl -- bash -c "nohup bash /mnt/c/Users/Violet/.claude/yukibot/wsl_watchdog.sh > /tmp/yuki_watchdog.log 2>&1 &"

Write-Host ""
Write-Host "[tmux-mode] 完成。tmux 会话 'yuki' 已在 WSL2 运行。"
Write-Host "  查看状态：wsl -- tmux list-sessions"
Write-Host "  附加查看：wsl -- tmux attach -t yuki"
Write-Host "  分离返回：Ctrl+B, D"
