# Research: What Data Do Golfers Care About?

**Generated:** 2026-02-03
**Focus:** Indoor simulator users, practice analytics, Uneekor data

---

## 1. Critical Metrics by Skill Level

### Beginners (25+ handicap)
**What They Track:**
- Carry distance (am I hitting it far enough?)
- Ball speed (am I generating power?)
- Contact quality (did I hit the sweet spot?)

**What Confuses Them:**
- Spin axis vs side spin
- Attack angle vs dynamic loft
- Why their "perfect" shot went left

**What They Need:**
- Simple "good shot / bad shot" feedback
- Clear explanations of what went wrong
- Progress indicators ("you're improving!")

---

### Mid-Handicappers (10-24)
**What They Track:**
- Consistency (dispersion width)
- Club gapping (distance between clubs)
- Smash factor (efficiency)
- Launch conditions (angle + spin combo)

**Metrics That Help Them Improve:**
- Standard deviation of carry distance
- Face-to-path relationship
- Spin rate optimization per club
- Attack angle trends

**What They Want:**
- Comparison to "optimal" numbers
- Specific drills for their flaws
- Week-over-week improvement charts

---

### Low Handicappers / Scratch (0-9)
**What They Track:**
- Everything, precisely
- Spin axis for shot shaping
- Low point control (attack angle)
- Delivery consistency (path + face)

**Fine-Tuning Data:**
- Dynamic loft vs static loft
- Vertical gear effect
- Horizontal launch direction
- Spin loft relationships

**What They Want:**
- Tour-level benchmarks
- 3D ball flight modeling
- Session-to-session micro-trends
- Data export for coach review

---

## 2. Uneekor-Specific Data Points

### Ball Data (EYE XO, QED)
| Metric | What It Tells You | Why It Matters |
|--------|-------------------|----------------|
| Ball Speed | Energy transfer to ball | Primary distance factor |
| Launch Angle | Vertical trajectory | Optimal varies by club |
| Back Spin | RPM of spin | Controls flight and stopping |
| Side Spin | Left/right spin | Causes draw/fade/slice |
| Spin Axis | Tilt of spin plane | True shape predictor |
| Carry Distance | Air travel | What you control |
| Total Distance | With roll | Course conditions vary |

### Club Data
| Metric | What It Tells You | Why It Matters |
|--------|-------------------|----------------|
| Club Speed | Swing speed at impact | Power potential |
| Club Path | In-to-out or out-to-in | Start direction |
| Face Angle | Where face points | Primary curve factor |
| Attack Angle | Up or down strike | Launch + spin control |
| Dynamic Loft | Actual loft delivered | Affects everything |

### Impact Location (Optix)
**Why It Matters:**
- Center hits = max ball speed
- Toe/heel hits = gear effect spin
- High/low hits = launch changes
- Consistency indicator

**How to Display:**
- Heat map on club face
- Sweet spot circle overlay
- Trend arrows for patterns
- Per-club breakdown

### Uneekor vs Competitors
| Feature | Uneekor | Trackman | GCQuad |
|---------|---------|----------|--------|
| Ball tracking | High-speed camera | Doppler radar | Quadroscopic |
| Club data | Yes (EYE XO) | Yes | Yes |
| Impact location | Optix (optional) | Not direct | Yes |
| Outdoor use | Limited | Excellent | Good |
| Spin accuracy | Very good | Excellent | Excellent |
| Price | Mid-tier | Premium | Premium |

---

## 3. Practice Session Insights Golfers Want

### Carry Distance Consistency
**Visualization:** Box plot or dispersion ellipse
**Key Metric:** Standard deviation
**Benchmark:** <5 yards SD is good, <3 yards is elite

### Club Gapping Analysis
**What They Want:**
- Average carry per club
- Overlap detection (clubs hitting same distance)
- Gap recommendations

**Display Approach:**
```
Driver    |████████████████████████| 265 yds
3-Wood    |█████████████████████| 240 yds
5-Wood    |███████████████████| 225 yds
4-Iron    |████████████████| 205 yds
          ↑ 20-yard gap is ideal
```

### Smash Factor Optimization
**Formula:** Ball Speed ÷ Club Speed
**Target:** 1.50 for driver, lower for irons
**Why It Matters:** Shows strike efficiency

### Swing Flaw Detection
**Patterns to Identify:**
- Consistent slice (face > path)
- Hook tendency (path > face)
- High spin (steep attack + high loft)
- Low launch (too much shaft lean)

### Progress Over Time
**What to Show:**
- Rolling average of key metrics
- Best session highlights
- Improvement percentage
- Milestones achieved

---

## 4. How Golfers Use Simulator Data

### During Practice (Real-Time)
**Needs:**
- Instant feedback after each shot
- Last 5 shots summary
- Running averages this session
- Quick good/bad indication

**Don't Show:**
- Complex statistical analysis
- Too many numbers
- Historical comparisons

### After Practice (Session Review)
**Needs:**
- Session summary with highlights
- Best shots of the day
- Areas that need work
- Comparison to last session

**Show:**
- All shots in table/scatter
- Aggregate statistics
- Outlier identification
- Export for notes

### Long-Term Tracking
**Needs:**
- Month-over-month trends
- Improvement in specific areas
- Handicap trajectory prediction
- Goal progress

### With Coaches
**What to Share:**
- Session exports (CSV/PDF)
- Video links with data overlay
- Specific problem shots
- Historical context

---

## 5. Common Frustrations with Simulator Software

### Data Overload
- "I don't know what half these numbers mean"
- "Too many tabs and menus"
- "Can't find what I'm looking for"

**Solution:** Progressive disclosure, skill-level presets

### Missing Features
- "Can't compare two sessions easily"
- "No way to export my data"
- "No historical trends"
- "Can't filter by club"

**Solution:** Build these features prominently

### Confusing Terminology
- "What's spin axis vs side spin?"
- "Attack angle or angle of attack?"
- "Is higher smash factor better?"

**Solution:** In-context help, glossary, tooltips

### No Actionable Insights
- "I know my numbers, but what should I DO?"
- "How do I compare to other golfers?"
- "Is this good or bad?"

**Solution:** Benchmarks, recommendations, AI coach

### Poor Session Management
- "All my sessions look the same"
- "Can't tag warmup vs practice"
- "Mixed clubs in one session"

**Solution:** Tags, session types, split tools (we have this!)

---

## 6. Key Data Hierarchy for UI

### Primary (Always Visible)
1. Carry Distance
2. Ball Speed
3. Club Speed
4. Smash Factor

### Secondary (One Click Away)
5. Launch Angle
6. Back Spin
7. Side Distance
8. Face Angle

### Advanced (Expandable)
9. Spin Axis
10. Attack Angle
11. Club Path
12. Dynamic Loft
13. Impact Location

### Analysis (Separate Tab)
14. Dispersion
15. Gapping
16. Trends
17. Strokes Gained (if on-course)
