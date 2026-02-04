"""
Reusable UI components for the Golf Data App.
"""

from .session_selector import render_session_selector
from .metrics_card import render_metrics_row
from .shot_table import render_shot_table
from .heatmap_chart import render_impact_heatmap
from .trend_chart import render_trend_chart
from .radar_chart import render_radar_chart
from .export_tools import (
    render_csv_export_button,
    render_excel_export_button,
    render_summary_export
)

# Wave 1: New UI components
from .shared_sidebar import (
    render_shared_sidebar,
    render_navigation,
    render_data_source,
    render_sync_status,
    render_mode_toggle,
    render_session_stats,
    render_documentation_links,
)
from .loading_states import (
    render_skeleton_card,
    render_skeleton_metrics,
    render_skeleton_table,
    render_loading_spinner,
    render_progress_bar,
    render_loading_placeholder,
    LoadingContext,
)
from .empty_states import (
    render_empty_state,
    render_no_data_state,
    render_no_sessions_state,
    render_no_shots_for_filter_state,
    render_no_club_data_state,
    render_error_state,
    render_ai_unavailable_state,
    render_comparison_empty_state,
    render_section_empty_state,
)

# Wave 2: Core value components
from .metrics_card import (
    render_kpi_card,
    render_kpi_grid,
    render_club_kpi_cards,
)
from .session_comparison import (
    render_session_comparison,
    render_comparison_selector,
)
from .session_header import (
    render_session_header,
    render_compact_session_header,
)

# Wave 3: Persona coverage components
from .simple_view import (
    render_simple_dashboard,
    render_mode_toggle as render_view_mode_toggle,
)
from .coach_export import (
    render_coach_export,
    export_session_csv,
    export_session_json,
    generate_session_summary,
    generate_club_summary,
    identify_problem_shots,
)
from .session_list import (
    render_session_list,
    render_session_timeline,
)

# Wave 4: AI enhancements
from .ai_insights import (
    generate_session_insights,
    render_insights_card,
    render_quick_insights_banner,
)

__all__ = [
    # Original components
    'render_session_selector',
    'render_metrics_row',
    'render_shot_table',
    'render_impact_heatmap',
    'render_trend_chart',
    'render_radar_chart',
    'render_csv_export_button',
    'render_excel_export_button',
    'render_summary_export',
    # Shared sidebar
    'render_shared_sidebar',
    'render_navigation',
    'render_data_source',
    'render_sync_status',
    'render_mode_toggle',
    'render_session_stats',
    'render_documentation_links',
    # Loading states
    'render_skeleton_card',
    'render_skeleton_metrics',
    'render_skeleton_table',
    'render_loading_spinner',
    'render_progress_bar',
    'render_loading_placeholder',
    'LoadingContext',
    # Empty states
    'render_empty_state',
    'render_no_data_state',
    'render_no_sessions_state',
    'render_no_shots_for_filter_state',
    'render_no_club_data_state',
    'render_error_state',
    'render_ai_unavailable_state',
    'render_comparison_empty_state',
    'render_section_empty_state',
    # Wave 2: Core value components
    'render_kpi_card',
    'render_kpi_grid',
    'render_club_kpi_cards',
    'render_session_comparison',
    'render_comparison_selector',
    'render_session_header',
    'render_compact_session_header',
    # Wave 3: Persona coverage components
    'render_simple_dashboard',
    'render_view_mode_toggle',
    'render_coach_export',
    'export_session_csv',
    'export_session_json',
    'generate_session_summary',
    'generate_club_summary',
    'identify_problem_shots',
    'render_session_list',
    'render_session_timeline',
    # Wave 4: AI enhancements
    'generate_session_insights',
    'render_insights_card',
    'render_quick_insights_banner',
]
