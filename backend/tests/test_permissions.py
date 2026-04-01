"""RBAC权限控制测试"""

import pytest
from app.core.permissions import ROLE_PERMISSIONS, Role, has_permission


class TestRoleEnum:
    """角色枚举测试"""

    def test_role_admin_value(self):
        """admin角色值"""
        assert Role.ADMIN.value == "admin"

    def test_role_operator_value(self):
        """operator角色值"""
        assert Role.OPERATOR.value == "operator"

    def test_role_viewer_value(self):
        """viewer角色值"""
        assert Role.VIEWER.value == "viewer"

    def test_role_is_string_enum(self):
        """Role继承自str和Enum"""
        assert isinstance(Role.ADMIN, str)
        assert Role.ADMIN == "admin"  # 可以直接比较字符串


class TestPermissionMatrix:
    """权限矩阵测试"""

    def test_admin_has_all_permissions(self):
        """admin应具有所有权限（通过*通配符）"""
        assert has_permission("admin", "content:read")
        assert has_permission("admin", "content:write")
        assert has_permission("admin", "content:delete")
        assert has_permission("admin", "knowledge:delete")
        assert has_permission("admin", "any:permission")

    def test_operator_has_defined_permissions(self):
        """operator应具有权限矩阵中定义的权限"""
        assert has_permission("operator", "content:read")
        assert has_permission("operator", "content:write")
        assert has_permission("operator", "content:delete")
        assert has_permission("operator", "material:read")
        assert has_permission("operator", "material:write")
        assert has_permission("operator", "knowledge:read")
        assert has_permission("operator", "lead:read")
        assert has_permission("operator", "customer:write")

    def test_operator_missing_permissions(self):
        """operator不应具有未定义的权限"""
        # operator没有 knowledge:delete
        assert not has_permission("operator", "knowledge:delete")
        # operator没有 insight:write
        assert not has_permission("operator", "insight:write")

    def test_viewer_read_only(self):
        """viewer只读权限"""
        # 读权限
        assert has_permission("viewer", "content:read")
        assert has_permission("viewer", "material:read")
        assert has_permission("viewer", "knowledge:read")
        assert has_permission("viewer", "lead:read")
        assert has_permission("viewer", "customer:read")
        assert has_permission("viewer", "generation:read")
        assert has_permission("viewer", "publish:read")
        assert has_permission("viewer", "insight:read")
        assert has_permission("viewer", "compliance:read")

        # 无写权限
        assert not has_permission("viewer", "content:write")
        assert not has_permission("viewer", "content:delete")
        assert not has_permission("viewer", "material:write")
        assert not has_permission("viewer", "knowledge:write")
        assert not has_permission("viewer", "lead:write")

    def test_invalid_role(self):
        """无效角色应返回False"""
        assert not has_permission("invalid_role", "content:read")
        assert not has_permission("superuser", "content:delete")
        # 空字符串角色被视为falsy，默认为viewer，所以有read权限
        assert has_permission("", "content:read")  # 空字符串默认为viewer
        assert not has_permission("", "content:write")  # viewer无写权限

    def test_unknown_permission(self):
        """未知权限测试"""
        assert not has_permission("viewer", "unknown:permission")
        assert not has_permission("operator", "unknown:action")


class TestHasPermissionFunction:
    """has_permission函数测试"""

    def test_case_insensitive_role(self):
        """角色应不区分大小写"""
        assert has_permission("ADMIN", "content:read")
        assert has_permission("Admin", "content:write")
        assert has_permission("VIEWER", "content:read")
        assert not has_permission("VIEWER", "content:write")

    def test_null_role_defaults_to_viewer(self):
        """空角色默认为viewer（只读）"""
        assert has_permission(None, "content:read")
        assert not has_permission(None, "content:write")

    def test_permission_matrix_structure(self):
        """权限矩阵结构测试"""
        # 验证ROLE_PERMISSIONS包含所有角色
        assert Role.ADMIN in ROLE_PERMISSIONS
        assert Role.OPERATOR in ROLE_PERMISSIONS
        assert Role.VIEWER in ROLE_PERMISSIONS

    def test_admin_has_wildcard(self):
        """admin应包含通配符权限"""
        admin_perms = ROLE_PERMISSIONS.get(Role.ADMIN, set())
        assert "*" in admin_perms


class TestPermissionHierarchy:
    """权限层级测试"""

    def test_permission_inheritance_simulation(self):
        """模拟权限继承：admin > operator > viewer"""
        # viewer可以读的权限，operator也可以读
        viewer_perms = ROLE_PERMISSIONS.get(Role.VIEWER, set())
        operator_perms = ROLE_PERMISSIONS.get(Role.OPERATOR, set())

        # operator应包含viewer的所有权限
        for perm in viewer_perms:
            assert perm in operator_perms or has_permission("operator", perm)

    def test_operator_more_permissions_than_viewer(self):
        """operator应比viewer有更多权限"""
        viewer_perms = ROLE_PERMISSIONS.get(Role.VIEWER, set())
        operator_perms = ROLE_PERMISSIONS.get(Role.OPERATOR, set())

        assert len(operator_perms) > len(viewer_perms)


class TestRolePermissionsContent:
    """各角色权限内容详细测试"""

    def test_operator_permissions_content(self):
        """operator权限内容检查"""
        perms = ROLE_PERMISSIONS.get(Role.OPERATOR, set())

        # 内容权限
        assert "content:read" in perms
        assert "content:write" in perms
        assert "content:delete" in perms

        # 素材权限
        assert "material:read" in perms
        assert "material:write" in perms
        assert "material:delete" in perms

        # 知识库权限（无delete）
        assert "knowledge:read" in perms
        assert "knowledge:write" in perms
        assert "knowledge:delete" not in perms

    def test_viewer_permissions_content(self):
        """viewer权限内容检查"""
        perms = ROLE_PERMISSIONS.get(Role.VIEWER, set())

        # 全部是read权限
        for perm in perms:
            assert ":read" in perm, f"viewer权限应只包含read: {perm}"

        # 应有常见资源的read权限
        expected_reads = [
            "content:read",
            "material:read",
            "knowledge:read",
            "lead:read",
            "customer:read",
            "generation:read",
            "publish:read",
            "insight:read",
            "compliance:read",
        ]
        for perm in expected_reads:
            assert perm in perms, f"viewer应有权限: {perm}"
