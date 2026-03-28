from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.detail import CollectDetailResponse
from app.schemas.result import CollectResponse, CollectStats, ContentItem
from app.services.collect_service import CollectService
from app.services.detail_service import DetailService


client = TestClient(app)


def _build_item(parse_status: str = "detail_success") -> ContentItem:
    return ContentItem(
        source_platform="xiaohongshu",
        source_type="note",
        source_id="note_001",
        url="https://www.xiaohongshu.com/explore/note_001",
        keyword="贷款",
        task_id="task_001",
        title="测试标题",
        snippet="测试摘要",
        content_text="测试正文",
        image_urls=["https://img.example.com/1.jpg"],
        image_count=1,
        cover_url="https://img.example.com/1.jpg",
        like_count=5,
        comment_count=2,
        parse_stage="detail",
        detail_attempted=True,
        detail_error="",
        field_completeness=0.8,
        engagement_score=11,
        quality_score=0.8,
        lead_score=0.5,
        risk_level="low",
        content_length=4,
        is_detail_complete=True,
        collected_at=datetime.now().astimezone(),
        updated_at=datetime.now().astimezone(),
        parse_status=parse_status,
    )


def test_collect_run_contract(monkeypatch):
    def fake_run_collect(_data):
        return CollectResponse(
            success=True,
            platform="xiaohongshu",
            keyword="贷款",
            task_id="task_001",
            count=1,
            items=[_build_item()],
            stats=CollectStats(discovered=1, list_success=1, detail_attempted=1, detail_success=1),
            message="采集完成",
            request_id="req_001",
            cost_ms=12,
            collected_at=datetime.now().astimezone(),
        )

    monkeypatch.setattr(CollectService, "run_collect", staticmethod(fake_run_collect))

    payload = {
        "platform": "xiaohongshu",
        "keyword": "贷款",
        "max_items": 5,
        "need_detail": True,
        "need_comments": False,
        "dedup": True,
        "timeout_sec": 120,
    }
    response = client.post("/api/collect/run", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["platform"] == "xiaohongshu"
    assert body["keyword"] == "贷款"
    assert body["task_id"] == "task_001"
    assert body["count"] == 1
    assert isinstance(body["items"], list)
    assert set(["discovered", "list_success", "detail_attempted", "detail_success", "detail_failed", "dropped"]).issubset(
        set(body["stats"].keys())
    )


def test_collect_detail_contract(monkeypatch):
    def fake_fetch_detail(_req):
        item = _build_item(parse_status="detail_success")
        return CollectDetailResponse(
            success=True,
            platform="xiaohongshu",
            url=item.url,
            source_id=item.source_id,
            data=item,
            message="详情补采完成",
            raw_data={"stage": "detail"},
        )

    monkeypatch.setattr(DetailService, "fetch_detail", staticmethod(fake_fetch_detail))

    response = client.post(
        "/api/collect/detail",
        json={"platform": "xiaohongshu", "url": "https://www.xiaohongshu.com/explore/note_001"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["platform"] == "xiaohongshu"
    assert body["source_id"] == "note_001"
    assert body["data"]["parse_status"] == "detail_success"


def test_collect_detail_request_validation():
    response = client.post(
        "/api/collect/detail",
        json={"platform": "xiaohongshu"},
    )

    assert response.status_code == 422
