# Golf Data Pipeline - Automation Guide

This guide explains how to automate your golf data analysis pipeline.

---

## Quick Start

### Option 1: Post-Session Analysis (Recommended for beginners)

After each practice session, run:
```bash
python scripts/post_session.py
```

This will:
1. ✅ Sync new data from Supabase to BigQuery
2. 📊 Show today's session summary
3. 🤖 Optionally analyze your performance with AI
4. 📈 Display all-time stats

### Option 2: Automated Background Syncing

Set up automatic syncing with the setup wizard:
```bash
./setup_cron.sh
```

Choose from:
- **Hourly sync**: Data stays fresh automatically
- **Daily sync with analysis**: Get insights every evening
- **Manual only**: You control when to sync

---

## Automation Scripts

### 1. `post_session.py` - Interactive Post-Session Analysis

**Best for**: After each practice session

**Usage:**
```bash
python scripts/post_session.py
```

**What it does:**
- Syncs new data to BigQuery
- Shows today's practice summary
- Asks if you want AI analysis
- Displays all-time club stats

**Example output:**
```
======================================================================
                    TODAY'S SESSION SUMMARY
======================================================================

             club  shots  avg_carry  avg_total  avg_smash  avg_ball_speed  avg_club_speed
           Driver      5      258.3      277.5       1.38            70.5            51.1
         Wedge 50     15      100.2      103.1       1.14            38.2            33.8

📈 Total shots today: 20
🏌️  Clubs practiced: Driver, Wedge 50

🤖 Would you like AI analysis of today's session? (y/n):
```

---

### 2. `auto_sync.py` - Automated Background Sync

**Best for**: Scheduled automation (cron jobs)

**Usage:**
```bash
# Sync only (no analysis)
python scripts/auto_sync.py

# Sync + analyze recent sessions
python scripts/auto_sync.py --analyze
```

**What it does:**
- Checks for new shots in Supabase
- Runs incremental sync if new data exists
- Logs all operations to `logs/sync.log`
- Optionally runs AI analysis on recent clubs

**Features:**
- ✅ Smart checking (only syncs when needed)
- ✅ Detailed logging for troubleshooting
- ✅ Error handling and recovery
- ✅ Timestamp tracking

---

### 3. `setup_cron.sh` - Automation Setup Wizard

**Best for**: One-time setup of scheduled syncing

**Usage:**
```bash
./setup_cron.sh
```

**Interactive setup that offers:**

1. **Hourly Sync** (Recommended)
   - Schedule: Every hour on the hour
   - Command: `python scripts/auto_sync.py`
   - Best for: Keeping data fresh with minimal delay

2. **Daily Sync + Analysis**
   - Schedule: 8 PM every day
   - Command: `python scripts/auto_sync.py --analyze`
   - Best for: End-of-day insights and tracking

3. **Manual Only**
   - No automatic syncing
   - Run manually after each session

---

## Cron Job Management

### View installed cron jobs
```bash
crontab -l
```

### Edit cron jobs manually
```bash
crontab -e
```

### Remove automation
```bash
crontab -e
# Delete the line containing "scripts/auto_sync.py"
```

### View sync logs
```bash
# View recent logs
tail -n 50 logs/sync.log

# Follow logs in real-time
tail -f logs/sync.log

# View all logs
cat logs/sync.log
```

---

## Example Workflows

### Workflow 1: Manual After Each Session

```bash
# 1. Practice at the range (data goes to Supabase automatically)
# 2. Come home and run:
python scripts/post_session.py

# 3. Review insights and plan next session
```

**Pros:**
- Full control over when analysis runs
- Interactive prompts guide you
- See results immediately

**Cons:**
- Must remember to run it
- Requires manual intervention

---

### Workflow 2: Automated Hourly + Manual Analysis

```bash
# Setup (one-time):
./setup_cron.sh
# Select Option 1: Hourly Sync

# After practice:
python scripts/gemini_analysis.py summary
python scripts/gemini_analysis.py analyze Driver
```

**Pros:**
- Data always up-to-date in BigQuery
- Quick manual analysis when needed
- No sync delays

**Cons:**
- Requires manual analysis step
- More resource usage (hourly syncs)

---

### Workflow 3: Fully Automated Daily

```bash
# Setup (one-time):
./setup_cron.sh
# Select Option 2: Daily Sync with Analysis

# Check insights next morning:
tail -n 100 logs/sync.log
```

**Pros:**
- Completely hands-off
- Regular insights without effort
- Log history for tracking

**Cons:**
- Analysis happens on schedule, not immediately
- Less interactive

---

## Monitoring & Troubleshooting

### Check if automation is working

1. **View last sync:**
   ```bash
   tail -20 logs/sync.log
   ```

2. **Verify BigQuery data:**
   ```bash
   python scripts/supabase_to_bigquery.py incremental --dry-run
   ```

3. **Check cron status:**
   ```bash
   crontab -l
   ```

### Common issues

**Issue**: Cron job not running
```bash
# Check cron service is running (macOS)
launchctl list | grep cron

# View system logs
log show --predicate 'process == "cron"' --last 1h
```

**Issue**: Sync fails in automation
```bash
# Check logs
tail -50 logs/sync.log

# Run manually to see errors
python scripts/auto_sync.py
```

**Issue**: No new data syncing
```bash
# Verify Supabase has new data
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); s=create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); print(s.table('shots').select('shot_id', count='exact').execute().count)"

# Check BigQuery count
python -c "from google.cloud import bigquery; import os; from dotenv import load_dotenv; load_dotenv(); bq=bigquery.Client(project=os.getenv('GCP_PROJECT_ID')); result=bq.query('SELECT COUNT(*) FROM \`valued-odyssey-474423-g1.golf_data.shots\`').result(); print(list(result)[0][0])"
```

---

## Environment Variables

All scripts automatically load from `.env`:
```bash
SUPABASE_URL=...
SUPABASE_KEY=...
GCP_PROJECT_ID=...
GEMINI_API_KEY=...
```

For cron jobs, ensure `.env` is in the same directory as the scripts.

---

## Log File Format

Logs are stored in `logs/sync.log`:
```
[2025-12-16 10:00:01] ======================================================================
[2025-12-16 10:00:01] GOLF DATA PIPELINE - AUTO SYNC
[2025-12-16 10:00:01] ======================================================================
[2025-12-16 10:00:01] Checking for new shots...
[2025-12-16 10:00:02] Found 5 new shots to sync
[2025-12-16 10:00:03] Starting incremental sync...
[2025-12-16 10:00:05] Incremental sync completed successfully
[2025-12-16 10:00:05] ======================================================================
[2025-12-16 10:00:05] AUTO SYNC COMPLETE
[2025-12-16 10:00:05] ======================================================================
```

---

## Best Practices

1. **Start Manual**: Use `post_session.py` for first few sessions to understand the workflow

2. **Enable Automation**: Once comfortable, set up hourly or daily syncing

3. **Monitor Logs**: Check `logs/sync.log` weekly to ensure everything is working

4. **Analyze Intentionally**: Even with automation, manually analyze specific clubs when preparing for rounds

5. **Backup Data**: BigQuery has your data backed up, but consider periodic exports

---

## Performance Tips

### For Frequent Syncing (Hourly)
- Incremental sync is very fast (< 5 seconds)
- Minimal impact on system resources
- Data always fresh for queries

### For Daily Analysis
- Run analysis overnight or during off-hours
- Generates comprehensive reports
- Consolidates multiple sessions

### For Manual Only
- Full control and transparency
- Best for learning the system
- No background resource usage

---

## Next Steps

1. **Try Manual First:**
   ```bash
   python post_session.py
   ```

2. **Set Up Automation:**
   ```bash
   ./setup_cron.sh
   ```

3. **Monitor for a Week:**
   ```bash
   tail -f logs/sync.log
   ```

4. **Adjust as Needed:**
   - Too frequent? Switch to daily
   - Want instant feedback? Use manual mode
   - Need both? Use hourly sync + manual analysis

---

## Command Quick Reference

```bash
# Post-session (interactive)
python scripts/post_session.py

# Manual sync + analysis
python scripts/auto_sync.py --analyze

# Manual sync only
python scripts/auto_sync.py

# Club summary
python scripts/gemini_analysis.py summary

# Analyze specific club
python scripts/gemini_analysis.py analyze "Driver"

# View logs
tail -f logs/sync.log

# Setup automation
./setup_cron.sh
```

Happy analyzing! 🏌️‍♂️
