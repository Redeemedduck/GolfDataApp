"""
Sync Status Component for GolfDataApp.

Displays cloud sync health in Streamlit UI with color-coded indicators.
"""

import streamlit as st
import golf_db
from datetime import datetime, timedelta


def render_sync_status():
    """
    Render sync status indicator in Streamlit.

    Shows:
    - Green checkmark if synced
    - Yellow warning if pending
    - Red X if error
    - Gray circle if offline mode

    Includes timestamp of last sync and retry button on errors.
    """
    status_data = golf_db.get_sync_status()

    status = status_data.get("status", "offline")
    last_sync = status_data.get("last_sync")
    pending_count = status_data.get("pending_count", 0)
    last_error = status_data.get("last_error")

    # Format last sync time
    if last_sync:
        if isinstance(last_sync, str):
            try:
                last_sync_dt = datetime.fromisoformat(last_sync)
            except ValueError:
                last_sync_dt = None
        else:
            last_sync_dt = last_sync

        if last_sync_dt:
            now = datetime.utcnow()
            delta = now - last_sync_dt
            if delta < timedelta(minutes=1):
                time_ago = "just now"
            elif delta < timedelta(hours=1):
                mins = int(delta.total_seconds() / 60)
                time_ago = f"{mins}m ago"
            elif delta < timedelta(days=1):
                hours = int(delta.total_seconds() / 3600)
                time_ago = f"{hours}h ago"
            else:
                days = delta.days
                time_ago = f"{days}d ago"
        else:
            time_ago = "unknown"
    else:
        time_ago = None

    # Render status indicator
    if status == "synced":
        st.sidebar.caption(f"✓ Synced {time_ago}" if time_ago else "✓ Synced")

    elif status == "pending":
        st.sidebar.caption(f"⚠ {pending_count} pending sync")

    elif status == "error":
        st.sidebar.caption(f"✗ Sync error")
        if last_error:
            with st.sidebar.expander("Error details"):
                st.caption(last_error)
        if st.sidebar.button("Retry Sync", key="retry_sync_button"):
            st.sidebar.info("Retry functionality coming soon")

    elif status == "offline":
        st.sidebar.caption("○ Offline mode")
