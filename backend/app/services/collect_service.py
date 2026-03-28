"""Compatibility facade for the canonical collect service implementation."""

from app.domains.acquisition.collect_service import (
    ALL_CATEGORIES,
    PLATFORM_LABELS,
    CollectService,
)

__all__ = ["CollectService", "PLATFORM_LABELS", "ALL_CATEGORIES"]
