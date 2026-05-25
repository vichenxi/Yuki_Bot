"""
tg_daemon.py — Telegram 来消息监听器

功能：轮询 Telegram getUpdates，当收到薰的消息时，
     写入 pending_reply.json，等待 Claude Code 消费（删除文件）。

用法：
  pythonw tg_daemon.py    # 后台无窗口运行
  python tg_daemon.py     # 前台调试

日志：C:/Users/Violet/.claude/yukibot/tg_daemon.log
"""

import json
import time
import sys
import os
import io
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request
import urllib.error

# pythonw 下重定向输出
if sys.stdout is None or getattr(sys.stdout, 'encoding', 'utf-8').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(open(os.devnull, 'wb'), encoding='utf-8')
if sys.stderr is None or getattr(sys.stderr, 'encoding', 'utf-8').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(open(os.devnull, 'wb'), encoding='utf-8')

BASE             = Path(__file__).resolve().parent.parent
DATA             = BASE / "data"
CONFIG_PATH      = BASE / "config.json"
PENDING_REPLY    = DATA / "pending_reply.json"
OFFSET_FILE      = DATA / "tg_offset.json"
LOG_FILE         = BASE / "tg_daemon.log"
PID_FILE         = BASE / "tg_daemon.pid"

POLL_TIMEOUT     = 30    # Telegram long-poll 等待秒数
SIGNAL_TIMEOUT   = 120   # 等待 handle_reply.py 完成的最长秒数
RETRY_INTERVAL   = 300   # 处理超时后重试间隔（秒）
HANDLE_REPLY     = BASE / "core" / "handle_reply.py"

CST = timezone(timedelta(hours=8))


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


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def read_offset() -> int:
    if OFFSET_FILE.exists():
        try:
            return json.loads(OFFSET_FILE.read_text(encoding="utf-8-sig")).get("offset", 0)
        except Exception:
            pass
    return 0


def save_offset(offset: int):
    OFFSET_FILE.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def get_updates(token: str, offset: int) -> list:
    url = (
        f"https://api.telegram.org/bot{token}/getUpdates"
        f"?offset={offset}&timeout={POLL_TIMEOUT}&allowed_updates=[\"message\"]"
    )
    try:
        with urllib.request.urlopen(url, timeout=POLL_TIMEOUT + 10) as resp:
            data = json.loads(resp.read())
            return data.get("result", [])
    except urllib.error.URLError as e:
        log(f"getUpdates 网络错误：{e}")
        return []
    except Exception as e:
        log(f"getUpdates 异常：{e}")
        return []


def ts_to_cst_iso(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=CST).isoformat()


def download_photo(token: str, file_id: str, save_path: str) -> bool:
    """从 Telegram 下载图片并保存到本地。"""
    try:
        url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        file_path = data["result"]["file_path"]
        dl_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        with urllib.request.urlopen(dl_url, timeout=30) as resp:
            image_data = resp.read()
        with open(save_path, "wb") as f:
            f.write(image_data)
        return True
    except Exception as e:
        log(f"图片下载失败：{e}")
        return False


def write_pending_reply(messages: list):
    payload = {
        "requested_at": datetime.now(CST).isoformat(),
        "trace_id": uuid.uuid4().hex[:8],
        "messages": messages,
    }
    with open(PENDING_REPLY, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"[pending_reply] 已写入 {len(messages)} 条消息，trace={payload['trace_id']}")


def merge_into_pending(new_messages: list) -> bool:
    """将新消息合并进现有 pending_reply.json。返回 True 表示合并成功（文件存在）。"""
    if not PENDING_REPLY.exists():
        return False
    try:
        existing = json.loads(PENDING_REPLY.read_text(encoding="utf-8"))
        old_msgs = existing.get("messages", [])
        old_ids = {m.get("update_id") for m in old_msgs}
        to_add = [m for m in new_messages if m.get("update_id") not in old_ids]
        if to_add:
            existing["messages"] = old_msgs + to_add
            existing["updated_at"] = datetime.now(CST).isoformat()
            PENDING_REPLY.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log(f"[pending_reply] 追加 {len(to_add)} 条新消息（合并入现有文件）")
        return True
    except Exception as e:
        log(f"[pending_reply] 合并失败：{e}")
        return False


def launch_handle_reply():
    """启动 handle_reply.py 后台子进程，立即返回 Popen 对象（非阻塞）。"""
    log("[handle] 启动 handle_reply.py（后台）...")
    return subprocess.Popen(
        ["python", str(HANDLE_REPLY)],
        cwd=str(BASE),
        stdout=open(BASE / "handle_reply.log", "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )


def main():
    if not acquire_lock():
        print(f"[tg_daemon] 已有实例在运行（{PID_FILE}），退出。")
        sys.exit(0)

    try:
        log("=== tg_daemon 启动 ===")
        log(f"PID：{os.getpid()}")

        cfg = load_config()
        token = cfg["bot_token"]
        chat_id = str(cfg["default_chat_id"])

        offset = read_offset()
        log(f"起始 offset：{offset}")

        handle_proc = None   # 当前 handle_reply.py 子进程
        handle_start = 0.0   # 子进程启动时间（用于超时判断）
        msg_queue = []       # handle_reply 运行期间收到的消息

        while True:
            try:
                # ── 1. 检查 handle_reply 子进程状态 ──────────────────
                if handle_proc is not None:
                    retcode = handle_proc.poll()
                    if retcode is not None:
                        log(f"[handle] handle_reply.py 完成（exitcode={retcode}）")
                        handle_proc = None
                        # 若有队列消息，立即处理
                        if msg_queue:
                            write_pending_reply(msg_queue)
                            msg_queue = []
                            handle_proc = launch_handle_reply()
                            handle_start = time.time()
                    elif time.time() - handle_start > SIGNAL_TIMEOUT:
                        log(f"[warn] handle_reply.py 超时（{SIGNAL_TIMEOUT}s），强制终止")
                        handle_proc.kill()
                        handle_proc = None
                        log("[warn] pending_reply.json 保留，claude_monitor 兜底")
                        # 若有队列消息，合并进现有 pending 或新建
                        if msg_queue:
                            if not merge_into_pending(msg_queue):
                                write_pending_reply(msg_queue)
                            msg_queue = []

                # ── 2. 若 pending 存在但无子进程，重新启动 ────────────
                if handle_proc is None and PENDING_REPLY.exists():
                    log("[pending_reply] 文件残留，重新启动 handle_reply...")
                    handle_proc = launch_handle_reply()
                    handle_start = time.time()

                # ── 3. 轮询 Telegram ──────────────────────────────────
                updates = get_updates(token, offset)

                if not updates:
                    continue  # long-poll 超时，无新消息，直接重试

                new_messages = []
                max_update_id = offset - 1

                for upd in updates:
                    uid = upd.get("update_id", 0)
                    max_update_id = max(max_update_id, uid)

                    msg = upd.get("message")
                    if not msg:
                        continue

                    from_chat = str(msg.get("chat", {}).get("id", ""))
                    if from_chat != chat_id:
                        continue

                    text = msg.get("text", "")
                    caption = msg.get("caption", "")

                    # 图片处理
                    image_path = None
                    photo = msg.get("photo")
                    if photo:
                        largest = max(photo, key=lambda p: p.get("file_size", 0))
                        img_name = f"tg_img_{uid}.jpg"
                        img_save = str(DATA / img_name)
                        if download_photo(token, largest["file_id"], img_save):
                            image_path = img_save
                            log(f"图片已保存：{img_name}")

                    content = text or caption or ("[图片]" if image_path else "[非文字消息]")

                    new_messages.append({
                        "update_id": uid,
                        "text": content,
                        "ts": ts_to_cst_iso(msg.get("date", 0)),
                        "from": msg.get("from", {}).get("first_name", ""),
                        "image_path": image_path,
                    })

                # 推进 offset
                new_offset = max_update_id + 1
                if new_offset > offset:
                    save_offset(new_offset)
                    offset = new_offset

                if not new_messages:
                    continue

                log(f"收到 {len(new_messages)} 条新消息")

                if handle_proc is not None and handle_proc.poll() is None:
                    # handle_reply 正在运行：消息入队，合并进 pending 文件
                    msg_queue.extend(new_messages)
                    merge_into_pending(new_messages)
                    log(f"[handle] handle_reply 运行中，{len(new_messages)} 条入队（队列共 {len(msg_queue)} 条）")
                else:
                    # 无运行中的处理器：直接写文件并启动
                    all_msgs = new_messages + msg_queue
                    msg_queue = []
                    write_pending_reply(all_msgs)
                    handle_proc = launch_handle_reply()
                    handle_start = time.time()

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
        log("=== tg_daemon 已停止 ===")
    finally:
        if handle_proc is not None:
            handle_proc.kill()
        release_lock()


if __name__ == "__main__":
    main()
