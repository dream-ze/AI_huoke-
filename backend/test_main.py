"""
Pytest test suite
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from app.core.database import Base, get_db


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
TEST_PASSWORD = "StrongPass_ChangeMe_2026!"


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
    @pytest.fixture
    def auth_headers(self, test_db):
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": TEST_PASSWORD
            }
        )
        
        resp = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": TEST_PASSWORD
            }
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

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
    def test_compliance_check(self, test_db):
        response = client.post(
            "/api/compliance/check",
            json={
                "content": "这个产品100%通过！包过秒批！"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] is not None
