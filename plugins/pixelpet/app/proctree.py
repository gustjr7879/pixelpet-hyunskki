"""Windows 프로세스 트리 조회 (ctypes, 외부 패키지 없음)."""
import ctypes
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]


def snapshot():
    """{pid: (ppid, exe_name_lower)}"""
    procs = {}
    h = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not h or h == INVALID_HANDLE_VALUE:
        return procs
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = _k32.Process32FirstW(h, ctypes.byref(e))
        while ok:
            procs[e.th32ProcessID] = (e.th32ParentProcessID, e.szExeFile.lower())
            ok = _k32.Process32NextW(h, ctypes.byref(e))
    finally:
        _k32.CloseHandle(h)
    return procs


def ancestors(pid, procs=None):
    """pid 자신부터 위로 올라가며 [(pid, name), ...]. PID 재사용 루프 방지."""
    procs = procs if procs is not None else snapshot()
    chain, seen = [], set()
    while pid in procs and pid not in seen and pid != 0:
        seen.add(pid)
        ppid, name = procs[pid]
        chain.append((pid, name))
        pid = ppid
    return chain


def children_map(procs):
    kids = {}
    for pid, (ppid, _name) in procs.items():
        kids.setdefault(ppid, []).append(pid)
    return kids


def root_codex_under(claude_pid, procs, kids=None):
    """claude 프로세스 아래에서 실행 중인 '최상위' codex.exe pid 목록."""
    kids = kids if kids is not None else children_map(procs)
    found, stack = [], list(kids.get(claude_pid, []))
    seen = set()
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        seen.add(p)
        if procs.get(p, (0, ""))[1] == "codex.exe":
            found.append(p)  # 그 아래 codex.exe는 같은 작업의 일부이므로 내려가지 않음
            continue
        stack.extend(kids.get(p, []))
    return found
