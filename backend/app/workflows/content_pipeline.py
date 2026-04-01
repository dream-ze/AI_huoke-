"""内容生产流水线"""

from .base import BaseWorkflow


class ContentPipeline(BaseWorkflow):
    """
    内容生产流水线。

    链路：采集 -> 清洗 -> 分类打标 -> 入知识库 -> AI生成 -> 合规检测
    """

    name = "content_pipeline"
    description = "内容生产全链路流水线：从采集到合规检测"
    skill_chain = [
        "collect",
        "clean",
        "classify",
        "knowledge_ingest",
        "knowledge_retrieve",
        "rewrite",
        "compliance_check",
    ]
