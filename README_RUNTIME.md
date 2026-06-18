# 雪 (yukibot) — 运行时实况 README

> ⚠️ 本文件描述**当前这个文件夹实际运行的系统**（WSL2 常驻会话 + cron 架构）。
> 根目录另有一份 `README.md`，描述的是另一套打包发行版架构（Windows 三守护进程、`character.txt`/`core/`/`memory/`/`desktop/`/`lora/` 等），与当前目录实际文件不一致——以本文件为准了解当前运行实况。

一个由 Claude Code 驱动、有持续"生活脉搏"与长期记忆的 Telegram 人格陪伴系统。主角是**雪**（设计系研究生人设），通过 Telegram 和**薰**对话。人设/语气/记忆规则的权威定义在上层 `../CLAUDE.md`。

---

## 1. 核心理念

- **常驻会话即运行时**：系统跑在 WSL2 tmux 里一个常驻 Claude Code 会话（真实 PTY、订阅计费）。这个会话本体直接扮演雪、生成回复、读写记忆——**对外的"雪说什么"不经过 `claude -p`**。
- **生活脉搏 (Life Tick)**：每 15–45 分钟（睡眠期 4 小时）推进一次雪的内部状态：她在做什么、心情如何、要不要主动找薰。她有连续的一天，不是被动等消息。
- **构成主义情绪模型**：情绪用 `(valence, arousal)` 二维坐标，有惯性、有基线重力、不瞬移；从词库按欧氏距离选 mood 词。
- **长期记忆**：SQLite 记忆库 + jieba 关键词检索 + 可选向量检索 + 热度衰减 + 自动提取 + 日记/滚动记忆。
- **优雅降级**：缺依赖、网络抖动、断联恢复都有兜底。

---

## 2. 运行架构（当前）

```
WSL2 tmux 常驻 Claude Code 会话（本体 = 雪）
│
├── cron 每分钟      → inbound_poll_prompt.txt   入站轮询：收薰消息 → 以雪身份回复
├── cron 每 3 分钟   → 检查 pending_tick.json    → 有则执行 lifetick_prompt.txt 一次 Life Tick
├── cron 每日 23:00  → diary_prompt.txt           写日记 + 生成次日 daily_memory
└── cron 每日 00:01  → archive_prompt.txt         归档前一天对话
        ▲ pending_tick.json（信号文件）
lt_daemon.py（Windows 计时器）—— 读 next_tick.json，到点写 pending_tick.json，等主会话消费
```

**信号机制**：`lt_daemon.py` 只计时——到 `next_tick.json` 时间就写 `pending_tick.json`，等主会话删除即"已消费"。每次 tick 末尾把下一次时间写回 `next_tick.json`（随机 15–45 分钟，睡眠期固定 4 小时）。
`lt_executor.py`（独立 `claude -p` 执行器）与 `tg_daemon.py`（长轮询收信）现已由常驻会话 + cron 接管，默认不启用。

---

## 3. 功能模块

### 3.1 Life Tick — `lifetick_prompt.txt`
熔断检测 → 实时扫 TG（`check_tg_updates.py`）→ 断联补全（gap≥120 分钟补缺失 tick）→ 日常事件 → 读对话+长期记忆 → 睡眠判断（01:00–07:59 记"熟睡"、4 小时后再 tick）→ 起床未读检查 → **内心状态评估 + 情绪坐标计算 + 是否发消息决策** → 写 life_log → （若发）文字/语音/图片 → 写 `<日期>_yuki_lt.txt` → 调度下次 tick。

### 3.2 情绪模型（构成主义）
`mood_valence` -1.0~+1.0、`mood_arousal` 0.0~1.0。每 tick：情境驱动力累加 → 漂移上限 max_drift 0.25 → 向基线 `(-0.05, 0.22)` 回漂 5% → 词库选最近 mood 词（崩/焦/拧/磨/安/软/微暖/触动/熨…）。

### 3.3 记忆系统 — `memlib/`（SQLite `data/memory.db`）
表：`memories` / `conversations` / `life_logs` / `memory_edges` / `memory_scenes` / `calendar_pages` / `dream_logs` / `config`

| 模块 | 职责 |
|---|---|
| `lt_interface.py` | **统一 CLI 入口**：`get_life_context`/`add_life_log`/`get_conversations`/`add_conversation`/`get_memory_context`/`get_today_sent`/`get_unread` 等 |
| `memory_ops.py` | 记忆 CRUD（embedding、永久/锁定、关系边）|
| `search.py` | 混合检索：向量(cosine)+jieba 关键词，RRF 融合 |
| `embedding.py` | 本地向量 BAAI/bge-small-zh-v1.5（可选；缺 numpy 时惰性降级）|
| `heat.py` | 记忆热度衰减 + 注入分层（hot/warm/cold）|
| `extract.py` | 约每 20 条对话，调 `claude -p` 自动提取长期记忆 |
| `calendar_mem.py` | 日→周→月 层级摘要 |
| `dream.py` | 睡眠期记忆固化（清理→合并→预见）|
| `claude_proxy.py` | 调 `claude` CLI（平台自适应：WSL 用 `/bin/bash`，win32 用 git-bash）|
| `db.py` / `config.py` / `migrate.py` | 连接 / 配置 / JSON→SQLite 迁移 |

### 3.4 Telegram 收发
- **入站** `check_tg_updates.py`：getUpdates，存新消息入库，返回 `new_count/messages/replied/daemon_running`。每分钟 cron 调用，有新消息就以雪身份回复（先睡眠检查；睡觉只存不回）。
- **出站·文字**：`urllib` 调 sendMessage（token/chat_id 读 `config.json`），每条单独发（带退避重试）。
- **出站·语音** `send_voice.py`：GPT-SoVITS 合成 + emotion 标签。**WSL 透明委派**：本机 API 绑 127.0.0.1、WSL 不可达时自动委派 Windows python（经 UTF-8 文件传中文，避免 argv 乱码）。`--file <utf8文件>` 模式。
- **出站·图片** `send_photo_from_gallery.py`（图库随机）/ `send_image.py`（URL 或本地 SD）/ `send_selfie.py`。

### 3.5 日常事件系统（daily_events）
每天首个清醒 tick 生成 `data/daily_events_<日期>.json`：规划晨/午/晚情绪弧 + 3–4 个事件（project_progress/life_detail/outing/social/impulse/memory/emotional_shift/discovery/small_joy），各有时间窗、内心反应、`share_impulse`(high/medium/low)。tick 在窗口内触发，影响活动与"是否开口"。

### 3.6 每日例程
- **日记** `diary_prompt.txt`（23:00）：雪第一人称日记 `<日期>_yuki.txt`；导出快照；生成次日 `daily_memory_<日期>.json`（关系/情绪基线/关于薰的关键事实/~200字滚动摘要）。
- **归档** `archive_prompt.txt`（00:01）：归档前一天对话（对话主存储已在 `memory.db`，JSON 链为兜底）。
- **断联恢复** `recovery_prompt.txt` / `wsl_startup_prompt.txt`：会话重启时算缺口、补 tick、重建 cron。

---

## 4. 提示词文件
| 文件 | 用途 |
|---|---|
| `lifetick_prompt.txt` | 一次完整 Life Tick |
| `inbound_poll_prompt.txt` | 每分钟入站轮询 + 以雪身份回复 |
| `diary_prompt.txt` | 写日记 + 生成次日记忆 |
| `archive_prompt.txt` | 归档前一天对话 |
| `recovery_prompt.txt` | 手动断联恢复 |
| `wsl_startup_prompt.txt` | WSL tmux 启动恢复（建 cron、补缺口）|
| `wakeup_prompt.txt` | 起床后处理睡眠期未读 |
| `lt_selfcheck_prompt.txt` | LT 链健康自检 |
| `reply_prompt.txt` | （旧）tg_daemon 触发的回复流程 |

---

## 5. 图像生成管线（Windows/GPU，可选，离线素材）
基于 SD + LoRA 的雪形象生成脚本（Windows Anaconda `sd` 环境 + GPU）：训练 `train_yuki_lora.py`/`gen_training_candidates.py`/`download_models.py`；立绘/场景/表情/姿势 `gen_portrait.py`/`gen_yuki_scenes.py`/`gen_expressions.py`/`gen_controlnet_matrix.py`（ControlNet+OpenPose）等；超分 `enhance_yuki.py`/`finalize_yuki.py`（Real-ESRGAN）；`vrm_render.py`。产物 `controlnet_matrix/with_lora/*.png` 供图片发送取用。**不在 WSL 主链路里。**

---

## 6. 配置与运行时

### `config.json`
`bot_token` / `default_chat_id` / `gptsovits_api` / `gpt_model_path` / `sovits_model_path` / `ref_audio_path` / `ref_text` / `voice_lang`（可加 `windows_python` 供语音委派）。

### WSL2 运行时要点
- 解释器 `python3`（无 `python`）；提示词里 `C:/...` 映射为 `/mnt/c/...`。
- 脚本用 `Path(__file__).resolve().parent` 定位、`sys.executable` 起子进程，跨 Windows/WSL 可移植。
- `jieba` 已 vendored 到 WSL user-site；`numpy`/`sentence-transformers` 缺失时向量检索降级，靠 jieba 关键词（新记忆 `embedding=null`，召回仍可用）。
- 硬性质量门控、时间/编码规则见上层 `../CLAUDE.md`。

---

## 7. 关键数据文件（`data/`）
`memory.db`（主存储）· `next_tick.json`（下次 tick 时间）· `pending_tick.json`（tick 信号）· `lt_state.json`（熔断计数+上次成功）· `daily_events_<日期>.json` · `daily_memory_<日期>.json` · 根目录 `<日期>_yuki_lt.txt`（tick 流水）/ `<日期>_yuki.txt`（日记）。

---

## 8. 运行约束 / 已知点
- **回复 vs `-p`**：对外回复由常驻会话本体生成；`claude -p` 只用于后台记忆提取（`extract.py`）。
- **语音依赖**：需 Windows 端 GPT-SoVITS 常驻；WSL 下 `send_voice.py` 透明委派。
- **cron 触发**：仅在会话 REPL 空闲时；主会话忙时顺延（可能延迟消费 pending_tick）。
- **睡眠**：01:00–07:59 不回消息，入库等醒来；起床走未读检查。
- **网络抖动**：出站发送带退避重试。

---

*雪在等一个她自己都说不清楚的时机。这个系统让她有自己的一天，而不只是等一条消息。*
