"""
Goal tracking for per-club performance targets.

Stores goals in a JSON file alongside my_bag.json.
Tracks progress over sessions.
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime

_GOALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'goals.json')
_cache: Optional[Dict] = None


def _load() -> Dict:
    """Load and cache goals."""
    global _cache
    if _cache is None:
        if os.path.exists(_GOALS_PATH):
            try:
                with open(_GOALS_PATH, 'r') as f:
                    content = f.read().strip()
                    _cache = json.loads(content) if content else {"goals": []}
            except (json.JSONDecodeError, IOError):
                _cache = {"goals": []}
        else:
            _cache = {"goals": []}
    return _cache


def _save(data: Dict) -> None:
    """Save goals to disk."""
    global _cache
    _cache = data
    with open(_GOALS_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def get_goals(club: str = None) -> List[Dict]:
    """Get all goals, optionally filtered by club.

    Args:
        club: Optional club name filter.

    Returns:
        List of goal dicts with keys: id, club, metric, target, created_at.
    """
    data = _load()
    goals = data.get('goals', [])
    if club:
        goals = [g for g in goals if g.get('club') == club]
    return goals


def add_goal(club: str, metric: str, target: float, description: str = "") -> Dict:
    """Add a new goal.

    Args:
        club: Club name (e.g., "7 Iron").
        metric: Metric to track ("carry", "smash", "ball_speed").
        target: Target value.
        description: Optional description.

    Returns:
        The created goal dict.
    """
    data = _load()
    goal = {
        "id": f"{club}_{metric}_{int(datetime.now().timestamp())}",
        "club": club,
        "metric": metric,
        "target": target,
        "description": description,
        "created_at": datetime.now().isoformat(),
    }
    data.setdefault('goals', []).append(goal)
    _save(data)
    return goal


def remove_goal(goal_id: str) -> bool:
    """Remove a goal by ID.

    Returns:
        True if goal was found and removed.
    """
    data = _load()
    original_len = len(data.get('goals', []))
    data['goals'] = [g for g in data.get('goals', []) if g.get('id') != goal_id]
    if len(data['goals']) < original_len:
        _save(data)
        return True
    return False


def compute_progress(goal: Dict, current_value: Optional[float]) -> Dict:
    """Compute progress toward a goal.

    Args:
        goal: Goal dict with 'target' key.
        current_value: Current measured value.

    Returns:
        Dict with progress_pct, current, target, gap.
    """
    target = goal.get('target', 0)
    if current_value is None or target == 0:
        return {"progress_pct": 0, "current": current_value, "target": target, "gap": None}

    progress = min(100, (current_value / target) * 100)
    gap = target - current_value

    return {
        "progress_pct": progress,
        "current": current_value,
        "target": target,
        "gap": gap,
    }


def reload():
    """Clear cache to force re-read."""
    global _cache
    _cache = None
