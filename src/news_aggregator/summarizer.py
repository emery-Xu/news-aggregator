"""AI summarization component using Claude API."""

import asyncio
from typing import List
from anthropic import AsyncAnthropic
from anthropic import RateLimitError, APIError

from .models import Article, SummarizedArticle
from .logger import get_logger


class ClaudeSummarizer:
    """Generates article summaries using Claude API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5", max_tokens: int = 300, base_url: str = None):
        """
        Initialize Claude summarizer.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens per summary
            base_url: Optional custom API base URL
        """
        # Initialize client with custom base URL if provided
        if base_url:
            self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = AsyncAnthropic(api_key=api_key)

        self.model = model
        self.max_tokens = max_tokens
        self.logger = get_logger()
        self.semaphore = asyncio.Semaphore(2)  # Limit concurrent API calls
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def summarize_batch(self, articles: List[Article]) -> List[SummarizedArticle]:
        """
        Summarize multiple articles in parallel.

        Args:
            articles: List of articles to summarize

        Returns:
            List of summarized articles
        """
        self.logger.info(f"Starting to summarize {len(articles)} articles")

        tasks = []
        for article in articles:
            task = self.summarize_article(article)
            tasks.append(task)

        # Summarize all articles in parallel with rate limiting
        summarized_articles = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        results = []
        for i, result in enumerate(summarized_articles):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to summarize article '{articles[i].title}': {result}")
                # Create article with original content
                results.append(SummarizedArticle.from_article(
                    articles[i],
                    summary_bullets=[],
                    summarization_failed=True
                ))
            else:
                results.append(result)

        success_count = sum(1 for r in results if not r.summarization_failed)
        self.logger.info(
            f"Summarization complete: {success_count}/{len(articles)} successful. "
            f"Tokens used: {self.total_input_tokens} input, {self.total_output_tokens} output"
        )

        return results

    async def summarize_article(self, article: Article, max_retries: int = 3) -> SummarizedArticle:
        """
        Summarize a single article with retry logic.

        Args:
            article: Article to summarize
            max_retries: Maximum number of retry attempts

        Returns:
            SummarizedArticle with generated summary
        """
        async with self.semaphore:  # Rate limiting
            for attempt in range(max_retries):
                try:
                    # Create prompt
                    prompt = self._create_prompt(article)

                    # Call Claude API
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
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

                    # Parse bullet points
                    bullets = self._parse_bullets(summary_text)

                    # Validate bullet count
                    if len(bullets) < 3 or len(bullets) > 5:
                        self.logger.warning(
                            f"Article '{article.title}' has {len(bullets)} bullets (expected 3-5)"
                        )

                    self.logger.debug(f"Successfully summarized: '{article.title}'")

                    return SummarizedArticle.from_article(
                        article,
                        summary_bullets=bullets,
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
                        self.logger.error(f"All retries exhausted for '{article.title}'")
                        return SummarizedArticle.from_article(
                            article,
                            summary_bullets=[],
                            summarization_failed=True
                        )

                except APIError as e:
                    wait_time = 2 ** attempt
                    self.logger.warning(
                        f"API error for '{article.title}', "
                        f"attempt {attempt + 1}/{max_retries}: {e}"
                    )

                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        self.logger.error(f"All retries exhausted for '{article.title}'")
                        return SummarizedArticle.from_article(
                            article,
                            summary_bullets=[],
                            summarization_failed=True
                        )

                except Exception as e:
                    self.logger.error(f"Unexpected error summarizing '{article.title}': {e}")
                    return SummarizedArticle.from_article(
                        article,
                        summary_bullets=[],
                        summarization_failed=True
                    )

            # Should not reach here, but just in case
            return SummarizedArticle.from_article(
                article,
                summary_bullets=[],
                summarization_failed=True
            )

    def _create_prompt(self, article: Article) -> str:
        """
        Create prompt for Claude API.

        Args:
            article: Article to summarize

        Returns:
            Prompt string
        """
        # Truncate content if too long (keep first 2000 chars)
        content = article.content[:2000] if len(article.content) > 2000 else article.content

        prompt = f"""Summarize the following article in 3-5 brief bullet points. Each bullet point should be factual, concise (under 20 words), and focus on key information. Format each bullet with a bullet character (•).

Article Title: {article.title}

Article Content:
{content}

Provide 3-5 bullet point summary:"""

        return prompt

    def _parse_bullets(self, summary_text: str) -> List[str]:
        """
        Parse bullet points from Claude's response.

        Args:
            summary_text: Raw summary text from Claude

        Returns:
            List of bullet point strings
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
            for bullet_char in ['•', '•', '-', '*', '→']:
                if line.startswith(bullet_char):
                    line = line[1:].strip()
                    break

            # Skip very short lines (likely formatting artifacts)
            if len(line) < 10:
                continue

            bullets.append(line)

        # If no bullets found, try splitting the entire text
        if not bullets and summary_text.strip():
            bullets = [summary_text.strip()]

        return bullets
