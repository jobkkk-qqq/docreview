# API 路由包

from app.api.auth_router import router as auth_router
from app.api.user_router import router as user_router
from app.api.category_router import router as category_router
from app.api.document_router import router as document_router
from app.api.department_router import router as department_router
from app.api.system_router import router as system_router
from app.api.dashboard_router import router as dashboard_router
from app.api.audit_router import router as audit_router

__all__ = [
    "auth_router",
    "user_router",
    "category_router",
    "document_router",
    "department_router",
    "system_router",
    "dashboard_router",
    "audit_router",
]