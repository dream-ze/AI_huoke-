"""MVP AI生成服务 - 门面类

实际实现已拆分到：
- mvp_generate_core_service.py: 核心生成逻辑
- mvp_rewrite_service.py: 改写和口吻相关

保留此类以兼容现有导入。
"""

from app.schemas.generate_schema import ConstrainedGenerateRequest, ConstrainedGenerateResponse, FullPipelineRequest
from app.services.mvp_generate_core_service import MvpGenerateCoreService
from app.services.mvp_rewrite_service import MvpRewriteService


class MvpGenerateService:
    """门面类 - 委托调用核心生成和改写子服务

    此类保持与原MvpGenerateService完全兼容的接口，
    所有方法调用都委托给对应的子服务实现。
    """

    # 映射表 - 保持与原类一致，便于访问
    ACCOUNT_TYPE_MAP = MvpGenerateCoreService.ACCOUNT_TYPE_MAP
    AUDIENCE_MAP = MvpGenerateCoreService.AUDIENCE_MAP
    TOPIC_MAP = MvpGenerateCoreService.TOPIC_MAP
    GOAL_MAP = MvpGenerateCoreService.GOAL_MAP
    PLATFORM_STYLE_MAP = MvpGenerateCoreService.PLATFORM_STYLE_MAP
    TONE_MAP = MvpGenerateCoreService.TONE_MAP

    def __init__(self, db):
        self.db = db
        self._core = MvpGenerateCoreService(db)
        self._rewrite = MvpRewriteService(db)

    # ========== 核心生成方法（委托给 MvpGenerateCoreService）==========

    def generate_multi_version(
        self,
        source_type,
        source_id=None,
        manual_text=None,
        target_platform="xiaohongshu",
        audience="",
        style="",
        enable_knowledge=False,
        enable_rewrite=False,
        version_count=3,
        extra_requirements="",
    ):
        """多版本生成"""
        return self._core.generate_multi_version(
            source_type=source_type,
            source_id=source_id,
            manual_text=manual_text,
            target_platform=target_platform,
            audience=audience,
            style=style,
            enable_knowledge=enable_knowledge,
            enable_rewrite=enable_rewrite,
            version_count=version_count,
            extra_requirements=extra_requirements,
        )

    def generate_final(self, **kwargs):
        """完整主链路：标签识别→知识检索→多版本生成→合规审核"""
        return self._core.generate_final(**kwargs)

    async def generate_full_pipeline(self, request: FullPipelineRequest) -> dict:
        """完整生成6步链路"""
        return await self._core.generate_full_pipeline(request)

    async def constrained_generate(self, request: ConstrainedGenerateRequest) -> ConstrainedGenerateResponse:
        """强约束生成 - 基于细粒度约束条件生成结构化内容"""
        return await self._core.constrained_generate(request)

    def get_generation_history(self, material_id: int = None, page=1, size=20):
        """获取生成历史"""
        return self._core.get_generation_history(material_id, page, size)

    def mark_final(self, generation_id: int):
        """标记为最终版本"""
        return self._core.mark_final(generation_id)

    # ========== 改写方法（委托给 MvpRewriteService）==========

    async def rewrite_content(
        self, content: str, target_style: str, platform: str = "xiaohongshu", extra_requirements: str = ""
    ) -> dict:
        """内容改写 - 将内容改写为指定风格"""
        return await self._rewrite.rewrite_content(content, target_style, platform, extra_requirements)

    async def apply_tone_template(self, content: str, tone: str, platform: str = "xiaohongshu") -> dict:
        """应用口吻模板 - 调整内容的语气风格"""
        return await self._rewrite.apply_tone_template(content, tone, platform)

    async def generate_compliance_version(self, content: str, risk_points: list = None) -> dict:
        """生成合规版本 - 修复内容中的合规风险"""
        return await self._rewrite.generate_compliance_version(content, risk_points)

    async def convert_style(self, content: str, source_platform: str, target_platform: str) -> dict:
        """平台风格转换 - 将内容从一个平台风格转换为另一个平台风格"""
        return await self._rewrite.convert_style(content, source_platform, target_platform)
