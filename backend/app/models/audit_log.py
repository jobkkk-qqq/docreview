"""
审计日志模型

对应数据库表：
- audit_logs: id BIGSERIAL PK, user_id FK, action, target_type, target_id,
  detail TEXT(JSON), ip_address, created_at

注意：detail 字段在 SQLite 下使用 TEXT 存储序列化后的 JSON 字符串，
通过 detail_data 属性实现自动序列化/反序列化。
部署 PostgreSQL 时可改回 JSONB 类型，并移除 detail_data 属性。
"""

import json
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.timezone import beijing_now


class AuditLog(Base):
    """审计日志模型"""

    __tablename__ = "audit_logs"

    # ── 主键 ──────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ── 操作者 ──────────────────────────────────────────────
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        comment="操作用户ID",
    )

    # ── 操作信息 ────────────────────────────────────────────
    action: Mapped[str] = mapped_column(String(50), comment="操作类型（如 create/update/delete/login）")
    target_type: Mapped[str | None] = mapped_column(String(50), comment="目标类型（如 document/user）")
    target_id: Mapped[int | None] = mapped_column(Integer, comment="目标ID")
    # SQLite 不支持 JSONB，使用 TEXT 存储 JSON 字符串
    # 部署 PostgreSQL 时可改回 JSONB 类型
    _detail: Mapped[str | None] = mapped_column("detail", Text, comment="操作详情（JSON字符串）")
    ip_address: Mapped[str | None] = mapped_column(String(50), comment="操作IP地址")

    # ── 时间戳 ──────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        comment="操作时间",
    )

    # ── 关系 ────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        lazy="noload",
    )

    # ── JSON 序列化/反序列化 ───────────────────────────────
    @property
    def detail(self) -> dict | None:
        """读取时自动将 JSON 字符串反序列化为 dict"""
        if self._detail is None:
            return None
        try:
            return json.loads(self._detail)
        except (json.JSONDecodeError, TypeError):
            return None

    @detail.setter
    def detail(self, value: dict | None) -> None:
        """写入时自动将 dict 序列化为 JSON 字符串"""
        if value is None:
            self._detail = None
        else:
            self._detail = json.dumps(value, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} target={self.target_type}>"

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )