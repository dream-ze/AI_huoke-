# browser_collector

基于 FastAPI + Playwright 的浏览器采集服务。

## 功能
- 小红书关键词搜索
- 抓取前 N 条搜索结果并标准化输出
- 支持详情补采接口 `/api/collect/detail`
- 可选导出 Excel 样例（不影响主 JSON 输出）
- 多平台可扩展架构（工厂模式）

## 安装

```bash
pip install -r requirements.txt
playwright install
```

## 启动

在 `browser_collector/` 根目录下执行：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

启动后访问文档：http://127.0.0.1:8005/docs

## 测试请求

```
POST /api/collect/run
{
  "platform": "xiaohongshu",
  "keyword": "贷款",
  "max_items": 10,
  "export_sample_excel": true,
  "sample_size": 10
}
```

## 接口返回示例

```json
{
  "success": true,
  "platform": "xiaohongshu",
  "keyword": "贷款",
  "request_id": "collect_xiaohongshu_20260326_123725_d0eed3",
  "task_status": "finished",
  "count": 6,
  "cost_ms": 4280,
  "collected_at": "2026-03-26T10:25:30+08:00",
  "has_more": true,
  "stats": {
    "scanned": 20,
    "parsed": 6,
    "deduplicated": 10,
    "failed": 4
  },
  "items": [
    {
      "platform": "xiaohongshu",
      "keyword": "贷款",
      "source_id": "xxxx",
      "source_type": "note",
      "title": "公积金贷款流程",
      "author_name": "小张",
      "snippet": "公积金贷款流程分享...",
      "content_text": "",
      "url": "https://www.xiaohongshu.com/explore/xxxx",
      "cover_url": "https://...",
      "image_urls": [],
      "like_count": 123,
      "comment_count": 8,
      "engagement_score": 139,
      "quality_score": 78,
      "parse_status": "partial",
      "missing_fields": ["publish_time"],
      "publish_time": "",
      "meta": {},
      "raw_data": {},
      "debug_info": {}
    }
  ],
  "message": "采集完成",
  "sample_excel_file": "/www/browser_collector/exports/sample_xiaohongshu_...xlsx"
}
```

## 详情补采请求

```
POST /api/collect/detail
{
  "platform": "xiaohongshu",
  "url": "https://www.xiaohongshu.com/explore/xxxx"
}
```

`export_sample_excel` 为 `false` 时，不会生成 Excel 文件，`sample_excel_file` 返回 `null`。

## AI_huoke 接入方式

```python
import requests

def collect_content(platform: str, keyword: str, max_items: int = 10):
    resp = requests.post(
        "http://127.0.0.1:8005/api/collect/run",
        json={"platform": platform, "keyword": keyword, "max_items": max_items},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()
```
