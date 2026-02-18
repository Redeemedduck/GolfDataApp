# Uneekor Power U Report — Complete Data Map & Skill File

## Purpose
This document maps every aspect of the Uneekor my.uneekor.com Power U Report system — from the session listing page through every visualization tab, data point, and structural relationship. Use this as the canonical reference when building features that import, display, or analyze Uneekor data.

---

## 1. Report Listing Page (`my.uneekor.com/report`)

### Structure
- Title: "Power U Report (VIEW)"
- Paginated table (configurable: 5/10/20/30 per page)
- Searchable by keyword

### Table Columns
| Column | Description |
|--------|-------------|
| Session Name | User-editable free-text name (pencil icon to rename). This is what the user typed when saving the session in the Uneekor software. |
| Date | Date session was recorded (e.g., "Feb 12, 2026") |
| User Name | Player name from Uneekor account (e.g., "matt") |
| Shots | Total shot count across ALL club groups in the session |
| Open Report | Folder icon → opens full report in new tab |
| Delete Report | Trash icon → deletes the report |

### Session Name Conventions (User-Defined, Not Standardized)
Session names are entirely freeform. In practice, the user (matt) uses several naming patterns:

**Club-focused practice sessions** (single club):
- "Iron 1", "Iron 6", "Iron 9", "9", "Driver", "driver"
- These sessions typically contain 1-2 club groups (the main club + sometimes a warmup)

**Course/round sessions** (multi-club sim golf):
- "sgt pebble", "dpc scottsdale", "dpt scottsdale sgt1", "broadmore east front", "broadmoar"
- "sgt" prefix = likely SGT (sim golf tournament) rounds
- Course names include: Pebble Beach, Scottsdale, Broadmoor, Kapalua, Wailaie, Plantation, Shadow Ridge, Silvertip, Streamsong, Estes Park, Magnolia
- These contain many club groups (3-9+ different clubs used during the round)

**Warmup sessions**:
- "warmup", "8 iron magnolia", "9 iron magnolia"
- Shorter sessions, often 10-30 shots

**Date-based sessions**:
- "2026.2.12" — just the date, no descriptive name

**CRITICAL INSIGHT**: The session name is NOT the club. A session named "sgt pebble" contains clubs like IRON1, 50WEDGE, PITCHINGWEDGE. A session named "dpc scottsdale" contains IRON1, IRON8, DRIVER, 60WEDGE, 50WEDGE, PITCHINGWEDGE, IRON9, etc. The session name describes WHAT the player was doing; the club groups within describe WHICH clubs were used.

### Report URL Structure
```
/power-u-report?id={REPORT_ID}&key={ACCESS_KEY}&distance={yard|meter}&speed={mph|kph}
```
- `id`: Unique numeric report ID
- `key`: Alphanumeric access key (required for viewing)
- `distance`: Unit preference (yard or meter)
- `speed`: Unit preference (mph or kph)

---

## 2. Report Header

### Top Bar (persistent across all tabs)
- Uneekor logo + "Power U Report" title
- Date: Format `YYYY.MM.DD` (e.g., "2026.02.02")
- User avatar + name (clickable)

### User Profile Popup (click the ⓘ icon next to username)
| Field | Example | Notes |
|-------|---------|-------|
| Hand | R / L | Right or left handed |
| Gender | M / F | |
| Distance | yard / meter | Unit preference |
| Speed | mph / kph | Unit preference |

---

## 3. Session/Club Navigation (Left Sidebar)

### Structure
The left sidebar lists all **club groups** within the session. Each entry shows:
```
● (SHOT_COUNT) CLUB_NAME
  DATE
```

### Color Coding
Each club group has a colored dot (●) that matches its color in the Group trajectory view:
- Pink/Red, Yellow, Green, Blue, Orange, White, etc.
- Colors are assigned sequentially to club groups

### Example (dpc scottsdale session — 80 total shots):
```
● (26) dpc scottsdale    ← "main" group, named same as session
  2026.02.02
● (3) Iron 8
  2026.02.02
● (4) Driver
  2026.02.02
● (3) 70 yds             ← distance-based club label
  2026.02.02
● (3) Wedge 50
  2026.02.02
● (3) Wedge Pitching
  2026.02.02
● (3) Iron 9
  2026.02.02
● (6) Wedge 60
  2026.02.02
● (29) warmup            ← warmup shots grouped separately
  2026.02.02
```

### Behavior
- Clicking a club group filters ALL views (Summary, Side, Top, Group, Club, Optix, Swing) to show only that club's shots
- The currently selected club group is highlighted
- The shot data table at the bottom updates to show only that club's shots
- The shot counter (e.g., "Shot 1/26") resets per club group

### CRITICAL: Club Group Naming
Club groups within a session use Uneekor's internal club classification. These names come from the club selection in the Uneekor software, NOT from the session name. Common patterns:
- `IRON1`, `IRON8`, `IRON9` — iron numbers
- `DRIVER` — driver
- `50WEDGE`, `60WEDGE`, `PITCHINGWEDGE` — wedge types with degree or name
- `Wedge 50`, `Wedge 60`, `Wedge Pitching` — alternate wedge naming (in sidebar)
- `70 yds` — sometimes distance-based labels
- `warmup` — warmup shots grouped separately
- The first/main group often inherits the session name (e.g., "dpc scottsdale")

---

## 4. Visualization Tabs

### Tab Bar (horizontal, persistent)
Seven tabs in order: **Summary | Side | Top | Group | Club | Optix | Swing**

---

### 4a. Summary Tab

#### Simple Format (narrow viewport / older reports)
Shows pill buttons for each club group at the top:
```
[Summary] [IRON1 (52)] [50WEDGE (15)] [PITCHINGWEDGE (30)]
```
- Chevron (∨/∧) to expand/collapse the pill list
- Summary view shows a comparison table of all club groups

#### Summary Table
| Column Group | Columns | Description |
|-------------|---------|-------------|
| SESSION | Club group name | Row identifier with colored dot |
| DISTANCE | Carry, Total, Side | Carry distance, total distance, side distance (with L/R) |
| SMASH | Factor | Smash factor (ball speed / club speed) |
| SPEED | Club, Ball | Club head speed, ball speed (in mph) |
| SPIN | Back, Side | Backspin (rpm), sidespin (with L/R) |
| ANGLE | Launch, Side, Descent | Launch angle, side angle (with L/R), descent angle |
| APEX | Apex | Maximum height in yards |
| TIME | Time | Flight time in seconds |
| TYPE | Type | Shot type indicator |

Shows two rows per view: **Average** and **Max** for the selected club group.

#### Full Format (wide viewport)
Same data as above but with a richer summary table showing each club group as a row with averaged values.

Bottom section shows the per-club summary:
```
IRON1(26) | IRON8(3) | DRIVER(4) | 60WEDGE(3) | 50WEDGE(3) | PITCHINGWEDGE(3) | IRON9(3) | 60WEDGE(6) | PITCHINGWEDGE(29)
```

---

### 4b. Side Tab (Ball Flight — Side View)

**Visualization**: 2D trajectory arcs showing ball flight from the side (height vs distance).
- X-axis: Distance in yards (0 to 300+)
- Y-axis: Height in yards (0 to 80+)
- Each shot is a colored arc (pink/red for the selected club group)
- Grid lines at distance intervals (25, 50, 75, 100, etc.)
- All shots from the selected club group are overlaid

**Key Insight**: Shows trajectory shape — high vs low shots, carry distance clustering, etc.

---

### 4c. Top Tab (Ball Flight — Top/Overhead View)

**Visualization**: 2D trajectory lines showing ball flight from above (left-right dispersion vs distance).
- X-axis: Distance in yards
- Y-axis: Left/Right deviation
- Shows the "spread pattern" of shots
- Each shot is a colored line from tee to landing

**Key Insight**: Shows shot dispersion — draw/fade patterns, consistency of direction.

---

### 4d. Group Tab (Combined Dispersion View)

**Visualization**: Bird's-eye landing zone display with distance rings.
- Shows ALL club groups simultaneously, color-coded by club
- Each shot is a colored dot at its landing position
- Distance markers along the centerline (13, 65, 130, 195, 260, 325 yds)
- Oval/ellipse dispersion boundaries per club group
- Camera angle toggles in top-right corner

**Key Insight**: The "bag map" — shows how all clubs relate to each other in terms of distance and dispersion. Instantly shows distance gapping between clubs.

---

### 4e. Club Tab (Impact Analysis)

**Visualization**: Two side-by-side club face diagrams showing:

**Left diagram** (face-on view):
- Dynamic Loft angle
- Launch Angle (green text)
- Attack Angle indicator

**Right diagram** (looking down at club):
- Face Angle (red/green text)
- Side Angle (blue text)
- Club Path arrow

**Data displayed above diagrams**:
| Metric | Position | Color |
|--------|----------|-------|
| Dynamic Loft | Top-left | Cyan |
| Launch Angle | Top-center | Green |
| Face Angle | Top-right-left | Red/Green |
| Side Angle | Top-right-right | Blue |

**Data displayed below diagrams**:
| Metric | Position | Color |
|--------|----------|-------|
| Attack Angle | Bottom-left | Orange |
| Back Spin | Bottom-center-left | Red |
| Club Path | Bottom-center-right | Pink |
| Side Spin | Bottom-right | Red |

---

### 4f. Optix Tab (Impact Photos)

**Toggle**: `Illust` | `Photo`
- **Illust**: Illustrated/rendered view of ball impact on club face
- **Photo**: Actual camera photo of impact (if available from Uneekor hardware)
- Counter: `1/24` — browse through impact images per shot
- Shows the physical evidence of where the ball struck the club face

---

### 4g. Swing Tab (Swing Video)

**Visualization**: Video playback area for Swing Optix recordings.
- Drawing tools toolbar at top: eye icon (visibility), circle, square, line, curve, rotate, eraser, color selectors (red, blue, yellow), layers, trash
- These tools let the user annotate the swing video for coaching
- Shot navigation via the data table below

---

## 5. Per-Shot Statistics Bar (Persistent Below Visualization)

This horizontal bar appears below ALL visualization tabs and shows stats for the currently selected shot:

| Metric | Unit | Description |
|--------|------|-------------|
| Carry | yard | Carry distance (air distance before first bounce) |
| Total | yard | Total distance including roll |
| Smash Fac. | ratio | Ball speed ÷ club speed (efficiency of impact) |
| Club Path | degrees + L/R | Club head path relative to target line (+ = in-to-out/draw, - = out-to-in/fade) |
| Launch (Angle) | degrees | Vertical launch angle |
| Side (Angle) | degrees + L/R | Horizontal launch direction |
| Ball Speed | mph | Ball velocity at launch |
| Club Speed | mph | Club head velocity at impact |
| Back Spin | rpm | Backspin rate |
| Side Spin | rpm + L/R | Sidespin (positive = slice spin for RH) |
| Shot | n/total | Shot counter within current club group |

### Shot Navigation
- `<` and `>` arrow buttons to step through shots one at a time
- Currently selected shot is highlighted in the data table below

---

## 6. Per-Shot Data Table (Bottom Section)

### Header
Shows the club group name in uppercase (e.g., "DPC SCOTTSDALE", "DRIVER", "IRON1")

### Download Buttons (top-right of table)
| Button | Description |
|--------|-------------|
| SWING | Download Swing Optix Videos for this club group |
| CSV | Download numerical data of all session shots as CSV |
| ALL | Download all current shot data including club images and Swing Optix videos |

### Table Columns
| Column Group | Column | Type | Description |
|-------------|--------|------|-------------|
| — | 👁 (eye icon) | button | Toggle shot visibility in trajectory views |
| — | no | integer | Shot number (descending — most recent first) |
| Distance | Carry | float | Carry distance in yards |
| Distance | Total | float | Total distance in yards |
| Distance | Side | float + L/R | Side distance (lateral deviation from target) |
| Smash | Factor | float | Smash factor ratio |
| Speed | Club | float | Club head speed in mph |
| Speed | Ball | float | Ball speed in mph |
| Spin | Back | integer | Backspin in rpm |
| Spin | Side | integer + L/R | Sidespin in rpm with direction |
| Angle | Launch | float | Launch angle in degrees |
| Angle | Side | float + L/R | Side angle in degrees with direction |
| Angle | Descent | float | Descent/landing angle in degrees |
| Apex | Apex | float | Maximum height in yards |
| Time | Flight | float | Total flight time in seconds |
| Type | Type | icon | Shot shape indicator (draw/fade/straight arrows) |

### Row Behavior
- Currently selected shot row is highlighted in pink/red
- Clicking a row selects that shot and updates all visualizations above
- Shot numbers count DOWN from total (newest shot = highest number, displayed first)
- The eye icon toggles visibility of individual shots in the trajectory visualizations

---

## 7. Data Relationships & Hierarchy
```
UNEEKOR ACCOUNT (matt)
  └── REPORT (session)
        ├── Report ID: unique numeric (e.g., 43806)
        ├── Session Name: user-editable string (e.g., "dpc scottsdale")
        ├── Date: YYYY.MM.DD
        ├── User Settings: hand, gender, distance unit, speed unit
        ├── Total Shots: sum of all club groups
        │
        └── CLUB GROUPS (1 to N per session)
              ├── Club Name: from Uneekor's club selection (e.g., "IRON1", "DRIVER", "50WEDGE")
              ├── Shot Count: number of shots with this club
              ├── Color: assigned for visualization
              │
              └── SHOTS (1 to N per club group)
                    ├── Shot Number: sequential within club group
                    ├── Distance: carry, total, side
                    ├── Smash Factor
                    ├── Speed: club, ball
                    ├── Spin: back, side
                    ├── Angles: launch, side, descent
                    ├── Apex height
                    ├── Flight time
                    ├── Shot type
                    ├── Club Impact Data: dynamic loft, face angle, attack angle, club path, lie angle
                    ├── Optix Image: illustration and/or photo of club face impact
                    └── Swing Video: Swing Optix recording (if available)
```

---

## 8. Key Differences: Session Name vs Club Name

| Concept | Source | Examples | Purpose |
|---------|--------|----------|---------|
| Session Name | User types this when saving | "sgt pebble", "dpc scottsdale", "Iron 1", "warmup", "2026.2.12" | Describes the ACTIVITY (round, practice, warmup) |
| Club Group Name | Uneekor software assigns based on club selection | "IRON1", "DRIVER", "50WEDGE", "PITCHINGWEDGE" | Identifies the CLUB used for those shots |

### The mapping is ONE session → MANY club groups → MANY shots per group

A session named "dpc scottsdale" (a sim round at TPC Scottsdale) contains:
- 26 shots labeled "dpc scottsdale" (main/default group)
- 3 shots with Iron 8
- 4 shots with Driver
- 3 shots at 70 yds
- 3 shots with Wedge 50
- 3 shots with Wedge Pitching
- 3 shots with Iron 9
- 6 shots with Wedge 60
- 29 warmup shots

### Club Name Variations Observed
The same physical club may appear with different names across sessions:
- 1 Iron: "IRON1", "Iron 1", "Iron1", "1 Iron"
- 7 Iron: "IRON7", "Iron 7", "7", "M 7", "M 7 Iron"
- 8 Iron: "IRON8", "Iron 8", "8"
- 9 Iron: "IRON9", "Iron 9", "9"
- Pitching Wedge: "PITCHINGWEDGE", "Wedge Pitching", "PW"
- 50-degree Wedge: "50WEDGE", "Wedge 50", "50 Warmup"
- 56-degree Wedge: "56", "M 56"
- 60-degree Wedge: "60WEDGE", "Wedge 60", "GW"
- Sand Wedge: "SW"
- Driver: "DRIVER", "Driver", "driver"
- 3 Wood: "Wood 3"

---

## 9. Report Format Variants

### Narrow/Mobile Format
- No left sidebar
- Club groups shown as horizontal pill buttons: `[Summary] [IRON1 (52)] [50WEDGE (15)]`
- Expandable/collapsible with chevron
- Simpler summary table (Average row only per club group in summary)
- Per-shot view when clicking a club pill shows individual shot details with stat cards

### Wide/Desktop Format
- Full left sidebar with color-coded club group navigation
- All 7 visualization tabs (Summary, Side, Top, Group, Club, Optix, Swing)
- Richer summary table with Average and Max rows
- Full data table with all columns visible
- Drawing tools on Swing tab

---

## 10. Typical Session Patterns & Expected Data

| Session Type | Naming Pattern | Club Groups | Shot Count | Characteristics |
|-------------|---------------|-------------|------------|-----------------|
| Sim Round | Course name: "sgt pebble", "dpc scottsdale", "broadmore east front" | 5-10 different clubs | 40-100+ | Wide variety of clubs, distances range from wedge to driver |
| Single-Club Practice | Club name: "Iron 1", "Driver", "9" | 1-2 (main + warmup) | 30-70 | Consistent club, focus on repetition |
| Warmup | "warmup" | 1-3 | 20-40 | Mixed clubs, shorter distances, often precedes a practice or round |
| Fitting/Testing | "Bag Mapping", "8 iron magnolia" | 1-3 | 10-50 | Specific club testing, often at specific courses |
| Drill | Activity-based: would be things like speed drills, partial swings | 1 | 10-30 | Specific swing mechanic focus |

---

## 11. Data Points Reference (All Metrics)

### Ball Flight Metrics
| Metric | Unit | Range (typical) | Description |
|--------|------|-----------------|-------------|
| Carry Distance | yards | 3-330 | Air distance before first bounce |
| Total Distance | yards | 4-350 | Including roll after landing |
| Side Distance | yards + L/R | 0-100 | Lateral deviation from target line |
| Ball Speed | mph | 14-167 | Ball velocity at launch |
| Launch Angle | degrees | 8-50 | Vertical angle at launch |
| Side Angle | degrees + L/R | 0-17 | Horizontal angle at launch |
| Descent Angle | degrees | 16-53 | Landing angle |
| Apex | yards | 0.2-52 | Maximum height of ball flight |
| Flight Time | seconds | 0.2-7.8 | Time ball is airborne |
| Back Spin | rpm | 806-11210 | Backspin rate |
| Side Spin | rpm + L/R | 0-2507 | Sidespin (affects curve) |

### Club Delivery Metrics
| Metric | Unit | Description |
|--------|------|-------------|
| Club Speed | mph | Club head velocity at impact |
| Smash Factor | ratio | Ball Speed ÷ Club Speed (1.0-1.51 typical) |
| Club Path | degrees + L/R | Club head direction relative to target (+=in-to-out, -=out-to-in) |
| Face Angle | degrees + Open/Closed | Club face orientation at impact |
| Attack Angle | degrees + Up/Down | Club head vertical approach angle |
| Dynamic Loft | degrees | Actual loft presented at impact |
| Lie Angle | degrees + Up/Down | Club lie angle at impact |

### Derived/Calculated
| Metric | Calculation | Significance |
|--------|------------|--------------|
| Face-to-Path | Face Angle - Club Path | Determines curve: >0 = draw spin, <0 = fade spin |
| Shot Shape | Combination of path + face | Draw, fade, pull, push, straight |
| Consistency (Std Dev) | Standard deviation of metric | Lower = more consistent |

---

## 12. URL Patterns for API/Scraping Reference

### Report Listing
```
GET https://my.uneekor.com/report
```

### Individual Report  
```
GET https://my.uneekor.com/power-u-report?id={ID}&key={KEY}&distance=yard&speed=mph
```

### CSV Download (per report)
Available via the CSV button in the data table section. Downloads all shots for the current club group or full session.

---

## 13. What the My Golf Lab App Should Import

For each Uneekor report, the app needs to capture:

### Session Level
- Session name (user-editable label)
- Date
- Total shots
- User profile (hand, gender, units)
- Report ID and key (for re-fetching)

### Club Group Level  
- Club group name (the ACTUAL club, e.g., "IRON1", "DRIVER")
- Shot count per club group
- This is SEPARATE from the session name

### Shot Level (per shot)
- All ball flight metrics: carry, total, side, ball_speed, launch_angle, side_angle, descent_angle, apex, flight_time, back_spin, side_spin
- All club delivery metrics: club_speed, smash_factor, club_path, face_angle, attack_angle, dynamic_loft, lie_angle
- Shot number within club group
- Which club group this shot belongs to
- Shot type indicator