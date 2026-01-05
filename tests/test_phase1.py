"""Unit tests for Phase 1: Configuration and Data Models"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from news_aggregator.config import (
    Config,
    ConfigError,
    TopicConfig,
    FeedConfig,
    ArxivConfig,
    HackerNewsConfig,
    SummarizationConfig,
    QualityConfig,
    SMTPConfig,
    load_config,
    validate_config
)
from news_aggregator.models import (
    Article,
    RankedArticle,
    SummarizedArticle,
    DiscoveredFeed,
    FeedScore
)


class TestDataModels:
    """Test new and updated data models."""

    def test_ranked_article_creation(self):
        """Test RankedArticle dataclass creation."""
        article = Article(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )
        ranked = RankedArticle(article=article, quality_score=0.85)

        assert ranked.article == article
        assert ranked.quality_score == 0.85

    def test_ranked_article_serialization(self):
        """Test RankedArticle to_dict and from_dict."""
        article = Article(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            published_at=datetime(2024, 1, 1, 12, 0),
            topic="ai",
            source="Test Source"
        )
        ranked = RankedArticle(article=article, quality_score=0.75)

        # Serialize
        data = ranked.to_dict()
        assert data['quality_score'] == 0.75
        assert 'article' in data
        assert data['article']['url'] == article.url

        # Deserialize
        ranked_restored = RankedArticle.from_dict(data)
        assert ranked_restored.quality_score == 0.75
        assert ranked_restored.article.url == article.url

    def test_summarized_article_with_audience_level(self):
        """Test SummarizedArticle with new audience_level field."""
        article = Article(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )

        # Test beginner audience
        summarized_beginner = SummarizedArticle.from_article(
            article,
            summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
            audience_level="beginner"
        )
        assert summarized_beginner.audience_level == "beginner"
        assert len(summarized_beginner.summary_bullets) == 3

        # Test CS student audience
        summarized_cs = SummarizedArticle.from_article(
            article,
            summary_bullets=["Technical bullet 1", "Technical bullet 2"],
            audience_level="cs_student"
        )
        assert summarized_cs.audience_level == "cs_student"
        assert len(summarized_cs.summary_bullets) == 2

    def test_summarized_article_serialization(self):
        """Test SummarizedArticle serialization with audience_level."""
        article = Article(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            published_at=datetime(2024, 1, 1, 12, 0),
            topic="robotics",
            source="Test Source"
        )

        summarized = SummarizedArticle.from_article(
            article,
            summary_bullets=["Bullet 1", "Bullet 2"],
            audience_level="beginner"
        )

        # Serialize
        data = summarized.to_dict()
        assert data['audience_level'] == "beginner"
        assert data['summary_bullets'] == ["Bullet 1", "Bullet 2"]
        assert data['url'] == article.url

    def test_discovered_feed_model(self):
        """Test DiscoveredFeed dataclass."""
        # Valid feed
        feed_valid = DiscoveredFeed(
            url="https://example.com/feed.xml",
            is_valid=True,
            entry_count=10
        )
        assert feed_valid.is_valid is True
        assert feed_valid.entry_count == 10
        assert feed_valid.error is None

        # Invalid feed
        feed_invalid = DiscoveredFeed(
            url="https://example.com/bad-feed.xml",
            is_valid=False,
            error="Parse error"
        )
        assert feed_invalid.is_valid is False
        assert feed_invalid.error == "Parse error"

    def test_feed_score_model(self):
        """Test FeedScore dataclass."""
        score = FeedScore(
            url="https://example.com/feed.xml",
            update_frequency=0.9,
            content_quality=0.85,
            reliability=1.0,
            total_score=0.88,
            recommendation="add"
        )

        assert score.update_frequency == 0.9
        assert score.content_quality == 0.85
        assert score.reliability == 1.0
        assert score.total_score == 0.88
        assert score.recommendation == "add"


class TestConfigModels:
    """Test new configuration dataclasses."""

    def test_topic_config(self):
        """Test TopicConfig dataclass."""
        topic_config = TopicConfig(
            audience_level="beginner",
            include_context=True,
            context_text="Test context",
            min_quality_score=0.5,
            max_articles_per_day=10,
            trusted_sources=["Source 1", "Source 2"]
        )

        assert topic_config.audience_level == "beginner"
        assert topic_config.include_context is True
        assert topic_config.context_text == "Test context"
        assert topic_config.min_quality_score == 0.5
        assert topic_config.max_articles_per_day == 10
        assert len(topic_config.trusted_sources) == 2

    def test_feed_config(self):
        """Test FeedConfig dataclass."""
        # Default values
        feed1 = FeedConfig(url="https://example.com/feed.xml")
        assert feed1.priority == "medium"
        assert feed1.enabled is True

        # Custom values
        feed2 = FeedConfig(
            url="https://example.com/feed2.xml",
            priority="high",
            enabled=False
        )
        assert feed2.priority == "high"
        assert feed2.enabled is False

    def test_arxiv_config(self):
        """Test ArxivConfig dataclass."""
        arxiv_config = ArxivConfig(
            enabled=True,
            categories=['cs.AI', 'cs.LG'],
            max_per_category=5
        )

        assert arxiv_config.enabled is True
        assert len(arxiv_config.categories) == 2
        assert arxiv_config.max_per_category == 5

    def test_hacker_news_config(self):
        """Test HackerNewsConfig dataclass."""
        hn_config = HackerNewsConfig(
            enabled=True,
            min_score=50,
            max_age_hours=48,
            keywords=['ai', 'ml', 'robotics']
        )

        assert hn_config.enabled is True
        assert hn_config.min_score == 50
        assert hn_config.max_age_hours == 48
        assert len(hn_config.keywords) == 3

    def test_summarization_config(self):
        """Test SummarizationConfig dataclass."""
        summ_config = SummarizationConfig(
            beginner_prompt_path="config/prompts/beginner.txt",
            cs_student_prompt_path="config/prompts/cs_student.txt",
            max_tokens=500,
            temperature=0.3
        )

        assert summ_config.beginner_prompt_path == "config/prompts/beginner.txt"
        assert summ_config.cs_student_prompt_path == "config/prompts/cs_student.txt"
        assert summ_config.max_tokens == 500
        assert summ_config.temperature == 0.3

    def test_quality_config(self):
        """Test QualityConfig dataclass."""
        quality_config = QualityConfig(
            min_content_length=200,
            dedup_title_threshold=0.85,
            history_days=30
        )

        assert quality_config.min_content_length == 200
        assert quality_config.dedup_title_threshold == 0.85
        assert quality_config.history_days == 30


class TestConfigLoading:
    """Test configuration loading and validation."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # Create prompt files
            prompts_dir = config_dir / "prompts"
            prompts_dir.mkdir()

            (prompts_dir / "beginner.txt").write_text("Beginner prompt template")
            (prompts_dir / "cs_student.txt").write_text("CS student prompt template")

            yield config_dir

    def create_valid_config(self, config_dir: Path) -> Path:
        """Create a valid config.yaml file."""
        config_data = {
            'topics': {
                'polymarket': {
                    'audience_level': 'beginner',
                    'include_context': True,
                    'context_text': 'Polymarket context',
                    'min_quality_score': 0.5,
                    'max_articles_per_day': 10,
                    'trusted_sources': ['Source 1']
                },
                'robotics': {
                    'audience_level': 'beginner',
                    'include_context': True,
                    'context_text': 'Robotics context',
                    'min_quality_score': 0.5,
                    'max_articles_per_day': 10,
                    'trusted_sources': ['Source 2']
                },
                'ai': {
                    'audience_level': 'cs_student',
                    'include_context': False,
                    'context_text': None,
                    'min_quality_score': 0.6,
                    'max_articles_per_day': 10,
                    'trusted_sources': ['Source 3']
                }
            },
            'news_sources': {
                'polymarket': [
                    {'url': 'https://example.com/feed1.xml', 'priority': 'high', 'enabled': True}
                ],
                'robotics': [
                    {'url': 'https://example.com/feed2.xml', 'priority': 'medium', 'enabled': True}
                ],
                'ai': [
                    {'url': 'https://example.com/feed3.xml', 'priority': 'high', 'enabled': True}
                ]
            },
            'alternative_sources': {
                'arxiv': {'enabled': False, 'categories': ['cs.AI'], 'max_per_category': 5},
                'hacker_news': {'enabled': False, 'min_score': 50, 'max_age_hours': 48, 'keywords': ['ai']},
                'custom_scrapers': {'enabled': False}
            },
            'summarization': {
                'beginner_prompt_path': str(config_dir / 'prompts' / 'beginner.txt'),
                'cs_student_prompt_path': str(config_dir / 'prompts' / 'cs_student.txt'),
                'max_tokens': 500,
                'temperature': 0.3
            },
            'quality': {
                'min_content_length': 200,
                'dedup_title_threshold': 0.85,
                'history_days': 30
            },
            'claude': {
                'model': 'claude-sonnet-4-5',
                'max_tokens_per_summary': 500
            },
            'email': {
                'smtp_host': 'smtp.test.com',
                'smtp_port': 587,
                'smtp_username': 'test@example.com',
                'from_email': 'test@example.com',
                'use_tls': True
            },
            'execution': {
                'run_time': '08:00',
                'max_articles_per_topic': 15
            },
            'paths': {
                'history_file': 'data/sent_articles.json',
                'log_file': 'logs/news_aggregator.log',
                'execution_history_file': 'data/execution_history.json'
            }
        }

        config_file = config_dir / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        return config_file

    def test_load_valid_config(self, temp_config_dir, monkeypatch):
        """Test loading a valid configuration."""
        # Set environment variables
        monkeypatch.setenv('CLAUDE_API_KEY', 'test-api-key')
        monkeypatch.setenv('SMTP_PASSWORD', 'test-password')
        monkeypatch.setenv('RECIPIENT_EMAIL', 'recipient@example.com')

        config_file = self.create_valid_config(temp_config_dir)

        config = load_config(str(config_file))

        # Verify config loaded correctly
        assert config.claude_api_key == 'test-api-key'
        assert config.recipient_email == 'recipient@example.com'
        assert len(config.topics) == 3
        assert 'polymarket' in config.topics
        assert 'ai' in config.topics
        assert 'robotics' in config.topics

        # Verify topic configs
        assert config.topics['polymarket'].audience_level == 'beginner'
        assert config.topics['ai'].audience_level == 'cs_student'
        assert config.topics['robotics'].include_context is True

        # Verify news sources
        assert len(config.news_sources['polymarket']) == 1
        assert config.news_sources['polymarket'][0].url == 'https://example.com/feed1.xml'

    def test_missing_required_sections(self, temp_config_dir):
        """Test error when required sections are missing."""
        config_file = temp_config_dir / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump({'topics': {}}, f)  # Missing other required sections

        with pytest.raises(ConfigError, match="Missing required configuration section"):
            load_config(str(config_file))

    def test_missing_env_variables(self, temp_config_dir, monkeypatch):
        """Test error when required environment variables are missing."""
        config_file = self.create_valid_config(temp_config_dir)

        # Mock load_dotenv to prevent loading from actual .env files
        monkeypatch.setattr('news_aggregator.config.load_dotenv', lambda *args, **kwargs: None)

        # Explicitly clear all required environment variables
        monkeypatch.delenv('CLAUDE_API_KEY', raising=False)
        monkeypatch.delenv('SMTP_PASSWORD', raising=False)
        monkeypatch.delenv('RECIPIENT_EMAIL', raising=False)

        # Set only SMTP_PASSWORD and RECIPIENT_EMAIL to isolate the API key error
        monkeypatch.setenv('SMTP_PASSWORD', 'test-password')
        monkeypatch.setenv('RECIPIENT_EMAIL', 'test@example.com')

        with pytest.raises(ConfigError, match="No API key found"):
            load_config(str(config_file))

    def test_validate_config_invalid_audience_level(self, temp_config_dir, monkeypatch):
        """Test validation of invalid audience level."""
        monkeypatch.setenv('CLAUDE_API_KEY', 'test-api-key')
        monkeypatch.setenv('SMTP_PASSWORD', 'test-password')
        monkeypatch.setenv('RECIPIENT_EMAIL', 'recipient@example.com')

        config_file = self.create_valid_config(temp_config_dir)
        config = load_config(str(config_file))

        # Change audience level to invalid value
        config.topics['ai'].audience_level = 'invalid_level'

        with pytest.raises(ConfigError, match="Invalid audience_level"):
            validate_config(config)

    def test_validate_config_invalid_quality_score(self, temp_config_dir, monkeypatch):
        """Test validation of invalid quality score."""
        monkeypatch.setenv('CLAUDE_API_KEY', 'test-api-key')
        monkeypatch.setenv('SMTP_PASSWORD', 'test-password')
        monkeypatch.setenv('RECIPIENT_EMAIL', 'recipient@example.com')

        config_file = self.create_valid_config(temp_config_dir)
        config = load_config(str(config_file))

        # Set invalid quality score
        config.topics['ai'].min_quality_score = 1.5  # Out of range

        with pytest.raises(ConfigError, match="Invalid min_quality_score"):
            validate_config(config)

    def test_validate_config_missing_prompt_files(self, temp_config_dir, monkeypatch):
        """Test validation when prompt files don't exist."""
        monkeypatch.setenv('CLAUDE_API_KEY', 'test-api-key')
        monkeypatch.setenv('SMTP_PASSWORD', 'test-password')
        monkeypatch.setenv('RECIPIENT_EMAIL', 'recipient@example.com')

        config_file = self.create_valid_config(temp_config_dir)
        config = load_config(str(config_file))

        # Point to non-existent prompt file
        config.summarization.beginner_prompt_path = "non/existent/path.txt"

        with pytest.raises(ConfigError, match="Prompt template file not found"):
            validate_config(config)

    def test_legacy_feed_format_support(self, temp_config_dir, monkeypatch):
        """Test that legacy feed format (just URL strings) is still supported."""
        monkeypatch.setenv('CLAUDE_API_KEY', 'test-api-key')
        monkeypatch.setenv('SMTP_PASSWORD', 'test-password')
        monkeypatch.setenv('RECIPIENT_EMAIL', 'recipient@example.com')

        # Create config with legacy format
        config_data = {
            'topics': {
                'polymarket': {
                    'audience_level': 'beginner',
                    'include_context': True,
                    'context_text': 'Test',
                    'min_quality_score': 0.5,
                    'max_articles_per_day': 10,
                    'trusted_sources': []
                },
                'robotics': {
                    'audience_level': 'beginner',
                    'include_context': True,
                    'context_text': 'Test',
                    'min_quality_score': 0.5,
                    'max_articles_per_day': 10,
                    'trusted_sources': []
                },
                'ai': {
                    'audience_level': 'cs_student',
                    'include_context': False,
                    'context_text': None,
                    'min_quality_score': 0.6,
                    'max_articles_per_day': 10,
                    'trusted_sources': []
                }
            },
            'news_sources': {
                'polymarket': ['https://example.com/feed1.xml'],  # Legacy format
                'robotics': ['https://example.com/feed2.xml'],
                'ai': ['https://example.com/feed3.xml']
            },
            'alternative_sources': {
                'arxiv': {'enabled': False},
                'hacker_news': {'enabled': False},
                'custom_scrapers': {'enabled': False}
            },
            'summarization': {
                'beginner_prompt_path': str(temp_config_dir / 'prompts' / 'beginner.txt'),
                'cs_student_prompt_path': str(temp_config_dir / 'prompts' / 'cs_student.txt'),
                'max_tokens': 500,
                'temperature': 0.3
            },
            'quality': {
                'min_content_length': 200,
                'dedup_title_threshold': 0.85,
                'history_days': 30
            },
            'claude': {'model': 'claude-sonnet-4-5'},
            'email': {
                'smtp_host': 'smtp.test.com',
                'smtp_port': 587,
                'smtp_username': 'test@example.com',
                'from_email': 'test@example.com',
                'use_tls': True
            },
            'execution': {'run_time': '08:00'},
            'paths': {}
        }

        config_file = temp_config_dir / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_file))

        # Verify legacy format was parsed correctly
        assert len(config.news_sources['polymarket']) == 1
        assert config.news_sources['polymarket'][0].url == 'https://example.com/feed1.xml'
        assert config.news_sources['polymarket'][0].enabled is True
        assert config.news_sources['polymarket'][0].priority == 'medium'
