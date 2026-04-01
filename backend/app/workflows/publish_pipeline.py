"""发布分发流水线"""

from .base import BaseWorkflow


class PublishPipeline(BaseWorkflow):
    """
    发布分发流水线。

    链路：知识检索 -> AI改写 -> 合规检测
    （发布调度由 publish_service 独立管理）
    """

    name = "publish_pipeline"
    description = "发布前内容准备流水线：检索、改写、合规"
    skill_chain = [
        "knowledge_retrieve",
        "rewrite",
        "compliance_check",
    ]
