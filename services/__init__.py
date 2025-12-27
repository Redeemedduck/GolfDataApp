"""
Service Layer - Business Logic and Orchestration

This package contains service classes that handle business logic
and orchestrate operations across repositories and external APIs.

Services:
- BaseService: Base class with logging and error handling
- DataService: Unified database operations
- MediaService: Media caching and optimization
- ImportService: Import workflow orchestration
- AICoachService: Unified AI interface (Phase 2)
"""

from .base_service import BaseService
from .data_service import DataService
from .media_service import MediaService
from .import_service import ImportService

__all__ = ['BaseService', 'DataService', 'MediaService', 'ImportService']
