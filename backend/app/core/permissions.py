"""
权限判断逻辑模块

提供基础的权限检查工具函数。
注意：路由层应优先使用 app.api.deps 中的 require_permission 依赖（调用 permission_service），
该模块仅提供基础的用户-权限直接判断能力。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


def has_permission(user: "User", permission_code: str) -> bool:
    """
    判断用户是否拥有指定权限。
    管理员默认拥有所有权限。
    同时检查单角色（user.role）和多角色（user.roles）关系。
    """
    if user.is_superuser:
        return True

    # 收集所有角色（兼容单角色和多角色系统）
    roles = set()
    if user.role is not None:
        roles.add(user.role)
    for r in getattr(user, 'roles', []) or []:
        roles.add(r)

    if not roles:
        return False

    for role in roles:
        for perm in getattr(role, 'permissions', []) or []:
            if perm.code == permission_code:
                return True
    return False


def has_any_permission(user: "User", permission_codes: list[str]) -> bool:
    """判断用户是否拥有指定权限列表中的任意一个。"""
    return any(has_permission(user, code) for code in permission_codes)
