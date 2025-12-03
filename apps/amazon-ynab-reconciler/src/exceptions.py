"""
Custom exceptions for amazon-ynab-reconciler.

Provides typed exceptions for specific error scenarios,
improving error handling and debugging.
"""


class ReconcilerException(Exception):
    """Base exception for all reconciler errors."""
    pass


# Configuration Errors
class ConfigurationError(ReconcilerException):
    """Raised when configuration is invalid or missing."""
    pass


class CredentialError(ReconcilerException):
    """Raised when credentials are invalid or missing."""
    pass


# Amazon Service Errors
class AmazonServiceError(ReconcilerException):
    """Raised when Amazon operations fail."""
    pass


class AmazonLoginError(AmazonServiceError):
    """Raised when Amazon login fails."""
    pass


class AmazonScrapingError(AmazonServiceError):
    """Raised when scraping Amazon data fails."""
    pass


class AmazonCSVError(AmazonServiceError):
    """Raised when CSV import fails."""
    pass


# YNAB Service Errors
class YNABServiceError(ReconcilerException):
    """Raised when YNAB API operations fail."""
    pass


class YNABAuthenticationError(YNABServiceError):
    """Raised when YNAB authentication fails."""
    pass


class YNABRateLimitError(YNABServiceError):
    """Raised when YNAB rate limit is exceeded."""
    pass


class YNABTransactionError(YNABServiceError):
    """Raised when transaction operations fail."""
    pass


class YNABBudgetNotFoundError(YNABServiceError):
    """Raised when specified budget cannot be found."""
    pass


class YNABAccountNotFoundError(YNABServiceError):
    """Raised when specified account cannot be found."""
    pass


# Gmail Service Errors
class GmailServiceError(ReconcilerException):
    """Raised when Gmail operations fail."""
    pass


class GmailAuthenticationError(GmailServiceError):
    """Raised when Gmail authentication fails."""
    pass


class GmailTokenExpiredError(GmailServiceError):
    """Raised when Gmail OAuth token has expired."""
    pass


# Matching Errors
class MatchingError(ReconcilerException):
    """Raised when transaction matching fails."""
    pass


class NoMatchesFoundError(MatchingError):
    """Raised when no matches could be found for any transactions."""
    pass


# Validation Errors
class ValidationError(ReconcilerException):
    """Raised when data validation fails."""
    pass


class CSVValidationError(ValidationError):
    """Raised when CSV data is invalid."""
    pass


class DateValidationError(ValidationError):
    """Raised when date parsing or validation fails."""
    pass


class AmountValidationError(ValidationError):
    """Raised when amount parsing or validation fails."""
    pass


# State Management Errors
class StateError(ReconcilerException):
    """Raised when state management operations fail."""
    pass


class StateFileCorruptedError(StateError):
    """Raised when state file is corrupted or unreadable."""
    pass


# Report Generation Errors
class ReportError(ReconcilerException):
    """Raised when report generation fails."""
    pass


class EmailSendError(ReportError):
    """Raised when sending email report fails."""
    pass
