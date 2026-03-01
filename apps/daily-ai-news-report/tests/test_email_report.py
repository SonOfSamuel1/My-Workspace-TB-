"""Tests for Email Report Generator module."""

import pytest
from datetime import datetime

from src.email_report import EmailReportGenerator
from src.rss_fetcher import Article


class TestEmailReportGenerator:
    """Tests for EmailReportGenerator class."""

    def test_init_default_values(self):
        """Test default initialization."""
        generator = EmailReportGenerator()

        assert generator.subject_prefix == "[AI News]"

    def test_init_custom_prefix(self):
        """Test custom subject prefix."""
        generator = EmailReportGenerator(subject_prefix="[Custom]")

        assert generator.subject_prefix == "[Custom]"

    def test_generate_with_articles(self, sample_articles):
        """Test report generation with articles."""
        generator = EmailReportGenerator()
        result = generator.generate(sample_articles)

        assert 'subject' in result
        assert 'html' in result
        assert 'text' in result

        assert "[AI News]" in result['subject']
        assert "OpenAI" in result['html']
        assert "OpenAI" in result['text']

    def test_generate_without_articles(self):
        """Test report generation with no articles."""
        generator = EmailReportGenerator()
        result = generator.generate([])

        assert 'subject' in result
        assert 'html' in result
        assert "No new AI news" in result['html']

    def test_html_structure(self, sample_articles):
        """Test that HTML has proper structure."""
        generator = EmailReportGenerator()
        result = generator.generate(sample_articles)

        html = result['html']

        assert '<!DOCTYPE html>' in html
        assert '<html>' in html
        assert '</html>' in html
        assert '<body>' in html
        assert '</body>' in html

    def test_plain_text_formatting(self, sample_articles):
        """Test plain text version formatting."""
        generator = EmailReportGenerator()
        result = generator.generate(sample_articles)

        text = result['text']

        # Should have numbered articles
        assert "1." in text
        assert "Source:" in text
        assert "Link:" in text

    def test_subject_includes_date(self):
        """Test that subject includes today's date."""
        generator = EmailReportGenerator()
        result = generator.generate([])

        today = datetime.now().strftime("%B %d, %Y")
        assert today in result['subject']

    def test_article_count_in_footer(self, sample_articles):
        """Test that article count appears in report."""
        generator = EmailReportGenerator()
        result = generator.generate(sample_articles)

        assert str(len(sample_articles)) in result['html']

    def test_source_count_in_footer(self, sample_articles):
        """Test that source count appears in report."""
        generator = EmailReportGenerator()
        result = generator.generate(sample_articles)

        # Get unique sources
        sources = set(a.source for a in sample_articles)
        assert str(len(sources)) in result['html']
