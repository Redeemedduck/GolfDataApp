"""
Custom Exceptions for GolfDataApp.

Provides a hierarchy of exceptions for clear error handling:
- GolfDataAppError: Base exception for all app errors
- DatabaseError: Database operation failures
- ModelNotTrainedError: ML model not available
- ImportError: Session/shot import failures
- ValidationError: Data validation failures
- ConfigurationError: Configuration/setup issues

Usage:
    from exceptions import DatabaseError, ValidationError

    if not validate_shot(data):
        raise ValidationError("Invalid shot data: missing carry distance")

    try:
        save_shot(data)
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
"""


class GolfDataAppError(Exception):
    """Base exception for all GolfDataApp errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class DatabaseError(GolfDataAppError):
    """Exception for database operation failures."""

    def __init__(self, message: str, operation: str = None, table: str = None):
        details = {}
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        super().__init__(message, details)


class ModelNotTrainedError(GolfDataAppError):
    """Exception when an ML model is required but not trained/loaded."""

    def __init__(self, model_name: str, message: str = None):
        msg = message or f"Model '{model_name}' is not trained or loaded"
        super().__init__(msg, {'model': model_name})


class ImportError(GolfDataAppError):
    """Exception for session/shot import failures."""

    def __init__(self, message: str, session_id: str = None, source: str = None):
        details = {}
        if session_id:
            details['session_id'] = session_id
        if source:
            details['source'] = source
        super().__init__(message, details)


class ValidationError(GolfDataAppError):
    """Exception for data validation failures."""

    def __init__(self, message: str, field: str = None, value=None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = repr(value)
        super().__init__(message, details)


class ConfigurationError(GolfDataAppError):
    """Exception for configuration/setup issues."""

    def __init__(self, message: str, config_key: str = None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        super().__init__(message, details)


class RateLimitError(GolfDataAppError):
    """Exception when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: float = None):
        details = {}
        if retry_after:
            details['retry_after_seconds'] = retry_after
        super().__init__(message, details)


class AuthenticationError(GolfDataAppError):
    """Exception for authentication failures."""

    def __init__(self, message: str, provider: str = None):
        details = {}
        if provider:
            details['provider'] = provider
        super().__init__(message, details)
