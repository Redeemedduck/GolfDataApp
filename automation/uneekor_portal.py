"""
Uneekor Portal Navigator.

Handles navigation and data extraction from the Uneekor web portal:
- Session list retrieval
- Report URL extraction
- Session metadata parsing

This module is Uneekor-specific and may need updates if the portal changes.
"""

import re
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, parse_qs

from .browser_client import PlaywrightClient, BrowserConfig
from .rate_limiter import RateLimiter, get_conservative_limiter
from .naming_conventions import normalize_club


@dataclass
class SessionInfo:
    """
    Information about a session discovered from Uneekor portal.

    Attributes:
        report_id: Unique report identifier from URL
        api_key: API access key for data retrieval
        portal_name: Display name shown in Uneekor UI
        session_date: Date of the session
        shot_count: Number of shots (if available from portal)
        clubs_used: List of clubs detected in portal
        source_url: Full report URL for API access
        discovered_at: When this session was discovered
    """
    report_id: str
    api_key: str
    portal_name: Optional[str] = None
    session_date: Optional[datetime] = None
    shot_count: Optional[int] = None
    clubs_used: List[str] = field(default_factory=list)
    source_url: str = ''
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def import_url(self) -> str:
        """Get the URL needed for the API scraper."""
        return f"https://my.uneekor.com/report?id={self.report_id}&key={self.api_key}"


class UneekorPortalNavigator:
    """
    Navigates the Uneekor portal to discover and extract session data.

    This class handles the specifics of Uneekor's portal UI:
    - Finding and clicking session links
    - Extracting report IDs and API keys
    - Parsing session metadata

    Usage:
        async with UneekorPortalNavigator() as portal:
            # Login first
            await portal.login()

            # Get all sessions
            sessions = await portal.get_all_sessions()

            # Get specific session details
            session = await portal.get_session_details(report_id)

    Note: The Uneekor portal uses React and may load dynamically.
    Selectors may need updating if Uneekor changes their UI.
    """

    # Known Uneekor portal URLs
    LOGIN_URL = 'https://my.uneekor.com/login'
    REPORTS_URL = 'https://my.uneekor.com/reports'
    REPORT_URL_PATTERN = r'https://my\.uneekor\.com/report\?id=(\d+)&key=([^&]+)'

    # Alternative URL patterns (Uneekor has used different URL structures)
    ALT_REPORT_URL_PATTERN = r'https://my\.uneekor\.com/power-u-report\?id=(\d+)&key=([^&]+)'

    # CSS Selectors for portal elements (may need updating if UI changes)
    SELECTORS = {
        # Login page
        'email_input': 'input[type="email"], input[name="email"], #email, input[placeholder*="email" i]',
        'password_input': 'input[type="password"], input[name="password"], #password',
        'login_button': 'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign")',

        # Reports page
        'session_list': '.reports-list, .session-list, [class*="report"], [class*="session"]',
        'session_item': '.report-item, .session-item, [class*="report-card"], a[href*="report"]',
        'session_link': 'a[href*="report?id="], a[href*="power-u-report?id="]',
        'session_date': '.date, .session-date, [class*="date"], time',
        'shot_count': '.shot-count, .shots, [class*="shot"]',
        'club_info': '.club, .clubs, [class*="club"]',

        # Pagination (if exists)
        'next_page': 'button:has-text("Next"), a:has-text("Next"), [class*="next"]',
        'page_indicator': '.pagination, [class*="page"]',
    }

    def __init__(
        self,
        browser_client: Optional[PlaywrightClient] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize portal navigator.

        Args:
            browser_client: Playwright client to use (creates one if not provided)
            rate_limiter: Rate limiter for requests
        """
        self._own_client = browser_client is None
        self._client = browser_client
        self._rate_limiter = rate_limiter or get_conservative_limiter()

    async def __aenter__(self) -> 'UneekorPortalNavigator':
        """Async context manager entry."""
        if self._own_client:
            self._client = PlaywrightClient()
            await self._client.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._own_client and self._client:
            await self._client.stop()

    @property
    def client(self) -> PlaywrightClient:
        """Get the browser client."""
        if not self._client:
            raise RuntimeError("Navigator not initialized. Use 'async with' or call start().")
        return self._client

    async def login(self, force_fresh: bool = False) -> bool:
        """
        Log in to Uneekor portal.

        Args:
            force_fresh: Force fresh login even if cookies exist

        Returns:
            True if login successful
        """
        return await self.client.login(force_fresh=force_fresh)

    async def get_all_sessions(
        self,
        max_sessions: Optional[int] = None,
        since_date: Optional[datetime] = None,
    ) -> List[SessionInfo]:
        """
        Get all sessions from the portal.

        Args:
            max_sessions: Maximum number of sessions to retrieve
            since_date: Only get sessions after this date

        Returns:
            List of SessionInfo objects
        """
        if not self.client.is_logged_in:
            raise RuntimeError("Must be logged in to get sessions")

        sessions = []
        page = self.client.page

        # Navigate to reports page
        await self._rate_limiter.wait_async('navigate_reports')
        await page.goto(self.REPORTS_URL)
        await page.wait_for_load_state('networkidle')

        # Try to find session links
        session_links = await self._find_session_links()

        for link_info in session_links:
            if max_sessions and len(sessions) >= max_sessions:
                break

            try:
                session = await self._parse_session_from_link(link_info)
                if session:
                    # Apply date filter if specified
                    if since_date and session.session_date:
                        if session.session_date < since_date:
                            continue
                    sessions.append(session)
            except Exception as e:
                print(f"Error parsing session: {e}")
                continue

        return sessions

    async def _find_session_links(self) -> List[Dict[str, Any]]:
        """
        Find all session links on the current page.

        Returns:
            List of dicts with href and text for each link
        """
        page = self.client.page
        links = []

        # Try multiple selectors
        for selector in ['a[href*="report?id="]', 'a[href*="power-u-report?id="]']:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    href = await element.get_attribute('href')
                    text = await element.inner_text()
                    if href:
                        links.append({
                            'href': href,
                            'text': text,
                            'element': element,
                        })
            except Exception:
                continue

        # Also try to find links via JavaScript (for React-rendered content)
        if not links:
            try:
                js_links = await page.evaluate('''
                    () => {
                        const links = [];
                        document.querySelectorAll('a').forEach(a => {
                            if (a.href && a.href.includes('report') && a.href.includes('id=')) {
                                links.push({
                                    href: a.href,
                                    text: a.innerText || a.textContent || '',
                                });
                            }
                        });
                        return links;
                    }
                ''')
                links.extend(js_links)
            except Exception:
                pass

        return links

    async def _parse_session_from_link(self, link_info: Dict[str, Any]) -> Optional[SessionInfo]:
        """
        Parse session information from a link.

        Args:
            link_info: Dict with href and text

        Returns:
            SessionInfo or None if parsing failed
        """
        href = link_info.get('href', '')
        text = link_info.get('text', '')

        # Extract report_id and api_key from URL
        report_id = None
        api_key = None

        for pattern in [self.REPORT_URL_PATTERN, self.ALT_REPORT_URL_PATTERN]:
            match = re.search(pattern, href)
            if match:
                report_id = match.group(1)
                api_key = match.group(2)
                break

        if not report_id or not api_key:
            # Try parsing query string
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            report_id = params.get('id', [None])[0]
            api_key = params.get('key', [None])[0]

        if not report_id or not api_key:
            return None

        # Parse session date from text or nearby elements
        session_date = self._parse_date_from_text(text)

        # Parse club info if available
        clubs_used = self._parse_clubs_from_text(text)

        return SessionInfo(
            report_id=report_id,
            api_key=api_key,
            portal_name=text.strip() if text else None,
            session_date=session_date,
            clubs_used=clubs_used,
            source_url=href,
            raw_data=link_info,
        )

    def _parse_date_from_text(self, text: str) -> Optional[datetime]:
        """
        Attempt to parse a date from text.

        Args:
            text: Text that may contain a date

        Returns:
            datetime or None
        """
        if not text:
            return None

        # Common date patterns
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # Month DD, YYYY
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # DD Month YYYY
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Try common formats
                    date_str = match.group(0)
                    for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    continue

        return None

    def _parse_clubs_from_text(self, text: str) -> List[str]:
        """
        Attempt to parse club names from text.

        Args:
            text: Text that may contain club names

        Returns:
            List of normalized club names
        """
        if not text:
            return []

        # Look for patterns like "(5) Driver" or "Driver - 5 shots"
        clubs = []

        # Pattern: (count) club_name
        count_club_pattern = r'\((\d+)\)\s*([A-Za-z0-9\s]+?)(?:\s*\(|$|,)'
        for match in re.finditer(count_club_pattern, text):
            club_name = match.group(2).strip()
            if club_name:
                clubs.append(normalize_club(club_name))

        # Pattern: club_name - count shots
        club_count_pattern = r'([A-Za-z0-9\s]+?)\s*[-:]\s*(\d+)\s*(?:shots?|hits?)'
        for match in re.finditer(club_count_pattern, text, re.IGNORECASE):
            club_name = match.group(1).strip()
            if club_name:
                clubs.append(normalize_club(club_name))

        return list(set(clubs))  # Remove duplicates

    async def get_session_details(self, report_id: str) -> Optional[SessionInfo]:
        """
        Get detailed information about a specific session.

        This navigates to the session page and extracts more detailed data.

        Args:
            report_id: The report ID to get details for

        Returns:
            SessionInfo with full details, or None if not found
        """
        # First find the session in the list
        sessions = await self.get_all_sessions()

        for session in sessions:
            if session.report_id == report_id:
                return session

        return None

    async def extract_report_url(self, session: SessionInfo) -> str:
        """
        Get the full report URL for API access.

        Args:
            session: SessionInfo object

        Returns:
            Full URL for the golf_scraper API
        """
        return session.import_url

    async def check_for_new_sessions(
        self,
        known_report_ids: List[str],
        max_check: int = 20,
    ) -> List[SessionInfo]:
        """
        Check for sessions not in the known list.

        Efficient check that stops early when hitting known sessions.

        Args:
            known_report_ids: List of report IDs already imported
            max_check: Maximum sessions to check before stopping

        Returns:
            List of new SessionInfo objects
        """
        new_sessions = []
        known_set = set(known_report_ids)

        sessions = await self.get_all_sessions(max_sessions=max_check)

        for session in sessions:
            if session.report_id not in known_set:
                new_sessions.append(session)
            else:
                # Hit a known session - likely no more new ones
                # But continue checking in case of out-of-order sessions
                pass

        return new_sessions


async def discover_sessions(
    headless: bool = True,
    max_sessions: Optional[int] = None,
    since_date: Optional[datetime] = None,
) -> List[SessionInfo]:
    """
    Convenience function to discover sessions.

    Args:
        headless: Run browser in headless mode
        max_sessions: Maximum sessions to retrieve
        since_date: Only get sessions after this date

    Returns:
        List of discovered sessions
    """
    config = BrowserConfig(headless=headless)
    client = PlaywrightClient(config=config)

    async with client:
        await client.login()

        navigator = UneekorPortalNavigator(browser_client=client)
        sessions = await navigator.get_all_sessions(
            max_sessions=max_sessions,
            since_date=since_date,
        )

        return sessions


if __name__ == '__main__':
    # Test the portal navigator
    async def test():
        print("Testing UneekorPortalNavigator...")
        sessions = await discover_sessions(headless=False, max_sessions=5)
        for session in sessions:
            print(f"  - {session.report_id}: {session.portal_name} ({session.session_date})")

    asyncio.run(test())
