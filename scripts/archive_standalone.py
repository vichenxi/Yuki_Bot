# -*- coding: utf-8 -*-
"""
archive_standalone.py — 每日对话归档（纯 Python，无 AI / 无 claude / 无 Telegram 插件依赖）

适合由操作系统定时器（Windows 任务计划程序 / cron）每日 00:01 调用，把**前一天（北京时间）**
的对话从 memory.db 导出到 data/full_archive_<昨天>.json。完全独立于任何 LLM 会话运行，
因此不会与基于会话/插件的收发产生冲突（如 Telegram getUpdates 409）。

用法：
  python scripts/archive_standalone.py            # 归档昨天
  python scripts/archive_standalone.py 2026-06-17 # 归档指定日期

日志：archive_standalone.log（仓库根目录）
"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repo root
LT_IF = ROOT / "memory" / "lt_interface.py"
DATA = ROOT / "data"
LOG = ROOT / "archive_standalone.log"
CST = timezone(timedelta(hours=8))


def log(msg: str):
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def main() -> int:
    day = sys.argv[1] if len(sys.argv) >= 2 else (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
    out = DATA / f"full_archive_{day}.json"
    try:
        r = subprocess.run(
            [sys.executable, str(LT_IF), "get_conversations", day, "200"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
    except Exception as e:
        log(f"FAIL 调用 lt_interface ({day}): {e}")
        return 1
    if r.returncode != 0:
        log(f"FAIL get_conversations {day} (rc={r.returncode}): {(r.stderr or '')[:300]}")
        return 1
    try:
        arr = json.loads(r.stdout.strip())
    except Exception as e:
        log(f"FAIL 解析 JSON ({day}): {e}")
        return 1
    try:
        out.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"FAIL 写文件 {out.name}: {e}")
        return 1
    log(f"OK {day} -> {out.name}（{len(arr)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
