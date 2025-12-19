#!/usr/bin/env python3
"""
Test script for AI Coach functionality (simulates Streamlit chat)
"""
import os
import anthropic
import golf_db
from dotenv import load_dotenv

load_dotenv()

# Initialize
golf_db.init_db()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Get session data
sessions = golf_db.get_unique_sessions()
if not sessions:
    print("❌ No sessions found in database")
    exit(1)

# Use first session
session_id = sessions[0]['session_id']
df = golf_db.get_session_data(session_id)

print(f"✅ Testing AI Coach with Session {session_id}")
print(f"✅ {len(df)} shots loaded\n")

# Prepare session summary (same as Streamlit app)
session_summary = f"""
**Session Data Context:**
- Club: {df['club'].iloc[0] if len(df) > 0 else 'Unknown'}
- Total Shots: {len(df)}
- Avg Carry: {df['carry'].mean():.1f} yards
- Avg Ball Speed: {df['ball_speed'].mean():.1f} mph
- Avg Club Speed: {df['club_speed'].mean():.1f} mph
- Avg Smash: {df['smash'].mean():.2f}
- Avg Launch: {df['launch_angle'].mean():.1f}°
- Avg Back Spin: {df['back_spin'].mean():.0f} rpm
- Avg Side Spin: {df['side_spin'].mean():.0f} rpm

**Shot Dispersion:**
- Side Distance Std Dev: {df['side_distance'].std():.1f} yards
- Carry Std Dev: {df['carry'].std():.1f} yards
"""

# Build system prompt (same as Streamlit app)
system_prompt = f"""You are an expert golf coach with 20+ years of experience analyzing launch monitor data.

The golfer is practicing at Denver altitude (5,280 ft), which affects ball flight:
- 10-15% more carry distance than sea level
- Lower spin rates due to air density
- Less ball roll due to altitude

**Current Session Data:**
{session_summary}

**Your coaching style:**
- Encouraging but honest
- Specific and data-driven
- Focused on actionable drills
- Ask clarifying questions when needed
- Compare to PGA Tour averages (altitude-adjusted)

Provide coaching in a conversational, supportive tone. Reference the session data when relevant."""

# Test question
test_question = "Based on this session data, what's my biggest area for improvement?"

print("=" * 70)
print(f"🤖 AI COACH TEST")
print("=" * 70)
print(f"\nQuestion: {test_question}\n")
print("Thinking...")

# Call Claude (same model as Streamlit default)
try:
    response = client.messages.create(
        model="claude-3-5-haiku-latest",  # Using Haiku as it's available with this API key
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": test_question}]
    )

    answer = response.content[0].text
    print("\n" + "=" * 70)
    print("🎓 AI COACH RESPONSE:")
    print("=" * 70)
    print(answer)
    print("\n" + "=" * 70)
    print(f"✅ Token Usage: {response.usage.input_tokens} input + {response.usage.output_tokens} output")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ Error: {e}")
