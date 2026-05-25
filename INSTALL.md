# 安装指南

## 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 主运行环境 |
| [Claude Code CLI](https://github.com/anthropics/claude-code) | 最新版 | 驱动 AI 回复和 Life Tick |
| Telegram Bot Token | — | 从 [@BotFather](https://t.me/BotFather) 获取 |
| Git Bash（Windows） | — | Claude Code 运行所需 |

语音功能（可选）还需要 GPT-SoVITS 推理服务，默认关闭。

---

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/vichenxi/Yuki_Bot.git
cd Yuki_Bot
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

复制示例配置文件并填入真实值：

```bash
cp config.example.json config.json
```

编辑 `config.json`，必填项：

```json
{
  "bot_token": "从 BotFather 获取的 Token",
  "default_chat_id": "你的 Telegram Chat ID",
  "llm": {
    "provider": "claude",
    "model": "claude-sonnet-4-6",
    "api_key": ""
  }
}
```

> **provider 说明**：使用 `"claude"` 时 `api_key` 留空，由 Claude Code CLI 登录态驱动；使用其他 provider 时填入对应 API Key。

### 4. 初始化数据库

```bash
# Windows
memory\init_and_migrate.bat

# 或直接运行
python memory/migrate.py
```

这会在 `data/` 目录下创建 `memory.db`。

### 5. 登录 Claude Code

```bash
claude login
```

按提示完成浏览器授权。

### 6. 启动 Bot

```bash
# Windows 一键启动
start.bat

# 或手动启动各守护进程
python core/tg_daemon.py       # Telegram 消息收发
python core/claude_monitor.py  # 自动调用 Claude Code
```

---

## 目录结构

```
Yuki_Bot/
├── core/               # 守护进程（tg_daemon, lt_daemon, claude_monitor...）
├── memory/             # 记忆系统（DB、向量检索、提取、管理面板）
├── prompts/            # 各阶段 Prompt 模板
├── assets/
│   ├── pose_skeletons/ # 姿势骨骼参考图
│   ├── samples/        # 角色图像样本
│   ├── voice_models/   # 语音模型（不含，见下）
│   └── lora/           # LoRA 权重（不含，见下）
├── scripts/            # 启动脚本、工具脚本
├── config.example.json # 配置模板
└── requirements.txt
```

---

## 可选功能

### 语音发送

需要本地运行 GPT-SoVITS 推理服务，并将语音模型（`.ckpt` / `.pth`）放入 `assets/voice_models/`，然后在 `config.json` 中填写对应路径和 `gptsovits_api` 地址。

### 图像生成（Selfie）

需要 Stable Diffusion WebUI，在 `config.json` 的 `sd_model_path` 填入模型绝对路径。LoRA 权重放入 `assets/lora/`。

### 记忆管理面板

```bash
memory\start_admin.bat
# 访问 http://localhost:8765
```

---

## 常见问题

**Q: claude_monitor 报找不到 claude**
确认已安装 Claude Code CLI 且 `claude` 命令在 PATH 中：`claude --version`

**Q: 数据库初始化失败**
确认 `data/` 目录存在，或手动创建：`mkdir data`

**Q: Telegram 收不到消息**
检查 `bot_token` 和 `default_chat_id` 是否正确，确认 bot 已被添加到目标对话。
