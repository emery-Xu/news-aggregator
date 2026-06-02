"""Tests for web interface: storage layer and FastAPI routes."""

import json
from datetime import date, datetime

import pytest

from news_aggregator.models import SummarizedArticle
from news_aggregator.web.storage import ArticleStore


class TestArticleStore:

    @pytest.fixture
    def store(self, tmp_path):
        return ArticleStore(base_dir=tmp_path / "articles")

    @pytest.fixture
    def sample_articles(self):
        return [
            SummarizedArticle(
                url="https://example.com/article1",
                title="Test Article 1",
                content="Content for article 1 with enough text to be meaningful.",
                published_at=datetime(2026, 6, 1, 10, 0, 0),
                topic="ai",
                source="Test Source",
                summary_bullets=["Bullet 1", "Bullet 2"],
                audience_level="cs_student",
                quality_score=0.85,
            ),
            SummarizedArticle(
                url="https://example.com/article2",
                title="Test Article 2",
                content="Content for article 2 with enough text to be meaningful.",
                published_at=datetime(2026, 6, 1, 11, 0, 0),
                topic="robotics",
                source="Robot Source",
                summary_bullets=["Robot bullet"],
                audience_level="beginner",
                quality_score=0.6,
            ),
        ]

    def test_save_and_load_articles(self, store, sample_articles):
        target_date = date(2026, 6, 1)
        store.save_articles(sample_articles, target_date)

        loaded = store.load_articles(target_date)
        assert len(loaded) == 2
        assert loaded[0]["title"] == "Test Article 1"
        assert loaded[0]["quality_score"] == 0.85
        assert loaded[0]["summary_bullets"] == ["Bullet 1", "Bullet 2"]
        assert loaded[1]["topic"] == "robotics"

    def test_load_nonexistent_date(self, store):
        loaded = store.load_articles(date(2020, 1, 1))
        assert loaded == []

    def test_list_available_dates(self, store, sample_articles):
        store.save_articles(sample_articles, date(2026, 6, 1))
        store.save_articles(sample_articles[:1], date(2026, 6, 2))
        store.save_articles(sample_articles, date(2026, 5, 30))

        dates = store.list_available_dates()
        assert dates == [date(2026, 6, 2), date(2026, 6, 1), date(2026, 5, 30)]

    def test_list_available_dates_empty(self, store):
        assert store.list_available_dates() == []

    def test_get_latest_date(self, store, sample_articles):
        store.save_articles(sample_articles, date(2026, 6, 1))
        store.save_articles(sample_articles, date(2026, 6, 3))

        assert store.get_latest_date() == date(2026, 6, 3)

    def test_get_latest_date_empty(self, store):
        assert store.get_latest_date() is None

    def test_get_article_count(self, store, sample_articles):
        store.save_articles(sample_articles, date(2026, 6, 1))
        assert store.get_article_count(date(2026, 6, 1)) == 2
        assert store.get_article_count(date(2026, 6, 2)) == 0

    def test_save_creates_directory(self, tmp_path, sample_articles):
        base = tmp_path / "deep" / "nested" / "articles"
        store = ArticleStore(base_dir=base)
        store.save_articles(sample_articles, date(2026, 6, 1))
        assert (base / "2026-06-01.json").exists()

    def test_json_format(self, store, sample_articles):
        target_date = date(2026, 6, 1)
        store.save_articles(sample_articles, target_date)

        file_path = store._date_to_path(target_date)
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["date"] == "2026-06-01"
        assert "generated_at" in data
        assert len(data["articles"]) == 2

    def test_overwrite_existing_date(self, store, sample_articles):
        target_date = date(2026, 6, 1)
        store.save_articles(sample_articles, target_date)
        store.save_articles(sample_articles[:1], target_date)

        loaded = store.load_articles(target_date)
        assert len(loaded) == 1


class TestSummarizedArticleQualityScore:

    def test_quality_score_default(self):
        article = SummarizedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            published_at=datetime.now(),
            topic="ai",
            source="Source",
        )
        assert article.quality_score == 0.0

    def test_quality_score_in_to_dict(self):
        article = SummarizedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
            published_at=datetime(2026, 6, 1),
            topic="ai",
            source="Source",
            quality_score=0.75,
        )
        data = article.to_dict()
        assert data["quality_score"] == 0.75

    def test_quality_score_from_dict(self):
        data = {
            "url": "https://example.com",
            "title": "Test",
            "content": "Content",
            "published_at": "2026-06-01T10:00:00",
            "topic": "ai",
            "source": "Source",
            "summary_bullets": ["b1"],
            "audience_level": "beginner",
            "summarization_failed": False,
            "quality_score": 0.9,
        }
        article = SummarizedArticle.from_dict(data)
        assert article.quality_score == 0.9

    def test_quality_score_from_article(self):
        from news_aggregator.models import Article

        base = Article(
            url="https://example.com",
            title="Test",
            content="Content",
            published_at=datetime.now(),
            topic="ai",
            source="Source",
        )
        summarized = SummarizedArticle.from_article(base, quality_score=0.82)
        assert summarized.quality_score == 0.82
