#!/bin/bash
# wsl_watchdog.sh — 监控 tmux yuki 会话，崩溃后自动重启
source ~/.nvm/nvm.sh

SESSION="yuki"
LOGFILE="/tmp/yuki_watchdog.log"
CHECK_INTERVAL=60  # 秒

echo "[$(date '+%H:%M:%S')] watchdog 启动，监控 '$SESSION'" | tee -a "$LOGFILE"

while true; do
  if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] 会话 '$SESSION' 不存在，重启中..." | tee -a "$LOGFILE"
    bash /mnt/c/Users/Violet/.claude/yukibot/wsl_start_yuki.sh >> "$LOGFILE" 2>&1
    echo "[$(date '+%H:%M:%S')] 重启完成" | tee -a "$LOGFILE"
    sleep 30  # 重启后多等一会
  fi
  sleep "$CHECK_INTERVAL"
done
