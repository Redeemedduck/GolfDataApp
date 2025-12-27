import os
import re
import requests
import golf_db
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

API_BASE_URL = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

def clean_invalid_data(value):
    """
    Convert Uneekor's invalid data marker (99999) to None.

    Uneekor uses 99999 to indicate that a sensor didn't capture a particular metric.
    Converting to None allows for proper null handling in analytics.

    Args:
        value: Raw value from Uneekor API

    Returns:
        None if value is 99999, otherwise the original value
    """
    if value == 99999 or value == "99999":
        return None
    return value


def calculate_low_point(attack_angle, club_speed):
    """
    Estimate low point (bottom of swing arc) relative to ball position.

    Low point is where the club reaches its lowest point in the swing arc.
    Positive attack angle = hitting up on ball (low point before ball)
    Negative attack angle = hitting down on ball (low point after ball)

    Formula: low_point_inches = (attack_angle_degrees / 10) * (club_speed_mph / 100)

    This is an approximation based on swing geometry. Actual low point can vary
    based on shaft lean, swing plane, and other factors.

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

    # Rough estimate: attack angle correlates with low point
    # For every 1° of attack angle, low point moves ~0.5-1 inch
    # Faster swings have slightly different ratios
    low_point_estimate = -(attack_angle / 2.0)  # Negative attack = low point before ball

    return round(low_point_estimate, 2)


def extract_url_params(url):
    """Extract report_id and key from Uneekor URL"""
    try:
        report_id_match = re.search(r'id=(\d+)', url)
        key_match = re.search(r'key=([^&]+)', url)

        if report_id_match and key_match:
            return report_id_match.group(1), key_match.group(1)
        else:
            return None, None
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None, None

def calculate_smash(ball_speed, club_speed):
    """Calculate smash factor (ball speed / club speed)"""
    if club_speed and club_speed > 0:
        return round(ball_speed / club_speed, 2)
    return 0.0

def run_scraper(url, progress_callback):
    """
    Main scraper function using Uneekor API
    """

    # 1. Extract report_id and key from URL
    progress_callback("Parsing URL...")
    report_id, key = extract_url_params(url)

    if not report_id or not key:
        return "Error: Could not extract report ID and key from URL. Please use a valid Uneekor report URL."

    # 2. Fetch shot data from API
    progress_callback(f"Fetching data for report {report_id}...")
    api_url = f"{API_BASE_URL}/{report_id}/{key}"

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        sessions_data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Error: Failed to fetch data from Uneekor API: {str(e)}"
    except ValueError as e:
        return f"Error: Invalid JSON response from API: {str(e)}"

    if not sessions_data or not isinstance(sessions_data, list):
        return "Error: No session data found in API response"

    progress_callback(f"Found {len(sessions_data)} club sessions")

    total_shots_imported = 0

    # 3. Process each session (club)
    for session in sessions_data:
        club_name = session.get('name', 'Unknown')
        session_id = session.get('id')
        session_date = session.get('client_created_date')  # Actual practice date
        shots = session.get('shots', [])

        # Session-level data (same for all shots in this session)
        ball_name = session.get('ball_name')  # Ball compression: SOFT, MEDIUM, FIRM
        ball_type = session.get('ball_type')  # Ball type code
        club_name_std = session.get('club_name')  # Standardized club name: DRIVER, IRON6, etc.
        club_type = session.get('club_type')  # Club type code
        client_session_id = session.get('client_session_id')  # Original device session ID

        if not shots:
            progress_callback(f"Skipping {club_name} - no shots")
            continue

        progress_callback(f"Processing {club_name} ({len(shots)} shots)...")

        # 4. Process each shot in the session
        for shot in shots:
            try:
                # Unit Conversions
                # API returns raw data in Metric (m/s for speed, likely Meters for distance)
                # We need to convert to Imperial (mph, yards)
                M_S_TO_MPH = 2.23694
                M_TO_YARDS = 1.09361

                ball_speed_ms = shot.get('ball_speed', 0)
                club_speed_ms = shot.get('club_speed', 0)
                
                # Convert speeds to MPH
                ball_speed = round(ball_speed_ms * M_S_TO_MPH, 1)
                club_speed = round(club_speed_ms * M_S_TO_MPH, 1) if club_speed_ms else 0

                # Convert distances to Yards
                carry = shot.get('carry_distance', 0)
                total = shot.get('total_distance', 0)
                carry_yards = round(carry * M_TO_YARDS, 1) if carry else 0
                total_yards = round(total * M_TO_YARDS, 1) if total else 0

                smash = calculate_smash(ball_speed, club_speed)

                # Clean invalid data (99999 markers)
                dynamic_loft_clean = clean_invalid_data(shot.get('dynamic_loft'))
                attack_angle_clean = clean_invalid_data(shot.get('attack_angle'))
                impact_x_clean = clean_invalid_data(shot.get('impact_x'))
                impact_y_clean = clean_invalid_data(shot.get('impact_y'))
                club_lie_clean = clean_invalid_data(shot.get('club_lie'))

                # Calculate low point (bottom of swing arc relative to ball)
                low_point = calculate_low_point(attack_angle_clean, club_speed)

                # Download/Upload images and get URLs
                images = upload_shot_images(report_id, key, session_id, shot.get('id'))

                # Prepare shot data for database
                shot_data = {
                    'id': f"{report_id}_{session_id}_{shot.get('id')}",
                    'session': report_id,
                    'session_date': session_date,  # Actual practice date
                    'club': club_name,
                    'carry_distance': carry_yards,
                    'total_distance': total_yards,
                    'smash': smash,
                    'club_path': shot.get('club_path'),
                    'club_face_angle': shot.get('club_face_angle'),
                    'ball_speed': ball_speed,
                    'club_speed': club_speed,
                    'side_spin': shot.get('side_spin'),
                    'back_spin': shot.get('back_spin'),
                    'launch_angle': shot.get('launch_angle'),
                    'side_angle': shot.get('side_angle'),
                    'dynamic_loft': dynamic_loft_clean,  # Cleaned (99999 → None)
                    'attack_angle': attack_angle_clean,  # Cleaned (99999 → None)
                    'impact_x': impact_x_clean,  # Club face impact horizontal (mm), cleaned
                    'impact_y': impact_y_clean,  # Club face impact vertical (mm), cleaned
                    'side_distance': shot.get('side_distance'),
                    'descent_angle': shot.get('decent_angle'),  # Fixed typo (was decent_angle)
                    'apex': shot.get('apex'),
                    'flight_time': shot.get('flight_time'),
                    'type': shot.get('type'),
                    'impact_img': images.get('impact_img'),
                    'swing_img': images.get('swing_img'),
                    'video_frames': images.get('video_frames'),  # Comma-separated video frame URLs
                    # Advanced Optix Metrics
                    'optix_x': shot.get('optix_x'),  # Optix horizontal position
                    'optix_y': shot.get('optix_y'),  # Optix vertical position
                    'club_lie': club_lie_clean,  # Cleaned (99999 → None)
                    'lie_angle': shot.get('lie_angle'),
                    # NEW: Additional metrics
                    'sensor_name': shot.get('sensor_name'),  # Launch monitor model: EYEXO, QED, etc.
                    'client_shot_id': shot.get('client_shot_id'),  # Original device shot number
                    'server_timestamp': shot.get('created'),  # Server upload timestamp
                    'is_deleted': shot.get('is_deleted', 'N'),  # Soft delete flag
                    'ball_name': ball_name,  # Ball compression: SOFT, MEDIUM, FIRM
                    'ball_type': ball_type,  # Ball type code
                    'club_name_std': club_name_std,  # Standardized club name: DRIVER, IRON6
                    'club_type': club_type,  # Club type code
                    'client_session_id': client_session_id,  # Original device session ID
                    'low_point': low_point  # Estimated low point in inches (calculated)
                }
                
                # Save to database
                golf_db.save_shot(shot_data)
                total_shots_imported += 1

            except Exception as e:
                print(f"Error processing shot {shot.get('id')}: {e}")
                continue

    progress_callback(f"Import complete!")
    return f"Success! Imported {total_shots_imported} shots (with images) from {len(sessions_data)} club sessions."

def upload_shot_images(report_id, key, session_id, shot_id, video_strategy="keyframes"):
    """
    Fetch images and video frames from Uneekor API and upload to Supabase Storage.
    Returns dictionary of Public URLs.

    Args:
        video_strategy: Controls which video frames to download
            - "none": Only impact image + first frame (minimal storage)
            - "keyframes": Key frames only (0, 6, 12, 18, 23 = 5 frames)
            - "half": Every other frame (12 frames)
            - "full": All 24 frames (maximum storage)
    """
    if not supabase:
        print("Warning: Supabase client not initialized, skipping image upload.")
        return {}

    image_api_url = f"{API_BASE_URL}/shotimage/{report_id}/{key}/{session_id}/{shot_id}"
    uploaded_urls = {}

    # Define which topview frames to download based on strategy
    frame_selections = {
        "none": [0],  # Just first frame (current behavior)
        "keyframes": [0, 6, 12, 18, 23],  # Key moments in swing
        "half": list(range(0, 24, 2)),  # Every other frame (0, 2, 4, ..., 22)
        "full": list(range(24))  # All frames (0-23)
    }

    selected_frames = frame_selections.get(video_strategy, frame_selections["keyframes"])
    video_frame_urls = []

    try:
        response = requests.get(image_api_url, timeout=30)
        if response.status_code != 200:
            return {}

        images_data = response.json()

        for img in images_data:
            img_name = img.get('name')
            img_path = img.get('image')

            if not img_path:
                continue

            # Check if this is a video frame we want to download
            is_impact = img_name == 'ballimpact'
            is_video_frame = img_name.startswith('topview')

            if is_video_frame:
                # Extract frame number (e.g., "topview12" -> 12)
                try:
                    frame_num = int(img_name.replace('topview', ''))
                    if frame_num not in selected_frames:
                        continue  # Skip this frame based on strategy
                except:
                    continue
            elif not is_impact:
                continue  # Skip non-impact, non-topview images

            # Download the image
            full_url = f"https://api-v2.golfsvc.com/v2{img_path}"
            img_response = requests.get(full_url, timeout=30)

            if img_response.status_code == 200:
                image_bytes = img_response.content

                # Define path in Supabase bucket
                storage_path = f"{report_id}/{shot_id}_{img_name}.jpg"

                try:
                    # Upload to Supabase
                    bucket = "shot-images"
                    supabase.storage.from_(bucket).upload(
                        path=storage_path,
                        file=image_bytes,
                        file_options={"content-type": "image/jpeg", "upsert": "true"}
                    )

                    # Get Public URL
                    public_url = supabase.storage.from_(bucket).get_public_url(storage_path)

                    if img_name == 'ballimpact':
                        uploaded_urls['impact_img'] = public_url
                    elif img_name == 'topview00':
                        # First frame always goes to swing_img for backward compatibility
                        uploaded_urls['swing_img'] = public_url
                        video_frame_urls.append(public_url)
                    else:
                        # Collect all video frames
                        video_frame_urls.append(public_url)

                except Exception as storage_err:
                    print(f"Storage Upload Error ({img_name}): {storage_err}")

        # Store video frame URLs as comma-separated list
        if video_frame_urls:
            uploaded_urls['video_frames'] = ','.join(video_frame_urls)

        return uploaded_urls

    except Exception as e:
        print(f"Error handling images for shot {shot_id}: {e}")
        return {}
