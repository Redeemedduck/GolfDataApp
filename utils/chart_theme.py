"""Unified chart theme for all Plotly figures.

Dark mode as default — simulators are dark; pure white is jarring.
Context colors: green (good), yellow (needs attention), red (poor), blue (neutral).
"""
import plotly.graph_objects as go

# ── Palette ───────────────────────────────────────────────
BG_PRIMARY = "#1a1a2e"       # Dark navy background
BG_CARD = "#16213e"          # Card / secondary background
TEXT_COLOR = "#e8e8e8"        # Primary text
TEXT_MUTED = "#8892a4"        # Secondary text
GRID_COLOR = "#2a2a4a"       # Subtle grid lines
BORDER_COLOR = "#2a2a4a"

# Context colors (highest-impact design element)
COLOR_GOOD = "#00d26a"       # Green — good / improving
COLOR_FAIR = "#ffc107"       # Amber — needs attention
COLOR_POOR = "#ff4757"       # Red — poor / declining
COLOR_NEUTRAL = "#4dabf7"    # Blue — informational
COLOR_ACCENT = "#a29bfe"     # Purple — highlights

# Categorical palette for multi-club charts
CATEGORICAL = [
    "#4dabf7", "#00d26a", "#ffc107", "#ff4757",
    "#a29bfe", "#fd79a8", "#00cec9", "#fdcb6e",
    "#6c5ce7", "#e17055", "#81ecec", "#fab1a0",
]

# ── Layout defaults ───────────────────────────────────────
_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=BG_PRIMARY,
    plot_bgcolor=BG_PRIMARY,
    font=dict(family="Inter, sans-serif", color=TEXT_COLOR, size=13),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=dict(
        gridcolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_MUTED),
    ),
    yaxis=dict(
        gridcolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_MUTED),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COLOR),
    ),
    colorway=CATEGORICAL,
)


def themed_figure(**kwargs) -> go.Figure:
    """Create a new Plotly figure pre-styled with the dark theme.

    Any layout kwargs override the defaults.
    """
    layout = {**_LAYOUT_DEFAULTS, **kwargs}
    return go.Figure(layout=layout)


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the dark theme to an existing Plotly figure."""
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


def context_color(value: float, green_threshold: float, yellow_threshold: float) -> str:
    """Return context color based on value and thresholds.

    For metrics where LOWER is better (e.g., std dev, dispersion):
        value <= green  → good (green)
        value <= yellow → fair (amber)
        value > yellow  → poor (red)

    Args:
        value: The metric value.
        green_threshold: Upper bound for "good".
        yellow_threshold: Upper bound for "fair".

    Returns:
        CSS hex color string.
    """
    if value is None:
        return TEXT_MUTED
    if value <= green_threshold:
        return COLOR_GOOD
    if value <= yellow_threshold:
        return COLOR_FAIR
    return COLOR_POOR


def context_color_higher_better(value: float, red_threshold: float, yellow_threshold: float) -> str:
    """Return context color where HIGHER is better (e.g., smash factor).

    value >= yellow → good (green)
    value >= red    → fair (amber)
    value < red     → poor (red)
    """
    if value is None:
        return TEXT_MUTED
    if value >= yellow_threshold:
        return COLOR_GOOD
    if value >= red_threshold:
        return COLOR_FAIR
    return COLOR_POOR
