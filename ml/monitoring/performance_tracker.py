"""
Performance tracker for ML model predictions.

Logs individual predictions and computes session-level metrics for monitoring.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceTracker:
    """
    Track ML model predictions for monitoring and analysis.

    Logs individual predictions to model_predictions table and provides
    methods to retrieve prediction history.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize tracker.

        Args:
            db_path: Path to SQLite database. Defaults to golf_db.SQLITE_DB_PATH.
        """
        if db_path is None:
            import golf_db
            db_path = golf_db.SQLITE_DB_PATH
        self.db_path = db_path

    def log_prediction(
        self,
        shot_id: str,
        club: str,
        predicted_carry: float,
        actual_carry: float,
        model_version: str
    ) -> None:
        """
        Log a single prediction to the database.

        Args:
            shot_id: Shot identifier
            club: Club used
            predicted_carry: Predicted carry distance
            actual_carry: Actual carry distance
            model_version: Model version string

        Returns:
            None. Logs errors but does not raise exceptions (non-blocking).
        """
        # Skip sentinel values
        if actual_carry is None or actual_carry == 0 or actual_carry == 99999:
            logger.debug(f"Skipping prediction logging for shot {shot_id}: invalid actual_carry={actual_carry}")
            return

        try:
            absolute_error = abs(predicted_carry - actual_carry)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO model_predictions (
                    shot_id, club, predicted_value, actual_value,
                    absolute_error, model_version
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (shot_id, club, predicted_carry, actual_carry, absolute_error, model_version))

            conn.commit()
            conn.close()

            logger.debug(f"Logged prediction for shot {shot_id}: pred={predicted_carry:.1f}, actual={actual_carry:.1f}, error={absolute_error:.1f}")

        except sqlite3.Error as e:
            logger.error(f"Failed to log prediction for shot {shot_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error logging prediction for shot {shot_id}: {e}")

    def get_session_predictions(self, session_id: str) -> pd.DataFrame:
        """
        Get all predictions for a session.

        Args:
            session_id: Session identifier

        Returns:
            DataFrame with prediction records
        """
        try:
            conn = sqlite3.connect(self.db_path)

            query = '''
                SELECT
                    p.id,
                    p.shot_id,
                    p.club,
                    p.predicted_value,
                    p.actual_value,
                    p.absolute_error,
                    p.model_version,
                    p.timestamp,
                    s.session_id
                FROM model_predictions p
                JOIN shots s ON p.shot_id = s.shot_id
                WHERE s.session_id = ?
                ORDER BY p.timestamp
            '''

            df = pd.read_sql_query(query, conn, params=(session_id,))
            conn.close()

            return df

        except sqlite3.Error as e:
            logger.error(f"Failed to get session predictions for {session_id}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Unexpected error getting session predictions for {session_id}: {e}")
            return pd.DataFrame()

    def get_prediction_history(self, limit: int = 50) -> pd.DataFrame:
        """
        Get recent prediction history across all sessions.

        Args:
            limit: Maximum number of records to return

        Returns:
            DataFrame with recent prediction records
        """
        try:
            conn = sqlite3.connect(self.db_path)

            query = '''
                SELECT
                    p.id,
                    p.shot_id,
                    p.club,
                    p.predicted_value,
                    p.actual_value,
                    p.absolute_error,
                    p.model_version,
                    p.timestamp,
                    s.session_id
                FROM model_predictions p
                JOIN shots s ON p.shot_id = s.shot_id
                ORDER BY p.timestamp DESC
                LIMIT ?
            '''

            df = pd.read_sql_query(query, conn, params=(limit,))
            conn.close()

            return df

        except sqlite3.Error as e:
            logger.error(f"Failed to get prediction history: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Unexpected error getting prediction history: {e}")
            return pd.DataFrame()
