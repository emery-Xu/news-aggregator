# Daily AI News Aggregator

A Python-based automated news aggregation system that fetches daily news about **Polymarket**, **AI**, and **Robotics**, generates AI-powered summaries using Claude, and delivers them via email.

## Features

- **Multi-Source News Fetching**: Aggregates RSS feeds plus arXiv and Hacker News for three topics:
  - Polymarket (prediction markets and crypto)
  - Artificial Intelligence
  - Robotics

- **Audience-Specific Summarization**: Uses Claude prompts tailored for beginners vs CS students with strict 3-5 bullet summaries

- **Quality Ranking and Filtering**:
  - Scores articles by content depth, recency, and trusted sources
  - Filters low-quality items before summarization
  - Limits per-topic output for a focused daily digest

- **Beginner Context Cards**: Adds short background explanations for Polymarket and Robotics sections

- **Feed Management Tools**:
  - Discover feeds on domains with `--discover-feeds`
  - Score existing feeds with `--score-feeds`
  - Import OPML with `--import-opml`

- **Smart Deduplication**: URL matching, title similarity, and 30-day history tracking

- **Daily Email Digest**: Responsive HTML email with clearly labeled audience sections

- **Automated Scheduling**: Runs at a configured daily time using APScheduler

- **Error Handling & Logging**: Rotating logs, retries, and safe fallbacks when APIs fail

## What's New (v2.0)

- Multi-source fetching (RSS + arXiv + Hacker News) with curated feed lists
- Adaptive summarization prompts per audience level
- Quality ranking and topic-level filtering before summarization
- Context cards for beginner topics
- CLI tools for feed discovery, scoring, and OPML import

## Prerequisites

- **Python 3.11+**
- **UV** package manager ([installation guide](https://docs.astral.sh/uv/))
- **Claude API key** from [Anthropic](https://console.anthropic.com/)
- **SMTP server access** (e.g., Gmail with App Password)

## Installation

### 1. Clone or download the project

```bash
cd news-aggregator
```

### 2. Install UV (if not already installed)

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Install dependencies

```bash
uv sync
```

This will install all required dependencies and create a virtual environment.

## Configuration

### 1. Set up environment variables

Copy the example file and fill in your credentials:

```bash
cp example.env .env
# or: cp config/.env.example config/.env
```

Edit `.env` (or `config/.env`):

```bash
# Get your Claude API key from https://console.anthropic.com/
CLAUDE_API_KEY=sk-ant-api03-your-key-here

# Optional: Custom Claude API endpoint (proxies, local gateways)
# CLAUDE_API_BASE_URL=https://your-custom-api-endpoint.com/v1

# For Gmail, create an App Password: https://myaccount.google.com/apppasswords
SMTP_PASSWORD=your-smtp-app-password

# Email address to receive the daily digest
RECIPIENT_EMAIL=your-email@example.com
```

### 2. Configure news sources and settings

Edit `config/config.yaml` to customize:

- **News sources**: Add or remove RSS feed URLs
- **Email settings**: SMTP server details
- **Execution time**: When to run daily (default: 08:00 AM)
- **Maximum articles**: Limit per topic (default: 15)

Example `config/config.yaml`:

```yaml
topics:
  polymarket:
    audience_level: beginner
    include_context: true
    context_text: "Polymarket is a prediction market platform where users bet on future events using cryptocurrency."
    min_quality_score: 0.5
    max_articles_per_day: 10
    trusted_sources: ["CoinDesk", "Decrypt"]

  robotics:
    audience_level: beginner
    include_context: true
    context_text: "Robotics combines mechanical engineering, AI, and sensors to create autonomous machines."
    min_quality_score: 0.5
    max_articles_per_day: 10
    trusted_sources: ["IEEE Spectrum", "The Robot Report"]

  ai:
    audience_level: cs_student
    include_context: false
    context_text: null
    min_quality_score: 0.6
    max_articles_per_day: 10
    trusted_sources: ["OpenAI Blog", "Anthropic News", "arXiv"]

news_sources:
  polymarket:
    - url: https://www.coindesk.com/tag/polymarket/feed/
      priority: high
      enabled: true

  ai:
    - url: https://openai.com/blog/rss.xml
      priority: high
      enabled: true

  robotics:
    - url: https://spectrum.ieee.org/feeds/robotics.rss
      priority: high
      enabled: true

alternative_sources:
  arxiv:
    enabled: true
    categories: ["cs.AI", "cs.LG", "cs.RO"]
    max_per_category: 5
  hacker_news:
    enabled: true
    min_score: 50
    max_age_hours: 48
    keywords: ["ai", "machine learning", "robotics"]

summarization:
  beginner_prompt_path: config/prompts/beginner.txt
  cs_student_prompt_path: config/prompts/cs_student.txt
  max_tokens: 500
  temperature: 0.3

quality:
  min_content_length: 200
  dedup_title_threshold: 0.85
  history_days: 30

email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_username: your-email@gmail.com
  from_email: your-email@gmail.com

execution:
  run_time: "08:00"  # 24-hour format
  max_articles_per_topic: 15
```

## Usage

### Run Once (for testing)

Test the pipeline with a single immediate execution:

```bash
uv run news-aggregator --once
```

This will:
1. Fetch news from all configured sources
2. Deduplicate articles
3. Generate AI summaries
4. Send the email digest
5. Exit

### Run Scheduled (production mode)

Start the scheduler to run daily at the configured time:

```bash
uv run news-aggregator
```

The scheduler will:
- Run the pipeline at the specified time each day (default: 08:00 AM)
- Continue running until stopped (Ctrl+C)
- Log all activities to `logs/news_aggregator.log`

### Custom Configuration File

Use a different configuration file:

```bash
uv run news-aggregator --config /path/to/custom-config.yaml
```

## CLI Tools

Discover RSS/Atom feeds on a domain:

```bash
uv run news-aggregator --discover-feeds openai.com anthropic.com
```

Score all configured feeds:

```bash
uv run news-aggregator --score-feeds
```

Import feeds from an OPML file (prints grouped results):

```bash
uv run news-aggregator --import-opml path/to/feeds.opml
```

## Audience-Specific Summaries

Beginner summary example (Polymarket/Robotics):

```text
- Polymarket lets people trade on future events, similar to betting on outcomes.
- The market shows rising odds for a specific election result this week.
- Higher odds suggest more traders think that outcome is likely.
- This matters because prediction markets often react before traditional polls.
```

CS student summary example (AI):

```text
- The paper introduces a new transformer variant with sparse attention blocks.
- It reports lower memory use while matching baseline accuracy on GLUE.
- Training uses a hybrid optimizer combining AdamW with schedule-free warmup.
- Code and checkpoints are released for reproduction on standard benchmarks.
```

## Project Structure

```
news-aggregator/
├── src/news_aggregator/
│   ├── main.py              # Entry point + CLI tools
│   ├── orchestrator.py      # Pipeline coordination
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging setup
│   ├── models.py            # Data models
│   ├── scheduler.py         # Daily scheduling
│   ├── email_composer.py    # Email HTML generation
│   ├── email_sender.py      # SMTP email sending
│   ├── fetchers/
│   │   ├── rss_fetcher.py
│   │   ├── arxiv.py
│   │   ├── hacker_news.py
│   │   ├── multi_source.py
│   │   └── web_scraper.py
│   ├── processing/
│   │   ├── ranker.py
│   │   ├── summarizer.py
│   │   └── deduplicator.py
│   └── tools/
│       ├── feed_discovery.py
│       ├── feed_scorer.py
│       └── opml_importer.py
├── templates/
│   └── email_template.html  # Email template
├── config/
│   ├── config.yaml          # Main configuration
│   └── prompts/
│       ├── beginner.txt
│       └── cs_student.txt
├── data/                    # Runtime data
│   ├── sent_articles.json   # History of sent articles
│   └── execution_history.json
├── logs/                    # Application logs
│   └── news_aggregator.log
├── tests/                   # Unit tests
├── pyproject.toml           # Project dependencies
└── README.md
```

## How It Works

### Pipeline Stages

1. **Fetch**: Retrieves articles from RSS, arXiv, and Hacker News in parallel
2. **Deduplicate**: Removes duplicates by URL, title similarity, and history
3. **Rank**: Scores articles for quality and filters low-value items
4. **Summarize**: Uses audience-specific prompts for 3-5 bullet summaries
5. **Compose**: Creates HTML email with organized sections and context cards
6. **Send**: Delivers email via SMTP

### Data Flow

```
Sources → Articles → Deduplication → Ranking → Adaptive Summaries → Email → Your Inbox
```

### Deduplication Strategy

- **URL matching**: Exact duplicate URLs are removed
- **Title similarity**: Articles with >80% similar titles are filtered
- **History tracking**: Previously sent articles are not sent again (30-day history)

## Troubleshooting

### Email Not Sending

**Problem**: Email delivery fails

**Solutions**:
- For Gmail: Enable 2FA and create an [App Password](https://myaccount.google.com/apppasswords)
- Check SMTP credentials in `config/.env`
- Verify SMTP settings in `config/config.yaml`
- Check logs in `logs/news_aggregator.log`
- If send fails, email is saved to `data/failed_emails/`

### Claude API Errors

**Problem**: Summarization fails with API errors

**Solutions**:
- Verify your API key in `config/.env`
- Check API quota at [Anthropic Console](https://console.anthropic.com/)
- If using `CLAUDE_API_BASE_URL`, confirm the endpoint is reachable
- Rate limits are handled automatically with exponential backoff
- If summarization fails, original article descriptions are used

### No Articles Found

**Problem**: Email says "No new articles today"

**Solutions**:
- Check if RSS feed URLs are still valid
- Verify internet connection
- Check logs for fetch errors
- Some feeds may have publishing delays
- Try running with `--once` to test immediately

### Configuration Errors

**Problem**: Application won't start

**Solutions**:
- Run `uv run news-aggregator --once` to see specific error messages
- Ensure all required fields in `config.yaml` are filled
- Verify environment variables in `.env` are set
- Check Python version: `python --version` (requires 3.11+)

## Logs and Monitoring

### Log Files

- **Location**: `logs/news_aggregator.log`
- **Rotation**: Automatically rotates at 50MB (keeps 5 backups)
- **Format**: Timestamp, level, component, message

### Execution History

- **Location**: `data/execution_history.json`
- **Retention**: Last 30 days
- **Contains**: Success/failure status, article counts, errors, execution time

### Log Levels

- **INFO**: Normal operations (pipeline start/end, article counts)
- **WARNING**: Recoverable errors (source timeout, API retry)
- **ERROR**: Failed operations (email send failure)
- **CRITICAL**: Unrecoverable errors requiring intervention

## Advanced Configuration

### Adding News Sources

Edit `config/config.yaml` and add RSS feed URLs to any topic:

```yaml
news_sources:
  ai:
    - https://techcrunch.com/category/artificial-intelligence/feed/
    - https://your-custom-feed.com/rss
```

### Changing Schedule

Modify the `run_time` in `config/config.yaml`:

```yaml
execution:
  run_time: "06:30"  # Run at 6:30 AM
```

### Prompt Templates

Edit the audience-specific prompt templates:

- `config/prompts/beginner.txt`
- `config/prompts/cs_student.txt`

### Quality Filtering

Adjust thresholds per topic in `config/config.yaml`:

```yaml
topics:
  ai:
    min_quality_score: 0.6
    max_articles_per_day: 10
```

### Customizing Email Template

Edit `templates/email_template.html` to customize the email design.

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Code Formatting

```bash
uv run black src/
uv run ruff check src/
```

## Contributing

This is a personal-use project, but contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review logs in `logs/news_aggregator.log`
- Check execution history in `data/execution_history.json`

## Version

Current version: **2.0.0**

---

Built with Python, Claude AI, and UV package manager.
