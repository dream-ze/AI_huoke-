"""
Create a test user for development
"""

import sys
import os
import secrets
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services import UserService


def create_test_user():
    """Create a test user"""
    db: Session = SessionLocal()
    username = os.getenv("TEST_USER_USERNAME", "testuser")
    email = os.getenv("TEST_USER_EMAIL", "test@example.com")
    password = os.getenv("TEST_USER_PASSWORD")
    password_from_env = bool(password)

    if not password:
        password = secrets.token_urlsafe(18)
    
    try:
        user = UserService.create_user(
            db,
            username=username,
            email=email,
            password=password
        )
        print(f"✓ Test user created successfully!")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  ID: {user.id}")
        if password_from_env:
            print("  Password: loaded from TEST_USER_PASSWORD")
        else:
            print(f"  Password (generated): {password}")
            print("  Tip: set TEST_USER_PASSWORD for deterministic bootstrap")
    except Exception as e:
        message = str(e)
        if "already exists" in message:
            print("✓ Test user already exists, skipped")
        else:
            print(f"✗ Failed to create test user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
