from dataclasses import dataclass
from typing import Dict, List, Type, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    provider_cls: Type


_PROVIDERS: Dict[str, ProviderSpec] = {}


def register_provider(provider_cls):
    """Register an AI provider class.

    Args:
        provider_cls: Class with PROVIDER_ID and DISPLAY_NAME class attributes

    Raises:
        ValueError: If PROVIDER_ID or DISPLAY_NAME is missing
    """
    provider_id = getattr(provider_cls, "PROVIDER_ID", None)
    display_name = getattr(provider_cls, "DISPLAY_NAME", None)
    if not provider_id or not display_name:
        raise ValueError("Provider must define PROVIDER_ID and DISPLAY_NAME")

    # Warn on duplicate registration (may indicate config issue)
    if provider_id in _PROVIDERS:
        logger.warning(
            f"Provider '{provider_id}' is being re-registered. "
            f"Previous: {_PROVIDERS[provider_id].provider_cls.__name__}, "
            f"New: {provider_cls.__name__}"
        )

    _PROVIDERS[provider_id] = ProviderSpec(
        provider_id=provider_id,
        display_name=display_name,
        provider_cls=provider_cls
    )
    return provider_cls


def list_providers() -> List[ProviderSpec]:
    """Return list of all registered providers."""
    return list(_PROVIDERS.values())


def get_provider(provider_id: str) -> Optional[ProviderSpec]:
    """Get a provider by ID.

    Args:
        provider_id: The provider identifier

    Returns:
        ProviderSpec if found, None otherwise
    """
    return _PROVIDERS.get(provider_id)
