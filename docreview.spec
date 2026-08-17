# -*- mode: python ; coding: utf-8 -*-
"""
DocReview V1.0 — PyInstaller 打包配置
在 Windows 上运行: pyinstaller docreview.spec
"""
import sys
from pathlib import Path

# PyInstaller 工具函数：递归收集子模块和数据
from PyInstaller.utils.hooks import collect_submodules, collect_all

block_cipher = None

# 项目根目录（PyInstaller 执行 spec 时提供 SPECPATH）
ROOT = Path(SPECPATH)

# 将 backend 加入当前 Python 路径，确保 collect_submodules('app') 能正确定位
sys.path.insert(0, str(ROOT / 'backend'))

# ── 递归收集关键包的子模块（解决延迟导入导致的漏打包）────────────────
_uvicorn_hidden = collect_submodules('uvicorn')
_fastapi_hidden = collect_submodules('fastapi')
_starlette_hidden = collect_submodules('starlette')
_backend_hidden = collect_submodules('backend')
_app_hidden = collect_submodules('app')

# 收集 uvicorn / fastapi / starlette 的数据文件与二进制依赖
_uvicorn_datas, _uvicorn_bins, _ = collect_all('uvicorn')
_fastapi_datas, _fastapi_bins, _ = collect_all('fastapi')
_starlette_datas, _starlette_bins, _ = collect_all('starlette')
_fitz_datas, _fitz_bins, _fitz_hidden = collect_all('fitz')

a = Analysis(
    ['main_win.py'],
    pathex=[str(ROOT)],
    binaries=_uvicorn_bins + _fastapi_bins + _starlette_bins + _fitz_bins,
    datas=[
        # 仅嵌入后端 Python 代码；数据库和前端静态资源作为外部文件随包分发，便于持久化
        (str(ROOT / 'backend' / 'app'), 'backend/app'),
        (str(ROOT / 'backend' / 'main.py'), 'backend'),
        # 该模块在 backend 目录下，但 main_win.py 通过 sys.path 将其作为顶层模块导入，
        # 因此需要放到打包根目录，确保运行时可导入
        (str(ROOT / 'backend' / 'serve_frontend_3000.py'), '.'),
        # 系统托盘模块
        (str(ROOT / 'tray_app.py'), '.'),
    ] + _uvicorn_datas + _fastapi_datas + _starlette_datas + _fitz_datas,
    hiddenimports=[
        'serve_frontend_3000',
        'tray_app',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websocket',
        'uvicorn.protocols.websocket.auto',
        'uvicorn.middleware',
        'sqlalchemy',
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.sql.default_comparator',
        'aiosqlite',
        'aiofiles',
        'bcrypt',
        'jose',
        'jose.jwt',
        'jose.exceptions',
        'jose.constants',
        'jose.backends',
        'jose.utils',
        'pydantic',
        'pydantic_core',
        'yaml',
        'asyncio',
        'multipart',
        'email_validator',
        'fitz',
        'fastapi',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'starlette',
        'starlette.middleware',
        'starlette.middleware.cors',
    ] + _uvicorn_hidden + _fastapi_hidden + _starlette_hidden + _backend_hidden + _app_hidden + _fitz_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'unittest',
        'distutils',
        'setuptools',
        'pip',
        'wheel',
        'cryptography',
        '_cffi_backend',
        # 排除 TRAE 环境中多余的大包，减小体积并加快打包
        'IPython',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'jedi',
        'parso',
        'pygments',
        'sphinx',
        'docutils',
        'pytest',
        'black',
        'mypy',
        'pylint',
        'flake8',
        'jupyter',
        'notebook',
        'seaborn',
        'sklearn',
        'PIL',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DocReview',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # 不显示控制台窗口，通过系统托盘运行
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'icon.ico') if (ROOT / 'icon.ico').exists() else None,
    uac_admin=False,       # 不请求管理员权限（程序目录可写即可）
)
