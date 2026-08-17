"""
SQLAlchemy Base 和公共 Mixin

提供声明式基类和通用时间戳 Mixin。
所有主键使用 INTEGER（SERIAL），与数据库 init_db.py 脚本保持一致。
"""

from sqlalchemy import DateTime, Integer, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.timezone import beijing_now


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class TimestampMixin:
    """时间戳 Mixin，提供 created_at 和 updated_at 字段（北京时间 UTC+8）"""

    created_at = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        comment="创建时间",
    )
    updated_at = mapped_column(
        DateTime,
        server_default=text("(datetime('now', 'localtime'))"),
        default=beijing_now,
        onupdate=beijing_now,
        comment="更新时间",
    )