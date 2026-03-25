from app.schemas.request import CollectRequest
from app.schemas.result import CollectResponse
from app.factories.collector_factory import CollectorFactory


class CollectService:
    @staticmethod
    def run_collect(data: CollectRequest) -> CollectResponse:
        try:
            collector = CollectorFactory.get_collector(data.platform)
            items = collector.collect(keyword=data.keyword, max_items=data.max_items)

            return CollectResponse(
                success=True,
                platform=data.platform,
                keyword=data.keyword,
                count=len(items),
                items=items,
                message="采集完成",
            )
        except Exception as e:
            return CollectResponse(
                success=False,
                platform=data.platform,
                keyword=data.keyword,
                count=0,
                items=[],
                message=str(e),
            )
