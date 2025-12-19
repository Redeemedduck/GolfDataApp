#!/usr/bin/env python3
"""
Test script to verify golf_scraper works outside of Streamlit
"""
import golf_scraper
import golf_db

def progress_callback(msg):
    print(f"[PROGRESS] {msg}")

# Initialize database
print("Initializing database...")
golf_db.init_db()

# Test with a sample URL (you'll need to provide a real one)
test_url = input("Paste your Uneekor URL: ")

if test_url:
    print("\nStarting import...")
    result = golf_scraper.run_scraper(test_url, progress_callback)
    print(f"\n[RESULT] {result}")

    # Check database
    sessions = golf_db.get_unique_sessions()
    print(f"\nSessions in database: {len(sessions)}")
    for session in sessions:
        print(f"  - {session}")
else:
    print("No URL provided")
