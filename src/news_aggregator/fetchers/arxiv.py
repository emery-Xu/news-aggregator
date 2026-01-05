"""arXiv API fetcher for academic papers."""

import asyncio
from datetime import datetime, timedelta
from typing import List
import httpx
import feedparser

from ..models import Article
from ..config import ArxivConfig
from ..logger import get_logger


class ArxivFetcher:
    """Fetches academic papers from arXiv API."""

    # arXiv API endpoint
    API_BASE_URL = "https://export.arxiv.org/api/query"

    # Category to topic mapping
    CATEGORY_TO_TOPIC = {
        'cs.AI': 'ai',
        'cs.LG': 'ai',
        'cs.RO': 'robotics'
    }

    def __init__(self, config: ArxivConfig):
        """
        Initialize arXiv fetcher.

        Args:
            config: ArxivConfig with categories and max_per_category
        """
        self.config = config
        self.logger = get_logger()
        self.rate_limit_delay = 3  # 3 seconds between requests per arXiv guidelines

    async def fetch_all(self) -> List[Article]:
        """
        Fetch recent papers from all configured arXiv categories.

        Returns:
            List of Article objects from arXiv
        """
        if not self.config.enabled:
            self.logger.debug("arXiv fetcher is disabled")
            return []

        if not self.config.categories:
            self.logger.warning("No arXiv categories configured")
            return []

        self.logger.info(f"Fetching papers from arXiv categories: {self.config.categories}")

        all_articles = []
        for category in self.config.categories:
            try:
                articles = await self._fetch_category(category)
                all_articles.extend(articles)
                self.logger.info(f"Fetched {len(articles)} papers from arXiv category '{category}'")

                # Rate limiting - wait between requests
                if category != self.config.categories[-1]:  # Don't wait after last category
                    await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                self.logger.error(f"Failed to fetch arXiv category '{category}': {e}")
                continue

        self.logger.info(f"Total arXiv papers fetched: {len(all_articles)}")
        return all_articles

    async def _fetch_category(self, category: str) -> List[Article]:
        """
        Fetch papers from a single arXiv category.

        Args:
            category: arXiv category (e.g., 'cs.AI', 'cs.LG', 'cs.RO')

        Returns:
            List of Article objects
        """
        # Build query URL
        # Search for papers in category, sorted by last updated date, max results per category
        params = {
            'search_query': f'cat:{category}',
            'sortBy': 'lastUpdatedDate',
            'sortOrder': 'descending',
            'max_results': self.config.max_per_category
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(self.API_BASE_URL, params=params)
                response.raise_for_status()
                content = response.text

            # Parse Atom feed
            feed = feedparser.parse(content)

            # Determine topic from category
            topic = self.CATEGORY_TO_TOPIC.get(category, 'ai')

            # Parse entries
            articles = []
            cutoff_date = datetime.now() - timedelta(days=7)  # Only last 7 days

            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, topic, category)
                    if article and article.published_at >= cutoff_date:
                        articles.append(article)
                except Exception as e:
                    self.logger.debug(f"Failed to parse arXiv entry: {e}")
                    continue

            return articles

        except Exception as e:
            self.logger.error(f"Error fetching from arXiv category '{category}': {e}")
            return []

    def _parse_entry(self, entry, topic: str, category: str) -> Article:
        """
        Parse an arXiv entry into an Article.

        Args:
            entry: feedparser entry object from arXiv
            topic: Topic name ('ai' or 'robotics')
            category: arXiv category

        Returns:
            Article object or None if parsing fails
        """
        # Extract URL
        url = entry.get('id', entry.get('link', ''))
        if not url:
            return None

        # Extract title
        title = entry.get('title', '').strip()
        if not title:
            return None

        # Extract abstract (content)
        content = entry.get('summary', '').strip()
        if not content or len(content) < 100:
            return None

        # Extract authors
        authors = []
        if 'authors' in entry:
            authors = [author.get('name', '') for author in entry.authors]
        author_str = ', '.join(authors[:3])  # First 3 authors
        if len(authors) > 3:
            author_str += ' et al.'

        # Add author info to content
        if author_str:
            content = f"Authors: {author_str}\n\n{content}"

        # Extract publish date
        published_at = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except:
                pass

        if not published_at:
            published_at = datetime.now()

        return Article(
            url=url,
            title=title,
            content=content,
            published_at=published_at,
            topic=topic,
            source=f"arXiv ({category})"
        )
