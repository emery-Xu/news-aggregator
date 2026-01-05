"""Pipeline orchestrator for coordinating the news aggregation workflow."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List

from .config import Config
from .models import ExecutionResult, SummarizedArticle
from .fetchers.multi_source import MultiSourceFetcher
from .processing.deduplicator import Deduplicator
from .processing.ranker import ArticleRanker
from .providers.multi_provider_summarizer import MultiProviderSummarizer
from .email_composer import EmailComposer
from .email_sender import EmailSender
from .logger import get_logger


class PipelineOrchestrator:
    """Orchestrates the entire news aggregation pipeline."""

    def __init__(self, config: Config):
        """
        Initialize pipeline orchestrator.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger()

        # Initialize components
        self.fetcher = MultiSourceFetcher(config=config)
        similarity_threshold = int(config.quality.dedup_title_threshold * 100)
        self.deduplicator = Deduplicator(
            history_file=config.history_file,
            similarity_threshold=similarity_threshold
        )
        self.ranker = ArticleRanker(config)
        self.summarizer = MultiProviderSummarizer(config)
        self.email_composer = EmailComposer(config=config)
        self.email_sender = EmailSender(smtp_config=config.smtp)

    async def run_pipeline(self) -> ExecutionResult:
        """
        Execute the complete pipeline: fetch -> deduplicate -> rank -> summarize -> compose -> send.

        Returns:
            ExecutionResult with execution status and metrics
        """
        start_time = time.time()
        self.logger.info("=" * 70)
        self.logger.info("Starting news aggregation pipeline")
        self.logger.info("=" * 70)

        errors = []
        articles_fetched = 0
        articles_sent = 0

        try:
            # Stage 1: Fetch news articles
            self.logger.info("Stage 1: Fetching news articles")
            try:
                articles = await self.fetcher.fetch_all()
                articles_fetched = len(articles)
                self.logger.info(f"OK: Fetched {articles_fetched} articles")

                if articles_fetched == 0:
                    self.logger.warning("No articles fetched from any source")
                    # Still send email with "no articles" message
                    articles = []

            except Exception as e:
                error_msg = f"CRITICAL: Failed to fetch articles: {e}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                # Try to send error notification
                await self._send_error_notification(error_msg)
                return ExecutionResult(
                    success=False,
                    articles_fetched=0,
                    articles_sent=0,
                    errors=errors,
                    execution_time=time.time() - start_time
                )

            # Stage 2: Deduplicate articles
            self.logger.info("Stage 2: Deduplicating articles")
            try:
                unique_articles = self.deduplicator.deduplicate(articles)
                self.logger.info(f"OK: {len(unique_articles)} unique articles after deduplication")

            except Exception as e:
                error_msg = f"CRITICAL: Deduplication failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                await self._send_error_notification(error_msg)
                return ExecutionResult(
                    success=False,
                    articles_fetched=articles_fetched,
                    articles_sent=0,
                    errors=errors,
                    execution_time=time.time() - start_time
                )

            # Stage 3: Rank and filter articles by quality
            self.logger.info("Stage 3: Ranking and filtering articles")
            try:
                ranked_articles = self.ranker.rank_and_filter(unique_articles)
                self.logger.info(f"OK: Retained {len(ranked_articles)} articles after ranking")

            except Exception as e:
                error_msg = f"CRITICAL: Ranking failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                await self._send_error_notification(error_msg)
                return ExecutionResult(
                    success=False,
                    articles_fetched=articles_fetched,
                    articles_sent=0,
                    errors=errors,
                    execution_time=time.time() - start_time
                )

            # Stage 4: Summarize articles with AI
            self.logger.info("Stage 4: Generating AI summaries")
            try:
                # Group ranked articles by topic for audience-specific summarization
                articles_by_topic = {}
                for ranked_article in ranked_articles:
                    topic = ranked_article.article.topic
                    articles_by_topic.setdefault(topic, []).append(ranked_article)

                summarized_by_topic = await self.summarizer.summarize_by_audience(articles_by_topic)
                summarized_articles = [
                    article
                    for topic_articles in summarized_by_topic.values()
                    for article in topic_articles
                ]

                success_count = sum(1 for a in summarized_articles if not a.summarization_failed)
                self.logger.info(f"OK: Generated {success_count}/{len(summarized_articles)} summaries")

                if success_count == 0 and summarized_articles:
                    error_msg = "WARNING: All summarizations failed, using original content"
                    self.logger.warning(error_msg)
                    errors.append(error_msg)

            except Exception as e:
                error_msg = f"WARNING: Summarization failed: {e}"
                self.logger.warning(error_msg, exc_info=True)
                errors.append(error_msg)

                summarized_articles = []
                for ranked_article in ranked_articles:
                    topic = ranked_article.article.topic
                    topic_config = self.config.topics.get(topic)
                    audience_level = topic_config.audience_level if topic_config else "beginner"
                    summarized_articles.append(
                        SummarizedArticle.from_article(
                            ranked_article.article,
                            summary_bullets=[],
                            audience_level=audience_level,
                            summarization_failed=True
                        )
                    )

            # Stage 5: Compose email
            self.logger.info("Stage 5: Composing email")
            try:
                email_content = self.email_composer.compose(summarized_articles)
                self.logger.info(f"OK: Composed email with subject: {email_content.subject}")

            except Exception as e:
                error_msg = f"CRITICAL: Email composition failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                await self._send_error_notification(error_msg)
                return ExecutionResult(
                    success=False,
                    articles_fetched=articles_fetched,
                    articles_sent=0,
                    errors=errors,
                    execution_time=time.time() - start_time
                )

            # Stage 6: Send email
            self.logger.info("Stage 6: Sending email")
            try:
                success = self.email_sender.send(self.config.recipient_email, email_content)

                if success:
                    articles_sent = len(summarized_articles)
                    self.logger.info(f"OK: Email sent successfully to {self.config.recipient_email}")

                    # Update history with sent articles
                    if summarized_articles:
                        self.deduplicator.update_history(summarized_articles)
                        self.logger.info("OK: Updated article history")

                else:
                    error_msg = "CRITICAL: Failed to send email"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

                    # Save email to file
                    try:
                        saved_path = self.email_sender.save_to_file(email_content)
                        self.logger.info(f"Saved email to file: {saved_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to save email to file: {e}")

                    return ExecutionResult(
                        success=False,
                        articles_fetched=articles_fetched,
                        articles_sent=0,
                        errors=errors,
                        execution_time=time.time() - start_time
                    )

            except Exception as e:
                error_msg = f"CRITICAL: Email sending failed: {e}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

                # Save email to file
                try:
                    saved_path = self.email_sender.save_to_file(email_content)
                    self.logger.info(f"Saved email to file: {saved_path}")
                except Exception as e:
                    self.logger.error(f"Failed to save email to file: {e}")

                return ExecutionResult(
                    success=False,
                    articles_fetched=articles_fetched,
                    articles_sent=0,
                    errors=errors,
                    execution_time=time.time() - start_time
                )

            # Pipeline completed successfully
            execution_time = time.time() - start_time
            self.logger.info("=" * 70)
            self.logger.info(f"Pipeline completed successfully in {execution_time:.2f} seconds")
            self.logger.info(f"Articles: {articles_fetched} fetched -> {len(unique_articles)} unique -> {articles_sent} sent")
            self.logger.info("=" * 70)

            result = ExecutionResult(
                success=True,
                articles_fetched=articles_fetched,
                articles_sent=articles_sent,
                errors=errors,
                execution_time=execution_time
            )

            # Save execution history
            self._save_execution_history(result)

            return result

        except Exception as e:
            error_msg = f"CRITICAL: Unexpected pipeline error: {e}"
            self.logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                articles_fetched=articles_fetched,
                articles_sent=articles_sent,
                errors=errors,
                execution_time=execution_time
            )

    async def _send_error_notification(self, error_message: str) -> None:
        """
        Send error notification email.

        Args:
            error_message: Error message to include in notification
        """
        try:
            from .models import EmailContent

            content = EmailContent(
                subject="[ERROR] Daily AI News Aggregator Failed",
                html_body=f"""
                <html>
                <body>
                    <h2>News Aggregator Error</h2>
                    <p>The daily news aggregation pipeline encountered an error:</p>
                    <pre>{error_message}</pre>
                    <p>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </body>
                </html>
                """,
                plain_text_body=f"""
                News Aggregator Error

                The daily news aggregation pipeline encountered an error:

                {error_message}

                Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
            )

            self.email_sender.send(self.config.recipient_email, content, max_retries=1)

        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")

    def _save_execution_history(self, result: ExecutionResult) -> None:
        """
        Save execution result to history file.

        Args:
            result: Execution result to save
        """
        try:
            history_file = self.config.execution_history_file

            # Load existing history
            history = []
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            # Add new result
            history.append(result.to_dict())

            # Keep only last 30 days
            cutoff = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            history = [
                h for h in history
                if datetime.fromisoformat(h['timestamp']).timestamp() >= cutoff
            ]

            # Save updated history
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"Saved execution history to {history_file}")

        except Exception as e:
            self.logger.error(f"Failed to save execution history: {e}")
