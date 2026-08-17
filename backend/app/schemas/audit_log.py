"""
审计日志相关 Pydantic 模型
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class UserBrief(BaseModel):
    """用户简要信息"""
    username: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    """审计日志响应"""
    id: int
    user_id: Optional[int] = None
    user: Optional[UserBrief] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    detail: Optional[Any] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}