"""
Test Import Script - Using New Service Layer

Tests the complete import workflow:
1. ImportService fetches data from Uneekor API
2. MediaService downloads and caches media
3. DataService saves to SQLite + Firestore
4. Cloud Function auto-syncs to BigQuery
"""

import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services import ImportService

def progress_callback(message: str, current: int, total: int):
    """Progress callback for import"""
    if total > 0:
        percent = (current / total) * 100
        print(f"[{current}/{total}] {percent:.1f}% - {message}")
    else:
        print(f"[{current}] {message}")


def main():
    """Test import with new service layer"""

    # URL from user
    url = "https://my.uneekor.com/power-u-report?id=41511&key=pzlAxzpixWJoe&distance=yard&speed=mph"

    print("=" * 70)
    print("TESTING IMPORT WITH NEW SERVICE LAYER")
    print("=" * 70)
    print(f"\nURL: {url}")
    print(f"Session ID: 41511")

    # Initialize ImportService
    print("\n1. Initializing ImportService...")
    import_service = ImportService()
    print("   ✓ ImportService ready")

    # Validate URL
    print("\n2. Validating URL...")
    if not import_service.validate_url(url):
        print("   ✗ Invalid URL!")
        return
    print("   ✓ URL valid")

    # Run import
    print("\n3. Running import (with keyframes video strategy)...")
    start_time = time.time()

    result = import_service.import_report(
        url=url,
        progress_callback=progress_callback,
        frame_strategy="keyframes"  # 5 key frames per shot
    )

    duration = time.time() - start_time

    # Display results
    print("\n" + "=" * 70)
    print("IMPORT RESULTS")
    print("=" * 70)

    if result['success']:
        print("✓ Import successful!")
        print(f"\nShots processed:    {result['shot_count']}")
        print(f"Errors encountered: {result['error_count']}")
        print(f"Duration:           {duration:.2f} seconds")
        print(f"Report ID:          {result['report_id']}")

        if result['error_count'] > 0:
            print(f"\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")

        print("\n" + "=" * 70)
        print("WHAT HAPPENED:")
        print("=" * 70)
        print("✓ Data fetched from Uneekor API")
        print("✓ Media downloaded and cached locally")
        print("✓ Shots saved to SQLite (local database)")
        print("✓ Shots saved to Firestore (cloud database)")
        print("✓ Cloud Function will auto-sync to BigQuery")
        print("\nNext: Re-import same URL to test media caching (should be 10x faster)")

    else:
        print("✗ Import failed!")
        print(f"\nError: {result.get('error', 'Unknown error')}")
        if result['errors']:
            for error in result['errors']:
                print(f"  - {error}")

    print("=" * 70)


if __name__ == "__main__":
    main()
