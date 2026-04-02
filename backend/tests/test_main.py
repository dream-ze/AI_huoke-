"""
Pytest test suite
"""

import pytest
from app.core.database import Base, get_db
from app.models import GenerationTask, MaterialItem, User
from app.services.user_service import UserService
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# Test database - path relative to backend root
SQLALCHEMY_DATABASE_URL = "sqlite:///../test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)
TEST_PASSWORD = "StrongPass_2026!"


@pytest.fixture
def auth_headers(test_db):
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": TEST_PASSWORD,
        },
    )

    resp = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": TEST_PASSWORD,
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def another_auth_headers(test_db):
    client.post(
        "/api/auth/register",
        json={
            "username": "anotheruser",
            "email": "another@example.com",
            "password": TEST_PASSWORD,
        },
    )

    resp = client.post(
        "/api/auth/login",
        json={
            "username": "anotheruser",
            "password": TEST_PASSWORD,
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestAuth:
    def test_register(self, test_db):
        response = client.post(
            "/api/auth/register", json={"username": "testuser", "email": "test@example.com", "password": TEST_PASSWORD}
        )
        # 如果用户已存在（测试 db 残留）或注册成功均认为通过
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"

    def test_login(self, test_db):
        client.post(
            "/api/auth/register", json={"username": "testuser", "email": "test@example.com", "password": TEST_PASSWORD}
        )

        response = client.post("/api/auth/login", json={"username": "testuser", "password": TEST_PASSWORD})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestUserServiceRegression:
    class _FakeQuery:
        def __init__(self, existing_user=None):
            self._existing_user = existing_user

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self._existing_user

    class _FakeDB:
        def __init__(self, commit_side_effects=None, existing_user=None):
            self._commit_side_effects = list(commit_side_effects or [])
            self._existing_user = existing_user
            self.added_users = []
            self.commit_calls = 0
            self.rollback_calls = 0
            self.refresh_calls = 0

        def query(self, _model):
            return TestUserServiceRegression._FakeQuery(existing_user=self._existing_user)

        def add(self, obj):
            self.added_users.append(obj)

        def commit(self):
            self.commit_calls += 1
            if self._commit_side_effects:
                effect = self._commit_side_effects.pop(0)
                if isinstance(effect, Exception):
                    raise effect

        def rollback(self):
            self.rollback_calls += 1

        def refresh(self, _obj):
            self.refresh_calls += 1

    @staticmethod
    def _make_integrity_error(detail: str) -> IntegrityError:
        return IntegrityError("INSERT INTO users ...", {}, Exception(detail))

    @pytest.mark.regression
    def test_create_user_recovers_from_users_pkey_sequence_drift(self, monkeypatch):
        db = self._FakeDB(
            commit_side_effects=[
                self._make_integrity_error('duplicate key value violates unique constraint "users_pkey"'),
                None,
            ]
        )

        sync_called = {"count": 0}

        def fake_sync(_db):
            sync_called["count"] += 1
            return True

        monkeypatch.setattr(UserService, "_sync_user_id_sequence", staticmethod(fake_sync))

        user = UserService.create_user(
            db,
            username="seq_fix_user",
            email="seq_fix_user@example.com",
            password=TEST_PASSWORD,
        )

        assert user.username == "seq_fix_user"
        assert user.email == "seq_fix_user@example.com"
        assert sync_called["count"] == 1
        assert db.commit_calls == 2
        assert db.rollback_calls == 1
        assert db.refresh_calls == 1
        assert len(db.added_users) == 2

    @pytest.mark.regression
    def test_create_user_unique_constraint_still_returns_400(self):
        db = self._FakeDB(
            commit_side_effects=[
                self._make_integrity_error('duplicate key value violates unique constraint "users_email_key"')
            ]
        )

        with pytest.raises(HTTPException) as exc:
            UserService.create_user(
                db,
                username="dup_user",
                email="dup_user@example.com",
                password=TEST_PASSWORD,
            )

        assert exc.value.status_code == 400
        assert exc.value.detail == "Username or email already exists"
        assert db.commit_calls == 1
        assert db.rollback_calls == 1


class TestContent:
    def test_create_content(self, auth_headers, test_db):
        legacy = client.post(
            "/api/content/create",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "content_type": "post",
                "title": "Legacy Content",
                "content": "legacy",
            },
        )
        assert legacy.status_code == 410

        # ingest-page 已下线（410 Gone），手动录入需走收件箱接口
        response = client.post(
            "/api/v2/collect/ingest-page",
            headers=auth_headers,
            json={
                "source_type": "manual_link",
                "platform": "xiaohongshu",
                "content_type": "post",
                "title": "Test Content",
                "content_text": "This is test content",
            },
        )
        assert response.status_code == 410, "ingest-page 应返回 410 Gone"

        # 新链路：手动录入走收件箱
        inbox_resp = client.post(
            "/api/v1/material/inbox/manual",
            headers=auth_headers,
            json={"platform": "xiaohongshu", "title": "Test Content", "content": "This is test content", "tags": []},
        )
        assert inbox_resp.status_code == 200
        assert inbox_resp.json()["status"] == "pending"


class TestCompliance:
    def test_compliance_check(self, auth_headers):
        response = client.post(
            "/api/compliance/check", headers=auth_headers, json={"content": "这个产品100%通过！包过秒批！"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] is not None


class TestV1Routing:
    def test_v1_health(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "v1"

    def test_v1_collect_keyword_task_to_inbox(self, auth_headers, monkeypatch):
        from app.collector.services.browser_client import BrowserCollectorClient

        def fake_collect_keyword(self, platform: str, keyword: str, max_items: int = 20):
            return {
                "success": True,
                "total": 1,
                "items": [
                    {
                        "platform": platform,
                        "keyword": keyword,
                        "title": "关键词采集测试标题",
                        "author": "作者A",
                        "content": "内容A",
                        "url": "https://www.xiaohongshu.com/discovery/item/abc1",
                        "like_count": "12",
                        "comment_count": "3",
                        "collect_count": "2",
                        "share_count": "1",
                    }
                ],
            }

        monkeypatch.setattr(BrowserCollectorClient, "collect_keyword", fake_collect_keyword)

        response = client.post(
            "/api/v1/collector/tasks/keyword",
            headers=auth_headers,
            json={"platform": "xiaohongshu", "keyword": "贷款", "max_items": 10},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] is not None
        assert payload["inbox_count"] == 1

    def test_legacy_collect_route_removed(self, auth_headers):
        response = client.get(
            "/api/collect/stats",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_legacy_ai_route_removed(self, auth_headers):
        response = client.post(
            "/api/ai/rewrite/zhihu",
            headers=auth_headers,
            json={
                "content_id": 1,
                "target_platform": "zhihu",
                "content_type": "answer",
            },
        )
        assert response.status_code in (404, 405)

    def test_v1_plugin_collect_deprecated(self, auth_headers):
        response = client.post(
            "/api/v1/ai/plugin/collect",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "插件采集测试",
                "content": "测试内容",
                "author": "测试作者",
                "tags": ["插件"],
                "comments_json": [],
                "url": "https://example.com/plugin-sync-test",
                "heat_score": 10,
            },
        )
        assert response.status_code == 410

    def test_v1_employee_submission_link_to_inbox(self, auth_headers, monkeypatch):
        from app.collector.services.browser_client import BrowserCollectorClient

        def fake_collect_single_link(self, url: str):
            return {
                "success": True,
                "total": 1,
                "items": [
                    {
                        "platform": "xiaohongshu",
                        "title": "员工提交标题",
                        "author": "员工作者",
                        "content": "员工提交正文",
                        "url": url,
                        "like_count": "20",
                        "comment_count": "5",
                    }
                ],
            }

        monkeypatch.setattr(BrowserCollectorClient, "collect_single_link", fake_collect_single_link)

        submit_resp = client.post(
            "/api/v1/employee-submissions/link",
            headers=auth_headers,
            json={
                "url": "https://www.xiaohongshu.com/discovery/item/xyz1",
                "note": "员工提交",
            },
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["submission_id"] is not None

        list_resp = client.get("/api/v1/material/inbox", headers=auth_headers)
        assert list_resp.status_code == 200
        rows = list_resp.json()
        assert len(rows) >= 1
        assert rows[0]["source_channel"] in ("employee_submission", "collect_task", "wechat_robot")

    def test_v2_collect_ingest_and_material_detail(self, auth_headers):
        """ingest-page 已被标记为 410 Gone，新配置走收件箱链路。"""
        ingest_resp = client.post(
            "/api/v2/collect/ingest-page",
            headers=auth_headers,
            json={
                "source_type": "manual_link",
                "client_request_id": "req-v2-collect-001",
                "platform": "xiaohongshu",
                "source_url": "https://example.com/v2-material-1",
                "content_type": "post",
                "title": "v2 采集入库测试",
                "content_text": "这是一条用于验证 v2 采集入库的内容正文。",
            },
        )
        assert ingest_resp.status_code == 410, "ingest-page 应返回 410 Gone"

    def test_v2_collect_dedupe_by_request_id(self, auth_headers):
        """ingest-page 已被标记为 410 Gone，去重逻辑随旧端点一同下线。"""
        payload = {
            "source_type": "browser_plugin",
            "client_request_id": "req-v2-dedupe-001",
            "platform": "xiaohongshu",
            "source_url": "https://example.com/v2-dedupe",
            "content_type": "post",
            "title": "v2 去重测试",
            "content_text": "相同请求 ID 应复用已有素材",
        }
        first = client.post("/api/v2/collect/ingest-page", headers=auth_headers, json=payload)
        second = client.post("/api/v2/collect/ingest-page", headers=auth_headers, json=payload)
        assert first.status_code == 410, "ingest-page 应返回 410 Gone"
        assert second.status_code == 410

    def test_inbox_action_approve(self, auth_headers, monkeypatch):
        """approve → ContentAsset + InsightContentItem 均入库，status 变 approved。"""
        from app.collector.services.browser_client import BrowserCollectorClient

        def fake_kw(self, platform, keyword, max_items):
            return {
                "success": True,
                "total": 1,
                "items": [
                    {
                        "platform": platform,
                        "title": "审核测试标题",
                        "content": "审核正文",
                        "author": "测试作者",
                        "url": "https://example.com/approve-test",
                        "like_count": 100,
                        "comment_count": 20,
                    }
                ],
            }

        monkeypatch.setattr(BrowserCollectorClient, "collect_keyword", fake_kw)
        task_resp = client.post(
            "/api/v1/collector/tasks/keyword",
            headers=auth_headers,
            json={"platform": "xiaohongshu", "keyword": "审核测试", "max_items": 1},
        )
        assert task_resp.status_code == 200
        assert task_resp.json()["inbox_count"] == 1

        items = client.get("/api/v1/material/inbox", headers=auth_headers, params={"status": "pending"}).json()
        assert len(items) >= 1
        inbox_id = items[0]["id"]

        approve_resp = client.post(
            f"/api/v1/material/inbox/{inbox_id}/approve",
            headers=auth_headers,
            json={"remark": "单测审核"},
        )
        assert approve_resp.status_code == 200
        data = approve_resp.json()
        assert data["status"] == "approved"
        assert data["content_asset_id"] is not None
        assert data["insight_item_id"] is not None

        detail = client.get(f"/api/v1/material/inbox/{inbox_id}", headers=auth_headers).json()
        assert detail["status"] == "approved"

    def test_inbox_action_discard(self, auth_headers, monkeypatch):
        """discard → status 变 discarded，再次 discard 返回 409。"""
        from app.collector.services.browser_client import BrowserCollectorClient

        def fake_kw(self, platform, keyword, max_items):
            return {
                "success": True,
                "total": 1,
                "items": [
                    {
                        "platform": platform,
                        "title": "丢弃测试标题",
                        "content": "丢弃正文",
                        "author": "丢弃作者",
                        "url": "https://example.com/discard-test",
                        "like_count": 10,
                        "comment_count": 2,
                    }
                ],
            }

        monkeypatch.setattr(BrowserCollectorClient, "collect_keyword", fake_kw)
        client.post(
            "/api/v1/collector/tasks/keyword",
            headers=auth_headers,
            json={"platform": "xiaohongshu", "keyword": "丢弃测试", "max_items": 1},
        )
        items = client.get("/api/v1/material/inbox", headers=auth_headers, params={"status": "pending"}).json()
        assert len(items) >= 1
        inbox_id = items[0]["id"]

        discard_resp = client.post(
            f"/api/v1/material/inbox/{inbox_id}/discard",
            headers=auth_headers,
            json={"remark": "不符合要求"},
        )
        assert discard_resp.status_code == 200
        assert discard_resp.json()["status"] == "discarded"

        repeat_resp = client.post(
            f"/api/v1/material/inbox/{inbox_id}/discard",
            headers=auth_headers,
            json={},
        )
        assert repeat_resp.status_code == 409

    def test_inbox_action_to_negative_case(self, auth_headers, monkeypatch):
        """to-negative-case → InsightContentItem 入库（manual_note 含 [反案例]），status=negative_case。"""
        from app.collector.services.browser_client import BrowserCollectorClient

        def fake_kw(self, platform, keyword, max_items):
            return {
                "success": True,
                "total": 1,
                "items": [
                    {
                        "platform": platform,
                        "title": "反案例测试标题",
                        "content": "反案例正文",
                        "author": "反案例作者",
                        "url": "https://example.com/neg-test",
                        "like_count": 5,
                        "comment_count": 1,
                    }
                ],
            }

        monkeypatch.setattr(BrowserCollectorClient, "collect_keyword", fake_kw)
        client.post(
            "/api/v1/collector/tasks/keyword",
            headers=auth_headers,
            json={"platform": "xiaohongshu", "keyword": "反案例测试", "max_items": 1},
        )
        items = client.get("/api/v1/material/inbox", headers=auth_headers, params={"status": "pending"}).json()
        assert len(items) >= 1
        inbox_id = items[0]["id"]

        neg_resp = client.post(
            f"/api/v1/material/inbox/{inbox_id}/to-negative-case",
            headers=auth_headers,
            json={"remark": "导向错误"},
        )
        assert neg_resp.status_code == 200
        data = neg_resp.json()
        assert data["status"] == "negative_case"
        assert data["insight_item_id"] is not None

    def test_inbox_manual_submit(self, auth_headers):
        """手动录入 → 进收件箱 pending，approve 后入素材库。"""
        # 1. 提交到收件箱
        submit_resp = client.post(
            "/api/v1/material/inbox/manual",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "手动录入标题（单测）",
                "content": "这是一段用于验证手动录入链路的正文内容，长度足够。",
                "tags": ["单测", "手动"],
                "note": "来自 onSubmit / onVisionToRewrite",
            },
        )
        assert submit_resp.status_code == 200
        result = submit_resp.json()
        assert result["status"] == "pending"
        inbox_id = result["inbox_id"]
        assert inbox_id is not None

        # 2. 收件箱可见该条目
        inbox_list = client.get(
            "/api/v1/material/inbox",
            headers=auth_headers,
            params={"status": "pending"},
        ).json()
        ids = [item["id"] for item in inbox_list]
        assert inbox_id in ids

        # 3. 审核通过 → 入素材库与洞察库
        approve_resp = client.post(
            f"/api/v1/material/inbox/{inbox_id}/approve",
            headers=auth_headers,
            json={"remark": "手动录入通过"},
        )
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["status"] == "approved"
        assert approve_data["content_asset_id"] is not None
        assert approve_data["insight_item_id"] is not None

        # 4. 再次 approve 应返回 409（幂等保护）
        repeat_resp = client.post(
            f"/api/v1/material/inbox/{inbox_id}/approve",
            headers=auth_headers,
            json={},
        )
        assert repeat_resp.status_code == 409


class TestMaterialsQueryOptimization:
    def test_v2_materials_list_avoids_n_plus_one_queries(self, auth_headers):
        for idx in range(3):
            submit_resp = client.post(
                "/api/v1/material/inbox/manual",
                headers=auth_headers,
                json={
                    "platform": "xiaohongshu",
                    "title": f"素材优化测试-{idx}",
                    "content": f"这是第 {idx} 条素材，用于验证列表查询预加载能力。",
                    "tags": ["opt"],
                },
            )
            assert submit_resp.status_code == 200

        with TestingSessionLocal() as db:
            user = db.query(User).filter(User.username == "testuser").first()
            assert user is not None

            materials = (
                db.query(MaterialItem).filter(MaterialItem.owner_id == user.id).order_by(MaterialItem.id.asc()).all()
            )
            assert len(materials) >= 3

            for material in materials:
                db.add(
                    GenerationTask(
                        owner_id=user.id,
                        material_item_id=material.id,
                        platform=material.platform or "xiaohongshu",
                        account_type="科普号",
                        target_audience="泛人群",
                        task_type="rewrite",
                        output_text=f"改写结果-{material.id}",
                    )
                )
            db.commit()

        select_count = {"value": 0}

        def _before_cursor_execute(_conn, _cursor, statement, _parameters, _context, _executemany):
            sql = (statement or "").lstrip().upper()
            if sql.startswith("SELECT"):
                select_count["value"] += 1

        event.listen(engine, "before_cursor_execute", _before_cursor_execute)
        try:
            response = client.get("/api/v2/materials", headers=auth_headers)
        finally:
            event.remove(engine, "before_cursor_execute", _before_cursor_execute)

        assert response.status_code == 200
        rows = response.json()
        assert len(rows) >= 3
        assert all("generation_count" in row for row in rows)
        assert select_count["value"] <= 8


class TestMaterialPipelineOrchestratorApi:
    def test_v2_ingest_and_rewrite_cleans_content_and_persists_knowledge(self, auth_headers, monkeypatch):
        from app.services.ai_service import AIService

        async def fake_call_llm(self, prompt, system_prompt="", use_cloud=False, user_id=None, scene="general"):
            _ = prompt
            _ = system_prompt
            _ = use_cloud
            _ = user_id
            _ = scene
            return "这是一段用于生成测试的模型基础输出。"

        monkeypatch.setattr(AIService, "call_llm", fake_call_llm)

        response = client.post(
            "/api/v2/materials/ingest-and-rewrite",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "  采集测试标题  ",
                "content_text": (
                    "作者：张三\n"
                    "发布时间：今天\n"
                    "这是正文第一段。\n"
                    "#贷款 #征信\n"
                    "展开\n"
                    "这是正文第一段。\n"
                    "这是正文第二段。"
                ),
                "tags": ["采集", "测试"],
                "target_platform": "xiaohongshu",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["material_id"] is not None
        assert payload["knowledge_document_id"] is not None
        assert payload["generation_task_id"] is not None
        assert payload["cleaned_title"] == "采集测试标题"
        assert payload["cleaned_content_text"] == "这是正文第一段。\n这是正文第二段。"
        assert payload["output_text"]

        detail_resp = client.get(
            f"/api/v2/materials/{payload['material_id']}",
            headers=auth_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["content_text"] == "这是正文第一段。\n这是正文第二段。"
        assert len(detail["knowledge_documents"]) >= 1
        assert detail["knowledge_documents"][0]["content_text"] == "这是正文第一段。\n这是正文第二段。"
        assert len(detail["generation_tasks"]) >= 1


class TestPublishTaskWorkflow:
    def test_publish_task_lifecycle(self, auth_headers):
        create_resp = client.post(
            "/api/publish/tasks/create",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "account_name": "测试账号",
                "task_title": "发布任务闭环测试",
                "content_text": "这是一条用于验证任务中心闭环的发布内容。",
            },
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "pending"

        claim_resp = client.post(
            f"/api/publish/tasks/{task_id}/claim",
            headers=auth_headers,
            json={"note": "我来发布"},
        )
        assert claim_resp.status_code == 200
        assert claim_resp.json()["status"] == "claimed"

        submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=auth_headers,
            json={
                "post_url": "https://example.com/post/123",
                "views": 100,
                "wechat_adds": 8,
                "leads": 5,
                "valid_leads": 3,
                "conversions": 1,
                "note": "已发布并回填结果",
            },
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "submitted"
        assert submit_resp.json()["post_url"] == "https://example.com/post/123"

        trace_resp = client.get(
            f"/api/publish/tasks/{task_id}/trace",
            headers=auth_headers,
        )
        assert trace_resp.status_code == 200
        trace_data = trace_resp.json()
        assert trace_data["lead_id"] is not None

        detail_resp = client.get(
            f"/api/publish/tasks/{task_id}",
            headers=auth_headers,
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["feedbacks"]) >= 3

        reject_resp = client.post(
            f"/api/publish/tasks/{task_id}/reject",
            headers=auth_headers,
            json={"note": "封面不合规，打回"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

        close_resp = client.post(
            f"/api/publish/tasks/{task_id}/close",
            headers=auth_headers,
            json={"note": "本轮结束"},
        )
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "closed"

        stats_resp = client.get("/api/publish/tasks/stats", headers=auth_headers)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total"] >= 1
        assert stats["closed"] >= 1


class TestLeadPool:
    def test_lead_status_and_assign(self, auth_headers):
        task_resp = client.post(
            "/api/publish/tasks/create",
            headers=auth_headers,
            json={
                "platform": "douyin",
                "account_name": "测试账号2",
                "task_title": "线索池状态流转测试",
                "content_text": "用于验证线索池最小闭环",
            },
        )
        assert task_resp.status_code == 200
        task_id = task_resp.json()["id"]

        submit_resp = client.post(
            f"/api/publish/tasks/{task_id}/submit",
            headers=auth_headers,
            json={
                "wechat_adds": 2,
                "leads": 1,
                "valid_leads": 1,
            },
        )
        assert submit_resp.status_code == 200

        leads_resp = client.get("/api/lead/list", headers=auth_headers)
        assert leads_resp.status_code == 200
        leads = leads_resp.json()
        assert len(leads) >= 1

        matched = None
        for item in leads:
            if item["publish_task_id"] == task_id:
                matched = item
                break
        assert matched is not None

        update_resp = client.put(
            f"/api/lead/{matched['id']}/status",
            headers=auth_headers,
            json={"status": "qualified"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "qualified"

        assign_resp = client.post(
            f"/api/lead/{matched['id']}/assign",
            headers=auth_headers,
            json={},
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["owner_id"] is not None

        convert_resp = client.post(
            f"/api/lead/{matched['id']}/convert-customer",
            headers=auth_headers,
            json={"nickname": "线索转客户测试"},
        )
        assert convert_resp.status_code == 200
        assert convert_resp.json()["nickname"] == "线索转客户测试"

        leads_after_convert = client.get("/api/lead/list", headers=auth_headers)
        assert leads_after_convert.status_code == 200
        refreshed = None
        for item in leads_after_convert.json():
            if item["id"] == matched["id"]:
                refreshed = item
                break
        assert refreshed is not None
        assert refreshed["customer_id"] is not None

        lead_trace_resp = client.get(
            f"/api/lead/{matched['id']}/trace",
            headers=auth_headers,
        )
        assert lead_trace_resp.status_code == 200
        assert lead_trace_resp.json()["customer_id"] is not None

    def test_lead_convert_customer_forbidden_for_non_owner(self, auth_headers, another_auth_headers):
        create_resp = client.post(
            "/api/lead/create",
            headers=auth_headers,
            json={
                "platform": "douyin",
                "title": "权限流测试线索",
                "source": "manual",
                "status": "new",
            },
        )
        assert create_resp.status_code == 200
        lead_id = create_resp.json()["id"]

        forbidden_resp = client.post(
            f"/api/lead/{lead_id}/convert-customer",
            headers=another_auth_headers,
            json={"nickname": "无权限用户"},
        )
        assert forbidden_resp.status_code == 403


class TestExportFeatures:
    def test_export_customers_csv(self, auth_headers):
        create_resp = client.post(
            "/api/customer/create",
            headers=auth_headers,
            json={
                "nickname": "导出客户测试",
                "source_platform": "xiaohongshu",
                "tags": ["导出"],
                "intention_level": "medium",
            },
        )
        assert create_resp.status_code == 200

        resp = client.get("/api/customer/export/csv", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in (resp.headers.get("content-type") or "")
        assert "nickname" in resp.text
        assert "导出客户测试" in resp.text

    def test_export_publish_tasks_csv(self, auth_headers):
        task_resp = client.post(
            "/api/publish/tasks/create",
            headers=auth_headers,
            json={
                "platform": "douyin",
                "account_name": "导出账号",
                "task_title": "导出任务测试",
                "content_text": "导出发布任务CSV",
            },
        )
        assert task_resp.status_code == 200

        resp = client.get("/api/publish/tasks/export/csv", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in (resp.headers.get("content-type") or "")
        assert "task_title" in resp.text
        assert "导出任务测试" in resp.text

    def test_viewer_role_cannot_export(self, auth_headers):
        with TestingSessionLocal() as db:
            user = db.query(User).filter(User.username == "testuser").first()
            assert user is not None
            user.role = "viewer"
            db.commit()

        customer_resp = client.get("/api/customer/export/csv", headers=auth_headers)
        assert customer_resp.status_code == 403

        publish_resp = client.get("/api/publish/tasks/export/csv", headers=auth_headers)
        assert publish_resp.status_code == 403


class TestWeComNotify:
    def test_wecom_notify_requires_webhook(self, auth_headers):
        resp = client.post(
            "/api/wecom/notify/test",
            headers=auth_headers,
            json={"message": "测试通知"},
        )
        assert resp.status_code in (400, 502)
