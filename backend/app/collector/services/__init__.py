"""采集模块业务逻辑"""

from app.collector.services.browser_client import BrowserCollectorClient
from app.collector.services.collect_service import CollectService, PLATFORM_LABELS, ALL_CATEGORIES
from app.collector.services.enricher import enrich_item, should_drop
from app.collector.services.factory import CollectorFactory
from app.collector.services.inbox_service import InboxService
from app.collector.services.intake import AcquisitionIntakeService
from app.collector.services.normalizer import build_item, normalize_text
from app.collector.services.orchestrator import MaterialPipelineOrchestrator
from app.collector.services.pipeline import AcquisitionIntakeService as Pipeline

__all__ = [
    "AcquisitionIntakeService",
    "BrowserCollectorClient",
    "CollectService",
    "CollectorFactory",
    "InboxService",
    "MaterialPipelineOrchestrator",
    "PLATFORM_LABELS",
    "ALL_CATEGORIES",
    "Pipeline",
    "build_item",
    "enrich_item",
    "normalize_text",
    "should_drop",
]