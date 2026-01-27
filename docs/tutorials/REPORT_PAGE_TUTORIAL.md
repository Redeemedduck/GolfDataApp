# Understanding the Uneekor Report Page

A complete guide to navigating and analyzing your golf data in the Power U Report interface.

---

## Table of Contents

1. [Overview](#overview)
2. [The Seven Tabs at a Glance](#the-seven-tabs-at-a-glance)
3. [Tab Deep Dive](#tab-deep-dive)
4. [Interactive Elements](#interactive-elements)
5. [How Data Flows Between Tabs](#how-data-flows-between-tabs)
6. [Practical Analysis Workflows](#practical-analysis-workflows)
7. [Quick Reference](#quick-reference)

---

## Overview

The Uneekor Power U Report page is your command center for analyzing golf shot data. Every session you record is available as an interactive report containing trajectory visualizations, swing mechanics data, and high-speed impact imagery.

```
+------------------------------------------------------------------+
|                        REPORT PAGE LAYOUT                        |
+------------------------------------------------------------------+
|  Header: Profile info, date, units (yard/mph or meter/kph)       |
+------------------------------------------------------------------+
|  [Summary] [Side] [Top] [Group] [Club] [Optix] [Swing]           |
+------------------------------------------------------------------+
|                                                                  |
|              VISUALIZATION AREA (changes per tab)                |
|                                                                  |
+------------------------------------------------------------------+
|              METRICS CARDS (8 data categories)                   |
+------------------------------------------------------------------+
|                    SHOT TABLE (all shots)                        |
+------------------------------------------------------------------+
```

**Key Concept:** The report page has TWO persistent sections across all tabs:
- **Metrics Cards** - Summary statistics for the selected shot
- **Shot Table** - All shots in the session with full data

The VISUALIZATION AREA changes based on which tab you select.

---

## The Seven Tabs at a Glance

```
+----------+----------+----------+----------+----------+----------+----------+
| SUMMARY  |   SIDE   |   TOP    |  GROUP   |   CLUB   |  OPTIX   |  SWING   |
+----------+----------+----------+----------+----------+----------+----------+
| Numbers  | Flight   | Where    | Patterns | How You  | Impact   | Video    |
| Only     | Profile  | It Lands | & Spread | Struck It| Photos   | Markup   |
+----------+----------+----------+----------+----------+----------+----------+
|          |          |          |          |          |          |          |
| Avg/Max  | Height   | Left/    | Scatter  | D-Plane  | High-    | Drawing  |
| Stats    | vs       | Right    | Plot +   | Angles   | Speed    | Tools    |
|          | Distance | Spread   | Ellipse  |          | Frames   |          |
+----------+----------+----------+----------+----------+----------+----------+
```

| Tab | Primary Question It Answers |
|-----|----------------------------|
| **Summary** | "What were my average and best numbers?" |
| **Side** | "What does my ball flight look like?" |
| **Top** | "Where are my shots landing left to right?" |
| **Group** | "How consistent is my dispersion?" |
| **Club** | "What's happening at impact?" |
| **Optix** | "Where did I hit it on the face?" |
| **Swing** | "Can I annotate my swing video?" |

---

## Tab Deep Dive

### Tab 1: Summary

```
+------------------------------------------------------------------+
|                         SUMMARY TAB                              |
+------------------------------------------------------------------+
|                                                                  |
|   +-------------------+-------------------+-------------------+  |
|   | AVERAGE VALUES    | MAXIMUM VALUES    |                   |  |
|   |                   |                   |                   |  |
|   | Carry: 185.2 yds  | Carry: 278.4 yds  |                   |  |
|   | Total: 198.7 yds  | Total: 296.0 yds  |                   |  |
|   | Ball Speed: 142   | Ball Speed: 168   |                   |  |
|   | ... (all metrics) | ... (all metrics) |                   |  |
|   +-------------------+-------------------+-------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

**Purpose:** Quick statistical overview without visualizations.

**What You See:**
- Average row: Mean values across ALL shots in session
- Max row: Best values for each metric

**When to Use:**
- At the start of analysis to get baseline numbers
- To compare session-to-session performance
- When sharing quick stats without details

**Key Metrics Shown:**
| Metric | What It Tells You |
|--------|-------------------|
| Avg Carry | Your typical carry distance |
| Max Carry | Your best shot potential |
| Avg Ball Speed | Consistent power indicator |
| Avg Launch Angle | Ball flight tendency |

---

### Tab 2: Side (Default View)

```
+------------------------------------------------------------------+
|                          SIDE TAB                                |
+------------------------------------------------------------------+
|                                                                  |
|     Height (yards)                                               |
|       80 |                                                       |
|          |            ___                                        |
|       60 |          ./   \___   <- Apex (highest point)          |
|          |        ./         \___                                |
|       40 |      ./               \___                            |
|          |    ./                     \___                        |
|       20 |  ./                           \___                    |
|          |./                                 \___                |
|        0 +----------------------------------------> Distance     |
|          0        100       200       300                        |
|                                                                  |
|     [Gray lines = all shots]  [Yellow line = selected shot]      |
+------------------------------------------------------------------+
```

**Purpose:** Visualize ball flight trajectory from a side angle.

**What You See:**
- All shots overlaid as trajectory arcs
- Currently selected shot highlighted in yellow
- Height (y-axis) vs distance (x-axis)

**When to Use:**
- Analyzing launch angle consistency
- Comparing trajectory shapes across clubs
- Identifying shots with unusual apex heights
- Checking descent angles (important for greens holding)

**Pro Tips:**
- High apex = high spin, soft landing
- Low, penetrating trajectory = wind-resistant
- Compare driver vs irons to see different flight profiles

---

### Tab 3: Top (Bird's Eye View)

```
+------------------------------------------------------------------+
|                          TOP TAB                                 |
+------------------------------------------------------------------+
|                                                                  |
|   Left                                                           |
|     +  |                         o                               |
|        |                    o  o   o                             |
|        |                 o    o  o    o                          |
|   0 ---+---------------o--o--X--o--o---------> Distance          |
|        |              o    o   o    o                            |
|        |                  o   o  o                               |
|     -  |                     o                                   |
|   Right                                                          |
|        0         100        200        300                       |
|                                                                  |
|   [o = landing spots]  [X = selected shot]  [--- = target line]  |
+------------------------------------------------------------------+
```

**Purpose:** See dispersion pattern from above.

**What You See:**
- All shots plotted by landing position
- Semicircular distance rings at origin
- Left/right deviation clearly visible

**When to Use:**
- Analyzing your miss pattern (do you miss left or right?)
- Checking dispersion width for consistency
- Identifying outliers in your shot pattern

**Pro Tips:**
- Consistent players have tight clusters
- If all shots miss one direction, that's your stock shot shape
- Use this to set aim points on course (aim for center of your pattern)

---

### Tab 4: Group (Dispersion Analysis)

```
+------------------------------------------------------------------+
|                         GROUP TAB                                |
+------------------------------------------------------------------+
|                                                                  |
|        Left                                                      |
|          |         ____________________________                  |
|          |       ./                            \.                |
|          |      /    o   o    o                  \               |
|          |     |   o    o   o   o    o            |              |
|          |     |      o   o   o    o              |              |
|          |      \   o    o   o   o              ./               |
|          |       \.__________________________./                  |
|        Right                                                     |
|          +-----------------------------------------------> Dist  |
|                                                                  |
|    [Orange ellipse = dispersion boundary]                        |
|    Toggle: [Show All] [Show Ellipse Only]                        |
+------------------------------------------------------------------+
```

**Purpose:** Statistical dispersion visualization with confidence ellipse.

**What You See:**
- Scatter plot of all shot landing positions
- Orange dispersion ellipse showing shot spread boundary
- Toggle to show/hide the ellipse

**When to Use:**
- Understanding your typical shot spread
- Identifying if you have distinct shot clusters (chips vs full swings)
- Calculating course management (where can you miss safely?)

**Key Insight:**
The ellipse represents where roughly 95% of your shots will land. This is your "danger zone" for course planning.

---

### Tab 5: Club (D-Plane Mechanics)

```
+------------------------------------------------------------------+
|                          CLUB TAB                                |
+------------------------------------------------------------------+
|                                                                  |
|   SIDE VIEW                         FACE-ON VIEW                 |
|   +-------------------+             +-------------------+        |
|   |                   |             |                   |        |
|   |     [Club Head]   |             |     [Club Head]   |        |
|   |        /          |             |        /          |        |
|   |       /           |             |       /   Face    |        |
|   |      / Attack     |             |      /    Angle   |        |
|   |     /  Angle      |             |     /             |        |
|   |    /              |             |    /              |        |
|   |   /               |             |   /  Club Path    |        |
|   +-------------------+             +-------------------+        |
|                                                                  |
|   Dynamic Loft: 51.4 deg            Face Angle: 5.6 deg L        |
|   Launch Angle: 42.9 deg            Side Angle: 1.2 deg L        |
|   Attack Angle: -5.1 deg            Club Path:  5.7 deg L        |
|   Back Spin:    2637 rpm            Side Spin:  219 rpm R        |
|                                                                  |
+------------------------------------------------------------------+
```

**Purpose:** Understand the physics of impact (D-Plane theory).

**What You See:**
- 3D club head visualization at impact
- Side view: Attack angle, dynamic loft, launch angle
- Face-on view: Club path, face angle, side angle

**When to Use:**
- Diagnosing ball flight issues (slice, hook)
- Understanding why your ball curves
- Working on swing path changes

**D-Plane Quick Reference:**

| Face vs Path | Result |
|--------------|--------|
| Face open to path | Fade/Slice spin |
| Face closed to path | Draw/Hook spin |
| Face = Path | Straight (relative) |

| Attack Angle | Typical For |
|--------------|-------------|
| Negative (down) | Irons |
| Near zero | Fairway woods |
| Positive (up) | Driver |

---

### Tab 6: Optix (Impact Analysis)

```
+------------------------------------------------------------------+
|                         OPTIX TAB                                |
+------------------------------------------------------------------+
|                                                                  |
|   +-------------------------+   +-------------------------+      |
|   |                         |   |                         |      |
|   |    [Club Face Image]    |   |   [Side View Image]     |      |
|   |                         |   |                         |      |
|   |         o <- Ball       |   |                         |      |
|   |      impact point       |   |                         |      |
|   |                         |   |                         |      |
|   +-------------------------+   +-------------------------+      |
|                                                                  |
|   Frame: [1/24]  [<<] [>] [||] [>] [>>]                          |
|                                                                  |
|   [Illust] [Photo]   <-- Toggle visualization mode               |
|                                                                  |
|   Impact X: 0.12    Impact Y: 0.08    Lie: UP 2.25              |
+------------------------------------------------------------------+
```

**Purpose:** High-speed camera footage of impact.

**What You See:**
- Ball position on club face at impact
- Frame-by-frame playback (up to 24 frames)
- Toggle between illustration and photo modes

**When to Use:**
- Finding your strike pattern on the face
- Identifying toe/heel or high/low misses
- Understanding how strike location affects distance

**Strike Location Effects:**

```
        +---------------+
        |   TOE  |  TOE |    Toe hits: Less distance,
        |  HIGH  | LOW  |    gear effect adds draw spin
        +-------+-------+
        | CENTER| CENTER|    Center hits: Maximum energy
        |  HIGH |  LOW  |    transfer, optimal distance
        +-------+-------+
        |  HEEL | HEEL  |    Heel hits: Less distance,
        |  HIGH | LOW   |    gear effect adds fade spin
        +---------------+
```

---

### Tab 7: Swing (Video Annotation)

```
+------------------------------------------------------------------+
|                         SWING TAB                                |
+------------------------------------------------------------------+
|                                                                  |
|   TOOLS: [O] [[]  [/] [Pencil] [<->] [Eraser] [Trash]           |
|   COLORS: [Red] [Blue] [Yellow]                                  |
|                                                                  |
|   +----------------------------------------------------------+  |
|   |                                                          |  |
|   |                                                          |  |
|   |                    [Empty Canvas]                        |  |
|   |                                                          |  |
|   |              (For swing video annotation)                |  |
|   |                                                          |  |
|   |                                                          |  |
|   +----------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

**Purpose:** Canvas for marking up swing videos.

**Available Tools:**
| Tool | Use For |
|------|---------|
| Circle | Highlighting body positions |
| Rectangle | Boxing areas of interest |
| Line | Drawing swing plane lines |
| Pencil | Freehand annotations |
| Eraser | Remove specific marks |
| Trash | Clear all annotations |

**When to Use:**
- Coach-style video analysis
- Marking swing positions
- Creating teaching visuals

---

## Interactive Elements

### Shot Navigator

Located in the metrics cards area:

```
+------------------+
| Shot             |
| 1/41  [<] [>]    |
+------------------+
```

| Action | Result |
|--------|--------|
| Click `>` | Move to next shot |
| Click `<` | Move to previous shot |

**Effect:** ALL views update - metrics, visualization, and table selection.

---

### Shot Table Row Selection

Click any row in the shot table to select that shot:

```
+------+-------+-------+-------+-------+
|  no  | Carry | Total | Speed | Spin  |
+------+-------+-------+-------+-------+
|  41  | 57.4  | 64.5  | 63.0  | 2637  |  <- Click to select
|  40  | 181.6 | 188.0 | 97.1  | 7188  |
|  39  | 165.2 | 172.4 | 94.3  | 6890  |
+------+-------+-------+-------+-------+
```

**Visual Feedback:** Selected row highlights in coral/red color.

---

### Eye Icon Toggle (Visibility Control)

Each shot row has an eye icon on the left:

```
+------+------+-------+-------+
| ICON |  no  | Carry | Total |
+------+------+-------+-------+
|  O   |  41  | 57.4  | 64.5  |  <- Eye OPEN = visible
|  X   |  40  | 181.6 | 188.0 |  <- Eye CROSSED = hidden
|  O   |  39  | 165.2 | 172.4 |
+------+------+-------+-------+
```

**Use Cases:**
- Hide outlier shots to see your "real" pattern
- Focus on specific shots for comparison
- Remove warm-up shots from visualization

---

### Export Buttons

Above the shot table:

```
[SWING] [CSV] [ALL]
```

| Button | Downloads |
|--------|-----------|
| SWING | Swing Optix video files |
| CSV | Spreadsheet with all numerical data |
| ALL | Complete data including images and videos |

---

## How Data Flows Between Tabs

```
                    +------------------+
                    |  SELECT A SHOT   |
                    | (Row click, nav, |
                    |  or eye toggle)  |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
   +-----------+      +-----------+      +-----------+
   | METRICS   |      | VISUAL    |      | TABLE     |
   | CARDS     |      | AREA      |      | ROW       |
   | Update    |      | Highlights|      | Highlights|
   +-----------+      +-----------+      +-----------+
         |                   |
         |    +-------------+|
         |    |              |
         v    v              v
   +-----------+      +-----------+
   | Side Tab  |      | Top Tab   |
   | Yellow    |      | Yellow    |
   | trajectory|      | dot       |
   +-----------+      +-----------+
         |                   |
         v                   v
   +-----------+      +-----------+
   | Group Tab |      | Club Tab  |
   | Point     |      | D-Plane   |
   | highlight |      | for shot  |
   +-----------+      +-----------+
         |
         v
   +-----------+
   | Optix Tab |
   | Impact    |
   | for shot  |
   +-----------+
```

**Key Principle:** One selection, all tabs update.

When you select shot #25:
1. **Metrics Cards** show shot #25's numbers
2. **Side Tab** highlights shot #25's trajectory in yellow
3. **Top Tab** highlights shot #25's landing spot
4. **Group Tab** shows shot #25 in the scatter
5. **Club Tab** shows shot #25's D-plane data
6. **Optix Tab** loads shot #25's impact images

---

## Practical Analysis Workflows

### Workflow 1: Driver Consistency Check

**Goal:** Understand your driver dispersion and identify misses.

```
1. SUMMARY TAB
   - Note your average carry and total
   - Note max values (your potential)

2. TOP TAB
   - Look at left/right spread
   - Identify: Do you miss one direction more?

3. GROUP TAB
   - Check ellipse size (smaller = more consistent)
   - Note if pattern is centered or biased

4. CLUB TAB (for problem shots)
   - Click outlier shots in table
   - Check face angle vs club path
   - Diagnose: Open face? Out-to-in path?
```

---

### Workflow 2: Iron Strike Quality

**Goal:** Improve strike consistency with irons.

```
1. OPTIX TAB
   - Cycle through all shots with navigator
   - Note impact location patterns
   - Count: How many center strikes?

2. SIDE TAB
   - Compare apex heights
   - Consistent apex = consistent strike

3. CLUB TAB
   - Check attack angle (should be negative)
   - Compare dynamic loft between shots

4. Use EYE ICON
   - Hide off-center strikes
   - See what your good swings produce
```

---

### Workflow 3: Diagnosing a Slice

**Goal:** Find the cause of your slice.

```
1. TOP TAB
   - Confirm: Shots curving right (for right-hander)
   - How much right? (Side distance column)

2. CLUB TAB (Critical)
   - Check Club Path: Is it negative (out-to-in)?
   - Check Face Angle: Open at impact?
   - Compare Face to Path relationship

3. KEY DIAGNOSIS:
   +------------------------+------------------+
   | Condition              | Cause            |
   +------------------------+------------------+
   | Path out-to-in         | Swing path issue |
   | Face open to path      | Grip/release     |
   | Both                   | Combination fix  |
   +------------------------+------------------+

4. OPTIX TAB
   - Where on face? Heel = worse slice
```

---

### Workflow 4: Session Comparison

**Goal:** Compare two practice sessions.

```
1. Open both reports in separate browser tabs

2. SUMMARY TAB (both)
   - Compare average values side by side
   - Note improvements or regressions

3. TOP TAB (both)
   - Compare dispersion patterns
   - Tighter pattern = improved consistency

4. Export CSV from each session
   - Import to spreadsheet for detailed analysis
```

---

## Quick Reference

### Metric Abbreviations

| Abbrev | Full Name | Unit |
|--------|-----------|------|
| Carry | Carry Distance | yards/meters |
| Tot | Total Distance | yards/meters |
| Side | Side Distance | yards/meters L/R |
| Smash | Smash Factor | ratio |
| Ball | Ball Speed | mph/kph |
| Club | Club Speed | mph/kph |
| Back | Back Spin | rpm |
| Side | Side Spin | rpm L/R |
| Launch | Launch Angle | degrees |
| Side | Side Angle | degrees L/R |
| Desc | Descent Angle | degrees |
| Apex | Maximum Height | yards/meters |
| Flight | Flight Time | seconds |

### Ideal Numbers Reference (Driver)

| Metric | Tour Average | Amateur Target |
|--------|--------------|----------------|
| Launch Angle | 10-12 deg | 12-15 deg |
| Ball Speed | 167+ mph | 140-155 mph |
| Smash Factor | 1.48-1.50 | 1.44-1.48 |
| Back Spin | 2200-2700 rpm | 2500-3000 rpm |
| Attack Angle | 0 to +4 deg | +1 to +5 deg |

### Tab Keyboard Reference

| Key | Action |
|-----|--------|
| Click row | Select shot |
| `<` button | Previous shot |
| `>` button | Next shot |
| Eye icon | Toggle visibility |

---

## Summary

The Uneekor Report Page is a powerful tool when you know how to use it. Remember:

1. **Summary** = Quick stats overview
2. **Side** = Flight trajectory shape
3. **Top** = Where shots land (dispersion)
4. **Group** = Statistical spread pattern
5. **Club** = Why the ball curves (D-Plane)
6. **Optix** = Strike location on face
7. **Swing** = Video annotation tools

**The power is in combining tabs:** Use Top to find a bad shot, Club to diagnose why, and Optix to confirm strike location. One insight leads to another.

---

*Created: 2026-01-26*
*Based on: Uneekor Power U Report interface exploration*
