"""模型拆分后的导入兼容性测试"""

import pytest


class TestModelImports:
    """验证模型拆分后所有导入路径正常"""

    def test_import_from_models_package(self):
        """新的包导入路径应工作"""
        from app.models import ContentAsset, Customer, Lead, User

        assert User is not None
        assert ContentAsset is not None
        assert Lead is not None
        assert Customer is not None

    def test_import_enums(self):
        """枚举类型导入"""
        from app.models import ContentType, PlatformType, RiskLevel

        assert PlatformType is not None
        assert ContentType is not None
        assert RiskLevel is not None

    def test_import_base(self):
        """Base导入"""
        from app.models import Base

        assert Base is not None

    def test_import_mvp_models(self):
        """MVP模型导入"""
        from app.models import MvpInboxItem, MvpKnowledgeItem, MvpMaterialItem

        assert MvpInboxItem is not None
        assert MvpMaterialItem is not None
        assert MvpKnowledgeItem is not None

    def test_import_user_from_module(self):
        """从user模块导入User"""
        from app.models.user import User

        assert User is not None

    def test_import_content_from_module(self):
        """从content模块导入ContentAsset"""
        from app.models.content import ContentAsset

        assert ContentAsset is not None

    def test_import_crm_from_module(self):
        """从crm模块导入Lead和Customer"""
        from app.models.crm import Customer, Lead, LeadProfile

        assert Lead is not None
        assert Customer is not None
        assert LeadProfile is not None

    def test_import_knowledge_from_module(self):
        """从knowledge模块导入知识库模型"""
        from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, Rule

        assert KnowledgeDocument is not None
        assert KnowledgeChunk is not None
        assert Rule is not None

    def test_import_generation_from_module(self):
        """从generation模块导入"""
        from app.models.generation import GenerationTask

        assert GenerationTask is not None

    def test_import_publish_from_module(self):
        """从publish模块导入"""
        from app.models.publish import PublishRecord, PublishTask

        assert PublishRecord is not None
        assert PublishTask is not None


class TestModelBaseConsistency:
    """验证所有模型共享同一个Base"""

    def test_all_models_share_same_base(self):
        """所有模型应共享同一个Base"""
        from app.models.base import Base
        from app.models.content import ContentAsset
        from app.models.crm import Lead
        from app.models.user import User

        # 验证它们注册到同一个metadata
        assert User.__table__.metadata is Base.metadata
        assert ContentAsset.__table__.metadata is Base.metadata
        assert Lead.__table__.metadata is Base.metadata

    def test_base_has_timestamp_mixin(self):
        """Base模块应导出TimestampMixin"""
        from app.models.base import TimestampMixin

        assert TimestampMixin is not None


class TestModelExportList:
    """验证__all__导出列表完整性"""

    def test_all_exports_importable(self):
        """验证__all__中所有导出可导入"""
        from app import models as models_pkg
        from app.models import __all__

        for name in __all__:
            assert hasattr(models_pkg, name), f"模型未导出: {name}"
            obj = getattr(models_pkg, name)
            assert obj is not None, f"模型导出为None: {name}"

    def test_core_models_in_all(self):
        """核心模型应在__all__中"""
        from app.models import __all__

        expected_models = [
            "Base",
            "User",
            "ContentAsset",
            "Lead",
            "Customer",
            "KnowledgeDocument",
            "GenerationTask",
            "MvpInboxItem",
            "MvpMaterialItem",
            "MvpKnowledgeItem",
        ]

        for model_name in expected_models:
            assert model_name in __all__, f"核心模型未在__all__中: {model_name}"


class TestEnumValues:
    """枚举值测试"""

    def test_platform_type_values(self):
        """平台类型枚举值"""
        from app.models.enums import PlatformType

        # 检查常见平台
        assert hasattr(PlatformType, "XIAOHONGSHU") or hasattr(PlatformType, "xiaohongshu")

    def test_content_type_values(self):
        """内容类型枚举值"""
        from app.models.enums import ContentType

        assert ContentType is not None

    def test_risk_level_values(self):
        """风险等级枚举值"""
        from app.models.enums import RiskLevel

        assert RiskLevel is not None


class TestModelTableNames:
    """模型表名测试"""

    def test_user_table_name(self):
        """User表名验证"""
        from app.models.user import User

        assert User.__tablename__ == "users"

    def test_content_asset_table_name(self):
        """ContentAsset表名验证"""
        from app.models.content import ContentAsset

        assert ContentAsset.__tablename__ == "content_assets"

    def test_lead_table_name(self):
        """Lead表名验证"""
        from app.models.crm import Lead

        assert Lead.__tablename__ == "leads"

    def test_customer_table_name(self):
        """Customer表名验证"""
        from app.models.crm import Customer

        assert Customer.__tablename__ == "customers"
