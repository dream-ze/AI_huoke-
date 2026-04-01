"""清洗技能 - 内容清洗与质量筛选"""

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult


@SkillRegistry.register
class CleanSkill(BaseSkill):
    """内容清洗与质量筛选技能"""

    name = "clean"
    version = "1.0.0"
    description = "对采集内容进行清洗和质量筛选"

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 QualityScreeningService.screen_item 方法

        输入: context.input_data 包含:
            - inbox_item_id: int, 收件箱项目ID（优先使用）
            - normalized_content: dict, 标准化内容（如果没有 inbox_item_id）
        """
        from app.core.database import SessionLocal
        from app.services.quality_screening_service import QualityScreeningService

        db = SessionLocal()
        try:
            service = QualityScreeningService(db)

            # 优先使用 inbox_item_id 进行质量筛选
            inbox_item_id = context.input_data.get("inbox_item_id")

            if inbox_item_id:
                # 调用异步筛选方法
                screening_result = await service.screen_item(inbox_item_id)

                quality_passed = screening_result.get("success", False)
                quality_score = screening_result.get("quality_score", 0)
                risk_score = screening_result.get("risk_score", 0)

                return SkillResult(
                    success=True,
                    data={
                        **context.input_data,
                        "inbox_item_id": inbox_item_id,
                        "quality_passed": quality_passed,
                        "quality_score": quality_score,
                        "risk_score": risk_score,
                        "quality_status": screening_result.get("quality_status", "normal"),
                        "risk_status": screening_result.get("risk_status", "normal"),
                        "screened_at": True,
                    },
                )
            else:
                # 没有具体ID时，返回默认通过状态（后续入库时处理）
                return SkillResult(
                    success=True, data={**context.input_data, "quality_passed": True, "quality_score": 0}
                )
        except Exception as e:
            return SkillResult(success=False, data={}, error=str(e))
        finally:
            db.close()
