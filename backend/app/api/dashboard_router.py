"""
仪表盘路由

提供统计数据、最近文档、待审核文档等接口。
"""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import get_current_user
from app.core.timezone import beijing_now
from app.models.user import User
from app.models.document import Document
from app.models.category import Category
from app.models.department import Department
from app.schemas.dashboard import DashboardOverview, PendingReviewItem
from app.services import doc_service

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/overview", summary="概览数据")
async def get_dashboard_overview(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取仪表盘概览数据"""
    total_documents = (await session.execute(
        select(func.count()).select_from(Document)
    )).scalar() or 0

    total_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    )).scalar() or 0

    total_categories = (await session.execute(
        select(func.count()).select_from(Category)
    )).scalar() or 0

    total_departments = (await session.execute(
        select(func.count()).select_from(Department)
    )).scalar() or 0

    pending_review_count = (await session.execute(
        select(func.count()).select_from(Document).where(
            Document.status.in_(["pending_review", "reviewing"])
        )
    )).scalar() or 0

    published_count = (await session.execute(
        select(func.count()).select_from(Document).where(
            Document.status == "approved"
        )
    )).scalar() or 0

    # 最近7天上传数
    seven_days_ago = beijing_now() - timedelta(days=7)
    recent_upload_count = (await session.execute(
        select(func.count()).select_from(Document).where(
            Document.created_at >= seven_days_ago
        )
    )).scalar() or 0

    return DashboardOverview(
        total_documents=total_documents,
        total_users=total_users,
        total_categories=total_categories,
        total_departments=total_departments,
        pending_review_count=pending_review_count,
        published_count=published_count,
        recent_upload_count=recent_upload_count,
    )


@router.get("/recent-documents", summary="最近文档")
async def get_recent_documents(
    limit: int = 10,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户可见的最近上传/更新文档"""
    from app.schemas.document import DocumentListOut
    documents = await doc_service.get_recent_documents(session, limit, current_user)
    return [DocumentListOut.model_validate(d) for d in documents]


@router.get("/pending-reviews", summary="待审核文档")
async def get_pending_reviews(
    limit: int = 10,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户可见的待审核文档列表"""
    documents = await doc_service.get_pending_review_documents(session, limit, current_user)

    items = []
    for d in documents:
        items.append({
            "id": d.id,
            "title": d.title,
            "file_name": d.file_name,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "uploader_name": d.uploader.display_name or d.uploader.username if d.uploader else None,
        })
    return items