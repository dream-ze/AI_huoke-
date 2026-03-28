from app.services.collector_enricher import enrich_item
from app.services.collector_normalizer import build_item


def test_build_item_cleans_and_dedups_fields():
    item = build_item(
        raw={
            "source_platform": "xiaohongshu",
            "source_id": "abc123",
            "url": " https://www.xiaohongshu.com/explore/abc123 ",
            "title": " 标题\u200b示例 ",
            "snippet": " 标题示例 ",
            "author_name": " 小红 ",
            "content_text": "  正文 第一行\n\n第二行  ",
            "image_urls": [
                "https://img.example.com/content/a.jpg",
                "https://img.example.com/content/a.jpg",
                "data:image/png;base64,abc",
            ],
            "like_count": "1.2w",
            "comment_count": "8",
        },
        keyword="贷款",
        task_id="task_001",
    )

    assert item.title == "标题示例"
    assert item.snippet is None
    assert item.author_name == "小红"
    assert item.image_urls == ["https://img.example.com/content/a.jpg"]
    assert item.like_count == 12000
    assert item.comment_count == 8


def test_enrich_item_calculates_scores_and_flags():
    item = build_item(
        raw={
            "source_platform": "xiaohongshu",
            "source_id": "abc123",
            "url": "https://www.xiaohongshu.com/explore/abc123",
            "title": "完整标题",
            "content_text": "这是完整正文" * 20,
            "image_urls": ["https://img.example.com/content/a.jpg"],
            "publish_time": "2026-03-26T10:00:00+08:00",
            "comment_count": 4,
            "like_count": 20,
            "parse_stage": "detail",
            "parse_status": "detail_success",
            "detail_attempted": True,
        },
        keyword="贷款",
        task_id="task_001",
    )

    result = enrich_item(item)

    assert result.field_completeness > 0.7
    assert result.engagement_score == 32.0
    assert result.quality_score > 0.6
    assert result.is_detail_complete is True
