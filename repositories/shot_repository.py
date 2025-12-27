"""
Shot Repository - Firestore Implementation

Handles shot data access across SQLite (local) and Firestore (cloud).
Implements the Repository pattern for shot-related database operations.

Architecture:
- SQLite: Local-first for offline access and fast queries
- Firestore: Cloud primary database with real-time sync
- BigQuery: Auto-synced from Firestore via Cloud Functions
"""

import sqlite3
import os
import pandas as pd
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.api_core import exceptions as google_exceptions
from datetime import datetime

from .base_repository import SyncBaseRepository


class ShotRepository(SyncBaseRepository):
    """
    Repository for shot data with dual-backend support (SQLite + Firestore).

    Provides CRUD operations for golf shot data with automatic
    syncing between local SQLite and cloud Firestore databases.
    """

    def __init__(self, project_id: str = None):
        """
        Initialize shot repository with database connections.

        Args:
            project_id: GCP project ID (defaults to env var)
        """
        super().__init__()

        # SQLite setup (local-first)
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        if os.path.exists(self.data_dir):
            self.db_path = os.path.join(self.data_dir, "golf_stats.db")
        else:
            self.db_path = os.path.join(os.path.dirname(__file__), "..", "golf_stats.db")

        # Firestore setup (cloud primary)
        try:
            if project_id:
                self.firestore_db = firestore.Client(project=project_id)
            else:
                # Uses GOOGLE_APPLICATION_CREDENTIALS env var
                self.firestore_db = firestore.Client()

            self.cloud_enabled = True
            self.logger.info("Firestore connection established")
        except Exception as e:
            self.firestore_db = None
            self.cloud_enabled = False
            self.logger.warning(f"Firestore not available: {e}. Running in local-only mode.")

        # Firestore collection reference
        self.shots_collection = "shots" if self.cloud_enabled else None

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with proper schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shots (
                shot_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_date TEXT,
                club TEXT,
                carry REAL,
                total REAL,
                smash REAL,
                club_path REAL,
                face_angle REAL,
                ball_speed REAL,
                club_speed REAL,
                side_spin INTEGER,
                back_spin INTEGER,
                launch_angle REAL,
                side_angle REAL,
                dynamic_loft REAL,
                attack_angle REAL,
                impact_x REAL,
                impact_y REAL,
                side_distance REAL,
                descent_angle REAL,
                apex REAL,
                flight_time REAL,
                shot_type TEXT,
                impact_img TEXT,
                swing_img TEXT,
                video_frames TEXT,
                optix_x REAL,
                optix_y REAL,
                club_lie REAL,
                lie_angle TEXT
            )
        ''')

        # Handle migrations
        cursor.execute("PRAGMA table_info(shots)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        required_columns = {
            'session_date': 'TEXT',
            'video_frames': 'TEXT',
            'optix_x': 'REAL',
            'optix_y': 'REAL',
            'club_lie': 'REAL',
            'lie_angle': 'TEXT',
            # NEW COLUMNS (Dec 2024 expansion)
            'sensor_name': 'TEXT',
            'client_shot_id': 'TEXT',
            'server_timestamp': 'TEXT',
            'is_deleted': 'TEXT',
            'ball_name': 'TEXT',
            'ball_type': 'TEXT',
            'club_name_std': 'TEXT',
            'club_type': 'TEXT',
            'client_session_id': 'TEXT',
            'low_point': 'REAL'
        }

        for col, col_type in required_columns.items():
            if col not in existing_columns:
                self.logger.info(f"Migrating: Adding column {col} to SQLite")
                cursor.execute(f"ALTER TABLE shots ADD COLUMN {col} {col_type}")

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shots_session_id ON shots(session_id)')

        conn.commit()
        conn.close()

    def _clean_value(self, val: Any, default: float = 0.0) -> Any:
        """
        Handle sentinel values (99999) and None.

        Args:
            val: Value to clean
            default: Default value for None/sentinel

        Returns:
            Cleaned value
        """
        if val is None or val == 99999:
            return default
        return val

    def find_by_id(self, shot_id: str) -> Optional[Dict[str, Any]]:
        """
        Find shot by ID.

        Args:
            shot_id: Shot ID

        Returns:
            Shot dictionary if found, None otherwise
        """
        try:
            # Try Firestore first (most up-to-date)
            if self.cloud_enabled:
                doc = self.firestore_db.collection(self.shots_collection).document(shot_id).get()
                if doc.exists:
                    return doc.to_dict()

            # Fallback to SQLite
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shots WHERE shot_id = ?", (shot_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            self._log_error("Failed to find shot by ID", e, shot_id=shot_id)
            return None

    def find_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Find all shots matching filters.

        Args:
            filters: Optional filter criteria
                     Supported: session_id, club, date_range

        Returns:
            List of shot dictionaries
        """
        try:
            # Use SQLite for querying (faster for analytics)
            conn = sqlite3.connect(self.db_path)
            query = "SELECT * FROM shots"

            if filters:
                where_clause = self._build_filter_clause(filters)
                query += f" {where_clause}"

            df = pd.read_sql_query(query, conn)
            conn.close()

            return df.to_dict('records')

        except Exception as e:
            self._log_error("Failed to find shots", e, filters=filters)
            return []

    def save(self, shot_data: Dict[str, Any]) -> str:
        """
        Save shot to both SQLite and Firestore.

        Args:
            shot_data: Shot data dictionary

        Returns:
            Shot ID

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        self._validate_entity(shot_data, ['shot_id', 'session_id'])

        # Prepare payload
        payload = self._prepare_payload(shot_data)
        shot_id = payload['shot_id']

        # Save to local SQLite (local-first)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            columns = ', '.join(payload.keys())
            placeholders = ', '.join(['?'] * len(payload))
            sql = f"INSERT OR REPLACE INTO shots ({columns}) VALUES ({placeholders})"
            cursor.execute(sql, list(payload.values()))
            conn.commit()
            conn.close()

            self._log_operation(
                "Saved shot to SQLite",
                shot_id=shot_id,
                session_id=payload['session_id']
            )

        except Exception as e:
            self._log_error("Failed to save shot to SQLite", e, shot_id=shot_id)
            raise

        # Save to Firestore (cloud)
        if self.cloud_enabled:
            try:
                # Add timestamp for Firestore
                firestore_payload = payload.copy()
                firestore_payload['updated_at'] = firestore.SERVER_TIMESTAMP

                # Use shot_id as document ID for easy lookups
                self.firestore_db.collection(self.shots_collection).document(shot_id).set(
                    firestore_payload,
                    merge=True  # Update if exists
                )

                self._log_operation("Saved shot to Firestore", shot_id=shot_id)

            except Exception as e:
                # Log but don't fail - local-first approach
                self._log_error("Failed to save shot to Firestore", e, shot_id=shot_id)

        return shot_id

    def update(self, shot_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update shot fields.

        Args:
            shot_id: Shot ID
            updates: Dictionary of fields to update

        Returns:
            True if update successful
        """
        try:
            # Update SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [shot_id]

            sql = f"UPDATE shots SET {set_clause} WHERE shot_id = ?"
            cursor.execute(sql, values)
            conn.commit()
            conn.close()

            self._log_operation("Updated shot in SQLite", shot_id=shot_id)

            # Update Firestore
            if self.cloud_enabled:
                try:
                    updates_with_timestamp = updates.copy()
                    updates_with_timestamp['updated_at'] = firestore.SERVER_TIMESTAMP

                    self.firestore_db.collection(self.shots_collection).document(shot_id).update(
                        updates_with_timestamp
                    )
                    self._log_operation("Updated shot in Firestore", shot_id=shot_id)
                except google_exceptions.NotFound:
                    self._log_error("Shot not found in Firestore", None, shot_id=shot_id)
                except Exception as e:
                    self._log_error("Failed to update shot in Firestore", e, shot_id=shot_id)

            return True

        except Exception as e:
            self._log_error("Failed to update shot", e, shot_id=shot_id)
            return False

    def delete(self, shot_id: str) -> bool:
        """
        Delete shot from both SQLite and Firestore.

        Args:
            shot_id: Shot ID

        Returns:
            True if deletion successful
        """
        try:
            # Delete from SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shots WHERE shot_id = ?", (shot_id,))
            conn.commit()
            conn.close()

            self._log_operation("Deleted shot from SQLite", shot_id=shot_id)

            # Delete from Firestore
            if self.cloud_enabled:
                try:
                    self.firestore_db.collection(self.shots_collection).document(shot_id).delete()
                    self._log_operation("Deleted shot from Firestore", shot_id=shot_id)
                except Exception as e:
                    self._log_error("Failed to delete shot from Firestore", e, shot_id=shot_id)

            return True

        except Exception as e:
            self._log_error("Failed to delete shot", e, shot_id=shot_id)
            return False

    def find_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all shots in a session.

        Args:
            session_id: Session ID

        Returns:
            List of shot dictionaries
        """
        return self.find_all({'session_id': session_id})

    def get_unique_sessions(self) -> List[Dict[str, Any]]:
        """
        Get unique sessions with metadata.

        Returns:
            List of session dictionaries with session_id, session_date, date_added
        """
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT DISTINCT
                    session_id,
                    MAX(session_date) as session_date,
                    MAX(date_added) as date_added,
                    MAX(club) as club,
                    COUNT(*) as shot_count
                FROM shots
                GROUP BY session_id
                ORDER BY COALESCE(session_date, date_added) DESC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()

            return df.to_dict('records')

        except Exception as e:
            self._log_error("Failed to get unique sessions", e)
            return []

    def rename_club(self, session_id: str, old_name: str, new_name: str) -> int:
        """
        Rename club in a session.

        Args:
            session_id: Session ID
            old_name: Old club name
            new_name: New club name

        Returns:
            Number of shots updated
        """
        try:
            # Update SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE shots SET club = ? WHERE session_id = ? AND club = ?",
                (new_name, session_id, old_name)
            )
            count = cursor.rowcount
            conn.commit()
            conn.close()

            self._log_operation(
                "Renamed club in SQLite",
                session_id=session_id,
                old_name=old_name,
                new_name=new_name,
                count=count
            )

            # Update Firestore (batch update)
            if self.cloud_enabled:
                try:
                    # Query shots to update
                    shots_ref = self.firestore_db.collection(self.shots_collection)
                    query = shots_ref.where('session_id', '==', session_id).where('club', '==', old_name)
                    docs = query.stream()

                    # Batch update
                    batch = self.firestore_db.batch()
                    for doc in docs:
                        batch.update(doc.reference, {
                            'club': new_name,
                            'updated_at': firestore.SERVER_TIMESTAMP
                        })
                    batch.commit()

                    self._log_operation("Renamed club in Firestore", session_id=session_id)
                except Exception as e:
                    self._log_error("Failed to rename club in Firestore", e, session_id=session_id)

            return count

        except Exception as e:
            self._log_error("Failed to rename club", e, session_id=session_id)
            return 0

    def delete_by_session_and_club(self, session_id: str, club: str) -> int:
        """
        Delete all shots for a specific club in a session.

        Args:
            session_id: Session ID
            club: Club name

        Returns:
            Number of shots deleted
        """
        try:
            # Delete from SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM shots WHERE session_id = ? AND club = ?",
                (session_id, club)
            )
            count = cursor.rowcount
            conn.commit()
            conn.close()

            self._log_operation(
                "Deleted shots from SQLite",
                session_id=session_id,
                club=club,
                count=count
            )

            # Delete from Firestore (batch delete)
            if self.cloud_enabled:
                try:
                    shots_ref = self.firestore_db.collection(self.shots_collection)
                    query = shots_ref.where('session_id', '==', session_id).where('club', '==', club)
                    docs = query.stream()

                    batch = self.firestore_db.batch()
                    for doc in docs:
                        batch.delete(doc.reference)
                    batch.commit()

                    self._log_operation("Deleted shots from Firestore", session_id=session_id, club=club)
                except Exception as e:
                    self._log_error("Failed to delete shots from Firestore", e, session_id=session_id)

            return count

        except Exception as e:
            self._log_error("Failed to delete shots", e, session_id=session_id, club=club)
            return 0

    def sync_to_firestore(self, shot_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Sync SQLite data to Firestore (useful for migration or recovery).

        Args:
            shot_ids: Optional list of specific shot IDs to sync. If None, sync all.

        Returns:
            Dictionary with sync statistics
        """
        if not self.cloud_enabled:
            self.logger.warning("Firestore not enabled, cannot sync")
            return {'synced': 0, 'errors': 0}

        try:
            conn = sqlite3.connect(self.db_path)

            if shot_ids:
                placeholders = ','.join('?' * len(shot_ids))
                query = f"SELECT * FROM shots WHERE shot_id IN ({placeholders})"
                df = pd.read_sql_query(query, conn, params=shot_ids)
            else:
                df = pd.read_sql_query("SELECT * FROM shots", conn)

            conn.close()

            synced = 0
            errors = 0
            batch = self.firestore_db.batch()
            batch_count = 0

            for _, row in df.iterrows():
                try:
                    shot_data = row.to_dict()
                    shot_id = shot_data['shot_id']

                    # Add Firestore timestamp
                    shot_data['updated_at'] = firestore.SERVER_TIMESTAMP

                    doc_ref = self.firestore_db.collection(self.shots_collection).document(shot_id)
                    batch.set(doc_ref, shot_data, merge=True)

                    batch_count += 1
                    synced += 1

                    # Commit batch every 500 documents (Firestore limit)
                    if batch_count >= 500:
                        batch.commit()
                        batch = self.firestore_db.batch()
                        batch_count = 0

                except Exception as e:
                    self._log_error("Failed to sync shot", e, shot_id=shot_data.get('shot_id'))
                    errors += 1

            # Commit remaining batch
            if batch_count > 0:
                batch.commit()

            self._log_operation("Sync to Firestore completed", synced=synced, errors=errors)
            return {'synced': synced, 'errors': errors}

        except Exception as e:
            self._log_error("Failed to sync to Firestore", e)
            return {'synced': 0, 'errors': 1}

    def _prepare_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare shot data payload for database insertion.

        Args:
            data: Raw shot data

        Returns:
            Cleaned payload dictionary
        """
        return {
            'shot_id': data.get('id', data.get('shot_id')),
            'session_id': data.get('session', data.get('session_id')),
            'session_date': data.get('session_date'),
            'club': data.get('club'),
            'carry': self._clean_value(data.get('carry', data.get('carry_distance'))),
            'total': self._clean_value(data.get('total', data.get('total_distance'))),
            'smash': self._clean_value(data.get('smash', 0.0)),
            'club_path': self._clean_value(data.get('club_path')),
            'face_angle': self._clean_value(data.get('face_angle', data.get('club_face_angle'))),
            'ball_speed': self._clean_value(data.get('ball_speed')),
            'club_speed': self._clean_value(data.get('club_speed')),
            'side_spin': self._clean_value(data.get('side_spin'), 0),
            'back_spin': self._clean_value(data.get('back_spin'), 0),
            'launch_angle': self._clean_value(data.get('launch_angle')),
            'side_angle': self._clean_value(data.get('side_angle')),
            'dynamic_loft': self._clean_value(data.get('dynamic_loft')),
            'attack_angle': self._clean_value(data.get('attack_angle')),
            'impact_x': self._clean_value(data.get('impact_x')),
            'impact_y': self._clean_value(data.get('impact_y')),
            'side_distance': self._clean_value(data.get('side_distance')),
            'descent_angle': self._clean_value(data.get('descent_angle', data.get('decent_angle'))),
            'apex': self._clean_value(data.get('apex')),
            'flight_time': self._clean_value(data.get('flight_time')),
            'shot_type': data.get('shot_type', data.get('type')),
            'impact_img': data.get('impact_img'),
            'swing_img': data.get('swing_img'),
            'video_frames': data.get('video_frames'),
            'optix_x': self._clean_value(data.get('optix_x')),
            'optix_y': self._clean_value(data.get('optix_y')),
            'club_lie': self._clean_value(data.get('club_lie')),
            'lie_angle': data.get('lie_angle') if data.get('lie_angle') else None,
            # NEW: Additional metrics (Dec 2024 expansion)
            'sensor_name': data.get('sensor_name'),
            'client_shot_id': data.get('client_shot_id'),
            'server_timestamp': data.get('server_timestamp'),
            'is_deleted': data.get('is_deleted', 'N'),
            'ball_name': data.get('ball_name'),
            'ball_type': data.get('ball_type'),
            'club_name_std': data.get('club_name_std'),
            'club_type': data.get('club_type'),
            'client_session_id': data.get('client_session_id'),
            'low_point': self._clean_value(data.get('low_point'))
        }
