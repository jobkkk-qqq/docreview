"""
PDF 转换服务
将 Office 文件（Word、Excel、PPT）转换为 PDF 用于预览
使用 LibreOffice 命令行进行转换
"""

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional


def _get_app_dir() -> Path:
    """获取应用程序根目录（支持 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent.parent


def _build_libreoffice_candidates() -> list[str]:
    """生成 LibreOffice 可执行文件候选列表。

    Windows 下优先使用 soffice.com（控制台版本），它是为命令行无头转换设计的，
    soffice.exe 是 GUI 子系统程序，通过 subprocess 带管道调用时在无交互会话的
    服务器上容易初始化失败或挂起。
    """
    candidates: list[str] = []
    base_dirs = [
        Path(r"C:\Program Files\LibreOffice\program"),
        Path(r"C:\Program Files (x86)\LibreOffice\program"),
        # 便携版/程序目录下的 LibreOffice
        _get_app_dir() / "libreoffice" / "program",
        _get_app_dir() / "LibreOffice" / "program",
    ]
    for base in base_dirs:
        if sys.platform == "win32":
            com = base / "soffice.com"
            exe = base / "soffice.exe"
            if com.is_file():
                candidates.append(str(com))
            if exe.is_file():
                candidates.append(str(exe))
        else:
            candidates.append(str(base / "soffice"))
    # PATH 中的 soffice
    candidates.append("soffice")
    return candidates


# LibreOffice 可执行文件候选列表（动态构建）
LIBREOFFICE_PATHS = _build_libreoffice_candidates()


def get_libreoffice_path() -> Optional[str]:
    """查找 LibreOffice 可执行文件路径"""
    for path in LIBREOFFICE_PATHS:
        if path == "soffice":
            # 检查 PATH 中是否有 soffice
            try:
                subprocess.run(["soffice", "--version"], capture_output=True, timeout=5)
                return "soffice"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        elif os.path.isfile(path):
            return path
    return None


def is_libreoffice_available() -> bool:
    """检查 LibreOffice 是否可用"""
    return get_libreoffice_path() is not None


async def _kill_process_tree(process) -> None:
    """强制终止 LibreOffice 进程树（Windows 用 taskkill /T /F 杀子进程）"""
    try:
        if process is None or process.returncode is not None:
            return
        if sys.platform == "win32":
            kill_proc = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/T", "/PID", str(process.pid),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(kill_proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass
        else:
            process.kill()
        # 等待进程真正退出，避免文件句柄残留
        try:
            await asyncio.wait_for(process.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass
    except Exception:
        pass


# 全局转换锁：LibreOffice 使用默认 profile（单实例），并发转换会互相等待锁，
# 用程序内锁串行化，避免互锁挂起。对异步后台转换场景影响很小。
_convert_lock = asyncio.Lock()


async def convert_to_pdf(
    input_file: str,
    output_dir: str,
    timeout: int = 60
) -> Optional[str]:
    """
    将 Office 文件转换为 PDF

    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        timeout: 转换超时时间（秒）

    Returns:
        转换后的 PDF 文件路径，失败返回 None
    """
    libreoffice_path = get_libreoffice_path()
    if not libreoffice_path:
        print("[PDF Converter] LibreOffice 未安装，跳过转换")
        return None

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"[PDF Converter] 输入文件不存在：{input_file}")
        return None

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 构建 LibreOffice 命令。
    # 注意：不使用 -env:UserInstallation 独立 profile 参数——服务器上该参数
    # 可能导致 LibreOffice 初始化挂起（临时目录 .lo_xxx 卡住不消失）。
    # 与手动 CMD 成功命令保持一致，用默认 profile + 程序内串行锁避免并发互锁。
    cmd = [
        libreoffice_path,
        "--headless",
        "--norestore",
        "--nofirststartwizard",
        "--convert-to", "pdf",
        "--outdir", str(output_path),
        str(input_path)
    ]

    async with _convert_lock:
        process = None
        try:
            # 记录转换开始信息（便于服务器上排查）
            size_mb = input_path.stat().st_size / (1024 * 1024) if input_path.exists() else 0
            print(f"[PDF Converter] 开始转换：{input_file}（{size_mb:.1f}MB，超时{timeout}秒）")

            # Windows 下使用 CREATE_NO_WINDOW 标志，避免弹出控制台黑窗口
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            # 运行转换命令。
            # 注意：stdout/stderr 不使用 PIPE 管道捕获——LibreOffice 在输出被重定向到
            # 管道时可能挂起（手动在 CMD 中执行正常，subprocess 捕获输出时异常）。
            # 改用 DEVNULL，配合下方"轮询 PDF 文件生成"来判断转换是否完成。
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                creationflags=creation_flags,
            )

            # 查找目标 PDF 路径
            pdf_file = output_path / f"{input_path.stem}.pdf"

            # 轮询等待：PDF 生成 / 进程退出 / 超时 三选一。
            # 关键：soffice 转换完成后可能不退出进程（黑窗口不关），
            # 因此以"PDF 文件是否生成"为准，生成后立即终止进程并返回。
            import time
            start_time = time.monotonic()
            while time.monotonic() - start_time < timeout:
                if pdf_file.exists():
                    break
                if process.returncode is not None:
                    break
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass

            if pdf_file.exists():
                # PDF 已生成：终止可能残留的进程后返回成功
                await _kill_process_tree(process)
                print(f"[PDF Converter] 转换成功：{pdf_file}")
                return str(pdf_file)

            if process.returncode is not None:
                print(f"[PDF Converter] 转换失败（返回码{process.returncode}）")
                return None

            # 超时且无 PDF
            print(f"[PDF Converter] 转换超时（{timeout}秒），PDF 未生成，强制终止 LibreOffice 进程")
            await _kill_process_tree(process)
            return None

        except Exception as e:
            print(f"[PDF Converter] 转换异常：{e}")
            return None
        finally:
            # 无论成功失败，都终止残留进程，避免文件句柄残留
            await _kill_process_tree(process)


async def convert_office_to_pdf(
    input_file: str,
    output_dir: str,
    timeout: int = 60
) -> Optional[str]:
    """
    将 Office 文件转换为 PDF（仅处理 Office 格式）

    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        timeout: 转换超时时间（秒），默认 60

    Returns:
        转换后的 PDF 文件路径，非 Office 文件或失败返回 None
    """
    input_path = Path(input_file)
    ext = input_path.suffix.lower()

    # 只处理 Office 文件
    office_extensions = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
    if ext not in office_extensions:
        return None

    return await convert_to_pdf(input_file, output_dir, timeout=timeout)
