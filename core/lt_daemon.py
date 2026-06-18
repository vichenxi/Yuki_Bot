"""
lt_daemon.py — Life Tick 调度器（信号模式）

职责：只负责计时，到时间写 pending_tick.json 作为信号。
      实际 LT 执行由主 Claude Code 会话的 monitor cron 负责。

用法：
  python lt_daemon.py          # 前台运行
  pythonw lt_daemon.py         # 后台运行（无窗口，Windows）

停止：Ctrl+C 或结束进程
日志：C:/Users/Violet/.claude/yukibot/daemon.log
"""

import json
import time
import sys
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# pythonw 下 sys.stdout/stderr 为 None 或 GBK 流，统一重定向到 devnull
import io
if sys.stdout is None or getattr(sys.stdout, 'encoding', 'utf-8').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(open(os.devnull, 'wb'), encoding='utf-8')
if sys.stderr is None or getattr(sys.stderr, 'encoding', 'utf-8').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(open(os.devnull, 'wb'), encoding='utf-8')

# ── 路径配置 ────────────────────────────────────────────
BASE          = Path(__file__).resolve().parent.parent   # repo root
DATA          = BASE / "data"
CONFIG_PATH   = BASE / "config.json"
NEXT_TICK_FILE    = DATA / "next_tick.json"
PENDING_TICK_FILE = DATA / "pending_tick.json"
LOG_FILE      = BASE / "daemon.log"
PID_FILE      = BASE / "daemon.pid"

POLL_INTERVAL     = 30   # 秒：主循环轮询间隔
SIGNAL_TIMEOUT    = 600  # 秒：写入信号后等待 lt_executor 消费的最长时间（含首次失败+重试）
FALLBACK_INTERVAL = 900  # 秒：lt_executor 超时未消费，重置等待时间（15分钟后重试）

CST = timezone(timedelta(hours=8))

# ── Telegram 通知 ─────────────────────────────────────────
def notify_owner(token: str, chat_id: str, text: str):
    """向主人发送 Telegram 系统通知。"""
    import urllib.request as _req
    try:
        body = json.dumps({"chat_id": chat_id, "text": text}, ensure_ascii=False).encode("utf-8")
        r = _req.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        with _req.urlopen(r, timeout=10):
            pass
        log("[notify] 已发送通知给主人")
    except Exception as e:
        log(f"[notify] 发送通知失败：{e}")


# ── 配置 ──────────────────────────────────────────────────
def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── 单实例锁 ─────────────────────────────────────────────
def acquire_lock() -> bool:
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            check = subprocess.run(
                f'tasklist /FI "PID eq {old_pid}" /NH',
                capture_output=True, shell=True
            )
            if str(old_pid).encode() in check.stdout:
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

# ── 工具函数 ─────────────────────────────────────────────
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

def now_cst() -> datetime:
    return datetime.now(CST)

def read_next_tick() -> datetime:
    if NEXT_TICK_FILE.exists():
        try:
            with open(NEXT_TICK_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return datetime.fromisoformat(data["next_tick"])
        except Exception as e:
            log(f"读取 next_tick.json 失败：{e}，立即触发")
    return now_cst()

def write_pending_signal():
    """写入信号文件，通知主会话执行 LT。"""
    with open(PENDING_TICK_FILE, "w", encoding="utf-8") as f:
        json.dump({"requested_at": now_cst().isoformat()}, f)
    log("[pending] 已写入 pending_tick.json，等待主会话处理")

def wait_for_consumption() -> bool:
    """
    等待主会话消费 pending_tick.json（删除文件即为消费）。
    返回 True = 已消费，False = 超时未消费。
    """
    deadline = time.time() + SIGNAL_TIMEOUT
    while time.time() < deadline:
        if not PENDING_TICK_FILE.exists():
            log("[ok] 主会话已处理 LT")
            return True
        time.sleep(5)
    log(f"[warn] 主会话 {SIGNAL_TIMEOUT}s 内未处理，信号保留，下次主会话启动时会捡起")
    return False

# ── 主循环 ───────────────────────────────────────────────
def main():
    if not acquire_lock():
        print(f"[lt_daemon] 已有实例在运行（见 {PID_FILE}），本次退出。")
        sys.exit(0)

    try:
        log("=== lt_daemon 启动（信号模式）===")
        log(f"PID：{os.getpid()}")

        cfg = load_config()
        token = cfg["bot_token"]
        owner_id = str(cfg.get("owner_chat_id", cfg.get("default_chat_id", "")))

        _notified_timeout = False  # 本次信号超时只通知一次

        while True:
            try:
                # 如果已有未消费的信号，继续等待，不重复写入
                if PENDING_TICK_FILE.exists():
                    log("[pending] pending_tick.json 已存在，等待主会话处理...")
                    wait_for_consumption()
                    time.sleep(POLL_INTERVAL)
                    _notified_timeout = False
                    continue

                next_tick = read_next_tick()
                now = now_cst()
                wait_sec = (next_tick - now).total_seconds()

                if wait_sec <= 0:
                    write_pending_signal()
                    consumed = wait_for_consumption()
                    if not consumed:
                        # lt_executor 未在预期时间内处理，通知主人并等待重试
                        log(f"[warn] 将在 {FALLBACK_INTERVAL//60} 分钟后重新发送信号")
                        if not _notified_timeout and owner_id:
                            notify_owner(token, owner_id,
                                f"[LT系统] ⚠️ lt_executor 未在 {SIGNAL_TIMEOUT}s 内处理 Life Tick 信号。\n"
                                f"可能原因：API 故障/lt_executor 已停止/Claude 连续失败超过重试上限。\n"
                                f"请检查 lt_executor.log。下次重试：{FALLBACK_INTERVAL//60} 分钟后。")
                            _notified_timeout = True
                        time.sleep(FALLBACK_INTERVAL)
                    else:
                        _notified_timeout = False
                else:
                    eta = next_tick.strftime("%H:%M")
                    log(f"下次 tick：{eta}，等待 {wait_sec/60:.1f} 分钟")
                    time.sleep(min(wait_sec, POLL_INTERVAL))

            except KeyboardInterrupt:
                raise
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                log(f"主循环异常：{e}")
                try:
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(tb + "\n")
                except Exception:
                    pass
                if owner_id:
                    notify_owner(token, owner_id,
                        f"[LT系统] ❌ lt_daemon 主循环异常：{e}\n请检查 daemon.log。")
                time.sleep(10)

    except KeyboardInterrupt:
        log("=== lt_daemon 已停止（KeyboardInterrupt）===")
    finally:
        release_lock()

if __name__ == "__main__":
    main()
