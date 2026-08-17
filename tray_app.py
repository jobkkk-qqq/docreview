"""
DocReview V1.0 — Windows 系统托盘控制模块（纯 ctypes，无额外依赖）

提供：
- 系统托盘图标与气泡提示
- 右键菜单：打开浏览器、查看日志、停止服务并退出
- 服务状态 tooltip
"""
import os
import sys
import threading
import time
import winreg
from ctypes import (
    WINFUNCTYPE,
    Structure,
    byref,
    c_void_p,
    c_wchar,
    c_wchar_p,
    cast,
    sizeof,
    windll,
)
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    HBRUSH,
    HICON,
    HINSTANCE,
    HMENU,
    HWND,
    INT,
    LPARAM,
    LPCWSTR,
    LPVOID,
    POINT,
    UINT,
    WPARAM,
)

HCURSOR = HANDLE
HBITMAP = HANDLE

# ── Windows API 常量 ────────────────────────────────────
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_USER = 0x0400
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_TRAYMESSAGE = WM_USER + 1

NIF_MESSAGE = 0x01
NIF_ICON = 0x02
NIF_TIP = 0x04
NIF_INFO = 0x10
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2

MIIM_FTYPE = 0x00000100
MIIM_ID = 0x00000002
MIIM_STRING = 0x00000040
MIIM_STATE = 0x00000008
MFT_STRING = 0x00000000
MFS_ENABLED = 0x00000000
MFS_DEFAULT = 0x00001000
MFS_DISABLED = 0x00000003
MFS_CHECKED = 0x00000008

TPM_LEFTALIGN = 0x0000
TPM_RIGHTBUTTON = 0x0002

IDM_OPEN = 1000
IDM_LOGS = 1001
IDM_AUTOSTART = 1002
IDM_STOP = 1003

IDI_APPLICATION = 32512

CS_HREDRAW = 0x0002
CS_VREDRAW = 0x0001
CW_USEDEFAULT = 0x80000000
HWND_MESSAGE = -3

# ── Windows API 函数 ────────────────────────────────────
user32 = windll.user32
kernel32 = windll.kernel32
shell32 = windll.shell32

user32.RegisterClassExW.argtypes = [c_void_p]
user32.RegisterClassExW.restype = UINT
user32.CreateWindowExW.argtypes = [
    DWORD, LPCWSTR, LPCWSTR, DWORD, INT, INT, INT, INT,
    HWND, HMENU, HINSTANCE, LPVOID,
]
user32.CreateWindowExW.restype = HWND
user32.DefWindowProcW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LPARAM
user32.LoadIconW.argtypes = [HINSTANCE, LPCWSTR]
user32.LoadIconW.restype = HICON
user32.LoadCursorW.argtypes = [HINSTANCE, LPCWSTR]
user32.LoadCursorW.restype = HCURSOR
user32.TrackPopupMenu.argtypes = [HMENU, UINT, INT, INT, INT, HWND, c_void_p]
user32.TrackPopupMenu.restype = BOOL
user32.GetCursorPos.argtypes = [c_void_p]
user32.GetCursorPos.restype = BOOL
user32.PostQuitMessage.argtypes = [INT]
user32.DestroyWindow.argtypes = [HWND]
user32.DestroyMenu.argtypes = [HMENU]
user32.CreatePopupMenu.restype = HMENU
user32.AppendMenuW.argtypes = [HMENU, UINT, UINT, LPCWSTR]
user32.AppendMenuW.restype = BOOL
user32.SetForegroundWindow.argtypes = [HWND]
user32.SetForegroundWindow.restype = BOOL
user32.GetMessageW.argtypes = [c_void_p, HWND, UINT, UINT]
user32.GetMessageW.restype = INT
user32.TranslateMessage.argtypes = [c_void_p]
user32.TranslateMessage.restype = BOOL
user32.DispatchMessageW.argtypes = [c_void_p]
user32.DispatchMessageW.restype = LPARAM
user32.UpdateWindow.argtypes = [HWND]
user32.UpdateWindow.restype = BOOL
user32.ShowWindow.argtypes = [HWND, INT]
user32.ShowWindow.restype = BOOL
user32.PostMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.PostMessageW.restype = BOOL

shell32.Shell_NotifyIconW.argtypes = [DWORD, c_void_p]
shell32.Shell_NotifyIconW.restype = BOOL

kernel32.GetModuleHandleW.argtypes = [LPCWSTR]
kernel32.GetModuleHandleW.restype = HINSTANCE

# ── Windows 结构体 ──────────────────────────────────────
class WNDCLASSEXW(Structure):
    _fields_ = [
        ("cbSize", UINT),
        ("style", UINT),
        ("lpfnWndProc", c_void_p),
        ("cbClsExtra", INT),
        ("cbWndExtra", INT),
        ("hInstance", HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", LPCWSTR),
        ("lpszClassName", LPCWSTR),
        ("hIconSm", HICON),
    ]


class NOTIFYICONDATAW(Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("hWnd", HWND),
        ("uID", UINT),
        ("uFlags", UINT),
        ("uCallbackMessage", UINT),
        ("hIcon", HICON),
        ("szTip", c_wchar * 128),
        ("dwState", DWORD),
        ("dwStateMask", DWORD),
        ("szInfo", c_wchar * 256),
        ("uVersion", UINT),
        ("szInfoTitle", c_wchar * 64),
        ("dwInfoFlags", DWORD),
        ("guidItem", c_wchar * 39),
        ("hBalloonIcon", HICON),
    ]


class MSG(Structure):
    _fields_ = [
        ("hWnd", HWND),
        ("message", UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", DWORD),
        ("pt", POINT),
    ]


class POINT(Structure):
    _fields_ = [("x", INT), ("y", INT)]


# ── 托盘应用类 ──────────────────────────────────────────
class TrayApp:
    """Windows 系统托盘控制器"""

    # 开机自启动注册表路径
    _AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _AUTOSTART_REG_NAME = "DocReview"

    def __init__(self, frontend_url, backend_url, log_path, on_stop=None):
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.log_path = log_path
        self.on_stop = on_stop
        self.hwnd = None
        self.hmenu = None
        self.hicon = None
        self._tip = "沃迪森数字档案管理系统"
        self._running = True
        self._lock = threading.Lock()

    # ── 开机自启动管理 ────────────────────────────────────

    def _get_exe_path(self):
        """获取当前可执行文件路径"""
        if getattr(sys, "frozen", False):
            return sys.executable
        return os.path.abspath(sys.argv[0])

    def is_autostart_enabled(self):
        """检查开机自启动是否已启用"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._AUTOSTART_REG_PATH,
                0,
                winreg.KEY_READ,
            )
            try:
                value, _ = winreg.QueryValueEx(key, self._AUTOSTART_REG_NAME)
                winreg.CloseKey(key)
                return bool(value)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except OSError:
            return False

    def enable_autostart(self):
        """启用开机自启动（带 30 秒延迟启动参数）"""
        exe_path = self._get_exe_path()
        # 使用 --autostart 参数，main_win.py 检测到此参数会延迟 30 秒再启动
        reg_value = f'"{exe_path}" --autostart'
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._AUTOSTART_REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, self._AUTOSTART_REG_NAME, 0, winreg.REG_SZ, reg_value)
            winreg.CloseKey(key)
            return True
        except OSError:
            return False

    def disable_autostart(self):
        """禁用开机自启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self._AUTOSTART_REG_PATH,
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                winreg.DeleteValue(key, self._AUTOSTART_REG_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except OSError:
            return False

    def _toggle_autostart(self):
        """切换开机自启动状态"""
        if self.is_autostart_enabled():
            self.disable_autostart()
            self._show_balloon("已关闭开机自启动")
        else:
            if self.enable_autostart():
                self._show_balloon("已启用开机自启动（开机后延迟60秒启动）")
            else:
                self._show_balloon("设置开机自启动失败")
        # 刷新菜单勾选状态
        self._refresh_menu()

    def _show_balloon(self, message):
        """显示气泡提示"""
        if not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_INFO
        nid.szInfo = message
        nid.szInfoTitle = "DocReview"
        nid.dwInfoFlags = 0x01  # NIIF_INFO
        shell32.Shell_NotifyIconW(NIM_MODIFY, byref(nid))

    def _refresh_menu(self):
        """重建菜单以刷新勾选状态"""
        if self.hmenu:
            user32.DestroyMenu(self.hmenu)
        self.hmenu = self._create_menu()

    def _make_wndproc(self):
        """创建窗口过程回调"""
        WNDPROC = WINFUNCTYPE(LPARAM, HWND, UINT, WPARAM, LPARAM)

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYMESSAGE:
                if lparam == WM_RBUTTONUP:
                    self._show_menu()
                elif lparam == WM_LBUTTONUP:
                    self._open_browser()
                return 0
            elif msg == WM_COMMAND:
                cmd = wparam & 0xFFFF
                self._on_command(cmd)
                return 0
            elif msg == WM_DESTROY or msg == WM_CLOSE:
                self._remove_icon()
                user32.PostQuitMessage(0)
                self._running = False
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        return WNDPROC(wndproc)

    def _show_menu(self):
        """显示右键菜单"""
        if not self.hmenu:
            return
        pt = POINT()
        user32.GetCursorPos(byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        user32.TrackPopupMenu(
            self.hmenu,
            TPM_LEFTALIGN | TPM_RIGHTBUTTON,
            pt.x,
            pt.y,
            0,
            self.hwnd,
            None,
        )
        user32.PostMessageW(self.hwnd, 0, 0, 0)

    def _on_command(self, cmd):
        """处理菜单命令"""
        if cmd == IDM_OPEN:
            self._open_browser()
        elif cmd == IDM_LOGS:
            self._open_logs()
        elif cmd == IDM_AUTOSTART:
            self._toggle_autostart()
        elif cmd == IDM_STOP:
            self._stop_service()

    def _open_browser(self):
        import webbrowser
        webbrowser.open(self.frontend_url)

    def _open_logs(self):
        if self.log_path and os.path.isfile(self.log_path):
            os.startfile(self.log_path)

    def _stop_service(self):
        if self.on_stop:
            try:
                self.on_stop()
            except Exception:
                pass
        self._remove_icon()
        user32.PostQuitMessage(0)
        self._running = False
        # 结束整个进程
        os._exit(0)

    def _create_menu(self):
        """创建右键菜单"""
        menu = user32.CreatePopupMenu()
        user32.AppendMenuW(menu, MFT_STRING, IDM_OPEN, "打开 DocReview")
        user32.AppendMenuW(menu, MFT_STRING, IDM_LOGS, "查看运行日志")
        # 开机自启动菜单项（带勾选状态）
        autostart_state = MFS_CHECKED if self.is_autostart_enabled() else MFS_ENABLED
        user32.AppendMenuW(menu, MFT_STRING | autostart_state, IDM_AUTOSTART, "开机自启动")
        user32.AppendMenuW(menu, MFT_STRING, IDM_STOP, "停止服务并退出")
        return menu

    def _add_icon(self):
        """添加托盘图标"""
        nid = NOTIFYICONDATAW()
        nid.cbSize = sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid.uCallbackMessage = WM_TRAYMESSAGE
        nid.hIcon = self.hicon
        nid.szTip = self._tip
        shell32.Shell_NotifyIconW(NIM_ADD, byref(nid))

    def _remove_icon(self):
        """移除托盘图标"""
        if not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        shell32.Shell_NotifyIconW(NIM_DELETE, byref(nid))

    def update_tooltip(self, text):
        """更新托盘提示文本"""
        with self._lock:
            self._tip = text[:127]
        if not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_TIP
        nid.szTip = self._tip
        shell32.Shell_NotifyIconW(NIM_MODIFY, byref(nid))

    def run(self):
        """运行托盘消息循环（阻塞当前线程）"""
        hinstance = kernel32.GetModuleHandleW(None)
        self.hicon = user32.LoadIconW(None, cast(IDI_APPLICATION, LPCWSTR))

        class_name = "DocReviewTrayWindowClass"
        wndproc = self._make_wndproc()

        wc = WNDCLASSEXW()
        wc.cbSize = sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = cast(wndproc, c_void_p)
        wc.hInstance = hinstance
        wc.lpszClassName = class_name
        wc.hIcon = self.hicon
        wc.hCursor = user32.LoadCursorW(None, cast(32512, LPCWSTR))  # IDC_ARROW
        wc.hbrBackground = 0

        user32.RegisterClassExW(byref(wc))

        self.hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "DocReviewTray",
            0,
            0, 0, 0, 0,
            cast(-3, HWND),  # HWND_MESSAGE
            None,
            hinstance,
            None,
        )

        self.hmenu = self._create_menu()
        self._add_icon()

        msg = MSG()
        while self._running:
            ret = user32.GetMessageW(byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))

        if self.hmenu:
            user32.DestroyMenu(self.hmenu)


# 兼容旧导入名
if __name__ == "__main__":
    app = TrayApp("http://127.0.0.1:3000", "http://127.0.0.1:9002", None)
    app.run()
