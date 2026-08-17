"""
认证业务逻辑服务
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.timezone import beijing_now
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.auth import LoginRequest, TokenResponse


async def authenticate_user(
    session: AsyncSession,
    login_data: LoginRequest,
    ip_address: str = "",
) -> User:
    """
    验证用户凭据，更新最后登录时间，记录审计日志。
    """
    from sqlalchemy.orm import selectinload
    from app.models.role import Role
    stmt = select(User).options(
        selectinload(User.role).selectinload(Role.permissions),
        selectinload(User.roles).selectinload(Role.permissions),
    ).where(User.username == login_data.username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 更新最后登录时间
    user.last_login_at = beijing_now()
    await session.flush()

    # 记录审计日志
    await _create_audit_log(session, user.id, "login", "user", user.id, ip_address)

    return user


def create_tokens_for_user(user: User) -> TokenResponse:
    """为用户生成访问令牌和刷新令牌。"""
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def refresh_access_token(
    session: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """使用刷新令牌获取新的访问令牌。"""
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

    stmt = select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )

    return create_tokens_for_user(user)


async def change_password(
    session: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
    ip_address: str = "",
) -> None:
    """修改用户密码。"""
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )

    user.password_hash = get_password_hash(new_password)
    await session.flush()

    await _create_audit_log(session, user.id, "change_password", "user", user.id, ip_address)


async def _create_audit_log(
    session: AsyncSession,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    ip_address: str = "",
) -> None:
    """记录审计日志（内部工具函数）。"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
    )
    session.add(log)