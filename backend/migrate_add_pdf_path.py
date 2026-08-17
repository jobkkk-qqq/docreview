"""
数据库迁移脚本：为 documents 表添加 pdf_path 字段
"""

import sqlite3
import sys
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent / "docreview.db"


def migrate():
    """添加 pdf_path 字段"""
    if not DB_PATH.exists():
        print(f"数据库文件不存在：{DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(documents)")
    columns = [row[1] for row in cursor.fetchall()]

    if "pdf_path" in columns:
        print("pdf_path 字段已存在，无需迁移")
        conn.close()
        return

    # 添加字段
    cursor.execute("ALTER TABLE documents ADD COLUMN pdf_path VARCHAR(500) DEFAULT NULL")
    conn.commit()
    print("成功添加 pdf_path 字段")

    conn.close()


if __name__ == "__main__":
    migrate()
