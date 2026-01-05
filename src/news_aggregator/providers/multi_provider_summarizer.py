"""Multi-provider summarization with automatic fallback."""

import asyncio
from typing import List, Dict
from pathlib import Path

from ..models import Article, SummarizedArticle, RankedArticle
from ..config import Config
from ..logger import get_logger
from .registry import ProviderRegistry
from .selector import ProviderSelector
from .exceptions import ProviderAPIError


class MultiProviderSummarizer:
    """Coordinates summarization across multiple providers with fallback."""

    def __init__(self, config: Config):
        """
        Initialize multi-provider summarizer.

        Args:
            config: Application configuration with provider settings
        """
        self.config = config
        self.logger = get_logger()

        # Initialize provider infrastructure
        self.registry = ProviderRegistry(config.providers)
        self.selector = ProviderSelector(config.providers, config.provider_strategy)

        # Load prompts (reuse existing logic)
        self.prompts = self._load_prompts(config.summarization)

        # Audience level mapping (topic -> audience level)
        self.audience_map = {
            topic: topic_config.audience_level
            for topic, topic_config in config.topics.items()
        }

        # Semaphore for rate limiting
        self.semaphore = asyncio.Semaphore(5)

        # Track total token usage across all providers
        self.total_input_tokens = 0
        self.total_output_tokens = 0

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
        """Get default prompt template if file not found."""
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
            f"Starting multi-provider summarization for {len(articles_by_topic)} topics, "
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
            f"Multi-provider summarization complete: {success_count}/{total_count} successful. "
            f"Tokens used: {self.total_input_tokens} input, {self.total_output_tokens} output"
        )

        # Log provider usage summary
        self._log_provider_summary()

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
            self._summarize_article_with_fallback(article, audience_level, topic)
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

    async def _summarize_article_with_fallback(
        self,
        article: Article,
        audience_level: str,
        topic: str
    ) -> SummarizedArticle:
        """
        Try providers in order until one succeeds.

        Args:
            article: Article to summarize
            audience_level: 'beginner' or 'cs_student'
            topic: Topic name

        Returns:
            SummarizedArticle with generated summary
        """
        async with self.semaphore:
            provider_chain = self.selector.get_provider_chain(article)

            for provider_id in provider_chain:
                provider = self.registry.get_provider(provider_id)

                try:
                    # Create prompt
                    prompt = self._create_prompt(article, audience_level, topic)

                    # Call provider
                    bullets, usage = await provider.summarize_async(
                        article,
                        prompt,
                        self.config.max_tokens_per_summary,
                        self.config.summarization.temperature
                    )

                    # Track token usage
                    self.total_input_tokens += usage.get("input_tokens", 0)
                    self.total_output_tokens += usage.get("output_tokens", 0)

                    # Validate bullet count
                    if len(bullets) < 3:
                        self.logger.warning(
                            f"Provider {provider_id} returned {len(bullets)} bullets for "
                            f"'{article.title}', trying next provider"
                        )
                        continue

                    # Success!
                    self.logger.debug(
                        f"Summarized '{article.title}' using {provider_id} "
                        f"({len(bullets)} bullets)"
                    )
                    return SummarizedArticle.from_article(
                        article,
                        summary_bullets=bullets[:5],  # Enforce max 5
                        audience_level=audience_level,
                        summarization_failed=False
                    )

                except ProviderAPIError as e:
                    self.logger.warning(
                        f"Provider {provider_id} failed for '{article.title}': {e}"
                    )
                    continue
                except Exception as e:
                    self.logger.error(
                        f"Unexpected error with provider {provider_id} for '{article.title}': {e}"
                    )
                    continue

            # All providers failed
            self.logger.error(f"All providers failed for '{article.title}'")
            return SummarizedArticle.from_article(
                article,
                summary_bullets=[],
                audience_level=audience_level,
                summarization_failed=True
            )

    def _create_prompt(self, article: Article, audience_level: str, topic: str) -> str:
        """
        Create audience-specific prompt for AI model.

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

    def _log_provider_summary(self):
        """Log provider usage statistics."""
        self.logger.info("Provider usage summary:")
        for provider_id, provider in self.registry.get_all_providers().items():
            stats = provider.get_usage_stats()
            self.logger.info(
                f"  {provider_id}: {stats['successful_requests']}/{stats['total_requests']} successful, "
                f"{stats['total_input_tokens']} input tokens, {stats['total_output_tokens']} output tokens, "
                f"{stats['average_latency_seconds']:.2f}s avg latency"
            )
