"""
部门相关 Pydantic 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求模型 ──────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    """创建部门请求"""
    name: str = Field(..., max_length=100, description="部门名称")
    code: Optional[str] = Field(None, max_length=50, description="部门编码，不传则自动生成")
    description: Optional[str] = Field(None, max_length=500, description="部门描述")
    manager_user_id: Optional[int] = Field(None, description="部门负责人ID")


class DepartmentUpdate(BaseModel):
    """更新部门请求"""
    name: Optional[str] = Field(None, max_length=100, description="部门名称")
    description: Optional[str] = Field(None, max_length=500, description="部门描述")
    manager_user_id: Optional[int] = Field(None, description="部门负责人ID")
    is_active: Optional[bool] = Field(None, description="是否启用")


# ── 响应模型 ──────────────────────────────────────────────────

class DepartmentOut(BaseModel):
    """部门响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    manager_user_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    user_count: int = 0

    model_config = {"from_attributes": True}