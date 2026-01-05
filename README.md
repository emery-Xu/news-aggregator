# Daily AI News Aggregator

[English](#english) | [中文](#中文)

---

## English

A Python-based automated news aggregation system that fetches daily news, generates AI-powered summaries using Claude/OpenAI/local LLMs, and delivers them via email. Fully customizable topics and RSS feeds.

### Features

- **Multi-Source News Fetching**: Aggregates RSS feeds plus arXiv and Hacker News
- **Audience-Specific Summarization**: Tailored summaries for beginners and CS students
- **Smart Quality Ranking**: Filters articles by content depth, recency, and source reliability
- **Intelligent Deduplication**: URL matching, title similarity, and history tracking
- **Automated Daily Digest**: Beautiful HTML emails delivered on schedule
- **Feed Management Tools**: Discover, score, and import RSS feeds
- **OpenAI-Compatible API Support**: Works with Claude, OpenAI, Azure OpenAI, local LLMs (Ollama, LM Studio), and custom endpoints

### Prerequisites

- **Python 3.11+**
- **UV** package manager
- **LLM API key**: Claude API from [Anthropic](https://console.anthropic.com/), OpenAI API, or any OpenAI-compatible endpoint
- **SMTP email account** (Gmail, QQ Mail, etc.)

---

## Installation

### Windows

#### 1. Install Python 3.11+

Download from [python.org](https://www.python.org/downloads/) and ensure "Add Python to PATH" is checked.

Verify installation:
```cmd
python --version
```

#### 2. Install UV Package Manager

Open PowerShell as Administrator:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:
```cmd
uv --version
```

#### 3. Clone or Download the Project

```cmd
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator\news-aggregator
```

Or download and extract the ZIP file.

#### 4. Install Dependencies

```cmd
uv sync
```

This creates a virtual environment and installs all dependencies.

---

### Linux / macOS

#### 1. Install Python 3.11+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
```

**Fedora/RHEL:**
```bash
sudo dnf install python3.11
```

**macOS (using Homebrew):**
```bash
brew install python@3.11
```

Verify installation:
```bash
python3.11 --version
```

#### 2. Install UV Package Manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal or run:
```bash
source $HOME/.cargo/env
```

Verify installation:
```bash
uv --version
```

#### 3. Clone the Project

```bash
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator/news-aggregator
```

#### 4. Install Dependencies

```bash
uv sync
```

---

## Configuration

### 1. Environment Variables

**Windows:**
```cmd
copy example.env .env
notepad .env
```

**Linux/macOS:**
```bash
cp example.env .env
nano .env
```

Edit `.env` with your credentials:

```bash
# Option 1: Claude API (Recommended)
CLAUDE_API_KEY=sk-ant-api03-your-key-here

# Option 2: OpenAI API
# CLAUDE_API_BASE_URL=https://api.openai.com/v1
# CLAUDE_API_KEY=sk-your-openai-key-here

# Option 3: Local LLM (Ollama, LM Studio, etc.)
# CLAUDE_API_BASE_URL=http://localhost:11434/v1
# CLAUDE_API_KEY=dummy-key

# Option 4: Custom proxy/gateway
# CLAUDE_API_BASE_URL=https://your-proxy.com/v1
# CLAUDE_API_KEY=your-api-key

# SMTP password (Gmail App Password or QQ Mail authorization code)
SMTP_PASSWORD=your-smtp-password

# Recipient email address
RECIPIENT_EMAIL=your-email@example.com
```

#### API Configuration Options:

**Claude API (Official):**
- Get your API key from [Anthropic Console](https://console.anthropic.com/)
- Leave `CLAUDE_API_BASE_URL` commented out
- Best quality summaries, recommended

**OpenAI API:**
- Set `CLAUDE_API_BASE_URL=https://api.openai.com/v1`
- Set `CLAUDE_API_KEY` to your OpenAI key
- Works with GPT-4, GPT-3.5, etc.

**Local LLMs (Ollama, LM Studio, vLLM):**
- Set `CLAUDE_API_BASE_URL` to your local endpoint
- Set `CLAUDE_API_KEY=dummy` (not checked by local models)
- Free and private, but quality depends on model

**Azure OpenAI:**
- Set `CLAUDE_API_BASE_URL` to your Azure endpoint
- Set `CLAUDE_API_KEY` to your Azure key

#### Getting Gmail App Password:
1. Enable 2-Factor Authentication on your Google Account
2. Visit [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Use this password in `.env`

#### Getting QQ Mail Authorization Code:
1. Log in to QQ Mail settings
2. Go to Account → POP3/IMAP/SMTP
3. Enable IMAP/SMTP and generate authorization code
4. Use this code as `SMTP_PASSWORD`

### 2. Configure Email Settings

Edit `config/config.yaml` to set up your email:

**For Gmail:**
```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_username: your-email@gmail.com
  from_email: your-email@gmail.com
  use_tls: true
```

**For QQ Mail:**
```yaml
email:
  smtp_host: smtp.qq.com
  smtp_port: 465
  smtp_username: your-email@qq.com
  from_email: your-email@qq.com
  use_tls: false  # QQ Mail uses SSL on port 465
```

**Important Notes:**
- The `SMTP_PASSWORD` is set in `.env` file (see step 1)
- For Gmail: Use App Password (requires 2FA enabled)
- For QQ Mail: Use authorization code (not your login password)
- `smtp_username` and `from_email` should match your email address

### 3. Configure Topics and RSS Feeds

**Important**: The default `config/config.yaml` is intentionally empty. You need to add your own topics and RSS feeds.

See `config/config.example.yaml` for a complete example with pre-configured feeds for AI, Robotics, and Polymarket.

#### Option 1: Interactive Feed Management (Recommended)

**Add Multiple RSS Feeds:**
```bash
uv run news-aggregator --add-feeds
```

This interactive wizard will:
1. Prompt you to enter RSS URLs (one per line)
2. Validate all feeds automatically
3. Let you create a new topic or add to existing ones
4. Configure audience level (beginner/cs_student)
5. Save everything to `config/config.yaml`

**List Your Topics:**
```bash
uv run news-aggregator --list-topics
```

**Remove a Feed:**
```bash
uv run news-aggregator --remove-feed
```

#### Option 2: Discover RSS Feeds

Find RSS feeds on websites:
```bash
uv run news-aggregator --discover-feeds techcrunch.com theverge.com
```

#### Option 3: Manual Configuration

Copy the example and edit:
```bash
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your preferred feeds
```

Key sections:
- `topics`: Configure audience level and quality thresholds for each topic
- `news_sources`: Add/remove RSS feed URLs
- `email`: SMTP server settings
- `execution.run_time`: When to run daily (24-hour format, e.g., "08:00")

---

## Usage

### Interactive Feed Management Tutorial

#### Adding Your First RSS Feeds

Run the interactive wizard:

```bash
uv run news-aggregator --add-feeds
```

**Example Session:**

```
======================================================================
批量添加 RSS 订阅源
======================================================================

步骤 1/3: 输入RSS源URL
请输入RSS源URL（每行一个，输入空行结束）:

> https://techcrunch.com/feed/
> https://www.theverge.com/rss/index.xml
> https://openai.com/blog/rss.xml
> [Press Enter on empty line]

Validating feeds...
  Checking https://techcrunch.com/feed/... OK (25 articles)
  Checking https://www.theverge.com/rss/index.xml... OK (30 articles)
  Checking https://openai.com/blog/rss.xml... OK (15 articles)

总计: 3个有效RSS源

────────────────────────────────────

步骤 2/3: 选择或创建主题

现有主题:
  1) ai (10个源)
  2) [创建新主题]

请选择 [1-2]: 2

新主题名称: tech_news

────────────────────────────────────

步骤 3/3: 配置主题设置

受众级别:
  1) beginner (初学者 - 简单解释)
  2) cs_student (计算机学生 - 技术深度)

请选择 [1-2]: 1

默认优先级:
  1) high (高优先级)
  2) medium (中等优先级)
  3) low (低优先级)

请选择 [1-3]: 2

最大文章数/天 [默认: 10]: 15

────────────────────────────────────

✓ 配置摘要:
  主题: tech_news (beginner)
  RSS源: 3个 (优先级: medium)
  最大文章数: 15/天

确认添加? [Y/n]: y

✓ 已保存到 config/config.yaml
✓ 主题 'tech_news' 创建成功
✓ 3个RSS源添加完成

运行 'uv run news-aggregator --once' 测试配置
```

#### Viewing Your Topics

List all configured topics and their feeds:

```bash
uv run news-aggregator --list-topics
```

**Example Output:**

```
======================================================================
已配置的主题
======================================================================

主题: tech_news
  受众级别: beginner
  RSS源数量: 3
  最大文章数/天: 15
  质量阈值: 0.5
  RSS源:
    [OK] https://techcrunch.com/feed/ [medium]
    [OK] https://www.theverge.com/rss/index.xml [medium]
    [OK] https://openai.com/blog/rss.xml [medium]

主题: ai
  受众级别: cs_student
  RSS源数量: 10
  最大文章数/天: 10
  质量阈值: 0.6
  RSS源:
    [OK] https://openai.com/blog/rss.xml [high]
    [OK] https://blog.google/technology/ai/rss/ [high]
    ... 还有 8 个源

======================================================================
```

#### Removing a Feed

Interactively remove an RSS feed:

```bash
uv run news-aggregator --remove-feed
```

**Example Session:**

```
======================================================================
删除 RSS 订阅源
======================================================================

选择主题:
  1) tech_news (3个源)
  2) ai (10个源)

请选择 [1-2]: 1

选择要删除的RSS源:
  1) https://techcrunch.com/feed/ [medium]
  2) https://www.theverge.com/rss/index.xml [medium]
  3) https://openai.com/blog/rss.xml [medium]

请选择 [1-3]: 1

将删除: https://techcrunch.com/feed/
确认删除? [y/N]: y

✓ 已从 'tech_news' 删除 RSS源
```

---

### Quick Start Workflow

1. **Configure environment variables (.env):**
   ```bash
   cp example.env .env
   # Edit .env with your API key and SMTP password
   ```

2. **Configure email settings (config/config.yaml):**
   - Set `smtp_host`, `smtp_port`, `smtp_username`, `from_email`
   - See "Configure Email Settings" section above

3. **Add your first topic and feeds:**
   ```bash
   uv run news-aggregator --add-feeds
   ```

4. **Test the configuration:**
   ```bash
   uv run news-aggregator --once
   ```

5. **Start the daily scheduler:**
   ```bash
   uv run news-aggregator
   ```

### Run Once (Testing)

**Windows:**
```cmd
uv run news-aggregator --once
```

**Linux/macOS:**
```bash
uv run news-aggregator --once
```

This runs the pipeline immediately and exits. Use this to test your configuration.

### Run Scheduled (Production)

**Windows:**
```cmd
uv run news-aggregator
```

**Linux/macOS:**
```bash
uv run news-aggregator
```

The scheduler will run daily at the configured time. Press `Ctrl+C` to stop.

### Run as Background Service

**Linux (using systemd):**

Create `/etc/systemd/system/news-aggregator.service`:

```ini
[Unit]
Description=Daily AI News Aggregator
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/news-aggregator/news-aggregator
ExecStart=/home/youruser/.cargo/bin/uv run news-aggregator
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable news-aggregator
sudo systemctl start news-aggregator
sudo systemctl status news-aggregator
```

**Windows (using Task Scheduler):**

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at your preferred time
4. Action: Start a program
   - Program: `C:\Users\YourUser\.cargo\bin\uv.exe`
   - Arguments: `run news-aggregator`
   - Start in: `C:\path\to\news-aggregator\news-aggregator`
5. Save and test

---

## CLI Tools

### Discover RSS Feeds

Find RSS/Atom feeds on websites:

**Windows:**
```cmd
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

**Linux/macOS:**
```bash
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

### Score Existing Feeds

Evaluate quality of configured feeds:

```bash
uv run news-aggregator --score-feeds
```

### Import OPML

Import feeds from an OPML file:

```bash
uv run news-aggregator --import-opml path/to/feeds.opml
```

---

## Project Structure

```
news-aggregator/
├── news-aggregator/          # Main application directory
│   ├── src/                  # Source code
│   │   └── news_aggregator/
│   │       ├── main.py       # Entry point + CLI
│   │       ├── orchestrator.py
│   │       ├── fetchers/     # RSS, arXiv, Hacker News
│   │       ├── processing/   # Ranking, summarization, dedup
│   │       └── tools/        # Feed discovery, scoring, OPML
│   ├── config/
│   │   ├── config.yaml       # Main configuration
│   │   └── prompts/          # Summarization prompts
│   ├── templates/
│   │   └── email_template.html
│   ├── data/                 # Generated at runtime
│   ├── logs/                 # Generated at runtime
│   ├── .env                  # Your secrets (create from example.env)
│   └── pyproject.toml
├── CLAUDE.md                 # Developer guide
└── README.md                 # This file
```

---

## Troubleshooting

### Windows-Specific Issues

**"uv: command not found"**
- Close and reopen PowerShell/CMD after installing UV
- Or add `%USERPROFILE%\.cargo\bin` to PATH manually

**Python version issues**
- Ensure Python 3.11+ is in PATH: `python --version`
- If multiple Python versions exist, you may need to use `python3.11` explicitly

### Linux-Specific Issues

**Permission denied**
- Ensure uv is executable: `chmod +x ~/.cargo/bin/uv`
- Run `source $HOME/.cargo/env` to add uv to PATH

**systemd service fails**
- Check logs: `sudo journalctl -u news-aggregator -f`
- Verify WorkingDirectory and ExecStart paths
- Ensure user has permission to access the directory

### Common Issues

**Email not sending**
- Verify SMTP credentials in `.env`
- For Gmail: Use App Password, not your regular password
- For QQ Mail: Use authorization code, not password
- Check `logs/news_aggregator.log` for errors
- Failed emails are saved to `data/failed_emails/`

**Claude API errors**
- Check API key validity at [Anthropic Console](https://console.anthropic.com/)
- If using custom endpoint, verify `CLAUDE_API_BASE_URL` is reachable
- Check API quota and rate limits

**No articles found**
- Verify RSS feed URLs in `config/config.yaml`
- Check internet connection
- Some feeds update infrequently
- Review `logs/news_aggregator.log` for fetch errors

---

## Development

### Running Tests

```bash
uv run pytest tests/
uv run pytest tests/ --cov=src/news_aggregator
```

### Code Quality

```bash
uv run black src/
uv run ruff check src/
uv run ruff check --fix src/
```

### Adding New Features

See `CLAUDE.md` for architectural overview and development guidelines.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/news-aggregator/issues)
- **Documentation**: See `CLAUDE.md` for developer guide
- **Logs**: Check `logs/news_aggregator.log` for debugging

---

## 中文

一个基于 Python 的自动化新闻聚合系统，每日获取新闻，使用 Claude/OpenAI/本地大模型生成 AI 摘要，并通过邮件发送每日简报。完全可自定义主题和 RSS 订阅源。

### 功能特性

- **多源新闻获取**：聚合 RSS 订阅源、arXiv 和 Hacker News
- **受众定制摘要**：为初学者和计算机科学学生定制摘要
- **智能质量排序**：按内容深度、时效性和来源可靠性筛选文章
- **智能去重**：URL 匹配、标题相似度和历史记录跟踪
- **自动每日简报**：定时发送精美的 HTML 邮件
- **订阅源管理工具**：发现、评分和导入 RSS 订阅源
- **OpenAI 兼容 API 支持**：支持 Claude、OpenAI、Azure OpenAI、本地大模型（Ollama、LM Studio）和自定义端点

### 系统要求

- **Python 3.11+**
- **UV** 包管理器
- **LLM API 密钥**：Claude API（从 [Anthropic](https://console.anthropic.com/) 获取）、OpenAI API 或任何 OpenAI 兼容端点
- **SMTP 邮箱账号**（如 Gmail、QQ 邮箱等）

---

## 安装步骤

### Windows 系统

#### 1. 安装 Python 3.11+

从 [python.org](https://www.python.org/downloads/) 下载安装，确保勾选 "Add Python to PATH"。

验证安装：
```cmd
python --version
```

#### 2. 安装 UV 包管理器

以管理员身份打开 PowerShell：
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

验证安装：
```cmd
uv --version
```

#### 3. 克隆或下载项目

```cmd
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator\news-aggregator
```

或下载 ZIP 文件并解压。

#### 4. 安装依赖

```cmd
uv sync
```

此命令会创建虚拟环境并安装所有依赖。

---

### Linux / macOS 系统

#### 1. 安装 Python 3.11+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
```

**Fedora/RHEL:**
```bash
sudo dnf install python3.11
```

**macOS (使用 Homebrew):**
```bash
brew install python@3.11
```

验证安装：
```bash
python3.11 --version
```

#### 2. 安装 UV 包管理器

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

重启终端或运行：
```bash
source $HOME/.cargo/env
```

验证安装：
```bash
uv --version
```

#### 3. 克隆项目

```bash
git clone https://github.com/yourusername/news-aggregator.git
cd news-aggregator/news-aggregator
```

#### 4. 安装依赖

```bash
uv sync
```

---

## 配置

### 1. 环境变量

**Windows:**
```cmd
copy example.env .env
notepad .env
```

**Linux/macOS:**
```bash
cp example.env .env
nano .env
```

编辑 `.env` 文件，填入您的凭据：

```bash
# 选项 1：Claude API（推荐）
CLAUDE_API_KEY=sk-ant-api03-your-key-here

# 选项 2：OpenAI API
# CLAUDE_API_BASE_URL=https://api.openai.com/v1
# CLAUDE_API_KEY=sk-your-openai-key-here

# 选项 3：本地大模型（Ollama、LM Studio 等）
# CLAUDE_API_BASE_URL=http://localhost:11434/v1
# CLAUDE_API_KEY=dummy-key

# 选项 4：自定义代理/网关
# CLAUDE_API_BASE_URL=https://your-proxy.com/v1
# CLAUDE_API_KEY=your-api-key

# SMTP 密码（Gmail 应用专用密码或 QQ 邮箱授权码）
SMTP_PASSWORD=your-smtp-password

# 接收邮件的地址
RECIPIENT_EMAIL=your-email@example.com
```

#### API 配置选项：

**Claude API（官方）：**
- 从 [Anthropic 控制台](https://console.anthropic.com/) 获取 API 密钥
- 保持 `CLAUDE_API_BASE_URL` 注释状态
- 摘要质量最佳，推荐使用

**OpenAI API：**
- 设置 `CLAUDE_API_BASE_URL=https://api.openai.com/v1`
- 设置 `CLAUDE_API_KEY` 为您的 OpenAI 密钥
- 支持 GPT-4、GPT-3.5 等模型

**本地大模型（Ollama、LM Studio、vLLM）：**
- 设置 `CLAUDE_API_BASE_URL` 为本地端点
- 设置 `CLAUDE_API_KEY=dummy`（本地模型不检查）
- 免费且私密，但质量取决于模型

**Azure OpenAI：**
- 设置 `CLAUDE_API_BASE_URL` 为 Azure 端点
- 设置 `CLAUDE_API_KEY` 为 Azure 密钥

#### 获取 Gmail 应用专用密码：
1. 在 Google 账号中启用两步验证
2. 访问 [应用专用密码](https://myaccount.google.com/apppasswords)
3. 为"邮件"生成新的应用专用密码
4. 在 `.env` 中使用此密码

#### 获取 QQ 邮箱授权码：
1. 登录 QQ 邮箱设置
2. 进入"账户" → "POP3/IMAP/SMTP"
3. 开启 IMAP/SMTP 并生成授权码
4. 将授权码用作 `SMTP_PASSWORD`

### 2. 配置邮件设置

编辑 `config/config.yaml` 设置邮件发送：

**使用 Gmail：**
```yaml
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_username: your-email@gmail.com
  from_email: your-email@gmail.com
  use_tls: true
```

**使用 QQ 邮箱：**
```yaml
email:
  smtp_host: smtp.qq.com
  smtp_port: 465
  smtp_username: your-email@qq.com
  from_email: your-email@qq.com
  use_tls: false  # QQ 邮箱在 465 端口使用 SSL
```

**重要说明：**
- `SMTP_PASSWORD` 在 `.env` 文件中设置（见步骤 1）
- Gmail：使用应用专用密码（需要启用两步验证）
- QQ 邮箱：使用授权码（不是登录密码）
- `smtp_username` 和 `from_email` 应该与你的邮箱地址一致

### 3. 配置主题和 RSS 订阅源

**重要**：默认的 `config/config.yaml` 是空的。你需要添加自己的主题和 RSS 订阅源。

参考 `config/config.example.yaml` 查看完整示例，其中包含 AI、机器人和 Polymarket 的预配置订阅源。

#### 方式 1：交互式订阅管理（推荐）

**批量添加 RSS 订阅源：**
```bash
uv run news-aggregator --add-feeds
```

交互式向导将：
1. 提示你输入 RSS URL（每行一个）
2. 自动验证所有订阅源
3. 让你创建新主题或添加到现有主题
4. 配置受众级别（beginner/cs_student）
5. 保存所有配置到 `config/config.yaml`

**列出所有主题：**
```bash
uv run news-aggregator --list-topics
```

**删除订阅源：**
```bash
uv run news-aggregator --remove-feed
```

#### 方式 2：发现 RSS 订阅源

在网站上查找 RSS 订阅源：
```bash
uv run news-aggregator --discover-feeds techcrunch.com theverge.com
```

#### 方式 3：手动配置

复制示例并编辑：
```bash
cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml 添加你喜欢的订阅源
```

主要部分：
- `topics`：为每个主题配置受众级别和质量阈值
- `news_sources`：添加/删除 RSS 订阅源 URL
- `email`：SMTP 服务器设置
- `execution.run_time`：每日运行时间（24 小时格式，如 "08:00"）

---

## 使用方法

### 交互式订阅管理教程

#### 添加您的第一批 RSS 订阅源

运行交互式向导：

```bash
uv run news-aggregator --add-feeds
```

**示例会话：**

```
======================================================================
批量添加 RSS 订阅源
======================================================================

步骤 1/3: 输入RSS源URL
请输入RSS源URL（每行一个，输入空行结束）:

> https://techcrunch.com/feed/
> https://www.theverge.com/rss/index.xml
> https://openai.com/blog/rss.xml
> [在空行按回车]

Validating feeds...
  Checking https://techcrunch.com/feed/... OK (25 articles)
  Checking https://www.theverge.com/rss/index.xml... OK (30 articles)
  Checking https://openai.com/blog/rss.xml... OK (15 articles)

总计: 3个有效RSS源

────────────────────────────────────

步骤 2/3: 选择或创建主题

现有主题:
  1) ai (10个源)
  2) [创建新主题]

请选择 [1-2]: 2

新主题名称: 科技新闻

────────────────────────────────────

步骤 3/3: 配置主题设置

受众级别:
  1) beginner (初学者 - 简单解释)
  2) cs_student (计算机学生 - 技术深度)

请选择 [1-2]: 1

默认优先级:
  1) high (高优先级)
  2) medium (中等优先级)
  3) low (低优先级)

请选择 [1-3]: 2

最大文章数/天 [默认: 10]: 15

────────────────────────────────────

✓ 配置摘要:
  主题: 科技新闻 (beginner)
  RSS源: 3个 (优先级: medium)
  最大文章数: 15/天

确认添加? [Y/n]: y

✓ 已保存到 config/config.yaml
✓ 主题 '科技新闻' 创建成功
✓ 3个RSS源添加完成

运行 'uv run news-aggregator --once' 测试配置
```

#### 查看您的主题

列出所有已配置的主题和订阅源：

```bash
uv run news-aggregator --list-topics
```

**示例输出：**

```
======================================================================
已配置的主题
======================================================================

主题: 科技新闻
  受众级别: beginner
  RSS源数量: 3
  最大文章数/天: 15
  质量阈值: 0.5
  RSS源:
    [OK] https://techcrunch.com/feed/ [medium]
    [OK] https://www.theverge.com/rss/index.xml [medium]
    [OK] https://openai.com/blog/rss.xml [medium]

主题: ai
  受众级别: cs_student
  RSS源数量: 10
  最大文章数/天: 10
  质量阈值: 0.6
  RSS源:
    [OK] https://openai.com/blog/rss.xml [high]
    [OK] https://blog.google/technology/ai/rss/ [high]
    ... 还有 8 个源

======================================================================
```

#### 删除订阅源

交互式删除 RSS 订阅源：

```bash
uv run news-aggregator --remove-feed
```

**示例会话：**

```
======================================================================
删除 RSS 订阅源
======================================================================

选择主题:
  1) 科技新闻 (3个源)
  2) ai (10个源)

请选择 [1-2]: 1

选择要删除的RSS源:
  1) https://techcrunch.com/feed/ [medium]
  2) https://www.theverge.com/rss/index.xml [medium]
  3) https://openai.com/blog/rss.xml [medium]

请选择 [1-3]: 1

将删除: https://techcrunch.com/feed/
确认删除? [y/N]: y

✓ 已从 '科技新闻' 删除 RSS源
```

---

### 快速开始流程

1. **配置环境变量（.env）：**
   ```bash
   cp example.env .env
   # 编辑 .env 填入 API 密钥和 SMTP 密码
   ```

2. **配置邮件设置（config/config.yaml）：**
   - 设置 `smtp_host`、`smtp_port`、`smtp_username`、`from_email`
   - 参见上方"配置邮件设置"部分

3. **添加第一个主题和订阅源：**
   ```bash
   uv run news-aggregator --add-feeds
   ```

4. **测试配置：**
   ```bash
   uv run news-aggregator --once
   ```

5. **启动每日调度器：**
   ```bash
   uv run news-aggregator
   ```

### 单次运行（测试）

**Windows:**
```cmd
uv run news-aggregator --once
```

**Linux/macOS:**
```bash
uv run news-aggregator --once
```

立即运行一次并退出，用于测试配置。

### 定时运行（生产环境）

**Windows:**
```cmd
uv run news-aggregator
```

**Linux/macOS:**
```bash
uv run news-aggregator
```

调度器将在配置的时间每日运行。按 `Ctrl+C` 停止。

### 后台服务运行

**Linux (使用 systemd):**

创建 `/etc/systemd/system/news-aggregator.service`：

```ini
[Unit]
Description=Daily AI News Aggregator
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/news-aggregator/news-aggregator
ExecStart=/home/youruser/.cargo/bin/uv run news-aggregator
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动：
```bash
sudo systemctl daemon-reload
sudo systemctl enable news-aggregator
sudo systemctl start news-aggregator
sudo systemctl status news-aggregator
```

**Windows (使用任务计划程序):**

1. 打开任务计划程序
2. 创建基本任务
3. 设置触发器：每日在您选择的时间
4. 操作：启动程序
   - 程序：`C:\Users\YourUser\.cargo\bin\uv.exe`
   - 参数：`run news-aggregator`
   - 起始于：`C:\path\to\news-aggregator\news-aggregator`
5. 保存并测试

---

## CLI 工具

### 发现 RSS 订阅源

在网站上查找 RSS/Atom 订阅源：

**Windows:**
```cmd
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

**Linux/macOS:**
```bash
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

### 评估现有订阅源

评估已配置订阅源的质量：

```bash
uv run news-aggregator --score-feeds
```

### 导入 OPML

从 OPML 文件导入订阅源：

```bash
uv run news-aggregator --import-opml path/to/feeds.opml
```

---

## 项目结构

```
news-aggregator/
├── news-aggregator/          # 主应用目录
│   ├── src/                  # 源代码
│   │   └── news_aggregator/
│   │       ├── main.py       # 入口点 + CLI
│   │       ├── orchestrator.py
│   │       ├── fetchers/     # RSS、arXiv、Hacker News
│   │       ├── processing/   # 排序、摘要、去重
│   │       └── tools/        # 订阅源发现、评分、OPML
│   ├── config/
│   │   ├── config.yaml       # 主配置文件
│   │   └── prompts/          # 摘要提示词
│   ├── templates/
│   │   └── email_template.html
│   ├── data/                 # 运行时生成
│   ├── logs/                 # 运行时生成
│   ├── .env                  # 您的密钥（从 example.env 创建）
│   └── pyproject.toml
├── CLAUDE.md                 # 开发者指南
└── README.md                 # 本文件
```

---

## 故障排除

### Windows 特定问题

**"uv: 命令未找到"**
- 安装 UV 后关闭并重新打开 PowerShell/CMD
- 或手动将 `%USERPROFILE%\.cargo\bin` 添加到 PATH

**Python 版本问题**
- 确保 Python 3.11+ 在 PATH 中：`python --version`
- 如果存在多个 Python 版本，可能需要明确使用 `python3.11`

### Linux 特定问题

**权限被拒绝**
- 确保 uv 可执行：`chmod +x ~/.cargo/bin/uv`
- 运行 `source $HOME/.cargo/env` 将 uv 添加到 PATH

**systemd 服务失败**
- 查看日志：`sudo journalctl -u news-aggregator -f`
- 验证 WorkingDirectory 和 ExecStart 路径
- 确保用户有权限访问该目录

### 常见问题

**邮件发送失败**
- 验证 `.env` 中的 SMTP 凭据
- Gmail：使用应用专用密码，而非常规密码
- QQ 邮箱：使用授权码，而非密码
- 查看 `logs/news_aggregator.log` 中的错误
- 失败的邮件会保存到 `data/failed_emails/`

**Claude API 错误**
- 在 [Anthropic 控制台](https://console.anthropic.com/) 检查 API 密钥有效性
- 如使用自定义端点，验证 `CLAUDE_API_BASE_URL` 可访问
- 检查 API 配额和速率限制

**未找到文章**
- 验证 `config/config.yaml` 中的 RSS 订阅源 URL
- 检查网络连接
- 某些订阅源更新不频繁
- 查看 `logs/news_aggregator.log` 中的获取错误

---

## 开发

### 运行测试

```bash
uv run pytest tests/
uv run pytest tests/ --cov=src/news_aggregator
```

### 代码质量

```bash
uv run black src/
uv run ruff check src/
uv run ruff check --fix src/
```

### 添加新功能

参见 `CLAUDE.md` 了解架构概述和开发指南。

---

## 贡献

欢迎贡献！请：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

---

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 支持

- **问题反馈**：[GitHub Issues](https://github.com/yourusername/news-aggregator/issues)
- **文档**：参见 `CLAUDE.md` 开发者指南
- **日志**：查看 `logs/news_aggregator.log` 进行调试

---

**版本**: 2.0.0

使用 Python、Claude AI 和 UV 包管理器构建。
