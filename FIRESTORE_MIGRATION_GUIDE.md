# Firestore Migration Guide

**Date**: December 26, 2024
**Purpose**: Migrate from Supabase to Firestore for better GCP integration

---

## 🎯 New Architecture

### Before (Redundant)
```
SQLite → Supabase → BigQuery (manual sync)
```

### After (Streamlined)
```
SQLite (local cache)
   ↓
Firestore (cloud primary)
   ↓
BigQuery (auto-sync via Cloud Function)
```

---

## ✨ Benefits

1. **Eliminate Manual Syncing** - Firestore → BigQuery happens automatically
2. **Real-Time Updates** - Changes sync instantly across devices
3. **Single GCP Ecosystem** - Everything in Google Cloud
4. **Better Integration** - Works seamlessly with Vertex AI
5. **Same Cost** - Firestore free tier (50K reads/day) like Supabase

---

## 📦 What's Changed

### Files Created
- `repositories/shot_repository.py` - Now uses Firestore instead of Supabase
- `scripts/migrate_supabase_to_firestore.py` - One-time migration script
- `requirements.txt` - Added `google-cloud-firestore`

### Files Updated
- `services/data_service.py` - No changes needed! (Repository pattern works)
- `requirements.txt` - Added Firestore library

### What Stays The Same
- SQLite still works as local cache
- All your existing data is preserved
- API/interface unchanged (thanks to repository pattern)

---

## 🚀 Migration Steps

### Step 1: Install Dependencies

```bash
# Local (if not using Docker)
pip install google-cloud-firestore

# Docker
docker-compose down
docker-compose up -d --build
```

### Step 2: Verify Credentials

Make sure you have GCP credentials:

```bash
# Check if credentials exist
ls -la ~/.config/gcloud/application_default_credentials.json

# If not, login
gcloud auth application-default login
```

### Step 3: Dry Run (Recommended)

Test the migration without writing data:

```bash
python scripts/migrate_supabase_to_firestore.py --dry-run
```

**Expected Output:**
```
==============================================================
SUPABASE → FIRESTORE MIGRATION
==============================================================
✓ Connected to Supabase
✓ Connected to Firestore

📥 Fetching data from Supabase...
✓ Total shots in Supabase: 555

📤 Migrating to Firestore...
   [DRY RUN MODE - No data will be written]
   ...

==============================================================
MIGRATION SUMMARY
==============================================================
Total shots:     555
Migrated:        555
Errors:          0
Skipped:         0
[DRY RUN - No actual data was written]
```

### Step 4: Run Migration

Once dry run looks good:

```bash
python scripts/migrate_supabase_to_firestore.py --verify
```

You'll be prompted to confirm:
```
This will migrate all shots to Firestore. Continue? (yes/no): yes
```

**Expected Output:**
```
==============================================================
SUPABASE → FIRESTORE MIGRATION
==============================================================
✓ Connected to Supabase
✓ Connected to Firestore

📥 Fetching data from Supabase...
✓ Total shots in Supabase: 555

📤 Migrating to Firestore...
   Processing batch 1/2 (500 shots)...
      ✓ Batch 1 committed successfully
   Processing batch 2/2 (55 shots)...
      ✓ Batch 2 committed successfully

🔍 Verifying migration...
   Supabase shots: 555
   Firestore shots: 555
   ✓ Counts match!

==============================================================
MIGRATION SUMMARY
==============================================================
Total shots:     555
Migrated:        555
Errors:          0
Skipped:         0
Success rate:    100.0%
==============================================================

✓ Migration completed successfully!
```

### Step 5: Verify in GCP Console

1. Go to: https://console.cloud.google.com/firestore
2. Select project: `valued-odyssey-474423-g1`
3. Click on `shots` collection
4. Verify you see 555 documents

---

## 🧪 Testing

### Test 1: Read Data

```python
from repositories.shot_repository import ShotRepository

repo = ShotRepository(project_id="valued-odyssey-474423-g1")

# Get all sessions
sessions = repo.get_unique_sessions()
print(f"Found {len(sessions)} sessions")

# Get shots from a session
shots = repo.find_by_session(sessions[0]['session_id'])
print(f"Session has {len(shots)} shots")
```

### Test 2: Save New Shot

```python
from services.data_service import DataService

service = DataService()

test_shot = {
    'shot_id': 'test_12345',
    'session_id': 'test_session',
    'club': 'Driver',
    'carry': 250.0,
    'total': 275.0,
    'ball_speed': 165.0
}

shot_id = service.save_shot(test_shot)
print(f"Saved shot: {shot_id}")

# Verify it's in Firestore
shot = service.get_shot(shot_id)
print(f"Retrieved: {shot}")
```

### Test 3: Verify Dual Storage

```python
import sqlite3
from google.cloud import firestore

# Check SQLite
conn = sqlite3.connect('./data/golf_stats.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM shots")
sqlite_count = cursor.fetchone()[0]
conn.close()
print(f"SQLite: {sqlite_count} shots")

# Check Firestore
db = firestore.Client(project="valued-odyssey-474423-g1")
firestore_count = sum(1 for _ in db.collection('shots').stream())
print(f"Firestore: {firestore_count} shots")

# Should match!
assert sqlite_count == firestore_count
```

---

## 🔧 Troubleshooting

### Error: "Could not automatically determine credentials"

**Solution:**
```bash
gcloud auth application-default login
# Or set explicit credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### Error: "Permission denied" in Firestore

**Solution:**
```bash
gcloud projects add-iam-policy-binding valued-odyssey-474423-g1 \
  --member="user:YOUR_EMAIL" \
  --role="roles/datastore.user"
```

### Migration shows errors

**Solution:**
1. Check the error messages in the output
2. Run with `--dry-run` to validate data first
3. Ensure Supabase credentials are correct
4. Check network connectivity

---

## 📊 Firestore vs Supabase

| Feature | Supabase | Firestore |
|---------|----------|-----------|
| Type | PostgreSQL | NoSQL Document Store |
| Pricing | $0 (free tier) | $0 (free tier) |
| Sync | Manual scripts | Real-time |
| GCP Integration | External | Native |
| BigQuery Sync | Manual | Automatic (Cloud Functions) |
| Offline Support | No | Yes (with SDK) |
| Querying | SQL | NoSQL queries |

---

## 🎯 Next Steps After Migration

1. ✅ **Migration Complete** - Your data is in Firestore
2. ⏳ **Set up Firestore → BigQuery Sync** - Automatic via Cloud Functions (Phase 1)
3. ⏳ **Update Streamlit App** - Use new DataService (Phase 1)
4. ⏳ **Deploy Vertex AI Agent** - Now with unified GCP stack (Phase 2)
5. 🗑️ **Optional: Decommission Supabase** - Once everything is verified

---

## 🔄 Rollback Plan

If you need to rollback:

1. Your SQLite database still has all data locally
2. Supabase data is untouched (migration only reads, doesn't delete)
3. Simply switch back to old `golf_db.py` if needed

**To rollback:**
```python
# In app.py, use old module
import golf_db  # instead of services.data_service
```

---

## 📝 Notes

- **Local-First**: SQLite remains primary for offline access
- **Firestore**: Cloud backup with real-time sync
- **BigQuery**: Analytics warehouse (auto-synced soon)
- **No Data Loss**: Migration copies data, doesn't move it

---

## ❓ FAQ

**Q: Will my local SQLite data be affected?**
A: No. Migration only affects cloud storage (Supabase → Firestore).

**Q: Can I still use Supabase after migration?**
A: Yes, but it won't be updated. Firestore becomes the cloud source of truth.

**Q: What if migration fails halfway?**
A: It's safe to re-run. Firestore uses `merge=True`, so it won't duplicate data.

**Q: How long does migration take?**
A: ~30 seconds for 555 shots. Firestore batches 500 documents at a time.

**Q: Will this affect my Streamlit app?**
A: Not immediately. The app still uses old `golf_db.py` until we update it (next step).

---

**Status**: Ready to migrate! Run the script when ready.
