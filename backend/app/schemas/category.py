"""
分类相关 Pydantic 模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── 请求模型 ──────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., max_length=100, description="分类名称")
    code: Optional[str] = Field(None, max_length=50, description="分类编码，不传则自动生成")
    description: Optional[str] = Field(None, max_length=500, description="分类描述")
    folder_path: Optional[str] = Field(None, max_length=500, description="文件夹路径")
    sort_order: int = Field(default=0, description="排序号")
    is_public: bool = Field(default=False, description="是否全员可见")
    business_type: Optional[str] = Field(None, max_length=50, description="业务类型标签（standard/form/quality/environment/patent/contract）")


class CategoryUpdate(BaseModel):
    """更新分类请求"""
    name: Optional[str] = Field(None, max_length=100, description="分类名称")
    description: Optional[str] = Field(None, max_length=500, description="分类描述")
    folder_path: Optional[str] = Field(None, max_length=500, description="文件夹路径")
    sort_order: Optional[int] = Field(None, description="排序号")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_public: Optional[bool] = Field(None, description="是否全员可见")
    business_type: Optional[str] = Field(None, max_length=50, description="业务类型标签")


# ── 响应模型 ──────────────────────────────────────────────────

class CategoryOut(BaseModel):
    """分类响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    folder_path: Optional[str] = None
    sort_order: int
    is_active: bool
    is_public: bool = False
    business_type: Optional[str] = None
    created_at: datetime
    doc_count: int = 0

    model_config = {"from_attributes": True}


class CategoryTreeItem(CategoryOut):
    """分类树节点"""
    children: list["CategoryTreeItem"] = Field(default_factory=list, description="子分类列表")

    model_config = {"from_attributes": True}