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


ZERO_WIDTH = "​‌‍⁠"


def invisible_mark():
    """화면에 보이지 않는 폭 0 문자로 만든 고유 표식."""
    n = random.getrandbits(24)
    return "⁠" + "".join(ZERO_WIDTH[(n >> (2 * i)) & 3] for i in range(12))


def _swap_title(pid, make_new):
    """콘솔 제목을 make_new(현재 제목) 으로 바꾸고 이전 제목을 돌려준다 (None 이면 안 바꿈)."""
    with _con_lock:
        _k32.FreeConsole()
        if not _k32.AttachConsole(pid):
            return None
        try:
            buf = ctypes.create_unicode_buffer(1024)
            _k32.GetConsoleTitleW(buf, 1024)
            new = make_new(buf.value)
            if new is not None:
                _k32.SetConsoleTitleW(new)
            return buf.value
        finally:
            _k32.FreeConsole()


def add_title_mark(pid, mark):
    """보이는 제목은 그대로 두고 끝에 보이지 않는 표식만 붙인다."""
    return _swap_title(pid, lambda cur: cur + mark)


def remove_title_mark(pid, mark):
    """표식이 아직 붙어 있으면 떼어낸다 (그사이 Claude 가 제목을 새로 썼으면 건드리지 않음)."""
    _swap_title(pid, lambda cur: cur.replace(mark, "") if mark in cur else None)


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

    pid(claude 프로세스)가 있으면 그 콘솔 제목 끝에 보이지 않는 표식을 잠깐 붙여 탭을 정확히 찾는다
    → 보이는 세션 이름은 그대로이고, 'Claude Code' 그대로이거나 같은 이름의 탭이 여럿이어도 동작.
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
    mark = ""
    if pid:
        mark = invisible_mark()
        orig = add_title_mark(pid, mark)
        if orig is None:
            mark = ""
        elif clean_title(orig):
            want = clean_title(orig)
    if not (mark or want):
        return
    env = dict(os.environ, PP_HWND=str(int(hwnd)), PP_MARK=mark, PP_TABS=want)
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", os.path.join(APP_DIR, "select_tab.ps1")],
                       env=env, timeout=10, creationflags=0x08000000)
    except Exception:
        pass
    finally:
        if mark:
            remove_title_mark(pid, mark)
