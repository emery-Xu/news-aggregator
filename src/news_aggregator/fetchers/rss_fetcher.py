"""RSS feed fetching component for retrieving articles from RSS feeds."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import feedparser
import httpx

from ..models import Article
from ..config import FeedConfig
from ..logger import get_logger


class RSSFetcher:
    """Fetches news articles from RSS feeds."""

    def __init__(self, news_sources: Dict[str, List[FeedConfig]], max_articles_per_topic: int = 15):
        """
        Initialize RSS fetcher.

        Args:
            news_sources: Dictionary mapping topics to list of FeedConfig objects
            max_articles_per_topic: Maximum number of articles to return per topic
        """
        self.news_sources = news_sources
        self.max_articles_per_topic = max_articles_per_topic
        self.logger = get_logger()
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    async def fetch_all_topics(self) -> List[Article]:
        """
        Fetch articles for all configured topics in parallel.

        Returns:
            List of Article objects from all topics
        """
        self.logger.info("Starting to fetch news from RSS feeds for all topics")

        tasks = []
        for topic in self.news_sources.keys():
            task = self.fetch_topic(topic)
            tasks.append(task)

        # Fetch all topics in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_articles = []
        for topic, result in zip(self.news_sources.keys(), results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to fetch RSS for topic '{topic}': {result}")
            else:
                all_articles.extend(result)
                self.logger.info(f"Fetched {len(result)} RSS articles for topic '{topic}'")

        self.logger.info(f"Total RSS articles fetched: {len(all_articles)}")
        return all_articles

    async def fetch_topic(self, topic: str) -> List[Article]:
        """
        Fetch articles for a single topic from all its sources.

        Args:
            topic: Topic name (e.g., 'ai', 'robotics', 'polymarket')

        Returns:
            List of Article objects for this topic
        """
        feeds = self.news_sources.get(topic, [])
        if not feeds:
            self.logger.warning(f"No RSS feeds configured for topic: {topic}")
            return []

        # Filter to only enabled feeds
        enabled_feeds = [feed for feed in feeds if feed.enabled]
        if not enabled_feeds:
            self.logger.warning(f"No enabled RSS feeds for topic: {topic}")
            return []

        self.logger.info(f"Fetching topic '{topic}' from {len(enabled_feeds)} RSS feeds")

        tasks = []
        for feed_config in enabled_feeds:
            task = self._fetch_feed(feed_config, topic)
            tasks.append(task)

        # Fetch all sources in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine and filter results
        articles = []
        for feed_config, result in zip(enabled_feeds, results):
            if isinstance(result, Exception):
                self.logger.warning(f"Failed to fetch from {feed_config.url}: {result}")
            else:
                articles.extend(result)

        # Sort by publish date
        articles.sort(key=lambda a: a.published_at, reverse=True)

        return articles

    async def _fetch_feed(self, feed_config: FeedConfig, topic: str, max_retries: int = 3) -> List[Article]:
        """
        Fetch articles from a single RSS feed with retry logic.

        Args:
            feed_config: FeedConfig object with feed URL and settings
            topic: Topic name for categorization
            max_retries: Maximum number of retry attempts

        Returns:
            List of Article objects from this feed
        """
        async with self.semaphore:  # Limit concurrent requests
            for attempt in range(max_retries):
                try:
                    # Set User-Agent header to avoid 403 Forbidden errors
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }

                    # Fetch RSS feed
                    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
                        response = await client.get(feed_config.url)
                        response.raise_for_status()
                        content = response.text

                    # Parse RSS feed
                    feed = feedparser.parse(content)

                    # Extract source name from feed
                    source_name = feed.feed.get('title', feed_config.url)

                    # Parse articles
                    articles = []
                    for entry in feed.entries:
                        try:
                            article = self._parse_entry(entry, topic, source_name)
                            if article:
                                articles.append(article)
                        except Exception as e:
                            self.logger.debug(f"Failed to parse entry from {feed_config.url}: {e}")
                            continue

                    self.logger.debug(f"Fetched {len(articles)} articles from {feed_config.url}")
                    return articles

                except Exception as e:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {feed_config.url}: {e}")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"All retries failed for {feed_config.url}")
                        return []

            return []

    def _parse_entry(self, entry, topic: str, source_name: str) -> Article:
        """
        Parse a single RSS feed entry into an Article.

        Args:
            entry: feedparser entry object
            topic: Topic name
            source_name: Name of the source feed

        Returns:
            Article object or None if parsing fails
        """
        # Extract URL
        url = entry.get('link', '')
        if not url:
            return None

        # Extract title
        title = entry.get('title', '')
        if not title:
            return None

        # Extract content (try multiple fields)
        content = (
            entry.get('summary', '') or
            entry.get('description', '') or
            entry.get('content', [{}])[0].get('value', '')
        )

        # Basic quality filter - skip very short content
        if len(content) < 100:
            return None

        # Extract publish date
        published_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except:
                pass

        if not published_at:
            # Use current time if no date available
            published_at = datetime.now()

        return Article(
            url=url,
            title=title,
            content=content,
            published_at=published_at,
            topic=topic,
            source=source_name
        )
