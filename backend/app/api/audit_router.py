"""
审计日志路由

提供审计日志查询和导出接口。
"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.api.deps import require_permission
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut
from app.schemas.user import PaginatedResponse
import json
from datetime import datetime

router = APIRouter(prefix="/audit-logs", tags=["审计日志"])


@router.get("/", summary="审计日志列表")
async def list_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    action: str | None = Query(None, description="操作类型筛选"),
    target_type: str | None = Query(None, description="目标类型筛选"),
    user_id: int | None = Query(None, description="操作用户ID筛选"),
    username: str | None = Query(None, description="操作人用户名/显示名模糊筛选"),
    start_date: str | None = Query(None, description="开始日期（ISO格式）"),
    end_date: str | None = Query(None, description="结束日期（ISO格式）"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("view_audit_logs")),
):
    """分页查询审计日志（需要查看审计日志权限）"""
    stmt = select(AuditLog).options(selectinload(AuditLog.user))
    count_stmt = select(func.count()).select_from(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
        count_stmt = count_stmt.where(AuditLog.target_type == target_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if username:
        from app.models.user import User as UserModel
        stmt = stmt.join(UserModel, UserModel.id == AuditLog.user_id, isouter=True)
        count_stmt = count_stmt.join(UserModel, UserModel.id == AuditLog.user_id, isouter=True)
        username_filter = (
            UserModel.username.ilike(f"%{username}%")
            | UserModel.display_name.ilike(f"%{username}%")
        )
        stmt = stmt.where(username_filter)
        count_stmt = count_stmt.where(username_filter)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            stmt = stmt.where(AuditLog.created_at >= start_dt)
            count_stmt = count_stmt.where(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            stmt = stmt.where(AuditLog.created_at <= end_dt)
            count_stmt = count_stmt.where(AuditLog.created_at <= end_dt)
        except ValueError:
            pass

    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    logs = list(result.scalars().all())

    items = [AuditLogOut.model_validate(log) for log in logs]
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/export", summary="导出审计日志")
async def export_audit_logs(
    action: str | None = Query(None, description="操作类型筛选"),
    target_type: str | None = Query(None, description="目标类型筛选"),
    limit: int = Query(1000, ge=1, le=10000, description="导出最大条数"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("view_audit_logs")),
):
    """导出审计日志为 JSON 文件（需要查看审计日志权限）"""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)

    result = await session.execute(stmt)
    logs = list(result.scalars().all())

    export_data = []
    for log in logs:
        export_data.append({
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    content = json.dumps(export_data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
    )