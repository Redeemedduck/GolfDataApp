"""Shared date parsing utilities."""
from datetime import date, datetime
from typing import Optional


def parse_session_date(value) -> Optional[date]:
    """Parse a session date from ISO datetime/date strings with fallbacks."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.fromisoformat(raw.split("T", 1)[0]).date()
            except (ValueError, TypeError):
                return None


def format_session_date(value, fmt: str = "short") -> str:
    """Format a session date for display.

    Args:
        value: Date value to format.
        fmt: "short" for "Jan 28", "long" for "Jan 28, 2026".
    """
    parsed = parse_session_date(value)
    if parsed is None:
        return "No date"
    if fmt == "long":
        return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"
    return f"{parsed.strftime('%b')} {parsed.day}"
