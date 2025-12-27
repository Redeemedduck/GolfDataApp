"""
Repository Layer - Data Access

This package contains repository classes that handle data access
and abstract database implementations.

Repositories:
- BaseRepository: Base repository pattern with common operations
- SyncBaseRepository: Synchronous version of BaseRepository
- ShotRepository: Shot data access (SQLite + Firestore)
- MediaRepository: Media storage access (Supabase Storage)
"""

from .base_repository import BaseRepository, SyncBaseRepository
from .shot_repository import ShotRepository
from .media_repository import MediaRepository

__all__ = ['BaseRepository', 'SyncBaseRepository', 'ShotRepository', 'MediaRepository']
