"""DocReview V1.0 — Windows 桌面启动入口
双击运行，自动启动后端服务（8000）+ 前端服务（3000），并通过系统托盘管理
"""
import os
import sys
import threading
import time
from pathlib import Path

# ── PyInstaller 运行时路径处理 ─────────────────────────
# 打包后：可执行文件所在目录作为持久化数据根目录（数据库、上传文件等）
# PyInstaller 临时解压目录作为代码包根目录
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(sys._MEIPASS)
else:
    ROOT_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = ROOT_DIR

# 确保当前目录在项目根目录
os.chdir(ROOT_DIR)

# 无窗口运行时，将 stdout/stderr 重定向到日志文件，便于排查
LOG_PATH = ROOT_DIR / "docreview.log"
if getattr(sys, "frozen", False) and (sys.stdout is None or sys.stderr is None):
    try:
        _log_file = open(LOG_PATH, "a", encoding="utf-8", errors="replace")
        sys.stdout = _log_file
        sys.stderr = _log_file
    except Exception:
        pass

# 将 backend 目录和项目根目录加入 Python 路径
# 优先从 BUNDLE_DIR 加载嵌入代码，ROOT_DIR 用于外部扩展
sys.path.insert(0, str(BUNDLE_DIR / "backend"))
sys.path.insert(0, str(BUNDLE_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR))

# 顶层导入 uvicorn，确保 PyInstaller 静态分析能发现该依赖
# （运行时实际在 run_backend() 中使用，这里仅用于打包分析）
import uvicorn  # noqa: F401

# ── 路径设置 ──────────────────────────────────────────
DOC_REPO_DIR = ROOT_DIR / "doc-repo"
DB_PATH = ROOT_DIR / "backend" / "docreview.db"

os.environ["DOC_REPO_PATH"] = str(DOC_REPO_DIR)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
os.environ["DATABASE_SYNC_URL"] = f"sqlite:///{DB_PATH}"
os.environ["CORS_ORIGINS"] = "*"
os.environ["JWT_SECRET_KEY"] = "docreview-win-secret-key-v1.0"

DOC_REPO_DIR.mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "backend").mkdir(parents=True, exist_ok=True)

# 同步数据库中的存储路径配置，避免在另一台电脑上仍使用开发环境路径
if DB_PATH.is_file():
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='system_configs'")
        if cur.fetchone():
            cur.execute(
                "UPDATE system_configs SET value = ? WHERE key = 'doc_repo_path'",
                (str(DOC_REPO_DIR),),
            )
            conn.commit()
        conn.close()
    except Exception:
        pass

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:9002")
# 从后端 URL 解析端口，确保前后端端口一致
_BACKEND_PORT = int(BACKEND_URL.split(":")[-1].split("/")[0])
# 必须在导入 serve_frontend_3000 之前设置，否则静态目录会指向 PyInstaller 临时目录
os.environ.setdefault("FRONTEND_DIST", str(ROOT_DIR / "frontend" / "dist"))

# 前端静态服务器模块（放在顶层确保 PyInstaller 能正确打包）
from serve_frontend_3000 import SpaProxyHandler, PORT

# 系统托盘控制（放在顶层确保 PyInstaller 能正确打包）
from tray_app import TrayApp

# 全局前端服务器实例，用于优雅关闭
_FRONTEND_SERVER = None


def run_backend():
    """在后台线程中启动 FastAPI 服务。"""
    import uvicorn
    from backend.main import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=_BACKEND_PORT,
        reload=False,
        log_level="warning",
    )


def run_frontend():
    """在后台线程中启动前端静态服务器。"""
    from http.server import ThreadingHTTPServer

    global _FRONTEND_SERVER
    server = ThreadingHTTPServer(("0.0.0.0", PORT), SpaProxyHandler)
    server.daemon_threads = True
    server.allow_reuse_address = True
    _FRONTEND_SERVER = server
    try:
        server.serve_forever()
    except Exception:
        pass


def open_browser():
    """等待服务启动后打开浏览器。"""
    time.sleep(4)
    import webbrowser
    webbrowser.open(FRONTEND_URL)


def stop_service():
    """停止前端服务（后端线程会随进程退出而终止）。"""
    global _FRONTEND_SERVER
    if _FRONTEND_SERVER is not None:
        try:
            _FRONTEND_SERVER.shutdown()
        except Exception:
            pass


def _check_backend_health():
    """简单检查后端是否可达。"""
    try:
        from urllib.request import urlopen
        with urlopen(f"{BACKEND_URL}/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _status_updater(tray_app):
    """定时更新托盘提示状态。"""
    while True:
        time.sleep(5)
        backend_ok = _check_backend_health()
        tip = f"DocReview — 后端{'正常' if backend_ok else '未就绪'} | 前端端口 {PORT}"
        try:
            tray_app.update_tooltip(tip)
        except Exception:
            break


if __name__ == "__main__":
    # 检测 --autostart 参数：开机自启动时延迟 60 秒，等待系统完全就绪
    if "--autostart" in sys.argv:
        print("检测到开机自启动模式，延迟 60 秒后启动服务...")
        time.sleep(60)

    print("═" * 50)
    print("  DocReview V1.0 — 沃迪森数字档案管理系统")
    print("  正在启动，请稍候...")
    print("═" * 50)
    print(f"  数据库：{DB_PATH}")
    print(f"  存储目录：{DOC_REPO_DIR}")
    print(f"  前端地址：{FRONTEND_URL}")
    print(f"  后端 API：{BACKEND_URL}")
    print(f"  API文档：{BACKEND_URL}/docs")
    print("═" * 50)

    # 启动后端服务（后台线程）
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # 等待后端初始化
    time.sleep(2)

    # 启动前端服务（后台线程）
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()

    print(f"前端服务已启动：{FRONTEND_URL}")
    print(f"API 请求将代理到：{BACKEND_URL}")

    # 启动系统托盘（主线程，阻塞）
    tray = TrayApp(
        frontend_url=FRONTEND_URL,
        backend_url=BACKEND_URL,
        log_path=str(LOG_PATH),
        on_stop=stop_service,
    )
    threading.Thread(target=_status_updater, args=(tray,), daemon=True).start()
    tray.run()
