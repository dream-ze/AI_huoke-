"""服务门面类测试 - 验证拆分后的委托调用正常"""

from unittest.mock import MagicMock, patch

import pytest


class TestKnowledgeServiceFacade:
    """知识库服务门面类测试"""

    def test_facade_initialization(self):
        """门面类初始化测试"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert service.db is db
        assert service._crud is not None
        assert service._search is not None

    def test_facade_has_list_knowledge(self):
        """门面类应有list_knowledge方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "list_knowledge")
        assert callable(service.list_knowledge)

    def test_facade_has_create_knowledge(self):
        """门面类应有create_knowledge方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "create_knowledge")
        assert callable(service.create_knowledge)

    def test_facade_has_search_knowledge(self):
        """门面类应有search_knowledge方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "search_knowledge")
        assert callable(service.search_knowledge)

    def test_facade_has_delete_knowledge(self):
        """门面类应有delete_knowledge方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "delete_knowledge")
        assert callable(service.delete_knowledge)

    def test_facade_has_get_knowledge(self):
        """门面类应有get_knowledge方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "get_knowledge")
        assert callable(service.get_knowledge)

    def test_facade_delegates_list_knowledge_to_crud(self):
        """list_knowledge应委托给CRUD服务"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        # Mock CRUD服务的返回值
        service._crud.list_knowledge = MagicMock(return_value={"items": [], "total": 0})

        result = service.list_knowledge(page=1, size=10)

        service._crud.list_knowledge.assert_called_once()
        assert result == {"items": [], "total": 0}

    def test_facade_delegates_search_knowledge_to_search(self):
        """search_knowledge应委托给搜索服务"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        # Mock搜索服务的返回值
        service._search.search_knowledge = MagicMock(return_value=[])

        result = service.search_knowledge("test query")

        service._search.search_knowledge.assert_called_once_with("test query", None, None, 5)

    def test_facade_has_library_stats(self):
        """门面类应有get_library_stats方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "get_library_stats")
        assert callable(service.get_library_stats)

    def test_facade_has_auto_ingest_from_raw(self):
        """门面类应有auto_ingest_from_raw方法"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        assert hasattr(service, "auto_ingest_from_raw")
        assert callable(service.auto_ingest_from_raw)


class TestGenerateServiceFacade:
    """生成服务门面类测试"""

    def test_facade_initialization(self):
        """门面类初始化测试"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert service.db is db
        assert service._core is not None
        assert service._rewrite is not None

    def test_facade_has_generate_multi_version(self):
        """门面类应有generate_multi_version方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "generate_multi_version")
        assert callable(service.generate_multi_version)

    def test_facade_has_generate_final(self):
        """门面类应有generate_final方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "generate_final")
        assert callable(service.generate_final)

    def test_facade_has_generate_full_pipeline(self):
        """门面类应有generate_full_pipeline方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "generate_full_pipeline")
        # 这个方法是async的
        import asyncio

        assert asyncio.iscoroutinefunction(service.generate_full_pipeline)

    def test_facade_has_rewrite_content(self):
        """门面类应有rewrite_content方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "rewrite_content")
        # 这个方法是async的
        import asyncio

        assert asyncio.iscoroutinefunction(service.rewrite_content)

    def test_facade_has_apply_tone_template(self):
        """门面类应有apply_tone_template方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "apply_tone_template")
        import asyncio

        assert asyncio.iscoroutinefunction(service.apply_tone_template)

    def test_facade_has_get_generation_history(self):
        """门面类应有get_generation_history方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "get_generation_history")
        assert callable(service.get_generation_history)

    def test_facade_has_mark_final(self):
        """门面类应有mark_final方法"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        assert hasattr(service, "mark_final")
        assert callable(service.mark_final)

    def test_facade_has_mapping_tables(self):
        """门面类应包含映射表"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        # 检查映射表存在
        assert hasattr(service, "ACCOUNT_TYPE_MAP")
        assert hasattr(service, "AUDIENCE_MAP")
        assert hasattr(service, "TOPIC_MAP")
        assert hasattr(service, "GOAL_MAP")
        assert hasattr(service, "PLATFORM_STYLE_MAP")
        assert hasattr(service, "TONE_MAP")

    def test_facade_delegates_generate_multi_version(self):
        """generate_multi_version应委托给核心服务"""
        from app.services.mvp_generate_service import MvpGenerateService

        db = MagicMock()
        service = MvpGenerateService(db)

        # Mock核心服务的返回值
        service._core.generate_multi_version = MagicMock(return_value={"versions": []})

        result = service.generate_multi_version(source_type="material", source_id=1)

        service._core.generate_multi_version.assert_called_once()
        assert result == {"versions": []}


class TestServiceSubmodules:
    """验证服务子模块可独立导入"""

    def test_import_knowledge_crud_service(self):
        """CRUD服务应可独立导入"""
        from app.services.mvp_knowledge_crud_service import MvpKnowledgeCrudService

        assert MvpKnowledgeCrudService is not None

    def test_import_knowledge_search_service(self):
        """搜索服务应可独立导入"""
        from app.services.mvp_knowledge_search_service import MvpKnowledgeSearchService

        assert MvpKnowledgeSearchService is not None

    def test_import_generate_core_service(self):
        """核心生成服务应可独立导入"""
        from app.services.mvp_generate_core_service import MvpGenerateCoreService

        assert MvpGenerateCoreService is not None

    def test_import_rewrite_service(self):
        """改写服务应可独立导入"""
        from app.services.mvp_rewrite_service import MvpRewriteService

        assert MvpRewriteService is not None


class TestFacadeCompatibility:
    """门面类向后兼容性测试"""

    def test_knowledge_service_import_compatibility(self):
        """旧导入路径应继续工作"""
        # 新路径
        from app.services.mvp_knowledge_service import MvpKnowledgeService as Service1

        # 验证类存在
        assert Service1 is not None

        db = MagicMock()
        service = Service1(db)
        assert service is not None

    def test_generate_service_import_compatibility(self):
        """旧导入路径应继续工作"""
        # 新路径
        from app.services.mvp_generate_service import MvpGenerateService as Service2

        # 验证类存在
        assert Service2 is not None

        db = MagicMock()
        service = Service2(db)
        assert service is not None

    def test_service_methods_preserved(self):
        """服务方法签名应保持一致"""
        from app.services.mvp_knowledge_service import MvpKnowledgeService

        db = MagicMock()
        service = MvpKnowledgeService(db)

        # 验证关键方法存在且可调用
        methods = [
            "list_knowledge",
            "get_knowledge",
            "create_knowledge",
            "update_knowledge",
            "delete_knowledge",
            "search_knowledge",
        ]

        for method_name in methods:
            assert hasattr(service, method_name), f"方法丢失: {method_name}"
            method = getattr(service, method_name)
            assert callable(method), f"方法不可调用: {method_name}"
