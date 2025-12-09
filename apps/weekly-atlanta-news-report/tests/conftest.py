"""
Pytest configuration and shared fixtures for Atlanta News Report tests.
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytz

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from news_fetcher import Article


@pytest.fixture
def timezone():
    """Return the default timezone for tests."""
    return pytz.timezone('America/New_York')


@pytest.fixture
def sample_articles(timezone):
    """Generate sample articles for testing."""
    now = datetime.now(timezone)

    return [
        Article(
            title="Atlanta Mayor announces new infrastructure plan",
            url="https://example.com/article1",
            summary="The mayor unveiled a comprehensive infrastructure improvement plan "
                   "targeting roads, bridges, and public transit across the metro area.",
            published=now - timedelta(hours=2),
            source="Atlanta Journal-Constitution",
            category="general",
            image_url="https://example.com/image1.jpg"
        ),
        Article(
            title="Atlanta Mayor reveals new infrastructure initiative",
            url="https://example.com/article2",
            summary="A new initiative was announced today by city officials.",
            published=now - timedelta(hours=4),
            source="11Alive",
            category="general"
        ),
        Article(
            title="Tech startup raises $50M in Atlanta funding round",
            url="https://example.com/article3",
            summary="A promising Atlanta-based technology company has secured significant "
                   "venture capital funding to expand its operations.",
            published=now - timedelta(days=1),
            source="Atlanta Business Chronicle",
            category="business"
        ),
        Article(
            title="New restaurant opens in Midtown Atlanta",
            url="https://example.com/article4",
            summary="A highly anticipated new restaurant has opened its doors.",
            published=now - timedelta(days=2),
            source="WSB-TV",
            category="general"
        ),
        Article(
            title="Atlanta housing market sees record growth",
            url="https://example.com/article5",
            summary="Real estate prices continue to climb in the metro area.",
            published=now - timedelta(days=3),
            source="Atlanta Business Chronicle",
            category="business"
        ),
        Article(
            title="Weather forecast: Rain expected this weekend",
            url="https://example.com/article6",
            summary="Meteorologists predict scattered showers for the Atlanta area.",
            published=now - timedelta(hours=6),
            source="Fox 5 Atlanta",
            category="general"
        ),
    ]


@pytest.fixture
def sample_config():
    """Return sample configuration for tests."""
    return {
        'atlanta_news_report': {
            'enabled': True,
            'timezone': 'America/New_York',
            'feeds': [
                {
                    'name': 'Test Feed 1',
                    'url': 'https://example.com/feed1.xml',
                    'category': 'general'
                },
                {
                    'name': 'Test Feed 2',
                    'url': 'https://example.com/feed2.xml',
                    'category': 'business'
                }
            ],
            'report': {
                'max_articles': 25,
                'min_articles': 15,
                'lookback_days': 7,
                'deduplicate': True,
                'similarity_threshold': 0.7,
                'top_stories_count': 5
            },
            'email': {
                'subject_template': 'Atlanta Weekly News Digest - {date}',
                'recipient': 'test@example.com'
            }
        },
        'logging': {
            'level': 'INFO',
            'file': '/tmp/test_atlanta_news.log'
        }
    }


@pytest.fixture
def rss_feed_response():
    """Return sample RSS feed XML response."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test News Feed</title>
            <link>https://example.com</link>
            <description>Test feed for Atlanta news</description>
            <item>
                <title>Test Article Title</title>
                <link>https://example.com/test-article</link>
                <description>This is a test article description.</description>
                <pubDate>Mon, 02 Dec 2024 12:00:00 GMT</pubDate>
            </item>
            <item>
                <title>Another Test Article</title>
                <link>https://example.com/another-article</link>
                <description>Another test article description.</description>
                <pubDate>Mon, 02 Dec 2024 10:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    '''
