# 部署说明

## 目录

1. [环境要求](#1-环境要求)
2. [获取 Telegram Bot Token 和 Chat ID](#2-获取-telegram-bot-token-和-chat-id)
3. [安装 Python 依赖](#3-安装-python-依赖)
4. [配置 LLM（大语言模型）](#4-配置-llm大语言模型)
5. [配置 config.json](#5-配置-configjson)
6. [初始化（setup.bat）](#6-初始化setupbat)
7. [启动 Bot](#7-启动-bot)
8. [语音功能（可选）](#8-语音功能可选)
9. [生图功能（可选）](#9-生图功能可选)
10. [开机自启（可选）](#10-开机自启可选)
11. [常见问题](#11-常见问题)
12. [文件结构速查](#文件结构速查)

---

## 1. 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | 3.11 或更高版本 |
| 网络 | 能访问 Telegram API（`api.telegram.org`） |
| Claude CLI | 仅使用 Claude 作为 LLM 时需要 |

**安装 Python**：前往 [python.org](https://www.python.org/downloads/) 下载安装，安装时勾选"Add Python to PATH"。

**验证安装**：
```
python --version
```

---

## 2. 获取 Telegram Bot Token 和 Chat ID

### Bot Token
1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot`，按提示填写 bot 名称和用户名
3. BotFather 会返回一串 Token，格式如 `1234567890:AAF...`
4. 将这串 Token 填入 `config.json` 的 `bot_token`

### Chat ID（你自己的）
1. 在 Telegram 中搜索 `@userinfobot`，发送任意消息
2. 它会返回你的 Chat ID（一串数字）
3. 填入 `config.json` 的 `default_chat_id`

---

## 3. 安装 Python 依赖

在 bot 根目录打开命令提示符，运行：

```
pip install -r requirements.txt
```

安装内容：FastAPI（记忆管理面板）、sentence-transformers（向量记忆）、anthropic（Claude 图像接口）、requests 等。

> **注意**：`sentence-transformers` 首次运行时会自动下载嵌入模型（约 90 MB），需要网络连接。

---

## 4. 配置 LLM（大语言模型）

选择以下任意一种方式接入，修改 `config.json` 的 `llm` 字段。

### 方式一：Claude CLI（推荐）

无需 API Key，使用 Claude 官方命令行工具。

**安装 Claude CLI**：
```
npm install -g @anthropic-ai/claude-code
```
如果没有 Node.js，先从 [nodejs.org](https://nodejs.org/) 安装。

**登录**：
```
claude login
```
按提示在浏览器完成授权，凭据会自动保存到本地。

**config.json 配置**：
```json
"llm": {
  "provider": "claude",
  "model": "claude-sonnet-4-6",
  "api_key": "",
  "base_url": ""
}
```

---

### 方式二：OpenAI

```json
"llm": {
  "provider": "openai",
  "model": "gpt-4o-mini",
  "api_key": "sk-...",
  "base_url": ""
}
```

---

### 方式三：DeepSeek

```json
"llm": {
  "provider": "deepseek",
  "model": "deepseek-chat",
  "api_key": "sk-...",
  "base_url": ""
}
```

---

### 方式四：Gemini

```json
"llm": {
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "api_key": "AIza...",
  "base_url": ""
}
```

前往 [aistudio.google.com](https://aistudio.google.com/) 获取 API Key。

---

> **JSON 输出兼容性**：`handle_reply.py` 要求 LLM 返回 JSON 格式回复（包含角色话语、内心OS、心情、是否语音等字段）。若 LLM 输出不合法 JSON，会自动 fallback 到纯文字模式，功能不受影响，但情绪追踪精度下降。推荐使用 Claude 3+、GPT-4o、Gemini 1.5+；本地小模型（7B 以下）遵循率较低，不建议用于主对话。

### 方式五：Ollama（本地部署）

先安装并运行 Ollama：
```
ollama serve
ollama pull llama3
```

```json
"llm": {
  "provider": "ollama",
  "model": "llama3",
  "api_key": "",
  "base_url": ""
}
```

---

### 方式六：自定义 OpenAI 兼容接口

```json
"llm": {
  "provider": "custom",
  "model": "your-model-name",
  "api_key": "your-key",
  "base_url": "http://localhost:1234/v1"
}
```

---

## 5. 配置 config.json

在 bot 根目录找到 `config.json`，参考以下说明填写：

```json
{
  "bot_token": "你的 Telegram Bot Token",
  "default_chat_id": "对话对象的 Chat ID（数字）",

  "gptsovits_api": "http://127.0.0.1:9880",

  "gpt_model_path": "./assets/voice_models/42-e15.ckpt",
  "sovits_model_path": "./assets/voice_models/42_e8_s152.pth",
  "ref_audio_path": "./assets/voice_ref/任命助理.wav",
  "ref_text": "（语音参考文本，日语）",

  "llm": {
    "provider": "claude",
    "model": "claude-sonnet-4-6",
    "api_key": "",
    "base_url": ""
  },

  "sd_model_path": "",
  "lora_path": "./assets/lora/yuki_lora"
}
```

**必填项**：`bot_token`、`default_chat_id`、`llm`（至少填 provider 和 model）

**可选项**：语音相关字段留默认值即可（模型已内置）；`sd_model_path` 留空则禁用生图功能。

**路径说明**：所有以 `./` 开头的路径均相对于 bot 根目录，无需改动；`sd_model_path` 是 SD 底模的绝对路径，需手动填写。

---

## 6. 初始化（setup.bat）

**首次使用必须运行**，双击根目录的 `setup.bat`。

它会自动完成：
- 将 `prompts/` 目录中所有提示词文件里的路径占位符替换为实际安装路径
- 检查 `config.json` 是否存在（不存在则从 example 复制）
- 创建必要的子目录（`data/logs/`、`assets/voice_models/` 等）

运行后看到"初始化完成"即可。

---

## 7. 启动 Bot

**日常启动**：双击根目录的 `start.bat`

脚本会在后台启动三个进程：

| 进程 | 文件 | 职责 |
|------|------|------|
| lt_daemon | `core/lt_daemon.py` | Life Tick 计时器，每隔随机 15–45 分钟写信号 |
| tg_daemon | `core/tg_daemon.py` | Telegram 消息监听，收到消息后直接启动 handle_reply.py |
| claude_monitor | `core/claude_monitor.py` | 监控信号文件，执行 Life Tick；handle_reply 失败时兜底 |

**验证是否启动成功**：

几秒后检查根目录是否出现以下日志文件：
- `tg_daemon.log` — 有"tg_daemon 启动"字样
- `monitor.log` — 有"claude_monitor 启动"字样
- `daemon.log` — 有"lt_daemon 启动"字样

**调试某次具体回复**：

`handle_reply.log` 中每行都带一个 8 位 trace_id（由 tg_daemon 生成并写入 pending 文件）。要追踪某次回复的完整链路，先在 `tg_daemon.log` 找到收消息那行的 `trace=xxxxxxxx`，然后：
```
grep "xxxxxxxx" handle_reply.log
```

**手动前台运行（调试用）**：
```
python core/lt_daemon.py
python core/tg_daemon.py
python core/claude_monitor.py
```

**停止 Bot**：打开任务管理器，结束所有 `pythonw.exe` 进程；或运行：
```
taskkill /F /IM pythonw.exe
```

---

## 8. 语音功能（可选）

Bot 收到特定类型的消息时，可以用 GPT-SoVITS 合成雪的声音发送语音消息。

### 8-1. 安装 GPT-SoVITS

从官方 GitHub 下载 GPT-SoVITS v2Pro 安装包：
```
https://github.com/RVC-Boss/GPT-SoVITS/releases
```
下载 Windows 整合包，解压到任意目录。

### 8-2. 启动语音 API

双击 `scripts\start_voice_api.bat`（或运行 GPT-SoVITS 目录内的 `api_v2.bat`）。

API 启动后监听 `http://127.0.0.1:9880`，`config.json` 中的 `gptsovits_api` 默认已配置为此地址。

### 8-3. 语音模型

语音模型已内置于 `assets/voice_models/`：
- `42-e15.ckpt`：GPT 权重（148 MB）
- `42_e8_s152.pth`：SoVITS 权重（165 MB）
- `assets/voice_ref/任命助理.wav`：参考音频

`config.json` 中的默认路径已指向这些文件，无需修改。

### 8-4. 验证

语音 API 运行时，bot 在判断合适的情感时机会自动发出语音消息，无需额外操作。

---

## 9. 生图功能（可选）

Bot 可以生成雪的自拍图片（Stable Diffusion + 角色 LoRA）。

### 9-1. 安装 SD 环境

需要单独的 conda 环境（避免依赖冲突）：
```bash
conda create -n sd python=3.10
conda activate sd
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install diffusers peft transformers accelerate
```

需要 NVIDIA GPU（CUDA 12.1+），显存建议 8 GB 以上。

### 9-2. 下载 SD 底模

前往 Civitai 下载 `AOM3A1B_orangemixs.safetensors`（或其他兼容的 SD 1.5 底模）：
```
https://civitai.com/models/9942
```

### 9-3. 填写路径

在 `config.json` 中填写底模的绝对路径：
```json
"sd_model_path": "D:\\models\\AOM3A1B_orangemixs.safetensors"
```

LoRA 权重已内置于 `assets/lora/yuki_lora/`，`lora_path` 保持默认即可。

---

## 10. 开机自启（可选）

让 bot 在 Windows 启动后自动恢复运行。

以**管理员身份**运行（右键 → 以管理员身份运行）：
```
scripts\register_startup.bat
```

注册成功后，每次开机会等待 15 秒（等网络就绪），然后自动执行 `scripts\startup_recovery.ps1`：
- 检测离线时长，补全缺失的 Life Tick 记录
- 重新启动 lt_daemon、tg_daemon、claude_monitor

**取消开机自启**：
```
schtasks /Delete /TN "YukiBot_Startup" /F
```

---

## 11. 常见问题

**Q：bot 收不到消息**

检查 `tg_daemon.log`，常见原因：
- `bot_token` 填错（格式：`数字:字母`）
- `default_chat_id` 填错（必须是纯数字，不是用户名）
- 网络无法访问 `api.telegram.org`（需要代理）

**Q：回复失败，monitor.log 显示"找不到 claude"**

Claude CLI 未安装或未登录：
```
npm install -g @anthropic-ai/claude-code
claude login
```

如果使用其他 LLM，确认 `config.json` 的 `api_key` 正确填写。

**Q：语音 API 连不上**

确认 GPT-SoVITS 的 API 服务已启动（任务栏或进程里应有 `python` 进程），并且端口 9880 未被占用。

**Q：记忆管理面板打不开**

双击 `scripts\open_memory.bat`，它会先启动服务再打开浏览器。如果浏览器开了但页面空白，等 2–3 秒刷新。

**Q：`setup.bat` 提示"路径替换失败"**

确保 bot 目录路径中没有中文字符或特殊符号（括号、空格等可能导致 bat 脚本解析失败）。

**Q：想换角色人设**

- 修改根目录的 `character.txt`（纯文本，写角色背景/性格/说话方式，这是唯一需要改的人设文件）
- 调整 `persona.py` 顶部"角色设定区"中的角色名、睡眠时段、主动消息频率等参数
- `config.json` 中的语音参考文件和 LoRA 路径按需替换

---

## 文件结构速查

```
bot/
├── character.txt          ← 角色人设（改这一个文件定义角色）
├── persona.py             ← 角色参数（睡眠时段、消息频率、LT提示词）
├── start.bat              ← 一键启动三个守护进程
├── setup.bat              ← 首次运行，初始化路径和目录
├── config.json            ← 填写凭据和模型路径
├── config.example.json    ← 配置模板参考
├── requirements.txt       ← pip 依赖
├── README.md / DEPLOY.md  ← 文档
│
├── core/                  ← 运行时脚本
│   ├── tg_daemon.py       ← Telegram 监听，收消息 → 写 pending + 启动 handle_reply
│   ├── lt_daemon.py       ← Life Tick 计时，到时 → 写 pending_tick
│   ├── claude_monitor.py  ← 监控 pending_tick → 调 claude -p；handle_reply 失败兜底
│   ├── handle_reply.py    ← 回复引擎（读记忆 → 调 LLM → 发消息 → 存记忆）
│   ├── check_tg_updates.py
│   ├── send_voice.py
│   ├── send_image.py
│   └── send_selfie.py
│
├── memory/                ← 记忆系统
│   ├── lt_interface.py    ← 对外接口（命令行）
│   └── admin/             ← 管理面板
│
├── prompts/               ← 系统提示词（setup.bat 后路径自动配置）
├── data/                  ← 运行时数据、日志、数据库
├── assets/                ← 语音模型、LoRA、参考图
└── scripts/               ← 辅助脚本（open_memory、voice API、开机自启）
```
