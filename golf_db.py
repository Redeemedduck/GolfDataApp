import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize client
# Note: In a real production app, you might want to cache this client
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("Warning: Supabase credentials not found.")

def init_db():
    pass

def save_shot(data):
    """Save shot data to Supabase."""
    if not supabase:
        print("DB Error: No Supabase client")
        return

    # Helper function to handle invalid values
    def clean_value(val, default=0.0):
        if val is None or val == 99999:
            return default
        return val

    # Prepare payload
    payload = {
        'shot_id': data.get('id', data.get('shot_id')),
        'session_id': data.get('session', data.get('session_id')),
        'club': data.get('club'),
        'carry': clean_value(data.get('carry', data.get('carry_distance'))),
        'total': clean_value(data.get('total', data.get('total_distance'))),
        'smash': clean_value(data.get('smash', 0.0)),
        'club_path': clean_value(data.get('club_path')),
        'face_angle': clean_value(data.get('face_angle', data.get('club_face_angle'))),
        'ball_speed': clean_value(data.get('ball_speed')),
        'club_speed': clean_value(data.get('club_speed')),
        'side_spin': clean_value(data.get('side_spin'), 0),
        'back_spin': clean_value(data.get('back_spin'), 0),
        'launch_angle': clean_value(data.get('launch_angle')),
        'side_angle': clean_value(data.get('side_angle')),
        'dynamic_loft': clean_value(data.get('dynamic_loft')),
        'attack_angle': clean_value(data.get('attack_angle')),
        'impact_x': clean_value(data.get('impact_x')),
        'impact_y': clean_value(data.get('impact_y')),
        'side_distance': clean_value(data.get('side_distance')),
        'descent_angle': clean_value(data.get('descent_angle', data.get('decent_angle'))),
        'apex': clean_value(data.get('apex')),
        'flight_time': clean_value(data.get('flight_time')),
        'shot_type': data.get('shot_type', data.get('type')),
        'impact_img': data.get('impact_img'),
        'swing_img': data.get('swing_img')
    }

    try:
        supabase.table('shots').upsert(payload).execute()
    except Exception as e:
        print(f"Supabase Error: {e}")

def get_session_data(session_id=None):
    if not supabase:
        return pd.DataFrame()

    try:
        query = supabase.table('shots').select("*")
        if session_id:
            query = query.eq('session_id', session_id)
        
        # Limit to 1000 for now to be safe, though pagination should be handled for large datasets
        response = query.limit(2000).execute()
        data = response.data
        
        if not data:
            return pd.DataFrame()
            
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Supabase Read Error: {e}")
        return pd.DataFrame()

def get_unique_sessions():
    if not supabase:
        return []

    try:
        # Fetch session_ids and dates. 
        # Supabase API doesn't support SELECT DISTINCT directly easily on large sets without RPC.
        # We will fetch only needed columns and dedupe in pandas.
        response = supabase.table('shots').select("session_id, date_added").order("date_added", desc=True).limit(2000).execute()
        data = response.data
        
        if not data:
            return []
            
        df = pd.DataFrame(data)
        # Convert date to datetime if needed, or just dedupe strings
        unique_df = df.drop_duplicates(subset=['session_id']).sort_values('date_added', ascending=False)
        
        # Return list of dicts
        return unique_df.to_dict('records')
        
    except Exception as e:
        print(f"Supabase Session Error: {e}")
        return []