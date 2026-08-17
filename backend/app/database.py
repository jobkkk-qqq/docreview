"""
SQLAlchemy 异步数据库连接模块

支持 SQLite（开发环境）和 PostgreSQL（生产环境）。
通过 DATABASE_URL 环境变量切换数据库类型：
  - SQLite:  sqlite+aiosqlite:///path/to/db.db
  - PG:      postgresql+asyncpg://user:pass@host:5432/dbname
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models.base import Base

# ── 判断数据库类型 ──────────────────────────────────────────
_is_sqlite = "sqlite" in settings.DATABASE_URL

# ── 创建异步引擎（根据数据库类型动态配置）───────────────────
if _is_sqlite:
    # SQLite 不支持连接池参数
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
else:
    # PostgreSQL 使用连接池
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,          # 生产环境设为 False，开发调试可设为 True
        pool_pre_ping=True,  # 连接池预检，自动回收断开的连接
        pool_size=10,        # 连接池大小
        max_overflow=20,     # 最大溢出连接数
        pool_recycle=3600,   # 连接回收时间（秒）
    )

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期，避免懒加载异常
)


async def get_async_session() -> AsyncSession:
    """
    获取异步数据库会话的依赖注入函数。

    用法::

        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise