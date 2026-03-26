# browser_collector

基于 FastAPI + Playwright 的浏览器采集服务（v2，非兼容旧版）。

## 功能
- 小红书关键词搜索
- 列表发现 + 详情补采
- 标准化输出（数值型点赞/评论、时间类型）
- 失败截图与 HTML 落盘（artifacts）

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
  "need_detail": true,
  "need_comments": false,
  "dedup": true,
  "timeout_sec": 120
}
```

## 运行测试

在 `browser_collector/` 根目录执行：

```bash
pytest -q tests
```

当前已包含三类测试：
- normalizer 纯函数单元测试
- parser/collector 字段映射测试（固定 HTML 夹具）
- API 层契约测试（`/api/collect/run`、`/api/collect/detail`）

## 接口返回示例

```json
{
  "success": true,
  "platform": "xiaohongshu",
  "keyword": "贷款",
  "task_id": "collect_20260326_123725_a1b2c3",
  "request_id": "collect_xiaohongshu_20260326_123725_d0eed3",
  "count": 6,
  "cost_ms": 4280,
  "collected_at": "2026-03-26T10:25:30+08:00",
  "stats": {
    "discovered": 20,
    "list_success": 6,
    "detail_attempted": 6,
    "detail_success": 5,
    "detail_failed": 1,
    "dropped": 0
  },
  "items": [
    {
      "source_platform": "xiaohongshu",
      "keyword": "贷款",
      "task_id": "collect_20260326_123725_a1b2c3",
      "source_id": "xxxx",
      "title": "公积金贷款流程",
      "author_name": "小张",
      "snippet": "公积金贷款流程分享...",
      "content_text": "完整正文...",
      "url": "https://www.xiaohongshu.com/explore/xxxx",
      "cover_url": "https://...",
      "image_urls": [],
      "image_count": 0,
      "like_count": 123,
      "comment_count": 8,
      "engagement_score": 147,
      "quality_score": 0.73,
      "lead_score": 0.4,
      "parse_status": "detail_success",
      "parse_stage": "detail",
      "detail_attempted": true,
      "detail_error": "",
      "field_completeness": 0.85,
      "risk_level": "low",
      "publish_time": "2026-03-25T11:20:00+08:00",
      "raw_data": {}
    }
  ],
  "message": "采集完成"
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

## 一键导出 Excel

在工作区根目录执行：

python browser_collector/run_collect_to_excel.py --keyword 贷款 --max-items 10 --need-detail --need-comments --timeout 180 --output-dir exports

执行成功后会在 `exports/` 目录生成 `.xlsx` 文件，包含：

- `items_view`: 业务可读字段
- `items_raw`: 原始全字段
- `summary`: 本次任务统计

## 平台能力接口

```
GET /api/platforms
```

## 健康检查

```
GET /health
```

返回中包含 `browser_ready`、`login_state_ready`、`storage_state_exists`。

## AI_huoke 接入方式

```python
import requests

def collect_content(keyword: str, max_items: int = 10):
    resp = requests.post(
        "http://127.0.0.1:8005/api/collect/run",
    json={
      "platform": "xiaohongshu",
      "keyword": keyword,
      "max_items": max_items,
      "need_detail": True,
      "need_comments": True,
      "dedup": True,
      "timeout_sec": 180,
    },
    timeout=240,
    )
    resp.raise_for_status()
  data = resp.json()
  print(data["count"])
  print(data["stats"])
  return data
```
