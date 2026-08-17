"""
认证相关 Pydantic 模型

用于登录、Token 响应等场景。
"""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: Optional["UserInfo"] = Field(None, description="当前用户信息")


class UserInfo(BaseModel):
    """用户简要信息（登录时返回）"""
    id: int
    username: str
    display_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = Field(default=False, description="是否超级管理员")
    permissions: list[str] = Field(default_factory=list, description="用户有效权限列表")
    role_names: list[str] = Field(default_factory=list, description="用户角色名称列表")
    role: Optional[dict] = Field(None, description="主角色信息 {id, name}")
    business_scopes: list[str] = Field(default_factory=list, description="用户业务范围列表")

    model_config = {"from_attributes": True}


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")