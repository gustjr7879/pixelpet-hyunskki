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


# ── 명령줄 / 시작 시각 (Claude 가 실행한 명령 표시용) ──
_ntdll = ctypes.WinDLL("ntdll")
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
_QUERY_LIMITED = 0x1000


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT), ("Buffer", ctypes.c_void_p)]


def process_info(pid):
    """(명령줄, 시작 시각 epoch) — 못 읽으면 ("", None)."""
    h = _k32.OpenProcess(_QUERY_LIMITED, False, pid)
    if not h:
        return "", None
    try:
        cmd, size = "", 65536
        for _ in range(2):
            buf = ctypes.create_string_buffer(size)
            need = wintypes.ULONG(0)
            st = _ntdll.NtQueryInformationProcess(h, 60, buf, size, ctypes.byref(need))  # ProcessCommandLineInformation
            if st == 0:
                us = _UNICODE_STRING.from_buffer(buf)
                cmd = ctypes.wstring_at(us.Buffer, us.Length // 2) if us.Buffer else ""
                break
            if not need.value or need.value <= size:
                break
            size = need.value
        times = [wintypes.FILETIME() for _ in range(4)]
        started = None
        if _k32.GetProcessTimes(h, *[ctypes.byref(t) for t in times]):
            ft = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            started = ft / 1e7 - 11644473600
        return cmd, started
    finally:
        _k32.CloseHandle(h)
