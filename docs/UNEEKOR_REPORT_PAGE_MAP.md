# Uneekor Report Page Structure Map

This document maps the structure of individual Power U Report pages for data extraction.

## Report Page URL

```
https://my.uneekor.com/power-u-report?id={REPORT_ID}&key={API_KEY}&distance={UNIT}&speed={SPEED_UNIT}
```

| Parameter | Description | Values |
|-----------|-------------|--------|
| `id` | Report/session ID | Integer (e.g., `43285`) |
| `key` | API authentication key | Alphanumeric string |
| `distance` | Distance unit | `yard` or `meter` |
| `speed` | Speed unit | `mph` or `kph` |

---

## Page Layout

```
+------------------------------------------------------------------+
|  [<]                    Power U Report           2026.01.25      |
|                                                                  |
|  [Profile]  matt    Hand: Right   Gender: Male                   |
|                     Distance: yard   Speed: mph                  |
+------------------------------------------------------------------+
|  [Summary] [Side] [Top] [Group] [Club] [Optix] [Swing]          |
+------------------------------------------------------------------+
|                                                                  |
|  +------------------+  +------------------+  +------------------+ |
|  | Carry            |  | Total            |  | Smash Fac.       | |
|  | 57.4 yard        |  | 64.5 yard        |  | 0.89             | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                  |
|  +------------------+  +------------------+  +------------------+ |
|  | Club Path        |  | Angles           |  | Speed            | |
|  | 5.7 L            |  | Launch: 42.9     |  | Ball: 56.3 mph   | |
|  |                  |  | Side: 1.2 L      |  | Club: 63.0 mph   | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                  |
|  +------------------+  +------------------+                      |
|  | Spin             |  | Shot             |                      |
|  | Back: 2637 rpm   |  | 1/41  [< >]      |                      |
|  | Side: 219 R      |  |                  |                      |
|  +------------------+  +------------------+                      |
|                                                                  |
+------------------------------------------------------------------+
|  Session: warmup              [SWING] [CSV] [ALL]               |
+------------------------------------------------------------------+
|  no | Distance      | Smash | Speed      | Spin       | Angle   |
|     | Carry|Tot|Side|Factor | Club|Ball  | Back|Side  | L|S|D   |
+------------------------------------------------------------------+
|  41 | 57.4|64.5|0.4L| 0.89  |63.0|56.3  |2637|219R   |42.9|... |
|  40 |181.6|188|35.8R| 1.37  |97.1|133.0 |7188|1657R  |18.8|... |
|  ...                                                             |
+------------------------------------------------------------------+
```

---

## Data Fields Reference

### Header Metadata

| Field | Location | Example |
|-------|----------|---------|
| Report Date | Header right | `2026.01.25` |
| Username | Profile section | `matt` |
| Hand | Profile section | `Right` |
| Gender | Profile section | `Male` |
| Distance Unit | Profile section | `yard` |
| Speed Unit | Profile section | `mph` |
| Session Name | Above shot table | `warmup` |
| Total Shots | Shot navigator | `41` |

### Summary Metrics Card

| Metric | Unit | Description |
|--------|------|-------------|
| Carry | yard/meter | Carry distance |
| Total | yard/meter | Total distance (carry + roll) |
| Smash Factor | ratio | Ball speed / Club speed |
| Club Path | degrees L/R | Club path relative to target |
| Launch Angle | degrees | Vertical launch angle |
| Side Angle | degrees L/R | Horizontal launch angle |
| Ball Speed | mph/kph | Ball velocity at impact |
| Club Speed | mph/kph | Club head speed at impact |
| Back Spin | rpm | Backspin rate |
| Side Spin | rpm L/R | Sidespin rate |

### Shot Table Columns

| Column | Sub-columns | Unit | Description |
|--------|-------------|------|-------------|
| no | - | int | Shot number (reverse order) |
| Distance | Carry | yard | Carry distance |
| | Total | yard | Total distance |
| | Side | yard L/R | Lateral deviation |
| Smash | Factor | ratio | Smash factor |
| Speed | Club | mph | Club head speed |
| | Ball | mph | Ball speed |
| Spin | Back | rpm | Backspin |
| | Side | rpm L/R | Sidespin |
| Angle | Launch | deg | Launch angle |
| | Side | deg L/R | Side angle |
| | Descent | deg | Descent angle |
| Apex | - | yard | Maximum height |
| Flight | Time | sec | Flight duration |
| Type | - | icon | Shot shape classification |

### Shot Shape Types

| Icon Name | Description |
|-----------|-------------|
| `straight` | Straight shot |
| `pullhookpushslice` | Pull-hook or push-slice |
| `pushslicepullhook` | Push-slice or pull-hook |
| `draw` | Draw shot |
| `fade` | Fade shot |
| `hook` | Hook shot |
| `slice` | Slice shot |

---

## API Export Endpoints

**CRITICAL DISCOVERY**: The report page exposes direct API endpoints for data export!

### Base URL
```
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/
```

### Endpoint: All Sessions CSV
```
GET /allsessions/{report_id}/{api_key}/{distance_unit}/{speed_unit}
```
**Example:**
```
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/allsessions/43285/CqueGwWNXRZU5cCB/yard/mph
```
**Returns:** CSV with all shots in the session

### Endpoint: Shot Data
```
GET /shotdata/{report_id}/{api_key}/{session_id}/{shot_id}/{distance_unit}/{speed_unit}
```
**Example:**
```
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/shotdata/43285/CqueGwWNXRZU5cCB/234797/1343991/yard/mph
```
**Returns:** Detailed shot data for specific shot

### Endpoint: Swing Optix
```
GET /swingoptix/{report_id}/{api_key}/{session_id}/{shot_id}
```
**Example:**
```
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/swingoptix/43285/CqueGwWNXRZU5cCB/234797/1343991
```
**Returns:** Swing analysis data (if Optix enabled)

### Authentication
- Uses the same `api_key` from the report URL
- No additional headers required
- Session cookies may be needed for some endpoints

---

## Navigation Tabs (Detailed)

### Tab 1: Summary
**Purpose:** Statistical aggregates for the session
**Content:**
- **Average Row:** Mean values across all shots (Carry, Total, Side, Smash, Speed, Spin, Angles, Apex, Flight Time)
- **Max Row:** Maximum values across all shots
- No visualization canvas - purely tabular data

| Statistic | Example Values |
|-----------|----------------|
| Average Carry | 128.7 yards |
| Average Total | 135.6 yards |
| Max Carry | 278.4 yards |
| Max Total | 296.0 yards |

---

### Tab 2: Side (Default Tab)
**Purpose:** Side-view trajectory visualization
**Content:**
- **Trajectory Canvas:** Ball flight paths from side angle
- **Y-Axis:** Height (0-80+ yards)
- **X-Axis:** Distance (0-300+ yards)
- **Gray Lines:** All shot trajectories
- **Yellow Line:** Currently selected shot (highlighted)
- Shows apex height, descent angle visually

---

### Tab 3: Top
**Purpose:** Top-down dispersion pattern
**Content:**
- **Bird's Eye View:** All shots from above
- **Y-Axis:** Left/right deviation
- **X-Axis:** Distance (0-275+ yards)
- **Semicircular Rings:** Distance interval markers at origin
- **Gray Lines:** All shot paths
- **Yellow Line:** Selected shot
- Best for visualizing shot consistency and miss patterns

---

### Tab 4: Group
**Purpose:** Statistical dispersion analysis
**Content:**
- **Scatter Plot:** Each dot = shot landing position
- **Dispersion Ellipse:** Orange oval showing shot spread boundary
- **Toggle Icons (top-right):**
  - Filled icon: Show all shots
  - Outline icon: Show ellipse only
- Shows natural clustering of shot groups (chips, irons, drivers)

---

### Tab 5: Club
**Purpose:** D-Plane swing mechanics visualization
**Content:**

**Left Panel (Side View):**
| Metric | Description | Example |
|--------|-------------|---------|
| Dynamic Loft | Loft at impact | 51.4° |
| Launch Angle | Vertical launch | 42.9° |
| Attack Angle | Angle of attack | -5.1° |
| Back Spin | Backspin rate | 2637 rpm |

**Right Panel (Face-On View):**
| Metric | Description | Example |
|--------|-------------|---------|
| Face Angle | Club face at impact | 5.6° L |
| Side Angle | Horizontal launch | 1.2° L |
| Club Path | Swing path direction | 5.7° L |
| Side Spin | Sidespin rate | 219 R |

- 3D club head visualizations at impact
- Arc indicators showing club path
- Critical for understanding ball flight physics

---

### Tab 6: Optix
**Purpose:** High-speed camera impact images
**Content:**
- **Left Panel:** Ball impact on club face
- **Right Panel:** Ball/club from alternate angle
- **Frame Navigator:** "1/24" with forward/back controls
- **Playback Controls:** Back, Play/Pause, Forward buttons
- **Toggle Buttons:** "Illust" vs "Photo" mode

**Data Fields:**
| Field | Description |
|-------|-------------|
| optix_x | Ball X position on face |
| optix_y | Ball Y position on face |
| club_lie | Lie angle at impact |
| Lie Angle | e.g., "UP 2.25" |

---

### Tab 7: Swing
**Purpose:** Video annotation canvas
**Content:**
- **Drawing Toolbar:**
  - Circle tool
  - Rectangle tool
  - Line/pencil tools
  - Undo/redo
  - Color options: Red, Blue, Yellow
  - Eraser
  - Trash (clear all)
- **Empty Canvas:** For swing video markup
- Used for coach-style video annotation

---

## Interactive Elements

### Shot Navigator
**Location:** Shot metrics card (bottom right of metrics row)
**Display:** "1/41" with `< >` arrow buttons

| Action | Result |
|--------|--------|
| Click `>` (right arrow) | Advance to next shot |
| Click `<` (left arrow) | Go to previous shot |
| Shows current/total | e.g., "2/41" |

**Behavior:**
- All metrics cards update to selected shot
- Trajectory visualization highlights selected shot (yellow)
- Table row selection syncs automatically

---

### Shot Row Selection
**Location:** Shot table rows
**Click Action:** Click anywhere on row to select that shot

**Behavior:**
- Same as using navigator arrows
- Row highlights in red/coral color when selected
- All views update to show selected shot data

---

### Eye Icon Toggle
**Location:** Left side of each shot row
**States:**
- **Open eye:** Shot visible in visualization
- **Crossed-out eye:** Shot hidden from visualization

**Behavior:**
- Click to toggle visibility
- Hidden shots dimmed in table
- Trajectory lines hidden from canvas
- Useful for focusing on specific shots or hiding outliers

---

### Export Buttons
**Location:** Above shot table, right side
**Buttons:** `[SWING]` `[CSV]` `[ALL]`

| Button | Action | Returns |
|--------|--------|---------|
| SWING | Download swing videos | Optix video files |
| CSV | Download session CSV | All shot numerical data |
| ALL | Download complete data | Shots + images + videos |

**Tooltips:**
- SWING: "Download Swing Optix Videos"
- CSV: "Download numerical data of all session shots"
- ALL: "Download all current shot data including club images and Swing Optix videos"

---

### Optix Frame Controls
**Location:** Optix tab, below image panels
**Controls:**
- **Frame indicator:** "1/24" (current/total frames)
- **Back button:** Previous frame
- **Play/Pause button:** Auto-advance through frames
- **Forward button:** Next frame
- **Illust/Photo toggle:** Switch between illustration and photo modes

---

## Data Extraction Strategy

### Method 1: Direct API (Recommended)
```python
import requests

def get_session_csv(report_id, api_key, distance='yard', speed='mph'):
    url = f"https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/allsessions/{report_id}/{api_key}/{distance}/{speed}"
    response = requests.get(url)
    return response.text  # CSV data
```

### Method 2: Page Scraping
```javascript
// Extract from shot table
const shots = [];
document.querySelectorAll('[ref^="e"][ref*="button"]').forEach(row => {
    // Parse button text which contains all shot data
    const text = row.getAttribute('aria-label') || row.textContent;
    // Parse: "eye {no} {carry} {total} {side} {smash} {club} {ball} {back} {side} {launch} {side_angle} {descent} {apex} {flight} {type}"
});
```

### Method 3: Network Interception
Monitor XHR/Fetch requests when page loads to capture:
- Initial data payload
- API authentication patterns
- Additional endpoints

---

## Sample Shot Data Row

```
Shot #41:
- Carry: 57.4 yards
- Total: 64.5 yards
- Side: 0.4 yards Left
- Smash Factor: 0.89
- Club Speed: 63.0 mph
- Ball Speed: 56.3 mph
- Back Spin: 2637 rpm
- Side Spin: 219 rpm Right
- Launch Angle: 42.9°
- Side Angle: 1.2° Left
- Descent Angle: 51.0°
- Apex: 16.7 yards
- Flight Time: 3.7 seconds
- Shot Type: straight
```

---

## Implementation Notes

1. **CSV Export is the most efficient** - Single API call returns all session data
2. **API keys are session-specific** - Each report has its own key
3. **Session IDs** (234797) and **Shot IDs** (1343991) are needed for individual shot exports
4. **Rate limiting** - Unknown limits on API, implement conservative delays
5. **Units** - Always specify `yard/mph` or `meter/kph` for consistent data

---

## UI to Database Field Mapping

Cross-reference of UI field names to scraper/database columns:

| UI Location | UI Label | Database Field | Notes |
|-------------|----------|----------------|-------|
| **Metrics Card** | Carry | `carry_distance` | Primary distance |
| Metrics Card | Total | `total_distance` | Carry + roll |
| Metrics Card | Smash Fac. | `smash` | Calculated: ball_speed / club_speed |
| Metrics Card | Club Path | `club_path` | Degrees L/R |
| Metrics Card | Launch (Angle) | `launch_angle` | Vertical launch |
| Metrics Card | Side (Angle) | `side_angle` | Horizontal launch |
| Metrics Card | Ball (Speed) | `ball_speed` | mph or kph |
| Metrics Card | Club (Speed) | `club_speed` | mph or kph |
| Metrics Card | Back (Spin) | `back_spin` | rpm |
| Metrics Card | Side (Spin) | `side_spin` | rpm L/R |
| **Shot Table** | no | `shot_number` | Reverse order in UI |
| Shot Table | Side (Distance) | `side_distance` | Lateral deviation |
| Shot Table | Descent | `decent_angle` | Note: typo in API |
| Shot Table | Apex | `apex` | Max height |
| Shot Table | Flight | `flight_time` | Seconds |
| Shot Table | Type | `shot_type` | Shape classification |
| **Club Tab** | Dynamic Loft | `dynamic_loft` | Degrees |
| Club Tab | Attack Angle | `attack_angle` | Degrees |
| Club Tab | Face Angle | `club_face_angle` | Degrees L/R |
| **Optix Tab** | Impact X | `optix_x` | Ball position on face |
| Optix Tab | Impact Y | `optix_y` | Ball position on face |
| Optix Tab | Club Lie | `club_lie` | Lie angle |
| Optix Tab | Lie Angle | `lie_angle` | e.g., "UP 2.25" |

---

## Exploration Verification Checklist

**Completed 2026-01-26:**

- [x] All 7 tabs explored with documentation
- [x] Shot row click behavior verified (selects shot)
- [x] Shot navigator arrows verified (cycles through shots)
- [x] Eye icon toggle verified (hides/shows from visualization)
- [x] Export button URLs documented
- [x] All data fields mapped to scraper fields
- [x] Interactive elements fully documented

---

## Portal Session Listing - Pagination Issue

### Discovery (2026-01-26)

**CRITICAL BUG FOUND:** The `automation/uneekor_portal.py` does NOT handle pagination!

The portal session listing at `https://my.uneekor.com/report`:
- Shows **10 sessions per page**
- Has **8 pages total** (as of 2026-01-26)
- **Total sessions: 80**

But the current `get_all_sessions()` method only scrapes page 1!

### Pagination Details

| Page | Sessions | Running Total |
|------|----------|---------------|
| 1 | 10 | 10 |
| 2 | 10 | 20 |
| 3 | 10 | 30 |
| 4 | 10 | 40 |
| 5 | 10 | 50 |
| 6 | 10 | 60 |
| 7 | 10 | 70 |
| 8 | 10 | 80 |

### Pagination UI Elements

```
Page selector buttons: [1] [2] [3] [4] [5] [6] [7] [8]
Selector patterns:
- button:text-is("N") - numeric page buttons
- a:text-is("N") - alternative link format
```

### Impact

- Current database shows only **30 sessions** (partial data)
- Actual portal has **80 sessions**
- **50 sessions are MISSING** from discovery

### Required Fix

The `UneekorPortalNavigator.get_all_sessions()` method needs pagination loop:

```python
# Pseudocode for fix needed in uneekor_portal.py
async def get_all_sessions(self):
    all_sessions = []
    page_num = 1

    while True:
        # Get sessions on current page
        sessions = await self._find_session_links()
        all_sessions.extend(sessions)

        # Try to go to next page
        next_btn = await page.query_selector(f'button:text-is("{page_num + 1}")')
        if not next_btn or not await next_btn.is_visible():
            break

        await next_btn.click()
        await page.wait_for_load_state('networkidle')
        page_num += 1

    return all_sessions
```

---

## Related Files

| File | Purpose |
|------|---------|
| `golf_scraper.py` | Current scraping implementation |
| `automation/uneekor_portal.py` | Portal navigation |
| `docs/UNEEKOR_PORTAL_MAP.md` | Portal listing page structure |
