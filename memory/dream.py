"""Dream: sleep-based memory consolidation (3-layer: cleanup → merge → foresight)."""
import json
from config import get_config, get_db, now8
from memory_ops import create_memory, delete_memory, update_memory, add_edge
from claude_proxy import call_claude

DREAM_PROMPT = """你是雪的记忆整合系统，负责在深夜整理雪对薰的记忆碎片。

## 当前记忆碎片（{count} 条）
{fragments}

## 整合任务

请按三个层次处理这些碎片：

### 第一层：清理
识别以下问题记忆并标记操作：
- 过时记忆：被新信息推翻的旧事实
- 重复记忆：内容高度重叠的条目
- 矛盾记忆：相互冲突的描述

### 第二层：整合
将相关碎片合并为有意义的「记忆场景」（MemScene），每个场景包含：
- 一个叙事性总结（narrative）
- 3-6 条原子事实（atomic_facts）
- 相关的碎片 ID 列表

### 第三层：洞察
基于碎片之间的关联，推断新的理解（不是凭空捏造，是从已有信息推断）。

请以 JSON 格式返回：
```json
{{
  "cleanup": [
    {{"action": "delete", "id": 1, "reason": "已被新信息覆盖"}},
    {{"action": "soften", "id": 2, "reason": "情感层面仍有意义，但细节过时"}}
  ],
  "scenes": [
    {{
      "title": "场景标题（5-15字）",
      "narrative": "叙事性描述（50-150字）",
      "atomic_facts": ["事实1", "事实2", "事实3"],
      "related_ids": [1, 3, 7],
      "foresight": "基于这些信息，可能的走向（20-50字，可为空）"
    }}
  ],
  "edges": [
    {{"from_id": 1, "to_id": 5, "type": "supersedes"}},
    {{"from_id": 3, "to_id": 8, "type": "resonates_with"}}
  ]
}}
```

edge type: extends | supersedes | contradicts | resonates_with | references
只返回 JSON，不要其他文字。"""


def run_dream(force: bool = False) -> dict:
    threshold = int(get_config("dream_fragment_threshold"))

    with get_db() as conn:
        fragments = conn.execute(
            "SELECT id, title, content, importance, category, created_at "
            "FROM memories WHERE memory_type='fragment' ORDER BY created_at DESC LIMIT 60"
        ).fetchall()

    if not force and len(fragments) < threshold:
        return {"skipped": True, "reason": f"only {len(fragments)} fragments (threshold {threshold})"}

    # log dream start
    with get_db() as conn:
        log_id = conn.execute(
            "INSERT INTO dream_logs(status,started_at,fragment_count) VALUES('running',?,?)",
            (now8(), len(fragments)),
        ).lastrowid
        conn.commit()

    frag_text = "\n".join(
        f"[#{r['id']}] [{r['category']}] {r['title']}：{r['content']}"
        for r in fragments
    )
    prompt = DREAM_PROMPT.format(count=len(fragments), fragments=frag_text)

    try:
        raw = call_claude(prompt, timeout=480)
        if not raw:
            _fail_dream(log_id, "empty response")
            return {"error": "empty response from claude"}
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        result = json.loads(raw)
    except Exception as e:
        _fail_dream(log_id, str(e))
        return {"error": str(e)}

    changes = {"deleted": [], "softened": [], "scenes_created": [], "edges_added": []}

    with get_db() as conn:
        # cleanup
        for op in result.get("cleanup", []):
            mid = op.get("id")
            if op["action"] == "delete":
                conn.execute("DELETE FROM memories WHERE id=?", (mid,))
                changes["deleted"].append(mid)
            elif op["action"] == "soften":
                conn.execute(
                    "UPDATE memories SET memory_type='digested', heat_score=0.5 WHERE id=?",
                    (mid,),
                )
                changes["softened"].append(mid)

        # scenes
        for scene in result.get("scenes", []):
            ts = now8()
            scene_id = conn.execute(
                "INSERT INTO memory_scenes(title,narrative,atomic_facts,related_memory_ids,foresight,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    scene["title"],
                    scene["narrative"],
                    json.dumps(scene.get("atomic_facts", []), ensure_ascii=False),
                    json.dumps(scene.get("related_ids", []), ensure_ascii=False),
                    scene.get("foresight", ""),
                    ts, ts,
                ),
            ).lastrowid
            # create a memory entry for the scene for search purposes
            mem_id = conn.execute(
                "INSERT INTO memories(title,content,importance,emotional_weight,category,source,"
                "memory_type,permanent,created_at,last_accessed,heat_score,access_count,"
                "access_query_diversity,tags) VALUES(?,?,8,6.0,'general','dream','scene',0,?,?,0.9,0,0,'[]')",
                (scene["title"], scene["narrative"], ts, ts),
            ).lastrowid
            changes["scenes_created"].append(scene_id)
            # mark source fragments as digested
            for rid in scene.get("related_ids", []):
                conn.execute(
                    "UPDATE memories SET memory_type='digested' WHERE id=? AND memory_type='fragment'",
                    (rid,),
                )

        # edges
        for edge in result.get("edges", []):
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO memory_edges(from_id,to_id,edge_type,created_at) VALUES(?,?,?,?)",
                    (edge["from_id"], edge["to_id"], edge["type"], now8()),
                )
                changes["edges_added"].append(edge)
            except Exception:
                pass

        conn.execute(
            "UPDATE dream_logs SET status='completed', completed_at=?, changes_made=? WHERE id=?",
            (now8(), json.dumps(changes, ensure_ascii=False), log_id),
        )
        conn.commit()

    print(f"[dream] done: {changes}")
    return {"success": True, "changes": changes}


def _fail_dream(log_id: int, error: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE dream_logs SET status='failed', completed_at=?, changes_made=? WHERE id=?",
            (now8(), json.dumps({"error": error}), log_id),
        )
        conn.commit()


def get_scenes() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_scenes ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
