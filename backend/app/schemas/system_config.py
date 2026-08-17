"""
系统配置相关 Pydantic 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SystemConfigUpdate(BaseModel):
    """修改系统配置请求"""
    key: str = Field(..., max_length=100, description="配置键")
    value: str = Field(..., description="配置值")


class SystemConfigOut(BaseModel):
    """系统配置响应"""
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = {"from_attributes": True}