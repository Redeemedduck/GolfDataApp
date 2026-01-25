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
        # Start new backfill
        config = BackfillConfig(
            date_start=datetime.strptime(args.start, '%Y-%m-%d').date() if args.start else None,
            date_end=datetime.strptime(args.end, '%Y-%m-%d').date() if args.end else None,
            max_sessions_per_run=args.max or 50,
            normalize_clubs=not args.no_normalize,
            auto_tag=not args.no_tags,
        )

        print("Starting new backfill run...")
        print(f"  Date range: {config.date_start or 'any'} to {config.date_end or 'any'}")
        print(f"  Max sessions: {config.max_sessions_per_run}")
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
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
