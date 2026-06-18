"""Generate tech-stack PDF via Playwright."""
import base64, sys, tempfile
from pathlib import Path

HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
    color: #2d2d2d;
    line-height: 1.75;
    background: #fff;
  }

  /* ── 封面 ── */
  .cover {
    height: 100vh;
    background: linear-gradient(135deg, #1a0533 0%, #3b0764 50%, #6d28d9 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    page-break-after: always;
    text-align: center;
    padding: 60px;
  }
  .cover .tag {
    background: rgba(167,139,250,0.25);
    border: 1px solid rgba(167,139,250,0.5);
    border-radius: 20px;
    padding: 4px 16px;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 32px;
    color: #c4b5fd;
  }
  .cover h1 {
    font-size: 48px;
    font-weight: 700;
    letter-spacing: -1px;
    margin-bottom: 8px;
    background: linear-gradient(90deg, #fff 0%, #c4b5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .cover h2 {
    font-size: 20px;
    font-weight: 300;
    color: #ddd6fe;
    margin-bottom: 48px;
  }
  .cover .subtitle {
    font-size: 13px;
    color: #a78bfa;
    max-width: 480px;
    line-height: 1.9;
  }
  .cover .meta {
    position: absolute;
    bottom: 48px;
    font-size: 11px;
    color: #7c3aed;
    letter-spacing: 1px;
  }

  /* ── 目录 ── */
  .toc-page {
    padding: 60px 72px;
    page-break-after: always;
  }
  .toc-page h2 { font-size: 22px; color: #6d28d9; margin-bottom: 32px; font-weight: 700; }
  .toc-item {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 1px dashed #e5e7eb;
    font-size: 13px;
  }
  .toc-num {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #ede9fe;
    color: #7c3aed;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .toc-title { flex: 1; color: #374151; }
  .toc-sub {
    font-size: 11px;
    color: #9ca3af;
    margin-left: 36px;
    padding: 2px 0;
  }

  /* ── 正文页面 ── */
  .page {
    padding: 56px 72px;
    page-break-before: always;
  }

  /* ── 章节标题 ── */
  .chapter-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 32px;
    padding-bottom: 16px;
    border-bottom: 2px solid #ede9fe;
  }
  .chapter-num {
    width: 42px;
    height: 42px;
    border-radius: 10px;
    background: linear-gradient(135deg, #7c3aed, #a78bfa);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .chapter-title { font-size: 22px; font-weight: 700; color: #1f2937; }
  .chapter-desc { font-size: 12px; color: #9ca3af; margin-top: 2px; }

  h3 {
    font-size: 15px;
    font-weight: 700;
    color: #4c1d95;
    margin: 28px 0 12px;
    padding-left: 10px;
    border-left: 3px solid #7c3aed;
  }
  h4 {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin: 20px 0 8px;
  }
  p { margin-bottom: 12px; color: #374151; }

  /* ── Callout 框 ── */
  .callout {
    background: #f5f3ff;
    border: 1px solid #ddd6fe;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 16px 0;
    font-size: 12px;
    color: #4c1d95;
  }
  .callout strong { color: #6d28d9; }
  .callout.tip { background: #ecfdf5; border-color: #6ee7b7; border-left-color: #10b981; color: #065f46; }
  .callout.tip strong { color: #059669; }
  .callout.warn { background: #fffbeb; border-color: #fcd34d; border-left-color: #f59e0b; color: #78350f; }

  /* ── 代码块 ── */
  pre {
    background: #1e1b4b;
    color: #c4b5fd;
    border-radius: 8px;
    padding: 16px 20px;
    font-size: 11px;
    line-height: 1.8;
    margin: 12px 0;
    overflow-x: auto;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  }
  code {
    background: #ede9fe;
    color: #6d28d9;
    padding: 1px 5px;
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
  }
  pre code { background: none; color: inherit; padding: 0; }

  /* ── 表格 ── */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 12px;
  }
  th {
    background: #ede9fe;
    color: #4c1d95;
    font-weight: 600;
    padding: 10px 14px;
    text-align: left;
    border: 1px solid #ddd6fe;
  }
  td {
    padding: 9px 14px;
    border: 1px solid #e5e7eb;
    vertical-align: top;
    color: #374151;
  }
  tr:nth-child(even) td { background: #faf9ff; }

  /* ── 架构图（ASCII 风格） ── */
  .arch {
    background: #0f0a1e;
    color: #a78bfa;
    border-radius: 8px;
    padding: 20px 24px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
    line-height: 1.9;
    margin: 16px 0;
  }
  .arch .hl { color: #fbbf24; }
  .arch .dim { color: #4c3d6b; }
  .arch .green { color: #34d399; }

  /* ── 技术徽章 ── */
  .badge-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
  .badge {
    background: #ede9fe;
    color: #5b21b6;
    border: 1px solid #c4b5fd;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 500;
  }
  .badge.green { background: #ecfdf5; color: #065f46; border-color: #6ee7b7; }
  .badge.blue  { background: #eff6ff; color: #1e40af; border-color: #93c5fd; }
  .badge.amber { background: #fffbeb; color: #78350f; border-color: #fcd34d; }

  /* ── 流程步骤 ── */
  .steps { margin: 16px 0; }
  .step {
    display: flex;
    gap: 14px;
    margin-bottom: 14px;
  }
  .step-num {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #7c3aed;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .step-body { flex: 1; }
  .step-body strong { color: #4c1d95; }

  /* ── 分隔线 ── */
  hr { border: none; border-top: 1px solid #ede9fe; margin: 24px 0; }

  /* ── 页脚 ── */
  @page {
    margin: 0;
    size: A4;
  }
</style>
</head>
<body>

<!-- ════════════════ 封面 ════════════════ -->
<div class="cover">
  <div class="tag">Technical Documentation</div>
  <h1>雪 (Yuki) Bot</h1>
  <h2>完整技术栈文档</h2>
  <div class="subtitle">
    面向初学者的技术解析<br>
    从 Telegram Bot 到 3D VRM 渲染、记忆系统到 LoRA 训练的全栈图解
  </div>
  <div class="meta">2026 · yukibot · F:\bot</div>
</div>

<!-- ════════════════ 目录 ════════════════ -->
<div class="toc-page">
  <h2>目录</h2>
  <div class="toc-item">
    <div class="toc-num">1</div>
    <div class="toc-title">项目是什么 — 整体概述</div>
  </div>
  <div class="toc-item">
    <div class="toc-num">2</div>
    <div class="toc-title">Telegram Bot 核心</div>
  </div>
  <div class="toc-sub">tg_daemon / handle_reply / lt_daemon / claude_monitor</div>
  <div class="toc-item">
    <div class="toc-num">3</div>
    <div class="toc-title">AI / LLM 接入层</div>
  </div>
  <div class="toc-sub">Claude CLI、多后端统一客户端、提示词工程</div>
  <div class="toc-item">
    <div class="toc-num">4</div>
    <div class="toc-title">记忆系统</div>
  </div>
  <div class="toc-sub">SQLite 数据库、向量检索、热度衰减、Dream 整合</div>
  <div class="toc-item">
    <div class="toc-num">5</div>
    <div class="toc-title">管理面板（Web UI）</div>
  </div>
  <div class="toc-sub">FastAPI 后端、前端 Bundle、REST API</div>
  <div class="toc-item">
    <div class="toc-num">6</div>
    <div class="toc-title">3D VRM 模型 & 渲染</div>
  </div>
  <div class="toc-sub">Three.js、@pixiv/three-vrm、Idle 动画、无头渲染</div>
  <div class="toc-item">
    <div class="toc-num">7</div>
    <div class="toc-title">桌面应用（Electron）</div>
  </div>
  <div class="toc-item">
    <div class="toc-num">8</div>
    <div class="toc-title">图像生成 & LoRA 训练</div>
  </div>
  <div class="toc-sub">Stable Diffusion、kohya-ss sd-scripts、训练流水线</div>
  <div class="toc-item">
    <div class="toc-num">9</div>
    <div class="toc-title">语音合成（GPT-SoVITS）</div>
  </div>
  <div class="toc-item">
    <div class="toc-num">10</div>
    <div class="toc-title">技术栈全览 & 数据流</div>
  </div>
</div>

<!-- ════════════════ 第 1 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">1</div>
    <div>
      <div class="chapter-title">项目是什么 — 整体概述</div>
      <div class="chapter-desc">一个运行在 Windows 上的 AI 陪伴 Bot</div>
    </div>
  </div>

  <p>雪 Bot 是一个运行在本地 Windows PC 上的 AI 陪伴系统。它通过 Telegram 与用户聊天，有自己的长期记忆、定时主动发消息、语音回复、3D 模型显示和生图能力。</p>

  <div class="callout">
    <strong>对初学者的比喻：</strong>把它想象成一个住在你电脑里的虚拟角色。她记得你们聊过的事，会自己想起来给你发消息，还有 3D 形象可以看。
  </div>

  <h3>项目目录结构</h3>
  <div class="arch">
<span class="hl">F:\bot\</span>                   ← 主代码仓库
<span class="green">├── core/</span>              ← Bot 运行时（Python）
<span class="green">├── memory/</span>            ← 记忆系统 + 后台服务
<span class="green">│   └── admin/</span>         ← Web 管理面板
<span class="green">├── desktop/</span>           ← 桌面 Electron 应用
<span class="green">├── lora/</span>              ← LoRA 训练流水线
<span class="green">├── prompts/</span>           ← AI 任务提示词（7个）
<span class="green">├── assets/</span>            ← 模型权重、语音资源
<span class="green">├── data/</span>              ← 运行时数据库和日志
<span class="dim">└── character.txt</span>      ← 角色人设（唯一需要改的文件）</div>

  <h3>五大核心能力</h3>
  <table>
    <tr><th>能力</th><th>做什么</th><th>用到的技术</th></tr>
    <tr><td>💬 聊天回复</td><td>接收 Telegram 消息，用 AI 生成回复</td><td>Python、Claude API、Telegram Bot API</td></tr>
    <tr><td>🧠 长期记忆</td><td>记住聊过的事、情绪、约定</td><td>SQLite、向量数据库、sentence-transformers</td></tr>
    <tr><td>🕐 主动消息</td><td>定时自己发消息（不等对方先说）</td><td>Claude CLI、文件信号机制</td></tr>
    <tr><td>🎤 语音回复</td><td>将文字转成角色声音发送</td><td>GPT-SoVITS</td></tr>
    <tr><td>🖼 图像 / 3D</td><td>3D 模型展示、AI 生图</td><td>Three.js、Stable Diffusion、LoRA</td></tr>
  </table>
</div>

<!-- ════════════════ 第 2 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">2</div>
    <div>
      <div class="chapter-title">Telegram Bot 核心</div>
      <div class="chapter-desc">三进程架构 — 每个进程只做一件事</div>
    </div>
  </div>

  <p>Bot 核心由四个 Python 脚本组成，它们<strong>并行运行</strong>，通过写/读本地 JSON 文件来传递任务，互不干扰。</p>

  <div class="callout">
    <strong>为什么这样设计？</strong>任何一个进程崩溃都不影响其他两个。tg_daemon 崩了不影响主动消息，lt_daemon 崩了不影响回复聊天。
  </div>

  <h3>消息回复流程</h3>
  <div class="arch">
薰发来消息
    │
    ▼
<span class="hl">tg_daemon.py</span>  ← 每 30 秒轮询 Telegram API
    │  发现新消息
    │  写入 <span class="green">data/pending_reply.json</span>
    │  直接启动 handle_reply.py
    ▼
<span class="hl">handle_reply.py</span>
    ├── 读记忆（lt_interface.py）
    ├── 调 LLM API → 生成回复文字
    ├── 调 GPT-SoVITS → 生成语音（可选）
    ├── 发 Telegram 消息
    └── 写回忆（存对话记录）
    │
    ▼
<span class="dim">删除 pending_reply.json → 完成</span></div>

  <h3>Life Tick — 主动消息流程</h3>
  <p>"Life Tick" 是雪<strong>自己决定要不要给你发消息</strong>的机制，每 15–45 分钟触发一次。</p>
  <div class="arch">
<span class="hl">lt_daemon.py</span>  ← 计时器（每 15~45 分钟）
    │  到时间后写入 <span class="green">data/pending_tick.json</span>
    ▼
<span class="hl">claude_monitor.py</span>  ← 监视 data/ 目录的文件变化
    │  发现 pending_tick.json
    │  执行 <span class="green">claude -p lifetick_prompt.txt</span>
    ▼
Claude 读取 character.txt + 记忆
    ├── 决策：现在要不要发消息？
    ├── 如果发：生成内容并发 Telegram
    └── 写 <span class="green">data/next_tick.json</span>（下次时间）</div>

  <h3>四个脚本的职责</h3>
  <table>
    <tr><th>脚本</th><th>类型</th><th>职责</th></tr>
    <tr><td><code>tg_daemon.py</code></td><td>常驻进程</td><td>轮询 Telegram，发现消息就写信号文件</td></tr>
    <tr><td><code>handle_reply.py</code></td><td>回复引擎</td><td>读消息→查记忆→调 AI→发回复→存记录</td></tr>
    <tr><td><code>lt_daemon.py</code></td><td>常驻进程</td><td>纯计时器，到点写信号文件</td></tr>
    <tr><td><code>claude_monitor.py</code></td><td>常驻进程</td><td>监控文件变化，调度所有 AI 任务</td></tr>
  </table>

  <div class="callout tip">
    <strong>信号文件机制：</strong>进程之间不通过网络或共享内存通信，而是通过创建/删除 JSON 文件来传递"任务"。这种设计极其简单可靠，任何文本编辑器都能看到系统当前在做什么。
  </div>
</div>

<!-- ════════════════ 第 3 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">3</div>
    <div>
      <div class="chapter-title">AI / LLM 接入层</div>
      <div class="chapter-desc">支持 6 种 AI 后端的统一客户端</div>
    </div>
  </div>

  <h3>什么是 LLM？</h3>
  <p>LLM（Large Language Model，大语言模型）是让 Bot 能"理解"和"生成"文字的核心 AI。雪 Bot 支持多种 LLM 后端，可以在配置文件里切换。</p>

  <h3>支持的 AI 后端</h3>
  <table>
    <tr><th>后端</th><th>代表模型</th><th>特点</th><th>需要什么</th></tr>
    <tr><td>Claude</td><td>claude-sonnet-4-6</td><td>推荐，JSON 输出最稳定</td><td>Claude CLI 登录</td></tr>
    <tr><td>OpenAI</td><td>gpt-4o</td><td>通用，效果好</td><td>API Key（付费）</td></tr>
    <tr><td>DeepSeek</td><td>deepseek-chat</td><td>中文能力强，价格低</td><td>API Key</td></tr>
    <tr><td>Gemini</td><td>gemini-2.0-flash</td><td>速度快</td><td>API Key</td></tr>
    <tr><td>Ollama</td><td>llama3、qwen2.5</td><td>完全本地，无需联网</td><td>本地 GPU</td></tr>
    <tr><td>Custom</td><td>任意模型</td><td>兼容 OpenAI API 格式的任何服务</td><td>自定义 URL</td></tr>
  </table>

  <h3>Claude CLI 的工作方式</h3>
  <p>雪 Bot 的主要 AI 调用方式是 <code>claude -p 提示词文件.txt</code>，这是 Anthropic 官方的命令行工具：</p>
  <div class="arch">
<span class="dim"># 不是直接调 API，而是调 claude 命令行工具</span>
claude -p lifetick_prompt.txt

<span class="dim"># claude 会：</span>
1. 读取 lifetick_prompt.txt 的内容作为系统提示
2. 让 AI 执行里面描述的任务（读文件、写文件、调工具）
3. 返回结果</div>

  <h3>提示词工程 — 7 个任务文件</h3>
  <p>Bot 的"大脑逻辑"不是写在代码里的，而是写在这 7 个提示词文件里：</p>
  <table>
    <tr><th>文件</th><th>什么时候用</th><th>做什么</th></tr>
    <tr><td><code>reply_prompt.txt</code></td><td>每条消息</td><td>完整回复流程：读记忆→生成→发送→存储</td></tr>
    <tr><td><code>lifetick_prompt.txt</code></td><td>每次 Tick</td><td>决策是否主动发消息，写生活日志</td></tr>
    <tr><td><code>wakeup_prompt.txt</code></td><td>每天早上</td><td>处理睡觉期间积压的未读消息</td></tr>
    <tr><td><code>lt_selfcheck_prompt.txt</code></td><td>每次回复后</td><td>检查计时系统是否正常运行</td></tr>
    <tr><td><code>recovery_prompt.txt</code></td><td>开机时</td><td>补全离线期间缺失的记录，恢复进程</td></tr>
    <tr><td><code>archive_prompt.txt</code></td><td>手动触发</td><td>整理归档对话</td></tr>
    <tr><td><code>diary_prompt.txt</code></td><td>手动触发</td><td>生成角色视角的日记</td></tr>
  </table>

  <div class="callout">
    <strong>设计理念：</strong>把 AI 逻辑放在提示词文件里而不是代码里，意味着你可以在不改一行 Python 代码的情况下，完全改变 Bot 的行为——只需编辑文本文件。
  </div>
</div>

<!-- ════════════════ 第 4 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">4</div>
    <div>
      <div class="chapter-title">记忆系统</div>
      <div class="chapter-desc">让 Bot 真正"记住"事情的技术实现</div>
    </div>
  </div>

  <h3>为什么需要记忆系统？</h3>
  <p>普通 AI 对话是无状态的——每次对话结束，AI 就"忘了"所有内容。雪 Bot 通过专门的记忆系统，让她能记住你们聊过的事，就像真实的人际关系。</p>

  <h3>数据库结构（SQLite）</h3>
  <p>所有数据存在一个 SQLite 文件里（<code>data/memory.db</code>），SQLite 就是一个存在单个文件里的轻量数据库，不需要单独安装服务器：</p>
  <table>
    <tr><th>数据表</th><th>存什么</th><th>示例</th></tr>
    <tr><td><code>memories</code></td><td>长期记忆片段</td><td>"薰不喜欢甜的"、"答应见面做番茄炒蛋"</td></tr>
    <tr><td><code>conversations</code></td><td>所有对话记录</td><td>每条消息的内容、时间、情绪</td></tr>
    <tr><td><code>life_logs</code></td><td>生活日志</td><td>每次 Tick 的活动、心情、是否发消息</td></tr>
    <tr><td><code>calendar_pages</code></td><td>日程记忆</td><td>重要事件、约定</td></tr>
    <tr><td><code>dream_logs</code></td><td>记忆整合记录</td><td>Dream 系统的运行历史</td></tr>
    <tr><td><code>config</code></td><td>系统配置</td><td>各种调节参数</td></tr>
  </table>

  <h3>向量检索 — 怎么找到"相关"记忆</h3>
  <p>存了几百条记忆后，如何快速找到"和当前话题最相关"的记忆？答案是<strong>向量检索</strong>：</p>
  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-body"><strong>文字 → 数字向量</strong>：每条记忆存入时，用 <code>BAAI/bge-small-zh-v1.5</code> 模型把文字转成 512 个数字组成的向量（代表语义）</div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-body"><strong>查询时同样转换</strong>：当前对话内容也转成向量</div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div class="step-body"><strong>计算余弦相似度</strong>：向量越接近，语义越相似，返回最相关的 15 条记忆</div>
    </div>
  </div>
  <div class="callout tip">
    <strong>为什么用中文专用模型？</strong>BAAI/bge-small-zh-v1.5 是专门针对中文优化的嵌入模型，只有 90MB，能在 CPU 上快速运行，不需要 GPU。
  </div>

  <h3>热度衰减系统</h3>
  <p>并非所有记忆都一直重要。就像人类记忆一样，雪 Bot 的记忆有"热度"概念：</p>
  <table>
    <tr><th>类型</th><th>热度半衰期</th><th>说明</th></tr>
    <tr><td>普通记忆</td><td>3 天</td><td>不被访问的话，3 天后热度降一半</td></tr>
    <tr><td>重要记忆</td><td>7 天</td><td>重要性 ≥7 分的记忆衰减更慢</td></tr>
    <tr><td>永久记忆</td><td>不衰减</td><td>被标记为 permanent 的核心记忆</td></tr>
    <tr><td>被访问</td><td>热度延长</td><td>每次被检索到，热度会回升</td></tr>
  </table>

  <h3>Dream 记忆整合</h3>
  <p>当碎片记忆积累超过 30 条，Dream 系统会被触发：让 AI 阅读所有碎片，合并、归纳成结构化的长期记忆——类比人类睡眠时大脑整理记忆。</p>
</div>

<!-- ════════════════ 第 5 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">5</div>
    <div>
      <div class="chapter-title">管理面板（Web UI）</div>
      <div class="chapter-desc">用浏览器管理 Bot 的一切</div>
    </div>
  </div>

  <h3>管理面板是什么？</h3>
  <p>管理面板是一个跑在本地的网页应用，地址是 <code>http://127.0.0.1:8765</code>。用浏览器打开就能看到 Bot 的所有数据，不需要懂命令行。</p>

  <h3>后端：FastAPI</h3>
  <p>FastAPI 是一个 Python Web 框架，负责处理前端的请求，读写数据库：</p>
  <div class="arch">
浏览器 <span class="dim">(index.html)</span>
    │  HTTP 请求
    ▼
<span class="hl">FastAPI server.py</span>  :8765
    ├── GET  /memories        → 查询记忆列表
    ├── POST /memories        → 添加记忆
    ├── GET  /memories/search → 语义搜索
    ├── GET  /status          → 今日状态
    ├── GET  /conversations   → 对话历史
    ├── GET  /model/vrm       → 提供 VRM 3D 模型文件
    └── GET  /vrm-viewer      → VRM 查看器页面</div>

  <h3>VRM 查看器（新功能）</h3>
  <p>管理面板首页内嵌了一个 3D 模型查看器——你可以直接在浏览器里旋转查看雪的 3D 形象：</p>
  <div class="callout">
    <strong>实现方式：</strong>一个独立的 HTML 页面（<code>vrm_viewer.html</code>）通过 <code>iframe</code> 嵌入到管理面板首页，用 Three.js 加载 VRM 文件并渲染，带有呼吸动画和随机眨眼效果。
  </div>

  <h3>前端技术</h3>
  <div class="badge-row">
    <span class="badge">FastAPI</span>
    <span class="badge">Uvicorn（ASGI服务器）</span>
    <span class="badge blue">Three.js</span>
    <span class="badge blue">@pixiv/three-vrm</span>
    <span class="badge green">SQLite</span>
    <span class="badge amber">Pydantic（数据验证）</span>
  </div>
</div>

<!-- ════════════════ 第 6 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">6</div>
    <div>
      <div class="chapter-title">3D VRM 模型 & 渲染</div>
      <div class="chapter-desc">在浏览器里实时渲染的 3D 角色</div>
    </div>
  </div>

  <h3>什么是 VRM？</h3>
  <p>VRM 是一种专门为虚拟角色设计的 3D 模型格式（基于 glTF），广泛用于 VTuber 和虚拟形象。它包含：3D 网格、骨骼绑定、材质、表情、物理弹簧等。</p>

  <h3>Three.js — 在浏览器里画 3D</h3>
  <p>Three.js 是一个 JavaScript 库，让你在浏览器里用 WebGL 渲染 3D 场景，不需要安装任何插件：</p>
  <table>
    <tr><th>概念</th><th>解释</th><th>类比</th></tr>
    <tr><td>Scene</td><td>3D 场景容器</td><td>舞台</td></tr>
    <tr><td>Camera</td><td>观察视角</td><td>摄像机</td></tr>
    <tr><td>Renderer</td><td>WebGL 渲染器</td><td>把场景画到屏幕上</td></tr>
    <tr><td>Mesh</td><td>3D 物体</td><td>演员</td></tr>
    <tr><td>Light</td><td>光源</td><td>打光</td></tr>
    <tr><td>OrbitControls</td><td>鼠标控制旋转</td><td>导演转镜头</td></tr>
  </table>

  <h3>Idle 动画系统</h3>
  <p>让 3D 模型自然"活着"——不是播放预录的动画，而是用数学公式实时计算：</p>
  <pre><code>// 呼吸：多个不同频率的正弦波叠加
const breath = sin(t × 0.78) × 0.013    // 主呼吸频率
             + sin(t × 1.56) × 0.003    // 二次谐波
             + sin(t × 0.31) × 0.005    // 低频起伏

// 应用到骨骼：胸腔随呼吸起伏
chest.rotation.x = breath × 0.55

// 随机眨眼：状态机
wait → closing (70ms) → opening (120ms) → wait (3~7秒后再眨)</code></pre>

  <h3>无头渲染（vrm_render.py）</h3>
  <p>用于生成 LoRA 训练数据时，需要在没有显示器的情况下截图。解决方案：</p>
  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-body">Playwright 启动一个<strong>无界面 Chromium 浏览器</strong></div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-body">加载包含 Three.js + VRM 渲染代码的 HTML 页面</div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div class="step-body">等待渲染完成，读取 <code>canvas.toDataURL()</code> 获取 base64 图片</div>
    </div>
    <div class="step">
      <div class="step-num">4</div>
      <div class="step-body">解码 base64，保存为 PNG 文件</div>
    </div>
  </div>

  <div class="callout tip">
    <strong>巧妙之处：</strong>用浏览器来渲染 3D，意味着不需要安装 OpenGL、DirectX 等复杂图形库——Chromium 自带 WebGL 支持，跨平台。
  </div>
</div>

<!-- ════════════════ 第 7 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">7</div>
    <div>
      <div class="chapter-title">桌面应用（Electron）</div>
      <div class="chapter-desc">用 Web 技术构建的原生桌面窗口</div>
    </div>
  </div>

  <h3>Electron 是什么？</h3>
  <p>Electron 让你用 HTML/CSS/JavaScript（网页技术）来写桌面应用程序。VS Code、Discord 都用 Electron 构建。</p>

  <div class="arch">
<span class="hl">Electron</span>
├── <span class="green">主进程 (main.js)</span>      ← Node.js 环境，可访问文件系统、系统托盘
└── <span class="green">渲染进程 (renderer/)</span>  ← Chromium，显示网页内容
    ├── app.js          ← Three.js 3D 场景
    └── editor.html     ← Pose 编辑器</div>

  <h3>桌面窗口特性</h3>
  <table>
    <tr><th>参数</th><th>值</th><th>效果</th></tr>
    <tr><td>尺寸</td><td>380 × 640</td><td>竖屏，类似手机比例</td></tr>
    <tr><td>transparent</td><td>true</td><td>窗口背景透明</td></tr>
    <tr><td>frame</td><td>false</td><td>无标题栏、无边框</td></tr>
    <tr><td>alwaysOnTop</td><td>true</td><td>始终显示在最前面</td></tr>
    <tr><td>resizable</td><td>false</td><td>固定大小</td></tr>
  </table>

  <div class="callout">
    <strong>效果：</strong>一个透明无边框、始终置顶的 3D 角色窗口，悬浮在桌面右侧，不挡其他窗口，像桌宠一样。
  </div>

  <h3>依赖管理（Node.js / npm）</h3>
  <div class="badge-row">
    <span class="badge blue">electron</span>
    <span class="badge blue">three.js r167</span>
    <span class="badge blue">@pixiv/three-vrm 2.1.2</span>
  </div>
</div>

<!-- ════════════════ 第 8 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">8</div>
    <div>
      <div class="chapter-title">图像生成 & LoRA 训练</div>
      <div class="chapter-desc">从 VRM 模型到 AI 生成图像的完整流水线</div>
    </div>
  </div>

  <h3>Stable Diffusion 是什么？</h3>
  <p>Stable Diffusion（SD）是一个开源的 AI 图像生成模型，输入文字描述，输出图像。雪 Bot 用它生成角色图像发送给用户。</p>

  <h3>LoRA — 教 SD "认识"一个特定角色</h3>
  <p>SD 默认不知道"雪"长什么样。LoRA（Low-Rank Adaptation）是一种在不修改原始模型的情况下，让模型学会新知识的微调技术：</p>
  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-body"><strong>准备训练数据</strong>：用 VRM 模型渲染 11 张不同角度的图片，每张配一个描述标签（caption）</div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-body"><strong>训练</strong>：让 SD 模型对比"正确图像"和"它生成的图像"的差距，调整一小部分参数</div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div class="step-body"><strong>输出</strong>：一个 ~37MB 的 <code>.safetensors</code> 文件，存储了角色外观的"特征偏移量"</div>
    </div>
    <div class="step">
      <div class="step-num">4</div>
      <div class="step-body"><strong>使用</strong>：生图时加上 <code>&lt;lora:yuki_lora_v1:0.8&gt;</code>，SD 就会把这些特征叠加到生成结果上</div>
    </div>
  </div>

  <div class="callout tip">
    <strong>为什么从 VRM 渲染训练数据？</strong>VRM 是 3D 模型，可以随时生成任意角度、任意姿势的图，不需要手动画参考图。而且外观完全一致，不存在风格差异。
  </div>

  <h3>训练流水线（lora/ 目录）</h3>
  <div class="arch">
<span class="hl">lora/1_setup.ps1</span>  ← 首次运行，克隆 kohya-ss/sd-scripts
    │
<span class="hl">lora/gen_data.py</span>  ← 调 vrm_render.py，渲染 11 张训练图
    │  输出到 data/yuki_lora/img/20_yukixue/
    │  自动生成对应的 caption .txt 文件
    │
<span class="hl">sd-scripts/train_network.py</span>  ← kohya 训练脚本
    │  底模：Realistic Vision V5.1 fp16
    │  30 epochs，batch_size=2，network_dim=32
    │  GPU：RTX 4070 12GB，fp16 精度
    ▼
<span class="green">data/lora/output/yuki_lora_v1.safetensors</span>  ← 成品</div>

  <h3>关键训练参数解释</h3>
  <table>
    <tr><th>参数</th><th>值</th><th>含义</th></tr>
    <tr><td>network_dim</td><td>32</td><td>LoRA 的"容量"，越大学得越多也越容易过拟合</td></tr>
    <tr><td>network_alpha</td><td>16</td><td>学习强度缩放，通常是 dim 的一半</td></tr>
    <tr><td>num_repeats</td><td>20</td><td>每张图重复 20 次，弥补训练数据少的问题</td></tr>
    <tr><td>clip_skip</td><td>2</td><td>跳过最后 1 层文字编码，Realistic Vision 的标准设置</td></tr>
    <tr><td>mixed_precision</td><td>fp16</td><td>半精度浮点数，节省 VRAM，速度更快</td></tr>
    <tr><td>cache_latents</td><td>true</td><td>缓存图片的潜空间编码，不用每步重算</td></tr>
  </table>
</div>

<!-- ════════════════ 第 9 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">9</div>
    <div>
      <div class="chapter-title">语音合成（GPT-SoVITS）</div>
      <div class="chapter-desc">让雪用自己的声音说话</div>
    </div>
  </div>

  <h3>GPT-SoVITS 是什么？</h3>
  <p>GPT-SoVITS 是一个开源的语音合成系统，只需要几秒钟的参考音频，就能克隆对应的音色，生成任意文字的语音。</p>

  <h3>工作流程</h3>
  <div class="arch">
<span class="hl">handle_reply.py</span>  生成回复文字
    │
    ▼
<span class="hl">send_voice.py</span>
    │  POST http://127.0.0.1:9880/tts
    │  {
    │    text: "要合成的文字",
    │    ref_audio: "assets/voice_ref/任命助理.wav",
    │    ref_text: "参考音频对应的文字"
    │  }
    ▼
<span class="hl">GPT-SoVITS API</span>  (start_voice_api.bat 启动)
    │  加载模型权重
    │  → GPT 模型 (42-e15.ckpt)：文字→音素序列
    │  → SoVITS 模型 (42_e8_s152.pth)：音素→音频波形
    ▼
返回 .wav 音频文件
    │
    ▼
Telegram sendVoice  → 发送语音消息</div>

  <h3>模型文件</h3>
  <table>
    <tr><th>文件</th><th>大小</th><th>作用</th></tr>
    <tr><td><code>42-e15.ckpt</code></td><td>~400MB</td><td>GPT 模型，将文字转为音素序列（决定节奏、停顿）</td></tr>
    <tr><td><code>42_e8_s152.pth</code></td><td>~100MB</td><td>SoVITS 模型，将音素转为音频波形（决定音色）</td></tr>
    <tr><td><code>任命助理.wav</code></td><td>几秒钟</td><td>参考音频，用来确定要克隆的音色</td></tr>
  </table>

  <div class="callout warn">
    <strong>注意：</strong>语音功能是可选的。如果不启动 GPT-SoVITS（<code>scripts/start_voice_api.bat</code>），Bot 会静默跳过语音合成步骤，只发文字消息。
  </div>
</div>

<!-- ════════════════ 第 10 章 ════════════════ -->
<div class="page">
  <div class="chapter-header">
    <div class="chapter-num">10</div>
    <div>
      <div class="chapter-title">技术栈全览 & 数据流</div>
      <div class="chapter-desc">把所有东西串起来看</div>
    </div>
  </div>

  <h3>完整技术栈</h3>
  <table>
    <tr><th>层次</th><th>技术</th><th>版本</th><th>用途</th></tr>
    <tr><td rowspan="3">AI / LLM</td><td>Claude</td><td>sonnet-4-6</td><td>主要对话与决策 AI</td></tr>
    <tr><td>BAAI/bge-small-zh-v1.5</td><td>—</td><td>记忆向量化（本地）</td></tr>
    <tr><td>sentence-transformers</td><td>—</td><td>向量计算库</td></tr>
    <tr><td rowspan="2">图像生成</td><td>Stable Diffusion 1.5</td><td>—</td><td>底模</td></tr>
    <tr><td>kohya-ss/sd-scripts</td><td>—</td><td>LoRA 训练框架</td></tr>
    <tr><td rowspan="3">3D 渲染</td><td>Three.js</td><td>r167</td><td>WebGL 3D 渲染</td></tr>
    <tr><td>@pixiv/three-vrm</td><td>2.1.2</td><td>VRM 模型解析</td></tr>
    <tr><td>Playwright</td><td>1.60</td><td>无头浏览器渲染</td></tr>
    <tr><td rowspan="2">数据存储</td><td>SQLite</td><td>—</td><td>记忆数据库</td></tr>
    <tr><td>JSON 文件</td><td>—</td><td>状态信号、配置</td></tr>
    <tr><td rowspan="2">后端服务</td><td>FastAPI</td><td>—</td><td>Web 管理面板 API</td></tr>
    <tr><td>Uvicorn</td><td>—</td><td>ASGI 服务器</td></tr>
    <tr><td>桌面应用</td><td>Electron</td><td>—</td><td>透明置顶桌面窗口</td></tr>
    <tr><td>消息平台</td><td>Telegram Bot API</td><td>—</td><td>与用户通信</td></tr>
    <tr><td>语音合成</td><td>GPT-SoVITS</td><td>—</td><td>文字转角色语音</td></tr>
    <tr><td rowspan="2">运行环境</td><td>Python 3.10</td><td>Conda (sd env)</td><td>后端运行环境</td></tr>
    <tr><td>Node.js / npm</td><td>—</td><td>桌面应用运行环境</td></tr>
    <tr><td>GPU</td><td>NVIDIA RTX 4070</td><td>12GB VRAM</td><td>LoRA 训练、SD 生图</td></tr>
  </table>

  <h3>完整数据流图</h3>
  <div class="arch">
<span class="dim">─────────────── 用户侧 ───────────────</span>
薰 (Telegram 手机)
    │
    ▼ 消息
<span class="hl">tg_daemon.py</span> ──写──▶ pending_reply.json
    │
    ▼ 启动
<span class="hl">handle_reply.py</span>
    ├──读──▶ <span class="green">memory.db</span>（历史 + 相关记忆）
    ├──调──▶ <span class="green">Claude API</span>（生成回复）
    ├──调──▶ <span class="green">GPT-SoVITS :9880</span>（生成语音）
    ├──发──▶ <span class="green">Telegram API</span>（发送）
    └──写──▶ <span class="green">memory.db</span>（存对话 + 生活日志）

<span class="dim">─────────────── 自主侧 ───────────────</span>
<span class="hl">lt_daemon.py</span> ──写──▶ pending_tick.json
    │
    ▼ 检测到文件
<span class="hl">claude_monitor.py</span>
    └──执行──▶ <span class="green">claude -p lifetick_prompt.txt</span>
         ├── 读 memory.db + character.txt
         ├── AI 决策：是否发消息
         └── 写 next_tick.json

<span class="dim">─────────────── 管理侧 ───────────────</span>
浏览器 :8765
    ├──▶ <span class="green">memory.db</span>（记忆管理）
    └──▶ <span class="green">Yuki.vrm</span>（3D 查看）

<span class="dim">─────────────── 训练侧（离线）───────────────</span>
<span class="hl">vrm_render.py</span> ──▶ Playwright ──▶ 11 张训练图
    └──▶ <span class="green">sd-scripts</span> ──▶ yuki_lora_v1.safetensors
              └──▶ <span class="green">SD WebUI</span>（生成角色图像）</div>

  <h3>端口占用一览</h3>
  <table>
    <tr><th>端口</th><th>服务</th><th>启动方式</th></tr>
    <tr><td>8765</td><td>记忆管理面板 (FastAPI)</td><td><code>memory/admin/server.py</code></td></tr>
    <tr><td>9880</td><td>GPT-SoVITS 语音 API</td><td><code>scripts/start_voice_api.bat</code></td></tr>
  </table>

  <div class="callout tip">
    <strong>学习路线建议：</strong>如果你想理解这个项目，建议按以下顺序学习：① Python 基础 → ② SQLite / 数据库 → ③ HTTP API（FastAPI）→ ④ Telegram Bot API → ⑤ LLM API 调用 → ⑥ Three.js 3D 入门 → ⑦ Stable Diffusion 原理
  </div>
</div>

</body>
</html>
"""

def main():
    out = Path(r"F:\bot\dev\tools\yukibot_techstack.pdf")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not found", file=sys.stderr); sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML, wait_until="networkidle")
        page.pdf(
            path=str(out),
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    print(f"saved: {out}")

if __name__ == "__main__":
    main()
