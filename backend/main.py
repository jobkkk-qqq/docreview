"""
FastAPI 应用入口

创建 FastAPI 实例，注册中间件，挂载所有 API 路由前缀。
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.base import Base


# ── 生命周期管理 ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理。

    启动时：初始化数据库连接池，创建表和索引。
    关闭时：释放资源。
    """
    # ── 启动阶段 ──
    from app.database import engine
    app.state.engine = engine

    # 导入所有模型确保它们被注册到 Base.metadata
    from app.models import user, category, document, role, audit_log, department, system_config  # noqa: F401
    
    # 创建所有表和索引（如果不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 自动迁移：检查并添加缺失的列（安全操作，不影响已有数据）
    from app.core.auto_migrate import auto_migrate
    await auto_migrate(engine)

    # 注册数据库配置加载器
    async def load_db_config():
        from app.database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            result = await session.execute(
                text("SELECT key, value FROM system_configs WHERE key = 'doc_repo_path'")
            )
            row = result.first()
            return {row.key: row.value} if row else {}

    Settings = settings.__class__
    Settings.set_db_config_loader(load_db_config)

    # 后台扫描文档仓库，自动关联已存在的PDF预览文件
    from app.services.repo_scanner import run_startup_repair_in_background
    run_startup_repair_in_background()

    yield

    # ── 关闭阶段 ──
    await engine.dispose()


# ── 创建 FastAPI 应用 ─────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="沃迪森数字档案管理系统后端 API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── 全局异常处理 ──────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局未捕获异常处理器。"""
    import logging
    logging.getLogger(__name__).error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


# ── CORS 中间件 ───────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 注册路由 ─────────────────────────────────────────────────
from app.api.auth_router import router as auth_router
from app.api.user_router import router as user_router
from app.api.category_router import router as category_router
from app.api.document_router import router as document_router
from app.api.department_router import router as department_router
from app.api.system_router import router as system_router
from app.api.dashboard_router import router as dashboard_router
from app.api.audit_router import router as audit_router
from app.api.permission_router import router as permission_router
from app.api.role_router import router as role_router

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(user_router, prefix=settings.API_PREFIX)
app.include_router(document_router, prefix=settings.API_PREFIX)
app.include_router(category_router, prefix=settings.API_PREFIX)
app.include_router(department_router, prefix=settings.API_PREFIX)
app.include_router(system_router, prefix=settings.API_PREFIX)
app.include_router(role_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(permission_router, prefix=settings.API_PREFIX)


# ── 健康检查 ──────────────────────────────────────────────────

@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return {"status": "ok", "version": settings.PROJECT_VERSION}


# ── 启动入口（仅用于开发调试）────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9002,
        reload=True,
    )
