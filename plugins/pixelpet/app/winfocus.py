"""세션 이름 조회 + 해당 터미널 창/탭으로 이동."""
import ctypes
import json
import os
import random
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


_con_lock = threading.Lock()  # 한 프로세스는 한 번에 콘솔 하나에만 붙을 수 있다


def console_info(pid):
    """claude 프로세스의 콘솔에 잠깐 붙어서 (터미널 제목, 터미널 창 hwnd) 를 얻는다."""
    with _con_lock:
        return _console_info(pid)


def swap_console_title(pid, new, only_if=None):
    """콘솔 제목을 new 로 바꾸고 이전 제목을 돌려준다 (only_if 가 있으면 현재 제목이 같을 때만)."""
    with _con_lock:
        _k32.FreeConsole()
        if not _k32.AttachConsole(pid):
            return None
        try:
            buf = ctypes.create_unicode_buffer(1024)
            _k32.GetConsoleTitleW(buf, 1024)
            if only_if is None or buf.value == only_if:
                _k32.SetConsoleTitleW(new)
            return buf.value
        finally:
            _k32.FreeConsole()


def _console_info(pid):
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


def focus(hwnd, tab_title="", pid=None):
    """창을 앞으로 가져오고, Windows Terminal 탭을 전환한다.

    pid(claude 프로세스)가 있으면 그 콘솔 제목을 잠깐 고유 표식으로 바꿔서 탭을 정확히 찾는다
    → 제목이 'Claude Code' 그대로이거나 같은 이름의 탭이 여럿이어도 동작.
    """
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
    if pid or want:
        threading.Thread(target=_select_tab, args=(hwnd, want, pid), daemon=True).start()
    return True


def _select_tab(hwnd, want, pid):
    marker, orig = "", None
    if pid:
        marker = f"PixelPet-{os.getpid()}-{random.randrange(1 << 30)}"
        orig = swap_console_title(pid, marker)
        if orig is None:
            marker = ""
        elif clean_title(orig):
            want = clean_title(orig)
    wants = "\n".join(t for t in (marker, want) if t)
    if not wants:
        return
    env = dict(os.environ, PP_HWND=str(int(hwnd)), PP_TABS=wants)
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", os.path.join(APP_DIR, "select_tab.ps1")],
                       env=env, timeout=10, creationflags=0x08000000)
    except Exception:
        pass
    finally:
        if marker:   # 원래 제목 복원 (그사이 Claude 가 제목을 바꿨으면 그대로 둔다)
            swap_console_title(pid, orig, only_if=marker)
