# CLAUDE.md — Developer Guide

This document is the canonical reference for working on the **Daily AI News
Aggregator** codebase. It is written for both human contributors and AI
coding assistants.

## Project overview

A Python 3.11+ pipeline that:

1. Fetches news from RSS, arXiv, Hacker News, and custom scrapers.
2. Deduplicates against a 30-day rolling history.
3. Ranks by content depth, recency, and source trust.
4. Summarizes per topic with an audience-specific prompt.
5. Renders an HTML digest and ships it via SMTP.

Runs either as a one-shot CLI (`--once`) or as a long-lived scheduler.

## Repository layout

```
src/news_aggregator/
├── orchestrator.py     # Pipeline coordinator (entry point of the data flow)
├── scheduler.py        # APScheduler integration
├── config.py           # YAML + .env loader, dataclass tree
├── models.py           # Article / RankedArticle / ExecutionResult / ...
├── fetcher.py          # Legacy single-source fetcher
├── email_composer.py   # Jinja2 HTML rendering
├── email_sender.py     # SMTP delivery, failed-email persistence
├── logger.py           # Centralized logger setup
├── fetchers/           # rss_fetcher, arxiv, hacker_news, web_scraper, multi_source
├── processing/         # deduplicator, ranker, summarizer
├── providers/          # Multi-provider LLM abstraction (anthropic, openai, registry, selector, metrics)
└── tools/              # CLI helpers: feed_manager, feed_discovery, feed_scorer, opml_importer

config/
├── config.yaml         # Local config (gitignored)
├── config.example.yaml # Reference config with 42 curated feeds
└── prompts/            # beginner.txt, cs_student.txt

templates/email_template.html
tests/                  # test_phase1.py … test_phase6.py, test_multi_provider.py
```

## Pipeline data flow

```
RSS / arXiv / HN  ──┐
                    │  fetch (async, multi_source)
                    ▼
              raw Articles
                    │  deduplicate (URL norm + Levenshtein)
                    ▼
              unique Articles
                    │  rank_and_filter (composite score)
                    ▼
              RankedArticles
                    │  summarize_by_audience (multi-provider LLM)
                    ▼
              SummarizedArticles
                    │  compose (Jinja2)
                    ▼
              EmailContent
                    │  send (SMTP, fallback to data/failed_emails/)
                    ▼
              Inbox  +  history updated
```

Each stage lives in its own module and is composed by
`PipelineOrchestrator.run_pipeline()`.

## Configuration model

`config/config.yaml` is the source of truth for non-secret settings.
Secrets live in `.env` (see `example.env`).

```yaml
topics:             # user-defined; at least one required
  <topic_id>:
    audience_level: beginner | cs_student
    min_quality_score: 0.0-1.0
    max_articles_per_day: int
    trusted_sources: [...]
news_sources:       # keyed by topic_id
  <topic_id>:
    - url: https://...
      priority: high | medium | low
      enabled: true
alternative_sources: { arxiv, hacker_news, custom_scrapers }
providers:          # multi-provider LLM list, priority-ordered
  - provider_id, provider_type (anthropic|openai), model, base_url, ...
provider_strategy:  priority | cost | performance
email: { smtp_host, smtp_port, smtp_username, from_email, use_tls }
execution: { run_time, max_articles_per_topic }
quality: { min_content_length, dedup_title_threshold, history_days }
```

Topics are **user-defined** — there is no hardcoded list. Use
`news-aggregator --add-feeds` to grow the set interactively.

## LLM provider abstraction

`providers/base.py` defines `LLMProvider` (an abstract interface).
`providers/anthropic_provider.py` and `providers/openai_provider.py` are
concrete implementations; both expose an OpenAI-style chat completion
surface so the Anthropic client is wrapped to match.

`providers/registry.py` builds a registry of enabled providers.
`providers/selector.py` picks one per request using the configured
strategy (`priority`, `cost`, `performance`).
`providers/metrics.py` tracks per-provider latency, success rate, and
cost for the selector to reason about.
`providers/multi_provider_summarizer.py` is the orchestrator entry
point used by `PipelineOrchestrator`.

When adding a new provider:

1. Implement `LLMProvider` in `providers/<name>_provider.py`.
2. Register it in `providers/registry.py`.
3. Add a config example block to `config/config.example.yaml`.
4. Add a test in `tests/test_multi_provider.py`.

## Testing

```bash
uv run pytest tests/                              # run everything
uv run pytest tests/test_phase1.py -v             # one file
uv run pytest tests/ --cov=src/news_aggregator    # with coverage
```

Tests are organized by feature area (`test_phase1.py` … `test_phase6.py`)
plus `test_multi_provider.py` for the LLM provider layer. New tests
should follow the same file naming (`test_<feature>.py`).

Use `pytest-mock` and `pytest-asyncio` (already in `dev` deps). Mocks
for HTTP should go through `httpx.MockTransport` so they exercise the
real client code path.

## Code style

- Formatter: `black` (line length 88).
- Linter: `ruff` (configured by `pyproject.toml`).
- Type checker: `mypy` (see `pyproject.toml`).
- Pre-commit hooks run all of the above plus a few basic sanity checks
  (see `.pre-commit-config.yaml`).

```bash
uv run black src/ tests/
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/
uv run mypy src/news_aggregator
```

## Common tasks

| Task | Command |
|---|---|
| Add a new RSS source | `uv run news-aggregator --add-feeds` |
| List topics | `uv run news-aggregator --list-topics` |
| Discover feeds on a domain | `uv run news-aggregator --discover-feeds example.com` |
| Score feed quality | `uv run news-aggregator --score-feeds` |
| Import OPML | `uv run news-aggregator --import-opml feeds.opml` |
| Run once for testing | `uv run news-aggregator --once` |
| Start the scheduler | `uv run news-aggregator` |

## Extension points

| Want to … | Touch |
|---|---|
| Add a fetcher | `src/news_aggregator/fetchers/` + register in `multi_source.py` |
| Add an LLM provider | `src/news_aggregator/providers/<name>_provider.py` + `registry.py` |
| Add a delivery channel (Slack, Telegram, …) | Mirror `email_sender.py` |
| Add a storage backend for history | Replace `data/sent_articles.json` with SQLite/Postgres in `processing/deduplicator.py` |
| Change the email template | `templates/email_template.html` |

## Things to avoid

- Don't reintroduce hardcoded topic lists — topics are user-defined.
- Don't read secrets from `config.yaml` — use `.env`.
- Don't `print()`; use the shared `get_logger()` from `logger.py`.
- Don't add `try/except: pass` around the LLM call — let the provider
  abstraction surface errors so the selector can record a failure.
- Don't catch `Exception` broadly when adding a new code path; prefer
  the specific exception type.

## Release checklist

1. `uv run ruff check src/ tests/`
2. `uv run black --check src/ tests/`
3. `uv run mypy src/news_aggregator`
4. `uv run pytest tests/`
5. Bump `version` in `pyproject.toml`.
6. Update `CHANGELOG` (if present).
7. Tag `vX.Y.Z` and push.
