"""Unit tests for Phase 2: Content Source Expansion"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import pytest

from news_aggregator.models import Article
from news_aggregator.config import FeedConfig, ArxivConfig, HackerNewsConfig, Config
from news_aggregator.fetchers.rss_fetcher import RSSFetcher
from news_aggregator.fetchers.arxiv import ArxivFetcher
from news_aggregator.fetchers.hacker_news import HackerNewsFetcher
from news_aggregator.fetchers.web_scraper import WebScraperBase
from news_aggregator.fetchers.multi_source import MultiSourceFetcher


class TestRSSFetcher:
    """Test RSSFetcher with FeedConfig."""

    @pytest.fixture
    def feed_configs(self):
        """Create sample feed configurations."""
        return {
            'ai': [
                FeedConfig(url="https://example.com/ai-feed1.xml", priority="high", enabled=True),
                FeedConfig(url="https://example.com/ai-feed2.xml", priority="medium", enabled=True),
                FeedConfig(url="https://example.com/ai-feed3.xml", priority="low", enabled=False),  # Disabled
            ],
            'robotics': [
                FeedConfig(url="https://example.com/robotics-feed.xml", priority="high", enabled=True),
            ]
        }

    @pytest.mark.asyncio
    async def test_fetch_topic_filters_disabled_feeds(self, feed_configs):
        """Test that disabled feeds are not fetched."""
        fetcher = RSSFetcher(news_sources=feed_configs, max_articles_per_topic=10)

        # Mock the _fetch_feed method
        fetcher._fetch_feed = AsyncMock(return_value=[])

        # Fetch AI topic (has 2 enabled, 1 disabled)
        await fetcher.fetch_topic('ai')

        # Should only call _fetch_feed for enabled feeds (2 times)
        assert fetcher._fetch_feed.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_all_topics(self, feed_configs):
        """Test fetching from all topics."""
        fetcher = RSSFetcher(news_sources=feed_configs, max_articles_per_topic=10)

        # Mock fetch_topic
        fetcher.fetch_topic = AsyncMock(side_effect=[
            [Mock(spec=Article) for _ in range(5)],  # AI returns 5 articles
            [Mock(spec=Article) for _ in range(3)],  # Robotics returns 3 articles
        ])

        articles = await fetcher.fetch_all_topics()

        # Should have called fetch_topic for each topic
        assert fetcher.fetch_topic.call_count == 2
        # Should have 8 total articles
        assert len(articles) == 8


class TestArxivFetcher:
    """Test ArxivFetcher for academic papers."""

    @pytest.fixture
    def arxiv_config(self):
        """Create ArxivConfig."""
        return ArxivConfig(
            enabled=True,
            categories=['cs.AI', 'cs.LG', 'cs.RO'],
            max_per_category=5
        )

    @pytest.mark.asyncio
    async def test_fetch_disabled(self):
        """Test that disabled config returns empty list."""
        config = ArxivConfig(enabled=False, categories=[], max_per_category=5)
        fetcher = ArxivFetcher(config)

        articles = await fetcher.fetch_all()

        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_fetch_all_categories(self, arxiv_config):
        """Test fetching from all categories."""
        fetcher = ArxivFetcher(arxiv_config)

        # Mock _fetch_category
        fetcher._fetch_category = AsyncMock(side_effect=[
            [Mock(spec=Article, topic='ai') for _ in range(3)],  # cs.AI
            [Mock(spec=Article, topic='ai') for _ in range(2)],  # cs.LG
            [Mock(spec=Article, topic='robotics') for _ in range(4)],  # cs.RO
        ])

        articles = await fetcher.fetch_all()

        # Should call _fetch_category 3 times
        assert fetcher._fetch_category.call_count == 3
        # Should have 9 total articles
        assert len(articles) == 9

    def test_category_to_topic_mapping(self):
        """Test that arXiv categories map to correct topics."""
        assert ArxivFetcher.CATEGORY_TO_TOPIC['cs.AI'] == 'ai'
        assert ArxivFetcher.CATEGORY_TO_TOPIC['cs.LG'] == 'ai'
        assert ArxivFetcher.CATEGORY_TO_TOPIC['cs.RO'] == 'robotics'

    @pytest.mark.asyncio
    async def test_rate_limiting(self, arxiv_config):
        """Test that rate limiting is applied between requests."""
        fetcher = ArxivFetcher(arxiv_config)
        fetcher._fetch_category = AsyncMock(return_value=[])

        start_time = asyncio.get_event_loop().time()
        await fetcher.fetch_all()
        end_time = asyncio.get_event_loop().time()

        # Should have waited at least 2 * rate_limit_delay (3 seconds each, between 3 categories)
        # Actually 2 delays since we don't wait after the last one
        min_expected_time = 2 * fetcher.rate_limit_delay
        assert end_time - start_time >= min_expected_time - 0.5  # Allow some tolerance


class TestHackerNewsFetcher:
    """Test HackerNewsFetcher for trending stories."""

    @pytest.fixture
    def hn_config(self):
        """Create HackerNewsConfig."""
        return HackerNewsConfig(
            enabled=True,
            min_score=50,
            max_age_hours=48,
            keywords=['ai', 'machine learning', 'robotics']
        )

    @pytest.mark.asyncio
    async def test_fetch_disabled(self):
        """Test that disabled config returns empty list."""
        config = HackerNewsConfig(enabled=False, min_score=50, max_age_hours=48, keywords=[])
        fetcher = HackerNewsFetcher(config)

        articles = await fetcher.fetch_all()

        assert len(articles) == 0

    def test_matches_filters_score(self, hn_config):
        """Test that stories with low scores are filtered out."""
        fetcher = HackerNewsFetcher(hn_config)
        cutoff_time = datetime.now() - timedelta(hours=48)

        # Story with low score
        story = {
            'score': 30,  # Below min_score of 50
            'url': 'https://example.com',
            'title': 'AI breakthrough',
            'time': datetime.now().timestamp()
        }

        assert fetcher._matches_filters(story, cutoff_time) is False

    def test_matches_filters_no_url(self, hn_config):
        """Test that stories without URLs are filtered out (Ask HN posts)."""
        fetcher = HackerNewsFetcher(hn_config)
        cutoff_time = datetime.now() - timedelta(hours=48)

        # Story without URL (Ask HN post)
        story = {
            'score': 100,
            'title': 'Ask HN: What AI tools do you use?',
            'time': datetime.now().timestamp()
        }

        assert fetcher._matches_filters(story, cutoff_time) is False

    def test_matches_filters_age(self, hn_config):
        """Test that old stories are filtered out."""
        fetcher = HackerNewsFetcher(hn_config)
        cutoff_time = datetime.now() - timedelta(hours=48)

        # Old story
        old_time = datetime.now() - timedelta(hours=72)
        story = {
            'score': 100,
            'url': 'https://example.com',
            'title': 'AI breakthrough',
            'time': old_time.timestamp()
        }

        assert fetcher._matches_filters(story, cutoff_time) is False

    def test_matches_filters_keywords(self, hn_config):
        """Test that stories without matching keywords are filtered out."""
        fetcher = HackerNewsFetcher(hn_config)
        cutoff_time = datetime.now() - timedelta(hours=48)

        # Story without matching keywords
        story = {
            'score': 100,
            'url': 'https://example.com',
            'title': 'New JavaScript framework released',
            'time': datetime.now().timestamp()
        }

        assert fetcher._matches_filters(story, cutoff_time) is False

    def test_matches_filters_success(self, hn_config):
        """Test that valid stories pass all filters."""
        fetcher = HackerNewsFetcher(hn_config)
        cutoff_time = datetime.now() - timedelta(hours=48)

        # Valid story
        story = {
            'score': 150,
            'url': 'https://example.com',
            'title': 'New AI model achieves breakthrough performance',
            'time': datetime.now().timestamp()
        }

        assert fetcher._matches_filters(story, cutoff_time) is True


class TestWebScraperBase:
    """Test WebScraperBase abstract class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that WebScraperBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WebScraperBase()

    @pytest.mark.asyncio
    async def test_custom_scraper_implementation(self):
        """Test implementing a custom scraper."""

        # Create concrete implementation
        class TestScraper(WebScraperBase):
            async def scrape(self) -> list:
                return [Article(
                    url="https://test.com/article",
                    title="Test Article",
                    content="Test content",
                    published_at=datetime.now(),
                    topic="ai",
                    source="Test Scraper"
                )]

        scraper = TestScraper()
        articles = await scraper.scrape()

        assert len(articles) == 1
        assert articles[0].title == "Test Article"


class TestMultiSourceFetcher:
    """Test MultiSourceFetcher coordinator."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config for MultiSourceFetcher."""
        config = Mock(spec=Config)
        config.news_sources = {
            'ai': [FeedConfig(url="https://example.com/feed.xml", priority="high", enabled=True)]
        }
        config.max_articles_per_topic = 10
        config.arxiv = ArxivConfig(enabled=True, categories=['cs.AI'], max_per_category=5)
        config.hacker_news = HackerNewsConfig(enabled=True, min_score=50, max_age_hours=48, keywords=['ai'])
        config.custom_scrapers_enabled = False
        return config

    @pytest.mark.asyncio
    async def test_fetch_all_sources(self, mock_config):
        """Test fetching from all enabled sources."""
        fetcher = MultiSourceFetcher(mock_config)

        # Mock individual fetchers
        fetcher.rss_fetcher.fetch_all_topics = AsyncMock(return_value=[
            Mock(spec=Article) for _ in range(5)
        ])
        fetcher.arxiv_fetcher.fetch_all = AsyncMock(return_value=[
            Mock(spec=Article) for _ in range(3)
        ])
        fetcher.hn_fetcher.fetch_all = AsyncMock(return_value=[
            Mock(spec=Article) for _ in range(2)
        ])

        articles = await fetcher.fetch_all()

        # Should have called all fetchers
        assert fetcher.rss_fetcher.fetch_all_topics.called
        assert fetcher.arxiv_fetcher.fetch_all.called
        assert fetcher.hn_fetcher.fetch_all.called

        # Should have 10 total articles (5 + 3 + 2)
        assert len(articles) == 10

    @pytest.mark.asyncio
    async def test_fetch_handles_failures_gracefully(self, mock_config):
        """Test that failures in one source don't affect others."""
        fetcher = MultiSourceFetcher(mock_config)

        # Mock individual fetchers - one fails
        fetcher.rss_fetcher.fetch_all_topics = AsyncMock(return_value=[
            Mock(spec=Article) for _ in range(5)
        ])
        fetcher.arxiv_fetcher.fetch_all = AsyncMock(side_effect=Exception("arXiv API error"))
        fetcher.hn_fetcher.fetch_all = AsyncMock(return_value=[
            Mock(spec=Article) for _ in range(2)
        ])

        articles = await fetcher.fetch_all()

        # Should still have articles from RSS and HN (5 + 2 = 7)
        assert len(articles) == 7

    @pytest.mark.asyncio
    async def test_disabled_sources_not_fetched(self):
        """Test that disabled sources are not initialized or fetched."""
        config = Mock(spec=Config)
        config.news_sources = {
            'ai': [FeedConfig(url="https://example.com/feed.xml", priority="high", enabled=True)]
        }
        config.max_articles_per_topic = 10
        config.arxiv = ArxivConfig(enabled=False, categories=[], max_per_category=5)  # Disabled
        config.hacker_news = HackerNewsConfig(enabled=False, min_score=50, max_age_hours=48, keywords=[])  # Disabled
        config.custom_scrapers_enabled = False

        fetcher = MultiSourceFetcher(config)

        # Disabled fetchers should be None
        assert fetcher.arxiv_fetcher is None
        assert fetcher.hn_fetcher is None

        # Mock RSS fetcher
        fetcher.rss_fetcher.fetch_all_topics = AsyncMock(return_value=[
            Mock(spec=Article) for _ in range(5)
        ])

        articles = await fetcher.fetch_all()

        # Should only have RSS articles
        assert len(articles) == 5
