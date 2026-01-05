"""Processing package for article filtering, ranking, and deduplication."""

from .ranker import ArticleRanker
from .deduplicator import Deduplicator
from .summarizer import AdaptiveSummarizer

__all__ = ['ArticleRanker', 'Deduplicator', 'AdaptiveSummarizer']
