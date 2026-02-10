# Phase 2: Analytics Engine - Research

**Researched:** 2026-02-10
**Domain:** Golf analytics, statistical analysis, data visualization
**Confidence:** HIGH

## Summary

Phase 2 implements trustworthy golf analytics using robust statistical methods suited for small datasets (2000-5000 shots). The analytics engine builds on existing infrastructure (SQLite, Plotly, pandas) with minimal new dependencies. Key insight: golf analytics requires domain-specific statistical approaches—median/IQR over mean/std for outlier-prone shot data, D-plane theory for miss tendency classification, and normalized scoring systems for session quality.

The project already has strong visualization patterns (heatmap_chart.py, radar_chart.py, trend_chart.py) following the `render_*(df: pd.DataFrame, **kwargs)` stateless component pattern. Phase 1 established the `session_stats` table with aggregate metrics, which Phase 2 will extend with per-club analytics and quality scoring.

**Primary recommendation:** Use IQR-based outlier filtering for dispersion analysis, median with percentiles for distance reporting, D-plane-derived classification for miss tendencies, and composite normalized metrics for session quality scoring. All analytics must gracefully handle sparse data (single-digit shot counts per club/session).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.x | Data manipulation, groupby aggregation | Already in use; industry standard for tabular analytics |
| scipy | 1.11+ | IQR calculation (`scipy.stats.iqr`), statistical tests | HIGH confidence: robust outlier detection, small dataset stats |
| plotly | 5.x | Interactive scatter plots, trend lines | Already in use; superior hover tooltips, no extra deps |
| numpy | 1.24+ | Array operations, percentile calculations | Already in use; foundation for pandas/scipy |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sklearn | 1.3+ | Linear regression for trend lines (optional) | Only if `np.polyfit` insufficient; already in deps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scipy.stats.iqr | Manual percentile calc | scipy is already installed, provides nan_policy |
| Plotly | matplotlib | Plotly already in use, better for interactive tooltips |
| pandas groupby | SQL aggregation | pandas more flexible for multi-level grouping |

**Installation:**
```bash
# Already installed (from requirements.txt review)
# scipy, plotly, pandas, numpy
pip install scipy plotly pandas numpy
```

## Architecture Patterns

### Recommended Project Structure
```
components/
├── dispersion_chart.py    # ANLYT-01: Scatter plot with IQR outlier filtering
├── distance_table.py       # ANLYT-02: Median/IQR distance reporting per club
├── miss_tendency.py        # ANLYT-03: D-plane-based shot shape classification
├── progress_tracker.py     # ANLYT-04: Session-over-session trends with stats sig
└── session_quality.py      # ANLYT-05: Composite quality score (0-100)

golf_db.py                  # Extend with analytics query functions
```

### Pattern 1: Stateless Render Components
**What:** All components follow `render_*(df: pd.DataFrame, **kwargs) -> None` pattern
**When to use:** Every analytics visualization (established pattern in codebase)
**Example:**
```python
# Source: components/heatmap_chart.py (existing)
def render_impact_heatmap(df: pd.DataFrame, use_optix: bool = True) -> None:
    """Render a heatmap of impact locations on the club face."""
    st.subheader("Impact Location Heatmap")

    if df.empty:
        st.info("No data available for heatmap")
        return

    # Filter invalid data
    df_filtered = df[(df['x_col'] != 0) & (df['y_col'] != 0)].copy()
    df_filtered = df_filtered.dropna(subset=['x_col', 'y_col'])

    if df_filtered.empty:
        st.info("No valid impact location data in this dataset")
        return

    # ... visualization code
```

### Pattern 2: IQR-Based Outlier Filtering
**What:** Use IQR method (Q1 - 1.5*IQR, Q3 + 1.5*IQR) for outlier detection
**When to use:** Shot dispersion analysis (ANLYT-01), any golf analytics with skewed distributions
**Example:**
```python
# Source: Context7 scipy.stats.iqr documentation
import numpy as np
from scipy.stats import iqr

def filter_outliers_iqr(data: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """
    Filter outliers using IQR method.

    Args:
        data: Series of numeric values
        multiplier: IQR multiplier (1.5 standard, 3.0 extreme)

    Returns:
        Boolean series mask for valid (non-outlier) data
    """
    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)
    iqr_value = iqr(data, nan_policy='omit')

    lower_bound = q1 - multiplier * iqr_value
    upper_bound = q3 + multiplier * iqr_value

    return (data >= lower_bound) & (data <= upper_bound)
```

**Why IQR for golf analytics:**
- Golf shot data is right-skewed (occasional extreme mishits)
- IQR robust to outliers (unlike z-score which assumes normality)
- Standard 1.5x multiplier used in golf industry research
- Source: [CareerFoundry - How to Find Outliers](https://careerfoundry.com/en/blog/data-analytics/how-to-find-outliers/), [Medium - IQR Method](https://medium.com/@tubelwj/python-outlier-detection-iqr-method-and-z-score-implementation-8e825edf4b32)

### Pattern 3: Median with IQR for Distance Reporting
**What:** Report median carry/total with 25th/75th percentiles instead of mean/max
**When to use:** Club distance analysis (ANLYT-02), any golf distance reporting
**Example:**
```python
# Source: Context7 pandas documentation
def calculate_club_distances(df: pd.DataFrame, club: str) -> dict:
    """
    Calculate robust distance statistics for a club.

    Returns:
        Dict with median, q25, q75, iqr, sample_size
    """
    club_data = df[df['club'] == club]['carry'].dropna()

    if len(club_data) < 3:
        return None  # Insufficient data

    return {
        'median': club_data.median(),
        'q25': club_data.quantile(0.25),
        'q75': club_data.quantile(0.75),
        'iqr': iqr(club_data),
        'sample_size': len(club_data)
    }
```

**Why median over mean:**
- Resistant to outliers (topped shots, shanks don't skew results)
- Golf industry standard (Tour averages use median proximity)
- IQR gives realistic "typical range" vs misleading best-case max
- Source: [Practical Golf - Driver Dispersion](https://practical-golf.com/driver-dispersion), [HackMotion - Shot Dispersion](https://hackmotion.com/shot-dispersion-in-golf/)

### Pattern 4: D-Plane Shot Shape Classification
**What:** Classify shot shape (straight/draw/fade/hook/slice) using face_angle, club_path, side_spin
**When to use:** Miss tendency analysis (ANLYT-03)
**Example:**
```python
# Source: Golf ball flight laws research + existing local_coach.py classify_shot_shape
def classify_miss_tendency(face_angle: float, club_path: float, side_spin: int) -> str:
    """
    Classify shot shape using D-plane theory.

    D-plane = plane formed by club path (bottom edge) and face angle (top edge)
    Ball flight primarily determined by face angle; curve by face-to-path difference

    Returns:
        'straight', 'draw', 'fade', 'hook', 'slice'
    """
    face_to_path = face_angle - club_path

    # Thresholds based on D-plane theory
    if abs(face_to_path) < 2.0 and abs(side_spin) < 300:
        return 'straight'
    elif face_to_path < -2.0 or side_spin < -300:
        if face_to_path < -6.0:
            return 'hook'
        return 'draw'
    elif face_to_path > 2.0 or side_spin > 300:
        if face_to_path > 6.0:
            return 'slice'
        return 'fade'

    return 'straight'  # Default for edge cases
```

**D-plane fundamentals:**
- Face angle determines initial direction (86% influence)
- Face-to-path differential determines curve amount (14% influence)
- Side spin confirms classification (negative = draw, positive = fade)
- Source: [Golf Ball Flight Laws](https://perfectgolfswingreview.net/ballflight.htm), [HackMotion - Ball Flight Laws](https://hackmotion.com/golf-ball-flight-laws/)

### Pattern 5: Session Quality Composite Score
**What:** Normalize and combine multiple metrics into 0-100 session quality score
**When to use:** Session quality assessment (ANLYT-05)
**Example:**
```python
def calculate_session_quality_score(session_stats: dict) -> dict:
    """
    Calculate composite quality score (0-100) from session metrics.

    Components:
    - Consistency (40%): Lower std_dev in face_angle, club_path, strike
    - Performance (30%): Average smash, ball_speed vs session baseline
    - Improvement (30%): Comparison to previous sessions

    Returns:
        Dict with overall_score, consistency_score, performance_score, improvement_score
    """
    # Normalize consistency (lower is better)
    consistency_score = normalize_inverse(
        session_stats['std_face_angle'],
        min_val=0.5, max_val=5.0  # Typical range for recreational players
    )

    # Normalize performance (higher is better)
    performance_score = normalize(
        session_stats['avg_smash'],
        min_val=1.35, max_val=1.50  # Typical range
    )

    # Improvement from baseline (requires historical data)
    improvement_score = calculate_improvement_pct(session_stats)

    overall_score = (
        consistency_score * 0.4 +
        performance_score * 0.3 +
        improvement_score * 0.3
    )

    return {
        'overall_score': round(overall_score, 1),
        'consistency_score': round(consistency_score, 1),
        'performance_score': round(performance_score, 1),
        'improvement_score': round(improvement_score, 1)
    }

def normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize to 0-100 scale, clamped."""
    normalized = ((value - min_val) / (max_val - min_val)) * 100
    return max(0, min(100, normalized))

def normalize_inverse(value: float, min_val: float, max_val: float) -> float:
    """Inverse normalize (lower is better)."""
    return 100 - normalize(value, min_val, max_val)
```

**Quality score design principles:**
- Weighted components (consistency > performance > improvement)
- Normalized to 0-100 for interpretability
- Robust to missing data (graceful degradation)
- Source: [Session Quality Measure](https://optimizingaudience.com/articles/session-quality-measure/), [HackMotion - Track Golf Stats](https://hackmotion.com/track-golf-stats/)

### Pattern 6: Statistical Significance for Trends
**What:** Indicate statistical significance when comparing session-to-session trends
**When to use:** Progress tracking (ANLYT-04) with small sample sizes
**Example:**
```python
from scipy import stats

def calculate_trend_significance(session_values: list, dates: list) -> dict:
    """
    Calculate linear trend with statistical significance.

    Args:
        session_values: List of metric values across sessions
        dates: List of session dates (for ordering)

    Returns:
        Dict with slope, p_value, is_significant, improvement_pct
    """
    if len(session_values) < 3:
        return {'is_significant': False, 'note': 'Insufficient data (need 3+ sessions)'}

    # Linear regression
    x = np.arange(len(session_values))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, session_values)

    # Calculate improvement percentage
    first_value = session_values[0]
    last_value = session_values[-1]
    improvement_pct = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0

    return {
        'slope': slope,
        'p_value': p_value,
        'is_significant': p_value < 0.05,  # 95% confidence
        'improvement_pct': improvement_pct,
        'r_squared': r_value ** 2,
        'note': 'Significant improvement' if p_value < 0.05 and slope > 0 else None
    }
```

**Why statistical significance matters:**
- Small samples (5-10 sessions) prone to random variation
- P-value < 0.05 standard threshold (95% confidence)
- Prevents false confidence from noise
- Source: [NAEP - Statistical Significance](https://nces.ed.gov/nationsreportcard/guides/statsig.aspx), [BlastX - Session-Based Metrics](https://www.blastanalytics.com/blog/calculate-statistical-significance-for-session-based-metrics-in-ab-test)

### Anti-Patterns to Avoid
- **Using maximum distance:** Maximums are misleading (one lucky shot != club capability); use median + IQR
- **Mean with standard deviation for skewed data:** Golf shots are right-skewed; use median + IQR
- **Absolute scoring without context:** "150 yard 7-iron" meaningless without knowing player ability; normalize scores
- **Ignoring sample size:** Report "7 Iron (n=3 shots)" to prevent over-confidence from sparse data
- **Complex ML for simple stats:** Don't train models for percentile calculations; use pandas native methods

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Outlier detection | Custom z-score logic | `scipy.stats.iqr` with standard 1.5x multiplier | Robust to non-normal distributions, industry standard |
| Percentile calculation | Manual sorting + indexing | `pandas.Series.quantile()` or `np.percentile()` | Handles interpolation, edge cases, missing data |
| Linear regression | Custom least-squares | `scipy.stats.linregress` or `np.polyfit` | Returns p-value, std error, handles collinearity |
| Trend lines | Manual slope calc | `np.polyfit` (already in codebase) | Tested, handles NaN, works with Plotly |
| Shot shape classification | Rule spaghetti | D-plane theory with thresholds (from research) | Physics-based, interpretable, validated by golf industry |

**Key insight:** Golf analytics has solved problems (dispersion, D-plane, miss patterns). Don't reinvent—use established thresholds and formulas from TrackMan/FlightScope research.

## Common Pitfalls

### Pitfall 1: Insufficient Data Handling
**What goes wrong:** Analytics crash or show nonsense with 1-2 shots per club
**Why it happens:** pandas groupby operations on tiny groups, division by zero in normalization
**How to avoid:**
- Always check `len(data) < MIN_SAMPLES` before analysis (MIN_SAMPLES = 3 for basic stats, 5 for trends)
- Show user-friendly messages: "Need 3+ shots for analysis" vs crashing
- Use `dropna()` and null-safe operations (`pd.Series.median()` handles NaN)
**Warning signs:** KeyError on groupby, NaN in displayed metrics, empty Plotly charts

### Pitfall 2: Outliers Dominating Visualizations
**What goes wrong:** Single 300-yard topped shot compresses entire dispersion scatter plot
**Why it happens:** Plotly auto-scales axes to include all data
**How to avoid:**
- Apply IQR filtering BEFORE visualization: `df_filtered = df[filter_outliers_iqr(df['carry'])]`
- Show outlier count in caption: "Showing 47 shots (3 outliers filtered)"
- Option to toggle outliers on/off (advanced users may want to see them)
**Warning signs:** Scatter plot where all points clustered in corner, axes spanning 0-500 yards

### Pitfall 3: Misleading "Best" Statistics
**What goes wrong:** User sees "Driver: 280 yards" and thinks that's normal distance
**Why it happens:** Showing maximum instead of median/typical
**How to avoid:**
- PRIMARY metric: Median (typical shot)
- SECONDARY metrics: 25th/75th percentile (consistency range)
- TERTIARY metric: Max (best shot, clearly labeled)
- UI: "Typical: 245 yds | Best: 262 yds | Range: 238-252 yds (IQR)"
**Warning signs:** User surprised on course ("my 7-iron goes 170!" but median is 155)

### Pitfall 4: Session Quality Score Opacity
**What goes wrong:** User sees "Session Quality: 68" with no understanding why
**Why it happens:** Black-box composite scoring
**How to avoid:**
- Show component breakdown: "Consistency: 72 | Performance: 65 | Improvement: 68"
- Provide context: "72/100 consistency (better than 60% of your sessions)"
- Actionable feedback: "Improve consistency by focusing on strike location"
**Warning signs:** User asks "why is my score low?" with no answer

### Pitfall 5: False Trend Confidence with Small N
**What goes wrong:** User sees "improving" trend line after 3 lucky sessions
**Why it happens:** Linear regression always produces a line, regardless of significance
**How to avoid:**
- Calculate p-value using `scipy.stats.linregress`
- Show confidence indicator: "Trend: Improving ⚠️ (3 sessions, not yet significant)"
- Require 5+ sessions before showing "statistically significant improvement"
- Gray out trend line if p > 0.05
**Warning signs:** Wild swing in trend line with one new session, contradictory messages

## Code Examples

Verified patterns from official sources and existing codebase:

### IQR Outlier Filtering
```python
# Source: Context7 scipy documentation + CareerFoundry research
from scipy.stats import iqr
import pandas as pd

def filter_outliers(df: pd.DataFrame, column: str, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Filter outliers from DataFrame using IQR method.

    Args:
        df: Input DataFrame
        column: Column to check for outliers
        multiplier: IQR multiplier (1.5 standard, 3.0 extreme)

    Returns:
        Filtered DataFrame with outliers removed
    """
    data = df[column].dropna()

    q1 = data.quantile(0.25)
    q3 = data.quantile(0.75)
    iqr_value = iqr(data, nan_policy='omit')

    lower = q1 - multiplier * iqr_value
    upper = q3 + multiplier * iqr_value

    return df[(df[column] >= lower) & (df[column] <= upper)]
```

### Distance Statistics with Confidence
```python
# Source: Context7 pandas + golf analytics research
def calculate_distance_stats(df: pd.DataFrame, club: str) -> dict:
    """Calculate robust distance statistics with sample size awareness."""
    club_data = df[df['club'] == club]['carry'].dropna()
    n = len(club_data)

    if n < 3:
        return {'error': 'Insufficient data', 'n': n}

    # Remove outliers
    club_data = club_data[filter_outliers_iqr(club_data)]

    stats = {
        'median': club_data.median(),
        'q25': club_data.quantile(0.25),
        'q75': club_data.quantile(0.75),
        'iqr': iqr(club_data),
        'max': club_data.max(),
        'n': n,
        'n_after_filter': len(club_data),
        'outliers_removed': n - len(club_data)
    }

    # Confidence note
    if n < 5:
        stats['confidence'] = 'low'
        stats['note'] = f'Limited data ({n} shots)'
    elif n < 10:
        stats['confidence'] = 'medium'
    else:
        stats['confidence'] = 'high'

    return stats
```

### Plotly Scatter with Custom Hover
```python
# Source: Context7 plotly documentation
import plotly.graph_objects as go

def render_dispersion_scatter(df: pd.DataFrame, club: str = None) -> None:
    """Render shot dispersion scatter plot with outlier filtering."""

    # Filter to club if specified
    if club:
        df = df[df['club'] == club]

    # Remove outliers
    df = df[filter_outliers_iqr(df['carry'])]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['side_distance'],
        y=df['carry'],
        mode='markers',
        marker=dict(
            size=10,
            color=df['smash'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Smash Factor")
        ),
        text=df['club'],
        customdata=df[['ball_speed', 'launch_angle']],
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "Carry: %{y:.1f} yds<br>" +
            "Side: %{x:.1f} yds<br>" +
            "Ball Speed: %{customdata[0]:.1f} mph<br>" +
            "Launch: %{customdata[1]:.1f}°<br>" +
            "Smash: %{marker.color:.2f}<extra></extra>"
        )
    ))

    fig.update_layout(
        title=f"Shot Dispersion{' - ' + club if club else ''}",
        xaxis_title="Side Distance (yds)",
        yaxis_title="Carry Distance (yds)",
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=True)
```

### Session-to-Session Trend Analysis
```python
# Source: existing trend_chart.py + scipy statistical tests
from scipy import stats
import numpy as np

def analyze_session_trend(sessions: list, metric: str) -> dict:
    """
    Analyze trend across sessions with statistical significance.

    Args:
        sessions: List of dicts with session_id, date, metric value
        metric: Metric name to analyze

    Returns:
        Dict with trend stats, significance, visualization data
    """
    if len(sessions) < 3:
        return {'error': 'Need 3+ sessions for trend analysis'}

    # Extract values
    values = [s[metric] for s in sessions if metric in s]
    x = np.arange(len(values))

    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)

    # Calculate improvement
    first = values[0]
    last = values[-1]
    improvement_pct = ((last - first) / first * 100) if first != 0 else 0

    # Determine significance and message
    is_significant = p_value < 0.05 and len(values) >= 5

    if is_significant:
        if slope > 0:
            message = f"Improving significantly ({improvement_pct:+.1f}%, p={p_value:.3f})"
        else:
            message = f"Declining significantly ({improvement_pct:+.1f}%, p={p_value:.3f})"
    else:
        message = f"Trend not yet significant ({len(values)} sessions, need 5+)"

    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_value ** 2,
        'p_value': p_value,
        'is_significant': is_significant,
        'improvement_pct': improvement_pct,
        'message': message,
        'trend_line': intercept + slope * x  # For plotting
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Max distance reporting | Median + IQR + percentiles | Golf analytics matured ~2015 | Prevents misleading "I hit it 280!" based on one lucky shot |
| Mean with std deviation | Median with IQR for skewed data | Stats best practice | Robust to outliers, more accurate for golf data |
| Basic ball flight classification | D-plane theory (TrackMan) | ~2008 TrackMan research | Physics-based, explains why ball curves, not just observation |
| Manual chart scaling | Plotly auto-scaling with outlier filtering | Plotly 4.0+ (2020) | Better UX, no compressed visualizations |
| Black-box quality scores | Component breakdowns + normalization | Modern analytics UX | User understanding, actionable feedback |

**Deprecated/outdated:**
- **"Old ball flight laws"**: Pre-D-plane theory saying "swing path determines initial direction" (wrong—face angle primary)
- **Strokes gained without baseline**: Requires PGA Tour baselines or handicap-specific data (not in Phase 2 scope)
- **Complex ML for simple stats**: Overkill for percentile/median calculations; pandas native methods sufficient

## Open Questions

1. **Session quality score thresholds for normalization**
   - What we know: Need min/max ranges for smash, std_dev, etc. to normalize 0-100
   - What's unclear: Recreational player ranges vs Tour player ranges (very different scales)
   - Recommendation: Use user's historical data for personalized normalization (5th/95th percentile as min/max)

2. **Minimum sample sizes for each analytic**
   - What we know: 3 shots minimum for basic stats, 5+ for trends
   - What's unclear: Optimal thresholds for per-club analysis with limited data
   - Recommendation: Start conservative (n=5), add "show anyway" option for advanced users

3. **Miss tendency classification thresholds**
   - What we know: D-plane theory fundamentals, face-to-path differential drives curve
   - What's unclear: Exact degree thresholds for straight/draw/fade/hook/slice boundaries
   - Recommendation: Use existing `local_coach.py` thresholds (validated against Uneekor data), tune with user feedback

## Sources

### Primary (HIGH confidence)
- Context7 scipy (/websites/scipy_doc_scipy) - IQR calculation, statistical methods
- Context7 plotly (/plotly/plotly.py) - Scatter plot customization, hover templates
- Context7 pandas (/websites/pandas_pydata) - Quantile, median, groupby aggregation
- Existing codebase: `components/heatmap_chart.py`, `radar_chart.py`, `trend_chart.py` - Established patterns

### Secondary (MEDIUM confidence)
- [Practical Golf - Driver Dispersion](https://practical-golf.com/driver-dispersion) - Golf analytics best practices
- [HackMotion - Shot Dispersion](https://hackmotion.com/shot-dispersion-in-golf/) - Industry standard metrics
- [Golf Ball Flight Laws](https://perfectgolfswingreview.net/ballflight.htm) - D-plane theory
- [CareerFoundry - Outlier Detection](https://careerfoundry.com/en/blog/data-analytics/how-to-find-outliers/) - IQR method verification
- [GeeksforGeeks - IQR in Python](https://www.geeksforgeeks.org/machine-learning/interquartile-range-to-detect-outliers-in-data/) - Implementation patterns

### Tertiary (LOW confidence)
- [Session Quality Measure](https://optimizingaudience.com/articles/session-quality-measure/) - GA4 session quality (different domain, general concept)
- [HackMotion - Track Golf Stats](https://hackmotion.com/track-golf-stats/) - Consistency metrics (blog post, not primary research)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - scipy/pandas/plotly already in use, verified via Context7
- Architecture: HIGH - Patterns established in existing codebase, D-plane theory validated
- Pitfalls: MEDIUM - Based on general analytics experience + golf domain research, not project-specific failures

**Research date:** 2026-02-10
**Valid until:** 60 days (stable domain—golf analytics hasn't changed significantly in years)
