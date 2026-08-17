"""
文档相关 Pydantic 模型
"""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求模型 ──────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    """创建文档请求（文件上传后的元信息）"""
    title: str = Field(..., max_length=255, description="文档标题")
    doc_no: Optional[str] = Field(None, max_length=50, description="文档编号，不传则自动生成")
    summary: Optional[str] = Field(None, description="文档摘要")
    keywords: Optional[str] = Field(None, description="关键词")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    confidential_level: Optional[str] = Field(None, description="密级")
    effective_date: Optional[date] = Field(None, description="生效日期")
    expiry_date: Optional[date] = Field(None, description="失效日期")


class DocumentUpdate(BaseModel):
    """更新文档请求"""
    title: Optional[str] = Field(None, max_length=255, description="文档标题")
    doc_no: Optional[str] = Field(None, max_length=50, description="文档编号")
    summary: Optional[str] = Field(None, description="文档摘要")
    keywords: Optional[str] = Field(None, description="关键词")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    status: Optional[str] = Field(None, description="文档状态")
    confidential_level: Optional[str] = Field(None, description="密级")
    effective_date: Optional[date] = Field(None, description="生效日期")
    expiry_date: Optional[date] = Field(None, description="失效日期")


class DocumentReview(BaseModel):
    """文档审核请求"""
    status: str = Field(..., description="审核结果（approved/rejected）")
    comment: Optional[str] = Field(None, description="审核意见")


# ── 响应模型 ──────────────────────────────────────────────────

class UploaderBrief(BaseModel):
    """上传者简要信息"""
    id: int
    username: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoryBrief(BaseModel):
    """分类简要信息"""
    id: int
    name: str

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    """文档响应"""
    id: int
    doc_no: Optional[str] = None
    title: str
    summary: Optional[str] = None
    keywords: Optional[str] = None
    category_id: Optional[int] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    version: int
    status: str
    confidential_level: Optional[str] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Optional[CategoryBrief] = None
    uploader: Optional[UploaderBrief] = None
    can_download: bool = False
    has_pdf: bool = False

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    """文档列表项"""
    id: int
    doc_no: Optional[str] = None
    title: str
    confidential_level: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    version: int
    status: str
    category: Optional[CategoryBrief] = None
    uploader: Optional[UploaderBrief] = None
    created_at: datetime
    can_download: bool = False
    has_pdf: bool = False

    model_config = {"from_attributes": True}


class DeletedDocumentOut(BaseModel):
    """已删除文档列表项"""
    id: int
    doc_no: Optional[str] = None
    title: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    category: Optional[CategoryBrief] = None
    uploader: Optional[UploaderBrief] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CategoryDocGroup(BaseModel):
    """分类-文档分组（用于按分类分组的文档列表）"""
    id: int | None = None
    name: str
    total: int = 0
    documents: list[DocumentListOut]