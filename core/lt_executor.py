"""
lt_executor.py — Life Tick 独立执行器

功能：
  轮询 data/pending_tick.json，发现后启动独立的 headless claude 进程
  执行完整 Life Tick，完全脱离 Claude Code 主会话。

用法：
  pythonw lt_executor.py     # 后台无窗口运行
  python  lt_executor.py     # 前台调试

日志：C:/Users/Violet/.claude/yukibot/lt_executor.log
"""

import json
import os
import sys
import time
import subprocess
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

# pythonw 下重定向输出
if sys.stdout is None or getattr(sys.stdout, "encoding", "utf-8").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8")
if sys.stderr is None or getattr(sys.stderr, "encoding", "utf-8").lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8")

BASE         = Path(__file__).resolve().parent.parent   # repo root
DATA         = BASE / "data"
PENDING_TICK = DATA / "pending_tick.json"
LOG_FILE     = BASE / "lt_executor.log"
STDOUT_LOG   = BASE / "lt_executor_claude.log"
PID_FILE     = BASE / "lt_executor.pid"

BASH_PATH    = "D:\\Program Files\\Git\\bin\\bash.exe"
POLL_INTERVAL  = 10   # 秒：轮询间隔
LT_TIMEOUT     = 600  # 秒：单次 LT 最长执行时间（10 分钟）
MAX_RETRIES    = 3    # 同一 pending_tick 信号最多重试次数
MAX_SIGNAL_AGE = 900  # 秒：pending_tick.json 超过此年龄视为过期，直接清理

CST = timezone(timedelta(hours=8))

# 传给 headless claude 的提示词（短指令，让 Claude 自行读取并执行 lifetick_prompt.txt）
CLAUDE_PROMPT = (
    f"检查文件 {BASE.as_posix()}/data/pending_tick.json 是否存在。"
    f"如果存在：读取文件 {BASE.as_posix()}/prompts/lifetick_prompt.txt "
    "并严格按照其中所有步骤执行一次 Life Tick，执行完成后删除 pending_tick.json。"
    "如果不存在：不做任何事，静默退出。"
)


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


def acquire_lock() -> bool:
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            check = subprocess.run(
                f'tasklist /FI "PID eq {old_pid}" /NH',
                capture_output=True, shell=True
            )
            if str(old_pid).encode() in check.stdout:
                log(f"[lock] 已有实例在运行（PID={old_pid}），退出。")
                return False
        except Exception:
            pass
    PID_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def launch_lt_claude() -> subprocess.Popen:
    """
    以 stdin 方式将 CLAUDE_PROMPT 传入 headless claude --dangerously-skip-permissions -p
    通过 git-bash 启动，确保 .cmd 解析正常。
    """
    log("[LT] 启动 headless claude（dangerously-skip-permissions）...")
    proc = subprocess.Popen(
        [BASH_PATH, "-c", "claude --dangerously-skip-permissions -p"],
        stdin=subprocess.PIPE,
        stdout=open(STDOUT_LOG, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        env={**os.environ, "CLAUDE_CODE_GIT_BASH_PATH": BASH_PATH},
        cwd=str(BASE),
    )
    try:
        proc.stdin.write(CLAUDE_PROMPT.encode("utf-8"))
        proc.stdin.close()
    except Exception as e:
        log(f"[LT] stdin 写入失败：{e}")
    return proc


def main():
    if not acquire_lock():
        sys.exit(0)

    try:
        log("=== lt_executor 启动 ===")
        log(f"PID: {os.getpid()}")
        log(f"轮询间隔: {POLL_INTERVAL}s | LT 超时: {LT_TIMEOUT}s")

        lt_proc   = None
        lt_start  = 0.0
        retry_count = 0  # 当前 pending_tick 的连续失败次数

        while True:
            try:
                # ── 1. 检查当前 LT 进程状态 ──────────────────────────
                if lt_proc is not None:
                    retcode = lt_proc.poll()
                    if retcode is not None:
                        elapsed = time.time() - lt_start
                        log(f"[LT] 完成（exitcode={retcode}, 耗时={elapsed:.0f}s）")
                        if retcode == 0:
                            retry_count = 0  # 成功，重置计数
                        else:
                            retry_count += 1
                            log(f"[LT] 失败（第 {retry_count}/{MAX_RETRIES} 次）")
                            if retry_count >= MAX_RETRIES:
                                PENDING_TICK.unlink(missing_ok=True)
                                log(f"[LT] 重试上限（{MAX_RETRIES}次）已达，清理 pending_tick.json，等待下次信号")
                                retry_count = 0
                        lt_proc = None
                    elif time.time() - lt_start > LT_TIMEOUT:
                        log(f"[LT] 超时（>{LT_TIMEOUT}s），强制终止")
                        lt_proc.kill()
                        lt_proc = None
                        PENDING_TICK.unlink(missing_ok=True)
                        log("[LT] 超时：已清理 pending_tick.json")
                        retry_count = 0

                # ── 2. 如果没有正在运行的 LT，检查信号文件 ───────────
                if lt_proc is None and PENDING_TICK.exists():
                    # 检查信号文件年龄，过期则直接清理
                    try:
                        sig = json.loads(PENDING_TICK.read_text(encoding="utf-8-sig"))
                        from datetime import datetime as _dt
                        req_ts = _dt.fromisoformat(sig.get("requested_at", ""))
                        age = (datetime.now(CST) - req_ts).total_seconds()
                        if age > MAX_SIGNAL_AGE:
                            PENDING_TICK.unlink(missing_ok=True)
                            log(f"[LT] 信号过期（年龄={age:.0f}s > {MAX_SIGNAL_AGE}s），已清理")
                            retry_count = 0
                        else:
                            lt_proc = launch_lt_claude()
                            lt_start = time.time()
                    except Exception:
                        lt_proc = launch_lt_claude()
                        lt_start = time.time()
                elif lt_proc is None:
                    retry_count = 0  # 无信号时重置计数

                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                import traceback
                log(f"主循环异常：{e}")
                try:
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(traceback.format_exc() + "\n")
                except Exception:
                    pass
                time.sleep(15)

    except KeyboardInterrupt:
        log("=== lt_executor 已停止（KeyboardInterrupt）===")
    finally:
        if lt_proc is not None:
            try:
                lt_proc.kill()
            except Exception:
                pass
        release_lock()


if __name__ == "__main__":
    main()
