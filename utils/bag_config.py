"""
Bag configuration loader.

Reads my_bag.json to provide club ordering and filtering
for Club Profiles, Dashboard, and other views.
"""

import json
import os
from typing import Dict, List, Optional

_BAG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'my_bag.json')
_cache: Optional[Dict] = None


def _load() -> Dict:
    """Load and cache bag configuration."""
    global _cache
    if _cache is None:
        with open(_BAG_PATH, 'r') as f:
            _cache = json.load(f)
    return _cache


def get_bag_order() -> List[str]:
    """Return ordered list of club canonical names (longest to shortest)."""
    return _load()['bag_order']


def get_club_aliases() -> Dict[str, List[str]]:
    """Return mapping of canonical name -> list of aliases."""
    return {c['canonical']: c.get('aliases', []) for c in _load()['clubs']}


def is_in_bag(club_name: str) -> bool:
    """Check if a club is in the configured bag."""
    bag = _load()
    canonicals = {c['canonical'] for c in bag['clubs']}
    return club_name in canonicals


def get_club_sort_key(club_name: str) -> int:
    """Return sort index for a club (for consistent ordering in UI)."""
    order = get_bag_order()
    try:
        return order.index(club_name)
    except ValueError:
        return len(order)  # Unknown clubs sort to end


def get_smash_target(club_name: str) -> Optional[List[float]]:
    """Return [low, high] smash factor target for a club, or None if not configured."""
    targets = _load().get('smash_targets', {})
    return targets.get(club_name)


def get_adjacent_clubs(club_name: str) -> List[str]:
    """Return clubs adjacent in the bag (for smart comparison suggestions).

    E.g., for '7 Iron' returns ['6 Iron', '8 Iron'].
    For 'Driver' returns ['3 Wood'].
    """
    order = get_bag_order()
    try:
        idx = order.index(club_name)
    except ValueError:
        return []
    adjacent = []
    if idx > 0:
        adjacent.append(order[idx - 1])
    if idx < len(order) - 1:
        adjacent.append(order[idx + 1])
    return adjacent


def reload():
    """Clear cache to force re-read on next access."""
    global _cache
    _cache = None
