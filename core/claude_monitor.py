"""
claude_monitor.py — Claude Code 自动调用守护进程

职责：监控 pending_reply.json 和 pending_tick.json，
      到时自动调用 claude -p 处理；同时在每日 00:01 触发归档、23:00 触发日记。

用法：
  python claude_monitor.py          # 前台运行
  pythonw claude_monitor.py         # 后台运行（无窗口，Windows）

停止：Ctrl+C 或结束进程
日志：<项目根目录>/monitor.log
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

PENDING_REPLY   = DATA / "pending_reply.json"
PENDING_TICK    = DATA / "pending_tick.json"

PROMPTS = BASE / "prompts"

# claude CLI：优先从 PATH 查找，再试常见安装位置
_CLAUDE_CANDIDATES = [
    "claude",
    str(Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd"),
    r"C:\Users\Public\AppData\Roaming\npm\claude.cmd",
]
CLAUDE_CMD = next(
    (c for c in _CLAUDE_CANDIDATES
     if c == "claude" or Path(c).exists()),
    "claude"
)

CST = timezone(timedelta(hours=8))
POLL_INTERVAL  = 20    # 秒：轮询间隔
CLAUDE_TIMEOUT = 600   # 秒：单次 claude 调用的超时限制（10分钟）
FAIL_SLEEP     = 60    # 秒：claude 调用失败后的冷却等待

LT_STATE_FILE      = DATA / "lt_state.json"
CONFIG_FILE        = BASE / "config.json"
HEALTH_CHECK_EVERY = 1800   # 秒：每 30 分钟检查一次健康状态
LT_STALE_THRESHOLD = 7200   # 秒：2 小时无更新视为异常

# 每日任务触发窗口（分钟，包含两端）
ARCHIVE_HOUR, ARCHIVE_MIN_START, ARCHIVE_MIN_END = 0,  1, 10   # 00:01–00:10
DIARY_HOUR,   DIARY_MIN_START,   DIARY_MIN_END   = 23, 0, 10   # 23:00–23:10

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
    f"如果存在：读取文件 {PROMPTS / 'reply_prompt.txt'} "
    "并严格按照其中所有步骤执行，完成后删除 pending_reply.json。"
    "如果不存在：不做任何事，静默退出。"
)

TICK_PROMPT = (
    f"检查文件 {DATA / 'pending_tick.json'} 是否存在。"
    f"如果存在：读取文件 {PROMPTS / 'lifetick_prompt.txt'} "
    "并严格按照其中所有步骤执行一次 Life Tick，执行完成后删除 pending_tick.json。"
    "如果不存在：不做任何事，静默退出。"
)

ARCHIVE_PROMPT = (
    f"读取文件 {PROMPTS / 'archive_prompt.txt'} 并严格按照其中所有步骤执行归档任务。"
    f"文件中出现的 YUKIBOT_ROOT_PLACEHOLDER 全部替换为 {BASE}。"
)

DIARY_PROMPT = (
    f"读取文件 {PROMPTS / 'diary_prompt.txt'} 并严格按照其中所有步骤执行。"
    f"文件中出现的 YUKIBOT_ROOT_PLACEHOLDER 全部替换为 {BASE}。"
    "今天的日期是北京时间当天日期（UTC+8）。"
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

# ── Telegram 通知 ─────────────────────────────────────────────
def _notify_owner(text: str):
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        token = cfg.get("bot_token", "")
        chat_id = str(cfg.get("owner_chat_id") or cfg.get("default_chat_id", ""))
        if not token or not chat_id:
            return
        import urllib.request
        body = json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, headers={"Content-Type": "application/json; charset=utf-8"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"[notify] 发送失败: {e}")

# ── LT 健康检查 ───────────────────────────────────────────────
_last_health_check = 0.0
_last_health_alert = 0.0

def check_lt_health():
    """每 30 分钟检查 lt_state.json，超过 2 小时无更新时发 Telegram 警报。"""
    global _last_health_check, _last_health_alert
    now_ts = time.time()
    if now_ts - _last_health_check < HEALTH_CHECK_EVERY:
        return
    _last_health_check = now_ts
    try:
        if not LT_STATE_FILE.exists():
            return
        state = json.loads(LT_STATE_FILE.read_text(encoding="utf-8"))
        last_success_str = state.get("last_success")
        if not last_success_str:
            return
        last_success = datetime.fromisoformat(last_success_str)
        now_cst = datetime.now(CST)
        gap = (now_cst - last_success).total_seconds()
        if gap > LT_STALE_THRESHOLD:
            if now_ts - _last_health_alert > 3600:
                _last_health_alert = now_ts
                hours = gap / 3600
                log(f"[health] ⚠️ LT 链 {hours:.1f} 小时未更新，发送警报")
                _notify_owner(
                    f"[雪系统] ⚠️ Life Tick 链已 {hours:.1f} 小时未更新（上次：{last_success_str[:16]}）。\n"
                    f"请检查 lt_daemon 和 claude_monitor 是否正常运行。"
                )
        else:
            log(f"[health] LT 链正常，上次更新 {gap/60:.0f} 分钟前")
    except Exception as e:
        log(f"[health] 检查异常: {e}")

# ── 每日任务状态 ──────────────────────────────────────────────
def _daily_done_path(date_str: str) -> Path:
    return DATA / f"daily_done_{date_str}.json"

def _is_task_done(date_str: str, task: str) -> bool:
    f = _daily_done_path(date_str)
    if not f.exists():
        return False
    try:
        return json.loads(f.read_text(encoding="utf-8")).get(task, False)
    except Exception:
        return False

def _mark_task_done(date_str: str, task: str):
    f = _daily_done_path(date_str)
    data: dict = {}
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    data[task] = True
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def check_daily_tasks() -> bool:
    """在 00:01-00:10 触发归档、23:00-23:10 触发日记。返回 True 表示本次有任务启动。"""
    now = datetime.now(CST)
    today = now.strftime("%Y-%m-%d")
    triggered = False

    if (now.hour == ARCHIVE_HOUR
            and ARCHIVE_MIN_START <= now.minute <= ARCHIVE_MIN_END
            and not _is_task_done(today, "archive")):
        log(f"[daily] 触发归档任务（{today} {now.hour:02d}:{now.minute:02d}）")
        ok = run_claude(ARCHIVE_PROMPT, "archive")
        if ok:
            _mark_task_done(today, "archive")
        triggered = True

    if (now.hour == DIARY_HOUR
            and DIARY_MIN_START <= now.minute <= DIARY_MIN_END
            and not _is_task_done(today, "diary")):
        log(f"[daily] 触发日记任务（{today} {now.hour:02d}:{now.minute:02d}）")
        ok = run_claude(DIARY_PROMPT, "diary")
        if ok:
            _mark_task_done(today, "diary")
        triggered = True

    return triggered

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

                # 无待处理文件，检查每日任务和健康状态，然后等待下次轮询
                check_daily_tasks()
                check_lt_health()
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
