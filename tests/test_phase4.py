"""Unit tests for Phase 4: Adaptive Summarization"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest

from news_aggregator.models import Article, RankedArticle, SummarizedArticle
from news_aggregator.config import Config, TopicConfig, SummarizationConfig
from news_aggregator.processing.summarizer import AdaptiveSummarizer


class TestAdaptiveSummarizer:
    """Test AdaptiveSummarizer with audience-specific prompts."""

    @pytest.fixture
    def temp_prompts(self):
        """Create temporary prompt template files."""
        temp_dir = tempfile.mkdtemp()
        prompt_dir = Path(temp_dir)

        # Create beginner prompt
        beginner_path = prompt_dir / "beginner.txt"
        beginner_path.write_text("""Summarize for beginners about {topic}.

Title: {title}
Content: {content}

Give 3-5 bullet points.""")

        # Create CS student prompt
        cs_path = prompt_dir / "cs_student.txt"
        cs_path.write_text("""Technical summary for CS students about {topic}.

Title: {title}
Content: {content}

Provide 3-5 bullet points.""")

        yield beginner_path, cs_path

        # Cleanup
        beginner_path.unlink()
        cs_path.unlink()
        prompt_dir.rmdir()

    @pytest.fixture
    def mock_config(self, temp_prompts):
        """Create mock config with temporary prompt files."""
        beginner_path, cs_path = temp_prompts

        config = Mock(spec=Config)
        config.topics = {
            'polymarket': TopicConfig(
                audience_level='beginner',
                include_context=True,
                context_text='Polymarket is a prediction market platform',
                min_quality_score=0.4,
                max_articles_per_day=5,
                trusted_sources=['Polymarket Blog']
            ),
            'ai': TopicConfig(
                audience_level='cs_student',
                include_context=False,
                context_text=None,
                min_quality_score=0.5,
                max_articles_per_day=5,
                trusted_sources=['OpenAI Blog', 'Anthropic News']
            ),
            'robotics': TopicConfig(
                audience_level='beginner',
                include_context=True,
                context_text='Robotics involves autonomous machines',
                min_quality_score=0.4,
                max_articles_per_day=3,
                trusted_sources=['IEEE Spectrum']
            )
        }

        config.claude_api_key = "test-api-key"
        config.claude_api_base_url = None
        config.claude_model = "claude-sonnet-4-5"

        config.summarization = SummarizationConfig(
            max_tokens=500,
            temperature=0.3,
            beginner_prompt_path=str(beginner_path),
            cs_student_prompt_path=str(cs_path)
        )

        return config

    def test_load_prompts_from_files(self, mock_config):
        """Test loading prompt templates from files."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Both prompts should be loaded
        assert 'beginner' in summarizer.prompts
        assert 'cs_student' in summarizer.prompts

        # Check content
        assert 'beginner' in summarizer.prompts['beginner'].lower()
        assert 'cs students' in summarizer.prompts['cs_student'].lower()

    def test_audience_mapping(self, mock_config):
        """Test topic to audience level mapping."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Check mappings
        assert summarizer.audience_map['polymarket'] == 'beginner'
        assert summarizer.audience_map['ai'] == 'cs_student'
        assert summarizer.audience_map['robotics'] == 'beginner'

    def test_create_prompt_beginner(self, mock_config):
        """Test prompt creation for beginner audience."""
        summarizer = AdaptiveSummarizer(mock_config)

        article = Article(
            url="https://example.com/1",
            title="Test Article",
            content="This is test content about prediction markets.",
            published_at=datetime.now(),
            topic="polymarket",
            source="Test Source"
        )

        prompt = summarizer._create_prompt(article, 'beginner', 'polymarket')

        # Prompt should include topic, title, and content
        assert 'polymarket' in prompt.lower()
        assert 'Test Article' in prompt
        assert 'prediction markets' in prompt

    def test_create_prompt_cs_student(self, mock_config):
        """Test prompt creation for CS student audience."""
        summarizer = AdaptiveSummarizer(mock_config)

        article = Article(
            url="https://example.com/1",
            title="New AI Model",
            content="This is technical content about transformers.",
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )

        prompt = summarizer._create_prompt(article, 'cs_student', 'ai')

        # Prompt should include topic, title, and content
        assert 'ai' in prompt.lower()
        assert 'New AI Model' in prompt
        assert 'transformers' in prompt

    def test_create_prompt_truncates_long_content(self, mock_config):
        """Test that very long content is truncated."""
        summarizer = AdaptiveSummarizer(mock_config)

        article = Article(
            url="https://example.com/1",
            title="Test",
            content="x" * 5000,  # Very long content
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )

        prompt = summarizer._create_prompt(article, 'cs_student', 'ai')

        # Content should be truncated to 3000 chars
        assert len(article.content) == 5000
        assert prompt.count('x') <= 3000

    def test_parse_bullets_valid_format(self, mock_config):
        """Test parsing valid bullet points."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Test with bullet character •
        summary_text = """• First bullet point here
• Second bullet point here
• Third bullet point here
• Fourth bullet point here"""

        bullets = summarizer._parse_and_validate_bullets(summary_text, "Test Article")

        assert len(bullets) == 4
        assert bullets[0] == "First bullet point here"
        assert bullets[3] == "Fourth bullet point here"

    def test_parse_bullets_dash_format(self, mock_config):
        """Test parsing bullet points with dash character."""
        summarizer = AdaptiveSummarizer(mock_config)

        summary_text = """- First point
- Second point
- Third point"""

        bullets = summarizer._parse_and_validate_bullets(summary_text, "Test Article")

        assert len(bullets) == 3

    def test_parse_bullets_numbered_format(self, mock_config):
        """Test parsing numbered bullet points."""
        summarizer = AdaptiveSummarizer(mock_config)

        summary_text = """1. First point here
2. Second point here
3. Third point here
4. Fourth point here
5. Fifth point here"""

        bullets = summarizer._parse_and_validate_bullets(summary_text, "Test Article")

        assert len(bullets) == 5

    def test_validate_bullets_too_few(self, mock_config):
        """Test validation rejects fewer than 3 bullets."""
        summarizer = AdaptiveSummarizer(mock_config)

        summary_text = """• First bullet
• Second bullet"""

        bullets = summarizer._parse_and_validate_bullets(summary_text, "Test Article")

        # Should return empty list if less than 3 bullets
        assert bullets == []

    def test_validate_bullets_too_many(self, mock_config):
        """Test validation truncates to 5 bullets if more."""
        summarizer = AdaptiveSummarizer(mock_config)

        summary_text = """• This is the first bullet point with enough text
• This is the second bullet point with enough text
• This is the third bullet point with enough text
• This is the fourth bullet point with enough text
• This is the fifth bullet point with enough text
• This is the sixth bullet point with enough text
• This is the seventh bullet point with enough text"""

        bullets = summarizer._parse_and_validate_bullets(summary_text, "Test Article")

        # Should keep only first 5 bullets
        assert len(bullets) == 5
        assert "first bullet point" in bullets[0]
        assert "fifth bullet point" in bullets[4]

    def test_parse_bullets_skips_short_lines(self, mock_config):
        """Test that very short lines are skipped."""
        summarizer = AdaptiveSummarizer(mock_config)

        summary_text = """• Valid bullet point here
• x
• Another valid bullet point
• y
• Third valid bullet point"""

        bullets = summarizer._parse_and_validate_bullets(summary_text, "Test Article")

        # Should only get 3 valid bullets (short ones skipped)
        assert len(bullets) == 3
        assert "Valid bullet point here" in bullets

    @pytest.mark.asyncio
    async def test_summarize_article_success(self, mock_config):
        """Test successful article summarization."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Mock the Claude API response
        mock_response = Mock()
        mock_response.content = [Mock(text="""• First bullet point
• Second bullet point
• Third bullet point""")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        summarizer.client.messages.create = AsyncMock(return_value=mock_response)

        article = Article(
            url="https://example.com/1",
            title="Test Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )

        result = await summarizer._summarize_article(article, 'cs_student', 'ai')

        # Check result
        assert isinstance(result, SummarizedArticle)
        assert result.audience_level == 'cs_student'
        assert len(result.summary_bullets) == 3
        assert result.summarization_failed is False

    @pytest.mark.asyncio
    async def test_summarize_article_invalid_bullets(self, mock_config):
        """Test article summarization with invalid bullet count."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Mock response with only 2 bullets
        mock_response = Mock()
        mock_response.content = [Mock(text="""• First bullet
• Second bullet""")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        summarizer.client.messages.create = AsyncMock(return_value=mock_response)

        article = Article(
            url="https://example.com/1",
            title="Test Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )

        result = await summarizer._summarize_article(article, 'cs_student', 'ai')

        # Should mark as failed due to insufficient bullets
        assert result.summarization_failed is True
        assert result.summary_bullets == []

    @pytest.mark.asyncio
    async def test_summarize_by_audience_groups_by_topic(self, mock_config):
        """Test that summarize_by_audience groups articles correctly."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Mock Claude API
        mock_response = Mock()
        mock_response.content = [Mock(text="""• First bullet point
• Second bullet point
• Third bullet point""")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        summarizer.client.messages.create = AsyncMock(return_value=mock_response)

        # Create articles grouped by topic
        articles_by_topic = {
            'polymarket': [
                RankedArticle(
                    article=Article(
                        url="https://example.com/pm1",
                        title="Polymarket Article",
                        content="Test content",
                        published_at=datetime.now(),
                        topic="polymarket",
                        source="Test"
                    ),
                    quality_score=0.8
                )
            ],
            'ai': [
                RankedArticle(
                    article=Article(
                        url="https://example.com/ai1",
                        title="AI Article",
                        content="Test content",
                        published_at=datetime.now(),
                        topic="ai",
                        source="Test"
                    ),
                    quality_score=0.9
                )
            ]
        }

        result = await summarizer.summarize_by_audience(articles_by_topic)

        # Check structure
        assert 'polymarket' in result
        assert 'ai' in result
        assert len(result['polymarket']) == 1
        assert len(result['ai']) == 1

        # Check audience levels
        assert result['polymarket'][0].audience_level == 'beginner'
        assert result['ai'][0].audience_level == 'cs_student'

    @pytest.mark.asyncio
    async def test_summarize_batch_handles_errors(self, mock_config):
        """Test that batch summarization handles individual errors."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Mock to raise error for first article, succeed for second
        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("API Error")
            else:
                mock_resp = Mock()
                # Use proper newlines in the text
                mock_resp.content = [Mock(text="• This is bullet 1 with enough text\n• This is bullet 2 with enough text\n• This is bullet 3 with enough text")]
                mock_resp.usage = Mock(input_tokens=100, output_tokens=50)
                return mock_resp

        summarizer.client.messages.create = mock_create

        articles = [
            Article(
                url="https://example.com/1",
                title="Article 1",
                content="Content 1",
                published_at=datetime.now(),
                topic="ai",
                source="Test"
            ),
            Article(
                url="https://example.com/2",
                title="Article 2",
                content="Content 2",
                published_at=datetime.now(),
                topic="ai",
                source="Test"
            )
        ]

        results = await summarizer._summarize_batch(articles, 'cs_student', 'ai')

        # Should have 2 results
        assert len(results) == 2

        # First should be failed
        assert results[0].summarization_failed is True

        # Second should be successful
        assert results[1].summarization_failed is False
        assert len(results[1].summary_bullets) == 3

    def test_create_failed_summary(self, mock_config):
        """Test creating failed summary."""
        summarizer = AdaptiveSummarizer(mock_config)

        article = Article(
            url="https://example.com/1",
            title="Test Article",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Test Source"
        )

        failed = summarizer._create_failed_summary(article, 'cs_student')

        assert isinstance(failed, SummarizedArticle)
        assert failed.summarization_failed is True
        assert failed.summary_bullets == []
        assert failed.audience_level == 'cs_student'

    def test_default_prompts_if_files_missing(self, mock_config):
        """Test that default prompts are used if files don't exist."""
        # Modify config to point to non-existent files
        mock_config.summarization.beginner_prompt_path = "/nonexistent/beginner.txt"
        mock_config.summarization.cs_student_prompt_path = "/nonexistent/cs_student.txt"

        summarizer = AdaptiveSummarizer(mock_config)

        # Should still have prompts (defaults)
        assert 'beginner' in summarizer.prompts
        assert 'cs_student' in summarizer.prompts

        # Defaults should contain key phrases
        assert 'bullet points' in summarizer.prompts['beginner'].lower()
        assert 'bullet points' in summarizer.prompts['cs_student'].lower()

    @pytest.mark.asyncio
    async def test_token_tracking(self, mock_config):
        """Test that token usage is tracked."""
        summarizer = AdaptiveSummarizer(mock_config)

        # Mock response with token usage
        mock_response = Mock()
        mock_response.content = [Mock(text="• Point 1\n• Point 2\n• Point 3")]
        mock_response.usage = Mock(input_tokens=150, output_tokens=75)

        summarizer.client.messages.create = AsyncMock(return_value=mock_response)

        article = Article(
            url="https://example.com/1",
            title="Test",
            content="Test content",
            published_at=datetime.now(),
            topic="ai",
            source="Test"
        )

        # Initial tokens should be 0
        assert summarizer.total_input_tokens == 0
        assert summarizer.total_output_tokens == 0

        await summarizer._summarize_article(article, 'cs_student', 'ai')

        # Tokens should be tracked
        assert summarizer.total_input_tokens == 150
        assert summarizer.total_output_tokens == 75
