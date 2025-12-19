import requests
import json
import os

# Using the URL provided earlier by the user
# https://my.uneekor.com/power-u-report?id=40777&key=gPpYYCrNQ4IUez&distance=yard&speed=mph

report_id = "40777"
key = "gPpYYCrNQ4IUez"
API_BASE_URL = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

print(f"Fetching raw data for report {report_id}...")
api_url = f"{API_BASE_URL}/{report_id}/{key}"

try:
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    sessions_data = response.json()
    
    if sessions_data and isinstance(sessions_data, list):
        # Get the first session and first shot
        first_session = sessions_data[0]
        shots = first_session.get('shots', [])
        
        if shots:
            first_shot = shots[0]
            print("\n--- RAW SHOT DATA SAMPLE ---")
            print(json.dumps(first_shot, indent=2))
            
            print("\n--- KEY FIELDS INSPECTION ---")
            print(f"Ball Speed Raw: {first_shot.get('ball_speed')}")
            print(f"Club Speed Raw: {first_shot.get('club_speed')}")
            print(f"Carry Raw: {first_shot.get('carry_distance')}")
            
            # Check for other potential keys
            keys = first_shot.keys()
            speed_keys = [k for k in keys if 'speed' in k.lower()]
            print(f"\nAll keys containing 'speed': {speed_keys}")
            
        else:
            print("No shots found in first session.")
    else:
        print("Invalid data format received.")

except Exception as e:
    print(f"Error: {e}")
