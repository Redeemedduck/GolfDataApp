#!/usr/bin/env python3
"""
Test script to inspect Uneekor video API response structure
"""
import requests
import json

# Using a known report with video data
report_id = "40945"
key = "pc0VcwgCBkYKZpHf"
session_id = "84428"  # From database
shot_id = "1283266"   # From database

API_BASE_URL = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

# First, let's check the shotimage endpoint (which may contain videos)
image_api_url = f"{API_BASE_URL}/shotimage/{report_id}/{key}/{session_id}/{shot_id}"

print("=" * 80)
print("TESTING UNEEKOR VIDEO/MEDIA API")
print("=" * 80)
print(f"\nEndpoint: {image_api_url}\n")

try:
    response = requests.get(image_api_url, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        media_data = response.json()

        print("\n" + "=" * 80)
        print("MEDIA RESPONSE STRUCTURE")
        print("=" * 80)
        print(json.dumps(media_data, indent=2, default=str))

        print("\n" + "=" * 80)
        print("MEDIA ITEMS SUMMARY")
        print("=" * 80)

        if isinstance(media_data, list):
            print(f"\nTotal items: {len(media_data)}")

            for idx, item in enumerate(media_data, 1):
                name = item.get('name', 'Unknown')
                path = item.get('image', item.get('video', 'N/A'))
                media_type = item.get('type', 'Unknown')

                print(f"\nItem {idx}:")
                print(f"  Name: {name}")
                print(f"  Type: {media_type}")
                print(f"  Path: {path}")

                # Check if this looks like a video
                if path and ('video' in name.lower() or 'mp4' in path.lower() or 'mov' in path.lower()):
                    print(f"  >>> POSSIBLE VIDEO CONTENT <<<")
                    full_url = f"https://api-v2.golfsvc.com/v2{path}"
                    print(f"  Full URL: {full_url}")
        else:
            print("Response is not a list. Structure:")
            print(f"Keys: {list(media_data.keys()) if isinstance(media_data, dict) else 'Not a dict'}")

    elif response.status_code == 404:
        print("\n404 - No media found for this shot")
        print("This may indicate:")
        print("  - No videos/images were captured for this shot")
        print("  - Different API endpoint for videos")
        print("  - Videos stored separately from images")
    else:
        print(f"\nUnexpected status code: {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

# Let's also check the main report endpoint to see if video URLs are in the shot data
print("\n" + "=" * 80)
print("CHECKING MAIN REPORT FOR VIDEO FIELDS")
print("=" * 80)

try:
    main_api_url = f"{API_BASE_URL}/{report_id}/{key}"
    response = requests.get(main_api_url, timeout=30)

    if response.status_code == 200:
        sessions_data = response.json()

        # Find our specific session and shot
        for session in sessions_data:
            if str(session.get('id')) == session_id:
                shots = session.get('shots', [])
                for shot in shots:
                    if str(shot.get('id')) == shot_id:
                        print("\nFound shot in main report. Checking for video fields:")

                        # Look for any video-related fields
                        video_fields = {k: v for k, v in shot.items() if 'video' in k.lower() or 'media' in k.lower() or 'mp4' in str(v).lower()}

                        if video_fields:
                            print("\nVideo-related fields found:")
                            for key, value in video_fields.items():
                                print(f"  {key}: {value}")
                        else:
                            print("\nNo obvious video fields in shot data")
                            print(f"Available fields: {list(shot.keys())[:10]}...")
                        break
                break

except Exception as e:
    print(f"\nError checking main report: {e}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
