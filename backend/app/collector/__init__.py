"""采集模块 - 独立子系统"""

from app.collector.services import (
    AcquisitionIntakeService,
    BrowserCollectorClient,
    CollectService,
    CollectorFactory,
    InboxService,
    MaterialPipelineOrchestrator,
    PLATFORM_LABELS,
    ALL_CATEGORIES,
)
from app.collector.adapters import BaseCollector
from app.collector.parsers import XiaohongshuCollector

__all__ = [
    "AcquisitionIntakeService",
    "BaseCollector",
    "BrowserCollectorClient",
    "CollectService",
    "CollectorFactory",
    "InboxService",
    "MaterialPipelineOrchestrator",
    "PLATFORM_LABELS",
    "ALL_CATEGORIES",
    "XiaohongshuCollector",
]