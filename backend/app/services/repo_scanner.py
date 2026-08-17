"""
文档仓库扫描和修复工具

启动时自动扫描 doc-repo 目录：
1. 为已有Office文档查找对应的PDF预览文件（按存储文件名UUID匹配，同目录下扩展名替换为.pdf）
2. 检查文件路径是否有效，修正不存在的路径
3. 不做重复转换，只更新数据库关联
"""
import asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


OFFICE_EXTS = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}


def find_existing_pdf(repo: Path, file_path: str) -> Path | None:
    """
    根据原始文件存储路径，查找磁盘上已存在的PDF预览文件。

    查找顺序：
    1. 同目录下同名（UUID）.pdf（LibreOffice默认输出）
    2. 递归搜索仓库中同名PDF（处理文件被移动的情况）

    Returns:
        PDF文件的绝对路径，未找到返回None
    """
    if not file_path:
        return None

    stored_full = repo / file_path
    if not stored_full.exists():
        # 文件本身不存在，尝试按存储文件名搜索
        stored_name = Path(file_path).name
        found_original = None
        for candidate in repo.rglob(stored_name):
            if candidate.is_file():
                found_original = candidate
                break
        if not found_original:
            return None
        stored_full = found_original

    # 1. 同目录同名PDF
    pdf_same_dir = stored_full.with_suffix('.pdf')
    if pdf_same_dir.exists() and pdf_same_dir.is_file():
        return pdf_same_dir

    # 2. 递归搜索同名PDF
    stored_stem = stored_full.stem
    for candidate in repo.rglob(f"{stored_stem}.pdf"):
        if candidate.is_file():
            return candidate

    return None


def _candidate_pdf_paths(repo: Path, file_path: str) -> list[Path]:
    """根据原始文件存储路径，推导可能的PDF文件路径（按优先级排序）"""
    candidates = []
    if not file_path:
        return candidates

    stored = Path(file_path)
    stored_full = repo / stored

    # 1. 最高优先级：同目录下，同名（UUID）.pdf（LibreOffice默认输出格式）
    #    例如 doc-repo/2024/08/uuid.docx -> doc-repo/2024/08/uuid.pdf
    pdf_same_dir = stored_full.with_suffix('.pdf')
    candidates.append(pdf_same_dir)

    # 2. 如果上述不存在，递归在仓库中搜索同名PDF（防止文件被移动到子目录）
    #    这一步成本较高，只在主路径找不到时使用
    return candidates


async def scan_and_repair_doc_repo(session: AsyncSession, repo_path: str) -> dict:
    """
    扫描文档仓库，修复数据库中的文件路径和PDF关联。

    查找规则：对于Office文件，PDF文件的文件名与存储文件相同（UUID），仅扩展名不同。
    例如 uuid.docx 转换后是 uuid.pdf，通常在同一目录下。

    Returns:
        dict: 扫描结果统计
    """
    from app.models.document import Document

    repo = Path(repo_path)
    if not repo.exists():
        return {"scanned": 0, "pdf_linked": 0, "missing_files": 0, "repaired_paths": 0}

    result = {
        "scanned": 0,
        "pdf_linked": 0,
        "missing_files": 0,
        "repaired_paths": 0,
    }

    # 查询所有文档
    stmt = select(Document)
    docs = (await session.execute(stmt)).scalars().all()

    for doc in docs:
        result["scanned"] += 1

        # 1. 检查原始文件是否存在
        file_ok = False
        full_path = None
        if doc.file_path:
            full_path = repo / doc.file_path
            if full_path.exists() and full_path.is_file():
                file_ok = True
            else:
                # 尝试通过UUID文件名查找（文件可能被移动）
                file_stored_name = Path(doc.file_path).name
                found = None
                for candidate in repo.rglob(file_stored_name):
                    if candidate.is_file():
                        found = candidate
                        break
                if found:
                    rel = found.relative_to(repo)
                    doc.file_path = str(rel).replace('\\', '/')
                    result["repaired_paths"] += 1
                    file_ok = True
                    full_path = found

        if not file_ok:
            result["missing_files"] += 1
            continue

        # 2. 检查/修复PDF预览路径
        file_ext = Path(doc.file_name).suffix.lower() if doc.file_name else ''
        stored_ext = Path(doc.file_path).suffix.lower() if doc.file_path else ''

        is_office = file_ext in OFFICE_EXTS or stored_ext in OFFICE_EXTS
        is_pdf = file_ext == '.pdf' or stored_ext == '.pdf'

        if not (is_office or is_pdf):
            continue

        # 检查现有pdf_path是否有效
        pdf_ok = False
        if doc.pdf_path:
            pdf_full = repo / doc.pdf_path
            if pdf_full.exists() and pdf_full.is_file():
                pdf_ok = True

        if pdf_ok:
            continue  # 已有有效PDF路径，跳过

        # PDF文件：pdf_path直接指向原文件
        if is_pdf:
            doc.pdf_path = doc.file_path
            result["pdf_linked"] += 1
            continue

        # Office文件：基于存储路径查找同目录同名PDF（UUID命名）
        if full_path:
            pdf_candidate = find_existing_pdf(repo, doc.file_path)
            if pdf_candidate:
                rel_pdf = pdf_candidate.relative_to(repo)
                doc.pdf_path = str(rel_pdf).replace('\\', '/')
                result["pdf_linked"] += 1

    await session.commit()
    return result


async def run_startup_repair():
    """在应用启动时后台运行文档仓库修复"""
    try:
        from app.database import async_session_factory
        from app.config import settings

        repo_path = await settings.get_doc_repo_path()
        print(f"[Startup Scan] 开始扫描文档仓库: {repo_path}")

        async with async_session_factory() as session:
            result = await scan_and_repair_doc_repo(session, repo_path)

        print(
            f"[Startup Scan] 扫描完成 — 共检查 {result['scanned']} 个文档, "
            f"关联PDF {result['pdf_linked']} 个, "
            f"修复路径 {result['repaired_paths']} 个, "
            f"缺失文件 {result['missing_files']} 个"
        )
    except Exception as e:
        print(f"[Startup Scan] 扫描异常（不影响启动）: {e}")


def run_startup_repair_in_background():
    """在后台线程中运行异步修复任务"""
    def _runner():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_startup_repair())
            loop.close()
        except Exception as e:
            print(f"[Startup Scan] 后台扫描失败: {e}")

    import threading
    t = threading.Thread(target=_runner, daemon=True, name="doc-repo-scan")
    t.start()
