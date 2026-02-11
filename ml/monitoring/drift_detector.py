"""
Drift detector for ML model performance.

Uses adaptive thresholds and statistical baselines to detect when model
performance degrades beyond expected ranges.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Optional, Dict
from utils.logging_config import get_logger

logger = get_logger(__name__)


class DriftDetector:
    """
    Detect model drift using adaptive baselines.

    Uses rolling median of session MAE as baseline and flags sessions
    that exceed threshold. Tracks consecutive drift sessions for
    retraining recommendations.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        drift_threshold_pct: float = 0.30,
        min_predictions: int = 5,
        baseline_sessions: int = 20,
        min_baseline_sessions: int = 10
    ):
        """
        Initialize drift detector.

        Args:
            db_path: Path to SQLite database. Defaults to golf_db.SQLITE_DB_PATH.
            drift_threshold_pct: Percentage above baseline to flag drift (default 30%)
            min_predictions: Minimum predictions required per session (default 5)
            baseline_sessions: Number of sessions to use for baseline (default 20)
            min_baseline_sessions: Minimum sessions needed for baseline (default 10)
        """
        if db_path is None:
            import golf_db
            db_path = golf_db.SQLITE_DB_PATH
        self.db_path = db_path
        self.drift_threshold_pct = drift_threshold_pct
        self.min_predictions = min_predictions
        self.baseline_sessions = baseline_sessions
        self.min_baseline_sessions = min_baseline_sessions

    def check_session_drift(self, session_id: str) -> Dict:
        """
        Check if a session shows model drift.

        Computes session MAE, compares to adaptive baseline, and stores result.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with:
                - has_drift (bool): Whether drift was detected
                - session_mae (float): Session MAE
                - baseline_mae (float): Baseline MAE (if available)
                - drift_pct (float): Percentage above baseline (if available)
                - consecutive_drift_sessions (int): Count of consecutive drift
                - recommendation (str): Action recommendation
                - message (str): Human-readable status message
        """
        try:
            # Get predictions for this session
            conn = sqlite3.connect(self.db_path)

            query = '''
                SELECT
                    p.absolute_error,
                    s.session_id
                FROM model_predictions p
                JOIN shots s ON p.shot_id = s.shot_id
                WHERE s.session_id = ?
            '''
            cursor = conn.cursor()
            cursor.execute(query, (session_id,))
            rows = cursor.fetchall()

            # Check minimum predictions
            if len(rows) < self.min_predictions:
                conn.close()
                return {
                    'has_drift': False,
                    'message': f'Need at least {self.min_predictions} predictions (have {len(rows)})'
                }

            # Compute session MAE
            errors = [r[0] for r in rows]
            session_mae = np.mean(errors)

            # Get baseline MAE (median of last N sessions)
            baseline_query = '''
                SELECT session_mae
                FROM model_performance
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            cursor.execute(baseline_query, (self.baseline_sessions,))
            baseline_rows = cursor.fetchall()

            # Check if we have enough baseline data
            if len(baseline_rows) < self.min_baseline_sessions:
                # Store the record but don't flag drift yet
                cursor.execute('''
                    INSERT INTO model_performance (
                        session_id, session_mae, has_drift, recommendation
                    ) VALUES (?, ?, 0, ?)
                ''', (session_id, session_mae, 'Building baseline'))

                conn.commit()
                conn.close()

                return {
                    'has_drift': False,
                    'session_mae': session_mae,
                    'message': f'Building baseline (need {self.min_baseline_sessions}+ sessions, have {len(baseline_rows)})'
                }

            # Compute baseline (median for robustness)
            baseline_mae = np.median([r[0] for r in baseline_rows])

            # Compute drift percentage
            drift_pct = (session_mae - baseline_mae) / baseline_mae

            # Determine drift status
            has_drift = drift_pct > self.drift_threshold_pct

            # Count consecutive drift sessions
            consecutive_drift = self._count_consecutive_drift(cursor)
            if has_drift:
                consecutive_drift += 1  # Include this session

            # Generate recommendation
            if consecutive_drift >= 3:
                recommendation = "URGENT: Retrain model"
            elif has_drift:
                recommendation = "Monitor closely"
            else:
                recommendation = "Model performing within expected range"

            # Get model version from most recent prediction
            cursor.execute('''
                SELECT p.model_version
                FROM model_predictions p
                JOIN shots s ON p.shot_id = s.shot_id
                WHERE s.session_id = ?
                ORDER BY p.timestamp DESC
                LIMIT 1
            ''', (session_id,))
            version_row = cursor.fetchone()
            model_version = version_row[0] if version_row else None

            # Store performance record
            cursor.execute('''
                INSERT INTO model_performance (
                    session_id, session_mae, baseline_mae, has_drift,
                    drift_pct, consecutive_drift, model_version, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, session_mae, baseline_mae, int(has_drift),
                drift_pct, consecutive_drift, model_version, recommendation
            ))

            conn.commit()
            conn.close()

            logger.info(f"Drift check for {session_id}: MAE={session_mae:.2f}, baseline={baseline_mae:.2f}, drift={drift_pct:.1%}, consecutive={consecutive_drift}")

            return {
                'has_drift': has_drift,
                'session_mae': session_mae,
                'baseline_mae': baseline_mae,
                'drift_pct': drift_pct,
                'consecutive_drift_sessions': consecutive_drift,
                'recommendation': recommendation,
                'message': f'Session MAE {session_mae:.2f} vs baseline {baseline_mae:.2f} ({drift_pct:+.1%})'
            }

        except sqlite3.Error as e:
            logger.error(f"Database error checking drift for {session_id}: {e}")
            return {
                'has_drift': False,
                'message': f'Database error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error checking drift for {session_id}: {e}")
            return {
                'has_drift': False,
                'message': f'Error: {str(e)}'
            }

    def _count_consecutive_drift(self, cursor) -> int:
        """
        Count consecutive drift sessions from most recent records.

        Args:
            cursor: Active database cursor

        Returns:
            Count of consecutive drift sessions
        """
        try:
            cursor.execute('''
                SELECT has_drift
                FROM model_performance
                ORDER BY timestamp DESC
                LIMIT 10
            ''')
            rows = cursor.fetchall()

            consecutive = 0
            for row in rows:
                if row[0] == 1:  # has_drift is INTEGER (SQLite boolean)
                    consecutive += 1
                else:
                    break

            return consecutive

        except Exception as e:
            logger.error(f"Error counting consecutive drift: {e}")
            return 0

    def get_drift_history(self, limit: int = 50) -> pd.DataFrame:
        """
        Get recent drift detection history.

        Args:
            limit: Maximum number of records to return

        Returns:
            DataFrame with drift history
        """
        try:
            conn = sqlite3.connect(self.db_path)

            query = '''
                SELECT
                    id,
                    session_id,
                    session_mae,
                    baseline_mae,
                    has_drift,
                    drift_pct,
                    consecutive_drift,
                    model_version,
                    recommendation,
                    timestamp
                FROM model_performance
                ORDER BY timestamp DESC
                LIMIT ?
            '''

            df = pd.read_sql_query(query, conn, params=(limit,))
            conn.close()

            return df

        except sqlite3.Error as e:
            logger.error(f"Failed to get drift history: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Unexpected error getting drift history: {e}")
            return pd.DataFrame()

    def get_consecutive_drift_count(self) -> int:
        """
        Get count of consecutive drift sessions from most recent.

        Returns:
            Number of consecutive drift sessions
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            count = self._count_consecutive_drift(cursor)

            conn.close()
            return count

        except Exception as e:
            logger.error(f"Error getting consecutive drift count: {e}")
            return 0
