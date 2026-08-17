"""
部门模型

对应数据库表：
- departments: id SERIAL PK, name, code, description, manager_user_id FK,
  is_active, created_at
- department_categories: department_id PK, category_id PK, created_at
"""

from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Integer,
    Table,
    Column,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# ── 部门-分类关联表（多对多）────────────────────────────────
department_category_table = Table(
    "department_categories",
    Base.metadata,
    Column("department_id", Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now(), comment="创建时间"),
)


class Department(Base):
    """部门模型"""

    __tablename__ = "departments"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 基本信息 ────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(100), comment="部门名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, comment="部门编码")
    description: Mapped[str | None] = mapped_column(String(500), comment="部门描述")

    # ── 负责人 ──────────────────────────────────────────────
    manager_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="部门负责人ID",
    )

    # ── 状态 ────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )

    # ── 关系 ────────────────────────────────────────────────
    manager: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[manager_user_id],
        lazy="noload",
    )
    members: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        foreign_keys="User.department_id",
        back_populates="department",
        lazy="noload",
    )
    categories: Mapped[list["Category"]] = relationship(  # noqa: F821
        "Category",
        secondary="department_categories",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Department id={self.id} name={self.name}>"