"""
仪表盘相关 Pydantic 模型
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.document import DocumentListOut


class DashboardOverview(BaseModel):
    """仪表盘概览数据"""
    total_documents: int = Field(0, description="文档总数")
    total_users: int = Field(0, description="用户总数")
    total_categories: int = Field(0, description="分类总数")
    total_departments: int = Field(0, description="部门总数")
    pending_review_count: int = Field(0, description="待审核文档数")
    published_count: int = Field(0, description="已发布文档数")
    recent_upload_count: int = Field(0, description="最近7天上传数")


class PendingReviewItem(BaseModel):
    """待审核文档"""
    id: int
    title: str
    file_name: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    uploader_name: Optional[str] = None

    model_config = {"from_attributes": True}