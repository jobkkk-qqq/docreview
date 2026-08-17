"""
部门管理路由

提供部门 CRUD 接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import require_permission, get_client_ip
from app.models.user import User
from app.models.department import Department
from app.models.audit_log import AuditLog
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentOut
from app.schemas.user import PaginatedResponse

router = APIRouter(prefix="/departments", tags=["部门管理"])


async def _attach_user_counts(session: AsyncSession, departments: list[Department]) -> dict[int, int]:
    """批量查询部门下的用户数，返回 {department_id: count}"""
    if not departments:
        return {}
    dept_ids = [d.id for d in departments]
    stmt = (
        select(Department.id, func.count(User.id))
        .join(User, User.department_id == Department.id, isouter=True)
        .where(Department.id.in_(dept_ids))
        .group_by(Department.id)
    )
    rows = (await session.execute(stmt)).all()
    return {row[0]: row[1] for row in rows}


@router.get("/tree", summary="部门树")
async def get_department_tree(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_departments")),
):
    """获取部门列表（平铺，前端构建树）"""
    stmt = select(Department).order_by(Department.id)
    result = await session.execute(stmt)
    departments = list(result.scalars().all())
    user_counts = await _attach_user_counts(session, departments)
    items = []
    for d in departments:
        item = DepartmentOut.model_validate(d)
        item.user_count = user_counts.get(d.id, 0)
        items.append(item)
    return items


@router.get("/", summary="部门列表")
async def list_departments(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_departments")),
):
    """分页获取部门列表"""
    count_stmt = select(func.count()).select_from(Department)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = select(Department).order_by(Department.id).offset(offset).limit(page_size)
    result = await session.execute(stmt)
    departments = list(result.scalars().all())

    user_counts = await _attach_user_counts(session, departments)
    items = []
    for d in departments:
        item = DepartmentOut.model_validate(d)
        item.user_count = user_counts.get(d.id, 0)
        items.append(item)
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.post("/", summary="创建部门")
async def create_department(
    data: DepartmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_departments")),
):
    """创建新部门"""
    # 自动生成编码
    code = data.code
    if not code:
        import re
        base = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', data.name)[:10]
        code = base
        # 检查唯一性，如果有重复则加数字后缀
        stmt = select(Department).where(Department.code == code)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            suffix = 1
            while True:
                new_code = f"{code[:8]}_{suffix}"
                stmt = select(Department).where(Department.code == new_code)
                existing = (await session.execute(stmt)).scalar_one_or_none()
                if not existing:
                    code = new_code
                    break
                suffix += 1
    else:
        # 检查编码唯一性
        stmt = select(Department).where(Department.code == code)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="部门编码已存在")

    department = Department(
        name=data.name,
        code=code,
        description=data.description,
        manager_user_id=data.manager_user_id,
    )
    session.add(department)
    await session.flush()

    # 记录审计日志
    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="create",
        target_type="department", target_id=department.id,
        ip_address=ip_address,
        detail={"name": data.name, "code": code},
    )
    session.add(log)

    await session.refresh(department)
    return DepartmentOut.model_validate(department)


@router.put("/{dept_id}", summary="更新部门")
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_departments")),
):
    """更新部门信息"""
    stmt = select(Department).where(Department.id == dept_id)
    department = (await session.execute(stmt)).scalar_one_or_none()
    if department is None:
        raise HTTPException(status_code=404, detail="部门不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)
    await session.flush()

    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="update",
        target_type="department", target_id=dept_id,
        ip_address=ip_address, detail=update_data,
    )
    session.add(log)

    await session.refresh(department)
    return DepartmentOut.model_validate(department)


@router.delete("/{dept_id}", summary="删除部门")
async def delete_department(
    dept_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("manage_departments")),
):
    """删除部门"""
    stmt = select(Department).where(Department.id == dept_id)
    department = (await session.execute(stmt)).scalar_one_or_none()
    if department is None:
        raise HTTPException(status_code=404, detail="部门不存在")

    # 检查是否有用户关联此部门
    from app.models.user import User as UserModel
    user_count_stmt = select(func.count()).select_from(UserModel).where(UserModel.department_id == dept_id)
    user_count = (await session.execute(user_count_stmt)).scalar() or 0
    if user_count > 0:
        raise HTTPException(status_code=400, detail=f"该部门下有 {user_count} 个用户，无法删除")

    await session.delete(department)
    await session.flush()

    ip_address = get_client_ip(request)
    log = AuditLog(
        user_id=current_user.id, action="delete",
        target_type="department", target_id=dept_id,
        ip_address=ip_address,
    )
    session.add(log)

    return {"detail": "部门已删除"}