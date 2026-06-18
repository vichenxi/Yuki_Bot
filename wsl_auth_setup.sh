#!/bin/bash
# 完整配置 WSL2 里的 claude 认证和设置
source ~/.nvm/nvm.sh 2>/dev/null || true

WIN_CLAUDE="/mnt/c/Users/Violet/.claude"
mkdir -p ~/.claude/channels/telegram

# 核心认证和设置
ln -sf "$WIN_CLAUDE/.credentials.json"  ~/.claude/.credentials.json
ln -sf "$WIN_CLAUDE/settings.json"       ~/.claude/settings.json

# Telegram 插件配置
ln -sf "$WIN_CLAUDE/channels/telegram/access.json" ~/.claude/channels/telegram/access.json

echo "=== ~/.claude/ 软链状态 ==="
ls -la ~/.claude/
echo ""
ls -la ~/.claude/channels/telegram/ 2>/dev/null

echo ""
echo "claude: $(which claude)"
echo "version: $(claude --version 2>&1 | head -1)"
