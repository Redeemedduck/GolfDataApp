#!/usr/bin/env python3
"""
Test script to inspect session date fields in Uneekor API response
"""
import requests
import json

# Using a known report ID from your database
report_id = "40945"
key = "pc0VcwgCBkYKZpHf"

API_BASE_URL = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"
api_url = f"{API_BASE_URL}/{report_id}/{key}"

print(f"Fetching data from Uneekor API...")
print(f"URL: {api_url}\n")

try:
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    sessions_data = response.json()

    if sessions_data and isinstance(sessions_data, list) and len(sessions_data) > 0:
        # Get first session to inspect structure
        first_session = sessions_data[0]

        print("=" * 80)
        print("SESSION OBJECT STRUCTURE")
        print("=" * 80)
        print(json.dumps(first_session, indent=2, default=str))

        print("\n" + "=" * 80)
        print("SESSION DATE FIELDS")
        print("=" * 80)

        # Look for date-related fields
        date_fields = {k: v for k, v in first_session.items() if 'date' in k.lower() or 'time' in k.lower() or 'created' in k.lower()}

        if date_fields:
            for key, value in date_fields.items():
                print(f"{key}: {value}")
        else:
            print("No obvious date fields found. Full keys:")
            print(list(first_session.keys()))

    else:
        print("No session data found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
