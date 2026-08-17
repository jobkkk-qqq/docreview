"""
自动数据库迁移
使用 schema 版本号机制：启动时只查询一次版本号，只有版本落后时才执行迁移。
迁移完成后更新版本号，后续启动直接跳过。

版本历史：
  v1 — 初始版本（pdf_path 字段、权限树字段等）
  v2 — 软删除（documents 表添加 is_deleted、deleted_at 字段）
  v3 — 文件重复检测（documents 表添加 content_hash 字段）
  v4 — 回填已有文档的 content_hash（文件内容 SHA-256）
"""
import hashlib
import logging
from pathlib import Path

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings

logger = logging.getLogger(__name__)

# 当前数据库 schema 版本，新增迁移时递增此值
CURRENT_SCHEMA_VERSION = 4

# system_configs 中存储版本号的 key
VERSION_KEY = "schema_version"


async def _get_current_db_version(conn) -> int:
    """从 system_configs 表读取当前 schema 版本"""
    try:
        result = await conn.execute(
            text(f"SELECT value FROM system_configs WHERE key = '{VERSION_KEY}'")
        )
        row = result.fetchone()
        if row:
            return int(row[0])
    except Exception:
        pass
    return 0


async def _set_db_version(conn, version: int) -> None:
    """更新 schema 版本号"""
    await conn.execute(
        text(f"DELETE FROM system_configs WHERE key = '{VERSION_KEY}'")
    )
    await conn.execute(
        text(f"INSERT INTO system_configs (key, value, description) VALUES ('{VERSION_KEY}', '{version}', '数据库 schema 版本号')")
    )


async def _migrate_v1(conn) -> None:
    """v1 迁移：添加缺失的列"""
    # 获取所有已存在的表
    tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

    # documents 表：添加 pdf_path
    if "documents" in tables:
        doc_cols = {col["name"] for col in await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("documents")
        )}
        if "pdf_path" not in doc_cols:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN pdf_path VARCHAR(500) DEFAULT NULL"))
            logger.info("[AutoMigrate] documents.pdf_path 字段已添加")

    # permissions 表：添加权限树字段
    if "permissions" in tables:
        perm_cols = {col["name"] for col in await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("permissions")
        )}
        for col_name, col_def in [
            ("permission_type", "VARCHAR(20) DEFAULT 'function'"),
            ("parent_code", "VARCHAR(100)"),
            ("menu_key", "VARCHAR(50)"),
            ("sort_order", "INTEGER DEFAULT 0"),
            ("is_deprecated", "BOOLEAN DEFAULT 0"),
        ]:
            if col_name not in perm_cols:
                await conn.execute(text(f"ALTER TABLE permissions ADD COLUMN {col_name} {col_def}"))
                logger.info(f"[AutoMigrate] permissions.{col_name} 字段已添加")

    # roles 表：添加 permission_version
    if "roles" in tables:
        role_cols = {col["name"] for col in await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("roles")
        )}
        if "permission_version" not in role_cols:
            await conn.execute(text("ALTER TABLE roles ADD COLUMN permission_version INTEGER DEFAULT 0"))
            logger.info("[AutoMigrate] roles.permission_version 字段已添加")

    # user_roles 中间表
    if "users" in tables and "roles" in tables and "user_roles" not in tables:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, role_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(role_id) REFERENCES roles(id) ON DELETE CASCADE
            )
        """))
        logger.info("[AutoMigrate] user_roles 中间表已创建")


async def _migrate_v2(conn) -> None:
    """v2 迁移：documents 表添加 is_deleted、deleted_at 字段"""
    tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    if "documents" in tables:
        doc_cols = {col["name"] for col in await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("documents")
        )}
        if "is_deleted" not in doc_cols:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
            logger.info("[AutoMigrate] documents.is_deleted 字段已添加")
        if "deleted_at" not in doc_cols:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN deleted_at DATETIME DEFAULT NULL"))
            logger.info("[AutoMigrate] documents.deleted_at 字段已添加")


async def _migrate_v3(conn) -> None:
    """v3 迁移：documents 表添加 content_hash 字段（文件重复检测）"""
    tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    if "documents" in tables:
        doc_cols = {col["name"] for col in await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_columns("documents")
        )}
        if "content_hash" not in doc_cols:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64) DEFAULT NULL"))
            logger.info("[AutoMigrate] documents.content_hash 字段已添加")


async def _migrate_v4(engine: AsyncEngine) -> None:
    """v4 迁移：回填已有文档的 content_hash（文件内容 SHA-256）

    旧文档在 v3 之前上传，content_hash 字段为空。若不回填，重复检测将无法匹配
    这些已存在的文件。本迁移读取每个文档的物理文件，计算 SHA-256 并更新数据库。
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    from app.database import async_session_factory
    from app.models.document import Document

    repo_path = await settings.get_doc_repo_path()
    repo = Path(repo_path)

    async with async_session_factory() as session:
        # 查询所有 content_hash 为空且文件路径不为空的文档
        stmt = select(Document).where(
            Document.content_hash.is_(None),
            Document.file_path.isnot(None),
        )
        result = await session.execute(stmt)
        docs = list(result.scalars().all())

        if not docs:
            logger.info("[AutoMigrate][v4] 没有需要回填 content_hash 的文档")
            return

        updated_count = 0
        for doc in docs:
            if not doc.file_path:
                continue
            full_path = repo / doc.file_path
            if not full_path.exists() or not full_path.is_file():
                # 文件已不存在，跳过
                doc.content_hash = ""
                updated_count += 1
                continue

            try:
                # 读取文件并计算 SHA-256
                data = full_path.read_bytes()
                doc.content_hash = hashlib.sha256(data).hexdigest()
                updated_count += 1
            except Exception as e:
                logger.warning(f"[AutoMigrate][v4] 文档 {doc.id} ({doc.file_path}) 计算哈希失败：{e}")
                doc.content_hash = ""

        await session.commit()
        logger.info(f"[AutoMigrate][v4] 回填完成，共处理 {updated_count}/{len(docs)} 个文档的 content_hash")


async def auto_migrate(engine: AsyncEngine) -> None:
    """
    自动迁移入口。
    先查询 schema_version，仅当版本号 < CURRENT_SCHEMA_VERSION 时执行迁移。
    正常情况下每次启动只执行一次轻量 SELECT 查询，性能开销可忽略。
    """
    async with engine.begin() as conn:
        db_version = await _get_current_db_version(conn)
        if db_version >= CURRENT_SCHEMA_VERSION:
            logger.info(f"[AutoMigrate] 数据库已是最新版本 (v{db_version})，无需迁移")
            return

        logger.info(f"[AutoMigrate] 数据库版本 v{db_version}，需要迁移到 v{CURRENT_SCHEMA_VERSION}")

        # 按需执行迁移
        if db_version < 1:
            await _migrate_v1(conn)
        if db_version < 2:
            await _migrate_v2(conn)
        if db_version < 3:
            await _migrate_v3(conn)

        # v4 需要读取物理文件，在 engine.begin() 外面用独立 session 执行
        # 但先更新版本号，然后退出 conn 事务，再用独立 session 跑 v4
        if db_version < 4:
            await _set_db_version(conn, CURRENT_SCHEMA_VERSION)
            logger.info(f"[AutoMigrate] 数据库版本已更新为 v{CURRENT_SCHEMA_VERSION}（v4 文件回填在事务外单独执行）")

    # v4 文件回填在 engine.begin() 事务外执行，避免长时间占用连接
    if db_version < 4:
        await _migrate_v4(engine)
