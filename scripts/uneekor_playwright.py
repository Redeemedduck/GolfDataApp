#!/usr/bin/env python3
"""
Playwright automation for Uneekor report discovery.

This script logs into the Uneekor portal, navigates to the report list, and
collects report URLs so the existing API scraper can ingest them without user
intervention.

Environment variables (selectors are required because the UI can change):
  UNEEKOR_EMAIL
  UNEEKOR_PASSWORD
  UNEEKOR_LOGIN_URL (default: https://my.uneekor.com)
  UNEEKOR_REPORT_LIST_URL (default: https://my.uneekor.com/report)
  UNEEKOR_BASE_URL (default: https://my.uneekor.com)

  UNEEKOR_EMAIL_SELECTOR
  UNEEKOR_PASSWORD_SELECTOR
  UNEEKOR_SUBMIT_SELECTOR
  UNEEKOR_SESSION_ROW_SELECTOR
  UNEEKOR_SESSION_LINK_SELECTOR
  UNEEKOR_SESSION_DATE_SELECTOR
  UNEEKOR_NEXT_PAGE_SELECTOR (optional)

Examples:
  python scripts/uneekor_playwright.py --mode incremental --dry-run
  python scripts/uneekor_playwright.py --mode backfill --since 2024-01-01 --ingest
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from typing import Iterable, List, Optional
from urllib.parse import urljoin

import golf_db
import golf_scraper

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit(
        "Playwright is not installed. Install it with: pip install playwright && playwright install"
    ) from exc


LOGIN_URL = os.getenv("UNEEKOR_LOGIN_URL", "https://my.uneekor.com")
REPORT_LIST_URL = os.getenv("UNEEKOR_REPORT_LIST_URL", "https://my.uneekor.com/report")
BASE_URL = os.getenv("UNEEKOR_BASE_URL", "https://my.uneekor.com")


def parse_date(value: str) -> Optional[dt.date]:
    """Parse a date string from the report list (YYYY-MM-DD or MM/DD/YYYY)."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y.%m.%d"):
        try:
            return dt.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def get_required_env(name: str) -> str:
    """Fetch required environment variables with a clear error."""
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def login(page) -> None:
    """Log into the Uneekor portal with selectors configured via env."""
    email = get_required_env("UNEEKOR_EMAIL")
    password = get_required_env("UNEEKOR_PASSWORD")
    email_selector = get_required_env("UNEEKOR_EMAIL_SELECTOR")
    password_selector = get_required_env("UNEEKOR_PASSWORD_SELECTOR")
    submit_selector = get_required_env("UNEEKOR_SUBMIT_SELECTOR")

    page.goto(LOGIN_URL, wait_until="networkidle")
    page.fill(email_selector, email)
    page.fill(password_selector, password)
    page.click(submit_selector)
    page.wait_for_load_state("networkidle")


def collect_report_links(
    page,
    since: Optional[dt.date],
    until: Optional[dt.date],
    limit: Optional[int],
    stop_on_known: bool,
    known_session_ids: set[str],
) -> List[dict]:
    """Collect report links from the list page, optionally paginating."""
    row_selector = get_required_env("UNEEKOR_SESSION_ROW_SELECTOR")
    link_selector = get_required_env("UNEEKOR_SESSION_LINK_SELECTOR")
    date_selector = get_required_env("UNEEKOR_SESSION_DATE_SELECTOR")
    next_page_selector = os.getenv("UNEEKOR_NEXT_PAGE_SELECTOR")

    collected: List[dict] = []
    page.goto(REPORT_LIST_URL, wait_until="networkidle")

    while True:
        try:
            page.wait_for_selector(row_selector, timeout=10000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Timed out waiting for session rows. Check selectors.") from exc

        rows = page.query_selector_all(row_selector)
        for row in rows:
            link_el = row.query_selector(link_selector)
            date_el = row.query_selector(date_selector)
            if not link_el:
                continue
            href = link_el.get_attribute("href")
            if not href:
                continue

            url = href if href.startswith("http") else urljoin(BASE_URL, href)
            date_text = date_el.inner_text().strip() if date_el else ""
            session_date = parse_date(date_text)

            report_id, _ = golf_scraper.extract_url_params(url)
            if stop_on_known and report_id and report_id in known_session_ids:
                return collected

            if since and session_date and session_date < since:
                return collected
            if until and session_date and session_date > until:
                continue

            collected.append(
                {
                    "url": url,
                    "date": session_date.isoformat() if session_date else None,
                }
            )
            if limit and len(collected) >= limit:
                return collected

        if not next_page_selector:
            break

        next_button = page.query_selector(next_page_selector)
        if not next_button:
            break
        if next_button.is_disabled():
            break
        next_button.click()
        page.wait_for_load_state("networkidle")

    return collected


def load_known_session_ids() -> set[str]:
    """Fetch known session IDs from the local database."""
    sessions = golf_db.get_unique_sessions()
    return {str(session["session_id"]) for session in sessions}


def ingest_reports(report_links: Iterable[dict], dry_run: bool) -> None:
    """Ingest report links via the existing scraper."""
    for report in report_links:
        url = report["url"]
        if dry_run:
            print(f"[DRY RUN] Would ingest: {url}")
            continue

        def progress(message: str) -> None:
            print(message)

        result = golf_scraper.run_scraper(url, progress)
        print(result)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate Uneekor report discovery via Playwright.")
    parser.add_argument("--mode", choices=["incremental", "backfill"], default="incremental")
    parser.add_argument("--since", help="Start date for backfill (YYYY-MM-DD).")
    parser.add_argument("--until", help="End date for backfill (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, help="Maximum number of reports to collect.")
    parser.add_argument("--dry-run", action="store_true", help="Only print report URLs.")
    parser.add_argument("--ingest", action="store_true", help="Run the API scraper for new reports.")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless.")
    parser.add_argument("--headed", action="store_true", help="Run browser with a visible window.")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    since = parse_date(args.since) if args.since else None
    until = parse_date(args.until) if args.until else None

    if args.mode == "incremental":
        since = None

    known_session_ids = load_known_session_ids()
    headless = args.headless and not args.headed

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        login(page)
        report_links = collect_report_links(
            page=page,
            since=since,
            until=until,
            limit=args.limit,
            stop_on_known=args.mode == "incremental",
            known_session_ids=known_session_ids,
        )
        browser.close()

    if not report_links:
        print("No new reports found.")
        return 0

    for report in report_links:
        print(f"Found report: {report['url']} (date={report['date']})")

    if args.ingest:
        ingest_reports(report_links, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
