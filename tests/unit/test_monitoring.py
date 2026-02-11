"""
Unit tests for ML monitoring components.

Tests PerformanceTracker (prediction logging) and DriftDetector (drift detection).
Uses isolated temporary databases for each test.
"""

import unittest
import tempfile
import shutil
import sqlite3
import os
from datetime import datetime, timedelta

# Test imports
from ml.monitoring.drift_detector import DriftDetector, check_and_trigger_retraining
from ml.monitoring.performance_tracker import PerformanceTracker


class TestPerformanceTracker(unittest.TestCase):
    """Tests for PerformanceTracker prediction logging."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_golf.db')
        self._init_tables()

    def tearDown(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)

    def _init_tables(self):
        """Initialize required database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create shots table
        cursor.execute('''
            CREATE TABLE shots (
                shot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                club TEXT,
                carry REAL
            )
        ''')

        # Create model_predictions table
        cursor.execute('''
            CREATE TABLE model_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_id TEXT NOT NULL,
                club TEXT,
                predicted_value REAL NOT NULL,
                actual_value REAL NOT NULL,
                absolute_error REAL NOT NULL,
                model_version TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def test_log_prediction_stores_record(self):
        """Test that log_prediction inserts a record into model_predictions."""
        tracker = PerformanceTracker(db_path=self.db_path)

        tracker.log_prediction(
            shot_id='shot_001',
            club='Driver',
            predicted_carry=250.0,
            actual_carry=245.0,
            model_version='v1.0'
        )

        # Verify record exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM model_predictions WHERE shot_id = ?', ('shot_001',))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[1], 'shot_001')  # shot_id
        self.assertEqual(row[2], 'Driver')     # club
        self.assertEqual(row[3], 250.0)        # predicted_value
        self.assertEqual(row[4], 245.0)        # actual_value
        self.assertEqual(row[5], 5.0)          # absolute_error

    def test_log_prediction_computes_absolute_error(self):
        """Test that absolute_error is computed correctly."""
        tracker = PerformanceTracker(db_path=self.db_path)

        tracker.log_prediction(
            shot_id='shot_002',
            club='7 Iron',
            predicted_carry=150.0,
            actual_carry=140.0,
            model_version='v1.0'
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT absolute_error FROM model_predictions WHERE shot_id = ?', ('shot_002',))
        error = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(error, 10.0)

    def test_log_prediction_skips_sentinel_carry(self):
        """Test that predictions with sentinel carry (99999) are skipped."""
        tracker = PerformanceTracker(db_path=self.db_path)

        tracker.log_prediction(
            shot_id='shot_003',
            club='Driver',
            predicted_carry=250.0,
            actual_carry=99999,
            model_version='v1.0'
        )

        # Verify no record inserted
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM model_predictions WHERE shot_id = ?', ('shot_003',))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0)

    def test_log_prediction_skips_zero_carry(self):
        """Test that predictions with zero carry are skipped."""
        tracker = PerformanceTracker(db_path=self.db_path)

        tracker.log_prediction(
            shot_id='shot_004',
            club='Driver',
            predicted_carry=250.0,
            actual_carry=0,
            model_version='v1.0'
        )

        # Verify no record inserted
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM model_predictions WHERE shot_id = ?', ('shot_004',))
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0)

    def test_log_prediction_handles_error_gracefully(self):
        """Test that invalid db_path doesn't raise exception (graceful degradation)."""
        tracker = PerformanceTracker(db_path='/nonexistent/path/database.db')

        # Should not raise exception
        try:
            tracker.log_prediction(
                shot_id='shot_005',
                club='Driver',
                predicted_carry=250.0,
                actual_carry=245.0,
                model_version='v1.0'
            )
        except Exception as e:
            self.fail(f"log_prediction raised exception: {e}")

    def test_get_session_predictions_returns_dataframe(self):
        """Test that get_session_predictions returns correct DataFrame."""
        tracker = PerformanceTracker(db_path=self.db_path)

        # Insert shots
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO shots (shot_id, session_id, club, carry)
            VALUES (?, ?, ?, ?)
        ''', ('shot_006', 'session_001', 'Driver', 250.0))
        cursor.execute('''
            INSERT INTO shots (shot_id, session_id, club, carry)
            VALUES (?, ?, ?, ?)
        ''', ('shot_007', 'session_001', '7 Iron', 150.0))
        conn.commit()
        conn.close()

        # Log predictions
        tracker.log_prediction('shot_006', 'Driver', 255.0, 250.0, 'v1.0')
        tracker.log_prediction('shot_007', '7 Iron', 145.0, 150.0, 'v1.0')

        # Get session predictions
        df = tracker.get_session_predictions('session_001')

        self.assertEqual(len(df), 2)
        self.assertIn('predicted_value', df.columns)
        self.assertIn('actual_value', df.columns)
        self.assertIn('absolute_error', df.columns)


class TestDriftDetector(unittest.TestCase):
    """Tests for DriftDetector drift detection."""

    def setUp(self):
        """Create temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_golf.db')
        self._init_tables()

    def tearDown(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)

    def _init_tables(self):
        """Initialize required database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create shots table
        cursor.execute('''
            CREATE TABLE shots (
                shot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                club TEXT,
                carry REAL
            )
        ''')

        # Create model_predictions table
        cursor.execute('''
            CREATE TABLE model_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shot_id TEXT NOT NULL,
                club TEXT,
                predicted_value REAL NOT NULL,
                actual_value REAL NOT NULL,
                absolute_error REAL NOT NULL,
                model_version TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create model_performance table
        cursor.execute('''
            CREATE TABLE model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                session_mae REAL NOT NULL,
                baseline_mae REAL,
                has_drift INTEGER DEFAULT 0,
                drift_pct REAL,
                consecutive_drift INTEGER DEFAULT 0,
                model_version TEXT,
                recommendation TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def _insert_predictions(self, session_id, errors):
        """Helper to insert predictions with specific errors."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for i, error in enumerate(errors):
            shot_id = f'shot_{session_id}_{i}'
            cursor.execute('''
                INSERT INTO shots (shot_id, session_id, club, carry)
                VALUES (?, ?, ?, ?)
            ''', (shot_id, session_id, 'Driver', 250.0))

            cursor.execute('''
                INSERT INTO model_predictions (
                    shot_id, club, predicted_value, actual_value, absolute_error, model_version
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (shot_id, 'Driver', 250.0, 250.0 - error, error, 'v1.0'))

        conn.commit()
        conn.close()

    def _insert_performance_record(self, session_id, session_mae, has_drift=0):
        """Helper to insert model_performance record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, baseline_mae, has_drift, recommendation
            ) VALUES (?, ?, ?, ?, ?)
        ''', (session_id, session_mae, 8.0, has_drift, 'Test'))
        conn.commit()
        conn.close()

    def test_check_session_drift_insufficient_predictions(self):
        """Test that sessions with <5 predictions return has_drift=False."""
        detector = DriftDetector(db_path=self.db_path)

        # Insert only 3 predictions
        self._insert_predictions('session_001', [5.0, 6.0, 7.0])

        result = detector.check_session_drift('session_001')

        self.assertFalse(result['has_drift'])
        self.assertIn('Need at least', result['message'])

    def test_check_session_drift_building_baseline(self):
        """Test that sessions during baseline building return has_drift=False."""
        detector = DriftDetector(db_path=self.db_path)

        # Insert sufficient predictions for this session
        self._insert_predictions('session_001', [5.0, 6.0, 7.0, 8.0, 9.0])

        # But no baseline sessions exist yet
        result = detector.check_session_drift('session_001')

        self.assertFalse(result['has_drift'])
        self.assertIn('Building baseline', result['message'])

    def test_check_session_drift_no_drift(self):
        """Test that sessions within threshold return has_drift=False."""
        detector = DriftDetector(db_path=self.db_path, drift_threshold_pct=0.30)

        # Insert 15 baseline sessions with MAE=8
        for i in range(15):
            self._insert_performance_record(f'baseline_{i}', 8.0)

        # Insert session with MAE=9 (12.5% above baseline, below 30% threshold)
        self._insert_predictions('session_test', [9.0, 9.0, 9.0, 9.0, 9.0])

        result = detector.check_session_drift('session_test')

        self.assertFalse(result['has_drift'])
        self.assertAlmostEqual(result['session_mae'], 9.0, places=1)
        self.assertAlmostEqual(result['baseline_mae'], 8.0, places=1)

    def test_check_session_drift_detects_drift(self):
        """Test that sessions exceeding threshold return has_drift=True."""
        detector = DriftDetector(db_path=self.db_path, drift_threshold_pct=0.30)

        # Insert 15 baseline sessions with MAE=8
        for i in range(15):
            self._insert_performance_record(f'baseline_{i}', 8.0)

        # Insert session with MAE=12 (50% above baseline, exceeds 30% threshold)
        self._insert_predictions('session_test', [12.0, 12.0, 12.0, 12.0, 12.0])

        result = detector.check_session_drift('session_test')

        self.assertTrue(result['has_drift'])
        self.assertGreater(result['drift_pct'], 0.30)
        self.assertIn('recommendation', result)

    def test_consecutive_drift_counting(self):
        """Test that consecutive drift sessions are counted correctly."""
        detector = DriftDetector(db_path=self.db_path)

        # Insert 3 drift records
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute('''
                INSERT INTO model_performance (
                    session_id, session_mae, has_drift, recommendation
                ) VALUES (?, ?, ?, ?)
            ''', (f'drift_{i}', 12.0, 1, 'Test'))
        conn.commit()
        conn.close()

        count = detector.get_consecutive_drift_count()
        self.assertEqual(count, 3)

    def test_consecutive_drift_resets_on_clean_session(self):
        """Test that consecutive drift count resets after clean session."""
        detector = DriftDetector(db_path=self.db_path)

        # Insert records: drift, drift, clean, drift
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Oldest first (will be reversed in query)
        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        ''', ('drift_1', 12.0, 1, 'Test', datetime.now() - timedelta(hours=3)))

        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        ''', ('drift_2', 12.0, 1, 'Test', datetime.now() - timedelta(hours=2)))

        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        ''', ('clean_1', 8.0, 0, 'OK', datetime.now() - timedelta(hours=1)))

        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?)
        ''', ('drift_3', 12.0, 1, 'Test', datetime.now()))

        conn.commit()
        conn.close()

        # Should only count most recent consecutive drift (after the clean session)
        count = detector.get_consecutive_drift_count()
        self.assertEqual(count, 1)

    def test_recommendation_urgent_at_three_consecutive(self):
        """Test that 3+ consecutive drift sessions trigger urgent recommendation."""
        detector = DriftDetector(db_path=self.db_path, drift_threshold_pct=0.30)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert 15 baseline sessions with older timestamps
        for i in range(15):
            cursor.execute('''
                INSERT INTO model_performance (
                    session_id, session_mae, baseline_mae, has_drift, recommendation, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (f'baseline_{i}', 8.0, 8.0, 0, 'OK', datetime.now() - timedelta(days=i+3)))

        # Insert 2 consecutive drift sessions (most recent before current test)
        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, baseline_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('drift_1', 12.0, 8.0, 1, 'Monitor', datetime.now() - timedelta(hours=2)))
        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, baseline_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('drift_2', 12.0, 8.0, 1, 'Monitor', datetime.now() - timedelta(hours=1)))
        conn.commit()
        conn.close()

        # Insert 3rd drift session (should trigger URGENT)
        self._insert_predictions('session_test', [12.0, 12.0, 12.0, 12.0, 12.0])

        result = detector.check_session_drift('session_test')

        self.assertTrue(result['has_drift'])
        self.assertEqual(result['consecutive_drift_sessions'], 3)
        self.assertIn('URGENT', result['recommendation'])

    def test_check_and_trigger_retraining_alert_only(self):
        """Test that check_and_trigger_retraining with auto_retrain=False only alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert 15 baseline sessions with older timestamps
        for i in range(15):
            cursor.execute('''
                INSERT INTO model_performance (
                    session_id, session_mae, baseline_mae, has_drift, recommendation, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (f'baseline_{i}', 8.0, 8.0, 0, 'OK', datetime.now() - timedelta(days=i+3)))

        # Insert 2 consecutive drift sessions (most recent before current test)
        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, baseline_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('drift_1', 12.0, 8.0, 1, 'Monitor', datetime.now() - timedelta(hours=2)))
        cursor.execute('''
            INSERT INTO model_performance (
                session_id, session_mae, baseline_mae, has_drift, recommendation, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('drift_2', 12.0, 8.0, 1, 'Monitor', datetime.now() - timedelta(hours=1)))
        conn.commit()
        conn.close()

        # Insert drift session that will trigger recommendation (3rd consecutive)
        self._insert_predictions('session_test', [12.0, 12.0, 12.0, 12.0, 12.0])

        result = check_and_trigger_retraining('session_test', auto_retrain=False, db_path=self.db_path)

        self.assertIsNotNone(result)
        self.assertTrue(result.get('has_drift'))
        self.assertTrue(result.get('retraining_recommended', False))
        self.assertNotIn('retraining_triggered', result)


if __name__ == '__main__':
    unittest.main()
