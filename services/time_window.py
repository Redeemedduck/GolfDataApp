"""Backward compatibility — delegates to golf-data-core package."""
from core_dependency import ensure_golf_data_core

ensure_golf_data_core()

from golf_data.filters.time_window import *  # noqa: F401,F403
