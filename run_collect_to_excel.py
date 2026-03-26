import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openpyxl import Workbook


def post_collect(api_url: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url=api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8")
        return json.loads(text)


def export_items_to_excel(items: list[dict], output_dir: Path, keyword: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(ch if ch.isalnum() else "_" for ch in keyword).strip("_") or "keyword"
    output_path = output_dir / f"collect_{safe_keyword}_{stamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "collect_items"

    headers = [
        "platform",
        "keyword",
        "source_id",
        "url",
        "title",
        "author_name",
        "snippet",
        "content_text",
        "cover_url",
        "image_urls",
        "like_count",
        "comment_count",
        "publish_time",
        "collected_at",
        "parse_status",
        "risk_status",
        "engagement_score",
        "quality_score",
    ]
    ws.append(headers)

    for item in items:
        ws.append(
            [
                item.get("platform"),
                item.get("keyword"),
                item.get("source_id"),
                item.get("url"),
                item.get("title"),
                item.get("author_name"),
                item.get("snippet"),
                item.get("content_text"),
                item.get("cover_url"),
                "\n".join(item.get("image_urls") or []),
                item.get("like_count"),
                item.get("comment_count"),
                item.get("publish_time"),
                item.get("collected_at"),
                item.get("parse_status"),
                item.get("risk_status"),
                item.get("engagement_score"),
                item.get("quality_score"),
            ]
        )

    wb.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="调用 /api/collect/run 并导出 Excel")
    parser.add_argument("--host", default="127.0.0.1", help="API 主机")
    parser.add_argument("--port", type=int, default=8005, help="API 端口")
    parser.add_argument("--keyword", required=True, help="搜索关键词")
    parser.add_argument("--max-items", type=int, default=10, help="最大条数")
    parser.add_argument("--need-detail", action="store_true", help="是否补采详情")
    parser.add_argument("--need-comments", action="store_true", help="是否补采评论")
    parser.add_argument("--timeout", type=int, default=180, help="请求超时（秒）")
    parser.add_argument("--output-dir", default="exports", help="Excel 输出目录")
    args = parser.parse_args()

    api_url = f"http://{args.host}:{args.port}/api/collect/run"
    payload = {
        "platform": "xiaohongshu",
        "keyword": args.keyword,
        "max_items": args.max_items,
        "need_detail": args.need_detail,
        "need_comments": args.need_comments,
        "dedup": True,
        "timeout_sec": min(max(args.timeout, 30), 300),
    }

    try:
        data = post_collect(api_url=api_url, payload=payload, timeout=args.timeout)
    except HTTPError as ex:
        print(f"HTTP 错误: {ex.code} {ex.reason}")
        return
    except URLError as ex:
        print(f"连接失败: {ex.reason}")
        return
    except Exception as ex:
        print(f"请求失败: {ex}")
        return

    items = data.get("items") or []
    if not items:
        print("接口调用成功，但 items 为空，未生成 Excel。")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    output_path = export_items_to_excel(
        items=items,
        output_dir=Path(args.output_dir),
        keyword=args.keyword,
    )
    print(f"Excel 已生成: {output_path.resolve()}")
    print(f"返回条数: {len(items)}")


if __name__ == "__main__":
    main()