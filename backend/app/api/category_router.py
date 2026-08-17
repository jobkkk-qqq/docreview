"""
分类管理路由

提供分类 CRUD 接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import require_admin, require_permission, get_current_user, get_client_ip
from app.models.user import User
from app.models.category import Category
from app.models.audit_log import AuditLog
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryOut, CategoryTreeItem
from app.schemas.user import PaginatedResponse

router = APIRouter(prefix="/categories", tags=["文档分类"])


async def _attach_doc_counts(session: AsyncSession, categories: list[Category]) -> dict[int, int]:
    """批量查询分类下的文档数，返回 {category_id: count}"""
    if not categories:
        return {}
    from app.models.document import Document
    cat_ids = [c.id for c in categories]
    stmt = (
        select(Category.id, func.count(Document.id))
        .join(Document, Document.category_id == Category.id, isouter=True)
        .where(Category.id.in_(cat_ids))
        .group_by(Category.id)
    )
    rows = (await session.execute(stmt)).all()
    return {row[0]: row[1] for row in rows}


@router.get("/tree", summary="分类树")
async def get_category_tree(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """获取分类列表（平铺，前端构建树）"""
    stmt = select(Category).order_by(Category.sort_order, Category.id)
    result = await session.execute(stmt)
    categories = list(result.scalars().all())
    doc_counts = await _attach_doc_counts(session, categories)
    items = []
    for c in categories:
        item = CategoryOut.model_validate(c)
        item.doc_count = doc_counts.get(c.id, 0)
        items.append(item)
    return items


@router.get("/", summary="分类列表")
async def list_categories(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """分页获取分类列表"""
    count_stmt = select(func.count()).select_from(Category)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = select(Category).order_by(Category.sort_order, Category.id).offset(offset).limit(page_size)
    result = await session.execute(stmt)
    categories = list(result.scalars().all())

    doc_counts = await _attach_doc_counts(session, categories)
    items = []
    for c in categories:
        item = CategoryOut.model_validate(c)
        item.doc_count = doc_counts.get(c.id, 0)
        items.append(item)
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.post("/", summary="创建分类")
async def create_category(
    data: CategoryCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """创建新分类"""
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

    category = Category(
        name=data.name,
        code=code,
        description=data.description,
        folder_path=data.folder_path,
        sort_order=data.sort_order,
        is_public=data.is_public,
        business_type=data.business_type,
    )
    session.add(category)
    await session.flush()

    # 记录审计日志
    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="create",
        target_type="category", target_id=category.id,
        ip_address=ip_address,
        detail={"name": data.name, "code": data.code},
    )
    session.add(log)

    await session.refresh(category)
    return CategoryOut.model_validate(category)


@router.put("/{cat_id}", summary="更新分类")
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """更新分类信息"""
    stmt = select(Category).where(Category.id == cat_id)
    category = (await session.execute(stmt)).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    await session.flush()

    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="update",
        target_type="category", target_id=cat_id,
        ip_address=ip_address, detail=update_data,
    )
    session.add(log)

    await session.refresh(category)
    return CategoryOut.model_validate(category)


@router.delete("/{cat_id}", summary="删除分类")
async def delete_category(
    cat_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_categories")),
):
    """删除分类"""
    stmt = select(Category).where(Category.id == cat_id)
    category = (await session.execute(stmt)).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")

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


@router.get("/simple", summary="简化分类列表（所有登录用户可访问）")
async def list_categories_simple(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取分类列表（简化版，用于上传时选择，所有登录用户可访问）
    
    显示规则：
    1. 管理员：显示所有分类
    2. 业务角色用户：显示公开分类 + 匹配业务范围的分类
    3. 普通用户：只显示公开分类
    """
    from app.services.permission_service import get_user_business_scopes
    
    # 获取用户的业务范围
    user_business_scopes = get_user_business_scopes(current_user)
    
    # 构建查询条件
    if current_user.is_superuser:
        # 管理员：所有分类
        stmt = select(Category).order_by(Category.sort_order, Category.id)
    elif user_business_scopes:
        # 特殊处理：文档管理员（doc_admin）可以看到所有分类
        if 'doc_admin' in user_business_scopes:
            stmt = select(Category).order_by(Category.sort_order, Category.id)
        else:
            # 其他业务角色用户：公开分类 OR 匹配业务范围的分类
            from sqlalchemy import or_
            stmt = select(Category).where(
                or_(
                    Category.is_public == True,
                    Category.business_type.in_(user_business_scopes)
                )
            ).order_by(Category.sort_order, Category.id)
    else:
        # 普通用户：只显示公开分类
        stmt = select(Category).where(Category.is_public == True).order_by(Category.sort_order, Category.id)
    
    result = await session.execute(stmt)
    categories = list(result.scalars().all())
    
    items = []
    for c in categories:
        items.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "business_type": c.business_type,
        })
    return {"items": items}