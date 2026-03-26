import re
from pathlib import Path

from app.collectors.xiaohongshu_collector import XiaohongshuCollector


class FakeLocator:
    def __init__(self, *, text: str = "", attrs: dict | None = None, exists: bool = True):
        self._text = text
        self._attrs = attrs or {}
        self._exists = exists

    def count(self) -> int:
        return 1 if self._exists else 0

    @property
    def first(self):
        return self

    def inner_text(self, timeout: int = 500) -> str:
        return self._text

    def get_attribute(self, attr: str):
        return self._attrs.get(attr)


class FakeCard:
    def __init__(self, html: str):
        self.html = html

    def locator(self, selector: str) -> FakeLocator:
        href_match = re.search(r'<a[^>]*href="([^"]*/explore/[^"]+)"', self.html, flags=re.S)
        title_match = re.search(r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>', self.html, flags=re.S)
        author_name_match = re.search(
            r'<div[^>]*class="[^"]*author[^"]*"[^>]*>.*?<span[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</span>',
            self.html,
            flags=re.S,
        )
        like_count_match = re.search(
            r'<div[^>]*class="[^"]*like-wrapper[^"]*"[^>]*>.*?<span[^>]*class="[^"]*count[^"]*"[^>]*>(.*?)</span>',
            self.html,
            flags=re.S,
        )
        desc_match = re.search(r'<div[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</div>', self.html, flags=re.S)
        img_match = re.search(r'<img[^>]*src="([^"]+)"', self.html, flags=re.S)

        def _clean(raw: str | None) -> str:
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw or "")).strip()

        if selector == 'a[href*="/explore/"]':
            return FakeLocator(attrs={"href": href_match.group(1)} if href_match else {}, exists=bool(href_match))
        if selector == ".title":
            return FakeLocator(text=_clean(title_match.group(1)) if title_match else "", exists=bool(title_match))
        if selector == ".author .name":
            return FakeLocator(
                text=_clean(author_name_match.group(1)) if author_name_match else "", exists=bool(author_name_match)
            )
        if selector == ".name":
            return FakeLocator(text=_clean(author_name_match.group(1)) if author_name_match else "", exists=bool(author_name_match))
        if selector == ".author":
            return FakeLocator(text=_clean(author_name_match.group(1)) if author_name_match else "", exists=bool(author_name_match))
        if selector == ".like-wrapper .count":
            return FakeLocator(text=_clean(like_count_match.group(1)) if like_count_match else "", exists=bool(like_count_match))
        if selector == ".count":
            return FakeLocator(text=_clean(like_count_match.group(1)) if like_count_match else "", exists=bool(like_count_match))
        if selector == ".like":
            return FakeLocator(text=_clean(like_count_match.group(1)) if like_count_match else "", exists=bool(like_count_match))
        if selector == ".desc":
            return FakeLocator(text=_clean(desc_match.group(1)) if desc_match else "", exists=bool(desc_match))
        if selector == ".note-text":
            return FakeLocator(text=_clean(desc_match.group(1)) if desc_match else "", exists=bool(desc_match))
        if selector == "img":
            return FakeLocator(attrs={"src": img_match.group(1)} if img_match else {}, exists=bool(img_match))
        return FakeLocator(exists=False)


def test_parse_list_card_maps_fields_from_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "xiaohongshu_list_card.html"
    card = FakeCard(fixture_path.read_text(encoding="utf-8"))
    collector = XiaohongshuCollector()

    item = collector._parse_list_card(card, keyword="贷款")

    assert item is not None
    assert item.platform == "xiaohongshu"
    assert item.keyword == "贷款"
    assert item.source_id == "67f9a8b00000000012012345"
    assert item.url == "https://www.xiaohongshu.com/explore/67f9a8b00000000012012345"
    assert item.title == "公积金 贷款 经验 分享"
    assert item.author_name == "小张同学"
    assert item.snippet == "真实办理流程，材料清单和避坑建议。"
    assert item.cover_url == "https://img.example.com/note-cover.jpg"
    assert item.like_count == 12000
    assert item.parse_status == "list_only"
    assert item.field_source["title"] == "list_dom"


def test_parse_list_card_returns_none_when_title_and_snippet_missing():
    html = """
    <section>
      <a href=\"/explore/abc\"><img src=\"https://img.example.com/a.jpg\"/></a>
      <div class=\"author\"><span class=\"name\">tester</span></div>
      <div class=\"like-wrapper\"><span class=\"count\">99</span></div>
    </section>
    """
    card = FakeCard(html)
    collector = XiaohongshuCollector()

    item = collector._parse_list_card(card, keyword="贷款")

    assert item is None
