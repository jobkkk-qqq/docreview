"""
系统管理路由

提供系统配置获取和修改接口。
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import require_admin, get_client_ip
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.system_config import SystemConfig
from app.schemas.system_config import SystemConfigOut, SystemConfigUpdate

router = APIRouter(prefix="/system", tags=["系统管理"])

# 品牌名称配置 key
BRAND_NAME_KEY = "brand_name"

# 业务范围配置 key
BUSINESS_SCOPES_KEY = "business_scopes"

# 默认业务范围列表
DEFAULT_BUSINESS_SCOPES = [
    {"code": "quality", "name": "品质"},
    {"code": "admin", "name": "行政"},
    {"code": "hr", "name": "人事"},
    {"code": "finance", "name": "财务"},
    {"code": "legal", "name": "法务"},
    {"code": "procurement", "name": "采购"},
    {"code": "production", "name": "生产"},
]


@router.get("/brand", summary="获取系统品牌名称")
async def get_system_brand(
    session: AsyncSession = Depends(get_async_session),
):
    """获取系统品牌名称（公开接口，无需登录，供登录页与侧边栏显示）"""
    stmt = select(SystemConfig).where(SystemConfig.key == BRAND_NAME_KEY)
    config = (await session.execute(stmt)).scalar_one_or_none()
    name = (config.value if config and config.value else None) or "XXX数字档案管理系统"
    return {"brand_name": name}


@router.get("/config", summary="获取系统配置")
async def get_system_config(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """获取所有系统配置（扁平化字典格式）"""
    stmt = select(SystemConfig).order_by(SystemConfig.id)
    result = await session.execute(stmt)
    configs = list(result.scalars().all())
    return {c.key: c.value for c in configs}


@router.put("/config", summary="批量修改系统配置")
async def update_system_config(
    data: dict,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """批量修改系统配置（需管理员权限）"""
    ip_address = get_client_ip(request)

    for key, value in data.items():
        stmt = select(SystemConfig).where(SystemConfig.key == key)
        config = (await session.execute(stmt)).scalar_one_or_none()

        if config is None:
            config = SystemConfig(
                key=key,
                value=str(value) if value is not None else None,
                updated_by=current_user.id,
            )
            session.add(config)
            await session.flush()
        else:
            config.value = str(value) if value is not None else None
            config.updated_by = current_user.id

        log = AuditLog(
            user_id=current_user.id, action="update",
            target_type="system_config", target_id=config.id,
            ip_address=ip_address,
            detail={"key": key, "value": str(value)},
        )
        session.add(log)

    return {"detail": "配置更新成功"}


@router.get("/stats", summary="系统统计")
async def get_system_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """获取系统统计数据"""
    from sqlalchemy import func
    from app.models.user import User
    from app.models.document import Document
    from app.models.category import Category
    from app.models.department import Department

    total_users = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    total_documents = (await session.execute(select(func.count()).select_from(Document))).scalar() or 0
    total_categories = (await session.execute(select(func.count()).select_from(Category))).scalar() or 0
    total_departments = (await session.execute(select(func.count()).select_from(Department))).scalar() or 0
    pending_review = (await session.execute(
        select(func.count()).select_from(Document).where(Document.status.in_(["pending_review", "reviewing"]))
    )).scalar() or 0
    active_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    )).scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_documents": total_documents,
        "total_categories": total_categories,
        "total_departments": total_departments,
        "pending_review_count": pending_review,
    }


# ── 业务范围管理 ────────────────────────────────────────────

async def _get_business_scopes_from_db(session: AsyncSession) -> list[dict]:
    """从数据库读取业务范围列表，不存在则返回默认值"""
    stmt = select(SystemConfig).where(SystemConfig.key == BUSINESS_SCOPES_KEY)
    config = (await session.execute(stmt)).scalar_one_or_none()
    if config and config.value:
        try:
            return json.loads(config.value)
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULT_BUSINESS_SCOPES


async def _save_business_scopes_to_db(
    session: AsyncSession, scopes: list[dict], user_id: int
) -> None:
    """保存业务范围列表到数据库"""
    stmt = select(SystemConfig).where(SystemConfig.key == BUSINESS_SCOPES_KEY)
    config = (await session.execute(stmt)).scalar_one_or_none()
    value = json.dumps(scopes, ensure_ascii=False)
    if config is None:
        config = SystemConfig(key=BUSINESS_SCOPES_KEY, value=value, updated_by=user_id)
        session.add(config)
    else:
        config.value = value
        config.updated_by = user_id


@router.get("/business-scopes", summary="获取业务范围列表")
async def get_business_scopes(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """获取业务范围列表（所有已登录管理员可访问）"""
    scopes = await _get_business_scopes_from_db(session)
    return {"items": scopes}


@router.put("/business-scopes", summary="保存业务范围列表")
async def save_business_scopes(
    data: dict,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_admin),
):
    """保存业务范围列表（全量替换）"""
    items = data.get("items", [])
    # 校验格式
    for item in items:
        if not isinstance(item, dict) or not item.get("code") or not item.get("name"):
            raise HTTPException(status_code=400, detail="每个业务范围必须包含 code 和 name")
        if not item["code"].replace("_", "").isalnum():
            raise HTTPException(status_code=400, detail=f"code '{item['code']}' 只能包含字母、数字和下划线")

    await _save_business_scopes_to_db(session, items, current_user.id)
    await session.flush()

    # 审计日志
    log = AuditLog(
        user_id=current_user.id,
        action="update",
        target_type="system_config",
        target_id=0,
        ip_address=get_client_ip(request),
        detail={"key": BUSINESS_SCOPES_KEY, "value": json.dumps(items, ensure_ascii=False)},
    )
    session.add(log)
    await session.flush()

    return {"detail": "保存成功", "items": items}
