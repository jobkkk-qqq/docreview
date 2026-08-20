"""
文档管理路由

提供文档上传、列表查询、详情、下载、删除、审核等接口。
"""

import logging
from pathlib import Path
import mimetypes

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.api.deps import get_current_user, get_client_ip, require_permission
from app.config import settings
from app.models.user import User
from app.models.category import Category
from app.models.department import Department
from app.services import doc_service
from app.services.permission_service import can_user_download_document, get_user_business_scopes
from app.core.doc_levels import DOC_LEVELS, is_valid_doc_level
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentReview, DocumentOut, DocumentListOut, DeletedDocumentOut, CategoryDocGroup
from app.schemas.user import PaginatedResponse

document_ext_mimetypes = {
    '.pdf': 'application/pdf',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
    '.svg': 'image/svg+xml',
    '.txt': 'text/plain;charset=utf-8',
    '.md': 'text/markdown;charset=utf-8',
}

def _get_inline_mimetype(filename: str) -> str:
    """根据文件扩展名返回内联渲染用的 MIME 类型"""
    ext = Path(filename).suffix.lower()
    if ext in document_ext_mimetypes:
        return document_ext_mimetypes[ext]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or 'application/octet-stream'


def _needs_watermark(document) -> bool:
    """判断文档是否需要添加水印（非公开文档需要水印）"""
    return document.confidential_level and document.confidential_level != "public"


async def _validate_dept_and_level(
    session: AsyncSession, department_id: int | None, doc_level: str | None,
) -> str:
    """校验部门（二级分类）与文档级别（三级分类），返回规范化后的文档级别。"""
    final_level = (doc_level or "").strip() or "无级别"
    if not is_valid_doc_level(final_level):
        raise HTTPException(
            status_code=400,
            detail=f"文档级别不合法，可选值：{'、'.join(DOC_LEVELS)}",
        )
    if department_id:
        dept = await session.get(Department, department_id)
        if dept is None or not dept.is_active:
            raise HTTPException(status_code=400, detail="所选部门不存在或已停用")
    return final_level


router = APIRouter(prefix="/documents", tags=["文档管理"])


@router.post("/upload", summary="上传文档")
async def upload_document(
    request: Request,
    title: str = Form(..., description="文档标题"),
    doc_no: str = Form(None, description="文档编号，不传则自动生成"),
    summary: str = Form(None, description="文档摘要"),
    keywords: str = Form(None, description="关键词"),
    category_id: int = Form(None, description="分类ID（一级分类）"),
    department_id: int = Form(None, description="部门ID（二级分类）"),
    doc_level: str = Form(None, description="文档级别（三级分类），不传默认为无级别"),
    confidential_level: str = Form(None, description="密级"),
    role_ids: str = Form(None, description="授权角色ID列表（逗号分隔，如 1,2,3）"),
    file: UploadFile = File(..., description="文件"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("upload_doc")),
):
    """上传新文档，保存文件到 doc-repo 目录"""
    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)

    # 校验文件大小
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE_MB}MB）")

    # 校验部门与文档级别
    final_doc_level = await _validate_dept_and_level(session, department_id, doc_level)

    # 构建文档数据
    doc_data = DocumentCreate(
        title=title,
        doc_no=doc_no or None,
        summary=summary,
        keywords=keywords,
        category_id=category_id,
        department_id=department_id,
        doc_level=final_doc_level,
        confidential_level=confidential_level,
    )

    # 业务角色分类范围校验
    business_scopes = get_user_business_scopes(current_user)
    if business_scopes and not current_user.is_superuser:
        # 未选择分类时，若用户有业务 scope 则必须选择
        if not category_id:
            raise HTTPException(status_code=400, detail="业务角色上传文档必须选择所属分类")
        cat_stmt = select(Category.id, Category.name, Category.business_type, Category.is_public).where(Category.id == category_id)
        cat_result = await session.execute(cat_stmt)
        category = cat_result.one_or_none()
        if category is None:
            raise HTTPException(status_code=400, detail="所选分类不存在")
        # 文档管理员（doc_admin）可以上传到任何分类
        if 'doc_admin' not in business_scopes:
            # 允许上传到：业务范围匹配的分类 或 公开分类
            cat_business_type = category.business_type
            cat_is_public = category.is_public
            if cat_business_type not in business_scopes and not cat_is_public:
                raise HTTPException(
                    status_code=403,
                    detail=f"无权上传至分类「{category.name}」，该分类不在您的业务范围内",
                )

    # 解析 role_ids
    parsed_role_ids = None
    if role_ids:
        try:
            parsed_role_ids = [int(x.strip()) for x in role_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="role_ids 格式错误，请用逗号分隔数字ID")

    ip_address = get_client_ip(request)
    document = await doc_service.upload_document(
        session, current_user, file_content, file.filename, file.content_type,
        doc_data, ip_address, role_ids=parsed_role_ids,
    )
    return DocumentOut.model_validate(document)


@router.post("/batch-upload", summary="批量上传文档")
async def batch_upload_documents(
    request: Request,
    category_id: int = Form(..., description="分类ID（统一应用到所有文件）"),
    department_id: int = Form(None, description="部门ID（二级分类，统一应用）"),
    doc_level: str = Form(None, description="文档级别（三级分类，统一应用，默认无级别）"),
    confidential_level: str = Form("internal", description="保密等级（统一应用到所有文件）"),
    summary: str = Form(None, description="文档摘要（选填，统一应用）"),
    role_ids: str = Form(None, description="授权角色ID列表（逗号分隔，如 1,2,3）"),
    files: list[UploadFile] = File(..., description="文件列表（支持多个）"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("upload_doc")),
):
    """批量上传文档：统一设置分类、保密等级和授权角色，标题自动取文件名"""
    if not files:
        raise HTTPException(status_code=400, detail="请选择要上传的文件")

    # 校验部门与文档级别（在整个循环之前统一校验一次）
    final_doc_level = await _validate_dept_and_level(session, department_id, doc_level)

    # 解析角色ID
    parsed_role_ids = []
    if role_ids:
        try:
            parsed_role_ids = [int(x.strip()) for x in role_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="role_ids 格式错误，请用逗号分隔数字ID")

    ip_address = get_client_ip(request)
    results = []
    success_count = 0
    fail_count = 0

    for up_file in files:
        try:
            file_content = await up_file.read()
            # 标题自动取文件名（去扩展名）
            original_name = up_file.filename or "未命名"
            auto_title = Path(original_name).stem or original_name

            doc_data = DocumentCreate(
                title=auto_title,
                category_id=category_id,
                department_id=department_id,
                doc_level=final_doc_level,
                confidential_level=confidential_level,
                summary=summary,
            )

            document = await doc_service.upload_document(
                session, current_user, file_content, original_name, up_file.content_type,
                doc_data, ip_address, role_ids=parsed_role_ids,
            )
            results.append({
                "filename": original_name,
                "success": True,
                "doc_id": document.id,
                "title": document.title,
            })
            success_count += 1
        except Exception as e:
            results.append({
                "filename": up_file.filename,
                "success": False,
                "error": str(e),
            })
            fail_count += 1

    return {
        "total": len(files),
        "success": success_count,
        "failed": fail_count,
        "results": results,
    }


@router.get("/", summary="文档列表")
async def list_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    keyword: str | None = Query(None, description="搜索关键词"),
    category_id: int | None = Query(None, description="分类ID"),
    department_id: int | None = Query(None, description="部门ID（二级分类）"),
    doc_level: str | None = Query(None, description="文档级别（三级分类）"),
    status: str | None = Query(None, description="状态筛选"),
    confidential_level: str | None = Query(None, description="保密等级筛选"),
    uploaded_by: int | None = Query(None, description="上传者ID"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """分页查询文档列表"""
    documents, total = await doc_service.list_documents(
        session, page=page, page_size=page_size,
        keyword=keyword, category_id=category_id,
        department_id=department_id, doc_level=doc_level,
        status_filter=status, uploaded_by=uploaded_by,
        confidential_level=confidential_level,
        current_user=current_user,
    )
    items = [DocumentListOut.model_validate(d) for d in documents]
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/grouped", summary="按分类分组的文档列表")
async def list_documents_grouped(
    keyword: str | None = Query(None, description="搜索关键词"),
    category_id: int | None = Query(None, description="分类ID"),
    department_id: int | None = Query(None, description="部门ID（二级分类）"),
    doc_level: str | None = Query(None, description="文档级别（三级分类）"),
    status: str | None = Query(None, description="状态筛选"),
    confidential_level: str | None = Query(None, description="保密等级筛选"),
    page: int = Query(1, ge=1, description="每个分类组内独立分页的页码"),
    page_size: int = Query(30, ge=1, le=100, description="每分类每页文档数"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """按分类分组返回文档列表，每个分类内独立分页，每页 page_size 条"""
    groups = await doc_service.list_documents_grouped(
        session,
        keyword=keyword,
        category_id=category_id,
        department_id=department_id,
        doc_level=doc_level,
        status_filter=status,
        confidential_level=confidential_level,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )
    output_items = []
    for g in groups:
        docs = [DocumentListOut.model_validate(d) for d in g["documents"]]
        output_items.append(CategoryDocGroup(id=g["id"], name=g["name"], total=g["total"], documents=docs))
    return output_items


@router.get("/deleted/list", summary="获取已删除文档列表")
async def get_deleted_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    keyword: str = Query("", description="搜索关键词（标题/文档编号）"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取已删除的文档列表（管理员操作）"""
    # 验证管理员权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅系统管理员可查看已删除文档")
    kw = keyword if keyword else None
    documents, total = await doc_service.list_deleted_documents(
        session, page=page, page_size=page_size, keyword=kw,
    )
    return {
        "items": [DeletedDocumentOut.model_validate(d) for d in documents],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{doc_id}", summary="文档详情")
async def get_document(
    doc_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取文档详细信息"""
    document = await doc_service.get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    document.can_download = can_user_download_document(current_user, document)
    document.has_pdf = bool(document.pdf_path)
    return DocumentOut.model_validate(document)


@router.put("/{doc_id}", summary="更新文档")
async def update_document(
    doc_id: int,
    doc_data: DocumentUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """更新文档元信息"""
    # 权限校验
    from app.services.permission_service import can_user_edit_document
    from app.models.document import CategoryPermission
    from sqlalchemy import select

    document = await doc_service.get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not can_user_edit_document(current_user, document):
        # 检查是否有分类级编辑权限
        if document.category_id:
            cp_stmt = select(CategoryPermission).where(
                CategoryPermission.user_id == current_user.id,
                CategoryPermission.category_id == document.category_id,
                CategoryPermission.can_edit == True,
            )
            cp_result = await session.execute(cp_stmt)
            if not cp_result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="无权编辑此文档")
        else:
            raise HTTPException(status_code=403, detail="无权编辑此文档")

    ip_address = get_client_ip(request)
    # 校验部门与文档级别（三级分类）若提交了相关字段
    if doc_data.department_id is not None or doc_data.doc_level is not None:
        final_level = await _validate_dept_and_level(session, doc_data.department_id, doc_data.doc_level)
        if doc_data.doc_level is not None:
            doc_data.doc_level = final_level
    document = await doc_service.update_document(session, doc_id, doc_data, current_user.id, ip_address)
    return DocumentOut.model_validate(document)


@router.post("/{doc_id}/review", summary="审核文档")
async def review_document(
    doc_id: int,
    review_data: DocumentReview,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """审核文档（通过/驳回）"""
    ip_address = get_client_ip(request)
    document = await doc_service.review_document(session, doc_id, current_user, review_data, ip_address)
    return DocumentOut.model_validate(document)


@router.delete("/{doc_id}", summary="删除文档")
async def delete_document(
    doc_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_permission("delete_doc")),
):
    """删除文档（软删除：将文件移至 draft 目录，标记为已删除）"""
    ip_address = get_client_ip(request)
    await doc_service.delete_document(session, doc_id, current_user.id, ip_address)
    return {"detail": "文档已删除"}


@router.post("/{doc_id}/restore", summary="恢复已删除文档")
async def restore_document(
    doc_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """恢复已删除的文档（仅系统管理员可操作）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅系统管理员可恢复已删除文档")
    ip_address = get_client_ip(request)
    document = await doc_service.restore_document(session, doc_id, current_user.id, ip_address)
    return DocumentOut.model_validate(document)


@router.post("/{doc_id}/print", summary="上报打印日志")
async def report_print_log(
    doc_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """记录文档打印操作到审计日志"""
    ip_address = get_client_ip(request)
    from app.models.audit_log import AuditLog
    log = AuditLog(
        user_id=current_user.id, action="print",
        target_type="document", target_id=doc_id,
        ip_address=ip_address, detail={"document_id": doc_id},
    )
    session.add(log)
    await session.flush()
    return {"detail": "打印记录已保存"}


@router.get("/{doc_id}/download", summary="下载文档")
async def download_document(
    doc_id: int,
    inline: int = Query(0, description="为 1 时以内联方式返回（浏览器直接渲染而非下载）"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """下载文档文件（带权限校验）"""
    document = await doc_service.get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限校验优先于文件存在性检查，避免信息泄露
    if not can_user_download_document(current_user, document):
        raise HTTPException(status_code=403, detail="没有下载该文档的权限")

    if not document.file_path:
        raise HTTPException(status_code=404, detail="文件不存在")

    repo_path = await settings.get_doc_repo_path()
    full_path = Path(repo_path) / document.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件已被删除或移动")

    return FileResponse(
        path=str(full_path),
        filename=document.file_name or "download",
        media_type=_get_inline_mimetype(document.file_name) if inline else (document.file_type or "application/octet-stream"),
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get("/{doc_id}/preview-pdf", summary="获取 PDF 预览文件")
async def get_preview_pdf(
    doc_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """获取文档的 PDF 预览文件（用于 Office 文件在线预览）。
    如果PDF不存在，会尝试实时转换。
    非公开文档会自动添加水印（用户名+年月日）。"""
    document = await doc_service.get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限校验
    if not can_user_download_document(current_user, document):
        raise HTTPException(status_code=403, detail="没有查看该文档的权限")

    # 判断是否需要水印
    apply_watermark = _needs_watermark(document)
    display_name = current_user.display_name or current_user.username

    repo_path = await settings.get_doc_repo_path()
    file_ext = Path(document.file_name).suffix.lower() if document.file_name else ''
    stored_ext = Path(document.file_path).suffix.lower() if document.file_path else ''
    office_extensions = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
    repo = Path(repo_path)

    is_pdf = file_ext == '.pdf' or stored_ext == '.pdf'
    is_office = file_ext in office_extensions or stored_ext in office_extensions

    # 获取 PDF 文件路径
    pdf_full_path = None

    # 如果本身就是PDF文件
    if is_pdf:
        full_path = repo / document.file_path
        if not full_path.exists():
            stored_name = Path(document.file_path).name
            for candidate in repo.rglob(stored_name):
                if candidate.is_file():
                    full_path = candidate
                    break
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        pdf_full_path = full_path

    # Office文件：检查是否已有PDF预览
    elif is_office:
        from app.services.repo_scanner import find_existing_pdf

        # 1. 先检查数据库记录的路径
        if document.pdf_path:
            pdf_full_path = repo / document.pdf_path
            if not pdf_full_path.exists() or not pdf_full_path.is_file():
                pdf_full_path = None

        # 2. 数据库路径无效，按UUID文件名在磁盘上查找
        if not pdf_full_path:
            pdf_full_path = find_existing_pdf(repo, document.file_path)
            if pdf_full_path:
                rel = pdf_full_path.relative_to(repo)
                document.pdf_path = str(rel).replace('\\', '/')
                session.add(document)
                await session.commit()

        # 3. 磁盘上也没有PDF，才尝试实时转换
        if not pdf_full_path:
            from app.services.pdf_converter import convert_office_to_pdf, is_libreoffice_available
            input_full_path = repo / document.file_path
            if not input_full_path.exists():
                stored_name = Path(document.file_path).name
                for candidate in repo.rglob(stored_name):
                    if candidate.is_file():
                        input_full_path = candidate
                        break
            if not input_full_path.exists():
                raise HTTPException(status_code=404, detail="原始文件不存在")
            if not is_libreoffice_available():
                raise HTTPException(status_code=404, detail="服务器未安装LibreOffice，无法转换Office文件为PDF进行预览，请下载后查看")
            output_dir = input_full_path.parent
            pdf_result = await convert_office_to_pdf(str(input_full_path), str(output_dir), timeout=120)
            if not pdf_result:
                raise HTTPException(status_code=500, detail="PDF转换失败，请下载后查看")
            pdf_full_path = Path(pdf_result)
            pdf_relative = str(pdf_full_path.relative_to(repo)).replace('\\', '/')
            document.pdf_path = pdf_relative
            session.add(document)
            await session.commit()
    else:
        raise HTTPException(status_code=400, detail="该文件类型不支持PDF预览")

    # 非公开文档：添加水印（生成临时文件）
    if apply_watermark:
        try:
            from app.services.pdf_watermark import add_watermark_to_pdf, cleanup_temp_pdf
            watermarked_path = add_watermark_to_pdf(
                pdf_path=str(pdf_full_path),
                display_name=display_name,
            )
            # 后台任务清理临时文件
            background_tasks.add_task(cleanup_temp_pdf, watermarked_path)
            return FileResponse(
                path=watermarked_path,
                filename=f"{Path(document.file_name).stem}.pdf" if document.file_name else "preview.pdf",
                media_type="application/pdf",
                content_disposition_type="inline",
            )
        except Exception as e:
            logger.warning("PDF水印添加失败，回退返回原始文件: %s", e)
            # 水印失败时回退到返回原始 PDF

    # 公开文档或水印失败：直接返回原文件
    return FileResponse(
        path=str(pdf_full_path),
        filename=document.file_name or "preview.pdf",
        media_type="application/pdf",
        content_disposition_type="inline",
    )


@router.get("/{doc_id}/preview.pdf", summary="手机端 PDF 预览（路径以 .pdf 结尾触发浏览器阅读器）")
async def mobile_preview_pdf(
    doc_id: int,
    token: str = Query("", description="JWT token（手机端无法带 Authorization header）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_async_session),
):
    """手机端 PDF 预览 — URL 路径以 .pdf 结尾，触发手机浏览器内置 PDF 阅读器
    非公开文档会自动添加水印（用户名+年月日）。"""
    from app.core.security import decode_token

    # 从查询参数校验 token（手机端新页面无法加 Authorization header）
    payload = decode_token(token) if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await session.get(User, int(user_id_str))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")

    document = await doc_service.get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 权限校验
    if not can_user_download_document(user, document):
        raise HTTPException(status_code=403, detail="没有查看该文档的权限")

    # 判断是否需要水印
    apply_watermark = _needs_watermark(document)
    # 水印使用手机端用户的姓名
    display_name = user.display_name or user.username
    from app.services.pdf_watermark import add_watermark_to_pdf, cleanup_temp_pdf

    file_name = document.file_name or "document.pdf"
    file_ext = Path(file_name).suffix.lower()
    stored_ext = Path(document.file_path).suffix.lower() if document.file_path else ''
    repo_path = await settings.get_doc_repo_path()
    repo = Path(repo_path)
    office_extensions = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}

    is_pdf = file_ext == '.pdf' or stored_ext == '.pdf'
    is_office = file_ext in office_extensions or stored_ext in office_extensions

    # 获取 PDF 路径
    pdf_full_path = None

    # PDF 文件
    if is_pdf:
        full_path = repo / document.file_path
        if not full_path.exists():
            stored_name = Path(document.file_path).name
            for candidate in repo.rglob(stored_name):
                if candidate.is_file():
                    full_path = candidate
                    break
        if full_path.exists():
            pdf_full_path = full_path
        else:
            raise HTTPException(status_code=404, detail="文件不存在")

    # Office 文件
    elif is_office:
        from app.services.repo_scanner import find_existing_pdf

        if document.pdf_path:
            pdf_full_path = repo / document.pdf_path
            if not pdf_full_path.exists() or not pdf_full_path.is_file():
                pdf_full_path = None

        if not pdf_full_path:
            pdf_full_path = find_existing_pdf(repo, document.file_path)
            if pdf_full_path:
                rel = pdf_full_path.relative_to(repo)
                document.pdf_path = str(rel).replace('\\', '/')
                session.add(document)
                await session.commit()

        if not pdf_full_path:
            from app.services.pdf_converter import convert_office_to_pdf, is_libreoffice_available
            input_full_path = repo / document.file_path
            if not input_full_path.exists():
                stored_name = Path(document.file_path).name
                for candidate in repo.rglob(stored_name):
                    if candidate.is_file():
                        input_full_path = candidate
                        break
            if not input_full_path.exists():
                raise HTTPException(status_code=404, detail="原始文件不存在")
            if not is_libreoffice_available():
                raise HTTPException(status_code=404, detail="服务器未安装LibreOffice，无法预览，请下载后查看")
            output_dir = input_full_path.parent
            pdf_result = await convert_office_to_pdf(str(input_full_path), str(output_dir), timeout=120)
            if not pdf_result:
                raise HTTPException(status_code=500, detail="PDF转换失败，请下载后查看")
            pdf_full_path = Path(pdf_result)
            pdf_relative = str(pdf_full_path.relative_to(repo)).replace('\\', '/')
            document.pdf_path = pdf_relative
            session.add(document)
            await session.commit()
    else:
        raise HTTPException(status_code=400, detail="该文件类型不支持PDF预览")

    # 非公开文档：添加水印
    if apply_watermark:
        try:
            watermarked_path = add_watermark_to_pdf(
                pdf_path=str(pdf_full_path),
                display_name=display_name,
            )
            # 后台任务清理临时文件
            background_tasks.add_task(cleanup_temp_pdf, watermarked_path)
            return FileResponse(
                path=watermarked_path,
                filename=f"{Path(file_name).stem}.pdf",
                media_type="application/pdf",
                content_disposition_type="inline",
            )
        except Exception as e:
            logger.warning("手机端PDF水印添加失败，回退返回原始文件: %s", e)

    # 公开文档或水印失败：直接返回原文件
    return FileResponse(
        path=str(pdf_full_path),
        filename=file_name,
        media_type="application/pdf",
        content_disposition_type="inline",
    )


@router.post("/{doc_id}/preview", summary="上报预览日志")
async def report_preview_log(
    doc_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """记录文档预览操作到审计日志"""
    ip_address = get_client_ip(request)
    from app.models.audit_log import AuditLog
    log = AuditLog(
        user_id=current_user.id, action="preview",
        target_type="document", target_id=doc_id,
        ip_address=ip_address, detail={"document_id": doc_id},
    )
    session.add(log)
    await session.flush()
    return {"detail": "预览记录已保存"}