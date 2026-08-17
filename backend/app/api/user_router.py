"""
用户管理路由

提供用户 CRUD 接口，系统管理员可管理所有用户。
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import get_current_user, require_admin, get_client_ip
from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import Role
from app.services import user_service
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserListOut, PaginatedResponse, RoleBrief

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/roles", summary="角色列表")
async def list_roles(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """获取所有角色列表（管理员权限）"""
    result = await session.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()
    return [RoleBrief.model_validate(r) for r in roles]


@router.get("/roles/simple", summary="简化角色列表（所有登录用户可访问）")
async def list_roles_simple(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取角色列表（简化版，用于上传时授权选择，所有登录用户可访问）"""
    result = await session.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()
    return [{"id": r.id, "name": r.name, "code": r.code} for r in roles]


@router.get("/", summary="用户列表")
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    keyword: str | None = Query(None, description="搜索关键词"),
    department_id: int | None = Query(None, description="部门ID筛选"),
    role_id: int | None = Query(None, description="角色ID筛选"),
    is_active: bool | None = Query(None, description="状态筛选"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """分页查询用户列表（管理员权限）"""
    users, total = await user_service.list_users(
        session, page=page, page_size=page_size,
        keyword=keyword, department_id=department_id, role_id=role_id, is_active=is_active,
    )
    items = [UserListOut.model_validate(u) for u in users]
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.post("/", summary="创建用户")
async def create_user(
    user_data: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """创建新用户（管理员权限）"""
    ip_address = get_client_ip(request)
    user = await user_service.create_user(session, user_data, current_user.id, ip_address)
    return UserOut.model_validate(user)


@router.get("/me", summary="当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息"""
    from app.services.permission_service import get_user_effective_permissions, get_user_business_scopes

    role_names = []
    if current_user.role:
        role_names.append(current_user.role.name)
    for r in current_user.roles:
        if r.name not in role_names:
            role_names.append(r.name)

    result = UserOut.model_validate(current_user)
    result.permissions = get_user_effective_permissions(current_user)
    result.role_names = role_names
    result.business_scopes = get_user_business_scopes(current_user)
    return result


@router.get("/{user_id}", summary="用户详情")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """获取用户详细信息（管理员权限）"""
    user = await user_service.get_user_by_id(session, user_id)
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserOut.model_validate(user)


@router.put("/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """更新用户信息（管理员权限）"""
    ip_address = get_client_ip(request)
    user = await user_service.update_user(session, user_id, user_data, current_user.id, ip_address)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """彻底删除用户（管理员权限）"""
    ip_address = get_client_ip(request)
    await user_service.delete_user(session, user_id, current_user.id, ip_address)
    return {"detail": "用户已删除"}


@router.put("/{user_id}/reset-password", summary="重置用户密码")
async def reset_user_password(
    user_id: int,
    data: dict,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """重置用户密码（管理员权限）"""
    from fastapi import HTTPException

    new_password = data.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = get_password_hash(new_password)

    ip_address = get_client_ip(request)
    from app.models.audit_log import AuditLog
    log = AuditLog(
        user_id=current_user.id, action="reset_password",
        target_type="user", target_id=user_id,
        ip_address=ip_address, detail={"target_user": user.username},
    )
    session.add(log)
    await session.flush()
    return {"detail": "密码已重置"}


@router.put("/{user_id}/status", summary="切换用户状态")
async def toggle_user_status(
    user_id: int,
    data: dict,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """启用/禁用用户（管理员权限）"""
    from fastapi import HTTPException

    is_active = data.get("is_active")
    if is_active is None:
        raise HTTPException(status_code=400, detail="缺少 is_active 参数")

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态")

    user.is_active = is_active

    ip_address = get_client_ip(request)
    from app.models.audit_log import AuditLog
    log = AuditLog(
        user_id=current_user.id, action="toggle_status",
        target_type="user", target_id=user_id,
        ip_address=ip_address,
        detail={"target_user": user.username, "is_active": is_active},
    )
    session.add(log)
    await session.flush()
    return {"detail": "用户已" + ("启用" if is_active else "禁用")}