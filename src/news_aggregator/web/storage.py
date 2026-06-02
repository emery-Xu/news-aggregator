"""Article storage layer for persisting daily digest data."""

import json
from datetime import date, datetime
from pathlib import Path

from ..logger import get_logger
from ..models import SummarizedArticle


class ArticleStore:
    """Manages per-day article storage in JSON files."""

    def __init__(self, base_dir: Path):
        """
        Initialize article store.

        Args:
            base_dir: Base directory for article storage (e.g., data/articles)
        """
        self.base_dir = base_dir
        self.logger = get_logger()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _date_to_path(self, target_date: date) -> Path:
        """Convert date to file path."""
        return self.base_dir / f"{target_date.isoformat()}.json"

    def save_articles(
        self, articles: list[SummarizedArticle], target_date: date | None = None
    ) -> Path:
        """
        Save articles for a specific date.

        Args:
            articles: List of summarized articles to save
            target_date: Date for the articles (defaults to today)

        Returns:
            Path to the saved file
        """
        if target_date is None:
            target_date = date.today()

        file_path = self._date_to_path(target_date)

        data = {
            "date": target_date.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "articles": [article.to_dict() for article in articles],
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(articles)} articles to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to save articles to {file_path}: {e}")
            raise

    def load_articles(self, target_date: date) -> list[dict]:
        """
        Load articles for a specific date.

        Args:
            target_date: Date to load articles for

        Returns:
            List of article dictionaries
        """
        file_path = self._date_to_path(target_date)

        if not file_path.exists():
            self.logger.debug(f"No articles found for {target_date}")
            return []

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("articles", [])
        except Exception as e:
            self.logger.error(f"Failed to load articles from {file_path}: {e}")
            return []

    def list_available_dates(self) -> list[date]:
        """
        List all dates with available article data.

        Returns:
            Sorted list of dates (newest first)
        """
        dates: list[date] = []

        if not self.base_dir.exists():
            return dates

        for file_path in self.base_dir.glob("*.json"):
            try:
                date_str = file_path.stem
                target_date = date.fromisoformat(date_str)
                dates.append(target_date)
            except ValueError:
                self.logger.debug(f"Skipping invalid file: {file_path.name}")

        return sorted(dates, reverse=True)

    def get_latest_date(self) -> date | None:
        """
        Get the most recent date with article data.

        Returns:
            Latest date or None if no data exists
        """
        dates = self.list_available_dates()
        return dates[0] if dates else None

    def get_article_count(self, target_date: date) -> int:
        """
        Get the number of articles for a specific date.

        Args:
            target_date: Date to check

        Returns:
            Number of articles
        """
        return len(self.load_articles(target_date))
