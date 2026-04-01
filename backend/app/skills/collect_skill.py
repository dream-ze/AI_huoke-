"""采集技能 - 封装 normalizer 的 build_item 函数"""

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult


@SkillRegistry.register
class CollectSkill(BaseSkill):
    """采集内容标准化技能"""

    name = "collect"
    version = "1.0.0"
    description = "采集内容并进行标准化处理"
    timeout_seconds = 120

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 normalizer.build_item 函数，将原始采集数据标准化

        输入: context.input_data 包含:
            - raw_content: dict, 原始采集数据
            - keyword: str, 采集关键词
            - task_id: str, 任务ID
            - platform: str, 平台标识（默认 xiaohongshu）
        """
        from app.collector.services.normalizer import build_item

        try:
            raw_data = context.input_data.get("raw_content", {})
            keyword = context.input_data.get("keyword", "")
            task_id = context.input_data.get("task_id", "")
            platform = context.input_data.get("platform", "xiaohongshu")

            # 确保平台信息在原始数据中
            if "source_platform" not in raw_data:
                raw_data["source_platform"] = platform

            # 调用标准化函数
            normalized_item = build_item(raw_data, keyword, task_id)

            # 转换为字典格式
            result_data = {
                "normalized_content": {
                    "source_platform": normalized_item.source_platform,
                    "source_type": normalized_item.source_type,
                    "source_id": normalized_item.source_id,
                    "url": normalized_item.url,
                    "keyword": normalized_item.keyword,
                    "title": normalized_item.title,
                    "snippet": normalized_item.snippet,
                    "content": normalized_item.content_text,
                    "author_name": normalized_item.author_name,
                    "author_id": normalized_item.author_id,
                    "like_count": normalized_item.like_count,
                    "comment_count": normalized_item.comment_count,
                    "share_count": normalized_item.share_count,
                    "collect_count": normalized_item.collect_count,
                    "publish_time": normalized_item.publish_time,
                    "tags": normalized_item.tags,
                    "image_urls": normalized_item.image_urls,
                    "image_count": normalized_item.image_count,
                    "content_length": normalized_item.content_length,
                },
                "platform": platform,
                "keyword": keyword,
                "task_id": task_id,
            }

            return SkillResult(success=True, data=result_data)
        except Exception as e:
            return SkillResult(success=False, data={}, error=str(e))
