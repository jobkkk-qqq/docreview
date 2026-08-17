"""
用户相关 Pydantic 模型

用于请求体验证和响应体序列化。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── 请求模型 ──────────────────────────────────────────────────

class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    department_id: Optional[int] = Field(None, description="所属部门ID")
    role_id: Optional[int] = Field(None, description="角色ID")
    role_ids: list[int] = Field(default_factory=list, description="多角色ID列表")


class UserUpdate(BaseModel):
    """更新用户请求（所有字段可选）"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    department_id: Optional[int] = Field(None, description="所属部门ID")
    role_id: Optional[int] = Field(None, description="角色ID")
    role_ids: Optional[list[int]] = Field(None, description="多角色ID列表")
    is_active: Optional[bool] = Field(None, description="是否启用")

    @field_validator("department_id", "role_id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转为 None，兼容前端未选择时传 '' 的情况"""
        if v == "":
            return None
        return v


# ── 响应模型 ──────────────────────────────────────────────────

class RoleBrief(BaseModel):
    """角色简要信息"""
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=255, description="角色描述")
    permission_ids: list[int] = Field(default_factory=list, description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色请求"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=255, description="角色描述")
    permission_ids: Optional[list[int]] = Field(None, description="权限ID列表")


class RoleOut(BaseModel):
    """角色详情响应"""
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: list[dict] = Field(default_factory=list, description="权限列表")
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentBrief(BaseModel):
    """部门简要信息"""
    id: int
    name: str
    code: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    """用户响应"""
    id: int
    username: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_superuser: bool = Field(default=False, description="是否超级管理员")
    department_id: Optional[int] = None
    role_id: Optional[int] = None
    department: Optional[DepartmentBrief] = None
    role: Optional[RoleBrief] = None
    roles: list[RoleBrief] = Field(default_factory=list, description="多角色列表")
    permissions: list[str] = Field(default_factory=list, description="用户有效权限列表")
    role_names: list[str] = Field(default_factory=list, description="用户角色名称列表")
    business_scopes: list[str] = Field(default_factory=list, description="用户业务范围列表")
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserListOut(BaseModel):
    """用户列表项"""
    id: int
    username: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    department: Optional[DepartmentBrief] = None
    role: Optional[RoleBrief] = None
    roles: list[RoleBrief] = Field(default_factory=list, description="多角色列表")
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 通用分页响应 ──────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """通用分页响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页记录数")
    items: list = Field(default_factory=list, description="数据列表")