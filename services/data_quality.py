"""Backward compatibility — delegates to golf-data-core package."""
from core_dependency import ensure_golf_data_core

ensure_golf_data_core()

from golf_data.filters.quality import *  # noqa: F401,F403
from golf_data.filters.quality import _apply_hard_caps, _apply_zscore  # noqa: F401
