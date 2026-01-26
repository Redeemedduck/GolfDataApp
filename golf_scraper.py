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

def extract_url_params(url):
    """Extract report_id and key from Uneekor URL."""
    try:
        report_id_match = re.search(r"[?&]id=(\d+)", url)
        key_match = re.search(r"[?&]key=([^&]+)", url)

        if report_id_match and key_match:
            return report_id_match.group(1), key_match.group(1)
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
        shots = session.get('shots', [])

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

                # Download/Upload images and get URLs
                images = upload_shot_images(report_id, key, session_id, shot.get('id'))

                # Prepare shot data for database
                shot_data = {
                    'id': f"{report_id}_{session_id}_{shot.get('id')}",
                    'session': report_id,
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
                    'dynamic_loft': shot.get('dynamic_loft'),
                    'attack_angle': shot.get('attack_angle'),
                    'impact_x': shot.get('impact_x'),
                    'impact_y': shot.get('impact_y'),
                    'side_distance': shot.get('side_distance'),
                    'decent_angle': shot.get('decent_angle'),
                    'apex': shot.get('apex'),
                    'flight_time': shot.get('flight_time'),
                    'type': shot.get('type'),
                    'impact_img': images.get('impact_img'),
                    'swing_img': images.get('swing_img'),
                    # Advanced Optix Metrics
                    'optix_x': shot.get('optix_x'),
                    'optix_y': shot.get('optix_y'),
                    'club_lie': shot.get('club_lie'),
                    'lie_angle': shot.get('lie_angle')
                }
                
                # Save to database
                golf_db.save_shot(shot_data)
                total_shots_imported += 1

            except Exception as e:
                print(f"Error processing shot {shot.get('id')}: {e}")
                continue

    progress_callback(f"Import complete!")
    return f"Success! Imported {total_shots_imported} shots (with images) from {len(sessions_data)} club sessions."

def upload_shot_images(report_id, key, session_id, shot_id):
    """
    Fetch images from Uneekor API and upload to Supabase Storage.
    Returns dictionary of Public URLs.
    """
    if not supabase:
        print("Warning: Supabase client not initialized, skipping image upload.")
        return {}

    image_api_url = f"{API_BASE_URL}/shotimage/{report_id}/{key}/{session_id}/{shot_id}"
    uploaded_urls = {}

    try:
        response = requests.get(image_api_url, timeout=30)
        if response.status_code != 200:
            return {}
            
        images_data = response.json()

        for img in images_data:
            img_name = img.get('name')
            img_path = img.get('image')

            if img_path:
                full_url = f"https://api-v2.golfsvc.com/v2{img_path}"

                # Download image into memory
                img_response = requests.get(full_url, timeout=30)
                if img_response.status_code == 200:
                    image_bytes = img_response.content
                    
                    # Define path in Supabase bucket
                    # Structure: report_id/shot_id_type.jpg
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
                        elif img_name.startswith('topview'):
                            uploaded_urls['swing_img'] = public_url
                            
                    except Exception as storage_err:
                        print(f"Storage Upload Error ({img_name}): {storage_err}")

        return uploaded_urls

    except Exception as e:
        print(f"Error handling images for shot {shot_id}: {e}")
        return {}
