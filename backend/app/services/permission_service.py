"""权限管理业务逻辑 — 角色驱动"""
from sqlalchemy import select, and_, or_, insert, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.document import Document, DocumentPermission, CategoryPermission
from app.models.category import Category
from app.models.user import User

DEFAULT_PERMISSIONS = {
    "base": ["view_doc_list", "view_doc_detail", "download_doc", "print_doc"],
    # 已取消业务角色默认权限：upload_doc、modify_doc 等权限不再自动继承，
    # 全部由管理员在“权限矩阵”中按角色显式配置，可自由授予或取消
}


async def get_doc_permissions(session: AsyncSession, doc_id: int) -> list[DocumentPermission]:
    """获取文档的所有权限记录"""
    stmt = select(DocumentPermission).where(DocumentPermission.document_id == doc_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def grant_doc_permission(
    session: AsyncSession, doc_id: int, user_id: int | None, role_id: int | None,
    can_view: bool, can_download: bool, can_edit: bool, granted_by: int,
    can_print: bool = False,
) -> DocumentPermission:
    """授予/更新文档权限"""
    # 检查是否已存在
    conds = [DocumentPermission.document_id == doc_id]
    if user_id:
        conds.append(DocumentPermission.user_id == user_id)
    if role_id:
        conds.append(DocumentPermission.role_id == role_id)

    stmt = select(DocumentPermission).where(and_(*conds))
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.can_view = can_view
        existing.can_download = can_download
        existing.can_edit = can_edit
        existing.can_print = can_print
        existing.granted_by = granted_by
        await session.flush()
        return existing

    perm = DocumentPermission(
        document_id=doc_id,
        user_id=user_id,
        role_id=role_id,
        can_view=can_view,
        can_download=can_download,
        can_edit=can_edit,
        can_print=can_print,
        granted_by=granted_by,
    )
    session.add(perm)
    await session.flush()
    return perm


async def revoke_doc_permission(session: AsyncSession, perm_id: int) -> None:
    """撤销文档权限"""
    stmt = select(DocumentPermission).where(DocumentPermission.id == perm_id)
    result = await session.execute(stmt)
    perm = result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(status_code=404, detail="权限记录不存在")
    await session.delete(perm)
    await session.flush()


async def get_category_permissions(session: AsyncSession, category_id: int) -> list[CategoryPermission]:
    """获取分类的所有权限记录"""
    stmt = select(CategoryPermission).where(CategoryPermission.category_id == category_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def grant_category_permission(
    session: AsyncSession, user_id: int | None, role_id: int | None,
    category_id: int, can_edit: bool, can_view: bool, granted_by: int,
) -> CategoryPermission:
    """授予/更新分类权限"""
    conds = [CategoryPermission.category_id == category_id]
    if user_id:
        conds.append(CategoryPermission.user_id == user_id)
    if role_id:
        conds.append(CategoryPermission.role_id == role_id)

    stmt = select(CategoryPermission).where(and_(*conds))
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.can_edit = can_edit
        existing.can_view = can_view
        existing.granted_by = granted_by
        await session.flush()
        return existing

    perm = CategoryPermission(
        user_id=user_id,
        role_id=role_id,
        category_id=category_id,
        can_edit=can_edit,
        can_view=can_view,
        granted_by=granted_by,
    )
    session.add(perm)
    await session.flush()
    return perm


async def revoke_category_permission(session: AsyncSession, perm_id: int) -> None:
    """撤销分类权限"""
    stmt = select(CategoryPermission).where(CategoryPermission.id == perm_id)
    result = await session.execute(stmt)
    perm = result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(status_code=404, detail="权限记录不存在")
    await session.delete(perm)
    await session.flush()


def get_document_visibility_filter(user: User):
    """根据用户角色返回文档查询的可见性过滤条件（角色驱动）"""
    if user.is_superuser:
        return None

    role_ids = user.all_role_ids

    conditions = [
        # 上传者始终可见自己上传的文档（即使未选择授权角色）
        Document.uploaded_by == user.id,
        Document.category_id.in_(
            select(Category.id).where(Category.is_public == True)
        )
    ]

    if role_ids:
        conditions.append(
            Document.permissions.any(
                or_(
                    DocumentPermission.user_id == user.id,
                    DocumentPermission.role_id.in_(role_ids),
                )
            )
        )
        conditions.append(
            Document.category_id.in_(
                select(CategoryPermission.category_id).where(
                    or_(
                        CategoryPermission.user_id == user.id,
                        CategoryPermission.role_id.in_(role_ids),
                    )
                )
            )
        )
    else:
        conditions.append(Document.permissions.any(DocumentPermission.user_id == user.id))

    return or_(*conditions)


def can_user_edit_document(user: User, document: Document) -> bool:
    """判断用户是否有编辑某文档的权限（角色驱动）"""
    if user.is_superuser:
        return True
    if document.uploaded_by == user.id:
        return True

    role_ids = user.all_role_ids

    # 文档级权限
    for perm in document.permissions:
        if perm.user_id == user.id and perm.can_edit:
            return True
        if perm.role_id and perm.role_id in role_ids and perm.can_edit:
            return True
    return False


def can_user_download_document(user: User, document: Document) -> bool:
    """判断用户是否有下载某文档的权限（角色驱动）"""
    if user.is_superuser:
        return True
    if document.uploaded_by == user.id:
        return True

    # 公开分类的文档对登录用户默认可下载（前提：用户有 download_doc 默认权限）
    category = getattr(document, "category", None)
    if category and getattr(category, "is_public", False):
        return True

    role_ids = user.all_role_ids

    # 文档级权限
    for perm in document.permissions:
        if perm.user_id == user.id and perm.can_download:
            return True
        if perm.role_id and perm.role_id in role_ids and perm.can_download:
            return True

    # 分类级查看权限（拥有分类权限即视为可下载该分类下的文档）
    for cat_perm in getattr(category, "permissions", []) if category else []:
        if cat_perm.user_id == user.id and cat_perm.can_view:
            return True
        if cat_perm.role_id and cat_perm.role_id in role_ids and cat_perm.can_view:
            return True

    return False


def get_user_effective_permissions(user: User) -> list[str]:
    """获取用户的所有有效权限码（基础权限 + 角色显式权限，不再自动继承业务默认权限）"""
    all_perms = set()

    all_perms.update(DEFAULT_PERMISSIONS["base"])

    for r in user.roles:
        for p in r.permissions:
            all_perms.add(p.code)

    if user.role:
        for p in user.role.permissions:
            all_perms.add(p.code)

    return list(all_perms)


def get_user_business_scopes(user: User) -> list[str]:
    """获取用户拥有的所有业务范围（去重，仅业务角色）"""
    scopes = []
    for r in user.roles:
        if getattr(r, "is_business_role", False) and r.business_scope:
            if r.business_scope not in scopes:
                scopes.append(r.business_scope)
    if user.role and getattr(user.role, "is_business_role", False) and user.role.business_scope:
        if user.role.business_scope not in scopes:
            scopes.append(user.role.business_scope)
    return scopes


def user_has_any_business_scope(user: User) -> bool:
    """用户是否拥有业务角色（按业务范围）"""
    return len(get_user_business_scopes(user)) > 0


async def get_role_permissions_with_inherited(session: AsyncSession, role_id: int) -> dict:
    """获取角色的显式权限（业务角色不再继承默认权限，inherited_permissions 恒为空）"""
    from app.models.role import Role

    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    granted = []
    for p in role.permissions:
        granted.append(p.code)

    # 业务默认权限已取消：所有权限均需管理员在权限矩阵中显式配置
    inherited = []

    return {
        "role_id": role.id,
        "role_name": role.name,
        "is_business_role": role.is_business_role,
        "business_scope": role.business_scope,
        "permission_version": role.permission_version,
        "granted_permissions": granted,
        "inherited_permissions": inherited,
    }


async def save_role_permissions(
    session: AsyncSession,
    role_id: int,
    permission_codes: list[str],
    current_user_id: int,
    expected_version: int | None = None,
) -> dict:
    """保存角色的菜单功能权限，返回变更详情"""
    from app.models.role import Role, Permission, role_permission_table

    role = await session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 系统内置角色允许编辑权限，仅不允许删除角色本身

    # 乐观锁校验
    if expected_version is not None and role.permission_version != expected_version:
        raise HTTPException(
            status_code=409,
            detail=f"该角色权限已被他人修改，请刷新后重试（当前版本 {role.permission_version}，提交版本 {expected_version}）"
        )

    # 当前显式权限
    old_codes = {p.code for p in role.permissions}
    new_codes = set(permission_codes)

    # 计算变更
    granted = list(new_codes - old_codes)
    revoked = list(old_codes - new_codes)

    # 删除旧关联
    await session.execute(
        sa_delete(role_permission_table).where(role_permission_table.c.role_id == role_id)
    )

    # 插入新关联
    if new_codes:
        perm_result = await session.execute(
            select(Permission.id).where(Permission.code.in_(new_codes))
        )
        perm_ids = [row[0] for row in perm_result.all()]
        if perm_ids:
            await session.execute(
                insert(role_permission_table),
                [{"role_id": role_id, "permission_id": pid} for pid in perm_ids],
            )

    # 版本号 +1
    role.permission_version += 1
    await session.flush()

    return {
        "role_id": role_id,
        "granted": granted,
        "revoked": revoked,
        "new_version": role.permission_version,
    }


async def get_documents_for_role_matrix(session: AsyncSession, role_id: int) -> list[dict]:
    """获取指定角色的文档权限矩阵数据（按分类分组）"""
    cats_result = await session.execute(select(Category).order_by(Category.id))
    categories = list(cats_result.scalars().all())

    cat_docs = []
    for cat in categories:
        docs_result = await session.execute(
            select(Document)
            .where(Document.category_id == cat.id)
            .order_by(Document.created_at.desc())
            .limit(500)
        )
        docs = list(docs_result.scalars().all())

        doc_items = []
        for d in docs:
            perms_result = await session.execute(
                select(DocumentPermission).where(
                    DocumentPermission.document_id == d.id,
                    DocumentPermission.role_id == role_id,
                )
            )
            p = perms_result.scalar_one_or_none()
            doc_items.append({
                "id": d.id,
                "title": d.title,
                "doc_no": d.doc_no,
                "file_name": d.file_name,
                "can_view": p.can_view if p else False,
                "can_download": p.can_download if p else False,
                "can_edit": p.can_edit if p else False,
                "can_print": p.can_print if p else False,
                "perm_id": p.id if p else None,
            })

        cat_docs.append({
            "id": cat.id,
            "name": cat.name,
            "documents": doc_items,
        })

    # 无分类文档
    no_cat_result = await session.execute(
        select(Document)
        .where(Document.category_id.is_(None))
        .order_by(Document.created_at.desc())
        .limit(500)
    )
    no_cat_docs = list(no_cat_result.scalars().all())
    if no_cat_docs:
        no_cat_items = []
        for d in no_cat_docs:
            perms_result = await session.execute(
                select(DocumentPermission).where(
                    DocumentPermission.document_id == d.id,
                    DocumentPermission.role_id == role_id,
                )
            )
            p = perms_result.scalar_one_or_none()
            no_cat_items.append({
                "id": d.id,
                "title": d.title,
                "doc_no": d.doc_no,
                "file_name": d.file_name,
                "can_view": p.can_view if p else False,
                "can_download": p.can_download if p else False,
                "can_edit": p.can_edit if p else False,
                "can_print": p.can_print if p else False,
                "perm_id": p.id if p else None,
            })
        cat_docs.append({
            "id": None,
            "name": "未分类",
            "documents": no_cat_items,
        })

    return cat_docs