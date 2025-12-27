"""
Base Service Class

Provides common functionality for all services including:
- Structured logging with context
- Error handling patterns
- Performance tracking
- Configuration management
"""

import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager


class BaseService:
    """
    Base class for all service classes.

    Provides consistent logging, error handling, and performance tracking
    across all services in the application.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base service.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = self._setup_logger()
        self._performance_metrics = {}

    def _setup_logger(self) -> logging.Logger:
        """
        Set up structured logger for this service.

        Returns:
            Configured logger instance
        """
        # Get logger name from class name
        logger_name = f"golf_data.{self.__class__.__name__}"
        logger = logging.getLogger(logger_name)

        # Set level from config or default to INFO
        level = self.config.get('log_level', 'INFO')
        logger.setLevel(getattr(logging, level))

        # Add handler if not already present
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _log_info(self, message: str, **context):
        """
        Log info message with optional context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"
        self.logger.info(message)

    def _log_warning(self, message: str, **context):
        """
        Log warning message with optional context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"
        self.logger.warning(message)

    def _log_error(self, message: str, error: Optional[Exception] = None, **context):
        """
        Log error message with optional exception and context.

        Args:
            message: Log message
            error: Exception object if available
            **context: Additional context key-value pairs
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"

        if error:
            self.logger.error(f"{message} | error={str(error)}", exc_info=True)
        else:
            self.logger.error(message)

    def _log_debug(self, message: str, **context):
        """
        Log debug message with optional context.

        Args:
            message: Log message
            **context: Additional context key-value pairs
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"
        self.logger.debug(message)

    def _handle_error(
        self,
        error: Exception,
        context: str,
        raise_error: bool = True
    ) -> Optional[Exception]:
        """
        Standard error handling pattern.

        Args:
            error: Exception that occurred
            context: Description of what was being done
            raise_error: Whether to re-raise the error

        Returns:
            The error if not re-raised, None otherwise

        Raises:
            The original exception if raise_error is True
        """
        error_msg = f"Error in {context}"
        self._log_error(error_msg, error, context=context)

        if raise_error:
            raise error
        return error

    @contextmanager
    def _track_performance(self, operation: str):
        """
        Context manager to track operation performance.

        Usage:
            with self._track_performance("import_shots"):
                # ... do work ...
                pass

        Args:
            operation: Name of the operation being tracked
        """
        start_time = time.time()
        self._log_debug(f"Starting {operation}")

        try:
            yield
        finally:
            duration = time.time() - start_time

            # Store metric
            if operation not in self._performance_metrics:
                self._performance_metrics[operation] = []
            self._performance_metrics[operation].append(duration)

            # Log completion
            self._log_info(
                f"Completed {operation}",
                duration_seconds=round(duration, 3)
            )

    def get_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Get performance metrics summary.

        Returns:
            Dictionary with operation names and their statistics
        """
        metrics = {}
        for operation, durations in self._performance_metrics.items():
            metrics[operation] = {
                'count': len(durations),
                'total_seconds': round(sum(durations), 3),
                'avg_seconds': round(sum(durations) / len(durations), 3),
                'min_seconds': round(min(durations), 3),
                'max_seconds': round(max(durations), 3)
            }
        return metrics

    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self._performance_metrics = {}
        self._log_debug("Performance metrics reset")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def update_config(self, **kwargs):
        """
        Update configuration.

        Args:
            **kwargs: Configuration key-value pairs to update
        """
        self.config.update(kwargs)
        self._log_debug("Configuration updated", **kwargs)

    def _validate_required_fields(self, data: Dict, required_fields: list) -> None:
        """
        Validate that required fields are present in data.

        Args:
            data: Dictionary to validate
            required_fields: List of required field names

        Raises:
            ValueError: If any required field is missing
        """
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string
        """
        return datetime.utcnow().isoformat()

    def __repr__(self) -> str:
        """String representation of service."""
        return f"<{self.__class__.__name__}>"
