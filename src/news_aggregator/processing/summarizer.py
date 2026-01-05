"""AI summarization component with adaptive, audience-specific prompts."""

import asyncio
from typing import List, Dict
from pathlib import Path
from anthropic import AsyncAnthropic
from anthropic import RateLimitError, APIError

from ..models import Article, SummarizedArticle, RankedArticle
from ..config import Config
from ..logger import get_logger


class AdaptiveSummarizer:
    """Generates audience-specific article summaries using Claude API with adaptive prompts."""

    def __init__(self, config: Config):
        """
        Initialize adaptive summarizer.

        Args:
            config: Application configuration with Claude settings and prompt templates
        """
        # Initialize Claude client with custom base URL if provided
        if config.claude_api_base_url:
            self.client = AsyncAnthropic(
                api_key=config.claude_api_key,
                base_url=config.claude_api_base_url
            )
        else:
            self.client = AsyncAnthropic(api_key=config.claude_api_key)

        self.model = config.claude_model
        self.max_tokens = config.summarization.max_tokens
        self.temperature = config.summarization.temperature
        self.logger = get_logger()
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Load prompt templates
        self.prompts = self._load_prompts(config.summarization)

        # Audience level mapping (topic -> audience level)
        self.audience_map = {
            topic: topic_config.audience_level
            for topic, topic_config in config.topics.items()
        }

    def _load_prompts(self, summ_config) -> Dict[str, str]:
        """
        Load prompt templates from files.

        Args:
            summ_config: SummarizationConfig with prompt file paths

        Returns:
            Dictionary mapping audience levels to prompt templates
        """
        prompts = {}

        # Load beginner prompt
        beginner_path = Path(summ_config.beginner_prompt_path)
        if beginner_path.exists():
            with open(beginner_path, 'r', encoding='utf-8') as f:
                prompts['beginner'] = f.read()
            self.logger.info(f"Loaded beginner prompt template from {beginner_path}")
        else:
            self.logger.warning(f"Beginner prompt template not found: {beginner_path}")
            prompts['beginner'] = self._get_default_prompt('beginner')

        # Load CS student prompt
        cs_path = Path(summ_config.cs_student_prompt_path)
        if cs_path.exists():
            with open(cs_path, 'r', encoding='utf-8') as f:
                prompts['cs_student'] = f.read()
            self.logger.info(f"Loaded CS student prompt template from {cs_path}")
        else:
            self.logger.warning(f"CS student prompt template not found: {cs_path}")
            prompts['cs_student'] = self._get_default_prompt('cs_student')

        return prompts

    def _get_default_prompt(self, audience_level: str) -> str:
        """
        Get default prompt template if file not found.

        Args:
            audience_level: 'beginner' or 'cs_student'

        Returns:
            Default prompt template
        """
        if audience_level == 'beginner':
            return """Summarize this article in exactly 3-5 brief bullet points for someone NEW to {topic}.

RULES:
- Use simple, clear language
- Focus on WHAT happened and WHY it matters
- Keep bullets SHORT (max 20 words each)
- Start each bullet with • symbol
- NO introduction, NO conclusion

Article Title: {title}
Article Content: {content}

Provide ONLY 3-5 bullet points:"""
        else:
            return """Summarize this article in exactly 3-5 bullet points for computer science students.

RULES:
- Include technical details and methods
- Highlight what's NOVEL
- Keep bullets concise (max 25 words each)
- Start each bullet with • symbol
- NO introduction, NO conclusion

Article Title: {title}
Article Content: {content}

Provide ONLY 3-5 bullet points:"""

    async def summarize_by_audience(
        self,
        articles_by_topic: Dict[str, List[RankedArticle]]
    ) -> Dict[str, List[SummarizedArticle]]:
        """
        Summarize articles grouped by topic using appropriate audience-level prompts.

        Args:
            articles_by_topic: Dictionary mapping topics to lists of RankedArticle objects

        Returns:
            Dictionary mapping topics to lists of SummarizedArticle objects
        """
        self.logger.info(
            f"Starting adaptive summarization for {len(articles_by_topic)} topics, "
            f"{sum(len(articles) for articles in articles_by_topic.values())} total articles"
        )

        results = {}

        for topic, ranked_articles in articles_by_topic.items():
            if not ranked_articles:
                results[topic] = []
                continue

            # Get audience level for this topic
            audience_level = self.audience_map.get(topic, 'beginner')
            self.logger.info(
                f"Summarizing {len(ranked_articles)} articles for topic '{topic}' "
                f"(audience: {audience_level})"
            )

            # Extract Article objects from RankedArticle
            articles = [ra.article for ra in ranked_articles]

            # Summarize all articles for this topic with appropriate prompt
            summarized = await self._summarize_batch(articles, audience_level, topic)
            results[topic] = summarized

        success_count = sum(
            sum(1 for article in articles if not article.summarization_failed)
            for articles in results.values()
        )
        total_count = sum(len(articles) for articles in results.values())

        self.logger.info(
            f"Adaptive summarization complete: {success_count}/{total_count} successful. "
            f"Tokens used: {self.total_input_tokens} input, {self.total_output_tokens} output"
        )

        return results

    async def _summarize_batch(
        self,
        articles: List[Article],
        audience_level: str,
        topic: str
    ) -> List[SummarizedArticle]:
        """
        Summarize multiple articles in parallel with the same audience level.

        Args:
            articles: List of articles to summarize
            audience_level: 'beginner' or 'cs_student'
            topic: Topic name for prompt customization

        Returns:
            List of summarized articles
        """
        tasks = [
            self._summarize_article(article, audience_level, topic)
            for article in articles
        ]

        # Summarize all articles in parallel with rate limiting
        summarized_articles = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        results = []
        for i, result in enumerate(summarized_articles):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Failed to summarize article '{articles[i].title}': {result}"
                )
                # Create article with fallback to original content
                results.append(SummarizedArticle.from_article(
                    articles[i],
                    summary_bullets=[],
                    audience_level=audience_level,
                    summarization_failed=True
                ))
            else:
                results.append(result)

        return results

    async def _summarize_article(
        self,
        article: Article,
        audience_level: str,
        topic: str,
        max_retries: int = 3
    ) -> SummarizedArticle:
        """
        Summarize a single article with retry logic.

        Args:
            article: Article to summarize
            audience_level: 'beginner' or 'cs_student'
            topic: Topic name
            max_retries: Maximum number of retry attempts

        Returns:
            SummarizedArticle with generated summary
        """
        async with self.semaphore:  # Rate limiting
            for attempt in range(max_retries):
                try:
                    # Create audience-specific prompt
                    prompt = self._create_prompt(article, audience_level, topic)

                    # Call Claude API
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        messages=[
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    )

                    # Track token usage
                    self.total_input_tokens += response.usage.input_tokens
                    self.total_output_tokens += response.usage.output_tokens

                    # Extract summary text
                    summary_text = response.content[0].text

                    # Parse and validate bullet points
                    bullets = self._parse_and_validate_bullets(summary_text, article.title)

                    # Check if validation failed (empty bullets)
                    if not bullets:
                        self.logger.warning(
                            f"Summarization validation failed for '{article.title}' (insufficient bullets)"
                        )
                        return SummarizedArticle.from_article(
                            article,
                            summary_bullets=[],
                            audience_level=audience_level,
                            summarization_failed=True
                        )

                    self.logger.debug(
                        f"Successfully summarized '{article.title}' "
                        f"({len(bullets)} bullets, audience: {audience_level})"
                    )

                    return SummarizedArticle.from_article(
                        article,
                        summary_bullets=bullets,
                        audience_level=audience_level,
                        summarization_failed=False
                    )

                except RateLimitError as e:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    self.logger.warning(
                        f"Rate limit hit for '{article.title}', "
                        f"attempt {attempt + 1}/{max_retries}, waiting {wait_time}s: {e}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        return self._create_failed_summary(article, audience_level)

                except APIError as e:
                    wait_time = 2 ** attempt
                    self.logger.warning(
                        f"API error for '{article.title}', "
                        f"attempt {attempt + 1}/{max_retries}: {e}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        return self._create_failed_summary(article, audience_level)

                except Exception as e:
                    self.logger.error(f"Unexpected error summarizing '{article.title}': {e}")
                    return self._create_failed_summary(article, audience_level)

            # Should not reach here, but just in case
            return self._create_failed_summary(article, audience_level)

    def _create_prompt(self, article: Article, audience_level: str, topic: str) -> str:
        """
        Create audience-specific prompt for Claude API.

        Args:
            article: Article to summarize
            audience_level: 'beginner' or 'cs_student'
            topic: Topic name

        Returns:
            Formatted prompt string
        """
        # Truncate content if too long (keep first 3000 chars for better context)
        content = article.content[:3000] if len(article.content) > 3000 else article.content

        # Get prompt template for this audience level
        prompt_template = self.prompts.get(audience_level, self.prompts['beginner'])

        # Format prompt with article details
        prompt = prompt_template.format(
            topic=topic,
            title=article.title,
            content=content
        )

        return prompt

    def _parse_and_validate_bullets(self, summary_text: str, article_title: str) -> List[str]:
        """
        Parse bullet points from Claude's response and validate count.

        Args:
            summary_text: Raw summary text from Claude
            article_title: Article title for logging

        Returns:
            List of bullet point strings (3-5 bullets)
        """
        bullets = []

        # Split by lines
        lines = summary_text.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove bullet characters and clean up
            for bullet_char in ['•', '•', '-', '*', '→', '1.', '2.', '3.', '4.', '5.']:
                if line.startswith(bullet_char):
                    line = line[len(bullet_char):].strip()
                    break

            # Skip very short lines (likely formatting artifacts)
            if len(line) < 10:
                continue

            bullets.append(line)

        # Validate bullet count (3-5)
        if len(bullets) < 3:
            self.logger.warning(
                f"Article '{article_title}' has only {len(bullets)} bullets (expected 3-5). "
                f"Using original content as fallback."
            )
            # Return empty to trigger fallback
            return []

        if len(bullets) > 5:
            self.logger.warning(
                f"Article '{article_title}' has {len(bullets)} bullets (expected 3-5). "
                f"Keeping first 5."
            )
            bullets = bullets[:5]

        return bullets

    def _create_failed_summary(self, article: Article, audience_level: str) -> SummarizedArticle:
        """
        Create a SummarizedArticle for failed summarization attempts.

        Args:
            article: Original article
            audience_level: Audience level for this article

        Returns:
            SummarizedArticle marked as failed
        """
        return SummarizedArticle.from_article(
            article,
            summary_bullets=[],
            audience_level=audience_level,
            summarization_failed=True
        )
