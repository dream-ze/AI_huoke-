"""
Example API usage / Testing
"""

import requests
import json
import os
from typing import Optional

BASE_URL = "http://localhost:8000"
TEST_PASSWORD = os.getenv("TEST_API_PASSWORD", "StrongPass_ChangeMe_2026!")

# Global token for maintaining session
token: Optional[str] = None


def register(username: str, email: str, password: str):
    """Register a new user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password
        }
    )
    print(f"Register: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()


def login(username: str, password: str):
    """Login user and get token"""
    global token
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "username": username,
            "password": password
        }
    )
    print(f"Login: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    token = data.get("access_token")
    return data


def get_headers():
    """Get request headers with auth token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_content(title: str, content: str, platform: str = "xiaohongshu"):
    """Create content asset"""
    response = requests.post(
        f"{BASE_URL}/api/v2/collect/ingest-page",
        headers=get_headers(),
        json={
            "source_type": "manual_link",
            "platform": platform,
            "content_type": "post",
            "title": title,
            "content_text": content,
            "tags": ["marketing", "content"],
        }
    )
    print(f"Create Content: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()


def check_compliance(content: str):
    """Check content compliance"""
    response = requests.post(
        f"{BASE_URL}/api/compliance/check",
        headers=get_headers(),
        json={
            "content": content,
            "content_type": "post"
        }
    )
    print(f"Compliance Check: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()


def list_contents():
    """List user's contents"""
    response = requests.get(
        f"{BASE_URL}/api/v2/materials",
        headers=get_headers()
    )
    print(f"List Contents: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()


def get_dashboard_summary():
    """Get dashboard summary"""
    response = requests.get(
        f"{BASE_URL}/api/dashboard/summary",
        headers=get_headers()
    )
    print(f"Dashboard Summary: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()


def create_customer(nickname: str, source_platform: str):
    """Create customer"""
    response = requests.post(
        f"{BASE_URL}/api/customer/create",
        headers=get_headers(),
        json={
            "nickname": nickname,
            "source_platform": source_platform,
            "intention_level": "medium",
            "tags": ["potential", "follow-up"]
        }
    )
    print(f"Create Customer: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return response.json()


if __name__ == "__main__":
    print("=" * 50)
    print("智获客 API 测试脚本")
    print("=" * 50 + "\n")
    
    # Test flow
    print("1. 注册用户")
    register("testuser1", "test1@example.com", TEST_PASSWORD)
    
    print("\n2. 登录")
    login("testuser1", TEST_PASSWORD)
    
    print("\n3. 创建内容")
    content_data = create_content(
        title="如何快速提升销售业绩",
        content="这是一篇关于销售技巧的内容。通过这些方法可以有效提升业绩。我们有专业的团队可以帮助你。",
        platform="xiaohongshu"
    )
    
    print("\n4. 合规检查")
    check_compliance("我们保证100%通过审核，这个产品是包过的，秒批！")
    
    print("\n5. 列表内容")
    list_contents()
    
    print("\n6. 创建客户")
    create_customer("张三", "xiaohongshu")
    
    print("\n7. 获取仪表板")
    get_dashboard_summary()
