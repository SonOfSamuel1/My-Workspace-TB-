#!/usr/bin/env python3
"""
News Analyzer for Atlanta News Report

Processes, filters, deduplicates, and ranks news articles.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from collections import defaultdict

import pytz

from news_fetcher import Article


logger = logging.getLogger(__name__)


@dataclass
class ProcessedNews:
    """Container for processed news data."""
    top_stories: List[Article]
    general_news: List[Article]
    business_news: List[Article]
    total_count: int
    sources_count: Dict[str, int]
    period_start: datetime
    period_end: datetime
    duplicates_removed: int


class NewsAnalyzer:
    """
    Analyzes and processes news articles for the weekly report.

    Handles filtering, deduplication, ranking, and categorization.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the analyzer with configuration.

        Args:
            config: Report configuration dictionary
        """
        self.config = config
        report_config = config.get('report', {})

        self.max_articles = report_config.get('max_articles', 25)
        self.min_articles = report_config.get('min_articles', 15)
        self.lookback_days = report_config.get('lookback_days', 7)
        self.deduplicate = report_config.get('deduplicate', True)
        self.similarity_threshold = report_config.get('similarity_threshold', 0.7)
        self.top_stories_count = report_config.get('top_stories_count', 7)

        self.timezone = pytz.timezone(
            config.get('timezone', 'America/New_York')
        )

    def process_articles(self, articles: List[Article]) -> ProcessedNews:
        """
        Main processing pipeline for articles.

        Args:
            articles: Raw list of articles from fetcher

        Returns:
            ProcessedNews object with categorized and ranked articles
        """
        logger.info(f"Processing {len(articles)} raw articles...")

        # Calculate time window
        now = datetime.now(self.timezone)
        period_end = now
        period_start = now - timedelta(days=self.lookback_days)

        # Step 1: Filter by date
        filtered = self.filter_by_date(articles, period_start, period_end)
        logger.info(f"After date filter: {len(filtered)} articles")

        # Step 2: Deduplicate
        original_count = len(filtered)
        if self.deduplicate:
            filtered = self.deduplicate_articles(filtered)
            duplicates_removed = original_count - len(filtered)
            logger.info(
                f"After deduplication: {len(filtered)} articles "
                f"({duplicates_removed} duplicates removed)"
            )
        else:
            duplicates_removed = 0

        # Step 3: Rank by relevance/recency
        ranked = self.rank_articles(filtered)

        # Step 4: Categorize
        categorized = self.categorize_articles(ranked)

        # Step 5: Select top stories
        top_stories = self._select_top_stories(categorized)

        # Step 6: Prepare final lists (exclude top stories from categories)
        top_story_ids = {a.id for a in top_stories}
        general_news = [
            a for a in categorized.get('general', [])
            if a.id not in top_story_ids
        ][:self.max_articles // 2]

        business_news = [
            a for a in categorized.get('business', [])
            if a.id not in top_story_ids
        ][:self.max_articles // 3]

        # Count sources
        all_articles = top_stories + general_news + business_news
        sources_count = defaultdict(int)
        for article in all_articles:
            sources_count[article.source] += 1

        return ProcessedNews(
            top_stories=top_stories,
            general_news=general_news,
            business_news=business_news,
            total_count=len(all_articles),
            sources_count=dict(sources_count),
            period_start=period_start,
            period_end=period_end,
            duplicates_removed=duplicates_removed
        )

    def filter_by_date(
        self,
        articles: List[Article],
        start_date: datetime,
        end_date: datetime
    ) -> List[Article]:
        """
        Filter articles to those within the date range.

        Args:
            articles: List of articles
            start_date: Start of time window
            end_date: End of time window

        Returns:
            Filtered list of articles
        """
        filtered = []
        for article in articles:
            # Ensure article date is timezone aware
            pub_date = article.published
            if pub_date.tzinfo is None:
                pub_date = self.timezone.localize(pub_date)

            # Convert to same timezone for comparison
            pub_date = pub_date.astimezone(self.timezone)
            start_aware = start_date.astimezone(self.timezone)
            end_aware = end_date.astimezone(self.timezone)

            if start_aware <= pub_date <= end_aware:
                filtered.append(article)

        return filtered

    def deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """
        Remove duplicate or very similar articles.

        Uses title similarity to detect duplicates across different sources.

        Args:
            articles: List of articles

        Returns:
            Deduplicated list of articles
        """
        if not articles:
            return []

        # Sort by date (newest first) so we keep the most recent version
        sorted_articles = sorted(
            articles,
            key=lambda a: a.published,
            reverse=True
        )

        unique = []
        seen_titles = []

        for article in sorted_articles:
            # Check similarity against all previously seen titles
            is_duplicate = False
            title_lower = article.title.lower()

            for seen_title in seen_titles:
                similarity = self._calculate_similarity(title_lower, seen_title)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    logger.debug(
                        f"Duplicate found: '{article.title}' "
                        f"(similarity: {similarity:.2f})"
                    )
                    break

            if not is_duplicate:
                unique.append(article)
                seen_titles.append(title_lower)

        return unique

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two strings.

        Args:
            text1: First string
            text2: Second string

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def rank_articles(self, articles: List[Article]) -> List[Article]:
        """
        Rank articles by relevance and recency.

        Scoring factors:
        - Recency (more recent = higher score)
        - Title length (moderate length preferred)
        - Has image (bonus points)
        - Has summary (bonus points)

        Args:
            articles: List of articles

        Returns:
            Sorted list of articles (highest score first)
        """
        if not articles:
            return []

        now = datetime.now(self.timezone)
        scored = []

        for article in articles:
            score = 0.0

            # Recency score (0-50 points)
            # Newer articles get higher scores
            pub_date = article.published
            if pub_date.tzinfo is None:
                pub_date = self.timezone.localize(pub_date)

            hours_old = (now - pub_date).total_seconds() / 3600
            recency_score = max(0, 50 - (hours_old / 4))  # Decay over ~8 days
            score += recency_score

            # Title quality score (0-20 points)
            title_len = len(article.title)
            if 30 <= title_len <= 100:
                score += 20
            elif 20 <= title_len <= 120:
                score += 10

            # Content quality (0-20 points)
            if article.summary and len(article.summary) > 50:
                score += 15
            if article.image_url:
                score += 5

            # Category bonus (business news slight boost)
            if article.category in ['business', 'development']:
                score += 5

            scored.append((score, article))

        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)

        return [article for _, article in scored]

    def categorize_articles(
        self,
        articles: List[Article]
    ) -> Dict[str, List[Article]]:
        """
        Group articles by category.

        Args:
            articles: List of articles

        Returns:
            Dictionary mapping category names to article lists
        """
        categories = defaultdict(list)

        for article in articles:
            cat = article.category.lower()
            # Normalize category names
            if cat in ['business', 'development', 'economy']:
                categories['business'].append(article)
            else:
                categories['general'].append(article)

        return dict(categories)

    def _select_top_stories(
        self,
        categorized: Dict[str, List[Article]]
    ) -> List[Article]:
        """
        Select top stories from all categories.

        Ensures diversity by picking from multiple sources and categories.

        Args:
            categorized: Dictionary of categorized articles

        Returns:
            List of top story articles
        """
        top_stories = []
        used_sources = set()

        # Get all articles sorted by score (they're already ranked)
        all_ranked = []
        for articles in categorized.values():
            all_ranked.extend(articles)

        # Re-sort to ensure proper ranking
        all_ranked = self.rank_articles(all_ranked)

        # Select top stories with source diversity
        for article in all_ranked:
            if len(top_stories) >= self.top_stories_count:
                break

            # Allow max 2 articles from same source in top stories
            source_count = sum(
                1 for a in top_stories if a.source == article.source
            )
            if source_count < 2:
                top_stories.append(article)

        return top_stories

    def get_statistics(self, processed: ProcessedNews) -> Dict[str, Any]:
        """
        Generate statistics about the processed news.

        Args:
            processed: ProcessedNews object

        Returns:
            Dictionary of statistics
        """
        return {
            'total_articles': processed.total_count,
            'top_stories': len(processed.top_stories),
            'general_news': len(processed.general_news),
            'business_news': len(processed.business_news),
            'duplicates_removed': processed.duplicates_removed,
            'sources': processed.sources_count,
            'period': {
                'start': processed.period_start.strftime('%Y-%m-%d'),
                'end': processed.period_end.strftime('%Y-%m-%d'),
                'days': self.lookback_days
            }
        }


if __name__ == '__main__':
    # Quick test with sample data
    import yaml

    logging.basicConfig(level=logging.INFO)

    # Load config
    with open('../config.yaml') as f:
        config = yaml.safe_load(f)

    # Create sample articles for testing
    now = datetime.now(pytz.timezone('America/New_York'))

    sample_articles = [
        Article(
            title="Atlanta Mayor announces new infrastructure plan",
            url="https://example.com/1",
            summary="The mayor unveiled a comprehensive plan...",
            published=now - timedelta(hours=2),
            source="AJC",
            category="general"
        ),
        Article(
            title="Atlanta Mayor reveals new infrastructure initiative",  # Similar
            url="https://example.com/2",
            summary="A new initiative was announced...",
            published=now - timedelta(hours=4),
            source="11Alive",
            category="general"
        ),
        Article(
            title="Tech startup raises $50M in Atlanta",
            url="https://example.com/3",
            summary="A local tech company has secured funding...",
            published=now - timedelta(days=1),
            source="Atlanta Business Chronicle",
            category="business"
        ),
    ]

    analyzer = NewsAnalyzer(config['atlanta_news_report'])
    processed = analyzer.process_articles(sample_articles)

    print("\n=== Processing Results ===")
    print(f"Top Stories: {len(processed.top_stories)}")
    print(f"General News: {len(processed.general_news)}")
    print(f"Business News: {len(processed.business_news)}")
    print(f"Duplicates Removed: {processed.duplicates_removed}")
