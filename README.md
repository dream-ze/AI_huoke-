# browser_collector

基于 FastAPI + Playwright 的浏览器采集服务。

## 功能
- 小红书关键词搜索
- 抓取前 N 条搜索结果
- 返回统一 JSON 数据
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
  "max_items": 10
}
```

## 接口返回示例

```json
{
  "success": true,
  "platform": "xiaohongshu",
  "keyword": "贷款",
  "count": 6,
  "items": [
    {
      "platform": "xiaohongshu",
      "keyword": "贷款",
      "title": "公积金贷款流程",
      "author": "小张",
      "content": "公积金贷款流程 ...",
      "url": "https://www.xiaohongshu.com/explore/xxxx",
      "cover_url": "",
      "like_count": "123",
      "comment_count": "",
      "publish_time": "",
      "source_id": "xxxx",
      "raw_data": {}
    }
  ],
  "message": "采集完成"
}
```

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
