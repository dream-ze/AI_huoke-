# 火山方舟 Responses API 调用指南

本指南提供三种接入方式：
- Rest API（curl）
- OpenAI SDK 兼容方式
- 火山引擎 SDK 方式

> 安全提醒：不要在代码仓库或聊天记录里暴露明文 API Key。请使用环境变量，并定期轮换密钥。

## 1. 前置准备

### 1.1 设置环境变量

Windows PowerShell:

```powershell
$env:ARK_API_KEY="<YOUR_ARK_API_KEY>"
$env:ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
$env:ARK_MODEL="doubao-seed-2-0-mini-260215"
```

Linux/macOS:

```bash
export ARK_API_KEY="<YOUR_ARK_API_KEY>"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export ARK_MODEL="doubao-seed-2-0-mini-260215"
```

## 2. Rest API 接入示例

```bash
curl https://ark.cn-beijing.volces.com/api/v3/responses \
  -H "Authorization: Bearer <YOUR_ARK_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seed-2-0-mini-260215",
    "input": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_image",
            "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"
          },
          {
            "type": "input_text",
            "text": "你看见了什么？"
          }
        ]
      }
    ]
  }'
```

## 3. OpenAI SDK 调用示例

> 说明：Ark 提供 OpenAI 兼容接口，设置 base_url 即可复用 OpenAI SDK。

先安装依赖：

```bash
pip install openai
```

Python 示例：

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["ARK_API_KEY"],
    base_url=os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
)

resp = client.responses.create(
    model=os.environ.get("ARK_MODEL", "doubao-seed-2-0-mini-260215"),
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png",
                },
                {
                    "type": "input_text",
                    "text": "你看见了什么？",
                },
            ],
        }
    ],
)

print(getattr(resp, "output_text", None) or resp)
```

## 4. 火山引擎 SDK 调用示例

先安装依赖：

```bash
pip install volcenginesdkarkruntime
```

Python 示例：

```python
import os
from volcenginesdkarkruntime import Ark

client = Ark(
    api_key=os.environ["ARK_API_KEY"],
    base_url=os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
)

resp = client.responses.create(
    model=os.environ.get("ARK_MODEL", "doubao-seed-2-0-mini-260215"),
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png",
                },
                {
                    "type": "input_text",
                    "text": "你看见了什么？",
                },
            ],
        }
    ],
)

print(resp.output_text if hasattr(resp, "output_text") else resp)
```

## 5. 在本项目中的调用位置

- 后端 Vision API：`POST /api/ai/ark/vision`
- 网页端入口：AI 页面中的“火山引擎图片理解（Ark Responses）”

请求体：

```json
{
  "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png",
  "text": "你看见了什么？",
  "model": "doubao-seed-2-0-mini-260215"
}
```

## 6. 日志与限流说明（已接入）

- 日志：记录请求开始/成功/失败、耗时、token 用量（如果响应返回 usage）
- 限流：按用户 ID 对 `/api/ai/ark/vision` 做每分钟调用次数限制
- 配置项：
  - `ARK_TIMEOUT_SECONDS`
  - `ARK_VISION_RATE_LIMIT_PER_MINUTE`
  - `ARK_VISION_RATE_LIMIT_WINDOW_SECONDS`
  - `USE_REDIS_RATE_LIMIT`
  - `REDIS_URL`
  - `RATE_LIMIT_KEY_PREFIX`

> 当前默认为 Redis 分布式限流；当 Redis 不可用时会自动降级到进程内限流，保证服务可用性。

## 7. 调用统计看板接口

- 接口：`GET /api/dashboard/ai-call-stats?days=7&scope=me`
- 参数：
  - `days`：统计天数，1-90
  - `scope`：`me`（当前用户）或 `all`（全部用户）

返回示例：

```json
{
  "period_days": 7,
  "scope": "all",
  "data": [
    {
      "date": "2026-03-21",
      "user_id": 1,
      "username": "testuser",
      "call_count": 42,
      "failed_count": 3,
      "failure_rate": 7.14,
      "input_tokens": 15600,
      "output_tokens": 8400,
      "total_tokens": 24000,
      "avg_latency_ms": 853.21
    }
  ]
}
```
