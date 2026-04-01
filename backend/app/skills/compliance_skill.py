"""合规检查技能 - 封装 mvp_compliance_service"""

import logging

from app.skills import SkillRegistry
from app.skills.base_skill import BaseSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


@SkillRegistry.register
class ComplianceSkill(BaseSkill):
    """合规检查技能"""

    name = "compliance_check"
    version = "1.0.0"
    description = "对内容进行合规性检查和风险评估"
    timeout_seconds = 60

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        封装 MvpComplianceService.check_async 方法

        输入: context.input_data 包含:
            - rewrite_result: dict, 改写结果（优先使用其中的内容）
            - normalized_content: dict, 标准化内容
            - enable_llm: bool, 是否启用LLM语义检测（默认True）
        """
        from app.core.database import SessionLocal
        from app.services.mvp_compliance_service import MvpComplianceService

        db = SessionLocal()
        try:
            service = MvpComplianceService(db)

            # 获取待检查内容
            rewrite_result = context.input_data.get("rewrite_result", {})
            if isinstance(rewrite_result, dict):
                # 从改写结果中提取文本
                if "versions" in rewrite_result:
                    # 多版本时，检查所有版本的合并文本
                    texts = [v.get("text", "") for v in rewrite_result.get("versions", [])]
                    content = "\n\n".join(texts)
                else:
                    content = rewrite_result.get("content", rewrite_result.get("text", ""))
            else:
                content = str(rewrite_result)

            # 如果没有改写结果，使用原始内容
            if not content:
                normalized = context.input_data.get("normalized_content", {})
                title = normalized.get("title", "")
                body = normalized.get("content", normalized.get("snippet", ""))
                content = f"{title}\n\n{body}"

            # 是否启用LLM检测
            enable_llm = context.input_data.get("enable_llm", True)

            # 调用异步合规检查方法
            compliance_result = await service.check_async(text=content, enable_llm=enable_llm)

            # 判断是否通过
            passed = compliance_result.get("is_compliant", True)
            risk_level = compliance_result.get("risk_level", "low")

            return SkillResult(
                success=True,
                data={
                    **context.input_data,
                    "compliance_result": compliance_result,
                    "compliance_passed": passed,
                    "risk_level": risk_level,
                    "risk_score": compliance_result.get("risk_score", 0),
                },
                should_continue=passed,  # 合规不通过则中断流水线
            )
        except Exception as e:
            logger.error(f"合规检查失败: {e}")
            return SkillResult(success=False, data={}, error=str(e))
        finally:
            db.close()
