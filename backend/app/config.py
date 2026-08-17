"""
应用配置管理模块

支持三种配置优先级（从高到低）：
1. 环境变量
2. .env 文件
3. 默认值

对于文档存储路径，还支持从数据库读取配置（通过 get_doc_repo_path_from_db 回调），
以便系统管理界面可以动态修改存储路径。
"""

import os
from pathlib import Path
from typing import Optional, Callable, Awaitable

# 项目根目录（backend 的父目录）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings:
    """应用全局配置"""

    # ── 项目基础 ──────────────────────────────────────────────
    PROJECT_NAME: str = "XXX数字档案管理系统"
    PROJECT_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # ── 数据库 ────────────────────────────────────────────────
    # 开发环境默认使用 SQLite，部署时切换为 PostgreSQL
    # 切换方式：设置环境变量 DATABASE_URL=postgresql+asyncpg://docuser:docpass@localhost:5432/docdb
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'backend' / 'docreview.db'}",
    )
    # 同步版本的连接字符串（供 Alembic 等同步工具使用）
    DATABASE_SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL",
        f"sqlite:///{_PROJECT_ROOT / 'backend' / 'docreview.db'}",
    )

    # ── JWT 配置 ──────────────────────────────────────────────
    # JWT 密钥，生产环境务必通过环境变量设置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "docreview-secret-key-change-in-production")
    # Token 过期时间（分钟）
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    # 刷新 Token 过期时间（天）
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    # JWT 算法
    JWT_ALGORITHM: str = "HS256"

    # ── 文档存储路径 ──────────────────────────────────────────
    # 默认文档仓库路径，支持环境变量覆盖
    DEFAULT_DOC_REPO_PATH: str = os.getenv(
        "DOC_REPO_PATH",
        str(_PROJECT_ROOT / "doc-repo"),
    )

    # ── CORS 配置 ────────────────────────────────────────────
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://192.168.1.196:3000,https://192.168.1.196:3000").split(",")

    # ── 文件上传限制 ──────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # ── 分页默认值 ────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    def __init__(self) -> None:
        # 确保默认存储路径存在
        Path(self.DEFAULT_DOC_REPO_PATH).mkdir(parents=True, exist_ok=True)

    # ── 数据库配置读取回调 ────────────────────────────────────
    # 预留：系统管理界面修改存储路径后，通过此回调从数据库读取最新配置
    _db_config_loader: Optional[Callable[[], Awaitable[dict[str, str]]]] = None

    @classmethod
    def set_db_config_loader(
        cls, loader: Callable[[], Awaitable[dict[str, str]]]
    ) -> None:
        """
        设置数据库配置加载回调。

        在应用启动时注入，系统管理接口修改配置后，
        get_doc_repo_path() 会优先从数据库读取最新值。

        用法示例::

            async def load_db_config() -> dict[str, str]:
                # 从数据库 system_configs 表读取键值对
                return {"doc_repo_path": "/new/path"}

            Settings.set_db_config_loader(load_db_config)
        """
        cls._db_config_loader = loader

    @classmethod
    async def get_doc_repo_path(cls) -> str:
        """
        获取当前生效的文档存储路径。

        优先级：
        1. 数据库中系统管理界面配置的路径（如果设置了 db_config_loader）
        2. 环境变量 DOC_REPO_PATH
        3. 默认路径 DEFAULT_DOC_REPO_PATH
        """
        if cls._db_config_loader is not None:
            try:
                db_configs = await cls._db_config_loader()
                db_path = db_configs.get("doc_repo_path")
                if db_path:
                    # 确保数据库配置的路径存在
                    Path(db_path).mkdir(parents=True, exist_ok=True)
                    return db_path
            except Exception:
                # 数据库读取失败时回退到本地配置
                pass
        return cls.DEFAULT_DOC_REPO_PATH


# 全局配置单例
settings = Settings()
