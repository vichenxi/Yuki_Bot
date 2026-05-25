"""
claude_monitor.py — Claude Code 自动调用守护进程

职责：监控 pending_reply.json 和 pending_tick.json，
      到时自动调用 claude -p 处理，无需人工触发 Claude Code 会话。

用法：
  python claude_monitor.py          # 前台运行
  pythonw claude_monitor.py         # 后台运行（无窗口，Windows）

停止：Ctrl+C 或结束进程
日志：C:/Users/Violet/.claude/yukibot/monitor.log
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# pythonw 下 stdout/stderr 为 None，重定向到 devnull
import io
if sys.stdout is None or getattr(sys.stdout, "encoding", "utf-8").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8")
if sys.stderr is None or getattr(sys.stderr, "encoding", "utf-8").lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8")

# ── 路径配置 ────────────────────────────────────────────────
BASE     = Path(__file__).resolve().parent.parent
DATA     = BASE / "data"
LOG_FILE = BASE / "monitor.log"
PID_FILE = BASE / "monitor.pid"

PENDING_REPLY = DATA / "pending_reply.json"
PENDING_TICK  = DATA / "pending_tick.json"

# claude CLI：优先从 PATH 查找，再试常见安装位置
_CLAUDE_CANDIDATES = [
    "claude",
    r"C:\Users\Violet\AppData\Roaming\npm\claude.cmd",
    r"C:\Users\Public\AppData\Roaming\npm\claude.cmd",
]
CLAUDE_CMD = next(
    (c for c in _CLAUDE_CANDIDATES
     if c == "claude" or Path(c).exists()),
    "claude"
)

CST = timezone(timedelta(hours=8))
POLL_INTERVAL = 20   # 秒：轮询间隔
CLAUDE_TIMEOUT = 600  # 秒：单次 claude 调用的超时限制（10分钟）
FAIL_SLEEP = 60       # 秒：claude 调用失败后的冷却等待

_BASH_CANDIDATES = [
    os.environ.get("CLAUDE_BASH_PATH", ""),
    r"D:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\bin\bash.exe",
    "bash",
]
GIT_BASH = next((b for b in _BASH_CANDIDATES if b and (b == "bash" or Path(b).exists())), "bash")

# ── 调用 claude 时传入的 prompt ─────────────────────────────
REPLY_PROMPT = (
    f"检查文件 {DATA / 'pending_reply.json'} 是否存在。"
    f"如果存在：读取文件 {BASE / 'prompts' / 'reply_prompt.txt'} "
    "并严格按照其中所有步骤执行，完成后删除 pending_reply.json。"
    "如果不存在：不做任何事，静默退出。"
)

TICK_PROMPT = (
    f"检查文件 {DATA / 'pending_tick.json'} 是否存在。"
    f"如果存在：读取文件 {BASE / 'prompts' / 'lifetick_prompt.txt'} "
    "并严格按照其中所有步骤执行一次 Life Tick，执行完成后删除 pending_tick.json。"
    "如果不存在：不做任何事，静默退出。"
)

# ── 单实例锁 ─────────────────────────────────────────────────
def acquire_lock() -> bool:
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            result = subprocess.run(
                f'tasklist /FI "PID eq {old_pid}" /NH',
                capture_output=True, shell=True
            )
            if str(old_pid).encode() in result.stdout:
                return False  # 进程仍在运行
        except Exception:
            pass
    PID_FILE.write_text(str(os.getpid()))
    return True

def release_lock():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass

# ── 日志 ─────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── claude 调用 ────────────────────────────────────────────────
def run_claude(prompt: str, label: str) -> bool:
    """调用 claude -p 并等待完成。返回 True 表示成功（exit 0）。"""
    log(f"→ 启动 claude: {label}")
    env = os.environ.copy()
    env["CLAUDE_CODE_GIT_BASH_PATH"] = GIT_BASH
    # 确保 node/npm 在 PATH 中（pythonw 启动时可能缺失）
    extra_paths = [p for p in [
        r"D:\Program Files\nodejs",
        r"C:\Program Files\nodejs",
        str(Path.home() / "AppData" / "Roaming" / "npm"),
    ] if Path(p).exists()]
    existing_path = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(extra_paths) + (os.pathsep + existing_path if existing_path else "")
    try:
        result = subprocess.run(
            [
                CLAUDE_CMD,
                "-p",
                "--dangerously-skip-permissions",
                "--add-dir", str(BASE),
                "--add-dir", str(DATA),
            ],
            input=prompt,
            timeout=CLAUDE_TIMEOUT,
            cwd=str(BASE),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            log(f"✓ claude 完成: {label}")
            return True
        else:
            stderr_snippet = (result.stderr or "").strip()[:300]
            log(f"✗ claude 退出码 {result.returncode}: {label} | stderr: {stderr_snippet}")
            return False
    except subprocess.TimeoutExpired:
        log(f"✗ claude 超时 ({CLAUDE_TIMEOUT}s): {label}")
        return False
    except FileNotFoundError:
        log(f"✗ 找不到 claude: {CLAUDE_CMD} — 检查路径是否正确")
        return False
    except Exception as e:
        log(f"✗ claude 调用异常: {label}: {e}")
        return False

# ── 主循环 ────────────────────────────────────────────────────
def main():
    if not acquire_lock():
        print(f"[claude_monitor] 已有实例在运行（见 {PID_FILE}），本次退出。")
        sys.exit(0)

    log("=== claude_monitor 启动 ===")
    log(f"PID: {os.getpid()}")
    log(f"轮询间隔: {POLL_INTERVAL}s  claude 超时: {CLAUDE_TIMEOUT}s")

    try:
        while True:
            try:
                if PENDING_REPLY.exists():
                    ok = run_claude(REPLY_PROMPT, "pending_reply")
                    # 失败时冷却，避免 tight loop
                    time.sleep(2 if ok else FAIL_SLEEP)
                    continue

                if PENDING_TICK.exists():
                    ok = run_claude(TICK_PROMPT, "pending_tick")
                    time.sleep(2 if ok else FAIL_SLEEP)
                    continue

                # 无待处理文件，等待下次轮询
                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                log(f"主循环异常: {e}")
                time.sleep(10)

    except KeyboardInterrupt:
        log("=== claude_monitor 已停止（KeyboardInterrupt）===")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
