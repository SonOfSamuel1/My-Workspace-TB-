"""Pytest fixtures for Daily AI News Report tests."""

import pytest
from datetime import datetime

from src.rss_fetcher import Article


@pytest.fixture
def sample_articles():
    """Generate sample articles for testing."""
    return [
        Article(
            title="OpenAI Releases GPT-5 with Breakthrough Capabilities",
            link="https://example.com/article1",
            summary="OpenAI has announced the release of GPT-5, featuring significant improvements in reasoning and multimodal understanding.",
            published=datetime(2024, 1, 15, 10, 0),
            source="Tech News",
            category="research"
        ),
        Article(
            title="Google DeepMind Achieves New AI Milestone",
            link="https://example.com/article2",
            summary="Google DeepMind researchers have developed a new neural network architecture that demonstrates unprecedented performance.",
            published=datetime(2024, 1, 14, 14, 30),
            source="AI Weekly",
            category="research"
        ),
        Article(
            title="Enterprise AI Adoption Surges in 2024",
            link="https://example.com/article3",
            summary="A new report shows that enterprise AI adoption has increased by 45% compared to last year.",
            published=datetime(2024, 1, 13, 9, 0),
            source="Business Tech",
            category="industry"
        ),
    ]


@pytest.fixture
def sample_feed_config():
    """Sample RSS feed configuration."""
    return [
        {
            'name': 'Test Feed 1',
            'url': 'https://example.com/feed1.xml',
            'category': 'research'
        },
        {
            'name': 'Test Feed 2',
            'url': 'https://example.com/feed2.xml',
            'category': 'industry'
        },
    ]


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv('SENDER_EMAIL', 'test@example.com')
    monkeypatch.setenv('RECIPIENT_EMAIL', 'recipient@example.com')
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
