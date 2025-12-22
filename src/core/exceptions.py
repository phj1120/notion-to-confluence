"""Custom exceptions for the Notion to Confluence migration tool."""


class MigrationError(Exception):
    """Base exception for all migration errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotionAPIError(MigrationError):
    """Raised when Notion API calls fail."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message, details)
        self.status_code = status_code


class ConfluenceAPIError(MigrationError):
    """Raised when Confluence API calls fail."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message, details)
        self.status_code = status_code


class ConfigurationError(MigrationError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(MigrationError):
    """Raised when input validation fails."""
    pass


class ConversionError(MigrationError):
    """Raised when content conversion fails."""

    def __init__(self, message: str, block_type: str = None, details: dict = None):
        super().__init__(message, details)
        self.block_type = block_type


class CSVError(MigrationError):
    """Raised when CSV file operations fail."""
    pass
