#!/usr/bin/env python3
"""
Quick analysis script for current practice session
"""
import requests
import json
from statistics import mean, stdev

# Parse URL parameters
report_id = "41245"
key = "4XyKk6AtuPk4J"

# Fetch from Uneekor API
api_url = f"https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{report_id}/{key}"

print("🏌️  Fetching your session data from Uneekor...")
print(f"API: {api_url}\n")

try:
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    sessions_data = response.json()

    print(f"✅ Found {len(sessions_data)} club sessions\n")
    print("="*60)

    # Conversion constants
    M_S_TO_MPH = 2.23694
    M_TO_YARDS = 1.09361

    # Analyze each club
    for session in sessions_data:
        club = session.get('name', 'Unknown')
        shots = session.get('shots', [])

        if not shots:
            continue

        print(f"\n📊 {club.upper()} - {len(shots)} shots")
        print("-"*60)

        # Extract key metrics
        carries = []
        ball_speeds = []
        club_speeds = []
        smashes = []
        club_paths = []
        face_angles = []
        side_spins = []
        back_spins = []
        launch_angles = []
        side_distances = []

        for shot in shots:
            # Convert to imperial
            carry = shot.get('carry_distance', 0)
            if carry and carry < 9999:  # Filter out invalid data
                carries.append(round(carry * M_TO_YARDS, 1))

            ball_speed = shot.get('ball_speed', 0)
            if ball_speed and ball_speed < 999:
                ball_speeds.append(round(ball_speed * M_S_TO_MPH, 1))

            club_speed = shot.get('club_speed', 0)
            if club_speed and club_speed < 999:
                club_speeds.append(round(club_speed * M_S_TO_MPH, 1))

            # Calculate smash
            if ball_speed and club_speed and club_speed > 0:
                smash = ball_speed / club_speed
                if 0.5 < smash < 2.0:  # Sanity check
                    smashes.append(round(smash, 2))

            # Path and face data
            path = shot.get('club_path')
            if path is not None and abs(path) < 90:
                club_paths.append(round(path, 1))

            face = shot.get('club_face_angle')
            if face is not None and abs(face) < 90:
                face_angles.append(round(face, 1))

            # Spin
            side_spin = shot.get('side_spin')
            if side_spin is not None and abs(side_spin) < 5000:
                side_spins.append(int(side_spin))

            back_spin = shot.get('back_spin')
            if back_spin is not None and back_spin < 10000:
                back_spins.append(int(back_spin))

            launch = shot.get('launch_angle')
            if launch is not None and 0 < launch < 90:
                launch_angles.append(round(launch, 1))

            side_dist = shot.get('side_distance')
            if side_dist is not None:
                side_distances.append(round(side_dist * M_TO_YARDS, 1))

        # Print summary stats
        if carries:
            print(f"  Carry:       {mean(carries):.1f} yds (±{stdev(carries) if len(carries) > 1 else 0:.1f})")
        if ball_speeds:
            print(f"  Ball Speed:  {mean(ball_speeds):.1f} mph")
        if club_speeds:
            print(f"  Club Speed:  {mean(club_speeds):.1f} mph")
        if smashes:
            print(f"  Smash:       {mean(smashes):.2f}")
        if club_paths:
            avg_path = mean(club_paths)
            print(f"  Club Path:   {avg_path:+.1f}° {'(out-to-in)' if avg_path < 0 else '(in-to-out)' if avg_path > 0 else '(neutral)'}")
        if face_angles:
            avg_face = mean(face_angles)
            print(f"  Face Angle:  {avg_face:+.1f}° {'(closed)' if avg_face < 0 else '(open)' if avg_face > 0 else '(square)'}")
        if side_spins:
            avg_spin = mean(side_spins)
            print(f"  Side Spin:   {avg_spin:+.0f} rpm {'(hook)' if avg_spin < 0 else '(slice)' if avg_spin > 0 else ''}")
        if back_spins:
            print(f"  Back Spin:   {mean(back_spins):.0f} rpm")
        if launch_angles:
            print(f"  Launch:      {mean(launch_angles):.1f}°")
        if side_distances:
            avg_side = mean(side_distances)
            print(f"  Dispersion:  {avg_side:+.1f} yds {'(left)' if avg_side < 0 else '(right)' if avg_side > 0 else ''}")

    print("\n" + "="*60)
    print("\n🎯 Saving full analysis to session_analysis.json...")

    # Save full data for detailed analysis
    with open('session_analysis.json', 'w') as f:
        json.dump(sessions_data, f, indent=2)

    print("✅ Done! Data saved.\n")

except requests.exceptions.RequestException as e:
    print(f"❌ Error fetching data: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
