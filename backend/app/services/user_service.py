"""
用户管理业务逻辑服务
"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import user_role_table
from app.models.audit_log import AuditLog
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """根据ID查询用户。"""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    """根据用户名查询用户。"""
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    department_id: int | None = None,
    role_id: int | None = None,
    is_active: bool | None = None,
) -> tuple[list[User], int]:
    """分页查询用户列表。"""
    stmt = select(User).options(
        selectinload(User.department),
        selectinload(User.role),
        selectinload(User.roles),
    )
    count_stmt = select(func.count()).select_from(User)

    conditions = []
    if keyword:
        conditions.append(
            (User.username.ilike(f"%{keyword}%"))
            | (User.display_name.ilike(f"%{keyword}%"))
            | (User.email.ilike(f"%{keyword}%"))
        )
    if department_id:
        conditions.append(User.department_id == department_id)
    if role_id:
        conditions.append(User.role_id == role_id)
    if is_active is not None:
        conditions.append(User.is_active == is_active)

    for cond in conditions:
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    users = list(result.scalars().all())

    return users, total


async def create_user(session: AsyncSession, user_data: UserCreate, operator_id: int = 0, ip_address: str = "") -> User:
    """创建用户。"""
    existing = await get_user_by_username(session, user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        display_name=user_data.display_name,
        email=user_data.email,
        phone=user_data.phone,
        department_id=user_data.department_id,
        role_id=user_data.role_id,
    )
    session.add(user)
    await session.flush()

    # 处理多角色
    if user_data.role_ids:
        await _sync_user_roles(session, user.id, user_data.role_ids)

    # 预加载关系，确保返回的 user 可被 Pydantic 同步序列化
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.department),
            selectinload(User.role),
            selectinload(User.roles),
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one()

    # 记录审计日志
    await _create_audit_log(session, operator_id, "create", "user", user.id, ip_address)

    return user


async def update_user(
    session: AsyncSession,
    user_id: int,
    user_data: UserUpdate,
    operator_id: int = 0,
    ip_address: str = "",
) -> User:
    """更新用户信息。"""
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    update_data = user_data.model_dump(exclude_unset=True)
    role_ids = update_data.pop("role_ids", None)

    # 用户名唯一性校验（排除自身）
    new_username = update_data.get("username")
    if new_username is not None and new_username != user.username:
        existing = await get_user_by_username(session, new_username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    await session.flush()

    # 处理多角色
    if role_ids is not None:
        await _sync_user_roles(session, user.id, role_ids)

    await _create_audit_log(session, operator_id, "update", "user", user.id, ip_address, update_data)

    return user


async def delete_user(
    session: AsyncSession,
    user_id: int,
    operator_id: int = 0,
    ip_address: str = "",
) -> None:
    """彻底删除用户（物理删除）。"""
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.id == operator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录用户自身",
        )

    await session.delete(user)
    await session.flush()

    await _create_audit_log(session, operator_id, "delete", "user", user_id, ip_address)


async def _create_audit_log(
    session: AsyncSession,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    ip_address: str = "",
    detail: dict | None = None,
) -> None:
    """记录审计日志。"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        detail=detail,
    )
    session.add(log)


async def _sync_user_roles(session: AsyncSession, user_id: int, role_ids: list[int]) -> None:
    """同步用户的多角色关联"""
    from sqlalchemy import delete
    # 删除旧关联
    await session.execute(
        delete(user_role_table).where(user_role_table.c.user_id == user_id)
    )
    # 插入新关联
    if role_ids:
        await session.execute(
            user_role_table.insert(),
            [{"user_id": user_id, "role_id": rid} for rid in role_ids],
        )
    await session.flush()