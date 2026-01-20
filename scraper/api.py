"""
Uneekor API client helpers.
"""
from typing import Any
import requests

from scraper.config import API_BASE_URL


def fetch_report_sessions(report_id: str, key: str) -> list[dict[str, Any]]:
    """Fetch report sessions from the Uneekor API."""
    api_url = f"{API_BASE_URL}/{report_id}/{key}"

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        sessions_data = response.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Failed to fetch data from Uneekor API: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON response from API: {exc}") from exc

    if not sessions_data or not isinstance(sessions_data, list):
        raise RuntimeError("No session data found in API response")

    return sessions_data


def fetch_shot_images(report_id: str, key: str, session_id: str, shot_id: str) -> list[dict[str, Any]]:
    """Fetch shot image metadata from the Uneekor API."""
    image_api_url = f"{API_BASE_URL}/shotimage/{report_id}/{key}/{session_id}/{shot_id}"
    response = requests.get(image_api_url, timeout=30)

    if response.status_code != 200:
        return []

    try:
        return response.json()
    except ValueError:
        return []
