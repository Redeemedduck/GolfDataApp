# MCP Setup for Pre-Practice Coaching

## What This Gives You

Chat with Claude (in Claude Desktop app) and get **real-time golf coaching** based on your actual shot data:

**Example Conversation:**
```
You: "What should I work on today?"

Claude: *queries your database*
"Looking at your last 3 sessions:
1. Driver dispersion is 15 yards left - focus on path
2. 7-iron smash factor dropped to 1.32 - center contact drills
3. Wedges are dialed - maintain tempo

Recommended focus: 20 drivers working on neutral path"
```

## Quick Setup (5 minutes)

### Option 1: SQLite (Easiest - Local Database)

**Step 1: Install Prerequisites**
```bash
# Make sure Node.js is installed
node --version  # Should show v16+

# If not installed:
brew install node
```

**Step 2: Configure Claude Desktop**

1. Open this file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Copy the contents from `claude_desktop_config.json` in this folder

3. **Update the database path** to match where your SQLite database lives:
   - If using Docker: `/home/user/GolfDataApp/data/golf_stats.db`
   - If local Mac: `~/path/to/GolfDataApp/data/golf_stats.db`

**Step 3: Restart Claude Desktop**

1. Quit Claude Desktop completely
2. Reopen it
3. Look for the 🔌 icon in the bottom-right
4. You should see "golf-data-sqlite" connected

**Step 4: Test It**
```
Ask Claude: "Show me my recent driver sessions"
Ask Claude: "What should I focus on today?"
Ask Claude: "Compare my 7-iron to last week"
```

---

### Option 2: Supabase (Cloud - Access Anywhere)

**Step 1: Get Supabase Connection String**

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Click **Connect** (top right)
4. Choose **Transaction Pooler** (port 6543)
5. Copy the full URI

**Step 2: Update Config**

Replace this line in `claude_desktop_config.json`:
```json
"postgresql://postgres.[YOUR_REF]:[YOUR_PASSWORD]@[HOST]:6543/postgres"
```

With your actual Supabase connection string.

**Step 3: Restart Claude Desktop**

Same as Option 1 above.

---

## Usage Examples

### Pre-Practice Planning
```
You: "I have 30 minutes at the range. What should I work on?"

Claude: *analyzes recent trends*
"Your driver club path has been 3° out-to-in the last 2 sessions.
Recommendation: 15 drivers with alignment stick drill, focusing on
neutral path. Your irons are solid - skip those today."
```

### Mid-Practice Check-In
```
You: "Just hit 10 drivers. Still pulling left. What's happening?"

Claude: *queries historical data*
"Your pull pattern shows when club path is >2° out-to-in AND face
angle is closed. Try: open stance 5°, focus on releasing through impact."
```

### Post-Practice Summary
```
You: "Summarize today's session"

Claude: *compares to historical averages*
"Progress indicators:
✅ Driver dispersion improved 8 yards (from 18y to 10y)
✅ Smash factor up to 1.41 (was 1.38)
⚠️  Still 2° out-to-in path - keep working alignment

Next session: Maintain tempo, continue path work"
```

---

## Mobile Workflow (iOS/Android)

Once MCP is set up on your Mac:

1. **Claude Desktop app** (on Mac) stays connected to database
2. **Claude mobile app** (on phone) - same account, same conversation
3. Start chat on desktop, continue on mobile at range
4. Or use Streamlit app for visual analysis

---

## Troubleshooting

### "Connection failed" error
```bash
# Check Node.js is installed
node --version

# Test npx
npx -y @modelcontextprotocol/server-sqlite --help
```

### "Database not found"
- Verify the absolute path in `claude_desktop_config.json`
- Make sure `golf_stats.db` exists at that location
- If using Docker, the path is inside the container

### "No MCP icon in Claude Desktop"
- Restart Claude Desktop completely (Cmd+Q on Mac)
- Check config file has valid JSON (use JSONLint.com)
- Check Claude Desktop version (must be recent)

---

## Advanced: Custom Coaching Prompts

Create a custom system prompt for Claude:

```
You: "From now on, when I ask for practice advice, structure it as:
1. What's working (keep doing)
2. Priority fix (biggest issue)
3. Drill recommendation (specific)
4. Success metric (how to measure)

And limit to 100 words max - I'm at the range!"
```

Claude will remember this for the conversation.

---

## What Data You Get Access To

With MCP connected, Claude can query:

**Shots Table (30+ fields):**
- Ball speed, club speed, smash factor
- Launch angle, side angle, descent angle
- Back spin, side spin
- Club path, face angle, attack angle, dynamic loft
- Carry distance, total distance, side distance
- Impact location (x, y, optix)
- Club lie angles
- Shot type classification
- Session ID, date, club used

**Sample Queries Claude Can Run:**
- "Show last 20 driver shots"
- "Calculate average smash factor by club"
- "Find sessions where I hit 7-iron"
- "Compare this week vs last week stats"
- "Show shots with club path >2° out-to-in"

---

## Cost

**MCP itself:** Free (just uses NPX)
**Claude Desktop:** Free tier available, Pro recommended for heavy use
**Database queries:** No additional cost (local SQLite or existing Supabase)

---

## Security Notes

- MCP runs locally on your machine
- Database credentials stay in config file (not sent to Anthropic)
- SQLite option = completely local (no cloud access needed)
- Supabase option = encrypted connection

---

## Next Steps

1. Set up MCP using instructions above
2. Test with a simple query
3. Head to range with Claude as your coach!
4. Come back and tell me how it works :)

---

**Questions?** Just ask in Claude Desktop once MCP is connected!
