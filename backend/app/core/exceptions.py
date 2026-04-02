class AppException(Exception):
    """Base application exception for domain-level errors."""


class DomainValidationError(AppException):
    """Raised when business validation fails."""


class BusinessError(Exception):
    """业务逻辑错误基类"""

    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        status_code: int = 400,
        detail: str = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class NotFoundError(BusinessError):
    """资源不存在错误"""

    def __init__(self, resource: str, identifier: str = None):
        msg = f"{resource}不存在"
        if identifier:
            msg = f"{resource}({identifier})不存在"
        super().__init__(message=msg, code="NOT_FOUND", status_code=404)


class PermissionDeniedError(BusinessError):
    """权限不足错误"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, code="PERMISSION_DENIED", status_code=403)


class ExternalAPIError(BusinessError):
    """外部服务调用错误"""

    def __init__(self, service: str, message: str = "外部服务调用失败"):
        super().__init__(message=f"{service}: {message}", code="EXTERNAL_API_ERROR", status_code=502)


class RateLimitError(BusinessError):
    """
    请求频率限制错误

    """

    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED", status_code=429)
