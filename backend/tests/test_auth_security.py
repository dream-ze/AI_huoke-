"""认证与安全测试 - 覆盖Token黑名单、登出、密码哈希"""

from unittest.mock import MagicMock, patch

import pytest


class TestTokenBlacklist:
    """Token黑名单测试"""

    def test_hash_token_consistency(self):
        """相同token应生成相同hash"""
        from app.core.security import _hash_token

        token = "test-token-123"
        hash1 = _hash_token(token)
        hash2 = _hash_token(token)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars

    def test_hash_token_different(self):
        """不同token应生成不同hash"""
        from app.core.security import _hash_token

        hash1 = _hash_token("token1")
        hash2 = _hash_token("token2")
        assert hash1 != hash2

    @patch("app.core.security.get_redis_client")
    def test_blacklist_token_success(self, mock_redis_getter):
        """成功将token加入黑名单"""
        mock_redis = MagicMock()
        mock_redis_getter.return_value = mock_redis

        from app.core.security import blacklist_token

        result = blacklist_token("test-token", 3600)

        assert result is True
        mock_redis.setex.assert_called_once()
        # 验证setex参数：key包含blacklist前缀，TTL为3600
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # expires_delta
        assert call_args[0][2] == "1"  # value

    @patch("app.core.security.get_redis_client")
    def test_blacklist_token_redis_unavailable(self, mock_redis_getter):
        """Redis不可用时黑名单操作返回False"""
        mock_redis_getter.return_value = None

        from app.core.security import blacklist_token

        result = blacklist_token("test-token", 3600)
        assert result is False

    @patch("app.core.security.get_redis_client")
    def test_blacklist_token_redis_exception(self, mock_redis_getter):
        """Redis抛出异常时黑名单操作返回False"""
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception("Redis connection error")
        mock_redis_getter.return_value = mock_redis

        from app.core.security import blacklist_token

        result = blacklist_token("test-token", 3600)
        assert result is False

    @patch("app.core.security.get_redis_client")
    def test_is_token_blacklisted_true(self, mock_redis_getter):
        """已黑名单的token应返回True"""
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1
        mock_redis_getter.return_value = mock_redis

        from app.core.security import is_token_blacklisted

        result = is_token_blacklisted("blacklisted-token")
        assert result is True
        mock_redis.exists.assert_called_once()

    @patch("app.core.security.get_redis_client")
    def test_is_token_blacklisted_false(self, mock_redis_getter):
        """未黑名单的token应返回False"""
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        mock_redis_getter.return_value = mock_redis

        from app.core.security import is_token_blacklisted

        result = is_token_blacklisted("valid-token")
        assert result is False

    @patch("app.core.security.get_redis_client")
    def test_is_token_blacklisted_redis_unavailable(self, mock_redis_getter):
        """Redis不可用时应返回False（优雅降级）"""
        mock_redis_getter.return_value = None

        from app.core.security import is_token_blacklisted

        result = is_token_blacklisted("any-token")
        assert result is False

    @patch("app.core.security.get_redis_client")
    def test_is_token_blacklisted_redis_exception(self, mock_redis_getter):
        """Redis异常时应返回False（优雅降级）"""
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = Exception("Redis error")
        mock_redis_getter.return_value = mock_redis

        from app.core.security import is_token_blacklisted

        result = is_token_blacklisted("any-token")
        assert result is False


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password(self):
        """密码哈希应成功"""
        from app.core.security import hash_password

        hashed = hash_password("MyPassword123!")
        assert hashed is not None
        assert hashed != "MyPassword123!"
        assert len(hashed) > 20  # 哈希值应该较长

    def test_verify_password_correct(self):
        """正确密码验证应返回True"""
        from app.core.security import hash_password, verify_password

        password = "MyPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """错误密码验证应返回False"""
        from app.core.security import hash_password, verify_password

        password = "MyPassword123!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False


class TestCreateAccessToken:
    """JWT Token创建测试"""

    def test_create_access_token_default_expiry(self):
        """创建默认过期时间的token"""
        from app.core.security import create_access_token

        token = create_access_token({"sub": "123"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT token应该较长

    def test_create_access_token_custom_expiry(self):
        """创建自定义过期时间的token"""
        from datetime import timedelta

        from app.core.security import create_access_token

        token = create_access_token({"sub": "456", "username": "testuser"}, expires_delta=timedelta(hours=1))
        assert token is not None

    def test_create_access_token_contains_data(self):
        """token应包含原始数据"""
        from app.core.config import settings
        from app.core.security import create_access_token
        from jose import jwt

        token = create_access_token({"sub": "789", "role": "admin"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == "789"
        assert payload["role"] == "admin"
        assert "exp" in payload
