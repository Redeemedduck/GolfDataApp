"""Helpers for validating shared core package dependencies."""

from __future__ import annotations


def ensure_golf_data_core() -> None:
    """Raise a clear error if golf-data-core is unavailable."""
    try:
        import golf_data  # noqa: F401
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("golf_data"):
            raise ModuleNotFoundError(
                "Missing required dependency 'golf-data-core'. "
                "Install project dependencies with `pip install -r requirements.txt`."
            ) from exc
        raise
