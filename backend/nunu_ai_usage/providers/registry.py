from pathlib import Path
from typing import Type

from nunu_ai_usage.providers.base import BaseProvider


_REGISTRY: dict[str, Type[BaseProvider]] = {}


def register_provider(provider_class: Type[BaseProvider]) -> None:
    provider_id = provider_class.provider_id.strip()

    if not provider_id:
        raise ValueError("Provider must define provider_id")

    if provider_id in _REGISTRY:
        raise ValueError(
            f"Provider already registered: {provider_id}"
        )

    _REGISTRY[provider_id] = provider_class


def create_provider(
    provider_id: str,
    runtime_dir: Path | None = None,
) -> BaseProvider:
    try:
        provider_class = _REGISTRY[provider_id]
    except KeyError as exc:
        raise KeyError(
            f"Unknown provider: {provider_id}"
        ) from exc

    return provider_class(runtime_dir=runtime_dir)


def list_providers() -> list[str]:
    return sorted(_REGISTRY)
