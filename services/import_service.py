"""
Import Service

Orchestrates the complete shot import workflow:
1. Fetch data from Uneekor API
2. Process media with caching
3. Save to databases

This service coordinates between the scraper, MediaService, and DataService.
"""

from typing import Dict, List, Callable, Optional
import re
import requests

from .base_service import BaseService
from .data_service import DataService
from .media_service import MediaService


class ImportService(BaseService):
    """
    Service for orchestrating shot import workflow.

    Coordinates scraping, media processing, and data storage
    for golf shot imports from Uneekor API.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize import service.

        Args:
            config: Optional configuration
        """
        super().__init__(config)

        self.data_service = DataService()
        self.media_service = MediaService()

        self.api_base_url = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

        self._log_info("ImportService initialized")

    def import_report(
        self,
        url: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        frame_strategy: str = "keyframes"
    ) -> Dict:
        """
        Import complete report from Uneekor URL.

        Args:
            url: Uneekor report URL
            progress_callback: Optional callback (message, current, total)
            frame_strategy: Video frame strategy (none, keyframes, half, full)

        Returns:
            Dictionary with import results:
            {
                'success': bool,
                'shot_count': int,
                'error_count': int,
                'errors': list,
                'report_id': str,
                'sessions': list
            }
        """
        with self._track_performance("import_report"):
            result = {
                'success': False,
                'shot_count': 0,
                'error_count': 0,
                'errors': [],
                'report_id': None,
                'sessions': []
            }

            try:
                # Step 1: Parse URL
                self._report_progress(progress_callback, "Parsing URL...", 0, 100)
                report_id, key = self._extract_url_params(url)

                if not report_id or not key:
                    result['errors'].append("Could not extract report ID and key from URL")
                    return result

                result['report_id'] = report_id

                # Step 2: Fetch data from API
                self._report_progress(progress_callback, f"Fetching data for report {report_id}...", 10, 100)
                sessions_data = self._fetch_from_api(report_id, key)

                if not sessions_data:
                    result['errors'].append("No session data found in API response")
                    return result

                self._log_info(f"Found {len(sessions_data)} sessions", report_id=report_id)

                # Step 3: Process each session
                total_sessions = len(sessions_data)
                total_shots_processed = 0

                for idx, session in enumerate(sessions_data):
                    club_name = session.get('name', 'Unknown')
                    session_id = session.get('id')
                    session_date = session.get('client_created_date')
                    shots = session.get('shots', [])

                    # Extract session-level data for all shots in this session
                    session_level_data = {
                        'ball_name': session.get('ball_name'),  # SOFT, MEDIUM, FIRM
                        'ball_type': session.get('ball_type'),
                        'club_name_std': session.get('club_name'),  # DRIVER, IRON6, etc.
                        'club_type': session.get('club_type'),
                        'client_session_id': session.get('client_session_id')
                    }

                    if not shots:
                        self._log_info(f"Skipping {club_name} - no shots")
                        continue

                    # Calculate progress
                    session_progress = 10 + (idx / total_sessions) * 80
                    self._report_progress(
                        progress_callback,
                        f"Processing {club_name} ({len(shots)} shots)...",
                        int(session_progress),
                        100
                    )

                    # Process shots in session
                    session_result = self._process_session(
                        report_id,
                        key,
                        session_id,
                        session_date,
                        club_name,
                        shots,
                        frame_strategy,
                        session_level_data
                    )

                    result['sessions'].append(session_result)
                    result['shot_count'] += session_result['shot_count']
                    result['error_count'] += session_result['error_count']
                    result['errors'].extend(session_result['errors'])

                    total_shots_processed += session_result['shot_count']

                # Step 4: Complete
                self._report_progress(progress_callback, "Import complete!", 100, 100)

                result['success'] = result['error_count'] == 0
                self._log_info(
                    "Import completed",
                    report_id=report_id,
                    shots=result['shot_count'],
                    errors=result['error_count']
                )

                return result

            except Exception as e:
                self._handle_error(e, "importing report", raise_error=False)
                result['errors'].append(f"Import failed: {str(e)}")
                return result

    def _process_session(
        self,
        report_id: str,
        key: str,
        session_id: str,
        session_date: str,
        club_name: str,
        shots: List[Dict],
        frame_strategy: str,
        session_level_data: Dict = None
    ) -> Dict:
        """
        Process all shots in a session.

        Args:
            report_id: Report ID
            key: API key
            session_id: Session ID
            session_date: Session date
            club_name: Club name
            shots: List of shot dictionaries
            frame_strategy: Video frame strategy
            session_level_data: Session-level fields (ball, club info)

        Returns:
            Dictionary with session results
        """
        result = {
            'session_id': f"{report_id}_{session_id}",
            'club': club_name,
            'shot_count': 0,
            'error_count': 0,
            'errors': []
        }

        # Use provided session data or initialize empty dict
        if session_level_data is None:
            session_level_data = {
                'ball_name': None,
                'ball_type': None,
                'club_name_std': None,
                'club_type': None,
                'client_session_id': None
            }

        for shot in shots:
            try:
                # Process single shot
                shot_result = self._process_shot(
                    report_id,
                    key,
                    session_id,
                    session_date,
                    club_name,
                    shot,
                    frame_strategy,
                    session_level_data
                )

                if shot_result['success']:
                    result['shot_count'] += 1
                else:
                    result['error_count'] += 1
                    result['errors'].append(shot_result['error'])

            except Exception as e:
                self._log_error("Failed to process shot", e, shot_id=shot.get('id'))
                result['error_count'] += 1
                result['errors'].append(f"Shot {shot.get('id')}: {str(e)}")

        return result

    def _clean_invalid_data(self, value):
        """
        Convert Uneekor's invalid data marker (99999) to None.

        Uneekor uses 99999 to indicate that a sensor didn't capture a particular metric.
        """
        if value == 99999 or value == "99999":
            return None
        return value

    def _calculate_low_point(self, attack_angle, club_speed):
        """
        Estimate low point (bottom of swing arc) relative to ball position.

        Args:
            attack_angle: Angle of attack in degrees (negative = downward)
            club_speed: Club head speed in mph

        Returns:
            Estimated low point in inches relative to ball:
            - Negative = low point is before the ball (hitting down)
            - Positive = low point is after the ball (hitting up)
            - None if inputs are invalid
        """
        if attack_angle is None or club_speed is None or club_speed == 0:
            return None

        # For every 1° of attack angle, low point moves ~0.5-1 inch
        low_point_estimate = -(attack_angle / 2.0)
        return round(low_point_estimate, 2)

    def _process_shot(
        self,
        report_id: str,
        key: str,
        session_id: str,
        session_date: str,
        club_name: str,
        shot: Dict,
        frame_strategy: str,
        session_level_data: Dict = None
    ) -> Dict:
        """
        Process a single shot (data + media).

        Args:
            report_id: Report ID
            key: API key
            session_id: Session ID
            session_date: Session date
            club_name: Club name
            shot: Shot data dictionary
            frame_strategy: Video frame strategy
            session_level_data: Session-level fields (ball, club info)

        Returns:
            Dictionary with shot result
        """
        # Unit conversion constants
        M_S_TO_MPH = 2.23694
        M_TO_YARDS = 1.09361

        shot_id_str = str(shot.get('id', ''))
        full_shot_id = f"{report_id}_{session_id}_{shot_id_str}"

        if session_level_data is None:
            session_level_data = {}

        try:
            # Convert units
            ball_speed_ms = shot.get('ball_speed', 0)
            club_speed_ms = shot.get('club_speed', 0)

            ball_speed = round(ball_speed_ms * M_S_TO_MPH, 1) if ball_speed_ms else 0
            club_speed = round(club_speed_ms * M_S_TO_MPH, 1) if club_speed_ms else 0

            carry = round(shot.get('carry_distance', 0) * M_TO_YARDS, 1) if shot.get('carry_distance') else 0
            total = round(shot.get('total_distance', 0) * M_TO_YARDS, 1) if shot.get('total_distance') else 0

            # Calculate smash factor
            smash = round(ball_speed / club_speed, 2) if club_speed > 0 else 0

            # Clean invalid data (99999 markers)
            dynamic_loft_clean = self._clean_invalid_data(shot.get('dynamic_loft'))
            attack_angle_clean = self._clean_invalid_data(shot.get('attack_angle'))
            impact_x_clean = self._clean_invalid_data(shot.get('impact_x'))
            impact_y_clean = self._clean_invalid_data(shot.get('impact_y'))
            club_lie_clean = self._clean_invalid_data(shot.get('club_lie'))

            # Calculate low point
            low_point = self._calculate_low_point(attack_angle_clean, club_speed)

            # Prepare shot data
            shot_data = {
                'shot_id': full_shot_id,
                'session_id': f"{report_id}_{session_id}",
                'session_date': session_date,
                'club': club_name,
                'carry': carry,
                'total': total,
                'ball_speed': ball_speed,
                'club_speed': club_speed,
                'smash': smash,
                'side_spin': shot.get('side_spin', 0),
                'back_spin': shot.get('back_spin', 0),
                'launch_angle': shot.get('launch_angle', 0),
                'side_angle': shot.get('side_angle', 0),
                'club_path': shot.get('club_path', 0),
                'face_angle': shot.get('club_face_angle', 0),
                'dynamic_loft': dynamic_loft_clean,
                'attack_angle': attack_angle_clean,
                'descent_angle': shot.get('decent_angle', 0),  # API has typo: decent_angle
                'side_distance': shot.get('side_distance', 0),
                'apex': shot.get('apex', 0),
                'flight_time': shot.get('flight_time', 0),
                'impact_x': impact_x_clean,
                'impact_y': impact_y_clean,
                'optix_x': shot.get('optix_x', 0),
                'optix_y': shot.get('optix_y', 0),
                'club_lie': club_lie_clean,
                'lie_angle': shot.get('lie_angle'),
                'shot_type': shot.get('type'),
                # NEW: Additional metrics (Dec 2024 expansion)
                'sensor_name': shot.get('sensor_name'),
                'client_shot_id': shot.get('client_shot_id'),
                'server_timestamp': shot.get('created'),
                'is_deleted': shot.get('is_deleted', 'N'),
                'ball_name': session_level_data.get('ball_name'),
                'ball_type': session_level_data.get('ball_type'),
                'club_name_std': session_level_data.get('club_name_std'),
                'club_type': session_level_data.get('club_type'),
                'client_session_id': session_level_data.get('client_session_id'),
                'low_point': low_point
            }

            # Process media
            api_params = {
                'report_id': report_id,
                'key': key,
                'session_id': session_id,
                'shot_id': shot_id_str
            }

            media_urls = self.media_service.process_shot_media(
                full_shot_id,
                api_params,
                frame_strategy
            )

            # Add media URLs to shot data
            shot_data.update(media_urls)

            # Save shot
            saved_id = self.data_service.save_shot(shot_data)

            return {
                'success': True,
                'shot_id': saved_id,
                'error': None
            }

        except Exception as e:
            error_msg = f"Failed to process shot {full_shot_id}: {str(e)}"
            self._log_error(error_msg, e)
            return {
                'success': False,
                'shot_id': full_shot_id,
                'error': error_msg
            }

    def _extract_url_params(self, url: str) -> tuple:
        """
        Extract report_id and key from Uneekor URL.

        Args:
            url: Uneekor URL

        Returns:
            Tuple of (report_id, key)
        """
        try:
            report_id_match = re.search(r'id=(\d+)', url)
            key_match = re.search(r'key=([^&]+)', url)

            if report_id_match and key_match:
                return report_id_match.group(1), key_match.group(1)

            return None, None

        except Exception as e:
            self._log_error("Failed to parse URL", e, url=url[:50])
            return None, None

    def _fetch_from_api(self, report_id: str, key: str) -> Optional[List]:
        """
        Fetch report data from Uneekor API.

        Args:
            report_id: Report ID
            key: API key

        Returns:
            List of session data or None
        """
        api_url = f"{self.api_base_url}/{report_id}/{key}"

        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data

            return None

        except requests.exceptions.RequestException as e:
            self._log_error("API request failed", e, report_id=report_id)
            return None
        except ValueError as e:
            self._log_error("Invalid JSON response", e, report_id=report_id)
            return None

    def _report_progress(
        self,
        callback: Optional[Callable],
        message: str,
        current: int,
        total: int
    ):
        """
        Report progress via callback.

        Args:
            callback: Progress callback function
            message: Progress message
            current: Current progress value
            total: Total progress value
        """
        if callback:
            try:
                callback(message, current, total)
            except Exception as e:
                self._log_error("Progress callback failed", e)

    def validate_url(self, url: str) -> bool:
        """
        Validate Uneekor URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid
        """
        report_id, key = self._extract_url_params(url)
        return report_id is not None and key is not None

    def get_import_summary(self, result: Dict) -> str:
        """
        Generate human-readable import summary.

        Args:
            result: Import result dictionary

        Returns:
            Formatted summary string
        """
        if not result['success']:
            return f"Import failed with {len(result['errors'])} errors"

        lines = [
            f"Successfully imported {result['shot_count']} shots",
            f"Report ID: {result['report_id']}",
            f"Sessions: {len(result['sessions'])}"
        ]

        if result['error_count'] > 0:
            lines.append(f"Warnings: {result['error_count']} shots had issues")

        return "\n".join(lines)
