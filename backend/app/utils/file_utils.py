"""
文件操作工具模块

提供安全的文件上传、存储路径构建、文件类型校验等功能。
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status, UploadFile

from app.config import settings


# 允许上传的文件类型（MIME type → 扩展名映射）
ALLOWED_FILE_TYPES: dict[str, list[str]] = {
    # 文档类
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/vnd.ms-excel": [".xls"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "application/vnd.ms-powerpoint": [".ppt"],
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
    # 纯文本
    "text/plain": [".txt"],
    "text/csv": [".csv"],
    "text/markdown": [".md"],
    # 图片
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
}

# 最大文件大小（字节），从配置读取
MAX_FILE_SIZE: int = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def validate_file_type(file: UploadFile) -> str:
    """
    校验上传文件的 MIME 类型是否在允许列表中。

    Args:
        file: FastAPI UploadFile 对象

    Returns:
        文件扩展名（含点号，如 ".pdf"）

    Raises:
        HTTPException 400: 文件类型不支持
    """
    content_type = file.content_type or ""
    if content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}",
        )
    return ALLOWED_FILE_TYPES[content_type][0]


async def validate_file_size(file: UploadFile) -> int:
    """
    校验上传文件大小是否超过限制。

    Args:
        file: FastAPI UploadFile 对象

    Returns:
        文件大小（字节）

    Raises:
        HTTPException 400: 文件大小超过限制
    """
    # 先读取文件内容到内存以计算大小（小文件场景）
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {settings.MAX_UPLOAD_SIZE_MB}MB）",
        )
    # 重置文件指针，以便后续再次读取
    await file.seek(0)
    return file_size


def get_safe_filename(original_filename: str) -> str:
    """
    生成安全的存储文件名。

    使用 UUID 替换原始文件名，防止路径遍历攻击。

    Args:
        original_filename: 原始文件名

    Returns:
        安全的文件名（UUID + 原始扩展名）
    """
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4()}{ext}"


def build_storage_path(sub_dir: str, filename: str) -> str:
    """
    构建文件存储的相对路径。

    Args:
        sub_dir: 子目录（如分类名或日期目录）
        filename: 文件名

    Returns:
        相对于存储根目录的路径
    """
    return str(Path(sub_dir) / filename)


async def get_repo_path() -> str:
    """
    获取当前生效的文档仓库根路径。

    Returns:
        文档仓库的绝对路径
    """
    return await settings.get_doc_repo_path()


def ensure_directory(path: str) -> Path:
    """
    确保目录存在，不存在则创建。

    Args:
        path: 目录路径

    Returns:
        Path 对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path