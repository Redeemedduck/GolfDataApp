"""
Test Script for Service Layer

Verifies that all services are working correctly before running the Streamlit app.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services import DataService, ImportService, MediaService

def test_data_service():
    """Test DataService operations"""
    print("\n=== Testing DataService ===")

    try:
        service = DataService()
        print("✓ DataService initialized")

        # Test get_sessions
        sessions = service.get_sessions()
        print(f"✓ Found {len(sessions)} sessions")

        if sessions:
            # Test get_session
            session_id = sessions[0]['session_id']
            session_data = service.get_session(session_id)
            print(f"✓ Retrieved session {session_id} with {session_data['shot_count']} shots")

            # Test get_shots
            shots = service.get_shots(session_id=session_id)
            print(f"✓ Retrieved {len(shots)} shots for session")

            # Test get_session_summary
            summary = service.get_session_summary(session_id)
            print(f"✓ Generated session summary")

            # Test get_club_statistics
            if session_data['clubs']:
                club = session_data['clubs'][0]
                stats = service.get_club_statistics(club)
                print(f"✓ Retrieved statistics for {club}: {stats['shot_count']} shots")

        # Test get_data_summary
        data_summary = service.get_data_summary()
        print(f"✓ Data summary: {data_summary['total_shots']} total shots, {data_summary['total_sessions']} sessions")

        # Performance metrics
        metrics = service.get_performance_metrics()
        if metrics:
            print(f"✓ Performance metrics collected: {len(metrics)} operations tracked")

        return True

    except Exception as e:
        print(f"✗ DataService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_import_service():
    """Test ImportService operations"""
    print("\n=== Testing ImportService ===")

    try:
        service = ImportService()
        print("✓ ImportService initialized")

        # Test URL validation
        valid_url = "https://my.uneekor.com/report?id=12345&key=abc123"
        invalid_url = "https://example.com/invalid"

        if service.validate_url(valid_url):
            print("✓ URL validation working (valid URL accepted)")
        else:
            print("✗ Valid URL rejected")
            return False

        if not service.validate_url(invalid_url):
            print("✓ URL validation working (invalid URL rejected)")
        else:
            print("✗ Invalid URL accepted")
            return False

        print("✓ ImportService ready for use")
        return True

    except Exception as e:
        print(f"✗ ImportService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_media_service():
    """Test MediaService operations"""
    print("\n=== Testing MediaService ===")

    try:
        service = MediaService()
        print("✓ MediaService initialized")

        # Test cache stats
        stats = service.get_cache_stats()
        print(f"✓ Cache stats: {stats['total_entries']} entries, {stats['total_size_mb']} MB")

        print("✓ MediaService ready for use")
        return True

    except Exception as e:
        print(f"✗ MediaService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repositories():
    """Test repository layer"""
    print("\n=== Testing Repositories ===")

    try:
        from repositories import ShotRepository, MediaRepository

        # Test ShotRepository
        shot_repo = ShotRepository()
        print("✓ ShotRepository initialized")

        sessions = shot_repo.get_unique_sessions()
        print(f"✓ ShotRepository: Found {len(sessions)} sessions")

        # Test MediaRepository
        media_repo = MediaRepository()
        print(f"✓ MediaRepository initialized (storage_enabled={media_repo.storage_enabled})")

        return True

    except Exception as e:
        print(f"✗ Repository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("SERVICE LAYER TEST SUITE")
    print("=" * 60)

    results = {
        'DataService': test_data_service(),
        'ImportService': test_import_service(),
        'MediaService': test_media_service(),
        'Repositories': test_repositories()
    }

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20s} {status}")

    all_passed = all(results.values())

    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nYour service layer is ready to use!")
        print("\nNext steps:")
        print("1. Run: streamlit run app.py")
        print("2. Test importing a report")
        print("3. Verify data appears correctly")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review the errors above before proceeding.")
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
