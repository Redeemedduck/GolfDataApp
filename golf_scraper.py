import os
import re
import requests
import time
import golf_db
import observability
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

API_BASE_URL = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

# Image download limits (security: prevent resource exhaustion)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif'}

def request_with_retries(url, timeout=30, max_retries=3, backoff=1.5):
    """Fetch a URL with basic retry/backoff for transient failures."""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code in (429,) or response.status_code >= 500:
                last_err = requests.HTTPError(f"HTTP {response.status_code} for {url}")
                time.sleep(backoff * attempt)
                continue
            return response
        except requests.exceptions.RequestException as e:
            last_err = e
            time.sleep(backoff * attempt)
    raise last_err

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

def run_scraper(url, progress_callback, session_date=None):
    """
    Main scraper function using Uneekor API

    Args:
        url: Uneekor report URL
        progress_callback: Function to call with progress messages
        session_date: Optional datetime for when the session occurred
                      (if not provided, only date_added is recorded)
    """
    start_time = time.time()
    error_count = 0
    report_id = None
    sessions_found = 0

    def log_run(status, message=None):
        observability.append_event(
            "import_runs.jsonl",
            {
                "status": status,
                "report_id": report_id,
                "sessions": sessions_found,
                "shots_imported": total_shots_imported,
                "errors": error_count,
                "duration_sec": round(time.time() - start_time, 2),
                "message": message,
            },
        )

    # 1. Extract report_id and key from URL
    progress_callback("Parsing URL...")
    report_id, key = extract_url_params(url)

    if not report_id or not key:
        total_shots_imported = 0
        log_run("failed", "Invalid report URL")
        return {
            'status': 'error',
            'message': "Could not extract report ID and key from URL. Please use a valid Uneekor report URL.",
            'total_shots_imported': 0
        }

    # 2. Fetch shot data from API
    progress_callback(f"Fetching data for report {report_id}...")
    api_url = f"{API_BASE_URL}/{report_id}/{key}"

    try:
        response = request_with_retries(api_url, timeout=30)
        response.raise_for_status()
        sessions_data = response.json()
    except requests.exceptions.RequestException as e:
        total_shots_imported = 0
        log_run("failed", f"Uneekor API request failed: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to fetch data from Uneekor API: {str(e)}",
            'total_shots_imported': 0
        }
    except ValueError as e:
        total_shots_imported = 0
        log_run("failed", f"Invalid JSON response: {str(e)}")
        return {
            'status': 'error',
            'message': f"Invalid JSON response from API: {str(e)}",
            'total_shots_imported': 0
        }

    if not sessions_data or not isinstance(sessions_data, list):
        total_shots_imported = 0
        log_run("failed", "No session data in API response")
        return {
            'status': 'error',
            'message': "No session data found in API response",
            'total_shots_imported': 0
        }

    sessions_found = len(sessions_data)
    progress_callback(f"Found {sessions_found} club sessions")

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
                    'session_date': session_date.isoformat() if session_date else None,
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
                error_count += 1
                print(f"Error processing shot {shot.get('id')}: {e}")
                continue

    progress_callback(f"Import complete!")
    log_run("success", "Import complete")
    return {
        'status': 'success',
        'message': f"Imported {total_shots_imported} shots (with images) from {len(sessions_data)} club sessions.",
        'total_shots_imported': total_shots_imported,
        'club_sessions': len(sessions_data),
        'session_date': session_date.isoformat() if session_date else None,
        'report_id': report_id
    }

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
        response = request_with_retries(image_api_url, timeout=30)
        if response.status_code != 200:
            return {}
            
        images_data = response.json()

        for img in images_data:
            img_name = img.get('name')
            img_path = img.get('image')

            if img_path:
                full_url = f"https://api-v2.golfsvc.com/v2{img_path}"

                # Security: Check image size and type before downloading
                try:
                    head_response = requests.head(full_url, timeout=10)
                    content_length = int(head_response.headers.get('content-length', 0))
                    content_type = head_response.headers.get('content-type', '').split(';')[0].strip()

                    if content_length > MAX_IMAGE_SIZE:
                        print(f"Skipping image - too large: {content_length} bytes (max: {MAX_IMAGE_SIZE})")
                        continue
                    if content_type and content_type not in ALLOWED_MIME_TYPES:
                        print(f"Skipping image - invalid type: {content_type}")
                        continue
                except requests.exceptions.RequestException:
                    pass  # HEAD failed, proceed with GET

                # Download image into memory
                img_response = request_with_retries(full_url, timeout=30)
                if img_response.status_code == 200:
                    # Double-check size after download
                    if len(img_response.content) > MAX_IMAGE_SIZE:
                        print(f"Skipping image - downloaded size exceeds limit")
                        continue
                    image_bytes = img_response.content
                    
                    # Define path in Supabase bucket
                    # Structure: report_id/shot_id_type.jpg
                    storage_path = f"{report_id}/{shot_id}_{img_name}.jpg"
                    
                    try:
                        bucket = "shot-images"
                        for attempt in range(1, 4):
                            try:
                                supabase.storage.from_(bucket).upload(
                                    path=storage_path,
                                    file=image_bytes,
                                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                                )
                                break
                            except Exception as upload_err:
                                if attempt == 3:
                                    raise upload_err
                                time.sleep(1.5 * attempt)

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
