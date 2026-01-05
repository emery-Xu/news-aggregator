"""Email composition component for generating HTML emails."""

from datetime import datetime
from pathlib import Path
from typing import List, Dict
from jinja2 import Template, Environment, FileSystemLoader

from .models import SummarizedArticle, EmailContent
from .config import Config
from .logger import get_logger


class EmailComposer:
    """Composes HTML emails from summarized articles."""

    def __init__(self, config: Config, template_dir: Path = Path("templates")):
        """
        Initialize email composer.

        Args:
            config: Application configuration with topic settings
            template_dir: Directory containing email templates
        """
        self.config = config
        self.logger = get_logger()

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )

        try:
            self.template = self.env.get_template("email_template.html")
        except Exception as e:
            self.logger.error(f"Failed to load email template: {e}")
            raise

    def compose(self, articles: List[SummarizedArticle], date: datetime = None) -> EmailContent:
        """
        Generate email content from articles.

        Args:
            articles: List of summarized articles
            date: Date for the digest (defaults to today)

        Returns:
            EmailContent with subject and body
        """
        if date is None:
            date = datetime.now()

        # Group articles by topic
        grouped = self._group_by_topic(articles)

        # Calculate counts
        polymarket_count = len(grouped.get('polymarket', []))
        ai_count = len(grouped.get('ai', []))
        robotics_count = len(grouped.get('robotics', []))
        total_count = len(articles)

        # Get context text from config
        polymarket_context = None
        robotics_context = None
        if 'polymarket' in self.config.topics:
            topic_config = self.config.topics['polymarket']
            if topic_config.include_context:
                polymarket_context = topic_config.context_text

        if 'robotics' in self.config.topics:
            topic_config = self.config.topics['robotics']
            if topic_config.include_context:
                robotics_context = topic_config.context_text

        # Prepare template context
        context = {
            'date': date.strftime('%B %d, %Y'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'has_articles': total_count > 0,
            'total_count': total_count,
            'polymarket_count': polymarket_count,
            'ai_count': ai_count,
            'robotics_count': robotics_count,
            'polymarket_articles': grouped.get('polymarket', []),
            'ai_articles': grouped.get('ai', []),
            'robotics_articles': grouped.get('robotics', []),
            'polymarket_context': polymarket_context,
            'robotics_context': robotics_context
        }

        # Render HTML
        try:
            html_body = self.template.render(context)
        except Exception as e:
            self.logger.error(f"Failed to render email template: {e}")
            raise

        # Generate plain text version
        plain_text_body = self._generate_plain_text(articles, date, grouped)

        # Generate subject line
        if total_count == 0:
            subject = f"Daily AI News - {date.strftime('%b %d, %Y')} - No new articles"
        else:
            subject = f"Daily AI News - {date.strftime('%b %d, %Y')} - {total_count} articles"

        self.logger.info(f"Composed email with {total_count} articles")

        return EmailContent(
            subject=subject,
            html_body=html_body,
            plain_text_body=plain_text_body
        )

    def _group_by_topic(self, articles: List[SummarizedArticle]) -> Dict[str, List[SummarizedArticle]]:
        """
        Group articles by topic.

        Args:
            articles: List of articles

        Returns:
            Dictionary mapping topics to article lists
        """
        grouped: Dict[str, List[SummarizedArticle]] = {
            'polymarket': [],
            'ai': [],
            'robotics': []
        }

        for article in articles:
            topic = article.topic.lower()
            if topic in grouped:
                grouped[topic].append(article)
            else:
                self.logger.warning(f"Unknown topic '{topic}' for article: {article.title}")

        return grouped

    def _generate_plain_text(self, articles: List[SummarizedArticle], date: datetime,
                             grouped: Dict[str, List[SummarizedArticle]]) -> str:
        """
        Generate plain text version of the email.

        Args:
            articles: List of all articles
            date: Date of the digest
            grouped: Articles grouped by topic

        Returns:
            Plain text email body
        """
        lines = []
        lines.append(f"DAILY AI NEWS DIGEST - {date.strftime('%B %d, %Y')}")
        lines.append("=" * 70)
        lines.append("")

        if not articles:
            lines.append("No new articles today.")
            lines.append("")
            lines.append("Check back tomorrow for your daily digest!")
            return "\n".join(lines)

        # Summary
        polymarket_count = len(grouped.get('polymarket', []))
        ai_count = len(grouped.get('ai', []))
        robotics_count = len(grouped.get('robotics', []))
        total_count = len(articles)

        lines.append(f"Today's Summary:")
        lines.append(f"{polymarket_count} Polymarket | {ai_count} AI | {robotics_count} Robotics")
        lines.append(f"Total: {total_count} articles")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")

        # Polymarket section
        if grouped.get('polymarket'):
            lines.append("POLYMARKET NEWS")
            lines.append("-" * 70)
            for article in grouped['polymarket']:
                lines.append(f"\n{article.title}")
                lines.append(f"Source: {article.source}")
                if article.summary_bullets:
                    for bullet in article.summary_bullets:
                        lines.append(f"  • {bullet}")
                lines.append(f"Read more: {article.url}")
                lines.append("")

        # AI section
        if grouped.get('ai'):
            lines.append("AI NEWS")
            lines.append("-" * 70)
            for article in grouped['ai']:
                lines.append(f"\n{article.title}")
                lines.append(f"Source: {article.source}")
                if article.summary_bullets:
                    for bullet in article.summary_bullets:
                        lines.append(f"  • {bullet}")
                lines.append(f"Read more: {article.url}")
                lines.append("")

        # Robotics section
        if grouped.get('robotics'):
            lines.append("ROBOTICS NEWS")
            lines.append("-" * 70)
            for article in grouped['robotics']:
                lines.append(f"\n{article.title}")
                lines.append(f"Source: {article.source}")
                if article.summary_bullets:
                    for bullet in article.summary_bullets:
                        lines.append(f"  • {bullet}")
                lines.append(f"Read more: {article.url}")
                lines.append("")

        # Footer
        lines.append("-" * 70)
        lines.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("Daily AI News Aggregator")

        return "\n".join(lines)
