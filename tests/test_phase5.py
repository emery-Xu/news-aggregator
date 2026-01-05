"""Unit tests for Phase 5: Email Template Enhancement"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
import pytest

from news_aggregator.models import Article, SummarizedArticle, EmailContent
from news_aggregator.config import Config, TopicConfig
from news_aggregator.email_composer import EmailComposer


class TestEmailComposerEnhanced:
    """Test EmailComposer with context cards and audience labels."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config with context text."""
        config = Mock(spec=Config)
        config.topics = {
            'polymarket': TopicConfig(
                audience_level='beginner',
                include_context=True,
                context_text='Polymarket is a prediction market platform where users bet on future events using cryptocurrency. Markets cover politics, sports, crypto, and current events.',
                min_quality_score=0.5,
                max_articles_per_day=10,
                trusted_sources=['Polymarket Blog']
            ),
            'robotics': TopicConfig(
                audience_level='beginner',
                include_context=True,
                context_text='Robotics combines mechanical engineering, AI, and sensors to create machines that perform tasks autonomously or assist humans in various industries.',
                min_quality_score=0.5,
                max_articles_per_day=10,
                trusted_sources=['IEEE Spectrum']
            ),
            'ai': TopicConfig(
                audience_level='cs_student',
                include_context=False,
                context_text=None,
                min_quality_score=0.6,
                max_articles_per_day=10,
                trusted_sources=['OpenAI Blog']
            )
        }
        return config

    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory with email template."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create a simplified template for testing
        template_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Daily AI News Digest - {{ date }}</h1>

    {% if has_articles %}
    <div class="summary">
        <p>Total: {{ total_count }} articles</p>
        <p>{{ polymarket_count }} Polymarket | {{ ai_count }} AI | {{ robotics_count }} Robotics</p>
    </div>

    <!-- Polymarket Section -->
    <div class="topic-section">
        <h2>🎲 Polymarket ({{ polymarket_count }} {{ "article" if polymarket_count == 1 else "articles" }}) - For Beginners</h2>
        {% if polymarket_context %}
        <details class="context-card">
            <summary>Background: What is Polymarket?</summary>
            <p>{{ polymarket_context }}</p>
        </details>
        {% endif %}
        {% if polymarket_articles %}
        {% for article in polymarket_articles %}
        <div class="article">
            <h3>{{ article.title }}</h3>
            {% if article.summary_bullets %}
            <ul>
                {% for bullet in article.summary_bullets %}
                <li>{{ bullet }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            <a href="{{ article.url }}">Read more</a>
        </div>
        {% endfor %}
        {% else %}
        <div class="no-topic-articles">No updates today.</div>
        {% endif %}
    </div>

    <!-- AI Section -->
    <div class="topic-section">
        <h2>🤖 AI ({{ ai_count }} {{ "article" if ai_count == 1 else "articles" }}) - For CS Students</h2>
        {% if ai_articles %}
        {% for article in ai_articles %}
        <div class="article">
            <h3>{{ article.title }}</h3>
            {% if article.summary_bullets %}
            <ul>
                {% for bullet in article.summary_bullets %}
                <li>{{ bullet }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            <a href="{{ article.url }}">Read more</a>
        </div>
        {% endfor %}
        {% else %}
        <div class="no-topic-articles">No updates today.</div>
        {% endif %}
    </div>

    <!-- Robotics Section -->
    <div class="topic-section">
        <h2>🦾 Robotics ({{ robotics_count }} {{ "article" if robotics_count == 1 else "articles" }}) - For Beginners</h2>
        {% if robotics_context %}
        <details class="context-card">
            <summary>Background: What is Robotics?</summary>
            <p>{{ robotics_context }}</p>
        </details>
        {% endif %}
        {% if robotics_articles %}
        {% for article in robotics_articles %}
        <div class="article">
            <h3>{{ article.title }}</h3>
            {% if article.summary_bullets %}
            <ul>
                {% for bullet in article.summary_bullets %}
                <li>{{ bullet }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            <a href="{{ article.url }}">Read more</a>
        </div>
        {% endfor %}
        {% else %}
        <div class="no-topic-articles">No updates today.</div>
        {% endif %}
    </div>

    {% else %}
    <div class="no-articles">
        <p>No new articles today.</p>
    </div>
    {% endif %}

    <div class="footer">
        <p>Generated on {{ timestamp }}</p>
    </div>
</body>
</html>"""

        template_path = temp_dir / "email_template.html"
        template_path.write_text(template_content, encoding='utf-8')

        yield temp_dir

        # Cleanup
        template_path.unlink()
        temp_dir.rmdir()

    def test_context_text_included_for_polymarket(self, mock_config, temp_template_dir):
        """Test that Polymarket context text is included in email."""
        composer = EmailComposer(mock_config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url="https://example.com/pm1",
                title="Polymarket Article",
                content="Content",
                published_at=datetime.now(),
                topic="polymarket",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner",
                summarization_failed=False
            )
        ]

        email = composer.compose(articles)

        # Check that context text is in HTML
        assert "Polymarket is a prediction market platform" in email.html_body
        assert "Background: What is Polymarket?" in email.html_body

    def test_context_text_included_for_robotics(self, mock_config, temp_template_dir):
        """Test that Robotics context text is included in email."""
        composer = EmailComposer(mock_config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url="https://example.com/rob1",
                title="Robotics Article",
                content="Content",
                published_at=datetime.now(),
                topic="robotics",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner",
                summarization_failed=False
            )
        ]

        email = composer.compose(articles)

        # Check that context text is in HTML
        assert "Robotics combines mechanical engineering" in email.html_body
        assert "Background: What is Robotics?" in email.html_body

    def test_no_context_for_ai(self, mock_config, temp_template_dir):
        """Test that AI section does not include context card."""
        composer = EmailComposer(mock_config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url="https://example.com/ai1",
                title="AI Article",
                content="Content",
                published_at=datetime.now(),
                topic="ai",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="cs_student",
                summarization_failed=False
            )
        ]

        email = composer.compose(articles)

        # AI section should not have context card
        assert "Background:" not in email.html_body.split("AI (")[1].split("</div>")[0]

    def test_audience_labels_in_headers(self, mock_config, temp_template_dir):
        """Test that audience labels appear in section headers."""
        composer = EmailComposer(mock_config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url="https://example.com/pm1",
                title="Polymarket Article",
                content="Content",
                published_at=datetime.now(),
                topic="polymarket",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner"
            ),
            SummarizedArticle(
                url="https://example.com/ai1",
                title="AI Article",
                content="Content",
                published_at=datetime.now(),
                topic="ai",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="cs_student"
            ),
            SummarizedArticle(
                url="https://example.com/rob1",
                title="Robotics Article",
                content="Content",
                published_at=datetime.now(),
                topic="robotics",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner"
            )
        ]

        email = composer.compose(articles)

        # Check audience labels
        assert "For Beginners" in email.html_body
        assert "For CS Students" in email.html_body

    def test_no_articles_message_per_topic(self, mock_config, temp_template_dir):
        """Test that 'No updates today' appears when topic has no articles."""
        composer = EmailComposer(mock_config, temp_template_dir)

        # Only AI articles, no Polymarket or Robotics
        articles = [
            SummarizedArticle(
                url="https://example.com/ai1",
                title="AI Article",
                content="Content",
                published_at=datetime.now(),
                topic="ai",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="cs_student"
            )
        ]

        email = composer.compose(articles)

        # Should show "No updates today" for Polymarket and Robotics
        assert email.html_body.count("No updates today") == 2

    def test_article_counts_in_headers(self, mock_config, temp_template_dir):
        """Test that article counts appear in section headers."""
        composer = EmailComposer(mock_config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url="https://example.com/pm1",
                title="Polymarket Article 1",
                content="Content",
                published_at=datetime.now(),
                topic="polymarket",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner"
            ),
            SummarizedArticle(
                url="https://example.com/pm2",
                title="Polymarket Article 2",
                content="Content",
                published_at=datetime.now(),
                topic="polymarket",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner"
            ),
            SummarizedArticle(
                url="https://example.com/ai1",
                title="AI Article",
                content="Content",
                published_at=datetime.now(),
                topic="ai",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="cs_student"
            )
        ]

        email = composer.compose(articles)

        # Check counts in headers
        assert "Polymarket (2 articles)" in email.html_body
        assert "AI (1 article)" in email.html_body  # Singular
        assert "Robotics (0 articles)" in email.html_body

    def test_context_not_included_when_disabled(self, temp_template_dir):
        """Test that context is not included when include_context is False."""
        # Create config with include_context=False for Polymarket
        config = Mock(spec=Config)
        config.topics = {
            'polymarket': TopicConfig(
                audience_level='beginner',
                include_context=False,  # Disabled
                context_text='This should not appear',
                min_quality_score=0.5,
                max_articles_per_day=10,
                trusted_sources=[]
            ),
            'ai': TopicConfig(
                audience_level='cs_student',
                include_context=False,
                context_text=None,
                min_quality_score=0.6,
                max_articles_per_day=10,
                trusted_sources=[]
            ),
            'robotics': TopicConfig(
                audience_level='beginner',
                include_context=False,
                context_text='This should not appear either',
                min_quality_score=0.5,
                max_articles_per_day=10,
                trusted_sources=[]
            )
        }

        composer = EmailComposer(config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url="https://example.com/pm1",
                title="Polymarket Article",
                content="Content",
                published_at=datetime.now(),
                topic="polymarket",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="beginner"
            )
        ]

        email = composer.compose(articles)

        # Context text should not appear
        assert "This should not appear" not in email.html_body
        assert "Background:" not in email.html_body

    def test_total_count_in_summary(self, mock_config, temp_template_dir):
        """Test that total article count is displayed in summary."""
        composer = EmailComposer(mock_config, temp_template_dir)

        articles = [
            SummarizedArticle(
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                content="Content",
                published_at=datetime.now(),
                topic="ai" if i % 2 == 0 else "polymarket",
                source="Test",
                summary_bullets=["Bullet 1", "Bullet 2", "Bullet 3"],
                audience_level="cs_student" if i % 2 == 0 else "beginner"
            )
            for i in range(6)
        ]

        email = composer.compose(articles)

        # Check total count
        assert "Total: 6 articles" in email.html_body
