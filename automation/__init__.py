"""
Automation module for GolfDataApp scraper.

This module provides automated session discovery, import, and management
for Uneekor golf data using Playwright browser automation.

Components:
- credential_manager: Secure credential and cookie handling
- rate_limiter: Conservative request throttling
- browser_client: Playwright browser lifecycle management
- uneekor_portal: Uneekor-specific navigation and extraction
- session_discovery: Session discovery and deduplication
- naming_conventions: Club and session name standardization
- backfill_runner: Historical data import with checkpointing
- notifications: Slack notification support
"""

from .credential_manager import CredentialManager
from .rate_limiter import RateLimiter, get_conservative_limiter, get_backfill_limiter
from .naming_conventions import (
    ClubNameNormalizer,
    SessionNamer,
    AutoTagger,
    normalize_club,
    normalize_clubs,
)
from .session_discovery import SessionDiscovery, get_discovery
from .notifications import NotificationManager, get_notifier, notify

__all__ = [
    # Credential management
    'CredentialManager',

    # Rate limiting
    'RateLimiter',
    'get_conservative_limiter',
    'get_backfill_limiter',

    # Naming conventions
    'ClubNameNormalizer',
    'SessionNamer',
    'AutoTagger',
    'normalize_club',
    'normalize_clubs',

    # Session discovery
    'SessionDiscovery',
    'get_discovery',

    # Notifications
    'NotificationManager',
    'get_notifier',
    'notify',
]

__version__ = '1.0.0'
