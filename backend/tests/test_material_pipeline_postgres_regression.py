import asyncio
import os

import pytest
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.domains.acquisition import MaterialPipelineOrchestrator
from app.models import (
    Customer,
    GenerationTask,
    KnowledgeDocument,
    Lead,
    MaterialItem,
    NormalizedContent,
    PromptTemplate,
    Rule,
    SourceContent,
)
from app.services.ai_service import AIService
from app.services.user_service import UserService
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = [pytest.mark.regression, pytest.mark.postgres_regression]


POSTGRES_TEST_URL = os.getenv("TEST_POSTGRES_DATABASE_URL") or os.getenv("DATABASE_URL", "")


requires_postgres = pytest.mark.skipif(
    not (os.getenv("RUN_POSTGRES_REGRESSION") == "1" and POSTGRES_TEST_URL.startswith("postgresql")),
    reason="Set RUN_POSTGRES_REGRESSION=1 and TEST_POSTGRES_DATABASE_URL to run Postgres regression tests",
)


def _make_pg_session():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, SessionLocal()


def _make_pg_api_client():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return engine, SessionLocal, client


def _make_auth_headers(db, username: str, email: str):
    user = UserService.create_user(
        db,
        username=username,
        email=email,
        password="StrongPass_2026!",
    )
    token = create_access_token({"sub": str(user.id)})
    return user, {"Authorization": f"Bearer {token}"}


@requires_postgres
def test_material_pipeline_ingest_retrieve_generate_on_postgres(monkeypatch):
    engine, db = _make_pg_session()

    async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
        _ = system_prompt
        _ = use_cloud
        _ = user_id
        _ = scene
        if "只返回 JSON" in prompt:
            return '{"tags":["征信"],"category":"征信修复","heat_score":68,"is_viral":false,"viral_reasons":[],"key_selling_points":["先看查询次数"],"rewrite_hints":"先清洗再改写"}'
        return "这是 PostgreSQL 主链路回归生成的文案结果。"

    monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

    try:
        user = UserService.create_user(
            db,
            username="pg_pipeline_user",
            email="pg_pipeline_user@example.com",
            password="StrongPass_2026!",
        )
        orchestrator = MaterialPipelineOrchestrator(db=db, owner_id=user.id, ai_service=AIService(db=db))

        seed = orchestrator.ingest_manual_content(
            platform="xiaohongshu",
            title="征信修复经验参考",
            content_text="征信花了怎么办？先看查询次数，再看当前负债情况。这是一条参考素材。",
            tags=["征信", "参考"],
        )
        seed_material = orchestrator.ensure_material_knowledge(seed["material_id"])
        seed_doc = seed_material.knowledge_documents[0]

        result = asyncio.run(
            orchestrator.ingest_and_generate(
                source_platform="xiaohongshu",
                title="  征信处理测试标题  ",
                content_text=(
                    "作者：张三\n"
                    "发布时间：今天\n"
                    "征信花了还能贷款吗？\n"
                    "展开\n"
                    "征信花了还能贷款吗？\n"
                    "先看查询次数，再看负债情况。"
                ),
                target_platform="xiaohongshu",
                tags=["征信", "清洗"],
            )
        )

        assert result["material_id"] is not None
        assert result["knowledge_document_id"] is not None
        assert result["generation_task_id"] is not None
        assert result["cleaned_title"] == "征信处理测试标题"
        assert "作者：" not in result["cleaned_content_text"]
        assert "发布时间" not in result["cleaned_content_text"]
        assert "展开" not in result["cleaned_content_text"]
        assert "先看查询次数，再看负债情况。" in result["cleaned_content_text"]
        assert result["output_text"]
        assert result["selected_variant"] is not None

        generation = db.query(GenerationTask).filter(GenerationTask.id == result["generation_task_id"]).first()
        assert generation is not None
        assert generation.prompt_snapshot is not None
        assert "【知识参考】" in generation.prompt_snapshot
        assert "【规则约束】" in generation.prompt_snapshot
        assert seed_doc.id in (generation.reference_document_ids or [])

        knowledge_document = (
            db.query(KnowledgeDocument).filter(KnowledgeDocument.id == result["knowledge_document_id"]).first()
        )
        assert knowledge_document is not None
        assert knowledge_document.title == "征信处理测试标题"
        assert knowledge_document.content_text == result["cleaned_content_text"]

        assert db.query(Rule).count() >= 2
        assert db.query(PromptTemplate).count() >= 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_materials_ingest_and_rewrite_api_on_postgres(monkeypatch):
    engine, SessionLocal, client = _make_pg_api_client()

    async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
        _ = system_prompt
        _ = use_cloud
        _ = user_id
        _ = scene
        if "只返回 JSON" in prompt:
            return '{"tags":["征信"],"category":"征信修复","heat_score":72,"is_viral":false,"viral_reasons":[],"key_selling_points":["看查询次数"],"rewrite_hints":"先清洗"}'
        return "这是 API 级 PostgreSQL 回归生成结果。"

    monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

    try:
        with SessionLocal() as db:
            user, auth_headers = _make_auth_headers(db, "pg_api_user", "pg_api_user@example.com")
            orchestrator = MaterialPipelineOrchestrator(db=db, owner_id=user.id, ai_service=AIService(db=db))
            seed = orchestrator.ingest_manual_content(
                platform="xiaohongshu",
                title="征信经验种子素材",
                content_text="征信花了怎么办？先看查询次数，再评估当前负债。",
                tags=["征信", "种子"],
            )
            seed_doc = orchestrator.ensure_material_knowledge(seed["material_id"]).knowledge_documents[0]

        response = client.post(
            "/api/v2/materials/ingest-and-rewrite",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "  API 测试标题  ",
                "content_text": (
                    "作者：张三\n"
                    "发布时间：今天\n"
                    "征信花了还能贷吗？\n"
                    "展开\n"
                    "征信花了还能贷吗？\n"
                    "先看查询次数，再评估负债。"
                ),
                "tags": ["征信"],
                "target_platform": "xiaohongshu",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["material_id"] is not None
        assert payload["knowledge_document_id"] is not None
        assert payload["generation_task_id"] is not None
        assert payload["cleaned_title"] == "API 测试标题"
        assert payload["cleaned_content_text"] == "征信花了还能贷吗？\n先看查询次数，再评估负债。"
        assert payload["output_text"]
        assert payload["selected_variant"] is not None
        assert any(ref["document_id"] == seed_doc.id for ref in payload["references"])
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_generation_adopt_backfills_material_content_on_postgres(monkeypatch):
    engine, SessionLocal, client = _make_pg_api_client()

    async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
        _ = prompt
        _ = system_prompt
        _ = use_cloud
        _ = user_id
        _ = scene
        return "这是用于采纳回写的模型输出。"

    monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

    try:
        with SessionLocal() as db:
            _user, auth_headers = _make_auth_headers(db, "pg_adopt_user", "pg_adopt_user@example.com")

        ingest_resp = client.post(
            "/api/v2/materials/ingest-and-rewrite",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "采纳测试标题",
                "content_text": "这是需要改写并采纳的一段原始正文。",
                "target_platform": "xiaohongshu",
            },
        )
        assert ingest_resp.status_code == 200
        ingest_payload = ingest_resp.json()

        adopt_resp = client.post(
            f"/api/v2/materials/{ingest_payload['material_id']}/generation/{ingest_payload['generation_task_id']}/adopt",
            headers=auth_headers,
            json={"adopt": True, "reason": "采用该版本"},
        )
        assert adopt_resp.status_code == 200
        assert adopt_resp.json()["adoption_status"] == "adopted"

        with SessionLocal() as db:
            material = db.query(MaterialItem).filter(MaterialItem.id == ingest_payload["material_id"]).first()
            generation = (
                db.query(GenerationTask).filter(GenerationTask.id == ingest_payload["generation_task_id"]).first()
            )
            assert material is not None
            assert generation is not None
            assert material.content_text == generation.output_text
            assert material.content_preview == (generation.output_text or "")[:100]
            assert material.review_note == "采用该版本"
            assert material.status == "pending"
            assert material.normalized_content is not None
            assert material.normalized_content.content_text == generation.output_text
            assert generation.adoption_status == "adopted"
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_duplicate_material_ingest_deduplicates_storage_on_postgres(monkeypatch):
    engine, SessionLocal, client = _make_pg_api_client()

    async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
        _ = prompt
        _ = system_prompt
        _ = use_cloud
        _ = user_id
        _ = scene
        return "这是重复素材场景下的生成结果。"

    monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

    payload = {
        "platform": "xiaohongshu",
        "title": "重复素材标题",
        "content_text": "这是同一条重复素材正文，用于验证去重。",
        "source_url": "https://example.com/repeated-material",
        "target_platform": "xiaohongshu",
    }

    try:
        with SessionLocal() as db:
            _user, auth_headers = _make_auth_headers(db, "pg_dedupe_user", "pg_dedupe_user@example.com")

        first = client.post("/api/v2/materials/ingest-and-rewrite", headers=auth_headers, json=payload)
        second = client.post("/api/v2/materials/ingest-and-rewrite", headers=auth_headers, json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        first_payload = first.json()
        second_payload = second.json()
        assert second_payload["material_id"] == first_payload["material_id"]

        with SessionLocal() as db:
            assert db.query(MaterialItem).count() == 1
            assert db.query(SourceContent).count() == 1
            assert db.query(NormalizedContent).count() == 1
            assert db.query(KnowledgeDocument).count() == 1
            assert db.query(GenerationTask).count() == 2
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_material_edit_then_reindex_refreshes_knowledge_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            user, auth_headers = _make_auth_headers(db, "pg_edit_user", "pg_edit_user@example.com")
            orchestrator = MaterialPipelineOrchestrator(db=db, owner_id=user.id, ai_service=AIService(db=db))
            seed = orchestrator.ingest_manual_content(
                platform="xiaohongshu",
                title="编辑前标题",
                content_text="编辑前正文内容。",
                tags=["编辑", "重建"],
            )
            material = orchestrator.ensure_material_knowledge(seed["material_id"])
            original_doc_id = material.knowledge_documents[0].id

        patch_resp = client.patch(
            f"/api/v2/materials/{seed['material_id']}",
            headers=auth_headers,
            json={
                "title": "编辑后标题",
                "content_text": "编辑后正文第一段。\n编辑后正文第二段。",
            },
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["title"] == "编辑后标题"

        analyze_resp = client.post(
            f"/api/v2/materials/{seed['material_id']}/analyze",
            headers=auth_headers,
        )
        assert analyze_resp.status_code == 200
        payload = analyze_resp.json()
        assert payload["knowledge_document_id"] != original_doc_id
        assert payload["chunk_count"] >= 1

        detail_resp = client.get(
            f"/api/v2/materials/{seed['material_id']}",
            headers=auth_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["title"] == "编辑后标题"
        assert detail["content_text"] == "编辑后正文第一段。\n编辑后正文第二段。"
        assert detail["knowledge_documents"][0]["document_id"] == payload["knowledge_document_id"]
        assert detail["knowledge_documents"][0]["title"] == "编辑后标题"
        assert detail["knowledge_documents"][0]["content_text"] == "编辑后正文第一段。\n编辑后正文第二段。"
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_custom_rules_and_prompt_templates_affect_generation_on_postgres(monkeypatch):
    engine, SessionLocal, client = _make_pg_api_client()
    captured: dict[str, str] = {}

    async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
        _ = use_cloud
        _ = user_id
        _ = scene
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        return "这是规则和提示词定制后的生成结果。"

    monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

    try:
        with SessionLocal() as db:
            user, auth_headers = _make_auth_headers(db, "pg_rule_user", "pg_rule_user@example.com")
            db.add(
                Rule(
                    owner_id=user.id,
                    rule_type="structure_rule",
                    platform="xiaohongshu",
                    account_type="科普号",
                    target_audience="泛人群",
                    name="强调风险提示",
                    content="输出时必须包含风险提醒和先判断再行动的表达。",
                    priority=999,
                )
            )
            db.add(
                PromptTemplate(
                    owner_id=user.id,
                    task_type="rewrite",
                    platform="xiaohongshu",
                    account_type="科普号",
                    target_audience="泛人群",
                    version="pg-test",
                    system_prompt="你是自定义系统提示，必须严格按规则输出。",
                    user_prompt_template="请使用自定义提示模板，为{platform}平台输出一篇{task_type}文案，账号类型为{account_type}，目标人群为{target_audience}。",
                )
            )
            db.commit()

        response = client.post(
            "/api/v2/materials/ingest-and-rewrite",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "规则模板测试标题",
                "content_text": "这是一段用于规则和提示词模板覆盖验证的正文。",
                "target_platform": "xiaohongshu",
                "account_type": "科普号",
                "target_audience": "泛人群",
            },
        )

        assert response.status_code == 200
        assert response.json()["output_text"]
        assert captured["system_prompt"] == "你是自定义系统提示，必须严格按规则输出。"
        assert "请使用自定义提示模板，为xiaohongshu平台输出一篇rewrite文案" in captured["prompt"]
        assert "强调风险提示" in captured["prompt"]
        assert "输出时必须包含风险提醒和先判断再行动的表达。" in captured["prompt"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_retrieval_is_isolated_per_user_on_postgres(monkeypatch):
    engine, SessionLocal, client = _make_pg_api_client()
    captured_prompts: list[str] = []

    async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
        _ = system_prompt
        _ = use_cloud
        _ = user_id
        _ = scene
        captured_prompts.append(prompt)
        return "这是多用户隔离场景下的生成结果。"

    monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

    try:
        with SessionLocal() as db:
            user_a, auth_headers_a = _make_auth_headers(db, "pg_user_a", "pg_user_a@example.com")
            user_b, _auth_headers_b = _make_auth_headers(db, "pg_user_b", "pg_user_b@example.com")

            orchestrator_a = MaterialPipelineOrchestrator(db=db, owner_id=user_a.id, ai_service=AIService(db=db))
            orchestrator_b = MaterialPipelineOrchestrator(db=db, owner_id=user_b.id, ai_service=AIService(db=db))

            material_a = orchestrator_a.ingest_manual_content(
                platform="xiaohongshu",
                title="用户A素材",
                content_text="用户A专属标记：征信修复先看查询次数，再评估负债。",
                tags=["A"],
            )
            material_b = orchestrator_b.ingest_manual_content(
                platform="xiaohongshu",
                title="用户B素材",
                content_text="用户B敏感串：这条内容绝不能被A用户检索命中。",
                tags=["B"],
            )
            doc_a = orchestrator_a.ensure_material_knowledge(material_a["material_id"]).knowledge_documents[0]
            doc_b = orchestrator_b.ensure_material_knowledge(material_b["material_id"]).knowledge_documents[0]

        response = client.post(
            "/api/v2/materials/ingest-and-rewrite",
            headers=auth_headers_a,
            json={
                "platform": "xiaohongshu",
                "title": "A用户检索测试",
                "content_text": "征信修复时应该先看查询次数和当前负债情况。",
                "target_platform": "xiaohongshu",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        reference_ids = [row["document_id"] for row in payload["references"]]
        assert doc_a.id in reference_ids
        assert doc_b.id not in reference_ids
        assert any("用户A专属标记" in prompt for prompt in captured_prompts)
        assert all("用户B敏感串" not in prompt for prompt in captured_prompts)
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_publish_task_submit_creates_lead_and_trace_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            owner, owner_headers = _make_auth_headers(db, "pg_publish_owner", "pg_publish_owner@example.com")
            assignee, assignee_headers = _make_auth_headers(
                db, "pg_publish_assignee", "pg_publish_assignee@example.com"
            )

        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=owner_headers,
            json={
                "platform": "xiaohongshu",
                "account_name": "PG账号",
                "task_title": "PG发布任务闭环",
                "content_text": "这是一条 PostgreSQL 发布任务闭环测试内容。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "pending"

        assign_resp = client.post(
            f"/api/publish/tasks/{task_id}/assign",
            headers=owner_headers,
            json={"assigned_to": assignee.id, "note": "分配给执行人"},
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["assigned_to"] == assignee.id
        assert assign_resp.json()["status"] == "pending"

        claim_resp = client.post(
            f"/api/publish/tasks/{task_id}/claim",
            headers=assignee_headers,
            json={"note": "我来执行"},
        )
        assert claim_resp.status_code == 200
        assert claim_resp.json()["status"] == "claimed"

        submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=assignee_headers,
            json={
                "post_url": "https://example.com/pg-publish-task",
                "views": 120,
                "wechat_adds": 3,
                "leads": 2,
                "valid_leads": 1,
                "conversions": 0,
                "note": "提交发布结果",
            },
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "submitted"
        assert submit_resp.json()["assigned_to"] == assignee.id

        trace_resp = client.get(
            f"/api/publish/tasks/{task_id}/trace",
            headers=assignee_headers,
        )
        assert trace_resp.status_code == 200
        trace_payload = trace_resp.json()
        assert trace_payload["lead_id"] is not None
        assert trace_payload["customer_id"] is None

        lead_list_resp = client.get("/api/lead/list", headers=assignee_headers)
        assert lead_list_resp.status_code == 200
        lead_rows = lead_list_resp.json()
        matched = next((row for row in lead_rows if row["publish_task_id"] == task_id), None)
        assert matched is not None
        assert matched["owner_id"] == assignee.id
        assert matched["status"] == "qualified"

        detail_resp = client.get(
            f"/api/publish/tasks/{task_id}",
            headers=assignee_headers,
        )
        assert detail_resp.status_code == 200
        assert len(detail_resp.json()["feedbacks"]) >= 4
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_lead_assign_and_convert_customer_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            owner, owner_headers = _make_auth_headers(db, "pg_lead_owner", "pg_lead_owner@example.com")
            operator, operator_headers = _make_auth_headers(db, "pg_lead_operator", "pg_lead_operator@example.com")

        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=owner_headers,
            json={
                "platform": "douyin",
                "account_name": "PG线索账号",
                "task_title": "PG线索转客户闭环",
                "content_text": "用于验证 PostgreSQL 线索分配与转客户。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=owner_headers,
            json={
                "wechat_adds": 2,
                "leads": 1,
                "valid_leads": 1,
                "conversions": 0,
                "note": "先生成线索，不自动转客户",
            },
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "submitted"

        leads_resp = client.get("/api/lead/list", headers=owner_headers)
        assert leads_resp.status_code == 200
        lead = next((row for row in leads_resp.json() if row["publish_task_id"] == task_id), None)
        assert lead is not None
        assert lead["customer_id"] is None

        assign_resp = client.post(
            f"/api/lead/{lead['id']}/assign",
            headers=owner_headers,
            json={"owner_id": operator.id},
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["owner_id"] == operator.id

        convert_resp = client.post(
            f"/api/lead/{lead['id']}/convert-customer",
            headers=operator_headers,
            json={
                "nickname": "PG转客户测试",
                "tags": ["postgres", "lead"],
                "intention_level": "high",
            },
        )
        assert convert_resp.status_code == 200
        customer_payload = convert_resp.json()
        assert customer_payload["nickname"] == "PG转客户测试"
        assert customer_payload["lead_id"] == lead["id"]

        trace_resp = client.get(
            f"/api/lead/{lead['id']}/trace",
            headers=operator_headers,
        )
        assert trace_resp.status_code == 200
        trace_payload = trace_resp.json()
        assert trace_payload["id"] == lead["id"]
        assert trace_payload["customer_id"] == customer_payload["id"]
        assert trace_payload["publish_task_id"] == task_id

        with SessionLocal() as db:
            lead_row = db.query(Lead).filter(Lead.id == lead["id"]).first()
            customer_row = db.query(Customer).filter(Customer.id == customer_payload["id"]).first()
            assert lead_row is not None
            assert customer_row is not None
            assert lead_row.owner_id == operator.id
            assert customer_row.owner_id == operator.id
            assert customer_row.lead_id == lead_row.id
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_publish_task_reject_and_close_lifecycle_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            owner, owner_headers = _make_auth_headers(db, "pg_publish_flow_owner", "pg_publish_flow_owner@example.com")
            assignee, assignee_headers = _make_auth_headers(
                db, "pg_publish_flow_assignee", "pg_publish_flow_assignee@example.com"
            )

        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=owner_headers,
            json={
                "platform": "xiaohongshu",
                "account_name": "PG发布流转账号",
                "task_title": "PG发布任务拒绝关闭流转",
                "content_text": "用于验证 PostgreSQL 下发布任务 reject/close 生命周期。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "pending"

        assign_resp = client.post(
            f"/api/publish/tasks/{task_id}/assign",
            headers=owner_headers,
            json={"assigned_to": assignee.id, "note": "分配执行"},
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["assigned_to"] == assignee.id

        claim_resp = client.post(
            f"/api/publish/tasks/{task_id}/claim",
            headers=assignee_headers,
            json={"note": "先认领任务"},
        )
        assert claim_resp.status_code == 200
        assert claim_resp.json()["status"] == "claimed"

        reject_resp = client.post(
            f"/api/publish/tasks/{task_id}/reject",
            headers=owner_headers,
            json={"note": "素材表达还需要调整"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"
        assert reject_resp.json()["reject_reason"] == "素材表达还需要调整"

        reclaim_resp = client.post(
            f"/api/publish/tasks/{task_id}/claim",
            headers=assignee_headers,
            json={"note": "调整后重新认领"},
        )
        assert reclaim_resp.status_code == 200
        assert reclaim_resp.json()["status"] == "claimed"

        close_resp = client.post(
            f"/api/publish/tasks/{task_id}/close",
            headers=owner_headers,
            json={"note": "本轮任务关闭归档"},
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"
        assert close_resp.json()["close_reason"] == "本轮任务关闭归档"

        close_again_resp = client.post(
            f"/api/publish/tasks/{task_id}/close",
            headers=owner_headers,
            json={"note": "重复关闭应保持幂等"},
        )
        assert close_again_resp.status_code == 200
        assert close_again_resp.json()["status"] == "closed"
        assert close_again_resp.json()["close_reason"] == "本轮任务关闭归档"

        detail_resp = client.get(f"/api/publish/tasks/{task_id}", headers=owner_headers)
        assert detail_resp.status_code == 200
        detail_payload = detail_resp.json()
        actions = [row["action"] for row in detail_payload["feedbacks"]]
        assert actions.count("assign") == 1
        assert actions.count("claim") >= 2
        assert actions.count("reject") == 1
        assert actions.count("close") == 1

        trace_resp = client.get(f"/api/publish/tasks/{task_id}/trace", headers=owner_headers)
        assert trace_resp.status_code == 200
        trace_payload = trace_resp.json()
        assert trace_payload["lead_id"] is None
        assert trace_payload["customer_id"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_lead_status_update_and_convert_customer_is_idempotent_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            owner, owner_headers = _make_auth_headers(db, "pg_lead_status_owner", "pg_lead_status_owner@example.com")

        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=owner_headers,
            json={
                "platform": "douyin",
                "account_name": "PG状态账号",
                "task_title": "PG线索状态与转客户幂等",
                "content_text": "用于验证 PostgreSQL 下线索状态更新和转客户幂等。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=owner_headers,
            json={
                "wechat_adds": 1,
                "leads": 1,
                "valid_leads": 0,
                "conversions": 0,
                "note": "生成初始线索",
            },
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "submitted"

        leads_resp = client.get("/api/lead/list", headers=owner_headers)
        assert leads_resp.status_code == 200
        lead = next((row for row in leads_resp.json() if row["publish_task_id"] == task_id), None)
        assert lead is not None
        assert lead["customer_id"] is None

        status_resp = client.put(
            f"/api/lead/{lead['id']}/status",
            headers=owner_headers,
            json={"status": "contacted"},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "contacted"

        convert_first_resp = client.post(
            f"/api/lead/{lead['id']}/convert-customer",
            headers=owner_headers,
            json={
                "nickname": "PG幂等客户",
                "tags": ["postgres", "idempotent"],
                "intention_level": "medium",
            },
        )
        assert convert_first_resp.status_code == 200
        first_customer = convert_first_resp.json()
        assert first_customer["nickname"] == "PG幂等客户"
        assert first_customer["lead_id"] == lead["id"]

        convert_second_resp = client.post(
            f"/api/lead/{lead['id']}/convert-customer",
            headers=owner_headers,
            json={
                "nickname": "第二次转换不应新建",
                "tags": ["should-not-create-new"],
                "intention_level": "high",
            },
        )
        assert convert_second_resp.status_code == 200
        second_customer = convert_second_resp.json()
        assert second_customer["id"] == first_customer["id"]
        assert second_customer["nickname"] == "PG幂等客户"
        assert second_customer["lead_id"] == lead["id"]

        trace_resp = client.get(f"/api/lead/{lead['id']}/trace", headers=owner_headers)
        assert trace_resp.status_code == 200
        trace_payload = trace_resp.json()
        assert trace_payload["status"] == "contacted"
        assert trace_payload["customer_id"] == first_customer["id"]
        assert trace_payload["publish_task_id"] == task_id

        with SessionLocal() as db:
            lead_row = db.query(Lead).filter(Lead.id == lead["id"]).first()
            customer_rows = db.query(Customer).filter(Customer.lead_id == lead["id"]).all()
            assert lead_row is not None
            assert lead_row.status == "contacted"
            assert len(customer_rows) == 1
            assert customer_rows[0].id == first_customer["id"]
            assert customer_rows[0].owner_id == owner.id
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_publish_task_repeat_submit_overwrites_metrics_without_duplicate_lead_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            owner, owner_headers = _make_auth_headers(
                db, "pg_repeat_submit_owner", "pg_repeat_submit_owner@example.com"
            )

        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=owner_headers,
            json={
                "platform": "xiaohongshu",
                "account_name": "PG重复提交账号",
                "task_title": "PG重复提交覆盖回归",
                "content_text": "用于验证 PostgreSQL 下重复提交不会产出重复线索。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]

        first_submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=owner_headers,
            json={
                "post_url": "https://example.com/repeat-submit-v1",
                "views": 100,
                "wechat_adds": 2,
                "leads": 1,
                "valid_leads": 0,
                "conversions": 0,
                "note": "第一次提交",
            },
        )
        assert first_submit_resp.status_code == 200
        assert first_submit_resp.json()["status"] == "submitted"

        trace_first_resp = client.get(f"/api/publish/tasks/{task_id}/trace", headers=owner_headers)
        assert trace_first_resp.status_code == 200
        first_trace = trace_first_resp.json()
        assert first_trace["lead_id"] is not None
        assert first_trace["customer_id"] is None

        second_submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=owner_headers,
            json={
                "post_url": "https://example.com/repeat-submit-v2",
                "views": 260,
                "wechat_adds": 5,
                "leads": 3,
                "valid_leads": 2,
                "conversions": 1,
                "note": "第二次提交覆盖统计",
            },
        )
        assert second_submit_resp.status_code == 200
        second_payload = second_submit_resp.json()
        assert second_payload["status"] == "submitted"
        assert second_payload["post_url"] == "https://example.com/repeat-submit-v2"
        assert second_payload["views"] == 260
        assert second_payload["valid_leads"] == 2
        assert second_payload["conversions"] == 1

        trace_second_resp = client.get(f"/api/publish/tasks/{task_id}/trace", headers=owner_headers)
        assert trace_second_resp.status_code == 200
        second_trace = trace_second_resp.json()
        assert second_trace["lead_id"] == first_trace["lead_id"]
        assert second_trace["customer_id"] is not None

        with SessionLocal() as db:
            lead_rows = db.query(Lead).filter(Lead.publish_task_id == task_id).all()
            customer_rows = db.query(Customer).filter(Customer.lead_id == first_trace["lead_id"]).all()
            assert len(lead_rows) == 1
            assert len(customer_rows) == 1
            lead_row = lead_rows[0]
            assert lead_row.post_url == "https://example.com/repeat-submit-v2"
            assert lead_row.wechat_adds == 5
            assert lead_row.leads == 3
            assert lead_row.valid_leads == 2
            assert lead_row.conversions == 1
            assert lead_row.status == "converted"
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@requires_postgres
def test_lead_and_customer_cross_user_access_is_forbidden_on_postgres():
    engine, SessionLocal, client = _make_pg_api_client()

    try:
        with SessionLocal() as db:
            owner, owner_headers = _make_auth_headers(db, "pg_acl_owner", "pg_acl_owner@example.com")
            intruder, intruder_headers = _make_auth_headers(db, "pg_acl_intruder", "pg_acl_intruder@example.com")

        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=owner_headers,
            json={
                "platform": "douyin",
                "account_name": "PG权限账号",
                "task_title": "PG跨用户权限回归",
                "content_text": "用于验证线索与客户跨用户不能越权访问。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]

        submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=owner_headers,
            json={
                "wechat_adds": 3,
                "leads": 2,
                "valid_leads": 1,
                "conversions": 0,
                "note": "生成归属给 owner 的线索",
            },
        )
        assert submit_resp.status_code == 200

        leads_resp = client.get("/api/lead/list", headers=owner_headers)
        assert leads_resp.status_code == 200
        lead = next((row for row in leads_resp.json() if row["publish_task_id"] == task_id), None)
        assert lead is not None

        owner_convert_resp = client.post(
            f"/api/lead/{lead['id']}/convert-customer",
            headers=owner_headers,
            json={"nickname": "PG权限客户"},
        )
        assert owner_convert_resp.status_code == 200
        customer = owner_convert_resp.json()

        list_other_resp = client.get(f"/api/lead/list?owner_id={owner.id}", headers=intruder_headers)
        assert list_other_resp.status_code == 403

        status_other_resp = client.put(
            f"/api/lead/{lead['id']}/status",
            headers=intruder_headers,
            json={"status": "lost"},
        )
        assert status_other_resp.status_code == 403

        assign_other_resp = client.post(
            f"/api/lead/{lead['id']}/assign",
            headers=intruder_headers,
            json={"owner_id": intruder.id},
        )
        assert assign_other_resp.status_code == 403

        trace_other_resp = client.get(f"/api/lead/{lead['id']}/trace", headers=intruder_headers)
        assert trace_other_resp.status_code == 403

        convert_other_resp = client.post(
            f"/api/lead/{lead['id']}/convert-customer",
            headers=intruder_headers,
            json={"nickname": "越权客户"},
        )
        assert convert_other_resp.status_code == 403

        customer_get_other_resp = client.get(f"/api/customer/{customer['id']}", headers=intruder_headers)
        assert customer_get_other_resp.status_code == 404

        customer_update_other_resp = client.put(
            f"/api/customer/{customer['id']}",
            headers=intruder_headers,
            json={"nickname": "恶意改名"},
        )
        assert customer_update_other_resp.status_code == 404

        customer_delete_other_resp = client.delete(f"/api/customer/{customer['id']}", headers=intruder_headers)
        assert customer_delete_other_resp.status_code == 404

        with SessionLocal() as db:
            lead_row = db.query(Lead).filter(Lead.id == lead["id"]).first()
            customer_row = db.query(Customer).filter(Customer.id == customer["id"]).first()
            assert lead_row is not None
            assert customer_row is not None
            assert lead_row.owner_id == owner.id
            assert lead_row.status == "qualified"
            assert customer_row.owner_id == owner.id
            assert customer_row.nickname == "PG权限客户"
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
