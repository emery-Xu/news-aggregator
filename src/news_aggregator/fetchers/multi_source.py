"""Multi-source fetcher coordinator for aggregating content from various sources."""

import asyncio
from typing import List
from ..models import Article
from ..config import Config
from ..logger import get_logger
from .rss_fetcher import RSSFetcher
from .arxiv import ArxivFetcher
from .hacker_news import HackerNewsFetcher


class MultiSourceFetcher:
    """Coordinates fetching from multiple content sources (RSS, arXiv, Hacker News, custom scrapers)."""

    def __init__(self, config: Config):
        """
        Initialize multi-source fetcher.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger()

        # Initialize individual fetchers
        self.rss_fetcher = RSSFetcher(
            news_sources=config.news_sources,
            max_articles_per_topic=config.max_articles_per_topic
        )

        self.arxiv_fetcher = ArxivFetcher(config.arxiv) if config.arxiv.enabled else None
        self.hn_fetcher = HackerNewsFetcher(config.hacker_news) if config.hacker_news.enabled else None

        # Custom scrapers would be initialized here if enabled
        # self.custom_scrapers = self._init_custom_scrapers() if config.custom_scrapers_enabled else []

    async def fetch_all(self) -> List[Article]:
        """
        Fetch articles from all enabled sources in parallel.

        Returns:
            Combined list of Article objects from all sources
        """
        self.logger.info("Starting multi-source fetch from all enabled sources")

        # Build list of fetch tasks
        tasks = []

        # Always fetch from RSS feeds
        tasks.append(self._safe_fetch("RSS", self.rss_fetcher.fetch_all_topics()))

        # Fetch from arXiv if enabled
        if self.arxiv_fetcher:
            tasks.append(self._safe_fetch("arXiv", self.arxiv_fetcher.fetch_all()))

        # Fetch from Hacker News if enabled
        if self.hn_fetcher:
            tasks.append(self._safe_fetch("Hacker News", self.hn_fetcher.fetch_all()))

        # Fetch from custom scrapers if enabled
        # if self.custom_scrapers:
        #     for scraper in self.custom_scrapers:
        #         tasks.append(self._safe_fetch(scraper.__class__.__name__, scraper.scrape()))

        # Run all fetches in parallel
        results = await asyncio.gather(*tasks)

        # Aggregate results
        all_articles = []
        for articles in results:
            if articles:  # Filter out None results from failures
                all_articles.extend(articles)

        self.logger.info(
            f"Multi-source fetch complete: {len(all_articles)} total articles from {len(tasks)} sources"
        )

        return all_articles

    async def _safe_fetch(self, source_name: str, fetch_coroutine) -> List[Article]:
        """
        Safely execute a fetch operation with error handling.

        Args:
            source_name: Name of the source for logging
            fetch_coroutine: Coroutine that fetches articles

        Returns:
            List of articles or empty list if fetch fails
        """
        try:
            articles = await fetch_coroutine
            self.logger.info(f"{source_name}: fetched {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"{source_name}: fetch failed - {e}", exc_info=True)
            return []
