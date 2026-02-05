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
    REPORTS_URL = 'https://my.uneekor.com/report'  # Note: singular 'report', not 'reports'
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

        Iterates through all pagination pages to collect complete session list.

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
        page_num = 1
        seen_report_ids = set()  # Track to avoid duplicates across pages

        # Navigate to reports page
        await self._rate_limiter.wait_async('navigate_reports')
        await page.goto(self.REPORTS_URL)
        await page.wait_for_load_state('networkidle')

        while True:
            print(f"Scanning page {page_num}...")

            # Find session links on current page
            session_links = await self._find_session_links()

            if not session_links:
                print(f"No sessions found on page {page_num}, stopping pagination")
                break

            sessions_on_page = 0
            for link_info in session_links:
                if max_sessions and len(sessions) >= max_sessions:
                    print(f"Reached max_sessions limit ({max_sessions})")
                    return sessions

                try:
                    session = await self._parse_session_from_link(link_info)
                    if session:
                        # Skip duplicates (same session can appear in multiple sections)
                        if session.report_id in seen_report_ids:
                            continue
                        seen_report_ids.add(session.report_id)

                        # Apply date filter if specified
                        if since_date and session.session_date:
                            if session.session_date < since_date:
                                continue
                        sessions.append(session)
                        sessions_on_page += 1
                except Exception as e:
                    print(f"Error parsing session: {e}")
                    continue

            print(f"Found {sessions_on_page} sessions on page {page_num} (total: {len(sessions)})")

            # Try to navigate to next page
            next_page_num = page_num + 1
            next_btn = await self._find_pagination_button(next_page_num)

            if not next_btn:
                print(f"No page {next_page_num} button found, finished at page {page_num}")
                break

            # Click next page and wait for content to load
            try:
                await self._rate_limiter.wait_async('navigate_page')
                await next_btn.click()
                await page.wait_for_load_state('networkidle')
                # Brief pause for any client-side rendering
                await asyncio.sleep(0.5)
                page_num = next_page_num
            except Exception as e:
                print(f"Error navigating to page {next_page_num}: {e}")
                break

        print(f"Pagination complete. Total sessions found: {len(sessions)}")
        return sessions

    async def _find_pagination_button(self, page_num: int):
        """
        Find a pagination button for the given page number.

        Args:
            page_num: Page number to find button for

        Returns:
            Element handle or None if not found
        """
        page = self.client.page

        # Try various pagination button selectors
        selectors = [
            f'button:text-is("{page_num}")',
            f'a:text-is("{page_num}")',
            f'[class*="pagination"] button:text-is("{page_num}")',
            f'[class*="pagination"] a:text-is("{page_num}")',
            f'[class*="page"] button:text-is("{page_num}")',
            f'[class*="page"] a:text-is("{page_num}")',
        ]

        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    return btn
            except Exception:
                continue

        return None

    async def _find_session_links(self) -> List[Dict[str, Any]]:
        """
        Find all session links on the current page with date context.

        The listing page organizes sessions by date. This method walks the DOM
        to associate each session link with its date header, enabling accurate
        session date extraction.

        Returns:
            List of dicts with href, text, and dateContext for each link
        """
        page = self.client.page
        links = []

        # Try multiple selectors first (quick approach)
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
                            'dateContext': None,  # Will be populated by DOM walker
                        })
            except Exception:
                continue

        # Use JavaScript DOM walker to find links with date context
        # This handles React-rendered content and extracts date associations
        try:
            js_links = await page.evaluate('''
                () => {
                    const results = [];
                    let currentDate = null;

                    // Date pattern: "January 15, 2026" or similar
                    const datePattern = /^(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+\\d{4}$/i;

                    // Alternative patterns
                    const altDatePatterns = [
                        /^\\d{1,2}\\/\\d{1,2}\\/\\d{4}$/,  // MM/DD/YYYY
                        /^\\d{4}-\\d{2}-\\d{2}$/,          // YYYY-MM-DD
                        /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\\s+\\d{1,2},?\\s+\\d{4}$/i  // Short month
                    ];

                    // Walk through all elements in document order
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        null,
                        false
                    );

                    while (walker.nextNode()) {
                        const node = walker.currentNode;
                        const text = (node.textContent || '').trim();

                        // Skip if text is too long (not a date header)
                        if (text.length > 50) continue;

                        // Check for date headers
                        if (datePattern.test(text)) {
                            // Check if this is a heading or date-like container
                            const tagName = node.tagName.toUpperCase();
                            if (['H1','H2','H3','H4','H5','H6','DIV','SPAN','P','TD','TH'].includes(tagName)) {
                                // Make sure it's not inside a link
                                if (!node.closest('a')) {
                                    currentDate = text;
                                }
                            }
                        } else {
                            // Check alternative date patterns
                            for (const pattern of altDatePatterns) {
                                if (pattern.test(text) && !node.closest('a')) {
                                    currentDate = text;
                                    break;
                                }
                            }
                        }

                        // Check for session links
                        if (node.tagName === 'A') {
                            const href = node.href || '';
                            if (href.includes('report') && href.includes('id=')) {
                                results.push({
                                    href: href,
                                    text: (node.innerText || node.textContent || '').trim(),
                                    dateContext: currentDate,
                                    parentClass: node.parentElement?.className || ''
                                });
                            }
                        }
                    }
                    return results;
                }
            ''')

            # Merge with existing links or use JS results
            if js_links:
                if links:
                    # Update existing links with date context from JS walker
                    # Use report ID for matching since CSS selectors return relative URLs
                    # while JavaScript node.href returns absolute URLs
                    def extract_report_id(href):
                        """Extract report ID from URL for reliable matching."""
                        if not href:
                            return None
                        # Match ?id=XXX or &id=XXX pattern
                        match = re.search(r'[?&]id=(\d+)', href)
                        return match.group(1) if match else None

                    js_id_map = {extract_report_id(link['href']): link for link in js_links}
                    for link in links:
                        report_id = extract_report_id(link['href'])
                        if report_id and report_id in js_id_map:
                            link['dateContext'] = js_id_map[report_id].get('dateContext')
                else:
                    links = js_links

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

        # Parse session date - prefer dateContext from DOM walker (listing page)
        # This is more reliable than parsing the link text
        session_date = None
        date_source = None

        date_context = link_info.get('dateContext')
        if date_context:
            session_date = self._parse_date_from_text(date_context)
            if session_date:
                date_source = 'listing_page'

        # Fallback: try to parse from link text
        if not session_date:
            session_date = self._parse_date_from_text(text)
            if session_date:
                date_source = 'link_text'

        # Parse club info if available
        clubs_used = self._parse_clubs_from_text(text)

        session = SessionInfo(
            report_id=report_id,
            api_key=api_key,
            portal_name=text.strip() if text else None,
            session_date=session_date,
            clubs_used=clubs_used,
            source_url=href,
            raw_data=link_info,
        )
        # Store date source for tracking
        session.raw_data['date_source'] = date_source

        return session

    def _parse_date_from_text(self, text: str) -> Optional[datetime]:
        """
        Attempt to parse a date from text.

        Supports multiple date formats found in Uneekor portal:
        - YYYY.MM.DD (report page header format - most reliable)
        - YYYY-MM-DD (ISO format)
        - MM/DD/YYYY or DD/MM/YYYY
        - DD.MM.YYYY (European format)
        - Month DD, YYYY / DD Month YYYY (spelled out)
        - Jan 25, 2026 (abbreviated month)

        Args:
            text: Text that may contain a date

        Returns:
            datetime or None
        """
        if not text:
            return None

        # Common date patterns - order matters, more specific first
        patterns_and_formats = [
            # YYYY.MM.DD (Uneekor report page header - most reliable)
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', ['%Y.%m.%d']),
            # YYYY-MM-DD (ISO format)
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', ['%Y-%m-%d']),
            # DD.MM.YYYY (European format with dots)
            (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', ['%d.%m.%Y']),
            # MM/DD/YYYY or DD/MM/YYYY
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', ['%m/%d/%Y', '%d/%m/%Y']),
            # Abbreviated month: Jan 25, 2026 or Jan 25 2026
            (r'([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{4})', ['%b %d, %Y', '%b %d %Y']),
            # Full month: January 25, 2026
            (r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', ['%B %d, %Y', '%B %d %Y']),
            # DD Month YYYY: 25 January 2026
            (r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', ['%d %B %Y', '%d %b %Y']),
        ]

        for pattern, formats in patterns_and_formats:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(0)
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
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

    async def extract_date_from_report_page(self, report_url: str, debug: bool = False) -> Optional[datetime]:
        """
        Navigate to a report page and extract the session date from the header.

        The Uneekor report page displays the date in YYYY.MM.DD format in the
        page header, which is more reliable than parsing portal listing text.

        Args:
            report_url: Full report URL (https://my.uneekor.com/report?id=...&key=...)
            debug: If True, print detailed extraction attempts

        Returns:
            datetime if found, None otherwise
        """
        if not self.client.is_logged_in:
            raise RuntimeError("Must be logged in to extract report page date")

        page = self.client.page

        try:
            # Rate limit navigation
            await self._rate_limiter.wait_async('navigate_report')

            # Navigate to the report page
            response = await page.goto(report_url)
            if response and response.status != 200:
                print(f"  Warning: Page returned status {response.status}")

            await page.wait_for_load_state('networkidle')

            # Wait longer for React rendering to complete
            await asyncio.sleep(2.0)

            # Method 1: Use JavaScript to find date patterns in DOM text nodes
            # This is more reliable than CSS selectors for React apps
            date_from_js = await page.evaluate(r'''
                () => {
                    // Try multiple date patterns
                    const patterns = [
                        /(\d{4})\.(\d{1,2})\.(\d{1,2})/,        // YYYY.MM.DD
                        /(\d{4})-(\d{1,2})-(\d{1,2})/,          // YYYY-MM-DD
                        /(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})/i,  // Mon DD, YYYY
                    ];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    while (walker.nextNode()) {
                        const text = walker.currentNode.textContent.trim();
                        for (const regex of patterns) {
                            const match = text.match(regex);
                            if (match) return match[0];
                        }
                    }
                    return null;
                }
            ''')

            if date_from_js:
                if debug:
                    print(f"    Found date via JS walker: {date_from_js}")
                # Try parsing with _parse_date_from_text which handles multiple formats
                parsed = self._parse_date_from_text(date_from_js)
                if parsed:
                    return parsed

            # Method 2: Try CSS selectors as fallback
            date_selectors = [
                'h1',
                'h2',
                '.report-header',
                '.session-header',
                '[class*="header"]',
                '.date-display',
                '[class*="date"]',
                '.MuiTypography-root',  # Material-UI typography
                '[class*="title"]',
            ]

            for selector in date_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if debug and elements:
                        print(f"    Selector '{selector}': {len(elements)} elements")
                    for element in elements:
                        text = await element.inner_text()
                        if text:
                            parsed_date = self._parse_date_from_text(text)
                            if parsed_date:
                                if debug:
                                    print(f"    Found date in '{selector}': {text[:50]}")
                                return parsed_date
                except Exception as e:
                    if debug:
                        print(f"    Selector '{selector}' error: {e}")
                    continue

            # Method 3: Regex search on full page text
            try:
                body_text = await page.inner_text('body')
                import re
                # Try YYYY.MM.DD format first
                match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', body_text)
                if match:
                    date_str = match.group(0)
                    if debug:
                        print(f"    Found date in body text: {date_str}")
                    return datetime.strptime(date_str, '%Y.%m.%d')

                # Try other common formats
                patterns = [
                    (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),  # MM/DD/YYYY
                    (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),      # ISO format
                ]
                for pattern, fmt in patterns:
                    match = re.search(pattern, body_text)
                    if match:
                        date_str = match.group(0)
                        if debug:
                            print(f"    Found date pattern {fmt}: {date_str}")
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
            except Exception as e:
                if debug:
                    print(f"    Body text extraction error: {e}")

            if debug:
                # Print first 500 chars of page for debugging
                try:
                    snippet = await page.inner_text('body')
                    print(f"    Page text snippet: {snippet[:500]}")
                except Exception:
                    pass

            return None

        except Exception as e:
            print(f"  Error extracting date from report page: {e}")
            return None


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
