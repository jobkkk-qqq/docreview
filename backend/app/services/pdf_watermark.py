"""
PDF 水印工具

为非公开文档的预览添加水印（用户名 + 年月日）。
水印使用 PyMuPDF (fitz) 渲染，生成临时文件，预览完成后由调用方清理。
"""
import logging
import tempfile
import os
from pathlib import Path

from app.core.timezone import beijing_now

logger = logging.getLogger(__name__)

try:
    import pymupdf as fitz
    _FITZ_AVAILABLE = True
except ImportError:
    try:
        import fitz
        _FITZ_AVAILABLE = True
    except ImportError:
        _FITZ_AVAILABLE = False
        fitz = None


def add_watermark_to_pdf(
    pdf_path: str,
    display_name: str,
    output_path: str | None = None,
) -> str:
    """为 PDF 添加水印，水印内容为用户名 + 年月日（斜体居中旋转）。

    Args:
        pdf_path: 源 PDF 文件路径
        display_name: 用户名（显示名称）
        output_path: 输出路径，不传则自动创建临时文件

    Returns:
        水印后的 PDF 文件路径

    Raises:
        RuntimeError: 当 PyMuPDF 不可用或水印处理失败时
    """
    if not _FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF 未安装，无法添加水印")

    watermark_text = f"{display_name} {beijing_now().strftime('%Y%m%d')}"

    doc = fitz.open(pdf_path)

    try:
        for page in doc:
            rect = page.rect
            w, h = rect.width, rect.height

            # 创建 45° 旋转矩阵
            rot_matrix = fitz.Matrix(45)

            # 在页面多个位置添加水印，形成覆盖全页的水印阵列
            step = 200
            for x in range(-int(w), int(w) + step, step):
                for y in range(-int(h), int(h) + step, step):
                    page.insert_text(
                        point=fitz.Point(x, y),
                        text=watermark_text,
                        fontsize=17,
                        fontname="china-s",
                        color=(0.90, 0.90, 0.90),
                        morph=(fitz.Point(x, y), rot_matrix),
                        overlay=True,
                    )

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            output_path = tmp.name
            tmp.close()

        doc.save(output_path, garbage=4, deflate=True)
        return output_path
    finally:
        doc.close()


def cleanup_temp_pdf(file_path: str) -> None:
    """清理临时 PDF 文件"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except OSError:
        pass