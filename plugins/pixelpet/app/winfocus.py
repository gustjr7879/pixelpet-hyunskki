"""세션 이름 조회 + 해당 터미널 창/탭으로 이동."""
import ctypes
import json
import os
import re
import subprocess
import threading
from ctypes import wintypes

import proctree

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.GetConsoleWindow.restype = wintypes.HWND
_u32 = ctypes.windll.user32
_u32.GetWindow.restype = wintypes.HWND
_u32.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CODEX_INDEX = os.path.join(os.path.expanduser("~"), ".codex", "session_index.jsonl")
DEFAULT_TITLES = {"claude code", "claude", "windows powershell", "powershell", "command prompt", ""}


def clean_title(t):
    """'✳ 작업 이름' / '◑ 작업 이름' 처럼 앞에 붙는 상태 기호 제거."""
    t = re.sub(r"^[^\w(\[]+", "", t or "").strip()
    return "" if t.lower() in DEFAULT_TITLES else t


def console_info(pid):
    """claude 프로세스의 콘솔에 잠깐 붙어서 (터미널 제목, 터미널 창 hwnd) 를 얻는다."""
    title, hwnd = "", None
    _k32.FreeConsole()
    if not _k32.AttachConsole(pid):
        return title, hwnd
    try:
        buf = ctypes.create_unicode_buffer(1024)
        _k32.GetConsoleTitleW(buf, 1024)
        title = buf.value
        con = _k32.GetConsoleWindow()
        if con:
            owner = _u32.GetWindow(con, 4)  # GW_OWNER → Windows Terminal 창
            hwnd = owner or (con if _u32.IsWindowVisible(con) else None)  # 옛날 conhost 창
    finally:
        _k32.FreeConsole()
    return title, hwnd


def visible_windows_by_pid():
    out = {}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _l):
        if _u32.IsWindowVisible(h) and _u32.GetWindowTextLengthW(h) > 0 and not _u32.GetWindow(h, 4):
            p = wintypes.DWORD()
            _u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            out.setdefault(p.value, h)
        return True

    _u32.EnumWindows(cb, 0)
    return out


def ancestor_window(pid):
    """콘솔 창이 없을 때(VS Code 터미널 등): 조상 프로세스 중 창을 가진 프로세스의 창."""
    wins = visible_windows_by_pid()
    for p, _name in proctree.ancestors(pid)[1:]:
        if p in wins:
            return wins[p]
    return None


def codex_thread_name(thread_id):
    try:
        with open(CODEX_INDEX, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 200_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        if thread_id in line:
            try:
                return json.loads(line).get("thread_name") or ""
            except ValueError:
                continue
    return ""


def window_text(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    _u32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def focus(hwnd, tab_title=""):
    """창을 앞으로 가져오고, 필요하면 Windows Terminal 탭을 전환한다."""
    if not hwnd or not _u32.IsWindow(hwnd):
        return False
    if _u32.IsIconic(hwnd):
        _u32.ShowWindow(hwnd, 9)  # SW_RESTORE
    _u32.SetForegroundWindow(hwnd)
    if _u32.GetForegroundWindow() != hwnd:  # 포커스 잠금 우회: Alt 키 한 번
        _u32.keybd_event(0x12, 0, 0, 0)
        _u32.keybd_event(0x12, 0, 2, 0)
        _u32.SetForegroundWindow(hwnd)
    want = clean_title(tab_title)
    if want and clean_title(window_text(hwnd)) != want:
        threading.Thread(target=_select_tab, args=(hwnd, want), daemon=True).start()
    return True


def _select_tab(hwnd, want):
    env = dict(os.environ, PP_HWND=str(int(hwnd)), PP_TAB=want)
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", os.path.join(APP_DIR, "select_tab.ps1")],
                       env=env, timeout=10, creationflags=0x08000000)
    except Exception:
        pass
