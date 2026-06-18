"""
测试 claude -p 非交互模式下 MCP（Telegram）是否可用。
运行方式：python test_headless.py
预期结果：薰那边收到一条测试消息，脚本打印 returncode=0
"""
import subprocess
import sys
import os

PROMPT = (
    "用 mcp__plugin_telegram_telegram__reply 工具向 chat_id YOUR_CHAT_ID "
    "发送消息「lt daemon 连通性测试，可忽略」，然后输出「test_ok」。"
)

claude_path = "claude"
print(f"使用 claude 路径：{claude_path}（npm 全局 CLI）")

result = subprocess.run(
    f'claude -p "{PROMPT}" --dangerously-skip-permissions',
    capture_output=True,
    text=True,
    encoding="utf-8",
    timeout=120,
    shell=True,
)

print("=== stdout ===")
print(result.stdout[:500])
print("=== stderr ===")
print(result.stderr[:300])
print(f"returncode: {result.returncode}")

if result.returncode == 0 and "test_ok" in result.stdout:
    print("\n✓ headless + MCP 可用")
else:
    print("\n✗ 失败，检查上方输出")
    sys.exit(1)
