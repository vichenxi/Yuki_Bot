# 雪 (Yuki) · AI 陪伴 Bot

一个运行在 Windows 上的 Telegram AI 陪伴 bot，集成长期记忆、定时主动消息、语音合成和 AI 生图。

---

## 快速开始（4 步）

**第一步：改角色**

用文本编辑器打开 `character.txt`，替换里面的人设内容（姓名、背景故事、说话方式……）。
这是唯一需要编辑的角色文件。

高级参数（主动消息频率、睡眠时段、life tick 提示词）在 `persona.py` 的"角色设定区"里调。

**第二步：初始化**
```
双击 setup.bat
```
自动写入安装路径、创建必要目录、复制配置模板。

**第三步：填写配置**

用文本编辑器打开 `config.json`，至少填写以下三项：
```json
{
  "bot_token": "你的 Telegram Bot Token",
  "default_chat_id": "对话对象的 Chat ID",
  "llm": {
    "provider": "claude",
    "model": "claude-sonnet-4-6",
    "api_key": ""
  }
}
```
详细配置说明见 `DEPLOY.md`。

**第四步：启动**
```
双击 start.bat
```

---

## 系统架构

三个进程并行运行，通过信号文件解耦：

```
  消息回复流程
  ─────────────────────────────────────────────────────────

  薰 ──Telegram消息──▶ tg_daemon.py（长轮询 30s）
                            │
                     写 pending_reply.json
                            │
                     直接启动 handle_reply.py
                            │
                      调 LLM API
                      发 Telegram 回复
                      存对话记忆 / LT 自检
                            │
                     删除 pending_reply.json ──▶ 完成

  ⚠ 若 handle_reply 超时或崩溃，claude_monitor 兜底：
    检测到 pending_reply.json 残留
    → claude -p reply_prompt.txt（读 character.txt → 执行全流程）


  Life Tick 流程
  ─────────────────────────────────────────────────────────

  lt_daemon.py ──读 next_tick.json──▶ 等到预定时间
       │
       写 pending_tick.json
       │
  claude_monitor.py 检测到文件
       │
  claude -p lifetick_prompt.txt
       │    读 character.txt → 读记忆 → 决策是否发消息
       │
  写 next_tick.json（下次 tick 时间）
  删除 pending_tick.json ──▶ 完成
```

**核心设计**：`tg_daemon` / `lt_daemon` 只负责计时和写信号文件，不含任何 AI 逻辑。`handle_reply.py` 处理绝大多数回复；`claude_monitor.py` 处理所有 Life Tick，并在 reply 链断掉时兜底。三个进程任意一个崩溃都不影响其他两个。

---

## 文件说明

### 根目录

| 文件 | 说明 |
|------|------|
| `character.txt` | **角色人设**（纯文本）。改这一个文件定义角色，其他文件无需动 |
| `persona.py` | 角色参数：睡眠时段、主动消息频率、life tick 提示词。上方"角色设定区"可改，下方框架代码不动 |
| `start.bat` | **一键启动**三个守护进程（lt_daemon、tg_daemon、claude_monitor），后台无窗口运行 |
| `setup.bat` | **首次运行必须执行**。写入安装路径、初始化目录结构 |
| `config.json` | 所有配置：Bot Token、Chat ID、LLM 接入、语音/图像模型路径 |
| `config.example.json` | 配置模板，含注释说明每个字段的含义 |
| `requirements.txt` | Python 依赖列表（`pip install -r requirements.txt` 安装） |
| `DEPLOY.md` | 详细部署文档：各 LLM 配置方法、大文件获取、完整启动流程 |

---

### `core/` — 运行时核心

Bot 的核心可执行模块，全部在这里。

| 文件 | 角色 | 说明 |
|------|------|------|
| `tg_daemon.py` | 常驻进程 | 轮询 Telegram API，接到消息后写 `pending_reply.json`，然后启动 `handle_reply.py` 处理 |
| `handle_reply.py` | 回复引擎 | 读取消息 → 查记忆 → 调 LLM 生成回复 → 发 Telegram（含语音合成）→ 存对话记录 |
| `lt_daemon.py` | 常驻进程 | 每隔随机 15–45 分钟写一次 `pending_tick.json`，触发 Life Tick |
| `claude_monitor.py` | 常驻进程 | 监控 `data/` 目录，发现 pending 文件就调用 `claude -p` 处理，是三个进程的调度核心 |
| `check_tg_updates.py` | 工具脚本 | Life Tick 开始前调用，扫描是否有未处理的 Telegram 消息。若 tg_daemon 停了则自动触发回复 |
| `send_voice.py` | 工具脚本 | 调 GPT-SoVITS API 合成语音，通过 Telegram sendVoice 发送。也可命令行单独使用 |
| `send_image.py` | 工具脚本 | 下载远程图片（url 模式）或本地 SD 生成图片（generate 模式），发 Telegram sendPhoto |
| `send_selfie.py` | 工具脚本 | 用 SD + LoRA 生成雪的自拍图，直接发送（一次性脚本，手动运行） |
| `vrm_render.py` | 工具脚本 | 无头渲染 VRM 模型为 PNG（Playwright + Three.js）。用于 LoRA 训练数据生成，也可单独调用生成参考图 |

---

### `memory/` — 记忆系统 & 管理面板

所有记忆的存取都通过这个包进行，外部只需调用 `lt_interface.py`。

| 文件 | 说明 |
|------|------|
| `lt_interface.py` | **唯一的对外入口**。命令行接口，支持：`get_life_context`、`add_life_log`、`get_conversations`、`add_conversation`、`get_memory_context`、`add_memory`、`get_unread`、`save_unread` 等指令 |
| `db.py` | SQLite 连接管理和基础查询 |
| `memory_ops.py` | 记忆的增删改查（长期记忆、生活日志、对话记录） |
| `search.py` | 向量相似度搜索，用于 `get_memory_context` 返回相关记忆片段 |
| `embedding.py` | 文本转向量，使用本地嵌入模型（无需外部 API） |
| `extract.py` | 对话满 20 条时自动运行，将重要信息提炼成长期记忆片段 |
| `dream.py` | 记忆整合模块，定期把碎片记忆归并梳理（类比"做梦"） |
| `calendar_mem.py` | 日程和重要事件的记忆接口 |
| `llm_client.py` | 通用 LLM 客户端。统一封装 Claude CLI / OpenAI / DeepSeek / Gemini / Ollama，其余模块调 LLM 时用这个，不直接写请求代码 |
| `claude_proxy.py` | Claude CLI 的底层调用封装 |
| `config.py` | 记忆系统内部配置（数据库路径、嵌入模型等） |
| `migrate.py` | 数据库版本迁移脚本，升级时用 |
| `admin/server.py` | 记忆库管理面板的 FastAPI 后端，端口 8765 |
| `admin/index.html` | 管理面板前端，浏览器打开可查看/编辑所有记忆、日记、对话 |
| `admin/vrm_viewer.html` | 独立 VRM 查看器页面（Three.js + @pixiv/three-vrm），含 idle 动画和眨眼 |

**管理面板**：双击 `scripts/open_memory.bat` 自动启动并打开浏览器。

**VRM 3D 模型查看器**：
- 管理面板首页内嵌 iframe，直接显示可旋转 3D 模型（仅 yaw 轴旋转，全身 fit 显示）
- 也可单独访问：`http://127.0.0.1:8765/vrm-viewer`
- 依赖 Three.js 静态文件由 `desktop/node_modules/` 提供，admin 启动时自动挂载
- 模型文件：`F:\bot\Yuki.vrm`，通过 `/model/vrm` 端点提供

---

### `prompts/` — 系统提示词

每个文件对应 bot 的一个任务流程，`claude -p` 执行时读取。路径已参数化，`setup.bat` 运行后自动替换为实际安装路径。

> 角色人设单独存放在根目录的 `character.txt`，每个 prompt 文件开头都有指令让 Claude 先读取它，无需在这里重复定义。

| 文件 | 触发时机 | 说明 |
|------|----------|------|
| `lifetick_prompt.txt` | 每次 Life Tick | 完整的 tick 执行流程：睡眠检查 → 消息扫描 → 读记忆 → 决策要不要发消息 → 写日志 → 调度下次 tick |
| `reply_prompt.txt` | 每条 Telegram 消息 | 处理 `pending_reply.json`：读历史 → 生成回复 → 发消息 → 存记忆 → LT 自检 |
| `wakeup_prompt.txt` | 早上第一个 tick | 处理睡眠期间积压的未读消息 |
| `lt_selfcheck_prompt.txt` | 每次回复后 | 检查 LT 链是否断掉，断了则重新调度 |
| `recovery_prompt.txt` | 系统启动时 | 检查离线时长，补全缺失的 tick 记录，恢复三个守护进程 |
| `archive_prompt.txt` | 手动触发 | 将对话归档整理 |
| `diary_prompt.txt` | 手动触发 | 生成雪视角的日记 |

---

### `data/` — 运行时数据

| 文件 / 目录 | 说明 |
|-------------|------|
| `memory.db` | **核心数据库**（SQLite）。存储所有长期记忆、对话记录、生活日志、未读队列 |
| `lt_state.json` | Life Tick 健康状态：连续失败次数、上次成功时间。失败 3 次触发熔断保护 |
| `next_tick.json` | 下次 Life Tick 的预定时间（ISO 格式），lt_daemon 读取这个文件决定等多久 |
| `tg_offset.json` | Telegram getUpdates 的消息游标，防止同一条消息被重复处理 |
| `pending_reply.json` | 信号文件：tg_daemon 写入，handle_reply 处理后删除 |
| `pending_tick.json` | 信号文件：lt_daemon 写入，claude_monitor 触发 LT 后删除 |
| `daily_events_<日期>.json` | 当日事件计划（由 Life Tick 生成），包含情绪弧度和计划内的"自发事件" |
| `daily_memory_<日期>.json` | 当日记忆摘要（结构化） |
| `profiles/` | 头像和立绘图片，管理面板使用 |
| `logs/<日期>_yuki.txt` | 雪的日记（雪的主观视角，按日期） |
| `logs/<日期>_yuki_lt.txt` | Life Tick 运行日志（每次 tick 的活动、心情、是否发消息） |

---

### `scripts/` — 辅助脚本

| 文件 | 说明 |
|------|------|
| `open_memory.bat` | 启动记忆库管理面板（如未运行），并自动打开浏览器 `http://127.0.0.1:8765` |
| `start_voice_api.bat` | 启动 GPT-SoVITS 语音合成 API（端口 9880），需要先安装 GPT-SoVITS |
| `startup_recovery.ps1` | 开机恢复脚本：检测离线、补全记录、重启三个守护进程。注册为开机任务后自动运行 |
| `register_startup.bat` | 将 `startup_recovery.ps1` 注册到 Windows 任务计划程序，实现开机自启 |

---

### `lora/` — LoRA 训练流水线

从 VRM 模型一键生成训练数据并训练角色 LoRA，无需手动标注图片。

| 文件 | 说明 |
|------|------|
| `1_setup.ps1` | **首次运行一次**。克隆 kohya-ss/sd-scripts 到 `E:\sd-scripts`，在 `sd` conda 环境中安装依赖 |
| `gen_data.py` | 调用 `core/vrm_render.py`，渲染 8 个全身角度 + 3 个半身角度共 11 张图，并自动生成 caption `.txt` 文件 |
| `dataset_config.toml` | kohya 数据集配置（`num_repeats=20`，`resolution=512`） |
| `2_train.ps1` | **一键完成**：渲染数据 → 训练 LoRA（30 epochs，`network_dim=32`）。结果输出至 `data/lora/output/` |

**前置条件**：admin 服务（`memory/start_admin.bat`）需在运行中，`gen_data.py` 通过 `/model/vrm` 端点取模型。

**训练产出位置**：
```
data/lora/output/yuki_lora_v1.safetensors          ← 最终权重
data/lora/output/yuki_lora_v1-000005.safetensors   ← epoch 5 checkpoint
data/lora/output/yuki_lora_v1-000010.safetensors   ← epoch 10 checkpoint
...（每 5 epoch 保存一次）
```

**使用训练好的 LoRA 生成图片**：
```
1. 复制 data/lora/output/yuki_lora_v1.safetensors
   → E:\stable-diffusion-webui\models\Lora\yuki_lora_v1.safetensors

2. 在 WebUI 提示词中加入：
   yukixue, 1girl, <lora:yuki_lora_v1:0.8>

3. 推荐参数：Realistic Vision V5.1、DPM++ 2M Karras、Steps 30、CFG 7、Clip skip 2
```

---

### `desktop/` — 桌面 Electron 应用

基于 Electron + Three.js 的桌面端雪交互界面，显示 VRM 3D 模型并支持实时对话。

```bash
cd desktop
npm install       # 首次
npm start         # 启动
```

VRM 模型文件路径：`F:\bot\Yuki.vrm`（需自行放置）。

---

### `assets/` — 静态资源

| 目录 | 说明 |
|------|------|
| `voice_models/` | GPT-SoVITS 语音模型权重（`.ckpt` + `.pth`），已内置，无需额外下载 |
| `voice_ref/` | 语音合成参考音频（`.wav`），决定音色基准 |
| `lora/yuki_lora/` | 旧版角色 LoRA 权重（HuggingFace PEFT 格式，基于 AOM3 底模），供 send_selfie.py 使用 |
| `pose_skeletons/` | 10 种姿势骨架图（ControlNet 用），用于控制生图中人物姿势 |
| `samples/` | 各阶段生成效果样图，仅供参考 |

---

### `dev/` — 开发工具（日常不需要）

| 目录 | 说明 |
|------|------|
| `tools/` | 模型训练和图像生成脚本（LoRA 训练、批量生图、样本处理等） |
| `tests/` | 各模块功能测试脚本（语音、LoRA、ControlNet 等） |

---

## 功能开关

| 功能 | 开启条件 |
|------|----------|
| Telegram 消息回复 | 填写 `bot_token` + `default_chat_id`，双击 `start.bat` |
| Life Tick（主动消息） | 同上（三个进程一起启动） |
| 语音消息 | 启动 GPT-SoVITS API（`scripts/start_voice_api.bat`），语音模型路径正确 |
| 自拍生图 | 填写 `sd_model_path`（SD 底模绝对路径），安装 diffusers 环境 |
| 记忆管理面板 | 双击 `scripts/open_memory.bat`，访问 `http://127.0.0.1:8765` |
| VRM 3D 查看器 | 管理面板启动后访问 `http://127.0.0.1:8765/vrm-viewer`，或直接在面板首页查看 |
| 桌面 Electron 应用 | `cd desktop && npm start`（需提前 `npm install`） |
| LoRA 训练 | 先运行 `lora/1_setup.ps1`（一次性），之后 `lora/2_train.ps1` 一键完成 |
| 开机自启 | 运行 `scripts/register_startup.bat`（需管理员权限） |

语音、自拍、桌面应用、LoRA 训练可以完全不启用，bot 正常以文字模式运行。

---

## 日志位置

| 日志 | 路径 |
|------|------|
| Telegram 监听日志 | `tg_daemon.log`（根目录） |
| 自主回复日志 | `handle_reply.log`（根目录） |
| claude_monitor 日志 | `monitor.log`（根目录） |
| lt_daemon 日志 | `daemon.log`（根目录） |
| Life Tick 详细记录 | `data/logs/<日期>_yuki_lt.txt` |
| 启动恢复日志 | `startup.log`（根目录） |

每次收到消息时，`tg_daemon` 会生成一个 8 位 `trace_id`，写入 `pending_reply.json`，`handle_reply.py` 的所有日志行都带这个前缀。调试某次具体回复时，只需在 `handle_reply.log` 里 grep 对应的 trace_id：

```
grep "a3f7b2c1" handle_reply.log
```

---

## LLM 兼容性说明

`handle_reply.py` 要求 LLM 返回 JSON 格式（包含 `messages`、`thought`、`mood`、`voice_index` 字段）。若 LLM 未能输出合法 JSON，会自动 fallback 到按 `---` 分割的文字模式，不影响正常发送，但 `thought` / `mood` 追踪会降级为上一条状态。

- **推荐**：Gemini 1.5+、GPT-4o、Claude 3+ —— JSON 输出稳定
- **可用**：DeepSeek、Gemini Flash —— 偶尔 fallback，不影响功能
- **不建议**：本地小模型（7B 以下）—— JSON 格式遵循率低，体验下降

---

## 详细部署文档

见 [DEPLOY.md](DEPLOY.md)，包含：各 LLM 接入方式、Claude CLI 安装、依赖安装、大文件获取地址。

---

## 修复日志 / Changelog

### 2026-06-18（晚）— 发布前脱敏 + 忽略规则加固，架构更新推送

- **脱敏**：`prompts/lifetick_prompt.txt`、`dev/tests/test_headless.py` 里硬编码的个人 Telegram `chat_id` 已替换为 `YOUR_CHAT_ID` 占位符（仓库为公开 remote，避免外泄个人信息）。
- **`.gitignore` 加固**：新增 `node_modules/`、`*.vrm`、`*.vroid`——`git add -A` 误纳入的 `desktop/node_modules/`（数千依赖文件）与 27MB 形象模型（`Yuki.vrm`/`Yuki.vroid`）已撤出暂存、不再提交。
- **推送**：架构更新提交并推送到 `origin/main`（97 文件：`core/`/`memory/`/`prompts/`/`desktop/`/`dev/`/docs）。再次确认 **无 memory（`data/`、`*.db`、日记/LT/归档）、无 bot token** 进入提交。
- 验证：`git ls-files` 无敏感文件、待提交文件内搜不到 token、`index.html`(18MB) 经核为打包前端 JS 而非嵌入对话数据。

### 2026-06-18 — 接通 API 路由 + 个人数据归一防外泄 + 新增独立脚本

**API 路由接通（回复 / 记忆提取改用 `llm_client`）**
- `core/handle_reply.py`：`call_claude` / 图片记忆评估改为调用 `memory/llm_client.py` 的 `chat` / `chat_with_image`（按文件位置解析 `memory/`，不再依赖旧的 `memlib` 绝对路径）。
- `memory/extract.py`：改 `from llm_client import chat as call_claude`，去掉对 `claude_proxy.is_available` 的前置探测（`llm_client` 自带降级）。
- `config.json` 增加 `llm` 块（`provider/model/api_key/base_url`，默认 `provider=claude` 行为不变；设为 openai/deepseek/gemini/ollama + api_key 即走 HTTP API）。
- 验证：`config.json` 合法、两文件 `py_compile` 通过、`llm_client.chat("…")` 经 claude 路径实测返回正常文本。
- ⚠️ 已知限制：`core/*.py` 与 `prompts/*.txt` 仍硬编码了 `C:/Users/Violet/.claude/yukibot` 的安装路径（本仓库目前是镜像备份而非可直接 clone 即跑的发行版）；要做到真正"clone→改 config→跑"的 1:1 复刻，还需把这些路径参数化。`lifetick / diary / archive / recovery` 等是**agent 流程**（要读写文件、跑 Python、查库），无法用纯 `/chat/completions` 等价替换，需 Claude Agent SDK 或自建带工具执行的 agent。

**个人数据归一 + 防外泄（仓库有公开 GitHub remote）**
- 已确认 git 历史干净（从未提交过 memory.db / 日记 / 对话）。
- 把散落在根目录的 89 个 `*_yuki.txt` / `*_yuki_lt.txt`（日记 + LT 流水）与 `yuki_export_*` 全部移入已被 `.gitignore` 的 `data/`（日记/LT 进 `data/logs/`）。
- `.gitignore` 加固：新增 `private/`、`*_yuki.txt`、`*_yuki_lt.txt`、`yuki_export_*/`、`*.db`、`full_archive*`、`daily_memory_*`、`daily_events_*`、`life_log*`、`thoughts_*`，即使误放到 `data/` 之外也不会被提交。
- 同步 live 当前 `memory.db`（1052KB）到 `data/memory.db`（原快照停在 6/7）。

**新增脚本**
- `core/send_text.py`：urllib 直连 sendMessage 的文字直发工具（带退避重试），主动消息不依赖任何插件。
- `scripts/archive_standalone.py`：纯 Python 每日归档，可由 OS 定时器独立调用，不触发任何 LLM/插件。

**方案 C：provider 无关的 agent 工具循环（让生活引擎可 API 化）**

目标：把 `lifetick / diary / archive / recovery` 从 Anthropic CLI agent 解耦，改由任意支持
tool-calling 的 LLM 通过"模型请求工具 → 本地执行 → 回灌结果"循环驱动。

- `memory/agent.py`：`run_agent(system, user, tools, executor, llm)` 通用工具循环；OpenAI 兼容
  （openai/deepseek/gemini/ollama，用 openai SDK 的 tools）与 anthropic（claude，用 SDK 的 tools）双后端。
- `core/agent_tools.py`：12 个本地工具 + schema + `execute()`：`get_current_time`、记忆库读写
  （`get_life_context/add_life_log/get_conversations/add_conversation/get_memory_context/get_today_sent/get_unread`）、
  `read_file/write_file`、`send_text`、`web_search`（未配置时返回降级提示）。
- `core/run_agent_task.py`：入口。`python core/run_agent_task.py <lifetick|diary|archive|recovery|wakeup>`；
  自动把提示词里旧的 `C:/Users/Violet/.claude/yukibot` 绝对路径改写为本仓库根，确保 agent 操作本仓库。
- `dev/tests/test_agent_loop_mock.py`：循环机制的确定性单测。

**测试状态（诚实记录）**
- ✅ 循环机制：mock 单测通过（多步工具调用、执行、结果回灌、按序、终止于最终文本）。
- ✅ 请求形态：对 Gemini 的真实调用已正确构造 OpenAI tools 请求（仅因该 key 免费额度=0 返回 429）。
- ✅ 工具执行：`agent_tools.execute` 实测可对 `data/memory.db` 取时间 / today_sent / 记忆上下文。
- ✅ 入口接线：`--dry` 自检显示提示词加载 + 路径改写（lifetick 命中 33 处）+ 12 工具就绪。
- ⏳ **真实 LLM 端到端**：本机无可用 API key（Gemini 额度 0；本地 `claude` 是订阅 oauth，非 API key，401；CLI 不暴露原始 tool-calling），故未实测整条 lifetick。**需在 `config.json` 的 `llm` 块填入可用的 openai/deepseek/gemini/anthropic API key 后**，运行 `python core/run_agent_task.py lifetick --verbose` 即可端到端验证。
**路径可移植化（已根治，2026-06-18）**
- `core/*.py` 的安装路径全部由硬编码 `C:/Users/Violet/.claude/yukibot` 改为相对 `__file__` 解析：`handle_reply / tg_daemon / lt_daemon / lt_executor` 的 `BASE = Path(__file__).resolve().parent.parent`（仓库根），同级脚本用 `core/`；并统一 `memlib → memory`。
- `prompts/*.txt`（lifetick/recovery/diary/archive/lt_selfcheck 共 ~58 处）的绝对路径改为 `{{ROOT}}` 占位符 + `/memlib/→/memory/`；`run_agent_task.py` 运行时把 `{{ROOT}}` 替换为本仓库根。
- 验证：全部 `py_compile` 通过；`handle_reply.BASE / tg_daemon.HANDLE_REPLY / lt_executor.CLAUDE_PROMPT` 实测均指向 `F:/bot/...`（不再指向 live 安装）；`run_agent_task lifetick --dry` 显示 `{{ROOT}}→F:/bot` 命中 33 处；源码已无功能性硬编码路径（仅余 docstring 注释）。
- 结论：**仓库现可 clone 到任意机器，填好 `config.json` 的 LLM api_key 即跑**（语音/生图等可选依赖另配）。
- `.gitignore` 再加 `*.log`（根目录日志可能含消息片段）。
