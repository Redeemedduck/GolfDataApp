#!/usr/bin/env python3
"""
Automation Runner CLI for GolfDataApp.

This script provides command-line access to automation features:
- Session discovery from Uneekor portal
- Historical backfill with rate limiting
- Future automation scheduling
- Status checking and reporting

Usage:
    # Discover new sessions (interactive login if needed)
    python automation_runner.py discover

    # Discover in headless mode (requires stored cookies or env credentials)
    python automation_runner.py discover --headless

    # Start historical backfill
    python automation_runner.py backfill --start 2025-01-01

    # Resume paused backfill
    python automation_runner.py backfill --resume

    # Check backfill status
    python automation_runner.py status

    # Interactive login to save cookies
    python automation_runner.py login

    # Test notification
    python automation_runner.py notify "Test message"

Environment Variables:
    UNEEKOR_USERNAME    - Uneekor portal username/email
    UNEEKOR_PASSWORD    - Uneekor portal password
    SLACK_WEBHOOK_URL   - Slack webhook for notifications

For detailed help on any command:
    python automation_runner.py <command> --help
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from automation.credential_manager import CredentialManager
from automation.session_discovery import SessionDiscovery, get_discovery
from automation.backfill_runner import BackfillRunner, BackfillConfig, list_backfill_runs, get_backfill_status
from automation.notifications import get_notifier, notify
from automation.browser_client import PlaywrightClient, BrowserConfig
from automation.naming_conventions import get_normalizer
from automation.uneekor_portal import UneekorPortalNavigator
import golf_db


def cmd_login(args):
    """Interactive login to save cookies for future use."""
    print("="*60)
    print("UNEEKOR PORTAL LOGIN")
    print("="*60)
    print()
    print("This will open a browser window for you to log in.")
    print("After successful login, your session will be saved")
    print("so future automation runs won't need manual login.")
    print()

    async def do_login():
        config = BrowserConfig(headless=False)  # Show browser
        client = PlaywrightClient(config=config)

        async with client:
            success = await client.login(force_fresh=True)

            if success:
                print()
                print("="*60)
                print("LOGIN SUCCESSFUL!")
                print("="*60)
                print("Your session has been saved.")
                print("You can now run automation commands in headless mode.")
            else:
                print()
                print("="*60)
                print("LOGIN FAILED")
                print("="*60)
                print("Please check your credentials and try again.")
                return 1

        return 0

    return asyncio.run(do_login())


def cmd_discover(args):
    """Discover sessions from Uneekor portal."""
    print("Discovering sessions from Uneekor portal...")
    print()

    discovery = get_discovery()

    async def do_discover():
        since_date = None
        if args.since:
            since_date = datetime.strptime(args.since, '%Y-%m-%d')

        result = await discovery.discover_sessions(
            headless=args.headless,
            max_sessions=args.max,
            since_date=since_date,
        )

        print()
        print("="*60)
        print("DISCOVERY RESULTS")
        print("="*60)
        print(f"Total discovered:  {result.total_discovered}")
        print(f"New sessions:      {result.new_sessions}")
        print(f"Already known:     {result.already_known}")
        print(f"Duration:          {result.duration_seconds:.1f}s")

        if result.errors:
            print()
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")

        if result.sessions:
            print()
            print("Sessions found:")
            for session in result.sessions[:10]:
                date_str = session.session_date.strftime('%Y-%m-%d') if session.session_date else 'Unknown'
                print(f"  - {session.report_id}: {session.portal_name or 'Unnamed'} ({date_str})")
            if len(result.sessions) > 10:
                print(f"  ... and {len(result.sessions) - 10} more")

        return 0 if not result.errors else 1

    return asyncio.run(do_discover())


def _cmd_retry_failed(args):
    """Retry previously failed imports."""
    discovery = get_discovery()

    # Get failed sessions
    failed = discovery.get_failed_sessions(include_needs_review=True, limit=100)

    if not failed:
        print("No failed sessions to retry.")
        return 0

    print(f"Found {len(failed)} failed session(s):")
    for item in failed[:10]:
        date_str = item.session_date.strftime('%Y-%m-%d') if item.session_date else 'unknown'
        print(f"  - {item.report_id}: {item.portal_name or 'Unnamed'} ({date_str})")
        print(f"    Status: {item.status.value}, Attempts: {item.attempts}")
        if item.error_message:
            # Truncate long error messages
            error_preview = item.error_message[:80] + '...' if len(item.error_message) > 80 else item.error_message
            print(f"    Error: {error_preview}")
    if len(failed) > 10:
        print(f"  ... and {len(failed) - 10} more")

    print()

    # Reset failed sessions to pending
    report_ids = [item.report_id for item in failed]
    reset_count = discovery.reset_for_retry(report_ids)
    print(f"Reset {reset_count} session(s) for retry.")

    # Now run a regular backfill
    print()
    print("Starting retry backfill...")

    config = BackfillConfig(
        max_sessions_per_run=args.max or 50,
        normalize_clubs=not getattr(args, 'no_normalize', False),
        auto_tag=not getattr(args, 'no_tags', False),
    )

    runner = BackfillRunner(config=config)

    async def do_retry():
        def progress_callback(progress):
            pct = (progress.sessions_processed / progress.sessions_total * 100) if progress.sessions_total > 0 else 0
            print(f"  Progress: {progress.sessions_processed}/{progress.sessions_total} ({pct:.0f}%) - {progress.total_shots} shots")

        result = await runner.run(progress_callback=progress_callback)

        print()
        print("="*60)
        print("RETRY RESULTS")
        print("="*60)
        print(f"Sessions imported: {result.sessions_imported}")
        print(f"Sessions failed:   {result.sessions_failed}")
        print(f"Total shots:       {result.total_shots}")

        if result.errors:
            print()
            print("Errors:")
            for error in result.errors[:5]:
                print(f"  - {error}")

        return 0 if result.status.value == 'completed' else 1

    return asyncio.run(do_retry())


def cmd_backfill(args):
    """Run historical backfill."""
    if args.status:
        # Show status of recent runs
        runs = list_backfill_runs(limit=5)
        if not runs:
            print("No backfill runs found.")
            return 0

        print("Recent backfill runs:")
        print()
        for run in runs:
            status = run.get('status', 'unknown')
            started = run.get('started_at', 'unknown')
            imported = run.get('sessions_imported', 0)
            total = run.get('sessions_total', 0)
            print(f"  {run['run_id']}: {status} - {imported}/{total} sessions ({started})")

        return 0

    # Handle retry-failed option
    if args.retry_failed:
        return _cmd_retry_failed(args)

    if args.resume:
        # Find most recent paused run
        runs = list_backfill_runs(limit=10)
        paused_run = None
        for run in runs:
            if run.get('status') == 'paused':
                paused_run = run
                break

        if not paused_run:
            print("No paused backfill run found to resume.")
            return 1

        print(f"Resuming backfill run {paused_run['run_id']}...")
        runner = BackfillRunner(resume_run_id=paused_run['run_id'])
    else:
        # Parse clubs filter
        clubs_filter = None
        if args.clubs:
            clubs_filter = [c.strip() for c in args.clubs.split(',') if c.strip()]

        # Start new backfill
        config = BackfillConfig(
            date_start=datetime.strptime(args.start, '%Y-%m-%d').date() if args.start else None,
            date_end=datetime.strptime(args.end, '%Y-%m-%d').date() if args.end else None,
            max_sessions_per_run=args.max or 50,
            normalize_clubs=not args.no_normalize,
            auto_tag=not args.no_tags,
            clubs_filter=clubs_filter,
            dry_run=args.dry_run,
            delay_seconds=args.delay,
            recent_first=args.recent,
        )

        print("Starting new backfill run...")
        print(f"  Date range: {config.date_start or 'any'} to {config.date_end or 'any'}")
        print(f"  Max sessions: {config.max_sessions_per_run}")
        if config.recent_first:
            print(f"  Order: newest first")
        if config.delay_seconds:
            print(f"  Delay: {config.delay_seconds}s between imports ({config.delay_seconds // 60} min)")
        if clubs_filter:
            print(f"  Clubs filter: {', '.join(clubs_filter)}")
        if args.dry_run:
            print("  Mode: DRY RUN (no changes will be made)")
        print()

        runner = BackfillRunner(config=config)

    async def do_backfill():
        def progress_callback(progress):
            pct = (progress.sessions_processed / progress.sessions_total * 100) if progress.sessions_total > 0 else 0
            print(f"  Progress: {progress.sessions_processed}/{progress.sessions_total} ({pct:.0f}%) - {progress.total_shots} shots")

        result = await runner.run(progress_callback=progress_callback)

        print()
        print("="*60)
        print("BACKFILL RESULTS")
        print("="*60)
        print(f"Run ID:            {result.run_id}")
        print(f"Status:            {result.status.value}")
        print(f"Sessions imported: {result.sessions_imported}")
        print(f"Sessions skipped:  {result.sessions_skipped}")
        print(f"Sessions failed:   {result.sessions_failed}")
        print(f"Total shots:       {result.total_shots}")
        print(f"Duration:          {result.duration_seconds:.1f}s")

        if result.errors:
            print()
            print("Errors:")
            for error in result.errors[:5]:
                print(f"  - {error}")
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more")

        return 0 if result.status.value == 'completed' else 1

    return asyncio.run(do_backfill())


def cmd_status(args):
    """Show automation status."""
    discovery = get_discovery()
    cred_manager = CredentialManager()

    print("="*60)
    print("AUTOMATION STATUS")
    print("="*60)
    print()

    # Credential status
    cred_info = cred_manager.get_credential_info()
    print("Credentials:")
    print(f"  Environment variables: {'Yes' if cred_info['has_env_credentials'] else 'No'}")
    print(f"  Stored cookies:        {'Yes' if cred_info['has_stored_cookies'] else 'No'}")
    print(f"  Cookies valid:         {'Yes' if cred_info['cookies_valid'] else 'No'}")
    if cred_info['cookies_expires_at']:
        print(f"  Cookies expire:        {cred_info['cookies_expires_at']}")
    print(f"  Auth method:           {cred_manager.get_auth_method()}")
    print()

    # Discovery stats
    stats = discovery.get_discovery_stats()
    print("Sessions discovered:")
    for status, count in stats.get('by_status', {}).items():
        print(f"  {status}: {count}")
    print(f"  Total shots imported: {stats.get('total_shots_imported', 0)}")
    print()

    # Recent backfill runs
    runs = list_backfill_runs(limit=3)
    if runs:
        print("Recent backfill runs:")
        for run in runs:
            status = run.get('status', 'unknown')
            imported = run.get('sessions_imported', 0)
            print(f"  {run['run_id']}: {status} ({imported} sessions)")
        print()

    # Notification status
    notifier = get_notifier()
    print("Notifications:")
    print(f"  Slack configured: {'Yes' if notifier.config.slack_webhook_url else 'No'}")
    print(f"  Console logging:  {'Yes' if notifier.config.log_to_console else 'No'}")
    print(f"  File logging:     {'Yes' if notifier.config.log_to_file else 'No'}")

    return 0


def cmd_notify(args):
    """Send a test notification."""
    message = args.message or "Test notification from GolfDataApp automation"

    async def do_notify():
        results = await notify(message, level=args.level)

        print("Notification sent:")
        for result in results:
            status = "OK" if result.success else f"FAILED: {result.error}"
            print(f"  {result.channel}: {status}")

        return 0 if all(r.success for r in results) else 1

    return asyncio.run(do_notify())


def cmd_reclassify_dates(args):
    """Manage session date reclassification."""
    discovery = get_discovery()

    # Handle --status first
    if args.status:
        print("="*60)
        print("SESSION DATE STATUS")
        print("="*60)
        print()

        # Get sessions missing dates
        missing = discovery.get_sessions_missing_dates(limit=100)
        print(f"Sessions missing dates: {len(missing)}")
        if missing:
            print()
            print("Sessions without dates:")
            for session in missing[:10]:
                print(f"  - {session['report_id']}: {session['portal_name'] or 'Unnamed'} ({session['shot_count']} shots)")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")

        # Get sessions with dates
        with_dates = discovery.get_sessions_with_dates()
        print()
        print(f"Sessions with dates: {len(with_dates)}")

        # Get shots missing session_date
        shots_missing = golf_db.get_sessions_missing_dates(limit=100)
        print()
        print(f"Sessions with shots missing session_date: {len(shots_missing)}")

        return 0

    # Handle --manual
    if args.manual:
        if len(args.manual) != 2:
            print("Error: --manual requires two arguments: <report_id> <date>")
            print("Example: --manual 43285 2026-01-15")
            return 1

        report_id = args.manual[0]
        date_str = args.manual[1]

        try:
            session_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
            return 1

        if args.dry_run:
            print(f"[DRY RUN] Would set session_date for {report_id} to {date_str}")
            return 0

        # Update sessions_discovered
        success = discovery.update_session_date(report_id, session_date, source='manual')
        if not success:
            print(f"Error: Failed to update session {report_id} in sessions_discovered")
            return 1

        # Update shots table
        updated = golf_db.update_session_date_for_shots(report_id, date_str)
        print(f"Updated {updated} shots with session_date = {date_str}")
        return 0

    # Handle --backfill
    if args.backfill:
        print("Backfilling session dates from sessions_discovered to shots...")
        print()

        if args.dry_run:
            # Show what would be updated
            sessions = discovery.get_sessions_with_dates()
            shots_missing = golf_db.get_sessions_missing_dates(limit=1000)
            missing_ids = {s['session_id'] for s in shots_missing}

            would_update = [s for s in sessions if s['report_id'] in missing_ids]
            print(f"[DRY RUN] Would update {len(would_update)} sessions with dates:")
            for s in would_update[:10]:
                print(f"  - {s['report_id']}: {s['session_date']}")
            if len(would_update) > 10:
                print(f"  ... and {len(would_update) - 10} more")
            return 0

        result = golf_db.backfill_session_dates()
        print()
        print("="*60)
        print("BACKFILL RESULTS")
        print("="*60)
        print(f"Shots updated:  {result['updated']}")
        print(f"Sessions skipped: {result['skipped']}")
        print(f"Errors:         {result['errors']}")
        return 0 if result['errors'] == 0 else 1

    # Handle --scrape
    if args.scrape:
        print("Scraping session dates from report pages...")
        print()

        # Get sessions missing dates
        missing = discovery.get_sessions_missing_dates(limit=args.max or 20)
        if not missing:
            print("No sessions missing dates!")
            return 0

        print(f"Found {len(missing)} sessions missing dates")
        print()

        async def do_scrape():
            config = BrowserConfig(headless=args.headless)
            client = PlaywrightClient(config=config)

            async with client:
                login_success = await client.login()
                if not login_success:
                    print("Error: Failed to log in")
                    return 1

                navigator = UneekorPortalNavigator(browser_client=client)

                scraped = 0
                failed = 0

                for i, session in enumerate(missing):
                    report_url = f"https://my.uneekor.com/report?id={session['report_id']}&key={session['api_key']}"

                    if args.dry_run:
                        print(f"[DRY RUN] Would scrape: {session['report_id']}")
                        scraped += 1
                        continue

                    print(f"[{i+1}/{len(missing)}] Scraping {session['report_id']}...")

                    try:
                        extracted_date = await navigator.extract_date_from_report_page(report_url)

                        if extracted_date:
                            # Update sessions_discovered
                            discovery.update_session_date(
                                session['report_id'],
                                extracted_date,
                                source='report_page'
                            )

                            # Update shots table
                            updated = golf_db.update_session_date_for_shots(
                                session['report_id'],
                                extracted_date.isoformat()
                            )

                            print(f"  Found date: {extracted_date.strftime('%Y-%m-%d')} ({updated} shots updated)")
                            scraped += 1
                        else:
                            print(f"  No date found on report page")
                            failed += 1

                    except Exception as e:
                        print(f"  Error: {e}")
                        failed += 1

                    # Rate limit: wait between scrapes
                    if i < len(missing) - 1:
                        delay = args.delay or 300  # Default 5 minutes
                        print(f"  Waiting {delay}s before next scrape...")
                        await asyncio.sleep(delay)

                print()
                print("="*60)
                print("SCRAPE RESULTS")
                print("="*60)
                print(f"Sessions scraped: {scraped}")
                print(f"Failed:           {failed}")
                return 0 if failed == 0 else 1

        return asyncio.run(do_scrape())

    # No action specified
    print("No action specified. Use one of:")
    print("  --scrape     Extract dates from report pages")
    print("  --manual     Set date manually for a session")
    print("  --backfill   Copy dates from sessions_discovered to shots")
    print("  --status     Show date status summary")
    return 1


def cmd_normalize(args):
    """Normalize club names in database."""
    normalizer = get_normalizer()

    if args.test:
        # Test mode - show what would be normalized
        clubs = args.test.split(',')
        print("Normalization preview:")
        for club in clubs:
            result = normalizer.normalize(club.strip())
            confidence = f"{result.confidence*100:.0f}%"
            print(f"  '{club.strip()}' -> '{result.normalized}' ({confidence})")
        return 0

    # Apply normalization to database
    print("This feature requires database access.")
    print("Run with --test to preview normalization.")
    return 1


def main():
    parser = argparse.ArgumentParser(
        description='GolfDataApp Automation Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Login command
    login_parser = subparsers.add_parser('login', help='Interactive login to save cookies')

    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover sessions from Uneekor')
    discover_parser.add_argument('--headless', action='store_true',
                                  help='Run in headless mode (requires saved cookies)')
    discover_parser.add_argument('--max', type=int, default=100,
                                  help='Maximum sessions to discover (default: 100)')
    discover_parser.add_argument('--since', type=str,
                                  help='Only discover sessions since date (YYYY-MM-DD)')

    # Backfill command
    backfill_parser = subparsers.add_parser('backfill', help='Run historical backfill')
    backfill_parser.add_argument('--start', type=str,
                                  help='Start date for backfill (YYYY-MM-DD)')
    backfill_parser.add_argument('--end', type=str,
                                  help='End date for backfill (YYYY-MM-DD)')
    backfill_parser.add_argument('--max', type=int,
                                  help='Maximum sessions per run (default: 50)')
    backfill_parser.add_argument('--resume', action='store_true',
                                  help='Resume most recent paused backfill')
    backfill_parser.add_argument('--status', action='store_true',
                                  help='Show status of recent backfill runs')
    backfill_parser.add_argument('--no-normalize', action='store_true',
                                  help='Skip club name normalization')
    backfill_parser.add_argument('--no-tags', action='store_true',
                                  help='Skip auto-tagging')
    backfill_parser.add_argument('--clubs', type=str,
                                  help='Only import sessions with these clubs (comma-separated, e.g. "Driver,7 Iron")')
    backfill_parser.add_argument('--dry-run', action='store_true',
                                  help='Preview what would be imported without making changes')
    backfill_parser.add_argument('--retry-failed', action='store_true',
                                  help='Retry previously failed imports')
    backfill_parser.add_argument('--delay', type=int,
                                  help='Seconds between imports (default: rate limiter, e.g. --delay 300 for 5 min)')
    backfill_parser.add_argument('--recent', action='store_true',
                                  help='Import newest sessions first (default: oldest first)')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show automation status')

    # Notify command
    notify_parser = subparsers.add_parser('notify', help='Send test notification')
    notify_parser.add_argument('message', nargs='?', help='Message to send')
    notify_parser.add_argument('--level', choices=['info', 'warning', 'error'],
                                default='info', help='Notification level')

    # Normalize command
    normalize_parser = subparsers.add_parser('normalize', help='Normalize club names')
    normalize_parser.add_argument('--test', type=str,
                                   help='Test normalization on comma-separated club names')

    # Reclassify-dates command
    reclassify_parser = subparsers.add_parser('reclassify-dates',
                                               help='Manage session date reclassification')
    reclassify_parser.add_argument('--scrape', action='store_true',
                                    help='Scrape dates from report pages (rate-limited)')
    reclassify_parser.add_argument('--manual', nargs=2, metavar=('REPORT_ID', 'DATE'),
                                    help='Set date manually (YYYY-MM-DD format)')
    reclassify_parser.add_argument('--backfill', action='store_true',
                                    help='Copy dates from sessions_discovered to shots table')
    reclassify_parser.add_argument('--status', action='store_true',
                                    help='Show session date status summary')
    reclassify_parser.add_argument('--max', type=int, default=20,
                                    help='Maximum sessions to scrape (default: 20)')
    reclassify_parser.add_argument('--delay', type=int, default=300,
                                    help='Seconds between scrapes (default: 300 = 5 min)')
    reclassify_parser.add_argument('--headless', action='store_true',
                                    help='Run browser in headless mode')
    reclassify_parser.add_argument('--dry-run', action='store_true',
                                    help='Preview without making changes')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to command handler
    handlers = {
        'login': cmd_login,
        'discover': cmd_discover,
        'backfill': cmd_backfill,
        'status': cmd_status,
        'notify': cmd_notify,
        'normalize': cmd_normalize,
        'reclassify-dates': cmd_reclassify_dates,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
