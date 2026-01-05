"""Article ranking and quality filtering component."""

from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

from ..models import Article, RankedArticle
from ..config import Config
from ..logger import get_logger


class ArticleRanker:
    """Ranks and filters articles based on quality metrics."""

    def __init__(self, config: Config):
        """
        Initialize article ranker.

        Args:
            config: Application configuration with topic settings
        """
        self.config = config
        self.topics = config.topics
        self.logger = get_logger()

        # Scoring weights
        self.CONTENT_WEIGHT = 0.4
        self.RECENCY_WEIGHT = 0.3
        self.SOURCE_WEIGHT = 0.3

    def rank_and_filter(self, articles: List[Article]) -> List[RankedArticle]:
        """
        Score all articles, filter by quality threshold, and limit per topic.

        Args:
            articles: List of Article objects to rank and filter

        Returns:
            List of RankedArticle objects (filtered and limited)
        """
        if not articles:
            self.logger.info("No articles to rank")
            return []

        self.logger.info(f"Ranking {len(articles)} articles")

        # Score all articles
        ranked_articles = []
        for article in articles:
            score = self.calculate_score(article)
            ranked_articles.append(RankedArticle(article=article, quality_score=score))

        # Group by topic
        articles_by_topic = defaultdict(list)
        for ranked_article in ranked_articles:
            topic = ranked_article.article.topic
            articles_by_topic[topic].append(ranked_article)

        # Filter and limit per topic
        filtered_articles = []
        total_filtered = 0
        total_limited = 0

        for topic, topic_articles in articles_by_topic.items():
            topic_config = self.topics.get(topic)
            if not topic_config:
                self.logger.warning(f"No config found for topic '{topic}', skipping")
                continue

            # Filter by minimum quality score
            before_filter = len(topic_articles)
            topic_articles = [
                ra for ra in topic_articles
                if ra.quality_score >= topic_config.min_quality_score
            ]
            filtered_count = before_filter - len(topic_articles)
            total_filtered += filtered_count

            # Sort by quality score (descending)
            topic_articles.sort(key=lambda ra: ra.quality_score, reverse=True)

            # Limit to max articles per day
            max_articles = topic_config.max_articles_per_day
            before_limit = len(topic_articles)
            topic_articles = topic_articles[:max_articles]
            limited_count = before_limit - len(topic_articles)
            total_limited += limited_count

            filtered_articles.extend(topic_articles)

            # Log stats for this topic
            self.logger.info(
                f"Topic '{topic}': {len(topic_articles)} articles "
                f"(filtered: {filtered_count}, limited: {limited_count}, "
                f"avg score: {sum(ra.quality_score for ra in topic_articles) / len(topic_articles):.2f})"
                if topic_articles else f"Topic '{topic}': 0 articles after filtering"
            )

        self.logger.info(
            f"Ranking complete: {len(filtered_articles)}/{len(ranked_articles)} articles retained "
            f"(filtered: {total_filtered}, limited: {total_limited})"
        )

        return filtered_articles

    def calculate_score(self, article: Article) -> float:
        """
        Calculate quality score for an article.

        Score is calculated as weighted average of:
        - Content depth (40%): Based on content length
        - Recency (30%): Based on publish time
        - Source trust (30%): Based on trusted sources list

        Args:
            article: Article to score

        Returns:
            Quality score between 0 and 1
        """
        # Content depth score (0-1)
        content_score = self._score_content_depth(article)

        # Recency score (0-1)
        recency_score = self._score_recency(article)

        # Source trust score (0-1)
        source_score = self._score_source_trust(article)

        # Calculate weighted average
        total_score = (
            content_score * self.CONTENT_WEIGHT +
            recency_score * self.RECENCY_WEIGHT +
            source_score * self.SOURCE_WEIGHT
        )

        return round(total_score, 3)

    def _score_content_depth(self, article: Article) -> float:
        """
        Score article based on content depth (length).

        Args:
            article: Article to score

        Returns:
            Score between 0 and 1
        """
        content_length = len(article.content)

        # Score based on content length
        # 0-200 chars: 0.0-0.5 (linear)
        # 200-500 chars: 0.5-0.8 (linear)
        # 500+ chars: 0.8-1.0 (diminishing returns)

        if content_length < 200:
            # Below minimum threshold
            return content_length / 400.0  # Max 0.5
        elif content_length < 500:
            # Good length
            return 0.5 + (content_length - 200) / 1000.0  # 0.5 to 0.8
        else:
            # Excellent length (with diminishing returns)
            extra_length = min(content_length - 500, 1000)
            return 0.8 + (extra_length / 5000.0)  # 0.8 to 1.0

    def _score_recency(self, article: Article) -> float:
        """
        Score article based on recency (how recently published).

        Args:
            article: Article to score

        Returns:
            Score between 0 and 1
        """
        now = datetime.now()
        age = now - article.published_at

        # Score based on age
        # < 24 hours: 1.0
        # 24-48 hours: 0.5
        # 48-72 hours: 0.2
        # > 72 hours: 0.0

        if age < timedelta(hours=24):
            return 1.0
        elif age < timedelta(hours=48):
            return 0.5
        elif age < timedelta(hours=72):
            return 0.2
        else:
            return 0.0

    def _score_source_trust(self, article: Article) -> float:
        """
        Score article based on source trustworthiness.

        Args:
            article: Article to score

        Returns:
            Score between 0 and 1
        """
        topic_config = self.topics.get(article.topic)
        if not topic_config:
            return 0.5  # Default score if topic not configured

        trusted_sources = topic_config.trusted_sources
        if not trusted_sources:
            return 0.5  # No trusted sources configured, neutral score

        # Check if source is in trusted list (case-insensitive partial match)
        source_lower = article.source.lower()
        for trusted_source in trusted_sources:
            if trusted_source.lower() in source_lower or source_lower in trusted_source.lower():
                return 1.0

        # Not in trusted list
        return 0.5
