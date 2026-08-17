"""
API 依赖注入模块

提供 FastAPI 路由中常用的依赖项：
- 获取当前数据库会话
- 获取当前登录用户
- 权限校验
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_async_session
from app.models.user import User
from app.services.permission_service import get_user_effective_permissions

# OAuth2 Bearer Token 提取器，从 Authorization 头中获取 Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """
    获取当前登录用户。

    从 JWT Token 中解析用户ID，查询数据库返回用户对象。
    Token 可从以下位置获取（按优先级）：
    1. Authorization: Bearer <token> 请求头
    2. ?token=xxx 查询参数（用于新标签页/手机端预览等无法设置请求头的场景）
    Token 无效或用户不存在时抛出 401 异常。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 获取 Token：优先从 Authorization 头，其次从查询参数
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.query_params.get("token")

    if not token:
        raise credentials_exception

    # 解码 Token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # 校验 Token 类型
    token_type = payload.get("type")
    if token_type != "access":
        raise credentials_exception

    # 提取用户ID
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    # 查询用户（role 和 department 已在模型中配置 lazy="selectin"）
    stmt = select(User).where(User.id == int(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户（已启用）。"""
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求管理员权限。"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


def require_permission(permission_code: str):
    """
    要求用户拥有指定权限。
    管理员默认拥有所有权限。
    
    用法：
        @router.get("/", dependencies=[Depends(require_permission("manage_categories"))])
    """
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        
        user_perms = get_user_effective_permissions(current_user)
        if permission_code not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {permission_code} 权限",
            )
        return current_user
    
    return permission_checker


def get_client_ip(request: Request) -> str:
    """获取客户端 IP 地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"