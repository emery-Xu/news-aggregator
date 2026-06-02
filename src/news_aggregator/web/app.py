"""FastAPI web application for viewing collected articles."""

from collections import defaultdict
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from ..config import Config
from ..logger import get_logger
from .storage import ArticleStore


def create_app(config: Config) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        config: Application configuration

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title="Daily AI News Digest", version="1.0.0")
    logger = get_logger()

    article_store = ArticleStore(base_dir=config.articles_dir)

    template_dir = Path("templates/web")
    if not template_dir.exists():
        template_dir = Path(__file__).parent.parent.parent.parent / "templates" / "web"

    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

    app.state.article_store = article_store
    app.state.config = config
    app.state.env = env
    app.state.logger = logger

    @app.get("/", response_class=RedirectResponse)
    async def index():
        """Redirect to the latest available digest."""
        latest = article_store.get_latest_date()
        if latest is None:
            return RedirectResponse(url="/digest/none")
        return RedirectResponse(url=f"/digest/{latest.isoformat()}")

    @app.get("/digest/{target_date}", response_class=HTMLResponse)
    async def digest_page(request: Request, target_date: str):
        """Render the digest page for a specific date."""
        if target_date == "none":
            template = env.get_template("index.html")
            return template.render(
                current_date=None,
                articles=[],
                topics={},
                topic_counts={},
                total_count=0,
                available_dates=article_store.list_available_dates(),
                prev_date=None,
                next_date=None,
                topic_configs={},
            )

        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            return HTMLResponse(
                content="<h1>Invalid date format. Use YYYY-MM-DD.</h1>", status_code=400
            )

        articles = article_store.load_articles(parsed_date)
        available_dates = article_store.list_available_dates()

        topics = defaultdict(list)
        for article in articles:
            topics[article.get("topic", "unknown")].append(article)

        topic_counts = {topic: len(arts) for topic, arts in topics.items()}
        total_count = len(articles)

        prev_date = None
        next_date = None
        for i, d in enumerate(available_dates):
            if d == parsed_date:
                if i + 1 < len(available_dates):
                    prev_date = available_dates[i + 1]
                if i > 0:
                    next_date = available_dates[i - 1]
                break

        topic_configs = {}
        for topic_id, topic_config in config.topics.items():
            topic_configs[topic_id] = {
                "audience_level": topic_config.audience_level,
                "context_text": (
                    topic_config.context_text if topic_config.include_context else None
                ),
            }

        template = env.get_template("index.html")
        return template.render(
            current_date=parsed_date,
            articles=articles,
            topics=dict(topics),
            topic_counts=topic_counts,
            total_count=total_count,
            available_dates=available_dates,
            prev_date=prev_date,
            next_date=next_date,
            topic_configs=topic_configs,
        )

    @app.get("/api/dates")
    async def api_dates():
        """Return list of available dates."""
        dates = article_store.list_available_dates()
        return JSONResponse(content=[d.isoformat() for d in dates])

    @app.get("/api/articles/{target_date}")
    async def api_articles(target_date: str):
        """Return articles for a specific date."""
        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            return JSONResponse(
                content={"error": "Invalid date format. Use YYYY-MM-DD."},
                status_code=400,
            )

        articles = article_store.load_articles(parsed_date)
        return JSONResponse(content={"date": target_date, "articles": articles})

    return app
