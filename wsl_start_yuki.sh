#!/bin/bash
# wsl_start_yuki.sh — 启动/重启 tmux yuki 会话
# 用法：bash wsl_start_yuki.sh [--restart]

set -e
source ~/.nvm/nvm.sh

SESSION="yuki"
WORKDIR="/mnt/c/Users/Violet/.claude/yukibot"
STARTUP_PROMPT="$WORKDIR/wsl_startup_prompt.txt"
LOGFILE="/tmp/yuki_tmux.log"

echo "[$(date '+%H:%M:%S')] wsl_start_yuki.sh 启动" | tee -a "$LOGFILE"

# 清理旧会话
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[$(date '+%H:%M:%S')] 终止旧会话 '$SESSION'" | tee -a "$LOGFILE"
  tmux kill-session -t "$SESSION"
  sleep 2
fi

# 启动新的 detached tmux 会话
echo "[$(date '+%H:%M:%S')] 启动 tmux 会话 '$SESSION'" | tee -a "$LOGFILE"
tmux new-session -d -s "$SESSION" \
  -c "$WORKDIR" \
  "source ~/.nvm/nvm.sh && claude --dangerously-skip-permissions 2>&1 | tee -a $LOGFILE"

# 等待 claude 启动
echo "[$(date '+%H:%M:%S')] 等待 claude 就绪..." | tee -a "$LOGFILE"
sleep 6

# 发送启动 prompt
if [ -f "$STARTUP_PROMPT" ]; then
  PROMPT_TEXT="读取文件 $STARTUP_PROMPT 并严格按照其中所有步骤执行。"
  tmux send-keys -t "$SESSION" "$PROMPT_TEXT" Enter
  echo "[$(date '+%H:%M:%S')] 启动 prompt 已注入" | tee -a "$LOGFILE"
else
  echo "[$(date '+%H:%M:%S')] 警告：wsl_startup_prompt.txt 不存在" | tee -a "$LOGFILE"
fi

echo "[$(date '+%H:%M:%S')] 会话已启动：" | tee -a "$LOGFILE"
tmux list-sessions | tee -a "$LOGFILE"
