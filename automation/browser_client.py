"""
Playwright Browser Client for Uneekor Portal Automation.

Manages the browser lifecycle, authentication state, and provides
a clean interface for portal navigation.

Features:
- Headless mode for Cloud Run / CI environments
- Cookie persistence for session reuse
- Automatic retry on transient failures
- Screenshot capture for debugging
"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Browser = None
    BrowserContext = None
    Page = None

from .credential_manager import CredentialManager
from .rate_limiter import RateLimiter, get_conservative_limiter


@dataclass
class BrowserConfig:
    """Configuration for browser client."""
    headless: bool = True
    slow_mo: int = 0                    # Milliseconds between actions (for debugging)
    timeout: int = 30000                # Default timeout in milliseconds
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None    # Custom user agent
    screenshots_dir: Optional[str] = None  # Directory for debug screenshots


class PlaywrightClient:
    """
    Manages Playwright browser for Uneekor portal automation.

    Usage:
        async with PlaywrightClient() as client:
            # Login (uses cookies if available)
            await client.login()

            # Navigate and interact
            page = client.page
            await page.goto('https://my.uneekor.com/reports')

            # Get data
            sessions = await client.get_session_list()

    The client handles:
    - Browser lifecycle (startup/shutdown)
    - Authentication state management
    - Cookie persistence
    - Error recovery and retries
    """

    UNEEKOR_LOGIN_URL = 'https://my.uneekor.com/login'
    UNEEKOR_REPORTS_URL = 'https://my.uneekor.com/reports'
    UNEEKOR_BASE_URL = 'https://my.uneekor.com'

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        credential_manager: Optional[CredentialManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize Playwright client.

        Args:
            config: Browser configuration
            credential_manager: For cookie persistence
            rate_limiter: For request throttling
        """
        if not HAS_PLAYWRIGHT:
            raise ImportError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        self.config = config or BrowserConfig()
        self.cred_manager = credential_manager or CredentialManager()
        self.rate_limiter = rate_limiter or get_conservative_limiter()

        # Detect Cloud Run environment
        self.is_cloud_run = os.getenv('K_SERVICE') is not None
        if self.is_cloud_run:
            self.config.headless = True  # Force headless on Cloud Run

        # Browser state
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_logged_in = False

        # Screenshots directory
        if self.config.screenshots_dir:
            self._screenshots_dir = Path(self.config.screenshots_dir)
            self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._screenshots_dir = Path(__file__).parent.parent / 'logs' / 'screenshots'

    @property
    def page(self) -> Optional[Page]:
        """Get the current page instance."""
        return self._page

    @property
    def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        return self._is_logged_in

    async def __aenter__(self) -> 'PlaywrightClient':
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the browser and create a new context."""
        self._playwright = await async_playwright().start()

        # Launch browser
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
        )

        # Try to restore session from cookies
        storage_state = self.cred_manager.load_storage_state()

        # Create context with or without stored state
        context_options = {
            'viewport': {
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
        }

        if self.config.user_agent:
            context_options['user_agent'] = self.config.user_agent

        if storage_state:
            context_options['storage_state'] = storage_state
            print("Restored browser session from stored cookies")

        self._context = await self._browser.new_context(**context_options)
        self._context.set_default_timeout(self.config.timeout)

        # Create page
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        """Stop the browser and clean up resources."""
        if self._page:
            await self._page.close()
            self._page = None

        if self._context:
            # Save cookies before closing
            if self._is_logged_in:
                await self._save_session()
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._is_logged_in = False

    async def _save_session(self) -> None:
        """Save current session state to credential manager."""
        if self._context:
            storage_state = await self._context.storage_state()
            username, _ = self.cred_manager.get_login_credentials()
            self.cred_manager.save_storage_state(storage_state, username)

    async def login(self, force_fresh: bool = False) -> bool:
        """
        Log in to Uneekor portal.

        Attempts authentication in this order:
        1. Check if already logged in (from restored cookies)
        2. Use stored cookies if valid
        3. Use environment credentials for fresh login
        4. Prompt for interactive login (if headless=False)

        Args:
            force_fresh: Skip cookie restoration and do fresh login

        Returns:
            True if login successful
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")

        # Rate limit the login attempt
        await self.rate_limiter.wait_async('login')

        # Check if we're already logged in from restored cookies
        if not force_fresh and self.cred_manager.has_valid_credentials():
            # Verify session is still valid by visiting a protected page
            try:
                await self._page.goto(self.UNEEKOR_REPORTS_URL)
                await self._page.wait_for_load_state('networkidle')

                # Check if we're on the reports page (not redirected to login)
                if 'login' not in self._page.url.lower():
                    print("Session restored from cookies - already logged in")
                    self._is_logged_in = True
                    self.rate_limiter.report_success()
                    return True
            except Exception as e:
                print(f"Cookie session invalid: {e}")

        # Need fresh login
        username, password = self.cred_manager.get_login_credentials()

        if not username or not password:
            if self.config.headless:
                print("No credentials available and running headless - cannot login interactively")
                self.rate_limiter.report_error()
                return False
            else:
                return await self._interactive_login()

        # Automated login with credentials
        return await self._credential_login(username, password)

    async def _credential_login(self, username: str, password: str) -> bool:
        """
        Perform login using provided credentials.

        Args:
            username: Uneekor username/email
            password: Uneekor password

        Returns:
            True if login successful
        """
        try:
            print(f"Logging in as {username}...")

            # Navigate to login page
            await self._page.goto(self.UNEEKOR_LOGIN_URL)
            await self._page.wait_for_load_state('networkidle')

            # Fill login form
            # Note: These selectors may need adjustment based on actual Uneekor portal
            await self._page.fill('input[type="email"], input[name="email"], #email', username)
            await self._page.fill('input[type="password"], input[name="password"], #password', password)

            # Click login button
            await self._page.click('button[type="submit"], input[type="submit"], .login-button')

            # Wait for navigation
            await self._page.wait_for_load_state('networkidle')

            # Check if login was successful
            if 'login' not in self._page.url.lower():
                print("Login successful")
                self._is_logged_in = True
                await self._save_session()
                self.rate_limiter.report_success()
                return True
            else:
                print("Login failed - still on login page")
                await self._capture_screenshot('login_failed')
                self.rate_limiter.report_error()
                return False

        except Exception as e:
            print(f"Login error: {e}")
            await self._capture_screenshot('login_error')
            self.rate_limiter.report_error()
            return False

    async def _interactive_login(self) -> bool:
        """
        Allow user to log in interactively in headed mode.

        Opens the login page and waits for user to complete login manually.

        Returns:
            True if login detected successful
        """
        print("\n" + "="*60)
        print("INTERACTIVE LOGIN REQUIRED")
        print("="*60)
        print("1. A browser window will open to the Uneekor login page")
        print("2. Please log in manually")
        print("3. Once logged in, the script will continue automatically")
        print("="*60 + "\n")

        try:
            await self._page.goto(self.UNEEKOR_LOGIN_URL)

            # Wait for user to complete login (up to 5 minutes)
            # We detect login completion by URL change away from login page
            for _ in range(300):  # 300 seconds = 5 minutes
                await asyncio.sleep(1)
                if 'login' not in self._page.url.lower():
                    print("Login detected - saving session")
                    self._is_logged_in = True
                    await self._save_session()
                    return True

            print("Interactive login timed out after 5 minutes")
            return False

        except Exception as e:
            print(f"Interactive login error: {e}")
            return False

    async def _capture_screenshot(self, name: str) -> Optional[Path]:
        """
        Capture a screenshot for debugging.

        Args:
            name: Base name for the screenshot file

        Returns:
            Path to screenshot file, or None if failed
        """
        if not self._page:
            return None

        try:
            self._screenshots_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self._screenshots_dir / f"{name}_{timestamp}.png"
            await self._page.screenshot(path=str(filepath))
            print(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"Failed to capture screenshot: {e}")
            return None

    async def navigate_to_reports(self) -> bool:
        """
        Navigate to the reports/sessions list page.

        Returns:
            True if navigation successful
        """
        if not self._is_logged_in:
            raise RuntimeError("Must be logged in to navigate to reports")

        await self.rate_limiter.wait_async('navigate_reports')

        try:
            await self._page.goto(self.UNEEKOR_REPORTS_URL)
            await self._page.wait_for_load_state('networkidle')
            self.rate_limiter.report_success()
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            self.rate_limiter.report_error()
            return False

    async def get_page_content(self) -> str:
        """Get the current page HTML content."""
        if not self._page:
            return ""
        return await self._page.content()

    async def evaluate(self, expression: str) -> Any:
        """
        Evaluate JavaScript expression in the page context.

        Args:
            expression: JavaScript expression to evaluate

        Returns:
            Result of the expression
        """
        if not self._page:
            return None
        return await self._page.evaluate(expression)

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for an element to appear on the page.

        Args:
            selector: CSS selector
            timeout: Maximum wait time in milliseconds

        Returns:
            True if element found
        """
        if not self._page:
            return False

        try:
            await self._page.wait_for_selector(
                selector,
                timeout=timeout or self.config.timeout
            )
            return True
        except Exception:
            return False

    async def click(self, selector: str) -> bool:
        """
        Click an element on the page.

        Args:
            selector: CSS selector

        Returns:
            True if click successful
        """
        if not self._page:
            return False

        try:
            await self._page.click(selector)
            return True
        except Exception as e:
            print(f"Click failed on {selector}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get current client status.

        Returns:
            Dict with status information
        """
        return {
            'browser_running': self._browser is not None,
            'has_page': self._page is not None,
            'is_logged_in': self._is_logged_in,
            'is_headless': self.config.headless,
            'is_cloud_run': self.is_cloud_run,
            'current_url': self._page.url if self._page else None,
            'rate_limiter_stats': self.rate_limiter.get_stats(),
        }


async def test_browser_client():
    """Test the browser client (run with: python -m automation.browser_client)."""
    print("Testing PlaywrightClient...")

    config = BrowserConfig(headless=False)  # Show browser for testing

    async with PlaywrightClient(config=config) as client:
        print(f"Status: {client.get_status()}")

        # Attempt login
        success = await client.login()
        print(f"Login result: {success}")

        if success:
            # Navigate to reports
            await client.navigate_to_reports()
            print(f"Current URL: {client.page.url}")

            # Get page content
            content = await client.get_page_content()
            print(f"Page content length: {len(content)} chars")


if __name__ == '__main__':
    asyncio.run(test_browser_client())
