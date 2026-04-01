"""通用分页Schema

提供标准化的分页请求参数和响应格式，支持泛型类型。
"""

import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页请求参数

    用于标准化分页请求，支持页码和每页数量参数。
    """

    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")

    @property
    def offset(self) -> int:
        """计算数据库查询的offset值"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """返回每页限制数量"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应

    泛型分页响应类，可适配任意数据类型的分页返回。

    Example:
        ```python
        # 定义用户列表分页响应
        UserListResponse = PaginatedResponse[UserResponse]

        # 创建响应实例
        response = PaginatedResponse[UserResponse].create(
            items=user_list,
            total=100,
            page=1,
            page_size=20
        )
        ```
    """

    items: List[T] = Field(description="当前页数据列表")
    total: int = Field(ge=0, description="总记录数")
    page: int = Field(ge=1, description="当前页码")
    page_size: int = Field(ge=1, description="每页数量")
    pages: int = Field(ge=0, description="总页数")

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        """创建分页响应实例

        Args:
            items: 当前页数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页数量

        Returns:
            PaginatedResponse: 分页响应实例
        """
        pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


class CursorPaginationParams(BaseModel):
    """游标分页请求参数

    适用于大数据量的分页场景，避免深分页性能问题。
    """

    cursor: str = Field(default="", description="游标，空字符串表示第一页")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """游标分页响应

    支持游标分页的响应格式，包含下一页游标。
    """

    items: List[T] = Field(description="当前页数据列表")
    next_cursor: str = Field(default="", description="下一页游标，空字符串表示没有更多数据")
    has_more: bool = Field(description="是否还有更多数据")
    page_size: int = Field(ge=1, description="每页数量")
