"""全局异常处理器测试"""

import pytest
from app.core.exceptions import (
    AppException,
    BusinessError,
    DomainValidationError,
    ExternalAPIError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)


class TestExceptionClasses:
    """异常类测试"""

    def test_app_exception_is_base(self):
        """AppException应是基类"""
        assert issubclass(DomainValidationError, AppException)
        assert issubclass(BusinessError, Exception)

    def test_domain_validation_error(self):
        """DomainValidationError测试"""
        err = DomainValidationError("验证失败")
        assert isinstance(err, AppException)
        assert str(err) == "验证失败"

    def test_business_error_defaults(self):
        """BusinessError默认值测试"""
        err = BusinessError("测试错误")
        assert err.message == "测试错误"
        assert err.code == "BUSINESS_ERROR"
        assert err.status_code == 400
        assert err.detail is None

    def test_business_error_custom_values(self):
        """BusinessError自定义值测试"""
        err = BusinessError(message="自定义错误", code="CUSTOM_ERROR", status_code=418, detail="详细信息")
        assert err.message == "自定义错误"
        assert err.code == "CUSTOM_ERROR"
        assert err.status_code == 418
        assert err.detail == "详细信息"

    def test_not_found_error_without_identifier(self):
        """NotFoundError不带标识符"""
        err = NotFoundError("用户")
        assert "用户" in err.message
        assert "不存在" in err.message
        assert err.status_code == 404
        assert err.code == "NOT_FOUND"

    def test_not_found_error_with_identifier(self):
        """NotFoundError带标识符"""
        err = NotFoundError("文章", "123")
        assert "文章" in err.message
        assert "123" in err.message
        assert "不存在" in err.message
        assert err.status_code == 404
        assert err.code == "NOT_FOUND"

    def test_permission_denied_error_default(self):
        """PermissionDeniedError默认消息"""
        err = PermissionDeniedError()
        assert err.message == "权限不足"
        assert err.status_code == 403
        assert err.code == "PERMISSION_DENIED"

    def test_permission_denied_error_custom(self):
        """PermissionDeniedError自定义消息"""
        err = PermissionDeniedError("您无权删除此资源")
        assert err.message == "您无权删除此资源"
        assert err.status_code == 403
        assert err.code == "PERMISSION_DENIED"

    def test_external_api_error_default(self):
        """ExternalAPIError默认消息"""
        err = ExternalAPIError("火山方舟")
        assert "火山方舟" in err.message
        assert err.status_code == 502
        assert err.code == "EXTERNAL_API_ERROR"

    def test_external_api_error_custom(self):
        """ExternalAPIError自定义消息"""
        err = ExternalAPIError("OpenAI", "请求超时")
        assert "OpenAI" in err.message
        assert "请求超时" in err.message
        assert err.status_code == 502
        assert err.code == "EXTERNAL_API_ERROR"

    def test_rate_limit_error_default(self):
        """RateLimitError默认消息"""
        err = RateLimitError()
        assert err.message == "请求过于频繁"
        assert err.status_code == 429
        assert err.code == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_error_custom(self):
        """RateLimitError自定义消息"""
        err = RateLimitError("API调用超过限制，请稍后重试")
        assert err.message == "API调用超过限制，请稍后重试"
        assert err.status_code == 429
        assert err.code == "RATE_LIMIT_EXCEEDED"


class TestExceptionInheritance:
    """异常继承关系测试"""

    def test_business_error_hierarchy(self):
        """BusinessError子类关系测试"""
        assert issubclass(NotFoundError, BusinessError)
        assert issubclass(PermissionDeniedError, BusinessError)
        assert issubclass(ExternalAPIError, BusinessError)
        assert issubclass(RateLimitError, BusinessError)

    def test_catch_as_business_error(self):
        """可以捕获为BusinessError"""
        errors = [NotFoundError("资源"), PermissionDeniedError(), ExternalAPIError("服务"), RateLimitError()]

        for err in errors:
            assert isinstance(err, BusinessError)
            assert isinstance(err, Exception)


class TestExceptionUsage:
    """异常使用场景测试"""

    def test_raise_not_found(self):
        """抛出NotFoundError"""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("订单", "ORD-001")

        assert "订单" in str(exc_info.value)
        assert "ORD-001" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    def test_raise_permission_denied(self):
        """抛出PermissionDeniedError"""
        with pytest.raises(PermissionDeniedError) as exc_info:
            raise PermissionDeniedError("需要管理员权限")

        assert exc_info.value.status_code == 403

    def test_raise_external_api_error(self):
        """抛出ExternalAPIError"""
        with pytest.raises(ExternalAPIError) as exc_info:
            raise ExternalAPIError("支付网关", "连接超时")

        assert exc_info.value.status_code == 502
        assert "支付网关" in str(exc_info.value)

    def test_catch_and_check_type(self):
        """捕获并检查类型"""
        try:
            raise NotFoundError("用户", "123")
        except BusinessError as e:
            assert isinstance(e, NotFoundError)
            assert e.status_code == 404
