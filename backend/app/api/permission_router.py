"""权限管理 API 路由 — 角色驱动"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.api.deps import require_permission, get_current_user, get_client_ip
from app.models.user import User
from app.models.role import Role
from app.models.document import Document, DocumentPermission
from app.models.category import Category
from app.schemas.permission import (
    DocPermissionCreate, DocPermissionOut,
    CatPermissionCreate, CatPermissionOut,
    BatchPermissionCreate,
)
from app.services import permission_service
from app.services.menu_function_tree import get_menu_function_tree, translate_permission_codes
from app.models.audit_log import AuditLog


router = APIRouter(prefix="/permissions", tags=["权限管理"])

# ── 菜单功能树 ────────────────────────────────────────────

@router.get("/menu-tree", summary="获取菜单功能树")
async def get_menu_tree(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """返回菜单-功能树，所有已登录用户可访问（用于渲染侧边栏）"""
    return {"tree": get_menu_function_tree()}


# ── 角色菜单功能权限 ──────────────────────────────────────

@router.get("/role-permissions", summary="获取角色的菜单功能权限")
async def get_role_permissions(
    role_id: int = Query(..., description="角色 ID"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_menu_permissions")),
):
    """返回指定角色的显式权限与业务默认权限"""
    return await permission_service.get_role_permissions_with_inherited(session, role_id)


@router.put("/role-permissions", summary="保存角色的菜单功能权限")
async def save_role_permissions(
    request: Request,
    data: dict = Body(..., description="{ role_id, permission_codes, expected_version }"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_menu_permissions")),
):
    """保存单个角色的菜单功能权限"""
    from app.models.role import Role

    role_id = data.get("role_id")
    permission_codes = data.get("permission_codes", [])
    expected_version = data.get("expected_version")

    if not role_id:
        raise HTTPException(status_code=400, detail="缺少 role_id")

    # 校验当前用户是否有 manage_menu_permissions
    if not current_user.is_superuser and "manage_menu_permissions" not in permission_service.get_user_effective_permissions(current_user):
        raise HTTPException(status_code=403, detail="没有管理菜单功能权限的权限")

    result = await permission_service.save_role_permissions(
        session, role_id, permission_codes, current_user.id, expected_version
    )

    # 写入审计日志
    ip_address = get_client_ip(request)
    role_name = "未知角色"
    if role_id:
        from app.models.role import Role
        role_obj = await session.get(Role, role_id)
        if role_obj:
            role_name = role_obj.name
    detail = {
        "操作": "修改菜单功能权限",
        "角色": role_name,
        "新增权限": translate_permission_codes(result["granted"]),
        "移除权限": translate_permission_codes(result["revoked"]),
        "版本": result["new_version"],
    }
    audit = AuditLog(
        user_id=current_user.id,
        action="update_role_menu_permissions",
        target_type="role",
        target_id=role_id,
        ip_address=ip_address,
        detail=detail,
    )
    session.add(audit)
    await session.flush()

    return {"detail": "保存成功", **result}


# ── 权限矩阵 — 按角色查看/编辑 ─────────────────────────────

@router.get("/matrix", summary="获取权限矩阵数据")
async def get_permission_matrix(
    role_id: int | None = Query(None, description="角色 ID，不传则只返回角色列表"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """返回指定角色的文档权限矩阵数据（含全部角色列表）"""
    # 加载全部角色列表供前端下拉选择（只需登录即可获取角色列表）
    roles_result = await session.execute(select(Role.id, Role.name, Role.code).order_by(Role.id))
    roles = [{"id": r[0], "name": r[1], "code": r[2]} for r in roles_result.all()]

    if role_id is None:
        return {"roles": roles, "role": None, "categories": []}

    # 查看具体角色的文档权限需要 manage_doc_permissions
    if not current_user.is_superuser and "manage_doc_permissions" not in permission_service.get_user_effective_permissions(current_user):
        raise HTTPException(status_code=403, detail="没有管理文档权限的权限")

    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    categories = await permission_service.get_documents_for_role_matrix(session, role_id)
    return {
        "roles": roles,
        "role": {"id": role.id, "name": role.name, "code": role.code},
        "categories": categories,
    }


@router.put("/matrix", summary="保存权限矩阵")
async def save_permission_matrix(
    request: Request,
    data: dict = Body(..., description="权限矩阵数据: { role_id, entries: [{ doc_id, can_view, can_download, can_edit, can_print }] }"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    """批量保存指定角色的文档权限变更"""
    role_id = data.get("role_id")
    entries = data.get("entries", [])
    if not role_id:
        raise HTTPException(status_code=400, detail="缺少 role_id")

    changed_doc_ids = []
    saved_count = 0
    for entry in entries:
        doc_id = entry.get("doc_id")
        if not doc_id:
            continue

        stmt = select(DocumentPermission).where(
            DocumentPermission.document_id == doc_id,
            DocumentPermission.role_id == role_id,
        )
        result = await session.execute(stmt)
        perm = result.scalar_one_or_none()

        can_view = entry.get("can_view", False)
        can_download = entry.get("can_download", False)
        can_edit = entry.get("can_edit", False)
        can_print = entry.get("can_print", False)

        if perm:
            if not can_view and not can_download and not can_edit and not can_print:
                await session.delete(perm)
            else:
                perm.can_view = can_view
                perm.can_download = can_download
                perm.can_edit = can_edit
                perm.can_print = can_print
                perm.granted_by = current_user.id
        else:
            if can_view or can_download or can_edit or can_print:
                perm = DocumentPermission(
                    document_id=doc_id,
                    role_id=role_id,
                    can_view=can_view,
                    can_download=can_download,
                    can_edit=can_edit,
                    can_print=can_print,
                    granted_by=current_user.id,
                )
                session.add(perm)
        changed_doc_ids.append(doc_id)
        saved_count += 1

    # 写入审计日志（合并记录）
    if changed_doc_ids:
        ip_address = get_client_ip(request)
        role_name = "未知角色"
        role_obj = await session.get(Role, role_id)
        if role_obj:
            role_name = role_obj.name
        audit = AuditLog(
            user_id=current_user.id,
            action="batch_update_doc_permissions",
            target_type="document",
            target_id=0,
            ip_address=ip_address,
            detail={
                "操作": "批量修改文档权限",
                "角色": role_name,
                "涉及文档数": len(changed_doc_ids),
            },
        )
        session.add(audit)

    await session.flush()
    return {"detail": f"已保存 {saved_count} 条权限变更"}


# ── 文档级权限 ────────────────────────────────────────

@router.get("/documents/{doc_id}", summary="获取文档权限列表")
async def get_doc_permissions(
    doc_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    perms = await permission_service.get_doc_permissions(session, doc_id)
    items = []
    for p in perms:
        d = DocPermissionOut.model_validate(p)
        if p.user_id:
            d.user_name = getattr(p, '_user_name', None)
        if p.role_id:
            role = await session.get(Role, p.role_id)
            d.role_name = role.name if role else None
        items.append(d)
    return items


@router.post("/documents/batch", summary="批量授予文档权限")
async def grant_batch_doc_permission(
    doc_ids: list[int] = Query(...),
    data: BatchPermissionCreate = Body(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    """批量授予文档权限 — 对多个文档同时给多个用户/角色授权"""
    count = 0
    for doc_id in doc_ids:
        for user_id in data.user_ids:
            await permission_service.grant_doc_permission(
                session, doc_id, user_id, None,
                data.can_view, data.can_download, data.can_edit, current_user.id,
                can_print=data.can_print,
            )
            count += 1
        for role_id in data.role_ids:
            await permission_service.grant_doc_permission(
                session, doc_id, None, role_id,
                data.can_view, data.can_download, data.can_edit, current_user.id,
                can_print=data.can_print,
            )
            count += 1
    return {"detail": f"已为 {len(data.user_ids)} 个用户、{len(data.role_ids)} 个角色对 {len(doc_ids)} 个文档授权（共 {count} 条记录）"}


@router.post("/documents/{doc_id}", summary="授予文档权限")
async def grant_doc_permission(
    doc_id: int,
    data: DocPermissionCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    perm = await permission_service.grant_doc_permission(
        session, doc_id, data.user_id, data.role_id,
        data.can_view, data.can_download, data.can_edit, current_user.id,
        can_print=data.can_print,
    )
    return DocPermissionOut.model_validate(perm)


@router.delete("/documents/{perm_id}", summary="撤销文档权限")
async def revoke_doc_permission(
    perm_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    await permission_service.revoke_doc_permission(session, perm_id)
    return {"detail": "权限已撤销"}


# ── 分类级权限 ────────────────────────────────────────

@router.get("/categories/{category_id}", summary="获取分类权限列表")
async def get_category_permissions(
    category_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    perms = await permission_service.get_category_permissions(session, category_id)
    items = []
    for p in perms:
        d = CatPermissionOut.model_validate(p)
        d.category_name = p.category.name if p.category else None
        items.append(d)
    return items


@router.post("/categories", summary="授予分类权限")
async def grant_category_permission(
    data: CatPermissionCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    perm = await permission_service.grant_category_permission(
        session, data.user_id, data.role_id,
        data.category_id, data.can_edit, data.can_view, current_user.id,
    )
    return CatPermissionOut.model_validate(perm)


@router.delete("/categories/{perm_id}", summary="撤销分类权限")
async def revoke_category_permission(
    perm_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_doc_permissions")),
):
    await permission_service.revoke_category_permission(session, perm_id)
    return {"detail": "权限已撤销"}
