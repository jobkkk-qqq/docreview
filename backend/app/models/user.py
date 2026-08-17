"""
用户模型

对应数据库表：users
- id SERIAL PK, username, password_hash, display_name, department_id FK,
  email, phone, role_id FK, is_active, last_login_at, created_at, updated_at
"""

from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.timezone import beijing_now


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 基本信息 ────────────────────────────────────────────
    username: Mapped[str] = mapped_column(String(50), unique=True, comment="用户名")
    password_hash: Mapped[str] = mapped_column(String(255), comment="密码哈希")
    display_name: Mapped[str | None] = mapped_column(String(100), comment="显示名称")
    email: Mapped[str | None] = mapped_column(String(255), comment="邮箱地址")
    phone: Mapped[str | None] = mapped_column(String(20), comment="手机号")

    # ── 关联 ────────────────────────────────────────────────
    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        comment="所属部门ID",
    )
    role_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        comment="角色ID",
    )

    # ── 状态 ────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    # ── 时间戳 ──────────────────────────────────────────────
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        comment="最后登录时间",
    )
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
    department: Mapped["Department | None"] = relationship(  # noqa: F821
        "Department",
        foreign_keys=[department_id],
        back_populates="members",
        lazy="selectin",
    )
    role: Mapped["Role | None"] = relationship(  # noqa: F821
        "Role",
        foreign_keys=[role_id],
        lazy="selectin",
    )
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
        overlaps="role",
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document",
        foreign_keys="Document.uploaded_by",
        back_populates="uploader",
        lazy="noload",
    )

    @property
    def is_superuser(self) -> bool:
        """判断是否为超级管理员（通过角色名判断）"""
        if self.role and self.role.name in ("admin", "系统管理员"):
            return True
        for r in self.roles:
            if r.name in ("admin", "系统管理员"):
                return True
        return False

    @property
    def all_role_ids(self) -> list[int]:
        """获取用户所有角色ID（包括旧 role_id 和新 roles）"""
        ids = [r.id for r in self.roles]
        if self.role_id and self.role_id not in ids:
            ids.append(self.role_id)
        return ids