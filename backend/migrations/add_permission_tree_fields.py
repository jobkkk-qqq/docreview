"""
数据库迁移脚本：为权限表添加菜单-功能树字段，并初始化菜单功能树数据。

运行方式：
    cd backend
    python migrations/add_permission_tree_fields.py
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# 将 backend 加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text, Column, String, Integer, Boolean
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.menu_function_tree import MENU_FUNCTION_TREE


def column_exists(conn, table, column):
    """检查 SQLite 表中是否存在某列"""
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    rows = result.fetchall()
    return any(row[1] == column for row in rows)


def upgrade():
    engine = create_engine(settings.DATABASE_SYNC_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 新增 Permission 表字段
        conn = session.connection()
        if not column_exists(conn, "permissions", "permission_type"):
            conn.execute(text("ALTER TABLE permissions ADD COLUMN permission_type VARCHAR(20) DEFAULT 'function'"))
        if not column_exists(conn, "permissions", "parent_code"):
            conn.execute(text("ALTER TABLE permissions ADD COLUMN parent_code VARCHAR(100)"))
        if not column_exists(conn, "permissions", "menu_key"):
            conn.execute(text("ALTER TABLE permissions ADD COLUMN menu_key VARCHAR(50)"))
        if not column_exists(conn, "permissions", "sort_order"):
            conn.execute(text("ALTER TABLE permissions ADD COLUMN sort_order INTEGER DEFAULT 0"))
        if not column_exists(conn, "permissions", "is_deprecated"):
            conn.execute(text("ALTER TABLE permissions ADD COLUMN is_deprecated BOOLEAN DEFAULT 0"))

        # 2. 新增 Role 表字段
        if not column_exists(conn, "roles", "permission_version"):
            conn.execute(text("ALTER TABLE roles ADD COLUMN permission_version INTEGER DEFAULT 0"))

        # 3. 同步菜单功能树到 permissions 表
        code_set = set()
        for node in MENU_FUNCTION_TREE:
            code = node["code"]
            code_set.add(code)
            existing = session.execute(
                text("SELECT id FROM permissions WHERE code = :code"),
                {"code": code}
            ).fetchone()

            if existing is None:
                session.execute(
                    text("""
                        INSERT INTO permissions (code, name, permission_type, parent_code, menu_key, sort_order, is_deprecated)
                        VALUES (:code, :name, :type, :parent, :menu_key, :sort, 0)
                    """),
                    {
                        "code": code,
                        "name": node["name"],
                        "type": node["type"],
                        "parent": node.get("parent"),
                        "menu_key": node.get("menu_key"),
                        "sort": node["sort"],
                    }
                )
            else:
                session.execute(
                    text("""
                        UPDATE permissions
                        SET name = :name,
                            permission_type = :type,
                            parent_code = :parent,
                            menu_key = :menu_key,
                            sort_order = :sort,
                            is_deprecated = 0
                        WHERE code = :code
                    """),
                    {
                        "code": code,
                        "name": node["name"],
                        "type": node["type"],
                        "parent": node.get("parent"),
                        "menu_key": node.get("menu_key"),
                        "sort": node["sort"],
                    }
                )

        # 4. 标记废弃节点
        if code_set:
            placeholders = ", ".join([f"'" + c.replace("'", "''") + "'" for c in code_set])
            session.execute(
                text(f"UPDATE permissions SET is_deprecated = 1 WHERE code NOT IN ({placeholders})")
            )

        # 5. 确保 manage_menu_permissions 存在
        perm_row = session.execute(
            text("SELECT id FROM permissions WHERE code = 'manage_menu_permissions'")
        ).fetchone()
        if perm_row is None:
            session.execute(
                text("""
                    INSERT INTO permissions (code, name, permission_type, parent_code, menu_key, sort_order, is_deprecated)
                    VALUES ('manage_menu_permissions', '菜单功能权限', 'function', 'permission_matrix', NULL, 2, 0)
                """)
            )
            perm_row = session.execute(
                text("SELECT id FROM permissions WHERE code = 'manage_menu_permissions'")
            ).fetchone()
        perm_id = perm_row[0]

        # 6. 为系统管理员角色授予 manage_menu_permissions 和 permission_matrix（幂等）
        admin_role = session.execute(
            text("SELECT id FROM roles WHERE name = '系统管理员' LIMIT 1")
        ).fetchone()
        if admin_role:
            admin_id = admin_role[0]

            # 6.1 授予 manage_menu_permissions
            exists = session.execute(
                text("SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"),
                {"role_id": admin_id, "perm_id": perm_id}
            ).fetchone()
            if exists is None:
                session.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"),
                    {"role_id": admin_id, "perm_id": perm_id}
                )

            # 6.2 授予 permission_matrix（菜单入口权限），否则系统管理员看不到“权限矩阵”菜单
            menu_perm_row = session.execute(
                text("SELECT id FROM permissions WHERE code = 'permission_matrix' LIMIT 1")
            ).fetchone()
            if menu_perm_row:
                menu_perm_id = menu_perm_row[0]
                menu_exists = session.execute(
                    text("SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"),
                    {"role_id": admin_id, "perm_id": menu_perm_id}
                ).fetchone()
                if menu_exists is None:
                    session.execute(
                        text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"),
                        {"role_id": admin_id, "perm_id": menu_perm_id}
                    )

            # 7. 写入审计日志（幂等）
            already_logged = session.execute(
                text("""
                    SELECT 1 FROM audit_logs
                    WHERE action = 'grant_permission'
                      AND target_type = 'role'
                      AND target_id = :role_id
                      AND detail LIKE '%system_upgrade%'
                    LIMIT 1
                """),
                {"role_id": admin_id}
            ).fetchone()
            if already_logged is None:
                session.execute(
                    text("""
                        INSERT INTO audit_logs (user_id, action, target_type, target_id, detail, ip_address, created_at)
                        VALUES (NULL, 'grant_permission', 'role', :role_id, :detail, 'system', :created_at)
                    """),
                    {
                        "role_id": admin_id,
                        "detail": json.dumps({
                            "permission_code": "manage_menu_permissions,permission_matrix",
                            "reason": "system_upgrade",
                            "description": "系统升级时自动为系统管理员授予权限矩阵菜单及菜单功能权限管理权限"
                        }),
                        "created_at": datetime.now().isoformat(),
                    }
                )

        session.commit()
        print("迁移完成：已添加权限树字段并初始化菜单功能树数据")
    except Exception as e:
        session.rollback()
        print(f"迁移失败：{e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    upgrade()
