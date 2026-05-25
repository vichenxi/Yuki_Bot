# 雪的 Life Tick 启动恢复脚本
# 每次系统启动时自动运行，检测断联缺口并恢复

# 等待系统和网络就绪
Start-Sleep -Seconds 15

$BASE = Split-Path $PSScriptRoot -Parent
$logFile = "$BASE\startup.log"

function Write-Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# ── 1. 执行断联恢复（claude -p）────────────────────────────────
Write-Log "=== yukibot 启动恢复开始 ==="

$recoveryPrompt = Get-Content "$BASE\prompts\recovery_prompt.txt" -Raw -Encoding UTF8
Write-Log "调用 claude 执行断联恢复..."
claude -p --dangerously-skip-permissions $recoveryPrompt
Write-Log "claude 恢复完成"

# ── 2. 启动 lt_daemon（LT 计时器）───────────────────────────────
$ltPid = "$BASE\daemon.pid"
$ltRunning = $false
if (Test-Path $ltPid) {
    $pid_ = [int](Get-Content $ltPid -ErrorAction SilentlyContinue)
    if ($pid_ -and (Get-Process -Id $pid_ -ErrorAction SilentlyContinue)) {
        $ltRunning = $true
    }
}
if (-not $ltRunning) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "pythonw"
    $psi.Arguments = "`"$BASE\core\lt_daemon.py`""
    $psi.WorkingDirectory = $BASE
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Write-Log "lt_daemon 已启动"
} else {
    Write-Log "lt_daemon 已在运行（PID=$pid_）"
}

# ── 3. 启动 tg_daemon（Telegram 消息监听）────────────────────────
$tgPid = "$BASE\tg_daemon.pid"
$tgRunning = $false
if (Test-Path $tgPid) {
    $pid_ = [int](Get-Content $tgPid -ErrorAction SilentlyContinue)
    if ($pid_ -and (Get-Process -Id $pid_ -ErrorAction SilentlyContinue)) {
        $tgRunning = $true
    }
}
if (-not $tgRunning) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "pythonw"
    $psi.Arguments = "`"$BASE\core\tg_daemon.py`""
    $psi.WorkingDirectory = $BASE
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Write-Log "tg_daemon 已启动"
} else {
    Write-Log "tg_daemon 已在运行（PID=$pid_）"
}

# ── 4. 启动 claude_monitor（自动调用 claude 处理 pending 文件）───
$monPid = "$BASE\monitor.pid"
$monRunning = $false
if (Test-Path $monPid) {
    $pid_ = [int](Get-Content $monPid -ErrorAction SilentlyContinue)
    if ($pid_ -and (Get-Process -Id $pid_ -ErrorAction SilentlyContinue)) {
        $monRunning = $true
    }
}
if (-not $monRunning) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "pythonw"
    $psi.Arguments = "`"$BASE\core\claude_monitor.py`""
    $psi.WorkingDirectory = $BASE
    $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    [System.Diagnostics.Process]::Start($psi) | Out-Null
    Write-Log "claude_monitor 已启动"
} else {
    Write-Log "claude_monitor 已在运行（PID=$pid_）"
}

Write-Log "=== yukibot 启动恢复完成 ==="
