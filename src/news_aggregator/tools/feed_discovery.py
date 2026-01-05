"""Feed discovery tool for finding RSS/Atom feeds on websites."""

import asyncio
from typing import List
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import feedparser

from ..models import DiscoveredFeed
from ..logger import get_logger


class FeedDiscovery:
    """Discovers RSS and Atom feeds from website domains."""

    # Common feed paths to try
    COMMON_PATHS = [
        '/rss',
        '/feed',
        '/feed.xml',
        '/atom.xml',
        '/rss.xml',
        '/blog/rss',
        '/blog/feed',
        '/news/rss',
        '/news/feed',
        '/feeds/posts/default',  # Blogger
        '/?feed=rss2',  # WordPress
    ]

    def __init__(self, timeout: int = 10, max_retries: int = 2):
        """
        Initialize feed discovery tool.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_logger()

    async def discover(self, domain: str) -> List[DiscoveredFeed]:
        """
        Discover RSS/Atom feeds for a given domain.

        Args:
            domain: Domain or URL to search (e.g., "example.com" or "https://example.com")

        Returns:
            List of DiscoveredFeed objects with feed metadata
        """
        # Normalize domain to URL
        if not domain.startswith(('http://', 'https://')):
            domain = f'https://{domain}'

        self.logger.info(f"Discovering feeds for {domain}")

        discovered_feeds = []

        # Step 1: Try common feed paths
        common_path_feeds = await self._try_common_paths(domain)
        discovered_feeds.extend(common_path_feeds)

        # Step 2: Parse homepage HTML for feed links
        homepage_feeds = await self._parse_homepage_links(domain)
        discovered_feeds.extend(homepage_feeds)

        # Remove duplicates (by URL)
        unique_feeds = self._deduplicate_feeds(discovered_feeds)

        self.logger.info(
            f"Discovered {len(unique_feeds)} unique feeds for {domain} "
            f"({sum(1 for f in unique_feeds if f.is_valid)} valid)"
        )

        return unique_feeds

    async def _try_common_paths(self, base_url: str) -> List[DiscoveredFeed]:
        """
        Try common feed paths.

        Args:
            base_url: Base URL of the website

        Returns:
            List of discovered feeds
        """
        feeds = []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            tasks = []
            for path in self.COMMON_PATHS:
                feed_url = urljoin(base_url, path)
                tasks.append(self._validate_feed(client, feed_url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, DiscoveredFeed):
                    feeds.append(result)

        return feeds

    async def _parse_homepage_links(self, url: str) -> List[DiscoveredFeed]:
        """
        Parse homepage HTML for feed link tags.

        Args:
            url: Homepage URL

        Returns:
            List of discovered feeds
        """
        feeds = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find feed link tags
                feed_links = soup.find_all('link', type=['application/rss+xml', 'application/atom+xml'])

                if feed_links:
                    self.logger.debug(f"Found {len(feed_links)} feed link tags in HTML")

                # Validate each feed link
                tasks = []
                for link in feed_links:
                    feed_url = link.get('href')
                    if feed_url:
                        # Make absolute URL
                        feed_url = urljoin(url, feed_url)
                        tasks.append(self._validate_feed(client, feed_url))

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, DiscoveredFeed):
                            feeds.append(result)

        except httpx.HTTPError as e:
            self.logger.warning(f"Failed to fetch homepage {url}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing homepage {url}: {e}")

        return feeds

    async def _validate_feed(self, client: httpx.AsyncClient, feed_url: str) -> DiscoveredFeed:
        """
        Validate a feed URL by fetching and parsing it.

        Args:
            client: HTTP client
            feed_url: Feed URL to validate

        Returns:
            DiscoveredFeed object with validation results
        """
        try:
            # Fetch feed
            response = await client.get(feed_url)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            # Check if it's a valid feed
            if feed.bozo:
                # Parse error
                error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Parse error"
                self.logger.debug(f"Invalid feed {feed_url}: {error_msg}")
                return DiscoveredFeed(
                    url=feed_url,
                    is_valid=False,
                    entry_count=0,
                    error=error_msg
                )

            # Valid feed
            entry_count = len(feed.entries)
            self.logger.debug(f"Valid feed {feed_url}: {entry_count} entries")

            return DiscoveredFeed(
                url=feed_url,
                is_valid=True,
                entry_count=entry_count,
                error=None
            )

        except httpx.HTTPStatusError as e:
            # HTTP error (404, 500, etc.)
            return DiscoveredFeed(
                url=feed_url,
                is_valid=False,
                entry_count=0,
                error=f"HTTP {e.response.status_code}"
            )

        except httpx.TimeoutException:
            return DiscoveredFeed(
                url=feed_url,
                is_valid=False,
                entry_count=0,
                error="Timeout"
            )

        except httpx.HTTPError as e:
            return DiscoveredFeed(
                url=feed_url,
                is_valid=False,
                entry_count=0,
                error=str(e)
            )

        except Exception as e:
            self.logger.error(f"Unexpected error validating {feed_url}: {e}")
            return DiscoveredFeed(
                url=feed_url,
                is_valid=False,
                entry_count=0,
                error=f"Error: {str(e)}"
            )

    def _deduplicate_feeds(self, feeds: List[DiscoveredFeed]) -> List[DiscoveredFeed]:
        """
        Remove duplicate feeds (by URL).

        Args:
            feeds: List of feeds

        Returns:
            List with duplicates removed
        """
        seen_urls = set()
        unique_feeds = []

        for feed in feeds:
            if feed.url not in seen_urls:
                seen_urls.add(feed.url)
                unique_feeds.append(feed)

        return unique_feeds
