"""
Base Repository Class

Provides common data access patterns for all repositories including:
- CRUD operations
- Filtering and querying
- Error handling
- Connection management
"""

import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class BaseRepository(ABC):
    """
    Abstract base class for all repository classes.

    Implements the Repository pattern to abstract data access
    and provide consistent interface across different storage backends.
    """

    def __init__(self, connection: Any = None):
        """
        Initialize base repository.

        Args:
            connection: Database connection or client object
        """
        self.connection = connection
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """
        Set up logger for this repository.

        Returns:
            Configured logger instance
        """
        logger_name = f"golf_data.{self.__class__.__name__}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Find entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Find all entities matching filters.

        Args:
            filters: Optional filter criteria

        Returns:
            List of entity dictionaries
        """
        pass

    @abstractmethod
    async def save(self, entity: Dict[str, Any]) -> str:
        """
        Save entity to storage.

        Args:
            entity: Entity dictionary to save

        Returns:
            Entity ID
        """
        pass

    @abstractmethod
    async def update(self, id: str, updates: Dict[str, Any]) -> bool:
        """
        Update entity by ID.

        Args:
            id: Entity ID
            updates: Dictionary of fields to update

        Returns:
            True if update successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deletion successful, False otherwise
        """
        pass

    def _log_operation(self, operation: str, **context):
        """
        Log repository operation.

        Args:
            operation: Operation name
            **context: Additional context
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{operation} | {context_str}"
        else:
            message = operation
        self.logger.info(message)

    def _log_error(self, message: str, error: Exception, **context):
        """
        Log repository error.

        Args:
            message: Error message
            error: Exception object
            **context: Additional context
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"

        self.logger.error(f"{message} | error={str(error)}", exc_info=True)

    def _build_filter_clause(self, filters: Dict[str, Any]) -> str:
        """
        Build SQL WHERE clause from filters.

        Args:
            filters: Dictionary of filter criteria

        Returns:
            SQL WHERE clause string
        """
        if not filters:
            return ""

        conditions = []
        for key, value in filters.items():
            if value is None:
                conditions.append(f"{key} IS NULL")
            elif isinstance(value, (list, tuple)):
                # IN clause for lists
                values_str = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in value)
                conditions.append(f"{key} IN ({values_str})")
            elif isinstance(value, str):
                conditions.append(f"{key} = '{value}'")
            else:
                conditions.append(f"{key} = {value}")

        return "WHERE " + " AND ".join(conditions) if conditions else ""

    def _validate_entity(self, entity: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate entity has required fields.

        Args:
            entity: Entity dictionary
            required_fields: List of required field names

        Raises:
            ValueError: If required fields are missing
        """
        missing = [field for field in required_fields if field not in entity]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    def __repr__(self) -> str:
        """String representation of repository."""
        return f"<{self.__class__.__name__}>"


class SyncBaseRepository(BaseRepository):
    """
    Synchronous version of BaseRepository for non-async operations.

    Use this when async operations are not needed or not supported
    by the underlying storage backend.
    """

    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Synchronous find by ID."""
        pass

    def find_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Synchronous find all."""
        pass

    def save(self, entity: Dict[str, Any]) -> str:
        """Synchronous save."""
        pass

    def update(self, id: str, updates: Dict[str, Any]) -> bool:
        """Synchronous update."""
        pass

    def delete(self, id: str) -> bool:
        """Synchronous delete."""
        pass
