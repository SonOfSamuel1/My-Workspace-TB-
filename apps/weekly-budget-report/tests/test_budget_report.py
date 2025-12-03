"""
Unit tests for BudgetReportGenerator class.
"""
import pytest
from pathlib import Path
from datetime import datetime

from budget_report import BudgetReportGenerator


class TestBudgetReportGeneratorInit:
    """Tests for BudgetReportGenerator initialization."""

    def test_init_with_config(self, sample_config):
        """Test generator initializes with config."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        assert generator.config == sample_config['budget_report']

    def test_init_finds_templates(self, sample_config):
        """Test generator finds templates directory."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        # Templates should exist in src/templates
        assert generator.use_templates is True
        assert generator.jinja_env is not None

    def test_init_with_custom_template_dir(self, sample_config, tmp_path):
        """Test generator with custom template directory."""
        # Create a temporary templates directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a minimal base template
        (templates_dir / "base.html").write_text("<html>{{ content }}</html>")
        (templates_dir / "weekly_report.html").write_text(
            "{% extends 'base.html' %}{% block content %}Test{% endblock %}"
        )

        generator = BudgetReportGenerator(
            sample_config['budget_report'],
            template_dir=str(templates_dir)
        )
        assert generator.use_templates is True

    def test_init_with_missing_templates(self, sample_config, tmp_path):
        """Test generator falls back when templates missing."""
        nonexistent_dir = tmp_path / "nonexistent"
        generator = BudgetReportGenerator(
            sample_config['budget_report'],
            template_dir=str(nonexistent_dir)
        )
        assert generator.use_templates is False


class TestBudgetReportGeneration:
    """Tests for HTML report generation."""

    @pytest.fixture
    def sample_report_data(self, sample_month_budget):
        """Create sample report data."""
        return {
            'period': {
                'start_date': '2025-11-19',
                'end_date': '2025-11-26',
                'days': 7
            },
            'analysis': {
                'summary': {
                    'total_inflow': 3500.00,
                    'total_outflow': 2100.00,
                    'net': 1400.00,
                    'transaction_count': 25
                },
                'category_breakdown': [
                    {
                        'category_id': 'cat-1',
                        'category_name': 'Groceries',
                        'category_group': 'True Expenses',
                        'amount': 650.00,
                        'transaction_count': 8
                    },
                    {
                        'category_id': 'cat-2',
                        'category_name': 'Dining Out',
                        'category_group': 'Quality of Life',
                        'amount': 280.00,
                        'transaction_count': 5
                    }
                ],
                'payee_breakdown': [
                    {
                        'payee_name': 'Whole Foods',
                        'amount': 450.00,
                        'transaction_count': 5
                    },
                    {
                        'payee_name': 'Amazon',
                        'amount': 250.00,
                        'transaction_count': 3
                    }
                ],
                'notable_transactions': [
                    {
                        'date': '2025-11-25',
                        'payee': 'Landlord LLC',
                        'category': 'Rent/Mortgage',
                        'amount': 1500.00,
                        'memo': 'Monthly rent',
                        'is_inflow': False
                    }
                ],
                'account_breakdown': [
                    {
                        'account_name': 'Checking',
                        'inflow': 3500.00,
                        'outflow': 1800.00,
                        'net': 1700.00,
                        'transaction_count': 20
                    }
                ]
            },
            'budget_comparison': {
                'total_budgeted': 3000.00,
                'total_spent': 2100.00,
                'total_remaining': 900.00,
                'overall_percentage_used': 70.0,
                'categories': [
                    {
                        'category_id': 'cat-1',
                        'category_name': 'Groceries',
                        'budgeted': 600.00,
                        'spent': 650.00,
                        'remaining': -50.00,
                        'percentage_used': 108.3,
                        'over_budget': True
                    },
                    {
                        'category_id': 'cat-2',
                        'category_name': 'Dining Out',
                        'budgeted': 300.00,
                        'spent': 280.00,
                        'remaining': 20.00,
                        'percentage_used': 93.3,
                        'over_budget': False
                    }
                ]
            },
            'alerts': [
                {
                    'level': 'critical',
                    'category': 'Groceries',
                    'message': 'Over budget by $50.00 (8.3%)'
                }
            ]
        }

    def test_generate_html_report(self, sample_config, sample_report_data):
        """Test generating weekly HTML report."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        # Check basic structure
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

        # Check content is present
        assert 'Weekly Budget Report' in html or 'Budget Report' in html
        assert '2025-11-19' in html
        assert '2025-11-26' in html

    def test_report_contains_summary(self, sample_config, sample_report_data):
        """Test report contains summary section."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        # Check summary values are present
        assert '3,500' in html or '3500' in html  # Income
        assert '2,100' in html or '2100' in html  # Spent
        assert '25' in html  # Transaction count

    def test_report_contains_alerts(self, sample_config, sample_report_data):
        """Test report contains alerts section."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        # Check alert content
        assert 'Groceries' in html
        assert 'critical' in html.lower() or 'over budget' in html.lower()

    def test_report_contains_categories(self, sample_config, sample_report_data):
        """Test report contains category breakdown."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        assert 'Groceries' in html
        assert 'Dining Out' in html

    def test_report_contains_payees(self, sample_config, sample_report_data):
        """Test report contains payee breakdown."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        assert 'Whole Foods' in html
        assert 'Amazon' in html

    def test_report_without_alerts(self, sample_config, sample_report_data):
        """Test report generates correctly without alerts."""
        sample_report_data['alerts'] = []
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        # Should still generate valid HTML
        assert '<!DOCTYPE html>' in html

    def test_report_without_budget_comparison(self, sample_config, sample_report_data):
        """Test report generates correctly without budget comparison."""
        sample_report_data['budget_comparison'] = {}
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_html_report(sample_report_data)

        # Should still generate valid HTML
        assert '<!DOCTYPE html>' in html


class TestAnnualReportGeneration:
    """Tests for annual report generation."""

    @pytest.fixture
    def sample_annual_report_data(self, sample_month_budget):
        """Create sample annual report data."""
        return {
            'period': {
                'start_date': '2025-11-19',
                'end_date': '2025-11-26',
                'days': 7
            },
            'analysis': {
                'summary': {
                    'total_inflow': 3500.00,
                    'total_outflow': 2100.00,
                    'net': 1400.00,
                    'transaction_count': 25
                },
                'category_breakdown': [],
                'payee_breakdown': [],
                'notable_transactions': [],
                'account_breakdown': []
            },
            'budget_comparison': {
                'total_budgeted': 3000.00,
                'total_spent': 2100.00,
                'total_remaining': 900.00,
                'overall_percentage_used': 70.0,
                'categories': []
            },
            'alerts': [],
            'annual_budget': {
                'year': 2025,
                'total_budgeted': 60000.00,
                'total_spent': 55000.00,
                'total_remaining': 5000.00,
                'overall_percentage_used': 91.7,
                'categories': [
                    {
                        'category_id': 'cat-1',
                        'name': 'Groceries',
                        'annual_budgeted': 7200.00,
                        'annual_spent': 6800.00,
                        'remaining': 400.00,
                        'percentage_used': 94.4,
                        'monthly_breakdown': {
                            'Jan': {'budgeted': 600, 'activity': 580},
                            'Feb': {'budgeted': 600, 'activity': 620},
                            'Mar': {'budgeted': 600, 'activity': 590},
                            'Apr': {'budgeted': 600, 'activity': 610},
                            'May': {'budgeted': 600, 'activity': 600},
                            'Jun': {'budgeted': 600, 'activity': 570},
                            'Jul': {'budgeted': 600, 'activity': 620},
                            'Aug': {'budgeted': 600, 'activity': 640},
                            'Sep': {'budgeted': 600, 'activity': 580},
                            'Oct': {'budgeted': 600, 'activity': 690},
                            'Nov': {'budgeted': 600, 'activity': 700},
                            'Dec': {'budgeted': 600, 'activity': 0}
                        }
                    }
                ]
            },
            'ytd_spending': {
                'year': 2025,
                'days_elapsed': 330,
                'days_remaining': 35,
                'months_elapsed': 11,
                'total_income': 77000.00,
                'total_expenses': 55000.00,
                'net_savings': 22000.00,
                'savings_rate': 28.6,
                'avg_monthly_income': 7000.00,
                'avg_monthly_expenses': 5000.00,
                'categories': []
            },
            'projections': {
                'categories': [
                    {
                        'category': 'Groceries',
                        'annual_budget': 7200.00,
                        'ytd_spent': 6800.00,
                        'daily_rate': 20.60,
                        'projected_spending': 7519.00,
                        'projected_remaining': -319.00,
                        'pace_ratio': 1.04,
                        'pace_status': 'danger',
                        'expected_pct_elapsed': 90.4,
                        'actual_pct_used': 94.4
                    }
                ],
                'summary': {
                    'total_annual_budget': 60000.00,
                    'total_projected_spending': 58500.00,
                    'projected_surplus_deficit': 1500.00,
                    'days_elapsed': 330,
                    'days_remaining': 35,
                    'pct_year_elapsed': 90.4
                }
            }
        }

    def test_generate_annual_report(self, sample_config, sample_annual_report_data):
        """Test generating annual HTML report."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_annual_report(sample_annual_report_data)

        # Check basic structure
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

        # Check annual content is present
        assert '2025' in html
        assert 'Annual' in html

    def test_annual_report_contains_dashboard(self, sample_config, sample_annual_report_data):
        """Test annual report contains dashboard section."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_annual_report(sample_annual_report_data)

        # Check for dashboard elements
        assert 'Annual Budget' in html or 'YTD' in html

    def test_annual_report_contains_projections(self, sample_config, sample_annual_report_data):
        """Test annual report contains projections section."""
        generator = BudgetReportGenerator(sample_config['budget_report'])
        html = generator.generate_annual_report(sample_annual_report_data)

        # Check for projection elements
        assert 'Projection' in html or 'Projected' in html


class TestFormatters:
    """Tests for formatting helper methods."""

    def test_format_currency(self, sample_config):
        """Test currency formatting."""
        generator = BudgetReportGenerator(sample_config['budget_report'])

        assert generator._format_currency(1234.56) == '$1,234.56'
        assert generator._format_currency(1000, decimals=0) == '$1,000'
        assert generator._format_currency(0) == '$0.00'
        assert generator._format_currency(-500.50) == '$-500.50'

    def test_get_pace_status(self, sample_config):
        """Test pace status calculation."""
        generator = BudgetReportGenerator(sample_config['budget_report'])

        # 50% used at 50% through year = on track
        assert generator._get_pace_status(50, 183, 365) == 'ok'

        # 100% used at 50% through year = danger
        assert generator._get_pace_status(100, 183, 365) == 'danger'

        # 90% used at 90% through year = warning (close to limit)
        assert generator._get_pace_status(90, 329, 365) in ['ok', 'warning']

        # 20% used at 90% through year = under budget
        assert generator._get_pace_status(20, 329, 365) == 'under'


class TestLegacyHTMLGeneration:
    """Tests for legacy HTML generation (when templates not available)."""

    @pytest.fixture
    def generator_without_templates(self, sample_config, tmp_path):
        """Create generator without templates."""
        nonexistent_dir = tmp_path / "nonexistent"
        return BudgetReportGenerator(
            sample_config['budget_report'],
            template_dir=str(nonexistent_dir)
        )

    def test_legacy_generates_valid_html(self, generator_without_templates):
        """Test legacy generator produces valid HTML."""
        report_data = {
            'period': {'start_date': '2025-11-19', 'end_date': '2025-11-26', 'days': 7},
            'analysis': {
                'summary': {'total_inflow': 0, 'total_outflow': 0, 'net': 0, 'transaction_count': 0},
                'category_breakdown': [],
                'payee_breakdown': [],
                'notable_transactions': [],
                'account_breakdown': []
            },
            'budget_comparison': {},
            'alerts': []
        }

        html = generator_without_templates.generate_html_report(report_data)

        assert '<!DOCTYPE html>' in html
        assert '</html>' in html
        assert 'Weekly Budget Report' in html
