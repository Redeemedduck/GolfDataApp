"""
Logging Configuration for GolfDataApp.

Provides structured logging with file rotation and console output.

Usage:
    from utils.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Starting import")
    logger.warning("Rate limit approaching")
    logger.error("Import failed", exc_info=True)
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


# Default log directory
LOG_DIR = Path(__file__).parent.parent / 'logs'


def setup_logging(
    level: str = 'INFO',
    log_dir: Optional[Path] = None,
    console: bool = True,
    file_logging: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure the root logger for GolfDataApp.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: ./logs/)
        console: Enable console logging
        file_logging: Enable file logging
        max_bytes: Max size per log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured root logger
    """
    log_dir = log_dir or LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create root logger
    root_logger = logging.getLogger('golfdata')
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers = []

    # Formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if file_logging:
        log_file = log_dir / 'golfdata.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # Capture all levels to file
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Usually __name__ of the calling module

    Returns:
        Logger instance
    """
    # Ensure parent logger exists
    if not logging.getLogger('golfdata').handlers:
        setup_logging()

    # Return a child logger
    if name.startswith('golfdata.'):
        return logging.getLogger(name)
    return logging.getLogger(f'golfdata.{name}')


# Convenience functions for quick logging without setup
def log_info(msg: str, *args):
    """Quick info logging."""
    get_logger('app').info(msg, *args)


def log_warning(msg: str, *args):
    """Quick warning logging."""
    get_logger('app').warning(msg, *args)


def log_error(msg: str, *args, exc_info: bool = False):
    """Quick error logging."""
    get_logger('app').error(msg, *args, exc_info=exc_info)


# Initialize on import if env var is set
if os.getenv('GOLFDATA_LOGGING') == '1':
    setup_logging()
