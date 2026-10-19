"""
分类管理路由

提供分类 CRUD 接口。分类按 parent_id 组织成目录树：
- GET /tree            管理端：返回嵌套树（需 manage_categories 权限）
- GET /simple          文档管理侧边栏/上传选择：返回平铺列表 + 嵌套树，带各分类可见文档数
- GET /                分页平铺列表（兼容旧调用）
- POST / PUT / DELETE  增删改，含父子层级与环路校验
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import require_permission, get_current_user, get_client_ip
from app.models.user import User
from app.models.category import Category, CategoryDefaultRole
from app.models.role import Role
from app.models.audit_log import AuditLog
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryOut, CategoryTreeItem
from app.schemas.user import PaginatedResponse
from app.services.doc_service import get_category_doc_counts

router = APIRouter(prefix="/categories", tags=["文档分类"])

# 目录树最大层级（根节点 depth=0），防止误操作产生过深嵌套
MAX_CATEGORY_DEPTH = 8


# ── 内部工具函数 ────────────────────────────────────────────

async def _get_default_role_ids(session: AsyncSession, category_id: int) -> list[int]:
    """查询分类的默认授权角色ID列表"""
    stmt = select(CategoryDefaultRole.role_id).where(CategoryDefaultRole.category_id == category_id)
    rows = (await session.execute(stmt)).all()
    return [r[0] for r in rows]


async def _validate_role_ids(session: AsyncSession, role_ids: list[int]) -> None:
    """校验角色ID列表均存在，不存在的抛 400"""
    if not role_ids:
        return
    stmt = select(func.count()).select_from(Role).where(Role.id.in_(role_ids))
    count = (await session.execute(stmt)).scalar() or 0
    if count != len(set(role_ids)):
        raise HTTPException(status_code=400, detail="默认授权角色中存在不存在的角色ID")


async def _save_default_roles(
    session: AsyncSession,
    category_id: int,
    role_ids: list[int],
    created_by: int,
) -> list[int]:
    """全量覆盖式保存分类的默认授权角色，返回最新的角色ID列表"""
    await _validate_role_ids(session, role_ids)
    stmt = select(CategoryDefaultRole).where(CategoryDefaultRole.category_id == category_id)
    result = await session.execute(stmt)
    for existing in result.scalars().all():
        await session.delete(existing)
    for rid in dict.fromkeys(role_ids):
        session.add(CategoryDefaultRole(category_id=category_id, role_id=rid, created_by=created_by))
    await session.flush()
    return await _get_default_role_ids(session, category_id)


async def _attach_default_role_ids(session: AsyncSession, categories: list[Category]) -> dict[int, list[int]]:
    """批量查询分类的默认授权角色，返回 {category_id: [role_id]}"""
    if not categories:
        return {}
    cat_ids = [c.id for c in categories]
    stmt = select(CategoryDefaultRole.category_id, CategoryDefaultRole.role_id).where(
        CategoryDefaultRole.category_id.in_(cat_ids)
    )
    rows = (await session.execute(stmt)).all()
    mapping: dict[int, list[int]] = {cid: [] for cid in cat_ids}
    for cid, rid in rows:
        mapping[cid].append(rid)
    return mapping


async def _load_all_categories(session: AsyncSession) -> list[Category]:
    """按排序号、ID 加载全部分类（平铺，顺序即树中兄弟节点顺序）"""
    stmt = select(Category).order_by(Category.sort_order, Category.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _build_items(session: AsyncSession, categories: list[Category], current_user: User) -> list[CategoryOut]:
    """把 ORM 分类对象转成带文档数、路径、层级的响应项（平铺，顺序不变）"""
    doc_counts, _ = await get_category_doc_counts(session, current_user)
    default_roles = await _attach_default_role_ids(session, categories)

    items: list[CategoryOut] = []
    for c in categories:
        item = CategoryOut.model_validate(c)
        item.doc_count = doc_counts.get(c.id, 0)
        item.subtree_doc_count = item.doc_count
        item.default_role_ids = default_roles.get(c.id, [])
        items.append(item)

    _apply_paths_and_depth(items)
    _apply_subtree_counts(items)
    return items


def _apply_paths_and_depth(items: list[CategoryOut]) -> None:
    """填充每个节点的 depth 与完整路径（如「标准表单 / 国家标准」）"""
    by_id = {i.id: i for i in items}
    for item in items:
        names = [item.name]
        depth = 0
        parent_id = item.parent_id
        seen = {item.id}
        while parent_id and parent_id in by_id and parent_id not in seen:
            seen.add(parent_id)
            parent = by_id[parent_id]
            names.append(parent.name)
            depth += 1
            parent_id = parent.parent_id
        item.depth = depth
        item.path = " / ".join(reversed(names))


def _apply_subtree_counts(items: list[CategoryOut]) -> None:
    """把每个节点的文档数累加进所有祖先的 subtree_doc_count"""
    by_id = {i.id: i for i in items}
    for item in items:
        parent_id = item.parent_id
        seen = {item.id}
        while parent_id and parent_id in by_id and parent_id not in seen:
            seen.add(parent_id)
            parent = by_id[parent_id]
            parent.subtree_doc_count += item.doc_count
            parent_id = parent.parent_id


def _build_tree(items: list[CategoryOut]) -> list[CategoryTreeItem]:
    """把平铺列表按 parent_id 组装成嵌套树；找不到父节点的节点作为根节点处理"""
    by_id: dict[int, CategoryTreeItem] = {}
    for item in items:
        by_id[item.id] = CategoryTreeItem(**item.model_dump())

    roots: list[CategoryTreeItem] = []
    for item in items:
        node = by_id[item.id]
        parent = by_id.get(item.parent_id) if item.parent_id else None
        if parent is not None and parent is not node:
            parent.children.append(node)
        else:
            roots.append(node)
    return roots


async def _validate_parent(
    session: AsyncSession,
    parent_id: int | None,
    *,
    category_id: int | None = None,
) -> None:
    """校验上级分类：必须存在、不能是自己、不能是自己的后代、层级不能超限"""
    if parent_id is None:
        return
    if category_id is not None and parent_id == category_id:
        raise HTTPException(status_code=400, detail="上级分类不能是自身")

    parent = (await session.execute(select(Category).where(Category.id == parent_id))).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=400, detail="上级分类不存在")

    if category_id is not None:
        descendants = await _get_descendant_ids(session, category_id)
        if parent_id in descendants:
            raise HTTPException(status_code=400, detail="不能把分类移动到它自己的子分类下")

    parent_depth = await _get_depth(session, parent_id)
    if parent_depth + 1 > MAX_CATEGORY_DEPTH:
        raise HTTPException(status_code=400, detail=f"分类层级最多 {MAX_CATEGORY_DEPTH + 1} 级，不能再新增下级")


async def _get_depth(session: AsyncSession, category_id: int) -> int:
    """计算分类的层级（根节点为 0）"""
    rows = dict((await session.execute(select(Category.id, Category.parent_id))).all())
    depth = 0
    current = rows.get(category_id)
    seen = {category_id}
    while current and current in rows and current not in seen:
        seen.add(current)
        depth += 1
        current = rows.get(current)
    return depth


async def _get_descendant_ids(session: AsyncSession, category_id: int) -> set[int]:
    """获取分类的全部后代ID（广度遍历 parent_id）"""
    rows = (await session.execute(select(Category.id, Category.parent_id))).all()
    children_map: dict[int | None, list[int]] = {}
    for cid, pid in rows:
        children_map.setdefault(pid, []).append(cid)

    descendants: set[int] = set()
    stack = [category_id]
    while stack:
        current = stack.pop()
        for child in children_map.get(current, []):
            if child not in descendants:
                descendants.add(child)
                stack.append(child)
    return descendants


async def _ensure_unique_name(
    session: AsyncSession,
    name: str,
    parent_id: int | None,
    *,
    exclude_id: int | None = None,
) -> None:
    """同一层级下不允许重名分类"""
    stmt = select(Category.id).where(Category.name == name)
    stmt = stmt.where(Category.parent_id.is_(None)) if parent_id is None else stmt.where(Category.parent_id == parent_id)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    if (await session.execute(stmt)).first() is not None:
        raise HTTPException(status_code=400, detail="同一层级下已存在同名分类")


# ── 查询接口 ────────────────────────────────────────────────

@router.get("/tree", summary="分类树")
async def get_category_tree(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """获取分类目录树（嵌套结构，含每个节点的文档数与子树文档数）"""
    categories = await _load_all_categories(session)
    items = await _build_items(session, categories, current_user)
    return _build_tree(items)


@router.get("/", summary="分类列表")
async def list_categories(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """分页获取分类列表（平铺，带 parent_id 与完整路径）"""
    count_stmt = select(func.count()).select_from(Category)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = select(Category).order_by(Category.sort_order, Category.id).offset(offset).limit(page_size)
    result = await session.execute(stmt)
    categories = list(result.scalars().all())

    # 路径需要全量分类才能拼出来
    all_items = await _build_items(session, await _load_all_categories(session), current_user)
    page_ids = {c.id for c in categories}
    items = [i for i in all_items if i.id in page_ids]
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


# ── 增删改 ──────────────────────────────────────────────────

@router.post("/", summary="创建分类")
async def create_category(
    data: CategoryCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """创建新分类（可通过 parent_id 挂到某个分类下）"""
    code = data.code
    if not code:
        import re
        base = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', data.name)[:10]
        code = base
        stmt = select(Category).where(Category.code == code)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            suffix = 1
            while True:
                new_code = f"{code[:8]}_{suffix}"
                stmt = select(Category).where(Category.code == new_code)
                existing = (await session.execute(stmt)).scalar_one_or_none()
                if not existing:
                    code = new_code
                    break
                suffix += 1
    else:
        stmt = select(Category).where(Category.code == code)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="分类编码已存在")

    await _validate_parent(session, data.parent_id)
    await _ensure_unique_name(session, data.name, data.parent_id)

    category = Category(
        name=data.name,
        code=code,
        description=data.description,
        folder_path=data.folder_path,
        parent_id=data.parent_id,
        sort_order=data.sort_order,
        is_public=data.is_public,
        business_type=data.business_type,
    )
    session.add(category)
    await session.flush()

    # 默认授权角色
    default_role_ids = []
    if data.default_role_ids:
        default_role_ids = await _save_default_roles(session, category.id, data.default_role_ids, current_user.id)

    # 记录审计日志
    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="create",
        target_type="category", target_id=category.id,
        ip_address=ip_address,
        detail={"name": data.name, "code": data.code, "parent_id": data.parent_id, "default_role_ids": default_role_ids},
    )
    session.add(log)

    await session.refresh(category)
    all_items = await _build_items(session, await _load_all_categories(session), current_user)
    item = next((i for i in all_items if i.id == category.id), None) or CategoryOut.model_validate(category)
    item.default_role_ids = default_role_ids
    return item


@router.put("/{cat_id}", summary="更新分类")
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """更新分类信息（含移动到其它上级分类）"""
    stmt = select(Category).where(Category.id == cat_id)
    category = (await session.execute(stmt)).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

    update_data = data.model_dump(exclude_unset=True)
    default_role_ids_provided = "default_role_ids" in update_data
    default_role_ids = update_data.pop("default_role_ids", None)

    # parent_id 允许显式传 null（移到根层级），因此用 model_fields_set 判断是否提交
    parent_provided = "parent_id" in update_data
    new_parent_id = update_data.pop("parent_id", None) if parent_provided else category.parent_id

    if parent_provided:
        await _validate_parent(session, new_parent_id, category_id=cat_id)
        update_data["parent_id"] = new_parent_id

    if "name" in update_data and update_data["name"] != category.name:
        await _ensure_unique_name(
            session,
            update_data["name"],
            new_parent_id if parent_provided else category.parent_id,
            exclude_id=cat_id,
        )
    elif parent_provided and new_parent_id != category.parent_id:
        await _ensure_unique_name(session, category.name, new_parent_id, exclude_id=cat_id)

    for field, value in update_data.items():
        setattr(category, field, value)
    await session.flush()

    if default_role_ids_provided:
        default_role_ids = await _save_default_roles(session, cat_id, default_role_ids or [], current_user.id)
    else:
        default_role_ids = await _get_default_role_ids(session, cat_id)

    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="update",
        target_type="category", target_id=cat_id,
        ip_address=ip_address, detail={**update_data, "default_role_ids": default_role_ids},
    )
    session.add(log)

    await session.refresh(category)
    all_items = await _build_items(session, await _load_all_categories(session), current_user)
    item = next((i for i in all_items if i.id == cat_id), None) or CategoryOut.model_validate(category)
    item.default_role_ids = default_role_ids
    return item


@router.delete("/{cat_id}", summary="删除分类")
async def delete_category(
    cat_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """删除分类（存在子分类时禁止删除，避免误删整棵子树）"""
    stmt = select(Category).where(Category.id == cat_id)
    category = (await session.execute(stmt)).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 检查是否有子分类
    child_count_stmt = select(func.count()).select_from(Category).where(Category.parent_id == cat_id)
    child_count = (await session.execute(child_count_stmt)).scalar() or 0
    if child_count > 0:
        raise HTTPException(status_code=400, detail=f"该分类下还有 {child_count} 个子分类，请先删除或移走子分类")

    # 检查是否有文档关联此分类
    from app.models.document import Document
    doc_count_stmt = select(func.count()).select_from(Document).where(Document.category_id == cat_id)
    doc_count = (await session.execute(doc_count_stmt)).scalar() or 0
    if doc_count > 0:
        raise HTTPException(status_code=400, detail=f"该分类下有 {doc_count} 个文档，无法删除")

    await session.delete(category)
    await session.flush()

    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="delete",
        target_type="category", target_id=cat_id,
        ip_address=ip_address,
    )
    session.add(log)

    return {"detail": "分类已删除"}


async def _granted_category_ids(
    session: AsyncSession, user: User, all_categories: list[Category],
) -> set[int]:
    """用户通过文档级/分类级显式授权即可访问的分类ID集合。

    与 permission_service 的可见性过滤保持同源语义：
    - 分类级授权：can_view 或 can_edit
    - 文档级授权：can_view 或 can_download（仅未删除文档）
    """
    from app.models.document import Document, DocumentPermission, CategoryPermission

    role_ids = user.all_role_ids
    cat_subject = [CategoryPermission.user_id == user.id]
    doc_subject = [DocumentPermission.user_id == user.id]
    if role_ids:
        cat_subject.append(CategoryPermission.role_id.in_(role_ids))
        doc_subject.append(DocumentPermission.role_id.in_(role_ids))

    ids: set[int] = set()

    cat_stmt = (
        select(CategoryPermission.category_id)
        .where(
            or_(CategoryPermission.can_view == True, CategoryPermission.can_edit == True),
            or_(*cat_subject),
        )
        .distinct()
    )
    ids.update(cid for (cid,) in (await session.execute(cat_stmt)).all() if cid)

    doc_stmt = (
        select(Document.category_id)
        .join(DocumentPermission, DocumentPermission.document_id == Document.id)
        .where(
            Document.is_deleted == False,
            Document.category_id.isnot(None),
            or_(DocumentPermission.can_view == True, DocumentPermission.can_download == True),
            or_(*doc_subject),
        )
        .distinct()
    )
    ids.update(cid for (cid,) in (await session.execute(doc_stmt)).all() if cid)

    known = {c.id for c in all_categories}
    return {cid for cid in ids if cid in known}


@router.get("/simple", summary="简化分类列表（所有登录用户可访问）")
async def list_categories_simple(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取分类列表（简化版，用于文档管理侧边栏、上传时选择，所有登录用户可访问）

    返回：
    - items: 平铺列表（含 parent_id / path / depth / doc_count / subtree_doc_count）
    - tree:  嵌套树（供侧边栏与树形选择器使用）
    - uncategorized_count: 未分类文档数

    显示规则：
    1. 管理员：显示所有分类
    2. 业务角色用户：显示公开分类 + 匹配业务范围的分类
    3. 普通用户：只显示公开分类

    可见分类的上级分类会作为「路径上下文」一并返回，保证树结构完整；
    上级本身不可见时标记 disabled，仅供展示不可选择。
    """
    from app.services.permission_service import get_user_business_scopes

    user_business_scopes = get_user_business_scopes(current_user)
    all_categories = await _load_all_categories(session)

    if current_user.is_superuser or 'doc_admin' in user_business_scopes:
        visible_ids = {c.id for c in all_categories}
    else:
        if user_business_scopes:
            visible_ids = {
                c.id for c in all_categories
                if c.is_public or (c.business_type and c.business_type in user_business_scopes)
            }
        else:
            visible_ids = {c.id for c in all_categories if c.is_public}
        # 显式授权（文档级 / 分类级）涉及的分类同样可见：
        # 管理员已把某分类下的文档授权给该用户或其角色时，侧边栏不应再隐藏该分类
        visible_ids |= await _granted_category_ids(session, current_user, all_categories)

    # 补齐祖先节点作为路径上下文
    by_id = {c.id: c for c in all_categories}
    context_ids: set[int] = set()
    for cid in list(visible_ids):
        parent_id = by_id[cid].parent_id
        seen = {cid}
        while parent_id and parent_id in by_id and parent_id not in seen:
            seen.add(parent_id)
            context_ids.add(parent_id)
            parent_id = by_id[parent_id].parent_id

    included_ids = visible_ids | context_ids
    included = [c for c in all_categories if c.id in included_ids]
    items = await _build_items(session, included, current_user)

    _, uncategorized_count = await get_category_doc_counts(session, current_user)
    disabled_ids = included_ids - visible_ids

    flat_items = [{
        "id": item.id,
        "name": item.name,
        "code": item.code,
        "parent_id": item.parent_id,
        "path": item.path,
        "depth": item.depth,
        "business_type": item.business_type,
        "default_role_ids": item.default_role_ids,
        "doc_count": item.doc_count,
        "subtree_doc_count": item.subtree_doc_count,
        "disabled": item.id in disabled_ids,
    } for item in items]

    return {
        "items": flat_items,
        "tree": _tree_to_dict(_build_tree(items), disabled_ids),
        "uncategorized_count": uncategorized_count,
    }


def _tree_to_dict(nodes: list[CategoryTreeItem], disabled_ids: set[int]) -> list[dict]:
    """把树节点转成前端友好的 dict，并标记不可选择的上下文节点"""
    result = []
    for node in nodes:
        result.append({
            "id": node.id,
            "name": node.name,
            "code": node.code,
            "parent_id": node.parent_id,
            "path": node.path,
            "depth": node.depth,
            "business_type": node.business_type,
            "default_role_ids": node.default_role_ids,
            "doc_count": node.doc_count,
            "subtree_doc_count": node.subtree_doc_count,
            "disabled": node.id in disabled_ids,
            "children": _tree_to_dict(node.children, disabled_ids),
        })
    return result
