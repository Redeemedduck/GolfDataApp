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

# Wave 4: AI enhancements
from .ai_insights import (
    generate_session_insights,
    render_insights_card,
    render_quick_insights_banner,
)

# Wave 5: Big 3 Impact Laws + Journal
from .big3_summary import render_big3_summary
from .face_path_diagram import render_face_path_diagram
from .direction_tendency import (
    render_face_tendency,
    render_path_tendency,
    render_shot_shape_distribution,
)
from .big3_detail_view import render_big3_detail_view
from .journal_card import render_journal_card
from .journal_view import render_journal_view
from .calendar_strip import render_calendar_strip
from .date_range_filter import render_date_range_filter, filter_by_date_range
from .trajectory_view import render_trajectory_view

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
    # Wave 4: AI enhancements
    'generate_session_insights',
    'render_insights_card',
    'render_quick_insights_banner',
    # Wave 5: Big 3 + Journal
    'render_big3_summary',
    'render_face_path_diagram',
    'render_face_tendency',
    'render_path_tendency',
    'render_shot_shape_distribution',
    'render_big3_detail_view',
    'render_journal_card',
    'render_journal_view',
    'render_calendar_strip',
    'render_date_range_filter',
    'filter_by_date_range',
    'render_trajectory_view',
]
