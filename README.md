# Daily AI News Aggregator

> Automated, AI-summarized daily news digests delivered to your inbox — fully customizable topics, multi-source fetching, and pluggable LLM providers.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](pyproject.toml)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter](https://img.shields.io/badge/linter-ruff-FCC21B.svg)](https://github.com/astral-sh/ruff)
[![Package](https://img.shields.io/badge/package-uv-DE5FE9.svg)](https://github.com/astral-sh/uv)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg)](https://pytest.org)

[English](#english) · [中文](#中文)

---

## Why this project?

Most news readers are noisy, full of clickbait, and force you to context-switch. **Daily AI News Aggregator** solves that with a small, opinionated pipeline that:

- Pulls from sources **you** care about (RSS, arXiv, Hacker News, custom scrapers).
- Ranks articles by depth, recency, and source trust.
- Uses an LLM to produce **audience-aware summaries** (beginner vs. CS student).
- Deduplicates against your history so you never see the same story twice.
- Delivers a polished HTML digest at a scheduled time, every day.

It's a single-binary CLI you can run locally, in Docker, or as a `systemd` service.

---

## Highlights

- **Multi-source ingestion** — RSS, arXiv (cs.AI / cs.LG / cs.RO), Hacker News, and a pluggable web scraper interface.
- **Multi-provider LLM** — Anthropic Claude, OpenAI, Azure, NVIDIA NIM, Ollama, LM Studio, vLLM, or any OpenAI-compatible endpoint. Priority / cost / performance routing built in.
- **Audience-specific prompts** — first-principles explanations for beginners, technical depth for CS students. Prompts are externalized in `config/prompts/`.
- **Smart deduplication** — URL normalization, fuzzy title matching (Levenshtein), and a 30-day rolling history.
- **Quality ranking** — composite score from content depth, recency, and trusted-source weighting.
- **HTML email digest** — Jinja2-templated, mobile-friendly, dark-mode aware.
- **Interactive feed management** — `--add-feeds`, `--list-topics`, `--remove-feed`, `--discover-feeds`, `--score-feeds`, `--import-opml`.
- **Tested** — 7 test modules, ~6,000 lines of source code.
- **Cross-platform** — Windows, Linux, macOS. `uv`-based reproducible environments.

---

## Architecture

```
                       +-------------------+
                       |  Scheduler (APScheduler)  |
                       +---------+---------+
                                 |
                                 v
+----------+    +-----------+   +-------------------+   +----------------+
| RSS Feed |--->|           |   |                   |   |                |
+----------+    |           |   |  MultiProvider    |   |  HTML Email    |
| arXiv    |--->|  Fetcher  +-->|  Summarizer  +--->+  Composer  +--->|  SMTP  |
+----------+    |           |   |  (Claude / OpenAI |   |                |   |        |
| HN       |--->|           |   |   / Local LLM)   |   +----------------+   +---++---+
+----------+    +-----+-----+   +-------------------+                        |   |
                       |                                                     v   v
                       v                                                  Inbox  Failed
                +-------------+                                       (data/failed_emails/)
                | Dedup + Rank|
                | (history)   |
                +-------------+
```

Each stage is independent and configured via `config/config.yaml`. The full pipeline is orchestrated by `src/news_aggregator/orchestrator.py`.

---

## Quick start

```bash
# 1. Install dependencies (creates .venv and installs everything)
uv sync

# 2. Create your local config
cp example.env .env
cp config/config.example.yaml config/config.yaml

# 3. Edit .env with your API key and SMTP password
$EDITOR .env

# 4. Add topics and feeds interactively
uv run news-aggregator --add-feeds

# 5. Run once to verify
uv run news-aggregator --once

# 6. Start the daily scheduler
uv run news-aggregator
```

That's it. Your first digest should land in your inbox within a minute of step 5.

---

## Table of contents

- [Highlights](#highlights)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [CLI reference](#cli-reference)
- [Project layout](#project-layout)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

<a id="english"></a>

## English

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | [`python.org`](https://www.python.org/downloads/) |
| uv | latest | [`astral.sh/uv`](https://github.com/astral-sh/uv) |
| LLM API key | — | Claude, OpenAI, Azure, NVIDIA, or any OpenAI-compatible endpoint |
| SMTP account | — | Gmail (App Password), QQ Mail (authorization code), Outlook, etc. |

### Installation

#### Linux / macOS

```bash
# Python 3.11+
brew install python@3.11          # macOS
sudo apt install python3.11      # Ubuntu / Debian

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Project
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator
uv sync
```

#### Windows

```powershell
# Python 3.11+ — download from python.org (check "Add Python to PATH")

# uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Project
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator
uv sync
```

### Configuration

#### 1. Environment variables (`.env`)

```bash
cp example.env .env
```

Choose **one** of the following LLM setups:

| Provider | `CLAUDE_API_BASE_URL` | `CLAUDE_API_KEY` |
|---|---|---|
| Anthropic Claude (default) | *leave commented* | `sk-ant-api03-...` |
| OpenAI | `https://api.openai.com/v1` | `sk-...` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<dep>` | `<azure-key>` |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | `<nvapi-...>` |
| Ollama / LM Studio / vLLM | `http://localhost:11434/v1` | `dummy` |

Then set:

```bash
SMTP_PASSWORD=your-app-password
RECIPIENT_EMAIL=you@example.com
```

> **Gmail users**: enable 2FA, then create an [App Password](https://myaccount.google.com/apppasswords).
> **QQ Mail users**: enable IMAP/SMTP and use the generated authorization code.

#### 2. Email & schedule (`config/config.yaml`)

```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_username: you@gmail.com
  from_email: you@gmail.com
  use_tls: true

execution:
  run_time: "08:00"          # 24-hour format, daily
  max_articles_per_topic: 15
```

#### 3. Topics & RSS feeds

The default `config/config.yaml` is intentionally empty. Pick one of three paths:

**Path A — Interactive wizard (recommended):**

```bash
uv run news-aggregator --add-feeds
```

Validates each URL, lets you create a new topic or extend an existing one, picks an audience level (`beginner` or `cs_student`), and writes everything back to `config/config.yaml`.

**Path B — Discover feeds from a website:**

```bash
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

**Path C — Manual:**

```bash
cp config/config.example.yaml config/config.yaml
$EDITOR config/config.yaml
```

`config.example.yaml` ships with 42 curated feeds across AI, Robotics, and Polymarket as a starting point.

### Usage

| Command | Purpose |
|---|---|
| `uv run news-aggregator` | Start the daily scheduler |
| `uv run news-aggregator --once` | Run the pipeline once and exit (for testing) |
| `uv run news-aggregator --add-feeds` | Interactive wizard to add topics and feeds |
| `uv run news-aggregator --list-topics` | Show all configured topics and their feeds |
| `uv run news-aggregator --remove-feed` | Interactively remove a feed from a topic |
| `uv run news-aggregator --discover-feeds <domains...>` | Find RSS/Atom feeds on the given sites |
| `uv run news-aggregator --score-feeds` | Score the quality of configured feeds |
| `uv run news-aggregator --import-opml <file>` | Import feeds from an OPML file |

#### Run once

```bash
uv run news-aggregator --once
```

Fetches, dedupes, ranks, summarizes, and sends. Check `logs/news_aggregator.log` if anything looks off, and failed emails land in `data/failed_emails/` for retry.

#### Run scheduled

```bash
uv run news-aggregator
```

The scheduler runs daily at `execution.run_time` from `config/config.yaml`. `Ctrl+C` to stop.

### Project layout

```
news-aggregator/
├── src/
│   └── news_aggregator/
│       ├── orchestrator.py          # Pipeline coordinator
│       ├── scheduler.py             # APScheduler integration
│       ├── config.py                # YAML + env config loader
│       ├── models.py                # Domain models
│       ├── fetcher.py               # Legacy single-source fetcher
│       ├── deduplicator.py          # Fuzzy title + URL dedup
│       ├── ranker.py                # Quality ranking
│       ├── summarizer.py            # Legacy single-provider summarizer
│       ├── email_composer.py        # Jinja2 HTML rendering
│       ├── email_sender.py          # SMTP delivery
│       ├── fetchers/                # RSS, arXiv, Hacker News, web scraper
│       ├── processing/              # Dedup, rank, summarize
│       ├── providers/               # Multi-provider LLM abstraction
│       └── tools/                   # Feed discovery, scoring, OPML
├── config/
│   ├── config.yaml                  # Your local config (gitignored)
│   ├── config.example.yaml          # Reference config with 42 feeds
│   └── prompts/                     # beginner.txt, cs_student.txt
├── templates/
│   └── email_template.html          # Digest layout
├── tests/                           # 7 test modules
├── example.env                      # .env template
├── pyproject.toml
└── uv.lock
```

### Deployment

#### Linux — `systemd`

Create `/etc/systemd/system/news-aggregator.service`:

```ini
[Unit]
Description=Daily AI News Aggregator
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/news-aggregator
ExecStart=/home/youruser/.local/bin/uv run news-aggregator
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now news-aggregator
sudo journalctl -u news-aggregator -f
```

#### Windows — Task Scheduler

1. Open **Task Scheduler** → **Create Basic Task**.
2. Trigger: **Daily** at your chosen time.
3. Action: **Start a program**
   - Program: `C:\Users\You\.local\bin\uv.exe`
   - Arguments: `run news-aggregator`
   - Start in: `C:\path\to\news-aggregator`

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `uv: command not found` | New shell didn't pick up PATH | Restart terminal, or `source $HOME/.local/bin/env` (Linux/macOS) |
| Email not sending | Wrong credentials | Gmail: use App Password, not account password. QQ: use authorization code. Check `logs/news_aggregator.log`. |
| `401` / `403` from LLM | Bad key, or proxy required | Verify `CLAUDE_API_KEY`; set `CLAUDE_API_BASE_URL` for proxies / local models |
| No articles found | Feeds empty or rate-limited | Run `uv run news-aggregator --score-feeds` to inspect feed health |
| `No module named news_aggregator` | Missing `uv sync` | Re-run `uv sync` to install into the venv |

### Development

```bash
# Run the test suite
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=src/news_aggregator

# Format
uv run black src/ tests/

# Lint
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/
```

See [`CLAUDE.md`](CLAUDE.md) for the architectural overview and extension points.

### Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-change`.
3. Make your change with tests.
4. Run `ruff check` and `pytest`.
5. Open a Pull Request describing the motivation and approach.

### License

[MIT](LICENSE)

---

<a id="中文"></a>

## 中文

一个基于 Python 的自动化新闻聚合系统：每日抓取多源新闻，使用 Claude / OpenAI / 本地大模型生成受众定制摘要，并通过 HTML 邮件定时投递。

### 系统要求

| 依赖 | 版本 | 备注 |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| uv | 最新版 | [astral.sh/uv](https://github.com/astral-sh/uv) |
| LLM API Key | — | Claude / OpenAI / Azure / NVIDIA / 任何 OpenAI 兼容端点 |
| SMTP 邮箱 | — | Gmail（应用专用密码）、QQ 邮箱（授权码）、Outlook 等 |

### 安装

#### Linux / macOS

```bash
brew install python@3.11          # macOS
sudo apt install python3.11      # Ubuntu / Debian

curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator
uv sync
```

#### Windows

```powershell
# 从 python.org 下载 Python 3.11+（勾选 "Add Python to PATH"）
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator
uv sync
```

### 配置

#### 1. 环境变量 (`.env`)

```bash
cp example.env .env
```

选择以下 LLM 之一：

| 提供方 | `CLAUDE_API_BASE_URL` | `CLAUDE_API_KEY` |
|---|---|---|
| Anthropic Claude（默认） | 保持注释 | `sk-ant-api03-...` |
| OpenAI | `https://api.openai.com/v1` | `sk-...` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<dep>` | `<azure-key>` |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | `<nvapi-...>` |
| Ollama / LM Studio / vLLM | `http://localhost:11434/v1` | `dummy` |

然后设置：

```bash
SMTP_PASSWORD=your-app-password
RECIPIENT_EMAIL=you@example.com
```

> **Gmail 用户**：开启两步验证后，在 [App Passwords](https://myaccount.google.com/apppasswords) 生成应用专用密码。
> **QQ 邮箱用户**：在设置中开启 IMAP/SMTP，使用生成的授权码。

#### 2. 邮件与定时 (`config/config.yaml`)

```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_username: you@gmail.com
  from_email: you@gmail.com
  use_tls: true

execution:
  run_time: "08:00"          # 24 小时制
  max_articles_per_topic: 15
```

#### 3. 主题与 RSS 源

默认的 `config/config.yaml` 是空的。请选择以下方式之一：

**方式 A — 交互式向导（推荐）：**

```bash
uv run news-aggregator --add-feeds
```

**方式 B — 从网站发现订阅源：**

```bash
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

**方式 C — 手动配置：**

```bash
cp config/config.example.yaml config/config.yaml
$EDITOR config/config.yaml
```

`config.example.yaml` 内置了 AI、机器人、Polymarket 三个主题共 42 个精选源，可作为起点。

### 使用

| 命令 | 用途 |
|---|---|
| `uv run news-aggregator` | 启动每日定时调度 |
| `uv run news-aggregator --once` | 立即执行一次（用于测试） |
| `uv run news-aggregator --add-feeds` | 交互式添加主题和订阅源 |
| `uv run news-aggregator --list-topics` | 列出所有主题和订阅源 |
| `uv run news-aggregator --remove-feed` | 交互式删除订阅源 |
| `uv run news-aggregator --discover-feeds <域名...>` | 在指定网站发现 RSS/Atom 源 |
| `uv run news-aggregator --score-feeds` | 评估已配置订阅源的质量 |
| `uv run news-aggregator --import-opml <file>` | 从 OPML 文件导入订阅源 |

### 项目结构

参见上方 [Project layout](#project-layout) 一节，结构相同。

### 部署

#### Linux — `systemd`

参见上方 [Deployment](#deployment) 一节。

#### Windows — 任务计划程序

参见上方 [Deployment](#deployment) 一节。

### 故障排除

| 现象 | 可能原因 | 解决办法 |
|---|---|---|
| `uv: 命令未找到` | 新终端未刷新 PATH | 重启终端或 `source $HOME/.local/bin/env` |
| 邮件发送失败 | 凭据错误 | Gmail 用应用专用密码，QQ 用授权码；查看 `logs/news_aggregator.log` |
| LLM 返回 401/403 | Key 无效或需要代理 | 检查 `CLAUDE_API_KEY`；本地模型需设置 `CLAUDE_API_BASE_URL` |
| 抓不到文章 | 订阅源为空或被限流 | 运行 `uv run news-aggregator --score-feeds` 检查订阅源健康度 |
| `No module named news_aggregator` | 未安装依赖 | 重新执行 `uv sync` |

### 开发

```bash
uv run pytest tests/
uv run pytest tests/ --cov=src/news_aggregator
uv run black src/ tests/
uv run ruff check src/ tests/
```

### 贡献

欢迎贡献！流程参见上方 [Contributing](#contributing) 一节。

### 许可证

[MIT](LICENSE)

---

**Built with** Python · APScheduler · Anthropic Claude · OpenAI · Jinja2 · uv
