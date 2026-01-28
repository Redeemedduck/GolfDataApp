"""
Pytest configuration and shared fixtures for GolfDataApp tests.

This module provides:
- Temporary database fixtures
- Mock browser fixtures for automation tests
- Sample data fixtures
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_path():
    """Provide a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test.db")


@pytest.fixture
def discovery_db(temp_db_path):
    """Provide an initialized SessionDiscovery instance."""
    from automation.session_discovery import SessionDiscovery

    discovery = SessionDiscovery(db_path=temp_db_path)
    discovery.init_tables()
    return discovery


@pytest.fixture
def golf_db_instance(temp_db_path):
    """Provide an initialized golf_db with temporary database."""
    import golf_db

    original_path = golf_db.SQLITE_DB_PATH
    original_supabase = golf_db.supabase

    golf_db.SQLITE_DB_PATH = temp_db_path
    golf_db.supabase = None
    golf_db.init_db()

    yield golf_db

    # Restore original settings
    golf_db.SQLITE_DB_PATH = original_path
    golf_db.supabase = original_supabase


@pytest.fixture
def sample_session_info():
    """Provide a factory for creating sample SessionInfo objects."""
    from datetime import datetime
    from automation.uneekor_portal import SessionInfo

    def _create(
        report_id="test_123",
        api_key="test_key",
        portal_name="Test Session",
        session_date=None,
        clubs_used=None,
    ):
        return SessionInfo(
            report_id=report_id,
            api_key=api_key,
            portal_name=portal_name,
            session_date=session_date or datetime(2025, 1, 15),
            clubs_used=clubs_used or ["Driver", "7 Iron"],
        )

    return _create


@pytest.fixture
def sample_shot_data():
    """Provide sample shot data for testing."""
    return {
        "shot_id": "shot_001",
        "session_id": "session_001",
        "club": "Driver",
        "carry": 250,
        "total": 270,
        "ball_speed": 165,
        "club_speed": 110,
        "smash": 1.5,
        "launch_angle": 12.5,
        "back_spin": 2500,
        "side_spin": 150,
        "club_path": -2.0,
        "face_angle": -1.0,
    }


@pytest.fixture
def sample_shots_batch(sample_shot_data):
    """Provide a batch of sample shots."""
    shots = []
    for i in range(10):
        shot = sample_shot_data.copy()
        shot["shot_id"] = f"shot_{i:03d}"
        shot["carry"] = 250 + (i * 5)  # Vary carry distance
        shots.append(shot)
    return shots


@pytest.fixture
def mock_rate_limiter():
    """Provide a permissive rate limiter for testing."""
    from automation.rate_limiter import RateLimiter, RateLimiterConfig

    config = RateLimiterConfig(
        calls_per_minute=1000,  # Very permissive
        burst_size=100,
        backoff_on_error=False,
    )
    return RateLimiter(config)


@pytest.fixture
def backfill_config():
    """Provide a basic BackfillConfig for testing."""
    from automation.backfill_runner import BackfillConfig

    return BackfillConfig(
        max_sessions_per_run=10,
        max_sessions_per_hour=100,
        checkpoint_interval=2,
        dry_run=True,  # Always dry run in tests
    )


@pytest.fixture
def local_coach():
    """Provide a LocalCoach instance."""
    from local_coach import LocalCoach
    return LocalCoach()


@pytest.fixture
def populated_golf_db(golf_db_instance, sample_shots_batch):
    """Provide a golf_db with sample data already inserted."""
    for shot in sample_shots_batch:
        golf_db_instance.save_shot(shot)
    return golf_db_instance


@pytest.fixture
def ml_test_dataframe():
    """Provide a DataFrame suitable for ML testing."""
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    n_shots = 100

    return pd.DataFrame({
        'ball_speed': np.random.normal(160, 10, n_shots),
        'launch_angle': np.random.normal(12, 2, n_shots),
        'back_spin': np.random.normal(2500, 300, n_shots),
        'club_speed': np.random.normal(107, 8, n_shots),
        'attack_angle': np.random.normal(-1, 2, n_shots),
        'dynamic_loft': np.random.normal(15, 2, n_shots),
        'face_angle': np.random.normal(0, 2, n_shots),
        'club_path': np.random.normal(0, 3, n_shots),
        'side_spin': np.random.normal(0, 500, n_shots),
        'carry': np.random.normal(250, 15, n_shots),
        'total': np.random.normal(270, 18, n_shots),
    })


@pytest.fixture
def swing_data_good():
    """Provide good swing metrics for testing."""
    return {
        'ball_speed': 165,
        'club_speed': 110,
        'attack_angle': -1.0,
        'club_path': 0.0,
        'face_angle': 0.0,
        'impact_x': 0.0,
        'impact_y': 0.0,
    }


@pytest.fixture
def swing_data_flawed():
    """Provide swing metrics with multiple flaws for testing."""
    return {
        'ball_speed': 130,
        'club_speed': 100,  # Low smash factor (1.30)
        'attack_angle': -8.0,  # Too steep
        'club_path': -10.0,  # Severe out-to-in (over the top)
        'face_angle': 8.0,  # Very open
        'impact_x': 20.0,  # Off-center
        'impact_y': 15.0,
    }
