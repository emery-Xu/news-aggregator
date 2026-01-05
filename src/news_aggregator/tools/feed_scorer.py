"""Feed scoring tool for evaluating RSS feed quality."""

from datetime import datetime, timedelta
from typing import Optional
import feedparser
import httpx

from ..models import FeedScore
from ..logger import get_logger


class FeedScorer:
    """Scores RSS feeds based on update frequency, content quality, and reliability."""

    def __init__(self, timeout: int = 10):
        """
        Initialize feed scorer.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.logger = get_logger()

        # Scoring weights
        self.FREQUENCY_WEIGHT = 0.4
        self.QUALITY_WEIGHT = 0.4
        self.RELIABILITY_WEIGHT = 0.2

    async def score_feed(self, feed_url: str) -> FeedScore:
        """
        Score a feed based on multiple quality factors.

        Args:
            feed_url: URL of the RSS/Atom feed

        Returns:
            FeedScore object with scoring breakdown
        """
        self.logger.info(f"Scoring feed: {feed_url}")

        try:
            # Fetch and parse feed
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(feed_url)
                response.raise_for_status()

                # Parse feed content
                feed = feedparser.parse(response.content)

                # Check for parse errors
                if feed.bozo:
                    error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Parse error"
                    self.logger.warning(f"Feed parse error for {feed_url}: {error_msg}")
                    return FeedScore(
                        url=feed_url,
                        update_frequency=0.0,
                        content_quality=0.0,
                        reliability=0.0,
                        total_score=0.0,
                        recommendation="skip",
                        error=error_msg
                    )

                # Calculate component scores
                frequency_score = self._score_update_frequency(feed)
                quality_score = self._score_content_quality(feed)
                reliability_score = 1.0  # No parse errors = reliable

                # Calculate total score (weighted average)
                total_score = (
                    frequency_score * self.FREQUENCY_WEIGHT +
                    quality_score * self.QUALITY_WEIGHT +
                    reliability_score * self.RELIABILITY_WEIGHT
                )

                # Determine recommendation
                if total_score >= 0.7:
                    recommendation = "add"
                elif total_score >= 0.5:
                    recommendation = "review"
                else:
                    recommendation = "skip"

                self.logger.info(
                    f"Feed {feed_url} scored {total_score:.2f} "
                    f"(freq: {frequency_score:.2f}, quality: {quality_score:.2f}, "
                    f"reliability: {reliability_score:.2f}) -> {recommendation}"
                )

                return FeedScore(
                    url=feed_url,
                    update_frequency=frequency_score,
                    content_quality=quality_score,
                    reliability=reliability_score,
                    total_score=total_score,
                    recommendation=recommendation,
                    error=None
                )

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error fetching {feed_url}: {e}")
            return FeedScore(
                url=feed_url,
                update_frequency=0.0,
                content_quality=0.0,
                reliability=0.0,
                total_score=0.0,
                recommendation="skip",
                error=f"HTTP error: {str(e)}"
            )

        except Exception as e:
            self.logger.error(f"Unexpected error scoring {feed_url}: {e}")
            return FeedScore(
                url=feed_url,
                update_frequency=0.0,
                content_quality=0.0,
                reliability=0.0,
                total_score=0.0,
                recommendation="skip",
                error=f"Error: {str(e)}"
            )

    def _score_update_frequency(self, feed: feedparser.FeedParserDict) -> float:
        """
        Score feed based on update frequency.

        Args:
            feed: Parsed feed object

        Returns:
            Score from 0.0 to 1.0 (1.0 = daily updates, 0.7 = weekly, 0.3 = monthly)
        """
        entries = feed.entries

        if not entries or len(entries) < 2:
            # Not enough data to determine frequency
            return 0.5

        # Get published dates from recent entries (up to 10)
        dates = []
        for entry in entries[:10]:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    date = datetime(*entry.published_parsed[:6])
                    dates.append(date)
                except (TypeError, ValueError):
                    continue
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    date = datetime(*entry.updated_parsed[:6])
                    dates.append(date)
                except (TypeError, ValueError):
                    continue

        if len(dates) < 2:
            # No valid dates found
            return 0.5

        # Sort dates (newest first)
        dates.sort(reverse=True)

        # Calculate average days between posts
        intervals = []
        for i in range(len(dates) - 1):
            delta = dates[i] - dates[i + 1]
            intervals.append(delta.days)

        avg_days = sum(intervals) / len(intervals)

        # Score based on average interval
        if avg_days <= 1:
            # Daily or more frequent
            return 1.0
        elif avg_days <= 3:
            # Every 2-3 days
            return 0.9
        elif avg_days <= 7:
            # Weekly
            return 0.7
        elif avg_days <= 14:
            # Bi-weekly
            return 0.5
        elif avg_days <= 30:
            # Monthly
            return 0.3
        else:
            # Less than monthly
            return 0.1

    def _score_content_quality(self, feed: feedparser.FeedParserDict) -> float:
        """
        Score feed based on content quality (description length).

        Args:
            feed: Parsed feed object

        Returns:
            Score from 0.0 to 1.0 (1.0 = 500+ char descriptions)
        """
        entries = feed.entries

        if not entries:
            return 0.5

        # Calculate average description length
        total_length = 0
        count = 0

        for entry in entries[:10]:  # Check up to 10 recent entries
            description = ""

            if hasattr(entry, 'description'):
                description = entry.description
            elif hasattr(entry, 'summary'):
                description = entry.summary
            elif hasattr(entry, 'content'):
                # Sometimes content is a list
                if isinstance(entry.content, list) and len(entry.content) > 0:
                    description = entry.content[0].value
                else:
                    description = str(entry.content)

            if description:
                # Strip HTML tags for accurate length
                from bs4 import BeautifulSoup
                text = BeautifulSoup(description, 'html.parser').get_text()
                total_length += len(text)
                count += 1

        if count == 0:
            # No descriptions found
            return 0.0

        avg_length = total_length / count

        # Score based on average length
        if avg_length >= 500:
            return 1.0
        elif avg_length >= 300:
            return 0.8
        elif avg_length >= 200:
            return 0.6
        elif avg_length >= 100:
            return 0.4
        elif avg_length >= 50:
            return 0.2
        else:
            return 0.1
