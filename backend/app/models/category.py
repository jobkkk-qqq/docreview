"""
文档分类模型

对应数据库表：
- categories: id SERIAL PK, name, code, description, folder_path, sort_order, is_active, created_at
- category_default_roles: 分类默认授权角色（上传到该分类的文档自动授予这些角色查看/下载权限）
"""

from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Category(Base):
    """文档分类模型"""

    __tablename__ = "categories"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 基本信息 ────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(100), comment="分类名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="分类编码")
    description: Mapped[str | None] = mapped_column(String(500), comment="分类描述")
    folder_path: Mapped[str | None] = mapped_column(String(500), comment="文件夹路径")

    # ── 权限与业务类型 ──────────────────────────────────────
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否全员可见")
    business_type: Mapped[str | None] = mapped_column(String(50), comment="业务类型标签（standard/form/quality/environment/patent/contract）")

    # ── 排序与状态 ──────────────────────────────────────────
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序号")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )

    # ── 关系 ────────────────────────────────────────────────
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document",
        back_populates="category",
        lazy="noload",
    )
    permissions: Mapped[list["CategoryPermission"]] = relationship(  # noqa: F821
        "CategoryPermission",
        back_populates="category",
        lazy="noload",
    )
    default_roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary="category_default_roles",
        lazy="noload",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"


class CategoryDefaultRole(Base):
    """分类默认授权角色：上传到该分类的文档自动授予这些角色 查看+下载 权限"""

    __tablename__ = "category_default_roles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        comment="分类ID",
    )
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        comment="角色ID",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="配置人ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )

    def __repr__(self) -> str:
        return f"<CategoryDefaultRole category={self.category_id} role={self.role_id}>"

    __table_args__ = (
        Index("ix_cat_default_role_category_id", "category_id"),
        Index("ix_cat_default_role_role_id", "role_id"),
    )