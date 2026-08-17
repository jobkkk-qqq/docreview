"""角色管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, insert, delete as sa_delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import require_admin, get_client_ip
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import PaginatedResponse

router = APIRouter(prefix="/system", tags=["角色管理"])


def _role_out(role) -> dict:
    """将角色对象转为响应字典，权限数据已预加载"""
    perms = [{"id": p.id, "code": p.code, "name": p.name} for p in role.permissions]
    return {
        "id": role.id, "code": role.code, "name": role.name,
        "description": role.description, "is_system": role.is_system,
        "is_business_role": getattr(role, "is_business_role", False),
        "business_scope": getattr(role, "business_scope", None),
        "permissions": perms, "created_at": role.created_at,
    }


@router.get("/roles", summary="角色列表")
async def list_roles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """分页获取角色列表（管理员权限）"""
    from app.models.role import Role, user_role_table
    from app.models.user import User as UserModel

    count_stmt = select(func.count()).select_from(Role)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = (
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.id)
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    roles = result.unique().scalars().all()

    items = []
    for r in roles:
        cnt1 = (await session.execute(
            select(func.count()).select_from(UserModel).where(UserModel.role_id == r.id)
        )).scalar() or 0
        cnt2 = (await session.execute(
            select(func.count()).select_from(user_role_table).where(user_role_table.c.role_id == r.id)
        )).scalar() or 0
        user_count = max(cnt1, cnt2)

        item = _role_out(r)
        item["user_count"] = user_count
        items.append(item)

    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/roles/{role_id}", summary="角色详情")
async def get_role(
    role_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """获取角色详情（管理员权限）"""
    from app.models.role import Role

    stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    result = await session.execute(stmt)
    role = result.unique().scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return _role_out(role)


@router.post("/roles", summary="创建角色")
async def create_role(
    data: dict,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """创建新角色（管理员权限）"""
    from app.models.role import Role, Permission, role_permission_table

    name = data.get("name")
    code = data.get("code", "")
    if not name:
        raise HTTPException(status_code=400, detail="角色名称不能为空")

    existing = (await session.execute(
        select(Role).where(Role.name == name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="角色名称已存在")

    role = Role(
        name=name, code=code or name,
        description=data.get("description"), is_system=False,
        is_business_role=data.get("is_business_role", False),
        business_scope=data.get("business_scope"),
    )
    session.add(role)
    await session.flush()

    # 通过直接插入关联表来关联权限（避免 ORM relationship setter 触发 lazy load）
    permission_codes = data.get("permission_ids", [])
    perm_ids = []
    if permission_codes:
        if isinstance(permission_codes[0], str):
            perm_stmt = select(Permission.id).where(Permission.code.in_(permission_codes))
        else:
            perm_stmt = select(Permission.id).where(Permission.id.in_(permission_codes))
        perm_result = await session.execute(perm_stmt)
        perm_ids = [row[0] for row in perm_result.all()]

        if perm_ids:
            await session.execute(
                insert(role_permission_table),
                [{"role_id": role.id, "permission_id": pid} for pid in perm_ids],
            )
            await session.flush()

    # 用 selectinload 重新加载以获取完整权限数据
    await session.refresh(role)
    reload_stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role.id)
    result = await session.execute(reload_stmt)
    role = result.unique().scalar_one()

    # 审计日志
    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="create",
        target_type="role", target_id=role.id,
        ip_address=ip_address, detail={"name": name, "code": code},
    )
    session.add(log)
    await session.flush()

    return _role_out(role)


@router.put("/roles/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    data: dict,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """更新角色信息（管理员权限）"""
    from app.models.role import Role, Permission, role_permission_table

    stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    result = await session.execute(stmt)
    role = result.unique().scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    if "name" in data and data["name"]:
        new_name = data["name"]
        # 名称唯一性校验：排除当前角色自身
        duplicate = (await session.execute(
            select(Role).where(Role.name == new_name, Role.id != role_id)
        )).scalar_one_or_none()
        if duplicate:
            raise HTTPException(status_code=400, detail="角色名称已存在")
        role.name = new_name
    if "code" in data and data["code"]:
        role.code = data["code"]
    if "description" in data:
        role.description = data["description"]
    if "is_business_role" in data:
        role.is_business_role = data["is_business_role"]
    if "business_scope" in data:
        role.business_scope = data["business_scope"]

    # 更新权限：先删后插（避免 ORM relationship setter 触发 lazy load）
    if "permission_ids" in data and data["permission_ids"] is not None:
        permission_codes = data["permission_ids"]
        # 删除旧关联
        await session.execute(
            sa_delete(role_permission_table).where(role_permission_table.c.role_id == role_id)
        )
        # 插入新关联
        if permission_codes:
            if isinstance(permission_codes[0], str):
                perm_stmt = select(Permission.id).where(Permission.code.in_(permission_codes))
            else:
                perm_stmt = select(Permission.id).where(Permission.id.in_(permission_codes))
            perm_result = await session.execute(perm_stmt)
            perm_ids = [row[0] for row in perm_result.all()]
            if perm_ids:
                await session.execute(
                    insert(role_permission_table),
                    [{"role_id": role_id, "permission_id": pid} for pid in perm_ids],
                )
        await session.flush()
        # 重新加载权限数据
        await session.refresh(role)
        reload_stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        result = await session.execute(reload_stmt)
        role = result.unique().scalar_one()

    # 审计日志
    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="update",
        target_type="role", target_id=role.id,
        ip_address=ip_address, detail={"name": role.name},
    )
    session.add(log)
    await session.flush()

    return _role_out(role)


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """删除角色（管理员权限）"""
    from app.models.role import Role, user_role_table
    from app.models.user import User as UserModel

    stmt = select(Role).where(Role.id == role_id)
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")

    cnt1 = (await session.execute(
        select(func.count()).select_from(UserModel).where(UserModel.role_id == role_id)
    )).scalar() or 0
    cnt2 = (await session.execute(
        select(func.count()).select_from(user_role_table).where(user_role_table.c.role_id == role_id)
    )).scalar() or 0
    user_count = max(cnt1, cnt2)
    if user_count > 0:
        raise HTTPException(status_code=400, detail=f"该角色下还有 {user_count} 个用户，无法删除")

    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="delete",
        target_type="role", target_id=role.id,
        ip_address=ip_address, detail={"name": role.name},
    )
    session.add(log)

    await session.delete(role)
    await session.flush()
    return {"detail": "角色已删除"}