"""
Data Service

Unified interface for all data operations.
Provides high-level business logic for shot and session management.
"""

from typing import Dict, List, Optional, Any
import pandas as pd

from .base_service import BaseService
from repositories.shot_repository import ShotRepository


class DataService(BaseService):
    """
    Service for unified data operations across all storage backends.

    This service provides a clean interface for the application to interact
    with golf shot data without needing to know about the underlying
    database implementations (SQLite, Supabase, BigQuery).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize data service.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.shot_repo = ShotRepository()
        self._log_info("DataService initialized")

    def save_shot(self, shot_data: Dict[str, Any]) -> str:
        """
        Save shot to all configured backends.

        Args:
            shot_data: Shot data dictionary with required fields:
                      - shot_id or id: Unique shot identifier
                      - session_id or session: Session identifier
                      - club: Club name
                      - Other golf metrics...

        Returns:
            Shot ID

        Raises:
            ValueError: If required fields are missing
        """
        with self._track_performance("save_shot"):
            try:
                shot_id = self.shot_repo.save(shot_data)
                self._log_info(
                    "Shot saved successfully",
                    shot_id=shot_id,
                    club=shot_data.get('club')
                )
                return shot_id

            except Exception as e:
                self._handle_error(e, "saving shot", raise_error=True)

    def get_shot(self, shot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get shot by ID.

        Args:
            shot_id: Shot ID

        Returns:
            Shot dictionary if found, None otherwise
        """
        with self._track_performance("get_shot"):
            try:
                shot = self.shot_repo.find_by_id(shot_id)
                if shot:
                    self._log_debug("Shot retrieved", shot_id=shot_id)
                else:
                    self._log_warning("Shot not found", shot_id=shot_id)
                return shot

            except Exception as e:
                self._handle_error(e, "retrieving shot", raise_error=False)
                return None

    def get_shots(
        self,
        session_id: Optional[str] = None,
        club: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve shots with optional filtering.

        Args:
            session_id: Optional session ID filter
            club: Optional club name filter
            filters: Optional additional filters

        Returns:
            List of shot dictionaries
        """
        with self._track_performance("get_shots"):
            try:
                # Build filter dictionary
                query_filters = filters or {}
                if session_id:
                    query_filters['session_id'] = session_id
                if club:
                    query_filters['club'] = club

                shots = self.shot_repo.find_all(query_filters)
                self._log_info(
                    "Shots retrieved",
                    count=len(shots),
                    session_id=session_id,
                    club=club
                )
                return shots

            except Exception as e:
                self._handle_error(e, "retrieving shots", raise_error=False)
                return []

    def get_all_shots(self) -> pd.DataFrame:
        """
        Get all shots as DataFrame.

        Returns:
            DataFrame with all shots
        """
        with self._track_performance("get_all_shots"):
            try:
                shots = self.shot_repo.find_all()
                df = pd.DataFrame(shots)
                self._log_info("All shots retrieved", count=len(df))
                return df

            except Exception as e:
                self._handle_error(e, "retrieving all shots", raise_error=False)
                return pd.DataFrame()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete session with all shots.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session metadata and shots
        """
        with self._track_performance("get_session"):
            try:
                shots = self.shot_repo.find_by_session(session_id)

                if not shots:
                    self._log_warning("Session not found", session_id=session_id)
                    return {
                        'session_id': session_id,
                        'shots': [],
                        'shot_count': 0
                    }

                # Calculate session summary
                session_data = {
                    'session_id': session_id,
                    'shots': shots,
                    'shot_count': len(shots),
                    'session_date': shots[0].get('session_date'),
                    'date_added': shots[0].get('date_added'),
                    'clubs': list(set(shot['club'] for shot in shots if shot.get('club')))
                }

                self._log_info("Session retrieved", session_id=session_id, shot_count=len(shots))
                return session_data

            except Exception as e:
                self._handle_error(e, "retrieving session", raise_error=False)
                return {'session_id': session_id, 'shots': [], 'shot_count': 0}

    def get_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions with metadata.

        Returns:
            List of session dictionaries
        """
        with self._track_performance("get_sessions"):
            try:
                sessions = self.shot_repo.get_unique_sessions()
                self._log_info("Sessions retrieved", count=len(sessions))
                return sessions

            except Exception as e:
                self._handle_error(e, "retrieving sessions", raise_error=False)
                return []

    def delete_shot(self, shot_id: str) -> bool:
        """
        Delete shot from all backends.

        Args:
            shot_id: Shot ID

        Returns:
            True if deletion successful
        """
        with self._track_performance("delete_shot"):
            try:
                success = self.shot_repo.delete(shot_id)
                if success:
                    self._log_info("Shot deleted", shot_id=shot_id)
                else:
                    self._log_warning("Shot deletion failed", shot_id=shot_id)
                return success

            except Exception as e:
                self._handle_error(e, "deleting shot", raise_error=False)
                return False

    def update_club_name(
        self,
        session_id: str,
        old_name: str,
        new_name: str
    ) -> int:
        """
        Rename club across all shots in a session.

        Args:
            session_id: Session ID
            old_name: Old club name
            new_name: New club name

        Returns:
            Number of shots updated
        """
        with self._track_performance("update_club_name"):
            try:
                count = self.shot_repo.rename_club(session_id, old_name, new_name)
                self._log_info(
                    "Club renamed",
                    session_id=session_id,
                    old_name=old_name,
                    new_name=new_name,
                    count=count
                )
                return count

            except Exception as e:
                self._handle_error(e, "renaming club", raise_error=False)
                return 0

    def delete_club_shots(self, session_id: str, club: str) -> int:
        """
        Delete all shots for a specific club in a session.

        Args:
            session_id: Session ID
            club: Club name

        Returns:
            Number of shots deleted
        """
        with self._track_performance("delete_club_shots"):
            try:
                count = self.shot_repo.delete_by_session_and_club(session_id, club)
                self._log_info(
                    "Club shots deleted",
                    session_id=session_id,
                    club=club,
                    count=count
                )
                return count

            except Exception as e:
                self._handle_error(e, "deleting club shots", raise_error=False)
                return 0

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistical summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session statistics
        """
        with self._track_performance("get_session_summary"):
            try:
                shots = self.shot_repo.find_by_session(session_id)
                if not shots:
                    return {'session_id': session_id, 'shot_count': 0}

                df = pd.DataFrame(shots)

                # Calculate statistics by club
                club_stats = {}
                for club in df['club'].unique():
                    club_df = df[df['club'] == club]
                    club_stats[club] = {
                        'shot_count': len(club_df),
                        'avg_carry': club_df['carry'].mean() if 'carry' in club_df else 0,
                        'avg_total': club_df['total'].mean() if 'total' in club_df else 0,
                        'avg_ball_speed': club_df['ball_speed'].mean() if 'ball_speed' in club_df else 0,
                        'avg_smash': club_df['smash'].mean() if 'smash' in club_df else 0
                    }

                summary = {
                    'session_id': session_id,
                    'shot_count': len(shots),
                    'session_date': shots[0].get('session_date'),
                    'clubs': list(df['club'].unique()),
                    'club_stats': club_stats
                }

                self._log_info("Session summary generated", session_id=session_id)
                return summary

            except Exception as e:
                self._handle_error(e, "generating session summary", raise_error=False)
                return {'session_id': session_id, 'shot_count': 0}

    def get_club_statistics(self, club: str) -> Dict[str, Any]:
        """
        Get statistics for a specific club across all sessions.

        Args:
            club: Club name

        Returns:
            Dictionary with club statistics
        """
        with self._track_performance("get_club_statistics"):
            try:
                shots = self.shot_repo.find_all({'club': club})
                if not shots:
                    return {'club': club, 'shot_count': 0}

                df = pd.DataFrame(shots)

                stats = {
                    'club': club,
                    'shot_count': len(df),
                    'avg_carry': df['carry'].mean() if 'carry' in df else 0,
                    'avg_total': df['total'].mean() if 'total' in df else 0,
                    'avg_ball_speed': df['ball_speed'].mean() if 'ball_speed' in df else 0,
                    'avg_club_speed': df['club_speed'].mean() if 'club_speed' in df else 0,
                    'avg_smash': df['smash'].mean() if 'smash' in df else 0,
                    'avg_launch_angle': df['launch_angle'].mean() if 'launch_angle' in df else 0,
                    'std_carry': df['carry'].std() if 'carry' in df else 0
                }

                self._log_info("Club statistics generated", club=club, shot_count=len(df))
                return stats

            except Exception as e:
                self._handle_error(e, "generating club statistics", raise_error=False)
                return {'club': club, 'shot_count': 0}

    def bulk_import(self, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Import multiple shots in bulk.

        Args:
            shots: List of shot dictionaries

        Returns:
            Dictionary with import results
        """
        with self._track_performance("bulk_import"):
            imported = 0
            errors = []

            for shot in shots:
                try:
                    self.shot_repo.save(shot)
                    imported += 1
                except Exception as e:
                    errors.append({
                        'shot_id': shot.get('shot_id', shot.get('id')),
                        'error': str(e)
                    })
                    self._log_error("Failed to import shot", e, shot_id=shot.get('shot_id'))

            result = {
                'total': len(shots),
                'imported': imported,
                'failed': len(errors),
                'errors': errors
            }

            self._log_info(
                "Bulk import completed",
                total=len(shots),
                imported=imported,
                failed=len(errors)
            )

            return result

    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get overall data summary.

        Returns:
            Dictionary with database statistics
        """
        with self._track_performance("get_data_summary"):
            try:
                shots = self.shot_repo.find_all()
                sessions = self.shot_repo.get_unique_sessions()

                if not shots:
                    return {
                        'total_shots': 0,
                        'total_sessions': 0,
                        'clubs': []
                    }

                df = pd.DataFrame(shots)

                summary = {
                    'total_shots': len(df),
                    'total_sessions': len(sessions),
                    'clubs': list(df['club'].unique()),
                    'date_range': {
                        'earliest': df['session_date'].min() if 'session_date' in df else None,
                        'latest': df['session_date'].max() if 'session_date' in df else None
                    }
                }

                self._log_info("Data summary generated", total_shots=len(df))
                return summary

            except Exception as e:
                self._handle_error(e, "generating data summary", raise_error=False)
                return {'total_shots': 0, 'total_sessions': 0, 'clubs': []}
