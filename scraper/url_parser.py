"""
URL parsing helpers for Uneekor report links.
"""
import re


def extract_url_params(url: str) -> tuple[str | None, str | None]:
    """Extract report_id and key from Uneekor URL."""
    try:
        report_id_match = re.search(r"id=(\d+)", url)
        key_match = re.search(r"key=([^&]+)", url)

        if report_id_match and key_match:
            return report_id_match.group(1), key_match.group(1)
        return None, None
    except Exception as exc:
        print(f"Error parsing URL: {exc}")
        return None, None
