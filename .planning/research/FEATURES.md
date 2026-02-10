# Features Research: Local AI/ML Golf Coaching

**Research Date:** 2026-02-10
**Purpose:** Identify ML-powered features for local (offline) golf analytics to minimize reliance on cloud AI APIs

---

## Executive Summary

Current golf analytics platforms (TrackMan, Arccos, Golfshot) combine real-time launch monitor data with ML-powered insights. The competitive landscape shows three tiers:

1. **Table Stakes:** Distance prediction, shot shape classification, strokes gained analysis, dispersion patterns
2. **Differentiators:** Personalized practice plans, context-aware recommendations, fault pattern detection, session-to-session progress tracking
3. **Emerging:** Local-first AI processing (privacy + offline capability), 3D motion analysis, probabilistic club recommendations

Key insight: Modern platforms emphasize **actionable insights over raw data** — users want to know *what to practice* and *why*, not just see more charts.

---

## Table Stakes (Must Have)

### 1. Shot Dispersion Analysis
**Description:** Visualize shot scatter patterns (width/depth) per club to identify directional and distance tendencies. Oval-shaped patterns show typical miss zones.

**Why It Matters:** Every competitor offers this. Users expect to see where shots cluster and how consistent they are with each club.

**Complexity:** **Low**
**Dependencies:** None (uses existing carry distance, offline, spin axis)
**Implementation:**
- Calculate 2D scatter (lateral deviation, distance variation) per club
- Remove outliers (>2.5 std dev)
- Visualize as ellipse/density heatmap

---

### 2. True Club Distances (Personalized Carry/Total)
**Description:** Calculate median carry and total distances per club (not maximum), excluding outliers. Show confidence intervals.

**Why It Matters:** Arccos made this a selling point — knowing your *typical* 7-iron is 150 yards (not your best 165-yard shot) prevents over-clubbing.

**Complexity:** **Low**
**Dependencies:** None
**Implementation:**
- Median + IQR per club (ignore top/bottom 10%)
- Track over time (rolling 30-day window)
- Flag when distances change >5% (equipment/swing change detection)

---

### 3. Strokes Gained Analysis (Practice Version)
**Description:** Compare shot outcomes to benchmarks (scratch, 10-handicap, 20-handicap) across categories: off-tee, approach, short game.

**Why It Matters:** Industry standard metric (PGA Tour uses it). Users want to know if their Driver is costing them strokes vs. their wedges.

**Complexity:** **Medium**
**Dependencies:** Benchmark data (can use static tables from USGA/PGA studies)
**Implementation:**
- Define benchmark expectations (e.g., 150-yard approach should land within 30ft for scratch)
- Calculate strokes gained/lost per shot category
- Aggregate by session and rolling 10-session windows

---

### 4. Miss Tendency Detection (Slice/Hook/Push/Pull Patterns)
**Description:** Identify consistent directional biases per club using spin axis, face angle, and club path data. Classify each shot as: straight, draw, fade, hook, slice, push, pull.

**Why It Matters:** Simulators inherently detect slice/hook via spin axis and face angle. Users expect the app to say "Your 5-iron has a 70% slice tendency."

**Complexity:** **Low**
**Dependencies:** Shot shape classifier (already exists)
**Implementation:**
- Use existing D-plane shot shape logic
- Aggregate by club (% of shots per shape)
- Highlight persistent biases (>60% of shots in one category)

---

### 5. Session-to-Session Progress Tracking
**Description:** Track key metrics over time: median distance, dispersion tightness, miss tendency %, strokes gained. Show trend lines and % improvement.

**Why It Matters:** Users need proof their practice is working. "Your 7-iron dispersion improved 18% this month" is motivating.

**Complexity:** **Low**
**Dependencies:** Features 1-4 above
**Implementation:**
- Store aggregate metrics per session (avg, median, std dev)
- Calculate rolling windows (7-day, 30-day)
- Flag statistically significant changes (t-test or effect size >0.5)

---

## Differentiators (Competitive Advantage)

### 6. Personalized Practice Plans
**Description:** Auto-generate 15-30 minute practice routines based on detected weaknesses. Example: "Focus on 7-iron accuracy — 60% of misses are right. Drill: Alignment stick + closed stance."

**Why It Matters:** TrackMan's Tracy and Golfshot's Golfplan 2.0 do this with cloud AI. Doing it locally (offline) is a **major differentiator**.

**Complexity:** **High**
**Dependencies:** Features 1, 3, 4 (dispersion, strokes gained, miss tendencies)
**Implementation:**
- Decision tree: Identify biggest strokes gained deficit -> drill library mapping
- Template-based plans with variable substitution (club, focus area, target metric)
- Track plan completion and re-test after 5-10 sessions

---

### 7. Context-Aware Shot Recommendations
**Description:** During a session, suggest optimal focus based on current conditions. Example: "Your last 5 driver swings show attack angle -2. Try teeing higher."

**Why It Matters:** Real-time feedback loop = faster improvement. Most competitors only offer post-session analysis.

**Complexity:** **Medium**
**Dependencies:** Features 1, 4 (dispersion, miss detection)
**Implementation:**
- Sliding window analysis (last 5-10 shots)
- Rule-based triggers (e.g., if attack angle <-1 for 5 shots -> suggest tee height)
- Avoid alert fatigue (max 1 suggestion per 10 shots)

---

### 8. Fault Pattern Recognition (Multi-Metric Clustering)
**Description:** Identify swing fault signatures by clustering similar poor shots. Example: "Low launch + high spin + slice = over-the-top pattern."

**Why It Matters:** Goes beyond simple "you slice" to "here's the mechanical cause" using launch monitor data patterns.

**Complexity:** **High**
**Dependencies:** ML clustering (DBSCAN or K-means), features 1, 4
**Implementation:**
- Define fault signatures (e.g., flip = high AoA + low ball speed + high spin)
- Cluster shots with similar metric combos
- Map clusters to known swing faults (over-the-top, early extension, flip, etc.)

---

### 9. Probabilistic Club Recommendations
**Description:** For a given target distance, recommend club(s) with highest success probability based on user's dispersion data. Show confidence % for each option.

**Why It Matters:** Bridges practice and course play. "Your 7-iron has 65% chance of hitting a 150-yard green vs. 8-iron at 45%."

**Complexity:** **Medium**
**Dependencies:** Feature 1 (dispersion), Feature 2 (true distances)
**Implementation:**
- Monte Carlo simulation: Given target, sample from each club's dispersion distribution
- Calculate % of shots landing within acceptable zone (e.g., on green or within 10 yards)
- Rank clubs by success probability

---

### 10. Equipment Change Detection
**Description:** Automatically flag when distances/patterns change significantly (>10% median distance shift or dispersion change >20%). Prompt user: "Did you change clubs or grips?"

**Why It Matters:** Contextualizes data shifts. Prevents confusion when a new driver adds 15 yards.

**Complexity:** **Low**
**Dependencies:** Feature 2 (true distances), Feature 5 (progress tracking)
**Implementation:**
- Rolling 30-day baseline for each club
- Statistical test (Mann-Whitney U) between current 10 sessions and baseline
- Trigger alert + log user's response (equipment change, swing change, other)

---

### 11. Session Quality Scoring
**Description:** Single 0-100 score per session based on: consistency (inverse of dispersion), improvement (vs. recent average), balance (all clubs practiced), anomaly rate (inverse of outliers).

**Why It Matters:** Gamification + quick progress indicator. Users want a summary metric beyond "I hit 87 shots today."

**Complexity:** **Low**
**Dependencies:** Features 1, 5 (dispersion, progress tracking)
**Implementation:**
- Weighted formula: 40% consistency + 30% improvement + 20% balance + 10% anomaly penalty
- Normalize to 0-100 scale
- Show trend over time

---

## Anti-Features (Do NOT Build)

### 1. Video Swing Analysis
**What:** 3D pose estimation, swing plane visualization, kinematic sequence analysis from video

**Why Avoid:**
- **Scope creep:** This app uses launch monitor data, not video. Competing with Sportsbox AI/DeepSwing requires entirely different tech stack (computer vision, ML models for pose detection)
- **Local processing limits:** CNNs for pose estimation are compute-intensive; would require GPU or slow inference
- **Uneekor data is sufficient:** Launch monitor metrics already capture swing outcomes (AoA, path, face angle). Video adds little actionable value for simulator users

---

### 2. Social/Competitive Features (Leaderboards, Challenges)
**What:** Compare stats with friends, global leaderboards, weekly challenges

**Why Avoid:**
- **Mission drift:** This is a personal improvement tool, not a social network
- **Privacy concerns:** Local-first ethos conflicts with sharing data to servers
- **Maintenance burden:** Social features require backend infrastructure, moderation, etc.

**Exception:** Export stats for manual sharing is fine (e.g., export PDF report).

---

### 3. Course Strategy Simulator
**What:** "Play" virtual rounds on famous courses, get club recommendations per hole

**Why Avoid:**
- **Out of scope:** This app is for practice analytics, not simulated rounds (Uneekor's own software does this)
- **Data mismatch:** Lacks real course conditions (wind, lies, elevation) — recommendations would be inaccurate
- **Complexity:** Requires course database, shot trajectory physics, environmental modeling

**Better alternative:** Focus on Feature 9 (probabilistic club recommendations) for generic distance scenarios.

---

### 4. Biometric Integration (Heart Rate, HRV, Sleep)
**What:** Correlate shot quality with fatigue, stress, recovery state

**Why Avoid:**
- **Peripheral value:** Golf simulator users are focused on mechanics, not physiology during practice
- **Data availability:** Requires wearables; adds dependency on external APIs (Apple Health, Garmin, etc.)
- **Signal noise:** Too many confounding variables (time of day, caffeine, etc.) for meaningful insights at 2000-5000 shot scale

---

## Feature Dependencies

```
Foundation Layer (Build First):
  [1] Shot Dispersion Analysis
  [2] True Club Distances
  [3] Strokes Gained Analysis
  [4] Miss Tendency Detection
         |
         v
  [5] Progress Tracking --> [10] Equipment Change Detection
         |
         v
  [6] Personalized Practice Plans
  [7] Context-Aware Recommendations
  [8] Fault Pattern Recognition
  [9] Probabilistic Club Recommendations
  [11] Session Quality Scoring
```

**Build Order:**
1. **Phase 1 (Table Stakes):** Features 1-4 (all low complexity, no dependencies)
2. **Phase 2 (Foundation):** Feature 5 (progress tracking depends on 1-4)
3. **Phase 3 (Differentiators):**
   - Start with Feature 11 (session scoring) — low complexity, high user value
   - Then Feature 7 (context-aware recommendations) — medium complexity
   - Then Feature 10 (equipment detection) — low complexity, enhances progress tracking
4. **Phase 4 (Advanced):**
   - Feature 6 (practice plans) — high complexity but high differentiation
   - Feature 9 (probabilistic recommendations) — medium complexity
   - Feature 8 (fault recognition) — high complexity, ML-heavy

---

## Key Takeaways for Local AI/ML Implementation

1. **Leverage existing data richness:** Uneekor provides 30+ metrics per shot. No video needed — launch monitor data is sufficient for 80% of actionable insights.

2. **Prioritize interpretability:** Users don't want black-box predictions. Show *why* the AI recommends something.

3. **Template + rules beat LLMs for structure:** Personalized practice plans can use decision trees + templates rather than expensive Gemini calls. Save LLM usage for freeform Q&A.

4. **Offline = competitive moat:** Major platforms (TrackMan, Arccos, Golfshot) all require internet for AI features. Local ML models that work offline are a differentiator.

5. **Start simple, prove value:** Shot dispersion + true distances (Features 1-2) can be built quickly and provide immediate user value.

6. **Progress visibility drives engagement:** Users practice more when they see measurable improvement (Feature 5). Make trend lines prominent.

---
*Research completed: 2026-02-10*
