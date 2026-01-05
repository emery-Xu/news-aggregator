"""Deduplication component for removing duplicate and previously sent articles."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set
from fuzzywuzzy import fuzz

from .models import Article, ArticleHistoryEntry
from .logger import get_logger


class ArticleHistory:
    """Manages history of sent articles."""

    def __init__(self, history_file: Path):
        """
        Initialize article history.

        Args:
            history_file: Path to JSON file storing sent articles
        """
        self.history_file = history_file
        self.history: Dict[str, ArticleHistoryEntry] = {}
        self.logger = get_logger()

    def load(self) -> Dict[str, ArticleHistoryEntry]:
        """
        Load history from JSON file.

        Returns:
            Dictionary mapping URLs to history entries
        """
        if not self.history_file.exists():
            self.logger.info(f"History file not found, starting fresh: {self.history_file}")
            return {}

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.history = {
                url: ArticleHistoryEntry.from_dict(entry)
                for url, entry in data.items()
            }

            self.logger.info(f"Loaded {len(self.history)} articles from history")
            return self.history

        except Exception as e:
            self.logger.error(f"Failed to load history file: {e}")
            return {}

    def save(self) -> None:
        """Save current history to JSON file."""
        try:
            # Create directory if it doesn't exist
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to serializable format
            data = {
                url: entry.to_dict()
                for url, entry in self.history.items()
            }

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Saved {len(self.history)} articles to history")

        except Exception as e:
            self.logger.error(f"Failed to save history file: {e}")

    def is_sent(self, url: str) -> bool:
        """
        Check if an article was already sent.

        Args:
            url: Article URL

        Returns:
            True if article was sent before, False otherwise
        """
        return url in self.history

    def add_articles(self, articles: List[Article]) -> None:
        """
        Add newly sent articles to history.

        Args:
            articles: List of articles that were sent
        """
        for article in articles:
            self.history[article.url] = ArticleHistoryEntry(
                url=article.url,
                title=article.title,
                sent_at=datetime.now()
            )

        self.logger.info(f"Added {len(articles)} articles to history")

    def cleanup_old(self, days: int = 30) -> None:
        """
        Remove entries older than specified days.

        Args:
            days: Maximum age of entries to keep
        """
        cutoff = datetime.now() - timedelta(days=days)

        old_count = len(self.history)
        self.history = {
            url: entry
            for url, entry in self.history.items()
            if entry.sent_at >= cutoff
        }
        new_count = len(self.history)

        removed = old_count - new_count
        if removed > 0:
            self.logger.info(f"Removed {removed} old entries from history (older than {days} days)")


class Deduplicator:
    """Removes duplicate articles and filters previously sent items."""

    def __init__(self, history_file: Path, similarity_threshold: int = 80):
        """
        Initialize deduplicator.

        Args:
            history_file: Path to article history file
            similarity_threshold: Minimum similarity score (0-100) for titles to be considered duplicates
        """
        self.history = ArticleHistory(history_file)
        self.similarity_threshold = similarity_threshold
        self.logger = get_logger()

        # Load existing history
        self.history.load()

    def deduplicate(self, articles: List[Article]) -> List[Article]:
        """
        Remove all types of duplicates from article list.

        Args:
            articles: List of articles to deduplicate

        Returns:
            Filtered list without duplicates
        """
        initial_count = len(articles)
        self.logger.info(f"Starting deduplication with {initial_count} articles")

        # Step 1: Remove exact URL duplicates
        articles = self._deduplicate_by_url(articles)
        after_url = len(articles)
        self.logger.info(f"After URL dedup: {after_url} articles ({initial_count - after_url} removed)")

        # Step 2: Remove title similarity duplicates
        articles = self._deduplicate_by_title(articles)
        after_title = len(articles)
        self.logger.info(f"After title dedup: {after_title} articles ({after_url - after_title} removed)")

        # Step 3: Remove previously sent articles
        articles = self._filter_sent(articles)
        final_count = len(articles)
        self.logger.info(f"After history filter: {final_count} articles ({after_title - final_count} removed)")

        self.logger.info(f"Deduplication complete: {initial_count} -> {final_count} articles")
        return articles

    def _deduplicate_by_url(self, articles: List[Article]) -> List[Article]:
        """
        Remove articles with duplicate URLs.

        Args:
            articles: List of articles

        Returns:
            List with unique URLs only
        """
        seen_urls: Set[str] = set()
        unique_articles = []

        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

        return unique_articles

    def _deduplicate_by_title(self, articles: List[Article]) -> List[Article]:
        """
        Remove articles with similar titles using fuzzy matching.

        Args:
            articles: List of articles

        Returns:
            List without near-duplicate titles
        """
        unique_articles = []

        for i, article in enumerate(articles):
            is_duplicate = False

            # Compare with articles already marked as unique
            for unique_article in unique_articles:
                similarity = fuzz.ratio(article.title.lower(), unique_article.title.lower())

                if similarity > self.similarity_threshold:
                    # Keep the one with earlier publication date
                    if article.published_at < unique_article.published_at:
                        # Replace the existing one with the earlier one
                        unique_articles.remove(unique_article)
                        unique_articles.append(article)
                        self.logger.debug(
                            f"Replaced duplicate (similarity: {similarity}%): "
                            f"'{unique_article.title}' with earlier '{article.title}'"
                        )
                    else:
                        self.logger.debug(
                            f"Skipping duplicate (similarity: {similarity}%): '{article.title}'"
                        )
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)

        return unique_articles

    def _filter_sent(self, articles: List[Article]) -> List[Article]:
        """
        Remove articles that were already sent in previous runs.

        Args:
            articles: List of articles

        Returns:
            List containing only new articles
        """
        new_articles = [
            article
            for article in articles
            if not self.history.is_sent(article.url)
        ]

        return new_articles

    def update_history(self, articles: List[Article]) -> None:
        """
        Update history with newly sent articles and clean up old entries.

        Args:
            articles: List of articles that were sent
        """
        self.history.add_articles(articles)
        self.history.cleanup_old(days=30)
        self.history.save()
