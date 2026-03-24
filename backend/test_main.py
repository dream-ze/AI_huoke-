"""
Pytest test suite
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.core.database import Base, get_db
from app.models import User


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_login(self, test_db):
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": TEST_PASSWORD
            }
        )
        
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestContent:
    def test_create_content(self, auth_headers, test_db):
        response = client.post(
            "/api/content/create",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "content_type": "post",
                "title": "Test Content",
                "content": "This is test content"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Content"


class TestCompliance:
    def test_compliance_check(self, auth_headers):
        response = client.post(
            "/api/compliance/check",
            headers=auth_headers,
            json={
                "content": "这个产品100%通过！包过秒批！"
            }
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

    def test_v1_collect_parse_link_invalid_url(self, auth_headers):
        response = client.post(
            "/api/v1/collect/parse-link",
            headers=auth_headers,
            json={"url": "invalid-url"},
        )
        assert response.status_code == 400

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

    def test_v1_plugin_collect_syncs_to_content_and_insight(self, auth_headers):
        response = client.post(
            "/api/v1/ai/plugin/collect",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "插件采集测试",
                "content": "这是从插件采集的正文内容，用于验证自动入库。",
                "author": "测试作者",
                "tags": ["插件", "自动入库"],
                "comments_json": [{"text": "第一条评论"}],
                "url": "https://example.com/plugin-sync-test",
                "heat_score": 92,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["synced_content_asset_id"] is not None
        assert data["synced_insight_item_id"] is not None

        content_resp = client.get("/api/content/list", headers=auth_headers)
        assert content_resp.status_code == 200
        assert any(item["title"] == "插件采集测试" for item in content_resp.json())

        insight_resp = client.get("/api/insight/list", headers=auth_headers)
        assert insight_resp.status_code == 200
        assert any(item["title"] == "插件采集测试" for item in insight_resp.json())

    def test_v1_inbox_promote_workflow(self, auth_headers):
        create_resp = client.post(
            "/api/v1/inbox/create",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "content_type": "post",
                "title": "收件箱流程测试",
                "content": "这是一条先进入收件箱、再入素材库的测试内容。",
                "source_type": "paste",
            },
        )
        assert create_resp.status_code == 200
        inbox_id = create_resp.json()["id"]

        analyze_resp = client.post(
            f"/api/v1/inbox/{inbox_id}/analyze",
            headers=auth_headers,
        )
        assert analyze_resp.status_code == 200
        assert analyze_resp.json()["status"] == "analyzed"

        promote_resp = client.post(
            f"/api/v1/inbox/{inbox_id}/promote",
            headers=auth_headers,
        )
        assert promote_resp.status_code == 200
        promote_data = promote_resp.json()
        assert promote_data["content_asset_id"] is not None
        assert promote_data["insight_item_id"] is not None

        inbox_list_resp = client.get("/api/v1/inbox/list", headers=auth_headers)
        assert inbox_list_resp.status_code == 200
        assert any(item["id"] == inbox_id and item["status"] == "imported" for item in inbox_list_resp.json())

    def test_v1_collect_intake_to_inbox_with_dedupe_hint(self, auth_headers):
        first = client.post(
            "/api/v1/collect/intake",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "source_url": "https://example.com/post/abc?utm=1",
                "content_type": "post",
                "title": "统一采集入口测试1",
                "content": "第一条内容",
                "source_type": "mobile_share",
            },
        )
        assert first.status_code == 200
        assert first.json()["dedupe_hit"] is False

        second = client.post(
            "/api/v1/collect/intake",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "source_url": "https://example.com/post/abc?utm=2",
                "content_type": "post",
                "title": "统一采集入口测试2",
                "content": "第二条内容",
                "source_type": "wechat_forward",
            },
        )
        assert second.status_code == 200
        assert second.json()["dedupe_hit"] is True
        assert len(second.json()["duplicate_ids"]) >= 1

    def test_v1_collect_intake_requires_auth(self, test_db):
        resp = client.post(
            "/api/v1/collect/intake",
            json={
                "platform": "xiaohongshu",
                "title": "未授权测试",
                "content": "无 token",
                "source_type": "mobile_share",
            },
        )
        assert resp.status_code in (401, 403)

    def test_v1_collect_intake_invalid_source_type(self, auth_headers):
        resp = client.post(
            "/api/v1/collect/intake",
            headers=auth_headers,
            json={
                "platform": "xiaohongshu",
                "title": "非法来源",
                "content": "非法 source_type",
                "source_type": "unknown_source",
            },
        )
        assert resp.status_code == 422

    def test_v1_inbox_batch_actions_and_dedupe_preview(self, auth_headers):
        created_ids = []
        for idx in range(2):
            create_resp = client.post(
                "/api/v1/inbox/create",
                headers=auth_headers,
                json={
                    "platform": "douyin",
                    "source_url": "https://example.com/inbox-dup/1",
                    "content_type": "post",
                    "title": f"批量处理测试{idx}",
                    "content": "测试批量处理与去重预览",
                    "source_type": "paste",
                },
            )
            assert create_resp.status_code == 200
            created_ids.append(create_resp.json()["id"])

        dedupe_resp = client.get("/api/v1/inbox/dedupe/preview", headers=auth_headers)
        assert dedupe_resp.status_code == 200
        assert dedupe_resp.json()["total_duplicates"] >= 2

        # 获取当前用户 ID（测试中第一个注册的用户 ID 为 1）
        assign_resp = client.post(
            "/api/v1/inbox/batch-actions/assign",
            headers=auth_headers,
            json={
                "inbox_ids": created_ids,
                "assignee_user_id": 1,
                "note_template": "优先处理",
            },
        )
        assert assign_resp.status_code == 200
        assert assign_resp.json()["success"] == 2

        discard_resp = client.post(
            "/api/v1/inbox/batch-actions/discard",
            headers=auth_headers,
            json={
                "inbox_ids": created_ids,
                "review_note": "重复内容，暂不入库",
            },
        )
        assert discard_resp.status_code == 200
        assert discard_resp.json()["success"] == 2


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
