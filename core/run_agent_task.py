# -*- coding: utf-8 -*-
"""
run_agent_task.py — 用 provider 无关的工具循环执行雪的生活引擎任务（方案 C 入口）

用法：
  python core/run_agent_task.py lifetick [--verbose] [--dry]
  python core/run_agent_task.py diary
  python core/run_agent_task.py archive
  python core/run_agent_task.py recovery | wakeup

它把 prompts/<task>_prompt.txt 作为流程说明喂给 agent，agent 通过 agent_tools 里的
工具（读写记忆/文件、发消息、联网）完成任务。LLM 后端由 config.json 的 llm 块决定，
provider 无关——claude / openai / deepseek / gemini / ollama 皆可。

  --dry  只组装 system/user/tools 并打印概览，不调用 LLM（用于自检接线）。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "memory"))
sys.path.insert(0, str(ROOT / "core"))
import agent
import agent_tools

PROMPTS = ROOT / "prompts"
LIVE_PREFIX = "C:/Users/Violet/.claude/yukibot"   # 旧硬编码安装路径
ROOT_POSIX = ROOT.as_posix()

SYSTEM = (
    "你是雪本人，同时是她的生活引擎执行器。你有一组本地工具可用（见 tools 列表）。"
    "请严格按用户消息里的流程提示词执行：用工具读写记忆与文件、做情绪/是否发消息的决策、必要时发消息。"
    "所有时间一律用北京时间(UTC+8)，开始前先用 get_current_time 获取当前时间与日期。"
    "你没有 shell/Bash：提示词里出现的任何 `python .../lt_interface.py <cmd> ...` 都改成调用同名工具"
    "（get_life_context/add_life_log/get_conversations/add_conversation/get_memory_context/get_today_sent/get_unread）；"
    "读写文件用 read_file/write_file；发消息用 send_text；联网用 web_search。"
    "全部步骤完成后，用一句话中文总结你这次做了什么（是否发消息、心情、下次 tick 时间）。"
)


def build_user(task: str) -> str:
    pf = PROMPTS / f"{task}_prompt.txt"
    prompt = pf.read_text(encoding="utf-8")
    # 把 {{ROOT}} 占位符（及历史遗留的绝对安装路径）改写为本仓库根，确保 agent 操作本仓库
    return prompt.replace("{{ROOT}}", ROOT_POSIX).replace(LIVE_PREFIX, ROOT_POSIX)


def main() -> int:
    args = sys.argv[1:]
    task = next((a for a in args if not a.startswith("-")), "lifetick")
    verbose = "--verbose" in args
    dry = "--dry" in args

    pf = PROMPTS / f"{task}_prompt.txt"
    if not pf.exists():
        print(f"[run_agent_task] 找不到提示词：{pf}")
        return 1

    user = build_user(task)

    if dry:
        print(f"[dry] task={task}")
        print(f"[dry] tools={len(agent_tools.TOOLS)}: {[t['function']['name'] for t in agent_tools.TOOLS]}")
        print(f"[dry] system chars={len(SYSTEM)}  user chars={len(user)}")
        print(f"[dry] path remap: {{{{ROOT}}}} -> {ROOT_POSIX}  (命中 {user.count(ROOT_POSIX)} 处)")
        return 0

    out = agent.run_agent(SYSTEM, user, agent_tools.TOOLS, agent_tools.execute,
                          max_steps=60, max_tokens=4096, verbose=verbose)
    print("=== AGENT DONE ===")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
