"""Data models for the News Aggregator."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class Article:
    """Represents a news article."""

    url: str
    title: str
    content: str
    published_at: datetime
    topic: str
    source: str

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        if not isinstance(other, Article):
            return False
        return self.url == other.url

    def to_dict(self) -> dict:
        """Convert article to dictionary for JSON serialization."""
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create Article from dictionary."""
        data = data.copy()
        if isinstance(data["published_at"], str):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        return cls(**data)


@dataclass
class RankedArticle:
    """Article with quality score."""

    article: Article
    quality_score: float  # 0-1 score based on content depth, recency, source trust

    def to_dict(self) -> dict:
        """Convert ranked article to dictionary for JSON serialization."""
        return {"article": self.article.to_dict(), "quality_score": self.quality_score}

    @classmethod
    def from_dict(cls, data: dict) -> "RankedArticle":
        """Create RankedArticle from dictionary."""
        return cls(
            article=Article.from_dict(data["article"]),
            quality_score=data["quality_score"],
        )


@dataclass
class SummarizedArticle(Article):
    """Article with AI-generated summary."""

    summary_bullets: List[str] = field(default_factory=list)
    audience_level: str = "beginner"  # "beginner" or "cs_student"
    summarization_failed: bool = False
    quality_score: float = 0.0

    def to_dict(self) -> dict:
        """Convert summarized article to dictionary for JSON serialization."""
        data = super().to_dict()
        data["summary_bullets"] = self.summary_bullets
        data["audience_level"] = self.audience_level
        data["summarization_failed"] = self.summarization_failed
        data["quality_score"] = self.quality_score
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SummarizedArticle":
        """Create SummarizedArticle from dictionary."""
        data = data.copy()
        if isinstance(data["published_at"], str):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        return cls(
            url=data["url"],
            title=data["title"],
            content=data["content"],
            published_at=data["published_at"],
            topic=data["topic"],
            source=data["source"],
            summary_bullets=data.get("summary_bullets", []),
            audience_level=data.get("audience_level", "beginner"),
            summarization_failed=data.get("summarization_failed", False),
            quality_score=data.get("quality_score", 0.0),
        )

    @classmethod
    def from_article(
        cls,
        article: Article,
        summary_bullets: list[str] | None = None,
        audience_level: str = "beginner",
        summarization_failed: bool = False,
        quality_score: float = 0.0,
    ) -> "SummarizedArticle":
        """Create SummarizedArticle from regular Article."""
        return cls(
            url=article.url,
            title=article.title,
            content=article.content,
            published_at=article.published_at,
            topic=article.topic,
            source=article.source,
            summary_bullets=summary_bullets or [],
            audience_level=audience_level,
            summarization_failed=summarization_failed,
            quality_score=quality_score,
        )


@dataclass
class EmailContent:
    """Email content with subject and body."""

    subject: str
    html_body: str
    plain_text_body: str


@dataclass
class ExecutionResult:
    """Results from a pipeline execution."""

    success: bool
    articles_fetched: int
    articles_sent: int
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert execution result to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionResult":
        """Create ExecutionResult from dictionary."""
        data = data.copy()
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class ArticleHistoryEntry:
    """Entry in the article history."""

    url: str
    title: str
    sent_at: datetime

    def to_dict(self) -> dict:
        """Convert entry to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "sent_at": self.sent_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ArticleHistoryEntry":
        """Create ArticleHistoryEntry from dictionary."""
        data = data.copy()
        if isinstance(data["sent_at"], str):
            data["sent_at"] = datetime.fromisoformat(data["sent_at"])
        return cls(**data)


@dataclass
class DiscoveredFeed:
    """Discovered RSS feed from CLI tool."""

    url: str
    is_valid: bool
    entry_count: Optional[int] = None
    error: Optional[str] = None


@dataclass
class FeedScore:
    """Feed quality score from CLI tool."""

    url: str
    update_frequency: float  # 0-1 score
    content_quality: float  # 0-1 score
    reliability: float  # 0-1 score
    total_score: float  # weighted average
    recommendation: str  # "add", "review", or "skip"
    error: Optional[str] = None  # Error message if scoring failed
