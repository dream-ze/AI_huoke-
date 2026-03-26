from datetime import datetime
from time import perf_counter
from uuid import uuid4

from app.core.config import settings
from app.factories.collector_factory import CollectorFactory
from app.schemas.request import CollectRequest
from app.schemas.result import CollectResponse, CollectStats
from app.utils.excel_export import export_sample_to_excel


class CollectService:
    @staticmethod
    def run_collect(data: CollectRequest) -> CollectResponse:
        request_id = f"collect_{data.platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        started_at = datetime.now().astimezone()
        start_ts = perf_counter()

        try:
            collector = CollectorFactory.get_collector(data.platform)
            items, stats, has_more = collector.collect(keyword=data.keyword, max_items=data.max_items)

            sample_excel_file = None
            if data.export_sample_excel and items:
                sample_excel_file = export_sample_to_excel(
                    items=items,
                    keyword=data.keyword,
                    platform=data.platform,
                    sample_size=data.sample_size,
                    export_dir=settings.SAMPLE_EXPORT_DIR,
                )

            parsed_count = len(items)
            if parsed_count == 0:
                task_status = "failed"
                success = False
                message = "未采集到有效数据"
            elif stats.failed > 0 or stats.parsed < min(data.max_items, max(stats.scanned, 1)):
                task_status = "partial"
                success = True
                message = "采集部分完成"
            else:
                task_status = "finished"
                success = True
                message = "采集完成"

            return CollectResponse(
                success=success,
                platform=data.platform,
                keyword=data.keyword,
                request_id=request_id,
                task_status=task_status,
                count=parsed_count,
                cost_ms=int((perf_counter() - start_ts) * 1000),
                collected_at=started_at.isoformat(),
                has_more=has_more,
                stats=stats,
                items=items,
                message=message,
                sample_excel_file=sample_excel_file,
            )
        except Exception as ex:
            return CollectResponse(
                success=False,
                platform=data.platform,
                keyword=data.keyword,
                request_id=request_id,
                task_status="failed",
                count=0,
                cost_ms=int((perf_counter() - start_ts) * 1000),
                collected_at=started_at.isoformat(),
                has_more=False,
                stats=CollectStats(scanned=0, parsed=0, deduplicated=0, failed=1),
                items=[],
                message=str(ex),
                sample_excel_file=None,
            )
