from dataclasses import dataclass
from typing import Dict, List, Type


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    display_name: str
    provider_cls: Type


_PROVIDERS: Dict[str, ProviderSpec] = {}


def register_provider(provider_cls):
    provider_id = getattr(provider_cls, "PROVIDER_ID", None)
    display_name = getattr(provider_cls, "DISPLAY_NAME", None)
    if not provider_id or not display_name:
        raise ValueError("Provider must define PROVIDER_ID and DISPLAY_NAME")
    _PROVIDERS[provider_id] = ProviderSpec(
        provider_id=provider_id,
        display_name=display_name,
        provider_cls=provider_cls
    )
    return provider_cls


def list_providers() -> List[ProviderSpec]:
    return list(_PROVIDERS.values())


def get_provider(provider_id: str) -> ProviderSpec:
    return _PROVIDERS.get(provider_id)
