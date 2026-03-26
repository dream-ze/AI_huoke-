from datetime import datetime
from time import perf_counter
from uuid import uuid4

from app.factories.collector_factory import CollectorFactory
from app.schemas.request import CollectRequest
from app.schemas.result import CollectResponse, CollectStats


class CollectService:
    @staticmethod
    def run_collect(data: CollectRequest) -> CollectResponse:
        request_id = f"collect_{data.platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        fallback_task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        task_id = fallback_task_id
        started_at = datetime.now().astimezone()
        start_ts = perf_counter()

        try:
            collector = CollectorFactory.get_collector(data.platform)
            items, stats = collector.collect(data)
            task_id = items[0].task_id if items else fallback_task_id

            parsed_count = len(items)
            success = parsed_count > 0
            message = "采集完成" if success else "未采集到有效数据"

            return CollectResponse(
                success=success,
                platform=data.platform,
                keyword=data.keyword,
                task_id=task_id,
                count=parsed_count,
                items=items,
                stats=stats,
                message=message,
                request_id=request_id,
                cost_ms=int((perf_counter() - start_ts) * 1000),
                collected_at=started_at,
            )
        except Exception as ex:
            return CollectResponse(
                success=False,
                platform=data.platform,
                keyword=data.keyword,
                task_id=task_id,
                count=0,
                items=[],
                stats=CollectStats(detail_failed=1),
                message=str(ex),
                request_id=request_id,
                cost_ms=int((perf_counter() - start_ts) * 1000),
                collected_at=started_at,
            )
