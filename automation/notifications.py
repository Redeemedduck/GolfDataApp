"""
Notification Manager for Automation Events.

Supports multiple notification channels:
- Slack (primary, requires webhook URL)
- Console/logging (always available)
- File logging (for audit trail)

Slack Setup Instructions:
1. Go to https://api.slack.com/apps
2. Create a new app (or use existing)
3. Enable "Incoming Webhooks"
4. Add a webhook to your workspace
5. Copy the webhook URL
6. Set SLACK_WEBHOOK_URL environment variable

Example webhook URL format:
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class NotificationLevel(Enum):
    """Severity level for notifications."""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None      # Override default channel
    slack_username: str = 'GolfDataApp Bot'
    slack_icon_emoji: str = ':golf:'

    log_to_console: bool = True
    log_to_file: bool = True
    log_file_path: Optional[str] = None

    min_level: NotificationLevel = NotificationLevel.INFO

    # Rate limiting to prevent spam
    max_notifications_per_hour: int = 20
    quiet_hours_start: Optional[int] = None  # Hour (0-23) to start quiet period
    quiet_hours_end: Optional[int] = None    # Hour (0-23) to end quiet period


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    channel: str
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class NotificationManager:
    """
    Manages notifications across multiple channels.

    Usage:
        # Initialize with environment variable
        notifier = NotificationManager()

        # Or with explicit config
        config = NotificationConfig(
            slack_webhook_url='https://hooks.slack.com/...',
        )
        notifier = NotificationManager(config)

        # Send notification
        await notifier.send("Import completed: 50 shots")

        # Send with level
        await notifier.send("Error importing session", level='error')

        # Structured notification
        await notifier.send_import_complete(
            session_id='12345',
            shots_imported=50,
            clubs=['Driver', '7 Iron'],
        )
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Initialize notification manager.

        Args:
            config: Notification configuration (uses environment if not provided)
        """
        self.config = config or self._config_from_env()

        # Set up log file
        if self.config.log_to_file:
            if self.config.log_file_path:
                self.log_path = Path(self.config.log_file_path)
            else:
                self.log_path = Path(__file__).parent.parent / 'logs' / 'notifications.jsonl'
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rate limiting state
        self._notification_times: List[datetime] = []

    def _config_from_env(self) -> NotificationConfig:
        """Create config from environment variables."""
        return NotificationConfig(
            slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
            slack_channel=os.getenv('SLACK_CHANNEL'),
            slack_username=os.getenv('SLACK_USERNAME', 'GolfDataApp Bot'),
            log_to_console=os.getenv('NOTIFICATION_CONSOLE', 'true').lower() == 'true',
            log_to_file=os.getenv('NOTIFICATION_LOG', 'true').lower() == 'true',
        )

    def _is_rate_limited(self) -> bool:
        """Check if we've hit the rate limit."""
        now = datetime.utcnow()
        hour_ago = now.replace(hour=now.hour - 1 if now.hour > 0 else 23)

        # Clean old timestamps
        self._notification_times = [
            t for t in self._notification_times
            if t > hour_ago
        ]

        return len(self._notification_times) >= self.config.max_notifications_per_hour

    def _is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours."""
        if self.config.quiet_hours_start is None or self.config.quiet_hours_end is None:
            return False

        current_hour = datetime.now().hour

        if self.config.quiet_hours_start <= self.config.quiet_hours_end:
            # Normal range (e.g., 22 to 8)
            return self.config.quiet_hours_start <= current_hour < self.config.quiet_hours_end
        else:
            # Overnight range (e.g., 22 to 8 = 22-24 and 0-8)
            return current_hour >= self.config.quiet_hours_start or current_hour < self.config.quiet_hours_end

    def _should_send(self, level: NotificationLevel) -> bool:
        """Determine if notification should be sent."""
        # Check level
        level_order = list(NotificationLevel)
        if level_order.index(level) < level_order.index(self.config.min_level):
            return False

        # Check rate limit (skip for critical)
        if level != NotificationLevel.CRITICAL and self._is_rate_limited():
            return False

        # Check quiet hours (skip for errors and critical)
        if level not in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]:
            if self._is_quiet_hours():
                return False

        return True

    async def send(
        self,
        message: str,
        level: str = 'info',
        title: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> List[NotificationResult]:
        """
        Send a notification to all configured channels.

        Args:
            message: The notification message
            level: Severity level (debug, info, warning, error, critical)
            title: Optional title/subject
            details: Optional additional details

        Returns:
            List of NotificationResult for each channel
        """
        try:
            notification_level = NotificationLevel(level)
        except ValueError:
            notification_level = NotificationLevel.INFO

        if not self._should_send(notification_level):
            return []

        results = []

        # Console logging
        if self.config.log_to_console:
            result = self._log_to_console(message, notification_level, title)
            results.append(result)

        # File logging
        if self.config.log_to_file:
            result = self._log_to_file(message, notification_level, title, details)
            results.append(result)

        # Slack
        if self.config.slack_webhook_url:
            result = await self._send_slack(message, notification_level, title, details)
            results.append(result)

        # Track for rate limiting
        self._notification_times.append(datetime.utcnow())

        return results

    def _log_to_console(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str],
    ) -> NotificationResult:
        """Log notification to console."""
        prefix = f"[{level.value.upper()}]"
        if title:
            print(f"{prefix} {title}: {message}")
        else:
            print(f"{prefix} {message}")

        return NotificationResult(success=True, channel='console')

    def _log_to_file(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str],
        details: Optional[Dict[str, Any]],
    ) -> NotificationResult:
        """Log notification to file."""
        try:
            entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': level.value,
                'title': title,
                'message': message,
                'details': details,
            }

            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')

            return NotificationResult(success=True, channel='file')
        except Exception as e:
            return NotificationResult(success=False, channel='file', error=str(e))

    async def _send_slack(
        self,
        message: str,
        level: NotificationLevel,
        title: Optional[str],
        details: Optional[Dict[str, Any]],
    ) -> NotificationResult:
        """Send notification to Slack."""
        if not HAS_REQUESTS:
            return NotificationResult(
                success=False,
                channel='slack',
                error='requests library not installed'
            )

        # Build Slack message
        emoji_map = {
            NotificationLevel.DEBUG: ':bug:',
            NotificationLevel.INFO: ':information_source:',
            NotificationLevel.WARNING: ':warning:',
            NotificationLevel.ERROR: ':x:',
            NotificationLevel.CRITICAL: ':rotating_light:',
        }

        blocks = []

        # Header with emoji
        header_text = f"{emoji_map.get(level, ':golf:')} "
        if title:
            header_text += f"*{title}*"
        else:
            header_text += f"*{level.value.upper()}*"

        blocks.append({
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': header_text}
        })

        # Message
        blocks.append({
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': message}
        })

        # Details as fields
        if details:
            fields = [
                {'type': 'mrkdwn', 'text': f"*{k}:* {v}"}
                for k, v in details.items()
            ]
            blocks.append({
                'type': 'section',
                'fields': fields[:10]  # Slack limit
            })

        # Timestamp
        blocks.append({
            'type': 'context',
            'elements': [
                {'type': 'mrkdwn', 'text': f"_Sent at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_"}
            ]
        })

        payload = {
            'username': self.config.slack_username,
            'icon_emoji': self.config.slack_icon_emoji,
            'blocks': blocks,
        }

        if self.config.slack_channel:
            payload['channel'] = self.config.slack_channel

        try:
            # Run synchronous request in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    self.config.slack_webhook_url,
                    json=payload,
                    timeout=10
                )
            )

            if response.status_code == 200:
                return NotificationResult(success=True, channel='slack')
            else:
                return NotificationResult(
                    success=False,
                    channel='slack',
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return NotificationResult(success=False, channel='slack', error=str(e))

    # Convenience methods for common notifications

    async def send_import_complete(
        self,
        session_id: str,
        shots_imported: int,
        clubs: Optional[List[str]] = None,
        duration_seconds: Optional[float] = None,
    ) -> List[NotificationResult]:
        """Send notification for completed import."""
        message = f"Imported session `{session_id}` with {shots_imported} shots"
        details = {'Session ID': session_id, 'Shots': shots_imported}

        if clubs:
            details['Clubs'] = ', '.join(clubs[:5])
            if len(clubs) > 5:
                details['Clubs'] += f' (+{len(clubs) - 5} more)'

        if duration_seconds:
            details['Duration'] = f"{duration_seconds:.1f}s"

        return await self.send(
            message=message,
            level='info',
            title='Import Complete',
            details=details,
        )

    async def send_backfill_progress(
        self,
        sessions_processed: int,
        sessions_total: int,
        shots_imported: int,
    ) -> List[NotificationResult]:
        """Send notification for backfill progress."""
        pct = (sessions_processed / sessions_total * 100) if sessions_total > 0 else 0
        message = f"Backfill progress: {sessions_processed}/{sessions_total} sessions ({pct:.0f}%)"

        return await self.send(
            message=message,
            level='info',
            title='Backfill Progress',
            details={
                'Processed': f"{sessions_processed}/{sessions_total}",
                'Total Shots': shots_imported,
            },
        )

    async def send_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[NotificationResult]:
        """Send error notification."""
        return await self.send(
            message=error_message,
            level='error',
            title='Automation Error',
            details=context,
        )

    async def send_daily_summary(
        self,
        sessions_imported: int,
        total_shots: int,
        errors: int = 0,
    ) -> List[NotificationResult]:
        """Send daily summary notification."""
        message = f"Daily summary: {sessions_imported} sessions, {total_shots} shots"
        if errors > 0:
            message += f", {errors} errors"

        return await self.send(
            message=message,
            level='info',
            title='Daily Summary',
            details={
                'Sessions': sessions_imported,
                'Shots': total_shots,
                'Errors': errors,
            },
        )


# Singleton instance
_notifier: Optional[NotificationManager] = None


def get_notifier() -> NotificationManager:
    """Get the singleton NotificationManager instance."""
    global _notifier
    if _notifier is None:
        _notifier = NotificationManager()
    return _notifier


def configure_notifier(config: NotificationConfig) -> NotificationManager:
    """Configure and get the notification manager."""
    global _notifier
    _notifier = NotificationManager(config)
    return _notifier


# Quick send function
async def notify(message: str, level: str = 'info') -> List[NotificationResult]:
    """Quick function to send a notification."""
    return await get_notifier().send(message, level=level)
