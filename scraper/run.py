"""
Runner module for the Uneekor scraper workflow.
"""
from typing import Callable

import golf_db
from scraper.api import fetch_report_sessions
from scraper.images import upload_shot_images
from scraper.metrics import calculate_smash
from scraper.url_parser import extract_url_params


def run_scraper(url: str, progress_callback: Callable[[str], None]) -> str:
    """
    Main scraper function using Uneekor API.
    """
    progress_callback("Parsing URL...")
    report_id, key = extract_url_params(url)

    if not report_id or not key:
        return "Error: Could not extract report ID and key from URL. Please use a valid Uneekor report URL."

    progress_callback(f"Fetching data for report {report_id}...")

    try:
        sessions_data = fetch_report_sessions(report_id, key)
    except RuntimeError as exc:
        return f"Error: {exc}"

    progress_callback(f"Found {len(sessions_data)} club sessions")

    total_shots_imported = 0

    # Process each session (club)
    for session in sessions_data:
        club_name = session.get("name", "Unknown")
        session_id = session.get("id")
        shots = session.get("shots", [])

        if not shots:
            progress_callback(f"Skipping {club_name} - no shots")
            continue

        progress_callback(f"Processing {club_name} ({len(shots)} shots)...")

        # Process each shot in the session
        for shot in shots:
            try:
                # Unit Conversions
                # API returns raw data in Metric (m/s for speed, likely Meters for distance)
                # We need to convert to Imperial (mph, yards)
                m_s_to_mph = 2.23694
                m_to_yards = 1.09361

                ball_speed_ms = shot.get("ball_speed", 0)
                club_speed_ms = shot.get("club_speed", 0)

                # Convert speeds to MPH
                ball_speed = round(ball_speed_ms * m_s_to_mph, 1)
                club_speed = round(club_speed_ms * m_s_to_mph, 1) if club_speed_ms else 0

                # Convert distances to Yards
                carry = shot.get("carry_distance", 0)
                total = shot.get("total_distance", 0)
                carry_yards = round(carry * m_to_yards, 1) if carry else 0
                total_yards = round(total * m_to_yards, 1) if total else 0

                smash = calculate_smash(ball_speed, club_speed)

                # Download/Upload images and get URLs
                images = upload_shot_images(report_id, key, session_id, shot.get("id"))

                # Prepare shot data for database
                shot_data = {
                    "id": f"{report_id}_{session_id}_{shot.get('id')}",
                    "session": report_id,
                    "club": club_name,
                    "carry_distance": carry_yards,
                    "total_distance": total_yards,
                    "smash": smash,
                    "club_path": shot.get("club_path"),
                    "club_face_angle": shot.get("club_face_angle"),
                    "ball_speed": ball_speed,
                    "club_speed": club_speed,
                    "side_spin": shot.get("side_spin"),
                    "back_spin": shot.get("back_spin"),
                    "launch_angle": shot.get("launch_angle"),
                    "side_angle": shot.get("side_angle"),
                    "dynamic_loft": shot.get("dynamic_loft"),
                    "attack_angle": shot.get("attack_angle"),
                    "impact_x": shot.get("impact_x"),
                    "impact_y": shot.get("impact_y"),
                    "side_distance": shot.get("side_distance"),
                    "decent_angle": shot.get("decent_angle"),
                    "apex": shot.get("apex"),
                    "flight_time": shot.get("flight_time"),
                    "type": shot.get("type"),
                    "impact_img": images.get("impact_img"),
                    "swing_img": images.get("swing_img"),
                    # Advanced Optix Metrics
                    "optix_x": shot.get("optix_x"),
                    "optix_y": shot.get("optix_y"),
                    "club_lie": shot.get("club_lie"),
                    "lie_angle": shot.get("lie_angle"),
                }

                golf_db.save_shot(shot_data)
                total_shots_imported += 1

            except Exception as exc:
                print(f"Error processing shot {shot.get('id')}: {exc}")
                continue

    progress_callback("Import complete!")
    return (
        "Success! Imported "
        f"{total_shots_imported} shots (with images) "
        f"from {len(sessions_data)} club sessions."
    )
