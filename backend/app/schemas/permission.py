"""权限管理相关 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocPermissionCreate(BaseModel):
    """创建文档权限 — user_id 和 role_id 至少填一个"""
    user_id: Optional[int] = Field(None, description="用户ID")
    role_id: Optional[int] = Field(None, description="角色ID")
    can_view: bool = Field(True, description="可查看")
    can_download: bool = Field(True, description="可下载")
    can_edit: bool = Field(False, description="可编辑")
    can_print: bool = Field(False, description="可打印")


class DocPermissionOut(BaseModel):
    """文档权限响应"""
    id: int
    document_id: int
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    can_view: bool
    can_download: bool
    can_edit: bool
    can_print: bool = False
    granted_by: Optional[int] = None
    created_at: datetime
    user_name: Optional[str] = None
    role_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CatPermissionCreate(BaseModel):
    """创建分类权限 — user_id 和 role_id 至少填一个"""
    user_id: Optional[int] = Field(None, description="用户ID")
    role_id: Optional[int] = Field(None, description="角色ID")
    category_id: int = Field(..., description="分类ID")
    can_edit: bool = Field(True, description="可编辑该分类下文档")
    can_view: bool = Field(True, description="可查看该分类下文档")


class CatPermissionOut(BaseModel):
    """分类权限响应"""
    id: int
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    category_id: int
    can_edit: bool
    can_view: bool
    granted_by: Optional[int] = None
    created_at: datetime
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    category_name: Optional[str] = None

    model_config = {"from_attributes": True}


class BatchPermissionCreate(BaseModel):
    """批量授权请求 — 结合 user_ids 和 role_ids"""
    user_ids: list[int] = Field(default_factory=list, description="用户ID列表")
    role_ids: list[int] = Field(default_factory=list, description="角色ID列表")
    can_view: bool = Field(True, description="可查看")
    can_download: bool = Field(True, description="可下载")
    can_edit: bool = Field(False, description="可编辑")
    can_print: bool = Field(False, description="可打印")