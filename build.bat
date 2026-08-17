@echo off
chcp 65001 >nul
title DocReview V1.0 — Windows 构建工具
echo ═══════════════════════════════════════════════
echo   DocReview V1.0 — Windows 安装包构建
echo ═══════════════════════════════════════════════
echo.

:: ── 检查 Python ────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [✓] Python 版本：
python --version

:: ── 检查 PyInstaller ───────────────────────────────
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 正在安装 PyInstaller...
    pip install pyinstaller
)
echo [✓] PyInstaller 已安装

:: ── 安装依赖 ───────────────────────────────────────
echo [*] 安装项目依赖...
pip install -r requirements-win.txt
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [✓] 依赖安装完成

:: ── 构建前端（如未构建）────────────────────────────
if not exist "frontend\dist\index.html" (
    echo [*] 构建前端...
    cd frontend
    call npm install
    call npm run build
    cd ..
    echo [✓] 前端构建完成
) else (
    echo [✓] 前端已构建
)

:: ── 打包 ──────────────────────────────────────────
echo [*] 正在打包为 Windows 可执行程序...
echo     这可能需 2-5 分钟，请耐心等待...
echo.

pyinstaller --clean docreview.spec
if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

:: ── 完成 ──────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════
echo  构建成功！
echo  可执行文件位置：dist\DocReview.exe
echo.
echo  使用方式：
echo    双击 dist\DocReview.exe 即可运行
echo    服务启动后自动打开浏览器访问
   echo    http://127.0.0.1:3000（前端），后端 API：http://127.0.0.1:8000
echo.
echo  默认管理员账号：admin / admin123
echo ═══════════════════════════════════════════════
pause
