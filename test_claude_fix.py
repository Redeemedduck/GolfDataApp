#!/usr/bin/env python3
"""
Quick test to verify Claude API model fix
Tests all three models to ensure they work with correct model IDs
"""

import os
from anthropic import Anthropic

# Initialize client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Models to test (same as in app.py)
models = {
    "Haiku (Fast)": "claude-3-5-haiku-20241022",
    "Sonnet (Balanced)": "claude-3-5-sonnet-20241022",
    "Opus (Best)": "claude-3-opus-20240229"
}

print("Testing Claude API with updated model names...")
print("=" * 70)

for name, model_id in models.items():
    print(f"\n🔍 Testing {name}: {model_id}")
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'Model working!' in 3 words or less."}]
        )
        result = response.content[0].text
        print(f"✅ SUCCESS: {result}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

print("\n" + "=" * 70)
print("Test complete!")
