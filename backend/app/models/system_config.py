"""
系统配置模型

对应数据库表：
- system_configs: id SERIAL PK, key, value, description, updated_at, updated_by FK
"""

from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.core.timezone import beijing_now


class SystemConfig(Base):
    """系统配置模型"""

    __tablename__ = "system_configs"

    # ── 主键 ────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 配置项 ──────────────────────────────────────────────
    key: Mapped[str] = mapped_column(String(100), unique=True, comment="配置键")
    value: Mapped[str | None] = mapped_column(String(1000), comment="配置值")
    description: Mapped[str | None] = mapped_column(String(500), comment="配置描述")

    # ── 更新信息 ────────────────────────────────────────────
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        onupdate=beijing_now,
        comment="更新时间",
    )
    updated_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="更新者ID",
    )

    def __repr__(self) -> str:
        return f"<SystemConfig id={self.id} key={self.key}>"