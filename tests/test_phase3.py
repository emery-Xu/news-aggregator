"""Unit tests for Phase 3: Content Quality and Ranking"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
import pytest

from news_aggregator.models import Article, RankedArticle
from news_aggregator.config import Config, TopicConfig, FeedConfig, ArxivConfig, HackerNewsConfig, SummarizationConfig, QualityConfig, SMTPConfig
from news_aggregator.processing.ranker import ArticleRanker
from news_aggregator.processing.deduplicator import Deduplicator, ArticleHistory


class TestArticleRanker:
    """Test ArticleRanker quality scoring and filtering."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for testing."""
        config = Mock(spec=Config)
        config.topics = {
            'ai': TopicConfig(
                audience_level='cs_student',
                include_context=False,
                context_text=None,
                min_quality_score=0.5,
                max_articles_per_day=5,
                trusted_sources=['OpenAI Blog', 'Anthropic News', 'arXiv']
            ),
            'robotics': TopicConfig(
                audience_level='beginner',
                include_context=True,
                context_text='Test context',
                min_quality_score=0.4,
                max_articles_per_day=3,
                trusted_sources=['IEEE Spectrum', 'Robot Report']
            )
        }
        return config

    def test_content_depth_scoring(self, mock_config):
        """Test content depth scoring algorithm."""
        ranker = ArticleRanker(mock_config)

        # Very short content (< 200 chars)
        article_short = Article(
            url="https://example.com/1",
            title="Short Article",
            content="x" * 100,  # 100 chars
            published_at=datetime.now(),
            topic="ai",
            source="Test"
        )
        score_short = ranker._score_content_depth(article_short)
        assert 0.0 <= score_short <= 0.5  # Should be low score

        # Medium content (200-500 chars)
        article_medium = Article(
            url="https://example.com/2",
            title="Medium Article",
            content="x" * 300,  # 300 chars
            published_at=datetime.now(),
            topic="ai",
            source="Test"
        )
        score_medium = ranker._score_content_depth(article_medium)
        assert 0.5 <= score_medium <= 0.8  # Should be medium score

        # Long content (> 500 chars)
        article_long = Article(
            url="https://example.com/3",
            title="Long Article",
            content="x" * 800,  # 800 chars
            published_at=datetime.now(),
            topic="ai",
            source="Test"
        )
        score_long = ranker._score_content_depth(article_long)
        assert 0.8 <= score_long <= 1.0  # Should be high score

    def test_recency_scoring(self, mock_config):
        """Test recency scoring algorithm."""
        ranker = ArticleRanker(mock_config)

        # Very recent (< 24 hours)
        article_recent = Article(
            url="https://example.com/1",
            title="Recent Article",
            content="Test content",
            published_at=datetime.now() - timedelta(hours=12),
            topic="ai",
            source="Test"
        )
        score_recent = ranker._score_recency(article_recent)
        assert score_recent == 1.0

        # 1-2 days old
        article_medium = Article(
            url="https://example.com/2",
            title="Medium Age Article",
            content="Test content",
            published_at=datetime.now() - timedelta(hours=36),
            topic="ai",
            source="Test"
        )
        score_medium = ranker._score_recency(article_medium)
        assert score_medium == 0.5

        # 2-3 days old
        article_old = Article(
            url="https://example.com/3",
            title="Older Article",
            content="Test content",
            published_at=datetime.now() - timedelta(hours=60),
            topic="ai",
            source="Test"
        )
        score_old = ranker._score_recency(article_old)
        assert score_old == 0.2

        # Very old (> 3 days)
        article_very_old = Article(
            url="https://example.com/4",
            title="Very Old Article",
            content="Test content",
            published_at=datetime.now() - timedelta(days=5),
            topic="ai",
            source="Test"
        )
        score_very_old = ranker._score_recency(article_very_old)
        assert score_very_old == 0.0

    def test_source_trust_scoring(self, mock_config):
        """Test source trust scoring algorithm."""
        ranker = ArticleRanker(mock_config)

        # Trusted source
        article_trusted = Article(
            url="https://example.com/1",
            title="Trusted Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="OpenAI Blog"
        )
        score_trusted = ranker._score_source_trust(article_trusted)
        assert score_trusted == 1.0

        # Trusted source (partial match)
        article_trusted_partial = Article(
            url="https://example.com/2",
            title="Trusted Article 2",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Article from Anthropic News"
        )
        score_trusted_partial = ranker._score_source_trust(article_trusted_partial)
        assert score_trusted_partial == 1.0

        # Untrusted source
        article_untrusted = Article(
            url="https://example.com/3",
            title="Untrusted Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Random Blog"
        )
        score_untrusted = ranker._score_source_trust(article_untrusted)
        assert score_untrusted == 0.5

    def test_calculate_score_integration(self, mock_config):
        """Test full score calculation (weighted average)."""
        ranker = ArticleRanker(mock_config)

        # Perfect article: long content, very recent, trusted source
        article_perfect = Article(
            url="https://example.com/1",
            title="Perfect Article",
            content="x" * 1000,  # Long content
            published_at=datetime.now() - timedelta(hours=1),  # Very recent
            topic="ai",
            source="OpenAI Blog"  # Trusted
        )
        score = ranker.calculate_score(article_perfect)
        assert score > 0.9  # Should be very high

        # Poor article: short content, old, untrusted source
        article_poor = Article(
            url="https://example.com/2",
            title="Poor Article",
            content="x" * 50,  # Short content
            published_at=datetime.now() - timedelta(days=5),  # Old
            topic="ai",
            source="Random Blog"  # Untrusted
        )
        score_poor = ranker.calculate_score(article_poor)
        assert score_poor < 0.3  # Should be low

    def test_rank_and_filter_quality_threshold(self, mock_config):
        """Test filtering by minimum quality score."""
        ranker = ArticleRanker(mock_config)

        articles = [
            Article(
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                content="x" * (100 + i * 100),  # Varying content length
                published_at=datetime.now() - timedelta(hours=i),
                topic="ai",
                source="Test Source"
            )
            for i in range(10)
        ]

        ranked = ranker.rank_and_filter(articles)

        # All returned articles should meet minimum quality threshold
        for ranked_article in ranked:
            assert ranked_article.quality_score >= mock_config.topics['ai'].min_quality_score

    def test_rank_and_filter_limit_per_topic(self, mock_config):
        """Test limiting articles per topic."""
        ranker = ArticleRanker(mock_config)

        # Create 10 high-quality AI articles
        articles = [
            Article(
                url=f"https://example.com/ai{i}",
                title=f"AI Article {i}",
                content="x" * 1000,  # Long content
                published_at=datetime.now() - timedelta(hours=i),
                topic="ai",
                source="OpenAI Blog"  # Trusted source
            )
            for i in range(10)
        ]

        ranked = ranker.rank_and_filter(articles)

        # Should be limited to max_articles_per_day (5 for AI)
        ai_articles = [ra for ra in ranked if ra.article.topic == 'ai']
        assert len(ai_articles) <= mock_config.topics['ai'].max_articles_per_day

    def test_rank_and_filter_sorts_by_score(self, mock_config):
        """Test that articles are sorted by quality score."""
        ranker = ArticleRanker(mock_config)

        articles = [
            Article(
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                content="x" * (100 + i * 100),
                published_at=datetime.now() - timedelta(hours=i),
                topic="ai",
                source="OpenAI Blog"
            )
            for i in range(5)
        ]

        ranked = ranker.rank_and_filter(articles)

        # Should be sorted by score (descending)
        for i in range(len(ranked) - 1):
            assert ranked[i].quality_score >= ranked[i + 1].quality_score

    def test_rank_and_filter_multiple_topics(self, mock_config):
        """Test filtering works correctly with multiple topics."""
        ranker = ArticleRanker(mock_config)

        articles = [
            # AI articles (higher quality threshold: 0.5, limit: 5)
            *[Article(
                url=f"https://example.com/ai{i}",
                title=f"AI Article {i}",
                content="x" * 800,
                published_at=datetime.now(),
                topic="ai",
                source="OpenAI Blog"
            ) for i in range(10)],
            # Robotics articles (lower quality threshold: 0.4, limit: 3)
            *[Article(
                url=f"https://example.com/robotics{i}",
                title=f"Robotics Article {i}",
                content="x" * 600,
                published_at=datetime.now(),
                topic="robotics",
                source="IEEE Spectrum"
            ) for i in range(8)]
        ]

        ranked = ranker.rank_and_filter(articles)

        # Check AI articles limit
        ai_articles = [ra for ra in ranked if ra.article.topic == 'ai']
        assert len(ai_articles) <= 5

        # Check Robotics articles limit
        robotics_articles = [ra for ra in ranked if ra.article.topic == 'robotics']
        assert len(robotics_articles) <= 3


class TestDeduplicator:
    """Test Deduplicator with enhanced logging."""

    @pytest.fixture
    def temp_history_file(self):
        """Create temporary history file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Write empty JSON object
            f.write('{}')
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_deduplicate_by_url(self, temp_history_file):
        """Test URL deduplication."""
        dedup = Deduplicator(temp_history_file, similarity_threshold=85)

        articles = [
            Article(url="https://example.com/1", title="Article about AI research", content="Content 1",
                   published_at=datetime.now(), topic="ai", source="Source A"),
            Article(url="https://example.com/1", title="Completely different title about robotics", content="Content 1",
                   published_at=datetime.now(), topic="ai", source="Source B"),  # Same URL, different title
            Article(url="https://example.com/2", title="Another article", content="Content 2",
                   published_at=datetime.now(), topic="ai", source="Source A"),
        ]

        result = dedup.deduplicate(articles)

        # Should have removed 1 URL duplicate
        assert len(result) == 2
        assert dedup.stats['url_duplicates'] == 1

    def test_deduplicate_by_title_similarity_85_percent(self, temp_history_file):
        """Test title similarity deduplication with 85% threshold."""
        dedup = Deduplicator(temp_history_file, similarity_threshold=85)

        articles = [
            Article(url="https://example.com/1", title="OpenAI releases GPT-5 model",
                   content="Content", published_at=datetime.now(), topic="ai", source="Source A"),
            Article(url="https://example.com/2", title="OpenAI releases GPT-5 Model",  # Very similar
                   content="Content", published_at=datetime.now(), topic="ai", source="Source B"),
            Article(url="https://example.com/3", title="Completely different article",
                   content="Content", published_at=datetime.now(), topic="ai", source="Source C"),
        ]

        result = dedup.deduplicate(articles)

        # Should have removed 1 title duplicate
        assert len(result) == 2
        assert dedup.stats['title_duplicates'] == 1

    def test_deduplicate_keeps_earlier_article(self, temp_history_file):
        """Test that deduplicator keeps the earlier published article."""
        dedup = Deduplicator(temp_history_file, similarity_threshold=85)

        now = datetime.now()
        articles = [
            Article(url="https://example.com/1", title="Breaking News",
                   content="Content", published_at=now - timedelta(hours=2),
                   topic="ai", source="Source A"),
            Article(url="https://example.com/2", title="Breaking News",  # Same title
                   content="Content", published_at=now - timedelta(hours=1),  # Published later
                   topic="ai", source="Source B"),
        ]

        result = dedup.deduplicate(articles)

        # Should keep the earlier one
        assert len(result) == 1
        assert result[0].published_at == now - timedelta(hours=2)

    def test_filter_sent_articles(self, temp_history_file):
        """Test filtering previously sent articles."""
        dedup = Deduplicator(temp_history_file, similarity_threshold=85)

        # Add some articles to history
        old_articles = [
            Article(url="https://example.com/old1", title="Old Article 1",
                   content="Content", published_at=datetime.now(), topic="ai", source="Source A"),
            Article(url="https://example.com/old2", title="Old Article 2",
                   content="Content", published_at=datetime.now(), topic="ai", source="Source B"),
        ]
        dedup.history.add_articles(old_articles)

        # Try to deduplicate with some old and some new articles
        articles = [
            Article(url="https://example.com/old1", title="Old Article 1",  # Already sent
                   content="Content", published_at=datetime.now(), topic="ai", source="Source A"),
            Article(url="https://example.com/new1", title="New Article",  # New
                   content="Content", published_at=datetime.now(), topic="ai", source="Source C"),
        ]

        result = dedup.deduplicate(articles)

        # Should filter out 1 previously sent article
        assert len(result) == 1
        assert result[0].url == "https://example.com/new1"
        assert dedup.stats['history_filtered'] == 1

    def test_statistics_tracking(self, temp_history_file):
        """Test that deduplication statistics are tracked correctly."""
        dedup = Deduplicator(temp_history_file, similarity_threshold=85)

        # Add one to history
        dedup.history.add_articles([
            Article(url="https://example.com/sent", title="Sent Article",
                   content="Content", published_at=datetime.now(), topic="ai", source="Source A")
        ])

        articles = [
            # URL duplicate
            Article(url="https://example.com/1", title="Article 1", content="Content",
                   published_at=datetime.now(), topic="ai", source="Source A"),
            Article(url="https://example.com/1", title="Article 1", content="Content",
                   published_at=datetime.now(), topic="ai", source="Source A"),
            # Title duplicate
            Article(url="https://example.com/2", title="Same Title", content="Content",
                   published_at=datetime.now(), topic="ai", source="Source A"),
            Article(url="https://example.com/3", title="Same Title", content="Content",
                   published_at=datetime.now(), topic="ai", source="Source A"),
            # Previously sent
            Article(url="https://example.com/sent", title="Sent Article", content="Content",
                   published_at=datetime.now(), topic="ai", source="Source A"),
            # Unique article
            Article(url="https://example.com/unique", title="Unique Article", content="Content",
                   published_at=datetime.now(), topic="ai", source="Source A"),
        ]

        result = dedup.deduplicate(articles)

        # Should have 3 unique articles (1 from URL dedup, 1 from title dedup, 1 unique)
        # URL duplicate removes 1, title duplicate removes 1, history removes 1 = 3 remaining
        assert len(result) == 3
        # Check statistics
        assert dedup.stats['url_duplicates'] == 1
        assert dedup.stats['title_duplicates'] == 1
        assert dedup.stats['history_filtered'] == 1
