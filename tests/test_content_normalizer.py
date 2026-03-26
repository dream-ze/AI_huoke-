from datetime import datetime

from app.normalizers.content_normalizer import ContentNormalizer
from app.schemas.result import ContentItem


def _make_item(**overrides):
    base = {
        "platform": "xiaohongshu",
        "keyword": "贷款",
        "source_id": "abc123",
        "url": "https://www.xiaohongshu.com/explore/abc123",
        "collected_at": datetime.now().astimezone(),
        "parse_status": "list_only",
        "risk_status": "normal",
        "title": " 标题\u200b示例 ",
        "author_name": " 小红 ",
        "snippet": None,
        "content_text": "  正文 第一行\n\n第二行  ",
        "cover_url": None,
        "author_avatar_url": "https://img.example.com/avatar.jpg?x=1",
        "content_image_urls": [],
        "like_count": 10,
        "comment_count": 3,
    }
    base.update(overrides)
    return ContentItem(**base)


def test_normalize_text_preview_and_snippet_fallback():
    normalizer = ContentNormalizer()
    long_text = "内容" * 80
    item = _make_item(snippet=None, content_text=long_text)

    result = normalizer.normalize(item)

    assert result.title == "标题 示例"
    assert result.author_name == "小红"
    assert result.snippet == long_text[:100]
    assert result.content_preview == long_text[:120]


def test_normalize_url_and_filter_images():
    normalizer = ContentNormalizer()
    item = _make_item(
        cover_url=None,
        content_image_urls=[
            "https://img.example.com/avatar_x.png?size=100",
            "https://img.example.com/content/a.jpg?x=1",
            "https://img.example.com/content/a.jpg?x=2",
            " data:image/png;base64,abc ",
            "https://img.example.com/content/b.jpg#fragment",
        ],
    )

    result = normalizer.normalize(item)

    assert result.cover_url == "https://img.example.com/content/a.jpg"
    assert result.content_image_urls == [
        "https://img.example.com/content/a.jpg",
        "https://img.example.com/content/b.jpg",
    ]


def test_quality_and_engagement_score_calculation():
    normalizer = ContentNormalizer()
    item = _make_item(
        title="完整标题",
        snippet="完整摘要",
        content_text="完整正文",
        cover_url="https://img.example.com/cover.jpg",
        content_image_urls=["https://img.example.com/content/a.jpg"],
        publish_time=datetime.now().astimezone(),
        like_count=20,
        comment_count=4,
    )

    result = normalizer.normalize(item)

    assert result.quality_score == 1.0
    assert result.engagement_score == 32.0
    assert result.data_quality["has_publish_time"] is True
    assert result.data_quality["content_image_count"] == 1
