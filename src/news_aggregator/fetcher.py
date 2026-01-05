"""News fetching component for retrieving articles from RSS feeds."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import feedparser
import httpx

from .models import Article
from .logger import get_logger


class NewsFetcher:
    """Fetches news articles from RSS feeds."""

    def __init__(self, news_sources: Dict[str, List[str]], max_articles_per_topic: int = 15):
        """
        Initialize news fetcher.

        Args:
            news_sources: Dictionary mapping topics to list of RSS feed URLs
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
        self.logger.info("Starting to fetch news for all topics")

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
                self.logger.error(f"Failed to fetch topic '{topic}': {result}")
            else:
                all_articles.extend(result)
                self.logger.info(f"Fetched {len(result)} articles for topic '{topic}'")

        self.logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles

    async def fetch_topic(self, topic: str) -> List[Article]:
        """
        Fetch articles for a single topic from all its sources.

        Args:
            topic: Topic name (e.g., 'ai', 'robotics', 'polymarket')

        Returns:
            List of Article objects for this topic
        """
        sources = self.news_sources.get(topic, [])
        if not sources:
            self.logger.warning(f"No sources configured for topic: {topic}")
            return []

        self.logger.info(f"Fetching topic '{topic}' from {len(sources)} sources")

        tasks = []
        for source_url in sources:
            task = self._fetch_source(source_url, topic)
            tasks.append(task)

        # Fetch all sources in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine and filter results
        articles = []
        for source_url, result in zip(sources, results):
            if isinstance(result, Exception):
                self.logger.warning(f"Failed to fetch from {source_url}: {result}")
            else:
                articles.extend(result)

        # Filter and sort
        articles = self._filter_quality(articles)
        articles = self._filter_recent(articles)
        articles.sort(key=lambda a: a.published_at, reverse=True)

        # Limit to max articles
        if len(articles) > self.max_articles_per_topic:
            self.logger.info(f"Limiting {topic} from {len(articles)} to {self.max_articles_per_topic} articles")
            articles = articles[:self.max_articles_per_topic]

        return articles

    async def _fetch_source(self, source_url: str, topic: str, max_retries: int = 3) -> List[Article]:
        """
        Fetch articles from a single RSS feed source with retry logic.

        Args:
            source_url: URL of the RSS feed
            topic: Topic name for categorization
            max_retries: Maximum number of retry attempts

        Returns:
            List of Article objects from this source
        """
        async with self.semaphore:  # Limit concurrent requests
            for attempt in range(max_retries):
                try:
                    # Fetch RSS feed
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(source_url)
                        response.raise_for_status()
                        content = response.text

                    # Parse RSS feed
                    feed = feedparser.parse(content)

                    # Extract source name from feed
                    source_name = feed.feed.get('title', source_url)

                    # Parse articles
                    articles = []
                    for entry in feed.entries:
                        try:
                            article = self._parse_entry(entry, topic, source_name)
                            if article:
                                articles.append(article)
                        except Exception as e:
                            self.logger.debug(f"Failed to parse entry from {source_url}: {e}")
                            continue

                    self.logger.debug(f"Fetched {len(articles)} articles from {source_url}")
                    return articles

                except Exception as e:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {source_url}: {e}")

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"All retries failed for {source_url}")
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

    def _filter_quality(self, articles: List[Article]) -> List[Article]:
        """
        Filter out low-quality articles.

        Args:
            articles: List of articles to filter

        Returns:
            Filtered list of articles
        """
        filtered = []
        for article in articles:
            # Skip articles with very short content (likely spam or broken)
            if len(article.content) < 100:
                self.logger.debug(f"Filtered out short article: {article.title}")
                continue

            # Skip articles with missing URL or title
            if not article.url or not article.title:
                self.logger.debug(f"Filtered out article with missing URL/title")
                continue

            filtered.append(article)

        return filtered

    def _filter_recent(self, articles: List[Article], hours: int = 24) -> List[Article]:
        """
        Filter articles to only include recent ones.

        Args:
            articles: List of articles to filter
            hours: Maximum age in hours

        Returns:
            Filtered list of recent articles
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        filtered = [a for a in articles if a.published_at >= cutoff]

        removed_count = len(articles) - len(filtered)
        if removed_count > 0:
            self.logger.debug(f"Filtered out {removed_count} articles older than {hours} hours")

        return filtered
