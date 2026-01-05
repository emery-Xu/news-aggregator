"""Hacker News API fetcher for trending tech stories."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import httpx

from ..models import Article
from ..config import HackerNewsConfig
from ..logger import get_logger


class HackerNewsFetcher:
    """Fetches trending tech stories from Hacker News."""

    # Hacker News API endpoints
    TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

    def __init__(self, config: HackerNewsConfig):
        """
        Initialize Hacker News fetcher.

        Args:
            config: HackerNewsConfig with filters and keywords
        """
        self.config = config
        self.logger = get_logger()
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    async def fetch_all(self) -> List[Article]:
        """
        Fetch trending stories from Hacker News matching configured keywords.

        Returns:
            List of Article objects from Hacker News
        """
        if not self.config.enabled:
            self.logger.debug("Hacker News fetcher is disabled")
            return []

        if not self.config.keywords:
            self.logger.warning("No Hacker News keywords configured")
            return []

        self.logger.info("Fetching trending stories from Hacker News")

        try:
            # Get top story IDs
            story_ids = await self._fetch_top_story_ids()
            self.logger.debug(f"Retrieved {len(story_ids)} top story IDs from Hacker News")

            # Fetch story details in parallel (limit to first 100 to avoid rate limits)
            story_ids = story_ids[:100]
            tasks = [self._fetch_story(story_id) for story_id in story_ids]
            stories = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter and parse valid stories
            articles = []
            cutoff_time = datetime.now() - timedelta(hours=self.config.max_age_hours)

            for story in stories:
                if isinstance(story, Exception) or story is None:
                    continue

                # Filter by score, age, URL presence, and keywords
                if self._matches_filters(story, cutoff_time):
                    article = self._parse_story(story)
                    if article:
                        articles.append(article)

            self.logger.info(f"Total Hacker News stories fetched: {len(articles)}")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching from Hacker News: {e}")
            return []

    async def _fetch_top_story_ids(self) -> List[int]:
        """
        Fetch list of top story IDs from Hacker News.

        Returns:
            List of story IDs
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.TOP_STORIES_URL)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch top story IDs: {e}")
            return []

    async def _fetch_story(self, story_id: int) -> Optional[Dict]:
        """
        Fetch details for a single story.

        Args:
            story_id: Hacker News story ID

        Returns:
            Story dictionary or None if fetch fails
        """
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    url = self.ITEM_URL.format(item_id=story_id)
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                self.logger.debug(f"Failed to fetch story {story_id}: {e}")
                return None

    def _matches_filters(self, story: Dict, cutoff_time: datetime) -> bool:
        """
        Check if story matches configured filters.

        Args:
            story: Story dictionary from HN API
            cutoff_time: Minimum publish time

        Returns:
            True if story matches all filters
        """
        # Must have minimum score
        score = story.get('score', 0)
        if score < self.config.min_score:
            return False

        # Must have a URL (not "Ask HN" posts)
        if 'url' not in story or not story['url']:
            return False

        # Must be within age limit
        timestamp = story.get('time', 0)
        if timestamp:
            story_time = datetime.fromtimestamp(timestamp)
            if story_time < cutoff_time:
                return False

        # Must match at least one keyword
        title = story.get('title', '').lower()
        if not any(keyword.lower() in title for keyword in self.config.keywords):
            return False

        return True

    def _parse_story(self, story: Dict) -> Optional[Article]:
        """
        Parse a Hacker News story into an Article.

        Args:
            story: Story dictionary from HN API

        Returns:
            Article object or None if parsing fails
        """
        try:
            url = story.get('url', '')
            title = story.get('title', '')

            if not url or not title:
                return None

            # Determine topic from keywords
            title_lower = title.lower()
            topic = 'ai'  # Default topic
            if any(kw in title_lower for kw in ['robot', 'robotic', 'drone']):
                topic = 'robotics'

            # Build content from HN metadata
            score = story.get('score', 0)
            descendants = story.get('descendants', 0)  # Number of comments
            hn_url = f"https://news.ycombinator.com/item?id={story.get('id', '')}"

            content = f"Hacker News: {score} points, {descendants} comments.\n\n"
            content += f"Discuss on HN: {hn_url}"

            # Parse timestamp
            timestamp = story.get('time', 0)
            if timestamp:
                published_at = datetime.fromtimestamp(timestamp)
            else:
                published_at = datetime.now()

            return Article(
                url=url,
                title=title,
                content=content,
                published_at=published_at,
                topic=topic,
                source="Hacker News"
            )

        except Exception as e:
            self.logger.debug(f"Failed to parse story: {e}")
            return None
