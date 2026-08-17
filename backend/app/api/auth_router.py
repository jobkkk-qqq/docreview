"""
认证路由

提供登录、刷新令牌、修改密码等接口。
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import get_current_user, get_client_ip
from app.models.user import User
from app.services import auth_service
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UserInfo,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", summary="用户登录")
async def login(
    login_data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """用户登录，验证用户名密码，返回 JWT Token 和用户信息"""
    from app.services.permission_service import get_user_effective_permissions, get_user_business_scopes

    ip_address = get_client_ip(request)
    user = await auth_service.authenticate_user(session, login_data, ip_address)
    token_resp = auth_service.create_tokens_for_user(user)

    role_names = []
    if user.role:
        role_names.append(user.role.name)
    for r in user.roles:
        if r.name not in role_names:
            role_names.append(r.name)

    token_resp.user = UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        permissions=get_user_effective_permissions(user),
        role_names=role_names,
        role={"id": user.role.id, "name": user.role.name} if user.role else None,
        business_scopes=get_user_business_scopes(user),
    )
    return token_resp


@router.post("/refresh", summary="刷新令牌")
async def refresh_token(
    data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """使用刷新令牌获取新的访问令牌"""
    return await auth_service.refresh_access_token(session, data.refresh_token)


@router.post("/logout", summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_user),
):
    """用户登出（客户端清除 Token 即可）"""
    return {"detail": "已登出"}


@router.get("/debug-role", summary="调试角色信息")
async def debug_role(
    current_user: User = Depends(get_current_user),
):
    """调试：查看当前用户的角色信息"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role_id": current_user.role_id,
        "role": {"id": current_user.role.id, "name": current_user.role.name} if current_user.role else None,
        "is_superuser": current_user.is_superuser,
    }


@router.post("/change-password", summary="修改密码")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """修改当前用户密码"""
    ip_address = get_client_ip(request)
    await auth_service.change_password(
        session, current_user, data.old_password, data.new_password, ip_address
    )
    return {"detail": "密码修改成功"}