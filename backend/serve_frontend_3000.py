"""
前端静态文件服务器（端口 3000）

- 提供 frontend/dist 目录的静态文件
- /api/* 请求代理到后端 http://127.0.0.1:8000
- SPA fallback：非文件路径返回 index.html
- 静态资源缓存优化：带 hash 的资源长期缓存，index.html 不缓存

用法：
    python serve_frontend_3000.py
"""

import os
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import mimetypes

# 配置（支持环境变量覆盖，便于在不同端口场景下复用）
DIST_DIR = Path(os.getenv("FRONTEND_DIST", Path(__file__).parent.parent / "frontend" / "dist"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:9002")
PORT = int(os.getenv("FRONTEND_PORT", "3000"))

# 确保常见静态资源 MIME 类型正确（Windows 上可能注册不全）
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/gif", ".gif")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("application/pdf", ".pdf")


class SpaProxyHandler(SimpleHTTPRequestHandler):
    """静态文件 + API 代理处理器（带缓存优化）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def log_message(self, format, *args):
        """打印请求日志（仅错误时输出，避免日志过多）"""
        # 注释掉下面这行可以减少日志输出
        # print(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}")
        pass

    def guess_type(self, path):
        """使用扩展后的 mimetypes 推断文件类型，为 JS/CSS 添加 charset"""
        ctype, _ = mimetypes.guess_type(path)
        if ctype is None:
            ctype = "application/octet-stream"
        # 为文本类型添加 charset
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype = ctype + "; charset=utf-8"
        return ctype

    def end_headers(self):
        """添加缓存相关响应头"""
        path = self.path.split("?")[0]
        # assets 目录下的文件都带 hash，可以长期缓存
        if path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        elif path.endswith(".svg") or path.endswith(".ico") or path.endswith(".png") or path.endswith(".jpg"):
            # 图片和图标缓存 7 天
            self.send_header("Cache-Control", "public, max-age=604800")
        elif path == "/" or path.endswith(".html"):
            # HTML 文件不缓存，确保更新及时
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def _is_static_file(self, path):
        """判断路径是否对应真实的静态文件"""
        # 移除查询字符串
        clean_path = path.split("?")[0].split("#")[0]
        # 移除开头的 /
        clean_path = clean_path.lstrip("/")
        if not clean_path:
            return False
        file_path = DIST_DIR / clean_path
        try:
            return file_path.is_file()
        except OSError:
            return False

    def _serve_index(self):
        """返回 index.html（SPA fallback）"""
        index_path = DIST_DIR / "index.html"
        try:
            with open(index_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "index.html not found")

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        elif self._is_static_file(self.path):
            super().do_GET()
        else:
            # SPA fallback：返回 index.html
            self._serve_index()

    def do_HEAD(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        elif self._is_static_file(self.path):
            super().do_HEAD()
        else:
            self._serve_index()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        else:
            self.send_error(405)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        else:
            self.send_error(405)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        else:
            self.send_error(405)

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        else:
            self.send_response(200)
            self.send_header("Allow", "GET, HEAD, OPTIONS")
            self.end_headers()

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
        else:
            self.send_error(405)

    def _proxy_to_backend(self):
        """将请求代理到后端服务"""
        # 解析查询字符串
        path_only = self.path
        target_url = f"{BACKEND_URL}{path_only}"
        content_length = self.headers.get("Content-Length")
        body = None
        if content_length:
            try:
                body = self.rfile.read(int(content_length))
            except Exception:
                body = None

        # 复制请求头，移除 hop-by-hop 头和 host 头
        skip_headers = {
            "host", "connection", "keep-alive", "transfer-encoding",
            "content-encoding", "content-length", "te", "trailer",
            "proxy-authorization", "proxy-authenticate",
        }
        headers = {}
        for key, val in self.headers.items():
            if key.lower() not in skip_headers:
                headers[key] = val

        try:
            req = Request(target_url, data=body, headers=headers, method=self.command)
            # 超时放宽到 300 秒，兼容大文件上传和后端 PDF 转换等耗时操作
            with urlopen(req, timeout=300) as resp:
                self.send_response(resp.status)
                # 复制响应头
                resp_skip = {"transfer-encoding", "connection", "keep-alive"}
                for key, val in resp.headers.items():
                    if key.lower() not in resp_skip:
                        self.send_header(key, val)
                self.end_headers()
                # 读取并转发响应体
                resp_body = resp.read()
                self.wfile.write(resp_body)
        except HTTPError as e:
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() not in {"transfer-encoding", "connection"}:
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(e.read())
        except URLError as e:
            err_msg = f'{{"detail":"后端服务不可达，请检查服务是否启动","error":"{e.reason}"}}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_msg.encode())))
            self.end_headers()
            self.wfile.write(err_msg.encode())
        except Exception as e:
            err_msg = f'{{"detail":"代理请求失败","error":"{str(e)}"}}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(err_msg.encode())


def main():
    if not DIST_DIR.is_dir():
        print(f"错误：前端构建目录不存在：{DIST_DIR}", file=sys.stderr)
        sys.exit(1)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), SpaProxyHandler)
    server.daemon_threads = True
    server.allow_reuse_address = True
    print(f"前端服务已启动：http://0.0.0.0:{PORT}")
    print(f"局域网访问：http://<服务器IP>:{PORT}")
    print(f"API 代理到：{BACKEND_URL}")
    print(f"静态文件目录：{DIST_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
