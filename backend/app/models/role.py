"""
角色与权限模型

对应数据库表：
- roles：id SERIAL PK, name, description, is_system, created_at
- permissions：id SERIAL PK, code, name
- role_permissions：role_id PK, permission_id PK
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


# ── 用户-角色关联表（多对多）────────────────────────────────
user_role_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


# ── 角色-权限关联表（多对多）────────────────────────────────
role_permission_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    """角色模型"""

    __tablename__ = "roles"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 基本信息 ────────────────────────────────────────────
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, comment="角色编码（英文唯一标识）")
    name: Mapped[str] = mapped_column(String(50), unique=True, comment="角色名称")
    description: Mapped[str | None] = mapped_column(String(255), comment="角色描述")

    # ── 业务身份 ────────────────────────────────────────────
    is_business_role: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否业务身份角色（用于自动映射）")
    business_scope: Mapped[str | None] = mapped_column(String(100), comment="业务范围（quality/admin/doc/standard）")

    # ── 状态 ────────────────────────────────────────────────
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否系统内置角色")

    # ── 权限版本号（乐观锁，并发编辑校验）────────────────────
    permission_version: Mapped[int] = mapped_column(
        Integer, default=0, comment="权限版本号（乐观锁）"
    )

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        comment="创建时间",
    )

    # ── 关系 ────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="noload",
    )
    permissions: Mapped[list["Permission"]] = relationship(  # noqa: F821
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name}>"


class Permission(Base):
    """权限模型"""

    __tablename__ = "permissions"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 基本信息 ────────────────────────────────────────────
    code: Mapped[str] = mapped_column(String(100), unique=True, comment="权限编码（如 document.create）")
    name: Mapped[str] = mapped_column(String(100), comment="权限名称")

    # ── 树形结构（菜单-功能树）───────────────────────────────
    permission_type: Mapped[str] = mapped_column(
        String(20), default="function", comment="节点类型：menu 菜单 / function 功能"
    )
    parent_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="父节点权限 code，为空则为一级菜单"
    )
    menu_key: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="对应前端菜单 key"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="同级排序"
    )
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否已废弃"
    )

    # ── 关系 ────────────────────────────────────────────────
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Permission id={self.id} code={self.code}>"