#!/usr/bin/env python3
"""
HTML Report Generator for Atlanta News Report

Generates formatted HTML email reports using Jinja2 templates.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

from jinja2 import Environment, FileSystemLoader, select_autoescape
import pytz

from news_analyzer import ProcessedNews


logger = logging.getLogger(__name__)


class NewsReportGenerator:
    """
    Generates HTML reports from processed news data.

    Uses Jinja2 templates for flexible report formatting.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the report generator.

        Args:
            config: Report configuration dictionary
        """
        self.config = config
        self.timezone = pytz.timezone(
            config.get('timezone', 'America/New_York')
        )

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Register custom filters
        self.env.filters['format_date'] = self._format_date
        self.env.filters['format_datetime'] = self._format_datetime
        self.env.filters['truncate_summary'] = self._truncate_summary
        self.env.filters['format_relative'] = self._format_relative_time
        self.env.filters['urlencode'] = lambda s: quote_plus(s) if s else ''

    def generate_html_report(
        self,
        processed_news: ProcessedNews,
        template_name: str = 'weekly_news_report.html'
    ) -> str:
        """
        Generate an HTML report from processed news data.

        Args:
            processed_news: ProcessedNews object with categorized articles
            template_name: Name of the template file to use

        Returns:
            Rendered HTML string
        """
        logger.info("Generating HTML report...")

        # Prepare template context
        context = self._prepare_context(processed_news)

        # Load and render template
        template = self.env.get_template(template_name)
        html_content = template.render(**context)

        logger.info(
            f"Report generated: {len(html_content)} characters, "
            f"{processed_news.total_count} articles"
        )

        return html_content

    def _prepare_context(self, processed_news: ProcessedNews) -> Dict[str, Any]:
        """
        Prepare the template context dictionary.

        Args:
            processed_news: ProcessedNews object

        Returns:
            Context dictionary for template rendering
        """
        now = datetime.now(self.timezone)

        return {
            # Report metadata
            'title': 'Atlanta Weekly News Digest',
            'header_emoji': '',
            'generated_at': now.strftime('%B %d, %Y at %I:%M %p'),
            'generated_timestamp': now.isoformat(),

            # Period information
            'period': {
                'start_date': processed_news.period_start.strftime('%B %d'),
                'end_date': processed_news.period_end.strftime('%B %d, %Y'),
                'start_full': processed_news.period_start.strftime('%Y-%m-%d'),
                'end_full': processed_news.period_end.strftime('%Y-%m-%d'),
            },

            # Article data
            'top_stories': processed_news.top_stories,
            'general_news': processed_news.general_news,
            'business_news': processed_news.business_news,

            # Statistics
            'stats': {
                'total_count': processed_news.total_count,
                'top_stories_count': len(processed_news.top_stories),
                'general_count': len(processed_news.general_news),
                'business_count': len(processed_news.business_news),
                'sources_count': len(processed_news.sources_count),
                'duplicates_removed': processed_news.duplicates_removed,
            },

            # Sources breakdown
            'sources': processed_news.sources_count,

            # Configuration
            'config': self.config,
        }

    def _format_date(self, dt: datetime) -> str:
        """Format datetime as readable date string."""
        if dt is None:
            return ""
        if isinstance(dt, str):
            return dt
        return dt.strftime('%B %d, %Y')

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime with time."""
        if dt is None:
            return ""
        if isinstance(dt, str):
            return dt
        return dt.strftime('%B %d, %Y at %I:%M %p')

    def _truncate_summary(self, text: str, length: int = 200) -> str:
        """Truncate text to specified length."""
        if not text:
            return ""
        if len(text) <= length:
            return text
        # Try to break at word boundary
        truncated = text[:length]
        last_space = truncated.rfind(' ')
        if last_space > length - 50:
            truncated = truncated[:last_space]
        return truncated + "..."

    def _format_relative_time(self, dt: datetime) -> str:
        """Format datetime as relative time (e.g., '2 hours ago')."""
        if dt is None:
            return ""

        now = datetime.now(self.timezone)
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)

        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"

    def generate_subject(self, processed_news: ProcessedNews) -> str:
        """
        Generate email subject line.

        Args:
            processed_news: ProcessedNews object

        Returns:
            Formatted subject string
        """
        subject_template = self.config.get('email', {}).get(
            'subject_template',
            'Atlanta Weekly News Digest - {date}'
        )

        return subject_template.format(
            date=processed_news.period_end.strftime('%B %d, %Y'),
            count=processed_news.total_count
        )

    def generate_plain_text(self, processed_news: ProcessedNews) -> str:
        """
        Generate plain text version of the report.

        Args:
            processed_news: ProcessedNews object

        Returns:
            Plain text report string
        """
        lines = []
        lines.append("ATLANTA WEEKLY NEWS DIGEST")
        lines.append(f"Week of {processed_news.period_start.strftime('%B %d')} - "
                    f"{processed_news.period_end.strftime('%B %d, %Y')}")
        lines.append("")
        lines.append(f"Total Stories: {processed_news.total_count}")
        lines.append("=" * 60)
        lines.append("")

        # Top Stories
        if processed_news.top_stories:
            lines.append("TOP STORIES")
            lines.append("-" * 40)
            for i, article in enumerate(processed_news.top_stories, 1):
                lines.append(f"{i}. {article.title}")
                lines.append(f"   Source: {article.source}")
                lines.append(f"   Link: {article.url}")
                if article.summary:
                    summary = self._truncate_summary(article.summary, 150)
                    lines.append(f"   {summary}")
                lines.append("")

        # General News
        if processed_news.general_news:
            lines.append("")
            lines.append("GENERAL NEWS")
            lines.append("-" * 40)
            for article in processed_news.general_news:
                lines.append(f"- {article.title}")
                lines.append(f"  {article.source} | {article.url}")
                lines.append("")

        # Business News
        if processed_news.business_news:
            lines.append("")
            lines.append("BUSINESS & DEVELOPMENT")
            lines.append("-" * 40)
            for article in processed_news.business_news:
                lines.append(f"- {article.title}")
                lines.append(f"  {article.source} | {article.url}")
                lines.append("")

        lines.append("")
        lines.append("=" * 60)
        lines.append("Generated by Atlanta Weekly News Report")
        lines.append(f"Report generated on {datetime.now(self.timezone).strftime('%B %d, %Y at %I:%M %p')}")

        return "\n".join(lines)


if __name__ == '__main__':
    # Quick test
    import yaml
    from datetime import timedelta
    from news_fetcher import Article

    logging.basicConfig(level=logging.INFO)

    # Load config
    with open('../config.yaml') as f:
        config = yaml.safe_load(f)

    # Create sample processed news
    tz = pytz.timezone('America/New_York')
    now = datetime.now(tz)

    sample_articles = [
        Article(
            title="Atlanta Mayor announces major infrastructure plan",
            url="https://example.com/1",
            summary="The mayor unveiled a comprehensive infrastructure improvement plan "
                   "targeting roads, bridges, and public transit across the metro area.",
            published=now - timedelta(hours=5),
            source="Atlanta Journal-Constitution",
            category="general",
            image_url="https://example.com/image1.jpg"
        ),
        Article(
            title="Tech startup raises $50M funding round",
            url="https://example.com/2",
            summary="A promising Atlanta-based technology company has secured significant "
                   "venture capital funding to expand operations.",
            published=now - timedelta(days=1),
            source="Atlanta Business Chronicle",
            category="business"
        ),
    ]

    processed = ProcessedNews(
        top_stories=sample_articles[:1],
        general_news=sample_articles[1:],
        business_news=[],
        total_count=len(sample_articles),
        sources_count={"AJC": 1, "ABC": 1},
        period_start=now - timedelta(days=7),
        period_end=now,
        duplicates_removed=0
    )

    generator = NewsReportGenerator(config['atlanta_news_report'])

    # Generate HTML
    html = generator.generate_html_report(processed)
    print(f"HTML length: {len(html)} characters")

    # Generate subject
    subject = generator.generate_subject(processed)
    print(f"Subject: {subject}")

    # Generate plain text
    plain = generator.generate_plain_text(processed)
    print("\nPlain text preview:")
    print(plain[:500])
