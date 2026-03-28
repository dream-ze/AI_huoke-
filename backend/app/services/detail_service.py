from app.factories.collector_factory import CollectorFactory
from app.schemas.detail import CollectDetailRequest, CollectDetailResponse


class DetailService:
    @staticmethod
    def fetch_detail(req: CollectDetailRequest) -> CollectDetailResponse:
        try:
            collector = CollectorFactory.get_collector(req.platform)
            item = collector.fetch_detail(req)
            is_success = item.parse_status == "detail_success"
            return CollectDetailResponse(
                success=is_success,
                platform=req.platform,
                url=item.url,
                source_id=item.source_id,
                data=item,
                message="详情补采完成" if is_success else "详情补采失败",
                raw_data=item.raw_data,
            )
        except Exception as ex:
            return CollectDetailResponse(
                success=False,
                platform=req.platform,
                url=req.url or "",
                source_id=req.source_id or "",
                data=None,
                message=f"详情补采失败: {ex}",
                raw_data={},
            )
