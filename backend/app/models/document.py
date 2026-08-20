"""
文档模型

对应数据库表：
- documents: id SERIAL PK, doc_no, title, category_id FK, file_path, file_name,
  file_size, file_type, version, status, summary, keywords, confidential_level,
  effective_date, expiry_date, uploaded_by FK, created_at, updated_at
- document_permissions: id SERIAL PK, document_id FK, user_id FK,
  can_view, can_download, can_print, granted_by FK, created_at
"""

from datetime import datetime, date

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Boolean,
    Text,
    DateTime,
    Date,
    ForeignKey,
    Index,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.timezone import beijing_now
from app.core.doc_levels import DEFAULT_DOC_LEVEL


class Document(Base):
    """文档模型"""

    __tablename__ = "documents"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 基本信息 ────────────────────────────────────────────
    doc_no: Mapped[str | None] = mapped_column(String(50), comment="文档编号")
    title: Mapped[str] = mapped_column(String(255), comment="文档标题")
    summary: Mapped[str | None] = mapped_column(Text, comment="文档摘要")
    keywords: Mapped[str | None] = mapped_column(String(500), comment="关键词（逗号分隔）")

    # ── 分类 ────────────────────────────────────────────────
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        comment="所属分类ID（一级分类）",
    )

    # ── 二级分类：部门 ──────────────────────────────────────
    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="所属部门ID（二级分类）",
    )

    # ── 三级分类：文档级别 ──────────────────────────────────
    doc_level: Mapped[str] = mapped_column(
        String(20),
        default=DEFAULT_DOC_LEVEL,
        server_default=text("'无级别'"),
        comment="文档级别（三级分类：Ⅰ级文件/Ⅱ级文件/Ⅲ级文件/Ⅳ级文件/无级别）",
    )

    # ── 文件信息 ────────────────────────────────────────────
    file_path: Mapped[str | None] = mapped_column(String(500), comment="文件存储路径")
    file_name: Mapped[str | None] = mapped_column(String(255), comment="原始文件名")
    file_size: Mapped[int | None] = mapped_column(BigInteger, comment="文件大小（字节）")
    file_type: Mapped[str | None] = mapped_column(String(50), comment="文件 MIME 类型")
    pdf_path: Mapped[str | None] = mapped_column(String(500), comment="PDF 预览文件路径")
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="文件内容 SHA-256 哈希值，用于重复检测",
    )

    # ── 版本控制 ────────────────────────────────────────────
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")

    # ── 状态 ────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(20), default="draft", comment="文档状态")

    # ── 密级和有效期 ────────────────────────────────────────
    confidential_level: Mapped[str | None] = mapped_column(String(20), comment="密级")
    effective_date: Mapped[date | None] = mapped_column(Date, comment="生效日期")
    expiry_date: Mapped[date | None] = mapped_column(Date, comment="失效日期")

    # ── 全文搜索 ────────────────────────────────────────────
    # SQLite 不支持 TSVECTOR，使用 TEXT 存储
    # 部署 PostgreSQL 时可改回 TSVECTOR 并添加 GIN 索引以获得全文检索能力
    full_text_search: Mapped[str | None] = mapped_column(Text, comment="全文搜索内容（TEXT）")

    # ── 上传者 ──────────────────────────────────────────────
    uploaded_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="上传者ID",
    )

    # ── 软删除 ──────────────────────────────────────────────
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已删除（软删除标志）",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="删除时间",
    )

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        onupdate=beijing_now,
        comment="更新时间",
    )

    # ── 关系 ────────────────────────────────────────────────
    category: Mapped["Category | None"] = relationship(  # noqa: F821
        "Category",
        back_populates="documents",
        lazy="selectin",
    )
    uploader: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[uploaded_by],
        back_populates="documents",
        lazy="selectin",
    )
    department: Mapped["Department | None"] = relationship(  # noqa: F821
        "Department",
        foreign_keys=[department_id],
        lazy="selectin",
    )
    permissions: Mapped[list["DocumentPermission"]] = relationship(
        "DocumentPermission",
        back_populates="document",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title} status={self.status}>"

    __table_args__ = (
        Index("ix_documents_category_id", "category_id"),
        Index("ix_documents_department_id", "department_id"),
        Index("ix_documents_doc_level", "doc_level"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_confidential_level", "confidential_level"),
        Index("ix_documents_category_status", "category_id", "status"),
    )


class DocumentPermission(Base):
    """文档权限模型"""

    __tablename__ = "document_permissions"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 关联 ────────────────────────────────────────────────
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        comment="文档ID",
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        comment="用户ID（用户级权限）",
    )
    role_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
        comment="角色ID（角色级权限）",
    )

    # ── 权限 ────────────────────────────────────────────────
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, comment="可查看")
    can_download: Mapped[bool] = mapped_column(Boolean, default=True, comment="可下载")
    can_print: Mapped[bool] = mapped_column(Boolean, default=False, comment="可打印")
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, comment="可编辑")

    # ── 授权 ────────────────────────────────────────────────
    granted_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="授权人ID",
    )

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        comment="创建时间",
    )

    # ── 关系 ────────────────────────────────────────────────
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="permissions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<DocumentPermission id={self.id} document_id={self.document_id}>"

    __table_args__ = (
        Index("ix_doc_perm_document_id", "document_id"),
        Index("ix_doc_perm_role_id", "role_id"),
        Index("ix_doc_perm_user_id", "user_id"),
    )


class CategoryPermission(Base):
    """分类权限模型 — 控制文档管理员对某分类下文档的编辑权限"""

    __tablename__ = "category_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="用户ID（用户级权限）")
    role_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, comment="角色ID（角色级权限）")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), comment="分类ID")
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, comment="可编辑该分类下的文档")
    can_view: Mapped[bool] = mapped_column(Boolean, default=True, comment="可查看该分类下的文档")
    granted_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), comment="授权人ID")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        comment="创建时间",
    )

    # 关系
    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id], lazy="noload")
    category: Mapped["Category | None"] = relationship("Category", back_populates="permissions", lazy="noload")

    def __repr__(self) -> str:
        return f"<CategoryPermission id={self.id} user={self.user_id} cat={self.category_id}>"

    __table_args__ = (
        Index("ix_cat_perm_category_id", "category_id"),
        Index("ix_cat_perm_role_id", "role_id"),
        Index("ix_cat_perm_user_id", "user_id"),
    )