# Uneekor API Data Analysis

**Date**: December 27, 2024
**Purpose**: Identify missing data points we can capture from Uneekor API

---

## Current Capture Status

### ✅ Currently Captured (32 fields)

**Shot Data (captured):**
- `ball_speed`, `club_speed`, `smash` (calculated)
- `carry_distance`, `total_distance`, `side_distance`
- `back_spin`, `side_spin`
- `launch_angle`, `side_angle`, `decent_angle` (typo: should be descent)
- `club_path`, `club_face_angle`
- `dynamic_loft`, `attack_angle`
- `impact_x`, `impact_y`
- `optix_x`, `optix_y`
- `club_lie`, `lie_angle`
- `apex`, `flight_time`
- `type` (shot shape: straight, fade, draw)
- `session_date` (actual practice date)
- `impact_img`, `swing_img`, `video_frames` (media URLs)

**Session Data (captured):**
- `name` (club name from session, e.g., "Iron 6")
- `client_created_date` (practice date)

---

## 🆕 Missing Data Points (Available but NOT Captured)

### Session-Level Metrics (6 new fields)

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `club_type` | string | "3" | Numeric club type code |
| `club` | string | "23" | Numeric club ID |
| `club_name` | string | "IRON6" | Standardized club name |
| `ball_type` | string | "3" | Ball type code |
| `ball_name` | string | "MEDIUM" | Ball compression name |
| `client_session_id` | string | "6023" | Client's session ID |

**Why These Matter:**
- **club_type/club/club_name**: More standardized club identification (currently we only use session name)
- **ball_type/ball_name**: Track ball compression used (soft/medium/firm) - affects spin and distance
- **client_session_id**: Original session ID from Uneekor device (useful for cross-referencing)

### Shot-Level Metrics (4 new fields)

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `sensor_name` | string | "EYEXO" | Launch monitor model used |
| `client_shot_id` | string | "439854" | Client's shot number |
| `created` | timestamp | "2025-12-27T02:30:16.000Z" | Server timestamp |
| `is_deleted` | string | "N" | Soft delete flag |

**Why These Matter:**
- **sensor_name**: Track which launch monitor was used (EyeXO, QED, etc.) - different sensors have different accuracy profiles
- **client_shot_id**: Original shot number from device (useful for troubleshooting)
- **created**: Server timestamp (vs client timestamp) for audit trail
- **is_deleted**: Know if Uneekor marked a shot as deleted

---

## 📊 Data Quality Issues Found

### Invalid Data Markers

Uneekor uses `99999` to indicate invalid/missing sensor data:

```json
{
  "dynamic_loft": 99999,  // Sensor didn't capture this
  "attack_angle": 99999,
  "impact_x": 99999,
  "impact_y": 99999,
  "club_lie": 99999
}
```

**Current Handling**: We save these as-is (99999 in database)
**Better Handling**: Convert 99999 → `null` or `0` so analytics don't get skewed

### Typo in Field Name

API field: `decent_angle` (misspelled)
Should be: `descent_angle`

We currently save as `decent_angle` to match API, but should rename in our schema.

---

## 🎯 Recommended Additions (Priority Order)

### High Priority (Immediate Value)

1. **sensor_name** - Track launch monitor model
   - **Use Case**: "Show me only EyeXO shots" or "EyeXO vs QED accuracy"
   - **Implementation**: Add to shot table

2. **ball_name** (ball_type) - Track ball compression
   - **Use Case**: "Do I spin more with soft balls?" "Distance difference with firm balls?"
   - **Implementation**: Add to session table (since all shots in session use same ball)

3. **client_shot_id** - Original device shot number
   - **Use Case**: "What was shot #50 today?" Match to device display
   - **Implementation**: Add to shot table

### Medium Priority (Nice to Have)

4. **club_name** (standardized) - Better club identification
   - **Use Case**: Query by standardized names instead of custom session names
   - **Current**: Session name might be "Driver" or "Driver TM" or "D"
   - **Standardized**: Always "DRIVER", "IRON6", etc.

5. **created** (server timestamp) - Audit trail
   - **Use Case**: Know when shot was uploaded to Uneekor servers
   - **Implementation**: Add as `server_timestamp` to shot table

6. **client_session_id** - Device session ID
   - **Use Case**: Cross-reference with Uneekor app
   - **Implementation**: Add to shot table or session table

### Low Priority (Maybe Later)

7. **club_type**, **club** - Numeric club codes
   - **Use Case**: Group by club type (irons, woods, wedges)
   - **Note**: Can derive from club_name, so less critical

8. **is_deleted** - Soft delete flag
   - **Use Case**: Filter out shots user deleted in Uneekor app
   - **Note**: Rarely used, but good for data integrity

---

## 💾 Proposed Database Schema Changes

### New Columns to Add

```sql
-- Add to shots table
ALTER TABLE shots ADD COLUMN sensor_name TEXT;
ALTER TABLE shots ADD COLUMN client_shot_id TEXT;
ALTER TABLE shots ADD COLUMN server_timestamp TEXT;
ALTER TABLE shots ADD COLUMN is_deleted TEXT DEFAULT 'N';
ALTER TABLE shots ADD COLUMN club_name_std TEXT;  -- Standardized club name

-- Add to sessions table (if we create one)
-- Or add to shots table (duplicated for each shot)
ALTER TABLE shots ADD COLUMN ball_name TEXT;
ALTER TABLE shots ADD COLUMN ball_type TEXT;
ALTER TABLE shots ADD COLUMN client_session_id TEXT;

-- Rename typo
ALTER TABLE shots RENAME COLUMN decent_angle TO descent_angle;
```

### Data Cleaning for Invalid Values

```python
# In golf_scraper.py, before saving:
def clean_invalid_data(value):
    """Convert Uneekor's 99999 marker to null"""
    if value == 99999:
        return None
    return value

# Apply to all numeric fields
shot_data['dynamic_loft'] = clean_invalid_data(shot.get('dynamic_loft'))
shot_data['attack_angle'] = clean_invalid_data(shot.get('attack_angle'))
shot_data['impact_x'] = clean_invalid_data(shot.get('impact_x'))
shot_data['impact_y'] = clean_invalid_data(shot.get('impact_y'))
shot_data['club_lie'] = clean_invalid_data(shot.get('club_lie'))
```

---

## 📈 Analytics Value of New Fields

### Ball Compression Analysis

```sql
-- Average carry by ball type
SELECT ball_name, club_name_std, AVG(carry) as avg_carry
FROM shots
WHERE club_name_std = 'DRIVER'
GROUP BY ball_name, club_name_std;

-- Spin rates by ball type
SELECT ball_name, AVG(back_spin) as avg_spin
FROM shots
WHERE club IN ('DRIVER', 'IRON7')
GROUP BY ball_name;
```

### Launch Monitor Comparison

```sql
-- Sensor accuracy comparison
SELECT sensor_name,
       COUNT(*) as shot_count,
       AVG(CASE WHEN dynamic_loft IS NOT NULL THEN 1 ELSE 0 END) as optix_capture_rate
FROM shots
GROUP BY sensor_name;
```

### Shot Sequence Analysis

```sql
-- Performance trends within session (by shot number)
SELECT client_shot_id, carry, club_speed
FROM shots
WHERE session_id = '41511_85589'
ORDER BY client_shot_id;
```

---

## 🚀 Implementation Plan

### Phase 1: High Priority Fields (Now)
1. Update `golf_scraper.py` to capture: sensor_name, ball_name, client_shot_id
2. Update database schema (add columns)
3. Update BigQuery schema
4. Test import with new fields

### Phase 2: Data Cleaning (Next)
1. Add `clean_invalid_data()` function
2. Convert 99999 → null for all numeric fields
3. Rename `decent_angle` → `descent_angle`

### Phase 3: Medium Priority Fields (Later)
1. Add server_timestamp, club_name_std, client_session_id
2. Create analytics queries using new fields

---

## 📝 Summary

**Currently Capturing**: 32 fields
**Available but Missing**: 10 fields
**Recommended to Add**: 6 fields (high + medium priority)
**Data Quality Improvements**: Clean 99999 markers, fix typo

**Biggest Value Adds:**
1. **Ball compression tracking** - Understand equipment impact
2. **Sensor name** - Data quality and accuracy tracking
3. **Client shot ID** - Better shot identification
4. **Data cleaning** - Remove invalid 99999 markers

**Next Steps**: Implement Phase 1 (high priority fields) first, test, then expand.
