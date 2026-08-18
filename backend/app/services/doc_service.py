"""
文档管理业务逻辑服务
"""

import asyncio
from datetime import date
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.timezone import beijing_now
from app.models.document import Document
from app.models.category import Category
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentReview


async def _safe_unlink(path: Path, retries: int = 3, delay: float = 1.0) -> bool:
    """安全删除文件，文件被占用时自动重试（避免进程残留句柄导致删除失败）"""
    for i in range(retries):
        try:
            if path.exists():
                path.unlink()
            return True
        except OSError:
            if i < retries - 1:
                await asyncio.sleep(delay)
    return False


async def _auto_mark_missing_files(
    session: AsyncSession,
    documents: list[Document],
    repo_path: str,
) -> list[Document]:
    """检测文档列表中的物理文件是否存在于磁盘上，对缺失文件的文档自动标记为已删除。

    场景：管理员可能通过文件系统直接删除了 doc-repo/ 下的文件（而非通过系统删除功能），
    导致数据库记录仍存在但文件已丢失。用户端列表刷新生效需要此函数自动修复。

    Args:
        session: 数据库会话
        documents: 待检查的文档列表（is_deleted == False）
        repo_path: 文档仓库根路径

    Returns:
        过滤后的有效文档列表（物理文件存在的文档）
    """
    from datetime import datetime, timezone

    repo = Path(repo_path)
    valid_docs: list[Document] = []
    now = beijing_now()

    for doc in documents:
        if doc.is_deleted:
            # 已标记删除的文档不参与检查
            continue

        if not doc.file_path:
            # 没有文件路径的文档，视为无效，标记为删除
            doc.is_deleted = True
            doc.deleted_at = now
            # 不加入 valid_docs，此类文档无法正常使用
            continue

        full_path = repo / doc.file_path
        if full_path.exists() and full_path.is_file():
            valid_docs.append(doc)
        else:
            # 文件不存在，自动标记为软删除
            doc.is_deleted = True
            doc.deleted_at = now
            # 记录审计日志（自动标记不指定操作人）
            log = AuditLog(
                user_id=0,
                action="auto_mark_deleted",
                target_type="document",
                target_id=doc.id,
                detail={"reason": "文件在磁盘上已不存在，自动标记为删除", "file_path": doc.file_path},
            )
            session.add(log)

    if len(documents) != len(valid_docs):
        await session.commit()

    return valid_docs


async def _auto_purge_missing_deleted_files(
    session: AsyncSession,
    documents: list[Document],
    repo_path: str,
) -> list[Document]:
    """检测已删除文档列表中的物理文件是否存在于磁盘上，对缺失文件的记录永久删除（硬删除）。

    场景：管理员直接删除了 draft/ 目录下的文件后，已删除文档列表（待恢复）中仍显示这些记录。
    由于文件已不存在，恢复操作无法执行，因此自动清理这些脏数据。

    Args:
        session: 数据库会话
        documents: 已删除的文档列表（is_deleted == True）
        repo_path: 文档仓库根路径

    Returns:
        过滤后的有效已删除文档列表（物理文件仍存在的文档）
    """
    from app.models.document import DocumentPermission

    repo = Path(repo_path)
    valid_docs: list[Document] = []
    purged_ids: list[int] = []

    for doc in documents:
        if not doc.file_path:
            # 没有文件路径，无法恢复，直接硬删除
            purged_ids.append(doc.id)
            continue

        full_path = repo / doc.file_path
        if full_path.exists() and full_path.is_file():
            valid_docs.append(doc)
        else:
            # 文件不存在，永久删除数据库记录
            purged_ids.append(doc.id)

    if purged_ids:
        # 硬删除：先删除关联权限，再删除文档记录
        for pid in purged_ids:
            # 删除关联权限
            perm_stmt = select(DocumentPermission).where(
                DocumentPermission.document_id == pid
            )
            perms = (await session.execute(perm_stmt)).scalars().all()
            for p in perms:
                await session.delete(p)

            # 删除文档记录
            doc_to_delete = next((d for d in documents if d.id == pid), None)
            if doc_to_delete:
                await session.delete(doc_to_delete)

            # 记录审计日志
            log = AuditLog(
                user_id=0,
                action="auto_purge_deleted",
                target_type="document",
                target_id=pid,
                detail={"reason": "文件已在磁盘上被删除，自动清理已删除文档记录"},
            )
            session.add(log)

        await session.commit()
        print(f"[DocService] 自动清理 {len(purged_ids)} 个文件已缺失的已删除文档记录")

    return valid_docs


async def _background_convert_to_pdf(
    doc_id: int,
    full_path: Path,
    full_dir: Path,
    relative_dir: str,
) -> None:
    """后台将 Office 文件转换为 PDF，成功后更新数据库 pdf_path。

    作为独立任务运行，不阻塞上传请求；转换失败仅记录日志，不影响上传。
    """
    try:
        from app.services.pdf_converter import convert_office_to_pdf
        # 后台转换超时放宽到 5 分钟，兼容服务器性能差/大文件场景
        pdf_result = await convert_office_to_pdf(str(full_path), str(full_dir), timeout=300)
        if not pdf_result:
            return
        pdf_relative_path = str(Path(relative_dir) / Path(pdf_result).name)
        from app.database import async_session_factory
        async with async_session_factory() as session:
            doc = await session.get(Document, doc_id)
            if doc is not None:
                doc.pdf_path = pdf_relative_path
                await session.commit()
                print(f"[DocService] 文档 {doc_id} PDF 转换完成：{pdf_relative_path}")
    except Exception as e:
        print(f"[DocService] 文档 {doc_id} 后台 PDF 转换失败：{e}")


async def upload_document(
    session: AsyncSession,
    uploader: User,
    file_content: bytes,
    file_name: str,
    file_type: str,
    doc_data: DocumentCreate,
    ip_address: str = "",
    role_ids: list[int] | None = None,
) -> Document:
    """
    上传文档并保存文件和元信息。

    文件存储逻辑：按 年月/UUID.ext 的目录结构存储到 doc-repo 目录。
    支持文件重复检测：通过 SHA-256 哈希值检测相同内容的文件是否已存在。
    """
    # 计算文件内容 SHA-256 哈希值（用于重复检测）
    import hashlib
    content_hash = hashlib.sha256(file_content).hexdigest()
    print(f"[DocService] 上传文件 SHA-256: {content_hash}")

    # 重复检测：查询是否存在相同哈希值且未删除的文档
    # 使用 first() 而非 scalar_one_or_none()，避免有多个匹配记录时抛出 MultipleResultsFound
    dup_stmt = select(Document).where(
        Document.content_hash == content_hash,
        Document.is_deleted == False,
    ).limit(1)
    dup_result = await session.execute(dup_stmt)
    existing_doc = dup_result.scalar_one_or_none()
    if existing_doc is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"文件内容重复，该文件已存在（文档标题：「{existing_doc.title}」）",
                "duplicate_doc_id": existing_doc.id,
                "duplicate_title": existing_doc.title,
            },
        )

    # 构建存储路径
    today = date.today()
    relative_dir = today.strftime("%Y/%m")
    file_ext = Path(file_name).suffix
    import uuid
    stored_name = f"{uuid.uuid4()}{file_ext}"
    relative_path = str(Path(relative_dir) / stored_name)

    # 获取存储根路径（支持数据库动态配置）
    repo_path = await settings.get_doc_repo_path()
    full_dir = Path(repo_path) / relative_dir
    full_dir.mkdir(parents=True, exist_ok=True)
    full_path = full_dir / stored_name

    # 写入文件
    import aiofiles
    async with aiofiles.open(full_path, "wb") as f:
        await f.write(file_content)

    # 判断是否为 Office 文件（后台异步转换 PDF，不阻塞上传）
    file_ext = Path(file_name).suffix.lower()
    office_extensions = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
    is_office = file_ext in office_extensions

    # 生成文档编号（如果用户未提供）
    doc_no = doc_data.doc_no
    if not doc_no:
        doc_no = await _generate_doc_no(session)

    # 创建文档记录（pdf_path 先置空，转换完成后由后台任务更新）
    document = Document(
        doc_no=doc_no,
        title=doc_data.title,
        summary=doc_data.summary,
        keywords=doc_data.keywords,
        file_path=relative_path,
        file_name=file_name,
        file_size=len(file_content),
        file_type=file_type,
        pdf_path=None,
        content_hash=content_hash,
        version=1,
        status="draft",
        category_id=doc_data.category_id,
        confidential_level=doc_data.confidential_level,
        effective_date=doc_data.effective_date,
        expiry_date=doc_data.expiry_date,
        uploaded_by=uploader.id,
    )
    session.add(document)
    await session.flush()
    await session.refresh(document, ["category", "uploader"])

    # Office 文件后台异步转换 PDF（失败不影响上传成功）
    if is_office:
        asyncio.create_task(
            _background_convert_to_pdf(document.id, full_path, full_dir, relative_dir)
        )

    # 记录审计日志
    await _create_audit_log(
        session, uploader.id, "create", "document", document.id, ip_address,
        {"title": doc_data.title, "file_name": file_name},
    )

    # 文档权限：仅授予上传者显式选择的授权角色
    # 不再自动添加上传者拥有的角色（如业务角色），也不自动继承同分类权限，
    # 权限完全由管理员/上传者在“授权角色”中自由设定
    from app.models.document import DocumentPermission

    granted_role_ids = set(role_ids) if role_ids else set()

    for rid in granted_role_ids:
        perm = DocumentPermission(
            document_id=document.id,
            role_id=rid,
            can_view=True,
            can_download=True,
            can_edit=False,
            granted_by=uploader.id,
        )
        session.add(perm)

    if granted_role_ids:
        await session.flush()

    return document


async def get_document_by_id(session: AsyncSession, doc_id: int, include_deleted: bool = False) -> Document | None:
    """根据ID查询文档，并预加载分类、上传人、权限等关系。
    
    Args:
        include_deleted: 是否包含已删除文档（仅删除/恢复操作需要传 True）
    """
    from app.models.category import Category
    stmt = (
        select(Document)
        .options(
            selectinload(Document.category).selectinload(Category.permissions),
            selectinload(Document.uploader),
            selectinload(Document.permissions),
        )
        .where(Document.id == doc_id)
    )
    if not include_deleted:
        stmt = stmt.where(Document.is_deleted == False)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_documents(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    category_id: int | None = None,
    status_filter: str | None = None,
    uploaded_by: int | None = None,
    confidential_level: str | None = None,
    current_user: User | None = None,
) -> tuple[list[Document], int]:
    """分页查询文档列表。"""
    from app.services.permission_service import get_document_visibility_filter, can_user_download_document
    from app.models.category import Category

    stmt = (
        select(Document)
        .options(
            selectinload(Document.permissions),
            selectinload(Document.category).selectinload(Category.permissions),
        )
        .where(Document.is_deleted == False)
    )
    count_stmt = (
        select(func.count()).select_from(Document)
        .where(Document.is_deleted == False)
    )

    if keyword:
        conditions = (
            Document.title.ilike(f"%{keyword}%")
            | Document.summary.ilike(f"%{keyword}%")
            | Document.keywords.ilike(f"%{keyword}%")
        )
        stmt = stmt.where(conditions)
        count_stmt = count_stmt.where(conditions)
    if category_id:
        stmt = stmt.where(Document.category_id == category_id)
        count_stmt = count_stmt.where(Document.category_id == category_id)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
        count_stmt = count_stmt.where(Document.status == status_filter)
    if confidential_level:
        stmt = stmt.where(Document.confidential_level == confidential_level)
        count_stmt = count_stmt.where(Document.confidential_level == confidential_level)
    if uploaded_by:
        stmt = stmt.where(Document.uploaded_by == uploaded_by)
        count_stmt = count_stmt.where(Document.uploaded_by == uploaded_by)

    # 权限过滤
    if current_user and not current_user.is_superuser:
        visibility = get_document_visibility_filter(current_user)
        if visibility is not None:
            stmt = stmt.where(visibility)
            count_stmt = count_stmt.where(visibility)

    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(page_size)

    result = await session.execute(stmt)
    documents = list(result.scalars().all())

    # 自动检测物理文件缺失的文档，标记为已删除（修复管理员直接删除文件系统文件后列表不更新的问题）
    if documents:
        repo_path = await settings.get_doc_repo_path()
        documents = await _auto_mark_missing_files(session, documents, repo_path)

    # 过滤掉已标记删除的文档（与 list_documents_grouped 保持一致）
    valid_documents = [d for d in documents if not d.is_deleted]

    # 为每个文档计算当前用户的下载权限和是否有PDF预览
    if current_user:
        for doc in valid_documents:
            doc.can_download = can_user_download_document(current_user, doc)
            doc.has_pdf = bool(doc.pdf_path)
    else:
        for doc in valid_documents:
            doc.can_download = False
            doc.has_pdf = bool(doc.pdf_path)

    return valid_documents, total


async def list_documents_grouped(
    session: AsyncSession,
    keyword: str | None = None,
    category_id: int | None = None,
    status_filter: str | None = None,
    confidential_level: str | None = None,
    current_user: User | None = None,
    page: int = 1,
    page_size: int = 30,
) -> list[dict]:
    """按分类分组查询文档列表，每个分类内独立分页（每页 page_size 条）。

    返回格式：
    [
        {"id": cat_id, "name": "分类名", "documents": [...], "total": 该分类总数},
        ...
    ]
    """
    from app.services.permission_service import get_document_visibility_filter, can_user_download_document

    # 构建基础过滤条件（默认排除已删除文档）
    base_conditions = [Document.is_deleted == False]
    if keyword:
        base_conditions.append(
            Document.title.ilike(f"%{keyword}%")
            | Document.summary.ilike(f"%{keyword}%")
            | Document.keywords.ilike(f"%{keyword}%")
        )
    if status_filter:
        base_conditions.append(Document.status == status_filter)
    if confidential_level:
        base_conditions.append(Document.confidential_level == confidential_level)

    # 权限过滤条件
    visibility_filter = None
    if current_user and not current_user.is_superuser:
        visibility_filter = get_document_visibility_filter(current_user)

    # 查询需要显示的分类
    cat_stmt = select(Category).order_by(Category.sort_order, Category.name)
    if category_id:
        cat_stmt = cat_stmt.where(Category.id == category_id)
    cat_result = await session.execute(cat_stmt)
    categories = list(cat_result.scalars().all())

    groups: list[dict] = []

    for cat in categories:
        # 统计该分类总数
        cat_total_stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.category_id == cat.id, *base_conditions)
        )
        if visibility_filter is not None:
            cat_total_stmt = cat_total_stmt.where(visibility_filter)
        cat_total = (await session.execute(cat_total_stmt)).scalar() or 0

        if cat_total == 0:
            continue

        # 该分类当页文档
        cat_docs_stmt = (
            select(Document)
            .options(selectinload(Document.permissions))
            .where(Document.category_id == cat.id)
            .order_by(Document.created_at.desc())
        )
        for cond in base_conditions:
            cat_docs_stmt = cat_docs_stmt.where(cond)
        if visibility_filter is not None:
            cat_docs_stmt = cat_docs_stmt.where(visibility_filter)

        offset = (page - 1) * page_size
        cat_docs_stmt = cat_docs_stmt.offset(offset).limit(page_size)
        cat_result = await session.execute(cat_docs_stmt)
        docs = list(cat_result.scalars().all())

        if docs:
            repo_path = await settings.get_doc_repo_path()
            docs = await _auto_mark_missing_files(session, docs, repo_path)

        valid_docs = []
        for doc in docs:
            if doc.is_deleted:
                continue
            doc.has_pdf = bool(doc.pdf_path)
            if current_user:
                doc.can_download = can_user_download_document(current_user, doc)
            else:
                doc.can_download = False
            valid_docs.append(doc)

        groups.append({
            "id": cat.id,
            "name": cat.name,
            "total": cat_total,
            "documents": valid_docs,
        })

    # 未分类文档
    if not category_id:
        uncat_total_stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.category_id.is_(None), *base_conditions)
        )
        if visibility_filter is not None:
            uncat_total_stmt = uncat_total_stmt.where(visibility_filter)
        uncat_total = (await session.execute(uncat_total_stmt)).scalar() or 0

        if uncat_total > 0:
            uncat_stmt = (
                select(Document)
                .options(selectinload(Document.permissions))
                .where(Document.category_id.is_(None), *base_conditions)
            )
            if visibility_filter is not None:
                uncat_stmt = uncat_stmt.where(visibility_filter)
            uncat_stmt = uncat_stmt.order_by(Document.created_at.desc())
            offset = (page - 1) * page_size
            uncat_stmt = uncat_stmt.offset(offset).limit(page_size)
            uncat_result = await session.execute(uncat_stmt)
            uncat_docs = list(uncat_result.scalars().all())

            if uncat_docs:
                repo_path = await settings.get_doc_repo_path()
                uncat_docs = await _auto_mark_missing_files(session, uncat_docs, repo_path)

            valid_uncat = []
            for doc in uncat_docs:
                if doc.is_deleted:
                    continue
                doc.has_pdf = bool(doc.pdf_path)
                if current_user:
                    doc.can_download = can_user_download_document(current_user, doc)
                else:
                    doc.can_download = False
                valid_uncat.append(doc)

            groups.append({
                "id": None,
                "name": "未分类",
                "total": uncat_total,
                "documents": valid_uncat,
            })

    return groups


async def update_document(
    session: AsyncSession,
    doc_id: int,
    doc_data: DocumentUpdate,
    operator_id: int = 0,
    ip_address: str = "",
) -> Document:
    """更新文档元信息。"""
    document = await get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    update_data = doc_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    await session.flush()
    await session.refresh(document, ["category", "uploader"])

    await _create_audit_log(
        session, operator_id, "update", "document", doc_id, ip_address, update_data,
    )

    return document


async def review_document(
    session: AsyncSession,
    doc_id: int,
    reviewer: User,
    review_data: DocumentReview,
    ip_address: str = "",
) -> Document:
    """审核文档。"""
    from datetime import datetime, timezone

    document = await get_document_by_id(session, doc_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    if document.status not in ("pending_review", "reviewing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档当前状态不允许审核",
        )

    new_status = review_data.status
    if new_status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="审核状态只能是 approved 或 rejected",
        )

    document.status = new_status
    await session.flush()

    await _create_audit_log(
        session, reviewer.id, "review", "document", doc_id, ip_address,
        {"status": new_status, "comment": review_data.comment},
    )

    await session.refresh(document, ["category", "uploader"])
    return document


async def _move_file_to_draft(
    repo_path: str, relative_path: str,
) -> str | None:
    """将文件从原位置移动到 draft/ 目录下，返回新的相对路径（含 draft/ 前缀）。"""
    import shutil

    full_path = Path(repo_path) / relative_path
    print(f"[DocService] _move_file_to_draft: repo_path={repo_path}, relative_path={relative_path}")
    print(f"[DocService] _move_file_to_draft: full_path={full_path}, exists={full_path.exists()}")

    if not full_path.exists():
        print(f"[DocService] _move_file_to_draft: 源文件不存在，跳过移动")
        return None

    # 构建 draft 目录下相同相对路径
    # relative_path 形如 "2026/08/uuid.ext" → draft_rel = "draft/2026/08/uuid.ext"
    # 注意 Windows 路径分隔符：数据库中 file_path 可能用 / 或 \
    # 统一用 / 拼接 draft 前缀
    normalized_rel = relative_path.replace("\\", "/")
    draft_rel = f"draft/{normalized_rel}"
    draft_full = Path(repo_path) / draft_rel

    print(f"[DocService] _move_file_to_draft: draft_rel={draft_rel}")
    print(f"[DocService] _move_file_to_draft: draft_full={draft_full}")

    # 创建 draft 目标目录
    try:
        draft_full.parent.mkdir(parents=True, exist_ok=True)
        print(f"[DocService] _move_file_to_draft: 目标目录已创建 {draft_full.parent}")
    except Exception as e:
        print(f"[DocService] _move_file_to_draft: 创建目录失败: {e}")
        return None

    try:
        # 如果目标已存在，先删除
        if draft_full.exists():
            draft_full.unlink()
        # 使用 shutil.move 代替 Path.rename
        # shutil.move 在 Windows 上更可靠：rename 失败时会自动回退到 copy+delete
        shutil.move(str(full_path), str(draft_full))
        print(f"[DocService] _move_file_to_draft: 文件移动成功 → {draft_full}")
        return draft_rel
    except Exception as e:
        print(f"[DocService] _move_file_to_draft: 文件移动失败: {e}")
        return None


async def _move_file_from_draft(
    repo_path: str, draft_relative_path: str,
) -> str | None:
    """将文件从 draft/ 目录移回原位置，返回原始相对路径。"""
    import shutil

    # draft_relative_path 形如 "draft/2026/08/uuid.ext"
    normalized = draft_relative_path.replace("\\", "/")
    if not normalized.startswith("draft/"):
        print(f"[DocService] _move_file_from_draft: 路径不以 draft/ 开头: {draft_relative_path}")
        return None

    original_rel = normalized[6:]  # 去掉 "draft/" 前缀
    draft_full = Path(repo_path) / draft_relative_path
    print(f"[DocService] _move_file_from_draft: draft_full={draft_full}, exists={draft_full.exists()}")

    if not draft_full.exists():
        print(f"[DocService] _move_file_from_draft: draft 中文件不存在")
        return None

    original_full = Path(repo_path) / original_rel
    original_full.parent.mkdir(parents=True, exist_ok=True)

    try:
        if original_full.exists():
            original_full.unlink()
        shutil.move(str(draft_full), str(original_full))
        print(f"[DocService] _move_file_from_draft: 文件恢复成功 → {original_full}")
        return original_rel
    except Exception as e:
        print(f"[DocService] _move_file_from_draft: 文件恢复失败: {e}")
        return None


async def delete_document(
    session: AsyncSession,
    doc_id: int,
    operator_id: int = 0,
    ip_address: str = "",
) -> None:
    """软删除文档：将文件移动到 draft/ 目录，标记为已删除。"""
    from datetime import datetime, timezone

    document = await get_document_by_id(session, doc_id, include_deleted=True)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )
    if document.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档已被删除，无需重复操作",
        )

    repo_path = await settings.get_doc_repo_path()

    # 移动原始文件到 draft/ 目录
    if document.file_path:
        new_path = await _move_file_to_draft(repo_path, document.file_path)
        if new_path:
            document.file_path = new_path

    # 移动 PDF 预览文件到 draft/ 目录
    if document.pdf_path:
        new_pdf_path = await _move_file_to_draft(repo_path, document.pdf_path)
        if new_pdf_path:
            document.pdf_path = new_pdf_path

    # 标记为已删除
    document.is_deleted = True
    document.deleted_at = beijing_now()
    await session.flush()

    await _create_audit_log(session, operator_id, "delete", "document", doc_id, ip_address)


async def restore_document(
    session: AsyncSession,
    doc_id: int,
    operator_id: int = 0,
    ip_address: str = "",
) -> Document:
    """恢复已删除的文档：将文件从 draft/ 目录移回原位置，清除删除标记。"""
    document = await get_document_by_id(session, doc_id, include_deleted=True)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )
    if not document.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档未被删除，无需恢复",
        )

    repo_path = await settings.get_doc_repo_path()

    # 检查文件是否存在（防止管理员直接删除 draft/ 下文件后仍然尝试恢复）
    if document.file_path:
        full_path = Path(repo_path) / document.file_path
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件的物理文件已从磁盘上删除，无法恢复。建议联系管理员确认数据是否可找回。",
            )

    # 还原原始文件
    if document.file_path:
        original_path = await _move_file_from_draft(repo_path, document.file_path)
        if original_path:
            document.file_path = original_path

    # 还原 PDF 预览文件
    if document.pdf_path:
        original_pdf = await _move_file_from_draft(repo_path, document.pdf_path)
        if original_pdf:
            document.pdf_path = original_pdf

    # 清除删除标记
    document.is_deleted = False
    document.deleted_at = None
    await session.flush()

    await _create_audit_log(session, operator_id, "restore", "document", doc_id, ip_address)
    return document


async def list_deleted_documents(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> tuple[list[Document], int]:
    """分页查询已删除的文档（仅管理员使用）。"""
    stmt = (
        select(Document)
        .options(
            selectinload(Document.category),
            selectinload(Document.uploader),
        )
        .where(Document.is_deleted == True)
        .order_by(Document.deleted_at.desc())
    )
    count_stmt = (
        select(func.count()).select_from(Document)
        .where(Document.is_deleted == True)
    )

    if keyword:
        condition = (
            Document.title.ilike(f"%{keyword}%")
            | Document.doc_no.ilike(f"%{keyword}%")
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await session.execute(stmt)
    documents = list(result.scalars().all())

    # 自动检测已删除文档的物理文件是否缺失，对缺失文件记录执行永久删除
    if documents:
        repo_path = await settings.get_doc_repo_path()
        documents = await _auto_purge_missing_deleted_files(session, documents, repo_path)

    # 清理后重新计算总数（物理文件缺失的记录已被硬删除）
    return documents, len(documents)


async def get_recent_documents(
    session: AsyncSession,
    limit: int = 10,
    current_user: User | None = None,
) -> list[Document]:
    """获取当前用户可见的最近上传文档。"""
    from app.services.permission_service import get_document_visibility_filter

    stmt = select(Document).where(Document.is_deleted == False).order_by(Document.created_at.desc()).limit(limit)
    if current_user and not current_user.is_superuser:
        visibility = get_document_visibility_filter(current_user)
        if visibility is not None:
            stmt = stmt.where(visibility)

    result = await session.execute(stmt)
    documents = list(result.scalars().all())

    # 自动检测物理文件缺失的文档，标记为已删除
    if documents:
        repo_path = await settings.get_doc_repo_path()
        documents = await _auto_mark_missing_files(session, documents, repo_path)

    return documents


async def get_pending_review_documents(
    session: AsyncSession,
    limit: int = 10,
    current_user: User | None = None,
) -> list[Document]:
    """获取当前用户可见的待审核文档。"""
    from app.services.permission_service import get_document_visibility_filter

    stmt = (
        select(Document)
        .where(Document.is_deleted == False)
        .where(Document.status.in_(["pending_review", "reviewing"]))
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    if current_user and not current_user.is_superuser:
        visibility = get_document_visibility_filter(current_user)
        if visibility is not None:
            stmt = stmt.where(visibility)

    result = await session.execute(stmt)
    documents = list(result.scalars().all())

    # 自动检测物理文件缺失的文档，标记为已删除
    if documents:
        repo_path = await settings.get_doc_repo_path()
        documents = await _auto_mark_missing_files(session, documents, repo_path)

    return documents


async def _generate_doc_no(session: AsyncSession) -> str:
    """生成文档编号。格式：YYYYMM-NNN"""
    today_str = date.today().strftime("%Y%m")
    prefix = f"{today_str}-"

    # 查询本月已有的最大编号
    stmt = (
        select(func.count())
        .select_from(Document)
        .where(Document.doc_no.like(f"{prefix}%"))
    )
    count = (await session.execute(stmt)).scalar() or 0
    return f"{prefix}{count + 1:03d}"


async def _create_audit_log(
    session: AsyncSession,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    ip_address: str = "",
    detail: dict | None = None,
) -> None:
    """记录审计日志。"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        detail=detail,
    )
    session.add(log)


async def _inherit_category_role_permissions(
    session: AsyncSession,
    document: Document,
    granted_by: int,
) -> None:
    """分类权限继承：查询同分类下已有文档的角色权限，取最大权限自动授予新文档。"""
    from app.models.document import DocumentPermission

    if not document.category_id:
        return

    # 查询同分类下所有文档的角色权限
    stmt = (
        select(DocumentPermission)
        .join(Document, DocumentPermission.document_id == Document.id)
        .where(
            Document.category_id == document.category_id,
            DocumentPermission.role_id.isnot(None),
        )
    )
    result = await session.execute(stmt)
    existing_perms = list(result.scalars().all())

    if not existing_perms:
        return

    # 按 role_id 聚合，取每个角色的最大权限
    role_max_perms: dict[int, dict[str, bool]] = {}
    for p in existing_perms:
        rid = p.role_id
        if rid not in role_max_perms:
            role_max_perms[rid] = {
                "can_view": False,
                "can_download": False,
                "can_edit": False,
                "can_print": False,
            }
        rp = role_max_perms[rid]
        rp["can_view"] = rp["can_view"] or p.can_view
        rp["can_download"] = rp["can_download"] or p.can_download
        rp["can_edit"] = rp["can_edit"] or p.can_edit
        rp["can_print"] = rp["can_print"] or p.can_print

    # 为新文档创建继承的权限记录（跳过已存在的）
    for rid, perms in role_max_perms.items():
        # 检查是否已有该角色的权限记录
        check_stmt = select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.role_id == rid,
        )
        check_result = await session.execute(check_stmt)
        if check_result.scalar_one_or_none() is not None:
            continue

        perm = DocumentPermission(
            document_id=document.id,
            role_id=rid,
            can_view=perms["can_view"],
            can_download=perms["can_download"],
            can_edit=perms["can_edit"],
            can_print=perms["can_print"],
            granted_by=granted_by,
        )
        session.add(perm)

    await session.flush()