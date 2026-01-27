# Shot Data Reference Guide

A comprehensive reference for understanding and analyzing your Uneekor launch monitor data. Use this guide to interpret your numbers, identify areas for improvement, and understand how different metrics relate to each other.

---

## Quick Reference Card

The most important metrics at a glance:

| Metric | What It Tells You | Target Range (Driver) | Target Range (7 Iron) |
|--------|------------------|----------------------|----------------------|
| **Carry Distance** | How far the ball flies | 220-280 yards | 140-170 yards |
| **Smash Factor** | Energy transfer efficiency | 1.48-1.52 | 1.33-1.38 |
| **Ball Speed** | Initial ball velocity | 155-175 mph | 115-130 mph |
| **Launch Angle** | Vertical launch | 10-14 degrees | 15-18 degrees |
| **Back Spin** | Backspin rate | 2000-2800 rpm | 6500-8000 rpm |
| **Club Path** | Swing direction | -2 to +4 degrees | -2 to +2 degrees |
| **Face Angle** | Clubface at impact | -1 to +1 degrees | -1 to +1 degrees |

**Quick Health Check:**
- Smash Factor > 1.45 (driver) = Good compression
- Launch Angle + Spin Loft should optimize for your club speed
- Face-to-Path difference determines curve: negative = draw, positive = fade

---

## Distance Metrics

### Carry Distance

**What it measures:** The distance the ball travels through the air before first touching the ground.

| Unit | Field Name |
|------|------------|
| yards/meters | `carry` |

**Skill Level Benchmarks (Driver):**

| Skill Level | Carry Distance |
|-------------|----------------|
| Beginner | 150-180 yards |
| Intermediate | 200-230 yards |
| Advanced | 240-270 yards |
| Professional | 280-310 yards |

**Key Relationships:**
- Carry = f(Ball Speed, Launch Angle, Spin)
- Higher ball speed = more carry (primary driver)
- Optimal launch angle varies by club speed
- Too much spin reduces carry (especially with driver)

**Troubleshooting:**
- Low carry with high ball speed: Check spin rate (likely too high)
- Low carry with low ball speed: Focus on smash factor and club speed

---

### Total Distance

**What it measures:** Carry distance plus roll after the ball lands.

| Unit | Field Name |
|------|------------|
| yards/meters | `total` |

**Understanding Roll:**
- Driver typically adds 20-40 yards of roll on firm fairways
- Irons may roll 5-15 yards depending on descent angle
- Higher descent angle = less roll (more "stick")
- Wet/soft conditions reduce roll significantly

**Skill Level Benchmarks (Driver):**

| Skill Level | Total Distance |
|-------------|----------------|
| Beginner | 180-220 yards |
| Intermediate | 230-260 yards |
| Advanced | 270-300 yards |
| Professional | 310-340 yards |

---

### Side Distance

**What it measures:** Lateral deviation from the target line at landing.

| Unit | Field Name |
|------|------------|
| yards/meters | `side_distance` |

**Sign Convention:**
- Positive (+) = Right of target
- Negative (-) = Left of target

**Benchmarks:**

| Quality | Driver | Irons |
|---------|--------|-------|
| Excellent | within 10 yards | within 5 yards |
| Good | within 20 yards | within 10 yards |
| Needs Work | beyond 30 yards | beyond 15 yards |

---

### Apex (Maximum Height)

**What it measures:** The highest point of the ball's flight trajectory.

| Unit | Field Name |
|------|------------|
| yards/meters | `apex` |

**Typical Values:**

| Club | Typical Apex |
|------|-------------|
| Driver | 25-40 yards |
| 5 Iron | 30-45 yards |
| 9 Iron | 35-50 yards |
| Wedge | 30-45 yards |

**Key Insights:**
- Higher apex generally means steeper descent (ball stops faster)
- Low-trajectory shots have lower apex but more roll
- Wind affects high-apex shots more

---

## Speed Metrics

### Ball Speed

**What it measures:** The velocity of the ball immediately after impact.

| Unit | Field Name |
|------|------------|
| mph/kph | `ball_speed` |

**Why It Matters:**
Ball speed is the #1 determinant of distance. Every 1 mph increase in ball speed adds approximately 2-2.5 yards of carry distance.

**Skill Level Benchmarks (Driver):**

| Skill Level | Ball Speed |
|-------------|------------|
| Beginner | 100-130 mph |
| Intermediate | 140-155 mph |
| Advanced | 160-175 mph |
| Professional | 175-195 mph |

**Skill Level Benchmarks (7 Iron):**

| Skill Level | Ball Speed |
|-------------|------------|
| Beginner | 85-105 mph |
| Intermediate | 110-120 mph |
| Advanced | 125-135 mph |
| Professional | 140-155 mph |

**Key Relationships:**
- Ball Speed = Club Speed x Smash Factor
- Center-face contact maximizes ball speed
- Quality of strike matters as much as swing speed

---

### Club Speed (Club Head Speed)

**What it measures:** The velocity of the club head at the moment of impact.

| Unit | Field Name |
|------|------------|
| mph/kph | `club_speed` |

**Skill Level Benchmarks (Driver):**

| Skill Level | Club Speed |
|-------------|------------|
| Beginner | 70-85 mph |
| Intermediate | 90-100 mph |
| Average Male | 93 mph |
| Average Female | 72 mph |
| Advanced | 105-115 mph |
| PGA Tour Avg | 114 mph |

**Key Insights:**
- Club speed is harder to change than smash factor
- Focus on smash factor improvement before chasing speed
- Proper sequencing and lag retention maximize club speed

---

### Smash Factor

**What it measures:** The efficiency of energy transfer from club to ball. Calculated as Ball Speed / Club Speed.

| Unit | Field Name |
|------|------------|
| ratio | `smash` |

**Why It's Critical:**
Smash factor tells you how well you're striking the ball. A higher smash factor means you're getting more ball speed from your swing speed.

**Optimal Values by Club:**

| Club | Optimal Smash | Acceptable Range |
|------|--------------|------------------|
| Driver | 1.50 | 1.45-1.52 |
| 3 Wood | 1.48 | 1.42-1.50 |
| 5 Iron | 1.38 | 1.32-1.40 |
| 7 Iron | 1.35 | 1.30-1.38 |
| PW | 1.25 | 1.20-1.30 |

**What Affects Smash Factor:**
- **Center-face contact:** Most important factor
- **Face angle at impact:** Glancing blows reduce smash
- **Attack angle:** Extreme angles reduce efficiency
- **Equipment:** Modern clubs have larger sweet spots

**Troubleshooting:**
- Smash < 1.40 (driver): Likely striking toe, heel, or top/bottom
- Smash > 1.52 (driver): Check data validity or equipment issue
- Inconsistent smash: Work on swing path consistency

---

## Spin Metrics

### Back Spin

**What it measures:** The rate of rearward rotation on the ball.

| Unit | Field Name |
|------|------------|
| rpm | `back_spin` |

**Optimal Back Spin by Club:**

| Club | Optimal | Low | High |
|------|---------|-----|------|
| Driver | 2200-2700 | <1800 | >3500 |
| 3 Wood | 3500-4500 | <3000 | >5500 |
| 5 Iron | 5000-6000 | <4500 | >7000 |
| 7 Iron | 6500-7500 | <6000 | >8500 |
| PW | 9000-10500 | <8500 | >11500 |

**Understanding Spin:**
- More spin = more lift = higher trajectory
- More spin = more drag = less carry distance (for driver)
- More spin = steeper descent = more stopping power (for irons)

**Spin Rate vs. Club Speed (Driver Optimization):**

| Club Speed | Optimal Spin |
|------------|--------------|
| 85 mph | 2800-3200 rpm |
| 95 mph | 2500-2900 rpm |
| 105 mph | 2200-2600 rpm |
| 115+ mph | 2000-2400 rpm |

**Key Insight:** Faster swingers need LESS spin to optimize carry.

---

### Side Spin

**What it measures:** The rate of horizontal rotation on the ball, which determines curve.

| Unit | Field Name |
|------|------------|
| rpm | `side_spin` |

**Sign Convention:**
- Positive (+) = Clockwise (fades/slices for right-handed)
- Negative (-) = Counter-clockwise (draws/hooks for right-handed)

**Shot Shape Guide:**

| Side Spin | Shot Shape |
|-----------|------------|
| -200 to +200 | Straight |
| +300 to +800 | Fade |
| -300 to -800 | Draw |
| +1000 to +2000 | Slice |
| -1000 to -2000 | Hook |
| beyond 2000 | Severe (needs correction) |

**Key Relationship:**
Side Spin is primarily determined by Face-to-Path relationship, not club path alone.

---

## Angle Metrics

### Launch Angle

**What it measures:** The vertical angle at which the ball leaves the club face.

| Unit | Field Name |
|------|------------|
| degrees | `launch_angle` |

**Optimal Launch by Club:**

| Club | Optimal | Low | High |
|------|---------|-----|------|
| Driver | 10-14 | <8 | >17 |
| 3 Wood | 12-16 | <10 | >18 |
| 5 Iron | 14-17 | <12 | >19 |
| 7 Iron | 16-19 | <14 | >22 |
| PW | 24-28 | <22 | >32 |

**Launch Angle Optimization (Driver):**
Your optimal launch angle depends on your club speed:

| Club Speed | Optimal Launch |
|------------|----------------|
| 85 mph | 14-16 degrees |
| 95 mph | 12-14 degrees |
| 105 mph | 10-12 degrees |
| 115+ mph | 9-11 degrees |

**Key Formula:** Lower club speed = higher launch needed

---

### Side Angle (Horizontal Launch)

**What it measures:** The horizontal direction the ball launches relative to the target line.

| Unit | Field Name |
|------|------------|
| degrees | `side_angle` |

**Sign Convention:**
- Positive (+) = Right of target line
- Negative (-) = Left of target line

**Understanding Initial Direction:**
- Ball starts approximately 75-85% in the direction of the face angle
- Ball then curves based on face-to-path differential
- Example: Face 2 degrees open, path 0 = starts right, fades further right

---

### Descent Angle

**What it measures:** The angle at which the ball approaches the ground at landing.

| Unit | Field Name |
|------|------------|
| degrees | `descent_angle` |

**Note:** This field may appear as `decent_angle` in some data exports (typo in API).

**Typical Values:**

| Club | Typical Descent |
|------|-----------------|
| Driver | 35-45 degrees |
| 3 Wood | 40-50 degrees |
| 5 Iron | 45-50 degrees |
| 7 Iron | 48-54 degrees |
| PW | 50-55 degrees |

**Implications:**
- Steeper descent = ball stops faster
- Shallower descent = more roll
- Important for course management and pin placement strategy

---

### Attack Angle (Angle of Attack)

**What it measures:** The vertical angle of the club head's path at impact.

| Unit | Field Name |
|------|------------|
| degrees | `attack_angle` |

**Sign Convention:**
- Positive (+) = Hitting up on the ball (ascending)
- Negative (-) = Hitting down on the ball (descending)

**Optimal Attack Angles:**

| Club | Optimal | Notes |
|------|---------|-------|
| Driver | +3 to +5 | Hit up for max distance |
| 3 Wood | -1 to +2 | Slight up or level |
| 5 Iron | -3 to -1 | Slightly down |
| 7 Iron | -4 to -2 | Down strike |
| PW | -5 to -3 | Definitely down |

**Key Insight:**
Hitting UP on the driver (positive attack angle) optimizes launch conditions by:
- Decreasing spin (less backspin)
- Increasing launch angle
- Maximizing smash factor

**Example:** Same club speed with +5 degree vs -5 degree attack angle can result in 20+ yards distance difference with driver.

---

### Dynamic Loft

**What it measures:** The actual loft presented to the ball at impact.

| Unit | Field Name |
|------|------------|
| degrees | `dynamic_loft` |

**Understanding Dynamic Loft:**
Dynamic loft differs from static (stated) loft based on:
- Shaft lean at impact (forward lean decreases loft)
- Attack angle
- Face angle

**Typical Dynamic Loft:**

| Club | Static Loft | Typical Dynamic |
|------|-------------|-----------------|
| Driver | 9-12 | 12-17 |
| 7 Iron | 30-34 | 22-28 |
| PW | 44-48 | 38-44 |

**Key Formula:**
Spin Loft = Dynamic Loft - Attack Angle

Higher spin loft = more backspin

---

## Impact & Club Delivery

### Club Path

**What it measures:** The horizontal direction the club head is moving at impact, relative to the target line.

| Unit | Field Name |
|------|------------|
| degrees | `club_path` |

**Sign Convention:**
- Positive (+) = In-to-out (draw path for right-handed)
- Negative (-) = Out-to-in (fade/slice path for right-handed)

**Optimal Ranges:**

| Shot Type | Club Path |
|-----------|-----------|
| Straight | -2 to +2 |
| Draw | +2 to +6 |
| Fade | -2 to -4 |
| Hook | >+8 |
| Slice | <-6 |

**The D-Plane Relationship:**
Ball flight is determined by the combination of Face Angle and Club Path:
- Ball starts mostly where the face points
- Ball curves based on face-to-path difference

---

### Face Angle (Club Face Angle)

**What it measures:** The direction the club face is pointing at impact, relative to the target line.

| Unit | Field Name |
|------|------------|
| degrees | `face_angle` |

**Sign Convention:**
- Positive (+) = Open (pointing right for right-handed)
- Negative (-) = Closed (pointing left for right-handed)

**Impact on Ball Flight:**
Face angle is responsible for approximately 75-85% of the ball's initial direction.

**Example Shot Shapes (Right-Handed Golfer):**

| Face | Path | Result |
|------|------|--------|
| 0 | 0 | Straight |
| -2 | +4 | Draw (starts left, curves right-to-left) |
| +2 | -4 | Fade (starts right, curves left-to-right) |
| +3 | -6 | Pull-Slice (starts left, curves hard right) |
| -3 | +6 | Push-Hook (starts right, curves hard left) |

---

### Impact Location (Optix X and Y)

**What it measures:** Where on the club face the ball was struck.

| Unit | Field Name |
|------|------------|
| mm from center | `optix_x`, `optix_y`, `impact_x`, `impact_y` |

**Coordinates:**
- X: Horizontal (toe/heel) - negative = heel, positive = toe
- Y: Vertical (high/low) - negative = low, positive = high

**Optimal Contact:**
- Center face contact maximizes ball speed
- Each mm off-center reduces smash factor
- Typical variation: 10-15mm is acceptable

**Miss Pattern Effects:**

| Miss Location | Effect |
|--------------|--------|
| Toe | Lower ball speed, gear effect closes face (draws) |
| Heel | Lower ball speed, gear effect opens face (fades) |
| High | Higher launch, less spin |
| Low | Lower launch, more spin |

---

### Club Lie and Lie Angle

**What it measures:** The angle of the club shaft relative to the ground at impact.

| Field | Description |
|-------|-------------|
| `club_lie` | Numeric lie angle |
| `lie_angle` | Text description (e.g., "UP 2.25") |

**Understanding Lie:**
- "UP" = toe up (heel striking ground first)
- "DOWN" = toe down (toe striking ground first)
- Affects face angle at impact and shot direction

---

## Flight Characteristics

### Flight Time

**What it measures:** Total time the ball is in the air.

| Unit | Field Name |
|------|------------|
| seconds | `flight_time` |

**Typical Values:**

| Club | Flight Time |
|------|-------------|
| Driver | 5.5-7.0 seconds |
| 5 Iron | 5.0-6.0 seconds |
| 7 Iron | 4.5-5.5 seconds |
| PW | 4.0-5.0 seconds |

---

### Shot Type (Shape Classification)

**What it measures:** Automatic classification of the shot shape.

| Field | Values |
|-------|--------|
| `shot_type` | straight, draw, fade, hook, slice, pull, push |

**Classification Logic:**
Based on face-to-path relationship and resulting ball flight curve.

---

## Troubleshooting Guide

### "My distance is too short"

Check these metrics in order:

1. **Smash Factor** - Are you making center-face contact?
   - If smash < 1.42 (driver): Work on strike consistency
   - Use impact tape or foot spray to see strike pattern

2. **Ball Speed** - Is it appropriate for your club speed?
   - Ball speed should be ~1.5x club speed (driver)
   - If ball speed is low, check contact point

3. **Launch Angle** - Is it optimized for your speed?
   - Slow swing = need higher launch
   - Fast swing = can get away with lower launch

4. **Spin Rate** - Is spin eating your distance?
   - If spin > 3000 rpm (driver): Check attack angle and strike location
   - Hit UP on the ball with driver

### "I slice/fade too much"

Check these metrics:

1. **Club Path** - Are you swinging out-to-in?
   - Path < -4 degrees: Severe out-to-in path
   - Work on shallowing the downswing

2. **Face Angle** - Is your face open to the path?
   - Face-to-Path > +3: Ball will curve right
   - Work on squaring the face earlier

3. **Attack Angle** - Are you too steep?
   - Steep attack often causes out-to-in path
   - Work on shallowing the club

**Quick Fix:** Face must be closed relative to path to draw the ball.

### "I hook/draw too much"

Check these metrics:

1. **Club Path** - Are you swinging too far in-to-out?
   - Path > +6 degrees: Excessive in-to-out
   - May indicate early extension or over-rotation

2. **Face Angle** - Is your face too closed?
   - Face-to-Path < -3: Ball will curve left
   - Check grip strength (may be too strong)

3. **Impact Location** - Are you hitting the toe?
   - Toe hits with in-to-out path = double hook effect

### "My trajectory is too low"

Check these metrics:

1. **Launch Angle** - Below optimal range?
   - Driver < 10 degrees: Likely hitting down
   - Irons < optimal: Ball position may be too far back

2. **Attack Angle** - Are you hitting down too much?
   - Driver should be +2 to +5 degrees (hitting UP)
   - Irons should be slightly negative

3. **Dynamic Loft** - Is loft being reduced too much?
   - Excessive shaft lean reduces dynamic loft
   - Check ball position and hand position at impact

### "My trajectory is too high"

Check these metrics:

1. **Back Spin** - Is spin too high?
   - High spin + high launch = balloon flight
   - Check attack angle and strike location

2. **Attack Angle** - Are you hitting up too much (irons)?
   - Irons should have negative attack angle
   - Positive attack with irons = high weak shots

3. **Dynamic Loft** - Is loft too high at impact?
   - May be flipping/scooping at impact
   - Work on forward shaft lean

### "My distance varies too much"

Check these consistency metrics:

1. **Smash Factor Consistency**
   - Standard deviation > 0.05: Contact inconsistency
   - Work on repeatable swing mechanics

2. **Ball Speed Consistency**
   - High variation indicates contact or timing issues

3. **Launch Angle Consistency**
   - Variation > 3 degrees: Attack angle varying

**Benchmark:** Coefficient of variation (CV) for carry distance should be < 5% for good consistency.

### "My smash factor is low"

Causes and fixes:

| Cause | Symptom | Fix |
|-------|---------|-----|
| Toe strikes | Gear effect draws | Stand closer, check posture |
| Heel strikes | Gear effect fades | Stand farther, arms dropping |
| High face strikes | Low spin, balloon | Tee lower, check eye level |
| Low face strikes | High spin, low | Tee higher, hit up more |
| Glancing blow | Open/closed face | Square face to path |

---

## Field Reference Table

Complete mapping of all shot data fields:

| UI Label | Database Field | Unit | Description |
|----------|---------------|------|-------------|
| Carry | `carry` | yards | Carry distance |
| Total | `total` | yards | Total distance (carry + roll) |
| Side | `side_distance` | yards | Lateral deviation |
| Smash Factor | `smash` | ratio | Ball speed / club speed |
| Ball Speed | `ball_speed` | mph | Ball velocity at impact |
| Club Speed | `club_speed` | mph | Club head speed at impact |
| Back Spin | `back_spin` | rpm | Backspin rate |
| Side Spin | `side_spin` | rpm | Sidespin rate |
| Launch Angle | `launch_angle` | degrees | Vertical launch angle |
| Side Angle | `side_angle` | degrees | Horizontal launch angle |
| Descent Angle | `descent_angle` | degrees | Landing approach angle |
| Attack Angle | `attack_angle` | degrees | Club approach angle |
| Club Path | `club_path` | degrees | Horizontal swing direction |
| Face Angle | `face_angle` | degrees | Club face orientation |
| Dynamic Loft | `dynamic_loft` | degrees | Loft at impact |
| Apex | `apex` | yards | Maximum flight height |
| Flight Time | `flight_time` | seconds | Time in air |
| Impact X | `optix_x`, `impact_x` | mm | Horizontal impact position |
| Impact Y | `optix_y`, `impact_y` | mm | Vertical impact position |
| Club Lie | `club_lie` | degrees | Lie angle at impact |
| Lie Angle | `lie_angle` | text | Descriptive lie angle |
| Shot Type | `shot_type` | text | Shape classification |

---

## Metric Relationships Diagram

```
Club Speed  -----> Ball Speed -----> Carry Distance
    |                 ^                    ^
    |                 |                    |
    v                 |                    |
Smash Factor <------ Impact Location       |
                                           |
Launch Angle + Spin ---------------------->|
    ^           ^
    |           |
Attack Angle    |
    |           |
    v           |
Dynamic Loft -->|
    ^
    |
Face Angle + Club Path ---> Side Spin ---> Shot Curve
```

**Key Takeaways:**
1. Club speed sets your ceiling; smash factor determines how much you use
2. Ball speed is the primary driver of distance
3. Launch conditions (angle + spin) optimize the ball speed you have
4. Face-to-path relationship determines curve
5. Impact location affects nearly everything

---

## Glossary

| Term | Definition |
|------|------------|
| **D-Plane** | The tilted plane created by the club head's path and face angle that determines ball flight |
| **Spin Loft** | Dynamic Loft minus Attack Angle; determines spin rate |
| **Face-to-Path** | Difference between face angle and club path; determines curvature |
| **Gear Effect** | Off-center hits cause the ball to spin opposite to the miss direction |
| **Smash Factor** | Efficiency of energy transfer; limited to ~1.52 by COR rules |
| **Attack Angle** | Vertical approach of club; up = positive, down = negative |
| **Dynamic Loft** | Actual loft at impact (differs from static club loft) |

---

*Last updated: 2026-01-26*
*For GolfDataApp - Uneekor Data Analysis*
