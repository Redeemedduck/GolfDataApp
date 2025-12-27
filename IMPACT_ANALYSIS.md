# Impact Analysis Guide

**Purpose**: Understanding ball-club contact through data and visual analysis
**Last Updated**: December 27, 2024
**Version**: 1.0

---

## Overview

This guide explains how to use impact position data (`impact_x`, `impact_y`) and impact images to analyze strike patterns, verify low point calculations, and identify swing characteristics through turf interaction.

---

## Impact Position Data

### What the Data Tells You

**Fields Captured**:
- `impact_x`: Horizontal position on club face (mm from center)
- `impact_y`: Vertical position on club face (mm from center)
- `impact_img`: URL to impact image (club face + ball at contact)

**Coordinate System**:
```
        Vertical (impact_y)
              ↑
              |  +y (high on face)
              |
    ←─────────●─────────→  Horizontal (impact_x)
   -x (heel)  |  +x (toe)
              |
              |  -y (low on face)
              ↓
```

### Example Data

```sql
SELECT shot_id, club, impact_x, impact_y, carry
FROM shots
WHERE impact_x != 0 AND impact_y != 0
LIMIT 5;
```

**Results**:
```
Shot 1298334 | 6 Iron | 2.0mm toe | 6.0mm high | 165 yards
Shot 1298351 | 6 Iron | 1.0mm toe | 3.0mm high | 168 yards
Shot 1298367 | 6 Iron | -3.0mm heel | 2.0mm high | 162 yards
```

**Interpretation**:
- **2.0mm toe**: Slightly off-center toward toe (minor distance loss)
- **6.0mm high**: Above center (reduced spin, slightly more distance)
- **-3.0mm heel**: Heel strike (gear effect = right spin for RH golfer)

---

## Strike Pattern Analysis

### 1. Sweet Spot Consistency

**Query**: Find average impact position by club
```sql
SELECT
  club_name_std,
  AVG(impact_x) as avg_x_offset,
  AVG(impact_y) as avg_y_offset,
  STDDEV(impact_x) as x_consistency,
  STDDEV(impact_y) as y_consistency,
  COUNT(*) as shot_count
FROM shots
WHERE impact_x != 0 AND impact_y != 0
GROUP BY club_name_std
ORDER BY shot_count DESC;
```

**What to Look For**:
- **avg_x_offset near 0**: Centered strikes horizontally
- **avg_y_offset near 0**: Centered strikes vertically
- **Low STDDEV**: Consistent contact pattern
- **High STDDEV**: Inconsistent strikes (practice needed)

**Good Pattern** (Driver):
```
avg_x: 0.5mm (nearly centered)
avg_y: 3.0mm (slightly high - good for driver)
x_consistency: 2.5mm (tight pattern)
y_consistency: 3.0mm (tight pattern)
```

**Problem Pattern** (7 Iron):
```
avg_x: -4.5mm (consistent heel bias)
avg_y: -2.0mm (low on face)
x_consistency: 6.0mm (wide dispersion)
y_consistency: 5.0mm (wide dispersion)
→ Issue: Heel strikes + inconsistent contact
```

### 2. Heel vs Toe Bias

**Query**: Count heel vs toe strikes
```sql
SELECT
  club_name_std,
  COUNT(CASE WHEN impact_x < -2 THEN 1 END) as heel_strikes,
  COUNT(CASE WHEN ABS(impact_x) <= 2 THEN 1 END) as center_strikes,
  COUNT(CASE WHEN impact_x > 2 THEN 1 END) as toe_strikes
FROM shots
WHERE impact_x != 0
GROUP BY club_name_std;
```

**Diagnosis**:
- **Heel bias**: Standing too close, early release, or hands too far from body
- **Toe bias**: Standing too far, late release, or arms extending early
- **Center bias**: Good setup and swing mechanics

### 3. High vs Low on Face

**Query**: Analyze vertical strike patterns
```sql
SELECT
  club_name_std,
  COUNT(CASE WHEN impact_y > 3 THEN 1 END) as high_strikes,
  COUNT(CASE WHEN ABS(impact_y) <= 3 THEN 1 END) as center_strikes,
  COUNT(CASE WHEN impact_y < -3 THEN 1 END) as low_strikes
FROM shots
WHERE impact_y != 0
GROUP BY club_name_std;
```

**Diagnosis**:
- **High strikes (Driver)**: Good - launch angle optimization
- **High strikes (Irons)**: Problem - thin contact, reduced spin
- **Low strikes**: Fat contact, increased spin, distance loss
- **Center strikes**: Optimal contact and energy transfer

---

## Low Point Analysis

### Understanding Low Point

**Definition**: The lowest point of the club's swing arc relative to the ball

**Calculation**: `low_point = -(attack_angle / 2.0)` inches

**Interpretation**:
- **Negative value**: Low point before ball (descending blow)
- **Positive value**: Low point after ball (ascending blow)
- **Zero**: Level strike (attack angle = 0°)

### Ideal Low Points by Club

| Club Type | Ideal Attack Angle | Ideal Low Point | Why |
|-----------|-------------------|-----------------|-----|
| **Driver** | +3° to +5° | -1.5 to -2.5 inches | Hit up for max launch |
| **Fairway Woods** | -1° to +2° | +0.5 to -1.0 inches | Sweeping contact |
| **Long Irons** | -2° to -3° | +1.0 to +1.5 inches | Shallow descending |
| **Mid Irons** | -3° to -4° | +1.5 to +2.0 inches | Ball-first contact |
| **Short Irons** | -4° to -5° | +2.0 to +2.5 inches | Steeper descent |
| **Wedges** | -5° to -7° | +2.5 to +3.5 inches | Ball-turf contact |

### Query Low Point by Club

```sql
SELECT
  club_name_std,
  AVG(attack_angle) as avg_attack,
  AVG(low_point) as avg_low_point,
  MIN(low_point) as min_low_point,
  MAX(low_point) as max_low_point,
  COUNT(*) as shot_count
FROM shots
WHERE low_point IS NOT NULL
GROUP BY club_name_std
ORDER BY avg_attack DESC;
```

**Example Results**:
```
DRIVER:   attack=-0.5°,  low_point=+0.25"  → Too steep (should be positive attack)
IRON6:    attack=-2.8°,  low_point=+1.4"   → Good (ball-first contact)
WEDGEPW:  attack=-4.5°,  low_point=+2.25"  → Good (descending blow)
```

---

## Using Impact Images

### What Impact Images Show

**Typical Impact Image Contents**:
1. **Club Face**: Shows strike location with ball mark
2. **Ball**: Position at moment of contact
3. **Turf/Mat**: Ground interaction visible
4. **Face Angle**: Visual confirmation of open/closed face
5. **Lie Angle**: Visual confirmation of club orientation

### Visual Analysis Checklist

#### 1. Strike Location Verification

**Compare data vs visual**:
```
Data: impact_x = 2.0mm (toe), impact_y = 6.0mm (high)

Visual check:
- Look for ball mark on face
- Measure from center of face
- Confirm toe bias and high position
- Note: Data should match visual ±2mm
```

**If mismatch**:
- Sensor calibration issue (report to Uneekor)
- Impact tape needed for verification
- Check multiple shots for pattern

#### 2. Turf Interaction

**What to Look For**:

**Fat Contact** (low point too early):
- Divot starts before ball position
- Deep divot
- Turf visible spraying forward
- Data: attack_angle too steep, low_point too positive

**Thin Contact** (low point too late):
- Minimal or no divot
- Ball mark high on face
- Club bounces into ball
- Data: attack_angle too shallow, low_point negative

**Pure Contact** (ideal low point):
- Divot starts at/after ball position
- Shallow divot (irons)
- Clean turf removal
- Data: low_point matches ideal range for club

**Example Analysis**:
```
Shot 1298334:
- Data: attack_angle = -0.76°, low_point = +0.38"
- Visual: Minimal divot, turf spray starts at ball
- Assessment: ✓ Good contact for 6-iron
```

#### 3. Face Contact Pattern

**Sweet Spot Analysis**:
- Center strikes: Maximum ball speed, optimal spin
- Heel strikes: Reduced ball speed, right spin (RH)
- Toe strikes: Reduced ball speed, left spin (RH)
- High strikes: Reduced spin, more distance
- Low strikes: Increased spin, less distance

**Heat Map Creation** (Manual):
1. Mark impact location on face diagram for each shot
2. Color code by distance/accuracy
3. Identify patterns (clusters indicate consistency issues)

#### 4. Lie Angle Verification

**Visual Check**:
- Heel up = lie angle too upright
- Toe up = lie angle too flat
- Level = correct lie angle

**Data Correlation**:
```sql
SELECT shot_id, club_lie, lie_angle, impact_x
FROM shots
WHERE impact_img IS NOT NULL
ORDER BY shot_id DESC
LIMIT 10;
```

**Analysis**:
- Heel strikes + upright lie = club too upright for you
- Toe strikes + flat lie = club too flat for you
- Centered strikes = proper fit

---

## Turf Analysis from Images

### 1. Divot Pattern Recognition

**Fat Divot** (Problem):
```
Visual: ======●=====  (divot before ball)
Data:   attack_angle = -5°, low_point = +2.5"
Issue:  Hitting ground first, distance loss
Fix:    Weight forward, hands ahead
```

**Pure Divot** (Good):
```
Visual: ====●======  (divot after ball)
Data:   attack_angle = -3°, low_point = +1.5"
Result: Ball-first contact, optimal compression
```

**Thin/Topped** (Problem):
```
Visual: ●----------- (no divot, turf mark only)
Data:   attack_angle = +1°, low_point = -0.5"
Issue:  Bottoming out early, topped shot
Fix:    Maintain spine angle, finish swing
```

### 2. Divot Depth Analysis

**Shallow Divot** (Irons):
- Depth: ~1 inch
- Length: 3-4 inches
- Direction: Slightly left (for RH, target-line)
- Data correlation: attack_angle -3° to -4°

**Deep Divot** (Problem):
- Depth: >2 inches
- Visual: Large turf chunk
- Data correlation: attack_angle < -5°
- Issue: Too steep, energy wasted

**No Divot** (Driver/Woods):
- Brushing turf only
- Data correlation: attack_angle +2° to +5°
- Result: Ascending blow (good for woods)

### 3. Directional Analysis

**Divot Direction**:
- Points left → out-to-in path (slice tendency)
- Points straight → neutral path
- Points right → in-to-out path (draw tendency)

**Cross-reference with data**:
```sql
SELECT shot_id, club_path, impact_img
FROM shots
WHERE ABS(club_path) > 3
ORDER BY club_path DESC;
```

---

## AI-Assisted Image Analysis

### Future Enhancement: Gemini Vision Integration

**Proposed Workflow**:
1. Upload impact image to Gemini Vision API
2. Ask: "Analyze this golf impact - describe strike location, turf interaction, and divot pattern"
3. Compare AI analysis with sensor data
4. Generate coaching recommendations

**Example Prompt**:
```python
prompt = f"""
Analyze this golf swing impact image:
1. Strike location on club face (center/heel/toe, high/low)
2. Turf interaction pattern (divot depth, direction, starting point)
3. Ball position relative to divot
4. Quality assessment (pure/fat/thin)

Sensor data for reference:
- impact_x: {impact_x}mm
- impact_y: {impact_y}mm
- attack_angle: {attack_angle}°
- low_point: {low_point} inches

Provide coaching insights based on visual + data analysis.
"""
```

**Expected Output**:
- Visual verification of sensor accuracy
- Turf pattern description
- Contact quality assessment
- Coaching recommendations

---

## Practical Applications

### 1. Club Fitting Analysis

**Query for fitting session**:
```sql
SELECT
  club,
  AVG(impact_x) as avg_x,
  AVG(impact_y) as avg_y,
  AVG(club_lie) as avg_lie,
  COUNT(*) as shots
FROM shots
WHERE session_id = 'YOUR_SESSION_ID'
GROUP BY club;
```

**Fitting Insights**:
- Consistent heel strikes → need flatter lie angle
- Consistent toe strikes → need more upright lie angle
- Low face strikes → shaft too long or posture issue
- High face strikes → shaft too short or posture issue

### 2. Swing Change Tracking

**Before/After Comparison**:
```sql
-- Before swing change (old session)
SELECT AVG(impact_x) as old_avg_x, AVG(impact_y) as old_avg_y
FROM shots
WHERE session_date < '2025-01-01';

-- After swing change (new session)
SELECT AVG(impact_x) as new_avg_x, AVG(impact_y) as new_avg_y
FROM shots
WHERE session_date >= '2025-01-01';
```

**Track improvement**:
- Strike pattern centering
- Consistency improvement (lower STDDEV)
- Low point progression toward ideal

### 3. Practice Session Analysis

**Post-session query**:
```sql
SELECT
  club,
  COUNT(*) as shots,
  AVG(impact_x) as avg_x,
  AVG(impact_y) as avg_y,
  AVG(low_point) as avg_low_point,
  STDDEV(impact_x) as consistency_x,
  STDDEV(impact_y) as consistency_y
FROM shots
WHERE session_date = CURRENT_DATE()
GROUP BY club
ORDER BY shots DESC;
```

**Session Summary**:
- Which clubs had best contact?
- Which clubs need work?
- Was low point consistent?
- Did strike pattern improve during session?

---

## Troubleshooting Common Issues

### Issue 1: No Impact Data (All Zeros)

**Symptoms**:
```sql
SELECT COUNT(*) FROM shots WHERE impact_x = 0 AND impact_y = 0;
-- Returns high count
```

**Causes**:
- Launch monitor doesn't have Optix sensors (older models)
- Sensors not calibrated
- Mat/lighting conditions preventing detection
- Shot not registered by sensors

**Solution**:
- Use impact_img for visual analysis
- Upgrade to EYEXO or QED (have Optix)
- Manual impact tape analysis

### Issue 2: Erratic Low Point Calculations

**Symptoms**:
```sql
SELECT club, low_point
FROM shots
WHERE ABS(low_point) > 5
ORDER BY low_point;
-- Shows extreme values
```

**Causes**:
- Attack angle sensor error (99999 values)
- Topped or fat shots (extreme angles)
- Data cleaning not applied

**Solution**:
- Check for 99999 markers
- Filter extreme outliers: `WHERE ABS(low_point) < 5`
- Verify with impact images

### Issue 3: Impact Data Doesn't Match Visual

**Symptoms**:
- Data says center strike, image shows heel
- Data says shallow divot, image shows deep divot

**Causes**:
- Sensor calibration drift
- Wrong club profile selected on device
- Image from different shot (sync issue)

**Solution**:
- Calibrate launch monitor
- Verify club selection on device
- Check shot_id matches image URL
- Use impact tape for independent verification

---

## Advanced Analysis: Strike Dispersion

### Dispersion Chart Query

```sql
SELECT
  shot_id,
  club_name_std,
  impact_x,
  impact_y,
  carry,
  CASE
    WHEN impact_x BETWEEN -3 AND 3 AND impact_y BETWEEN -3 AND 3 THEN 'Sweet Spot'
    WHEN ABS(impact_x) > 5 OR ABS(impact_y) > 5 THEN 'Mis-hit'
    ELSE 'Acceptable'
  END as contact_quality
FROM shots
WHERE impact_x != 0 AND impact_y != 0
  AND club_name_std = 'IRON7'
ORDER BY carry DESC;
```

### Scatter Plot (Visualization)

**X-axis**: impact_x (heel to toe)
**Y-axis**: impact_y (low to high)
**Color**: carry distance or ball speed

**Pattern Analysis**:
- Tight cluster = consistent contact
- Spread pattern = inconsistent swing
- Bias pattern (heel/toe) = setup issue
- Vertical spread = swing plane issue

---

## Best Practices

### 1. Data Collection
- ✅ Import every practice session immediately
- ✅ Verify impact images are captured
- ✅ Check for 99999 markers after import
- ✅ Review data quality before analysis

### 2. Image Review
- ✅ Examine impact images for key shots
- ✅ Compare data vs visual for verification
- ✅ Look for turf interaction patterns
- ✅ Save problematic shots for coaching review

### 3. Pattern Tracking
- ✅ Run consistency queries weekly
- ✅ Track strike pattern changes over time
- ✅ Monitor low point trends by club
- ✅ Document improvements/regressions

### 4. Coaching Integration
- ✅ Share impact data with coach
- ✅ Use images to demonstrate issues
- ✅ Track swing changes with data
- ✅ Set measurable improvement goals

---

## Example Analysis Workflow

### Step 1: Import Session Data
```bash
# Import data (Streamlit UI or test_import.py)
python test_import.py
```

### Step 2: Quick Data Check
```sql
SELECT
  club_name_std,
  COUNT(*) as shots,
  AVG(impact_x) as avg_x,
  AVG(impact_y) as avg_y,
  AVG(low_point) as avg_low_point
FROM shots
WHERE session_date = '2024-12-27'
GROUP BY club_name_std;
```

### Step 3: Identify Problem Areas
```sql
-- Find shots with poor contact
SELECT shot_id, club, impact_x, impact_y, carry, impact_img
FROM shots
WHERE (ABS(impact_x) > 5 OR ABS(impact_y) > 5)
  AND session_date = '2024-12-27'
ORDER BY carry ASC;
```

### Step 4: Visual Verification
- Open impact_img URLs for problem shots
- Check turf interaction
- Verify strike location
- Note patterns (heel bias, thin contact, etc.)

### Step 5: Generate Report
```sql
-- Session summary
SELECT
  'Total Shots' as metric,
  COUNT(*) as value
FROM shots
WHERE session_date = '2024-12-27'

UNION ALL

SELECT
  'Sweet Spot %',
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM shots WHERE session_date = '2024-12-27'), 1)
FROM shots
WHERE session_date = '2024-12-27'
  AND ABS(impact_x) <= 3
  AND ABS(impact_y) <= 3;
```

---

## Future Enhancements

### Planned Features
1. **Automated Image Analysis** - Gemini Vision API integration
2. **Heat Map Generation** - Visual strike pattern clustering
3. **Coaching Alerts** - Automatic detection of swing issues
4. **Trend Detection** - ML-based pattern recognition
5. **Video Integration** - Full swing video + impact image correlation

### Contributing
See CLAUDE.md for development guidance on implementing these features.

---

**Last Updated**: December 27, 2024
**Version**: 1.0
**Author**: AI-Assisted Analysis System
