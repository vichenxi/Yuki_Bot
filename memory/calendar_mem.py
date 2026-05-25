"""Calendar hierarchy: day → week → month summaries for efficient context injection."""
import json
from datetime import datetime, timedelta
from config import get_config, get_db, now8, TZ8
from claude_proxy import call_claude

DAY_PROMPT = """基于以下今日对话和生活记录，写一篇日记式总结（雪的视角，100-200字）：

## 对话摘要
{conversations}

## 今日 Life Tick
{life_logs}

要求：
- 第一人称（雪的内心视角），不是旁观者描述
- 包含：今天做了什么、和薰的交流、情绪流动
- 风格与雪日记一致：冷静，偶尔一句击中要害的话
只返回日记文本，不要标题和其他格式。"""

WEEK_PROMPT = """将以下七天的日记总结压缩为一段周摘要（50-100字）：

{day_pages}

要求：提炼本周的主要情绪走向、与薰关系的变化、重要事件。只返回摘要文本。"""

MONTH_PROMPT = """将以下四周的周摘要压缩为月摘要（30-60字）：

{week_pages}

要求：只保留最关键的关系进展和情绪转折。只返回摘要文本。"""


def _call_claude(prompt: str) -> str:
    return call_claude(prompt)


def generate_day_page(date: str) -> str:
    with get_db() as conn:
        convs = conn.execute(
            "SELECT role, content FROM conversations WHERE date=? ORDER BY ts",
            (date,),
        ).fetchall()
        logs = conn.execute(
            "SELECT ts, activity, mood FROM life_logs WHERE date=? AND sleeping=0 ORDER BY ts",
            (date,),
        ).fetchall()

    conv_text = "\n".join(
        f"{'薰' if r['role']=='user' else '雪'}：{r['content'][:100]}"
        for r in convs
    ) or "（今日无对话）"
    log_text = "\n".join(
        f"{r['ts'][11:16]} {r['mood']}：{r['activity']}"
        for r in logs
    ) or "（无记录）"

    content = _call_claude(DAY_PROMPT.format(conversations=conv_text, life_logs=log_text))
    if not content:
        content = f"{date} 无摘要"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO calendar_pages(date,page_type,content,generated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(date,page_type) DO UPDATE SET content=excluded.content, generated_at=excluded.generated_at",
            (date, "day", content, now8()),
        )
        conn.commit()
    return content


def generate_week_summary(week_start: str) -> str:
    start = datetime.fromisoformat(week_start)
    day_pages = []
    with get_db() as conn:
        for i in range(7):
            d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT content FROM calendar_pages WHERE date=? AND page_type='day'",
                (d,),
            ).fetchone()
            if row:
                day_pages.append(f"## {d}\n{row['content']}")

    if not day_pages:
        return ""
    content = _call_claude(WEEK_PROMPT.format(day_pages="\n\n".join(day_pages)))
    if not content:
        return ""

    with get_db() as conn:
        conn.execute(
            "INSERT INTO calendar_pages(date,page_type,content,generated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(date,page_type) DO UPDATE SET content=excluded.content, generated_at=excluded.generated_at",
            (week_start, "week", content, now8()),
        )
        conn.commit()
    return content


def generate_month_summary(month: str) -> str:
    """month: YYYY-MM"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date, content FROM calendar_pages WHERE date LIKE ? AND page_type='week' ORDER BY date",
            (f"{month}%",),
        ).fetchall()

    if not rows:
        return ""
    week_text = "\n\n".join(f"## 周 {r['date']}\n{r['content']}" for r in rows)
    content = _call_claude(MONTH_PROMPT.format(week_pages=week_text))
    if not content:
        return ""

    with get_db() as conn:
        conn.execute(
            "INSERT INTO calendar_pages(date,page_type,content,generated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(date,page_type) DO UPDATE SET content=excluded.content, generated_at=excluded.generated_at",
            (month, "month", content, now8()),
        )
        conn.commit()
    return content


def get_calendar_context(days_back: int | None = None) -> str:
    days_back = days_back or int(get_config("calendar_inject_days"))
    now = datetime.now(TZ8)
    lines = []

    with get_db() as conn:
        # recent day pages
        for i in range(min(days_back, 7)):
            d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT content FROM calendar_pages WHERE date=? AND page_type='day'",
                (d,),
            ).fetchone()
            if row:
                label = "今天" if i == 0 else f"{i}天前"
                lines.append(f"[{label} {d}] {row['content'][:100]}…")

        # recent week summary
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT content FROM calendar_pages WHERE date=? AND page_type='week'",
            (week_start,),
        ).fetchone()
        if row:
            lines.append(f"[本周摘要] {row['content'][:80]}…")

    return "\n".join(lines)


def list_pages(page_type: str | None = None, limit: int = 30) -> list[dict]:
    with get_db() as conn:
        if page_type:
            rows = conn.execute(
                "SELECT * FROM calendar_pages WHERE page_type=? ORDER BY date DESC LIMIT ?",
                (page_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calendar_pages ORDER BY date DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
