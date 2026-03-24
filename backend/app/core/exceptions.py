class AppException(Exception):
    """Base application exception for domain-level errors."""


class DomainValidationError(AppException):
    """Raised when business validation fails."""
