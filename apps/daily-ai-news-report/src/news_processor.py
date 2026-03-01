"""
News Processor - Filters, deduplicates, and scores articles.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional, Set

from .rss_fetcher import Article

logger = logging.getLogger(__name__)

# AI-related keywords for relevance scoring
AI_KEYWORDS = {
    'high': [
        'artificial intelligence', 'machine learning', 'deep learning',
        'neural network', 'llm', 'large language model', 'gpt', 'claude',
        'openai', 'anthropic', 'generative ai', 'transformer', 'chatbot',
        'natural language processing', 'nlp', 'computer vision',
    ],
    'medium': [
        'automation', 'algorithm', 'data science', 'robotics',
        'predictive', 'model training', 'inference', 'embedding',
        'fine-tuning', 'prompt engineering', 'ai agent', 'multimodal',
    ],
    'low': [
        'tech', 'software', 'cloud', 'api', 'startup', 'innovation',
        'digital', 'platform', 'tool', 'application',
    ]
}


class NewsProcessor:
    """Processes and filters news articles."""

    def __init__(
        self,
        max_articles: int = 10,
        min_relevance_score: float = 0.3,
        dedup_window_days: int = 7
    ):
        """
        Initialize the news processor.

        Args:
            max_articles: Maximum number of articles to return
            min_relevance_score: Minimum relevance score (0-1) to include
            dedup_window_days: Days to look back for deduplication
        """
        self.max_articles = max_articles
        self.min_relevance_score = min_relevance_score
        self.dedup_window_days = dedup_window_days
        self._seen_hashes: Set[str] = set()

    def process(
        self,
        articles: List[Article],
        seen_hashes: Optional[Set[str]] = None
    ) -> List[Article]:
        """
        Process articles: deduplicate, score, filter, and sort.

        Args:
            articles: List of articles to process
            seen_hashes: Optional set of previously seen article hashes

        Returns:
            Processed and filtered list of articles
        """
        if seen_hashes:
            self._seen_hashes = seen_hashes

        # Filter by date
        articles = self._filter_by_date(articles)

        # Deduplicate
        articles = self._deduplicate(articles)

        # Score and filter by relevance
        scored_articles = []
        for article in articles:
            score = self._calculate_relevance_score(article)
            if score >= self.min_relevance_score:
                article.relevance_score = score
                scored_articles.append((score, article))

        # Sort by score (descending) and take top N
        scored_articles.sort(key=lambda x: (-x[0], x[1].published or datetime.min), reverse=False)
        top_articles = [article for _, article in scored_articles[:self.max_articles]]

        logger.info(f"Processed {len(articles)} articles, returning {len(top_articles)}")
        return top_articles

    def _filter_by_date(self, articles: List[Article]) -> List[Article]:
        """Filter articles to only include recent ones."""
        cutoff = datetime.now() - timedelta(days=self.dedup_window_days)
        filtered = []
        for article in articles:
            if article.published is None or article.published >= cutoff:
                filtered.append(article)
        return filtered

    def _deduplicate(self, articles: List[Article]) -> List[Article]:
        """Remove duplicate articles based on title similarity."""
        unique_articles = []
        for article in articles:
            article_hash = self._generate_hash(article)
            if article_hash not in self._seen_hashes:
                self._seen_hashes.add(article_hash)
                unique_articles.append(article)
        return unique_articles

    def _generate_hash(self, article: Article) -> str:
        """Generate a hash for deduplication."""
        # Normalize title for comparison
        normalized_title = re.sub(r'[^\w\s]', '', article.title.lower())
        normalized_title = ' '.join(normalized_title.split())
        content = f"{normalized_title}|{article.source}"
        return hashlib.md5(content.encode()).hexdigest()

    def _calculate_relevance_score(self, article: Article) -> float:
        """
        Calculate relevance score for an article.

        Returns:
            Score between 0 and 1
        """
        text = f"{article.title} {article.summary}".lower()
        score = 0.0

        # Check high-priority keywords
        for keyword in AI_KEYWORDS['high']:
            if keyword in text:
                score += 0.3

        # Check medium-priority keywords
        for keyword in AI_KEYWORDS['medium']:
            if keyword in text:
                score += 0.15

        # Check low-priority keywords
        for keyword in AI_KEYWORDS['low']:
            if keyword in text:
                score += 0.05

        # Normalize to 0-1 range
        return min(score, 1.0)

    def get_seen_hashes(self) -> Set[str]:
        """Return the set of seen article hashes for persistence."""
        return self._seen_hashes
