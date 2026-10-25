"""PixelPet — Claude Code / Codex 작업 완료를 알려주는 90년대풍 픽셀 펫.

pythonw pet.py 로 실행. 훅(pet_hook.py)이 127.0.0.1:47321 로 이벤트를 보낸다.
"""
import collections
import ctypes
import json
import os
import queue
import random
import re
import struct
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import wave
import winsound
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
import autostart  # noqa: E402
import proctree  # noqa: E402
import runtime  # noqa: E402
import usage  # noqa: E402
import winfocus  # noqa: E402

PORT = runtime.PORT
ASSETS = os.path.join(os.path.dirname(APP_DIR), "assets")
os.makedirs(runtime.DATA_DIR, exist_ok=True)
SETTINGS_PATH = os.path.join(runtime.DATA_DIR, "settings.json")
LOG_PATH = os.path.join(runtime.DATA_DIR, "pet.log")
VISIBLE_LIMIT = 5

if sys.stderr is None:  # pythonw
    sys.stderr = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr

# ── 팔레트 ─────────────────────────────────────────────────────────
KEY = "#ff00fe"          # 투명 처리용 색
FACE = "#c0c0c0"         # Win95 회색
NAVY, NAVY2 = "#000080", "#1084d0"
CREAM = "#fffbe6"
INK = "#2a1f33"
CLAUDE_C = "#d0603a"
CODEX_C = "#178a68"
SHELL_C = "#4a5aa8"
STATUS_STYLE = {
    "working":   ("hourglass", "#2f5fa8", "작업중..."),
    "waiting":   ("hourglass", "#b8860b", "codex 작업 기다리는 중"),
    "done":      ("check",     "#2e8b3e", "작업 완료!"),
    "attention": ("bang",      "#d0304a", "확인이 필요해요!"),
    "ended":     ("cross",     "#808080", "세션 종료됨"),
}

# ── 펫 외형(스킨) ───────────────────────────────────────────────────
# half: 왼쪽 절반(8칸) — 좌우 대칭으로 16x16 생성 / extra: 비대칭 장식 (x, y, 색키)
# eye_x: 왼쪽 눈의 왼쪽 열 (오른쪽 눈은 대칭), eye_rows: 눈 3줄
SKINS = {
    "cat": {
        "name": "고양이",
        "colors": {"K": "#3a2541", "W": "#fff6e3", "S": "#f0c79a", "P": "#ff7aa2", "O": "#f5a03a",
                   "D": "#3a2541", "H": "#ffffff"},
        "half": ["........", ".K......", ".KK.....", ".KPK....", ".KPPKKKK", "KWWWWWWW", "KWWWWWWW",
                 "KWWWWWWW", "KWWWWWWW", "KPPWWWWP", "KWWWWKWK", "KWWWWWKW", "KWWWWWWW", "KSWWWWWW",
                 ".KSSSWWW", "..KKKKKK"],
        "extra": [(9, 5, "O"), (10, 5, "O"), (11, 5, "O"), (12, 5, "O"), (10, 6, "O"), (11, 6, "O")],
        "eye_x": 3, "eye_rows": (6, 7, 8),
    },
    "dog": {
        "name": "강아지",
        "colors": {"K": "#3b2a20", "W": "#fffaf0", "S": "#ead7b8", "P": "#ff8fa3", "O": "#b8763e",
                   "D": "#2b1d14", "H": "#ffffff"},
        "half": ["........", "........", "........", "...KKKKK", ".KKWWWWW", "KOOKWWWW", "KOOKWWWW",
                 "KOOKWWWW", "KOOKWWWW", "KOOKPWWD", "..KWWWKW", "..KWWWWK", "..KWWWWW", "..KSWWWW",
                 "...KSSWW", "....KKKK"],
        "extra": [(10, 5, "O"), (11, 5, "O"), (12, 5, "O"), (12, 6, "O"), (12, 7, "O")],
        "eye_x": 4, "eye_rows": (6, 7, 8),
    },
    "chick": {
        "name": "병아리",
        "colors": {"K": "#5a3a1a", "W": "#ffe45c", "S": "#f2b934", "P": "#ff9aa8", "O": "#ff8c2b",
                   "D": "#3a2410", "H": "#ffffff"},
        "half": ["........", "........", "........", "....KKKK", "..KKWWWW", ".KWWWWWW", ".KWWWWWW",
                 "KWWWWWWW", "KWWWWWWW", "KWPWWWOO", "KWWWWWWO", "KWWWWWWW", "KSWWWWWW", ".KSWWWWW",
                 "..KSSSWW", "...KKKKK"],
        "extra": [(7, 2, "K"), (8, 1, "K"), (8, 2, "K"), (9, 0, "K"), (5, 15, "O"), (6, 15, "O"),
                  (9, 15, "O"), (10, 15, "O")],
        "eye_x": 3, "eye_rows": (6, 7, 8),
    },
    "ghost": {
        "name": "유령",
        "colors": {"K": "#3b3561", "W": "#f4f0ff", "S": "#c9c0ee", "P": "#ffaacc", "O": "#9d8cf0",
                   "D": "#2b2550", "H": "#ffffff"},
        "half": ["........", "........", ".....KKK", "...KKWWW", "..KWWWWW", ".KWWWWWW", ".KWWWWWW",
                 "KWWWWWWW", "KWWWWWWW", "KWPWWWWW", "KWWWWWWK", "KWWWWWWW", "KWWWWWWW", "KSWWWWWW",
                 "KWKKWWKW", "KK..KK.K"],
        "extra": [],
        "eye_x": 3, "eye_rows": (6, 7, 8),
        "float": True,
    },
    "slime": {
        "name": "슬라임",
        "colors": {"K": "#1d2b5a", "W": "#5aa8ff", "S": "#2f6fd6", "P": "#ff9ccf", "O": "#ffffff",
                   "D": "#14204a", "H": "#ffffff"},
        "half": ["........", "........", "........", "........", ".......K", "......KW", ".....KWW",
                 "....KWWW", "...KWWWW", "..KWWWWW", ".KWWWWWW", "KWWWWWWW", "KWWPWWKW", "KSWWWWWK",
                 ".KSSSSSS", "..KKKKKK"],
        "extra": [(9, 6, "O"), (10, 7, "O"), (10, 8, "O")],
        "eye_x": 4, "eye_rows": (9, 10, 11),
    },
    # ── 위비프렌즈 (draft) ──
    "wibee": {'name': '위비', 'colors': {'K': '#3f8fd0', 'W': '#66c0ef', 'S': '#4aa8de', 'P': '#ff9ab0', 'O': '#ffd600', 'A': '#3f8fd0', 'G': '#d4ebf8', 'L': '#ffcc00', 'D': '#111111', 'H': '#ffffff'}, 'full': ['...AA......AA...', '...AA......AA...', '.....A....A.....', '.....KKKKKK.....', '....KWWWWWWK....', '.GGKWWWWWWWWKGG.', 'GGGKWWWWWWWWKGGG', 'GGGKWWWWWWWWKGGG', '.GGKWWWDDWWWKGG.', '...KWWWDDWWWK...', '..KOOOOOOOOOOK..', '..KWWWWWWWWWWK..', '..KOOOOOOOOOOK..', '...KWWWWWWWWK...', '....KKKKKKKK....', '.....LL..LL.....'], 'eye_x': 5, 'eye_rows': (6, 7), 'eye_w': 1, 'eye_hl': False, 'extra': []},
    "dalbo": {'name': '달보', 'colors': {'K': '#a8641c', 'W': '#ffd800', 'S': '#f0c400', 'P': '#ff9ab0', 'O': '#b06a1e', 'A': '#a8641c', 'G': '#faf3cc', 'L': '#a8641c', 'D': '#111111', 'H': '#ffffff'}, 'full': ['...AA......AA...', '...AA......AA...', '.....A....A.....', '.....KKKKKK.....', '....KWWWWWWK....', '.GGKWKKWWKKWKGG.', 'GGGKWWWWWWWWKGGG', 'GGGKWWWWWWWWKGGG', '.GGKWWKDDKWWKGG.', '...KWWWKKWWWK...', '..KOOOOOOOOOOK..', '..KWWWWWWWWWWK..', '..KOOOOOOOOOOK..', '...KWWWWWWWWK...', '....KKKKKKKK....', '.....LL..LL.....'], 'eye_x': 5, 'eye_rows': (6, 7), 'eye_w': 1, 'eye_hl': False, 'extra': []},
    "bombom": {'name': '봄봄', 'colors': {'K': '#ec5f97', 'W': '#ffa8cb', 'S': '#ff94bd', 'P': '#ff7aa8', 'O': '#ffffff', 'A': '#f0508a', 'G': '#fbe6ee', 'L': '#f0508a', 'D': '#111111', 'H': '#ffffff'}, 'full': ['...AA......AA...', '...AA......AA...', '.....A....A.....', '.....KKKKKK.....', '....KWWWWWWK....', '.GGKWWWWWWWWKGG.', 'GGGKWWWWWWWWKGGG', 'GGGKWWWWWWWWKGGG', '.GGKWWDWWDWWKGG.', '...KWWWDDWWWK...', '..KOOOOOOOOOOK..', '..KWWWWWWWWWWK..', '..KOOOOOOOOOOK..', '...KWWWWWWWWK...', '....KKKKKKKK....', '.....LL..LL.....'], 'eye_x': 5, 'eye_rows': (6, 7), 'eye_w': 1, 'eye_hl': False, 'extra': []},
    "dugi": {'name': '두기', 'colors': {'K': '#7a5a44', 'W': '#ab866b', 'S': '#987459', 'P': '#ff9ab0', 'M': '#f0c9a8', 'N': '#3a2418', 'R': '#e2572a', 'D': '#111111', 'H': '#ffffff'}, 'full': ['................', '.....KKKKKK.....', '....KWWWWWWK....', '...KWDDWWDDWK...', '...KWWWWWWWWK...', '...KWWWWWWWWK...', '...KWWWWWWWWK...', '...KWWMNNMWWK...', '...KWWMMMMWWK...', '...KWWWWWWWWK...', '..KRRRRRRRRRRK..', '..KWWWRRRRWWWK..', '..KWWWWWWWWWWK..', '..KWWWWWWWWWWK..', '...KKKKKKKKKK...', '....RR....RR....'], 'eye_x': 5, 'eye_rows': (5, 6), 'eye_w': 1, 'eye_hl': False, 'extra': []},
    "cu": {'name': '큐', 'colors': {'K': '#e8c8d6', 'W': '#fdf4f7', 'S': '#f5e3ea', 'P': '#ffb0c8', 'T': '#f0508a', 'D': '#111111', 'H': '#ffffff'}, 'full': ['................', '................', '......T.TT......', '......TTTT......', '.....KKKKKK.....', '....KWWWWWWK....', '....KWWWWWWK....', '...KWWWWWWWWK...', '...KWWWWWWWWK...', '...KWWWTTWWWK...', '..KWWWWWWWWWWK..', '..KSWWWWWWWWSK..', '...KSWWWWWWSK...', '....KSSSSSSK....', '.....KKKKKK.....', '......T..T......'], 'eye_x': 5, 'eye_rows': (7, 8), 'eye_w': 1, 'eye_hl': False, 'extra': []},
    "puding": {'name': '푸딩', 'colors': {'K': '#6a78b0', 'W': '#8598cc', 'S': '#7787c0', 'P': '#ff9ab0', 'M': '#f4f4f8', 'N': '#111111', 'T': '#bfe0f7', 'L': '#6a78b0', 'D': '#111111', 'H': '#ffffff'}, 'full': ['....KK....KK....', '...KWWKKKKWWK...', '...KWWWWWWWWK...', '..KWWWWWWWWWWK..', '..KWWWWWWWWWWK..', '..KWWWWWWWWWWK..', '..KWWWMNNMWWWK..', '..KWWWMMMMWWWK..', '..KWWWWWWWWWWK..', '..KWWWWWWWWWWK..', '..KWWTWWWWTWWK..', '..KWWWTTTTWWWK..', '..KWWWWWWWWWWK..', '..KWWWWWWWWWWK..', '...KKKKKKKKKK...', '....LL....LL....'], 'eye_x': 5, 'eye_rows': (4, 5), 'eye_w': 1, 'eye_hl': False, 'extra': []},
}
PET_COLORS = SKINS["cat"]["colors"]  # 알림함 타이틀 아이콘용

AGENT_COLOR = {"claude": "#e07a4f", "codex": "#19b37f", "shell": "#7d8ff0"}
AGENT_DIM = {"claude": "#a8502e", "codex": "#0f7a56", "shell": "#4a5aa8"}
CARD_STYLE = {"claude": (CLAUDE_C, " CLAUDE "), "codex": (CODEX_C, " CODEX "), "shell": (SHELL_C, " SHELL ")}

# 일반 셸 명령 (pixelpet_shell.ps1): 이만큼 넘게 걸린 것만 펫에 보이고 알린다
SHELL_MIN_SEC = 10
SHELL_PROCS = ("powershell.exe", "pwsh.exe")
# 대화형/상주 프로그램은 제외 — 항상, 또는 인자 없이 실행했을 때만
SHELL_SKIP = {"claude", "codex", "ssh", "vim", "vi", "nvim", "nano", "less", "more", "man", "top", "htop", "btop",
              "enter-pssession", "exit"}
SHELL_SKIP_BARE = {"python", "python3", "py", "ipython", "node", "pwsh", "powershell", "cmd", "bash", "sh", "zsh",
                   "wsl", "psql", "mysql", "sqlite3", "irb", "ghci", "lua"}
CTRL_C_CODES = {-1073741510, 3221225786, 130}   # STATUS_CONTROL_C_EXIT / SIGINT
SHELL_EXES = {"bash.exe", "sh.exe", "cmd.exe", "powershell.exe", "pwsh.exe", "conhost.exe"}
BASH_EVAL = re.compile(r"eval '(.*)'\s*(?:<\s*/dev/null)?\s*&&\s*pwd -P", re.S)


def tool_command_label(cmd):
    """Claude Bash 도구 명령줄에서 실제 명령만 (eval '...' 부분)."""
    m = BASH_EVAL.search(cmd or "")
    return m.group(1).replace("'\\''", "'").replace('\\"', '"').strip() if m else ""


def short_cmdline(cmd):
    """'"C:\\...\\python.exe" -m x' → 'python -m x'"""
    cmd = (cmd or "").strip()
    if cmd.startswith('"'):
        exe, _, rest = cmd[1:].partition('"')
    else:
        exe, _, rest = cmd.partition(" ")
    exe = os.path.basename(exe)
    exe = exe[:-4] if exe.lower().endswith(".exe") else exe
    return (exe + " " + rest.strip()).strip()


def build_skin(skin):
    if "full" in skin:  # 좌우 비대칭 캐릭터는 16칸 전체를 그대로
        return [list(r) for r in skin["full"]]
    rows = [list(h + h[::-1]) for h in skin["half"]]
    for x, y, c in skin["extra"]:
        rows[y][x] = c
    return rows


SKIN_GRIDS = {k: build_skin(v) for k, v in SKINS.items()}


def pet_frame(skin_id, eyes="open"):
    skin = SKINS[skin_id]
    g = [r[:] for r in SKIN_GRIDS[skin_id]]
    lx, rows = skin["eye_x"], skin["eye_rows"]
    top, bottom = rows[0], rows[-1]

    def put(x, y, c):  # 왼쪽 + 대칭 위치에 같이 찍기
        g[y][x] = c
        g[y][15 - x] = c

    ew = skin.get("eye_w", 2)  # 1 이면 콕 찍은 점눈
    for c in range(lx, lx + ew):
        for r in rows:
            put(c, r, "W")
    if eyes == "closed":
        for c in ((lx, lx + 1) if ew == 2 else (lx - 1, lx)):
            put(c, bottom, "D")
    elif eyes == "happy" and len(rows) == 2:  # 작은 점눈용 ^ ^
        put(lx - 1, bottom, "D")
        put(lx, top, "D")
        put(lx + 1, bottom, "D")
    elif eyes == "happy":  # ^ ^
        put(lx, bottom, "D")
        put(lx + 1, rows[1], "D")
        put(lx + 2, bottom, "D")
    else:  # 반짝이는 큰 눈 (오른쪽 위 하이라이트), 좌/우 보기
        d = {"left": -1, "right": 1}.get(eyes, 0)
        for left in (lx, 16 - ew - lx):
            for c in range(left + d, left + ew + d):
                for r in rows:
                    g[r][c] = "D"
            if ew == 2 and skin.get("eye_hl", True):
                g[top][left + 1 + d] = "H"
    return g


GLYPHS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "+": ["000", "010", "111", "010", "000"], "!": ["1", "1", "1", "0", "1"],
    ".": ["0", "0", "0", "0", "1"], "z": ["0000", "1111", "0010", "0100", "1111"],
    "*": ["10101", "01110", "11111", "01110", "10101"],      # Claude 반짝이
    ">": ["100", "010", "001", "010", "100"], "_": ["000", "000", "000", "000", "111"],  # Codex 프롬프트
    "h": ["111", "101", "010", "101", "111"],                # 모래시계 (codex 기다리는 중)
    "$": ["011", "110", "010", "011", "110"],                # 셸 명령
}

ICONS = {
    "check":     ["......1", ".....11", "1...11.", "11.11..", ".111...", "..1....", "......."],
    "hourglass": ["1111111", ".1...1.", "..1.1..", "...1...", "..1.1..", ".1...1.", "1111111"],
    "bang":      ["..111..", "..111..", "..111..", "..111..", ".......", "..111..", "..111.."],
    "cross":     ["1.....1", ".1...1.", "..1.1..", "...1...", "..1.1..", ".1...1.", "1.....1"],
}


# ── Win32 도우미 ────────────────────────────────────────────────────
def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def work_area():
    r = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
    return r.left, r.top, r.right, r.bottom


def virtual_screen():
    gm = ctypes.windll.user32.GetSystemMetrics
    x, y = gm(76), gm(77)
    return x, y, x + gm(78), y + gm(79)


def load_private_font(path):
    try:
        return ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0) > 0
    except Exception:
        return False


def make_chip_wav(path, notes, volume=0.16, rate=22050):
    """사각파 칩튠 효과음 생성. notes = [(freq, ms), ...] (freq 0 은 쉼표)."""
    frames = bytearray()
    for freq, ms in notes:
        n = int(rate * ms / 1000)
        for i in range(n):
            if freq <= 0:
                v = 0.0
            else:
                phase = (i * freq / rate) % 1.0
                v = 1.0 if phase < 0.25 else -1.0
                v *= min(1.0, (n - i) / (rate * 0.012))  # 끝을 살짝 페이드
            frames += struct.pack("<h", int(v * volume * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def fmt_dur(sec):
    sec = int(sec)
    if sec < 60:
        return f"{sec}초"
    if sec < 3600:
        return f"{sec // 60}분 {sec % 60}초"
    return f"{sec // 3600}시간 {sec % 3600 // 60}분"


def snippet(text, n):
    t = re.sub(r"[`*#>_|]+", "", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


# ── 상태 모델 ──────────────────────────────────────────────────────
class Sub:
    def __init__(self, key, pid=None):
        self.key, self.pid = key, pid
        self.thread = None       # codex thread(session) id — 훅에서 알게 됨
        self.transcript = ""     # codex rollout 파일 — 멈춤(응답 없음) 감지용
        self.status = "working"
        self.message = ""
        self.updated = time.time()


class Session:
    def __init__(self, key, agent, sid):
        self.key, self.agent, self.sid = key, agent, sid
        self.cwd = ""
        self.pid = None
        self.title = ""          # 세션 이름 (Claude 터미널 제목 / Codex 스레드 이름)
        self.raw_title = ""      # 상태 기호 포함 원래 터미널 제목 (탭 찾기용)
        self.hwnd = None         # 이동할 터미널 창
        self.transcript = ""
        self.status = "working"
        self.message = ""
        self.subs = {}
        self.unread = False
        self.updated = time.time()
        self.stopped = False
        self.waited = False      # Stop 시점에 codex 가 아직 돌고 있었는지
        self.ready_at = None
        self.attn_label = ""     # '확인이 필요해요!' / '선택이 필요해요!' 등
        self.attn_at = 0.0
        self.started = time.time()
        self.cmds = {}           # Claude 가 실행해 10초 넘게 도는 명령: pid -> (명령, 시작 시각)

    @property
    def project(self):
        return os.path.basename(self.cwd.rstrip("\\/")) or "(unknown)"

    def working_subs(self):
        return [s for s in self.subs.values() if s.status == "working"]


# ── HTTP 수신 ──────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    q = None
    state_fn = None

    def do_POST(self):
        if self.headers.get(runtime.AUTH_HEADER) != "1":
            self.send_response(403)
            self.end_headers()
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            self.q.put(json.loads(self.rfile.read(n).decode("utf-8")))
            code = 200
        except Exception:
            code = 400
        self.send_response(code)
        self.end_headers()

    def do_GET(self):
        body = b"pixelpet"
        if runtime.DEBUG and self.path == "/state" and Handler.state_fn:
            try:
                body = json.dumps(Handler.state_fn(), ensure_ascii=False, indent=1).encode("utf-8")
            except Exception as ex:
                body = repr(ex).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class ExclusiveServer(ThreadingHTTPServer):
    """Windows 에서 같은 포트 중복 바인딩을 막아 단일 인스턴스를 보장."""
    allow_reuse_address = False

    def server_bind(self):
        import socket
        self.socket.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", socket.SO_REUSEADDR), 1)
        super().server_bind()


# ── 앱 ─────────────────────────────────────────────────────────────
class App:
    def __init__(self, server, q):
        self.server, self.q = server, q
        self.sessions = {}
        self.shell_runs = {}                          # 셸 pid -> 아직 짧은(카드 전) 명령
        self.shell_ended = collections.deque(maxlen=64)
        self.shell_drawn = 0.0
        self.tool_cache = {}                          # Claude 도구 셸 pid -> (명령, 시작 시각)
        self.settings = {"enabled": True, "sound": True, "x": None, "y": None, "collapsed": False,
                         "skin": "cat"}
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                self.settings.update(json.load(f))
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()
        self.U = self.root.winfo_fpixels("1i") / 96.0
        self.F = max(1, round(self.U))          # 글꼴/아이콘 정수 배율
        self.P = max(2, round(3 * self.U))      # 펫 도트 크기
        self._init_fonts()
        self._init_sounds()

        self.frame_no = 0
        self.last_alert = 0.0
        self.expanded = False
        self.view = "alerts"      # alerts | usage
        self.usage_drawn = 0.0
        self.open_cards = set()
        self.new_labels = []
        self.panel_visible = False
        self.dirty = True

        self._build_pet()
        self._build_panel()
        self._build_menu()

        Handler.state_fn = self.debug_state
        self.root.after(100, self.drain)
        self.root.after(1500, self.poll)
        self.root.after(160, self.animate)
        self.root.after(30000, self.keep_on_top)

    # ── 초기화 ──
    def _init_fonts(self):
        for name in ("Galmuri11.ttf", "Galmuri11-Bold.ttf", "Galmuri9.ttf"):
            p = os.path.join(ASSETS, name)
            if os.path.exists(p):
                load_private_font(p)
        fams = set(tkfont.families(self.root))
        main = "Galmuri11" if "Galmuri11" in fams else "Malgun Gothic"
        small = "Galmuri9" if "Galmuri9" in fams else main
        bold = "Galmuri11 Bold" if "Galmuri11 Bold" in fams else main
        F = self.F
        self.f_body = tkfont.Font(self.root, family=main, size=-12 * F)
        self.f_bold = tkfont.Font(self.root, family=bold, size=-12 * F, weight="bold")
        self.f_small = tkfont.Font(self.root, family=small, size=-10 * F)

    def _init_sounds(self):
        self.snd_done = os.path.join(runtime.DATA_DIR, "done.wav")
        self.snd_attn = os.path.join(runtime.DATA_DIR, "attention.wav")
        if not os.path.exists(self.snd_done):
            make_chip_wav(self.snd_done, [(1319, 70), (1568, 70), (2093, 70), (0, 30), (2637, 160)])
        if not os.path.exists(self.snd_attn):
            make_chip_wav(self.snd_attn, [(880, 90), (0, 60), (880, 90), (0, 60), (698, 160)])

    def save_settings(self):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── 펫 창 ──
    PET_W, PET_H = 26, 29   # 도트 단위

    def _build_pet(self):
        r = self.root
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.configure(bg=KEY)
        r.wm_attributes("-transparentcolor", KEY)
        w, h = self.PET_W * self.P, self.PET_H * self.P
        self.pet_w, self.pet_h = w, h
        self.cv = tk.Canvas(r, width=w, height=h, bg=KEY, highlightthickness=0, bd=0, cursor="hand2")
        self.cv.pack()
        self.pet_items, self.pet_state, self.pet_used = [], [], 0
        x, y = self.settings.get("x"), self.settings.get("y")
        vx0, vy0, vx1, vy1 = virtual_screen()
        if x is None or y is None or not (vx0 <= x <= vx1 - w and vy0 <= y <= vy1 - h):
            _l, _t, wr, wb = work_area()
            x, y = wr - w - 24, wb - h - 4
        r.geometry(f"{w}x{h}+{x}+{y}")
        r.deiconify()
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.on_menu)
        self._drag = None

    def on_press(self, e):
        self._drag = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y(), False)

    def on_drag(self, e):
        if not self._drag:
            return
        sx, sy, wx, wy, moved = self._drag
        dx, dy = e.x_root - sx, e.y_root - sy
        if moved or abs(dx) + abs(dy) > 4:
            self._drag = (sx, sy, wx, wy, True)
            self.root.geometry(f"+{wx + dx}+{wy + dy}")
            if self.panel_visible:
                self.place_panel()

    def on_release(self, _e):
        if not self._drag:
            return
        moved = self._drag[4]
        self._drag = None
        if moved:
            self.settings["x"], self.settings["y"] = self.root.winfo_x(), self.root.winfo_y()
            self.save_settings()
        else:
            self.toggle_panel()

    # ── 펫 그리기 ──
    # 캔버스 항목을 매 프레임 지우고 새로 만들면 Tk 9.0 이 항목마다 ~80바이트를 돌려주지 않아
    # (하루 ~7GB) 한 번 만든 사각형을 재사용한다. 그리는 순서대로 쓰므로 겹침 순서도 같다.
    def px(self, x, y, color, w=1, h=1):
        P = self.P
        x0, y0, x1, y1 = x * P, y * P, (x + w) * P, (y + h) * P
        pool, i = self.pet_items, self.pet_used
        if i < len(pool):
            item = pool[i]
            if self.pet_state[i] != (x0, y0, x1, y1, color):
                self.cv.coords(item, x0, y0, x1, y1)
                self.cv.itemconfigure(item, fill=color, state="normal")
                self.pet_state[i] = (x0, y0, x1, y1, color)
        else:
            pool.append(self.cv.create_rectangle(x0, y0, x1, y1, fill=color, outline=""))
            self.pet_state.append((x0, y0, x1, y1, color))
        self.pet_used = i + 1

    def draw_glyphs(self, text, x, y, color):
        for ch in text:
            g = GLYPHS.get(ch)
            if not g:
                x += 2
                continue
            for gy, row in enumerate(g):
                for gx, c in enumerate(row):
                    if c == "1":
                        self.px(x + gx, y + gy, color)
            x += len(g[0]) + 1
        return x

    def glyph_width(self, text):
        return sum(len(GLYPHS[c][0]) + 1 for c in text if c in GLYPHS) - 1

    def bubble(self, text, color=INK):
        tw = max(0, self.glyph_width(text))
        bw, bh = max(tw + 6, 11), 9
        bx, by = self.PET_W - bw - 1, 0
        self.px(bx + 1, by, INK, bw - 2, 1)
        self.px(bx + 1, by + bh - 1, INK, bw - 2, 1)
        self.px(bx, by + 1, INK, 1, bh - 2)
        self.px(bx + bw - 1, by + 1, INK, 1, bh - 2)
        self.px(bx + 1, by + 1, "#ffffff", bw - 2, bh - 2)
        self.px(bx + 2, by + bh, INK, 2, 1)   # 꼬리
        self.px(bx + 2, by + bh + 1, INK, 1, 1)
        self.draw_glyphs(text, bx + (bw - tw) // 2, by + 2, color)

    def badge(self, n):
        text = str(n) if n < 10 else "9+"
        tw = self.glyph_width(text)
        x, y, w, h = 0, 7, tw + 4, 9
        self.px(x + 1, y, INK, w - 2, 1)
        self.px(x + 1, y + h - 1, INK, w - 2, 1)
        self.px(x, y + 1, INK, 1, h - 2)
        self.px(x + w - 1, y + 1, INK, 1, h - 2)
        self.px(x + 1, y + 1, "#e8364f", w - 2, h - 2)
        self.px(x + 1, y + 1, "#ff8a9b", w - 2, 1)
        self.draw_glyphs(text, x + 2, y + 2, "#ffffff")

    def working_agents(self):
        """지금 일하고 있는 에이전트 집합과 'Claude 가 codex 를 기다리는 중' 여부."""
        agents, waiting = set(), False
        for s in self.sessions.values():
            if s.status == "working" or (s.status == "attention" and s.agent != "shell"):
                agents.add(s.agent)
            if s.status == "waiting":
                waiting = True
            if any(x.status == "working" for x in s.subs.values()):
                agents.add("codex")
            if s.cmds:
                agents.add("shell")
        return agents, waiting

    def pet_mode(self):
        if not self.settings["enabled"]:
            return "sleep"
        if time.time() - self.last_alert < 3.2:
            return "alert"
        if any(s.unread for s in self.sessions.values()):
            return "happy"
        agents, waiting = self.working_agents()
        if agents or waiting:
            return "work"
        return "idle"

    def draw_laptop(self, ox, oy, agent, f):
        """펫 앞의 90년대 베이지 노트북 — 뒷면 로고 색으로 누가 일하는지 표시."""
        K, beige, shade = "#2a2a2a", "#e3dccb", "#b9b09a"
        x0, y0 = ox + 3, oy + 13
        self.px(x0, y0, K, 10, 1)
        self.px(x0, y0 + 4, K, 10, 1)
        self.px(x0, y0, K, 1, 5)
        self.px(x0 + 9, y0, K, 1, 5)
        self.px(x0 + 1, y0 + 1, beige, 8, 3)
        self.px(x0 + 1, y0 + 3, shade, 8, 1)
        if agent:                         # 로고가 밝게/어둡게 깜빡
            bright, dim = AGENT_COLOR[agent], AGENT_DIM[agent]
            self.px(x0 + 3, y0 + 1, bright if f % 6 < 3 else dim, 4, 2)
        else:                             # codex 기다리는 중: 회색 로고
            self.px(x0 + 3, y0 + 1, "#9a9a9a", 4, 2)
        self.px(x0 - 1, y0 + 5, "#6b6b6b", 12, 1)   # 본체
        # 타닥타닥 — 앞발이 번갈아 올라감
        paw = self.skin()["colors"]
        for i, x in enumerate((x0 + 1, x0 + 7)):
            yy = y0 - (1 if i == f % 2 else 0)
            self.px(x, yy, paw["K"], 2, 1)
            self.px(x, yy + 1, paw["W"], 2, 1)

    def skin_id(self):
        sid = self.settings.get("skin", "cat")
        return sid if sid in SKINS else "cat"

    def skin(self):
        return SKINS[self.skin_id()]

    def draw_pet(self):
        self.pet_used = 0
        self._draw_pet()
        for i in range(self.pet_used, len(self.pet_items)):   # 이번 프레임에 안 쓴 사각형은 숨김
            if self.pet_state[i] is not None:
                self.cv.itemconfigure(self.pet_items[i], state="hidden")
                self.pet_state[i] = None

    def _draw_pet(self):
        f = self.frame_no
        mode = self.pet_mode()
        skin = self.skin()
        agents, waiting = self.working_agents()
        busy = sorted(agents)
        dy, eyes = 0, "open"
        if mode == "alert":
            dy = [0, -2, -4, -5, -4, -2, 0, 0][f % 8]
            eyes = "happy"
        elif mode == "happy":
            dy = 1 if (f // 4) % 2 else 0
            eyes = "happy" if (f // 12) % 2 else "open"
        elif mode == "work":
            dy = 1 if (f // 2) % 2 else 0
            eyes = "left" if (f // 8) % 2 else "right"
        elif mode == "sleep":
            dy = 1 if (f // 8) % 2 else 0
            eyes = "closed"
        else:
            dy = 1 if (f // 5) % 2 else 0
            if f % 30 in (0, 1) or (f % 30 == 15 and random.random() < 0.3):
                eyes = "closed"
        if skin.get("float") and mode != "alert":  # 유령은 둥실둥실
            dy = [0, -1, -2, -1][(f // 3) % 4]

        # 그림자 (점프 높이에 따라 줄어듦)
        sw = 12 + dy if dy < 0 else 12
        self.px(5 + (16 - sw) // 2, 28, "#4b3b57", sw, 1)
        ox, oy = 5, 9 + dy
        colors = skin["colors"]
        for y, row in enumerate(pet_frame(self.skin_id(), eyes)):
            for x, c in enumerate(row):
                if c != ".":
                    self.px(ox + x, oy + y, colors[c])

        # 일하는 중이면 노트북 (Claude·Codex 둘 다 일하면 로고 색이 번갈아)
        agent = busy[(f // 8) % len(busy)] if busy else None
        if mode != "sleep" and (busy or waiting):
            self.draw_laptop(ox, 9, agent, f)

        if mode in ("alert", "happy"):
            if mode == "happy" or f % 2 == 0:
                self.bubble("!", "#e8364f")
        elif mode == "work":
            if agent == "claude":
                self.bubble("*" if f % 4 < 3 else "+", AGENT_COLOR["claude"])
            elif agent == "codex":
                self.bubble(">_" if f % 4 < 3 else ">", AGENT_COLOR["codex"])
            elif agent == "shell":
                self.bubble("$_" if f % 4 < 3 else "$", AGENT_COLOR["shell"])
            else:
                self.bubble("h", "#c99a12")
        elif mode == "sleep":
            self.bubble("z" * (1 + (f // 6) % 2), "#5b6ee1")

        unread = sum(1 for s in self.sessions.values() if s.unread)
        if unread:
            self.badge(unread)

    # ── 알림 패널 ──
    def _build_panel(self):
        F = self.F
        p = self.panel = tk.Toplevel(self.root)
        p.withdraw()
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.configure(bg=INK)
        self.panel_width = 320 * F
        outer = tk.Frame(p, bg=FACE, bd=2 * F, relief="raised")
        outer.pack(fill="both", expand=True, padx=F, pady=F)

        # 타이틀 바 (계단식 그라데이션)
        tb_h = 18 * F
        tb = tk.Frame(outer, bg=NAVY2, height=tb_h)
        tb.pack(fill="x", padx=F, pady=F)
        self.title_cv = tk.Canvas(tb, width=1, height=tb_h, bg=NAVY, highlightthickness=0, bd=0)
        self.title_cv.pack(side="left", fill="x", expand=True)
        self.title_cv.bind("<Configure>", lambda e: self.draw_title())
        self.title_cv.bind("<Double-Button-1>", lambda e: self.toggle_collapse())
        btn = dict(font=self.f_small, bg=FACE, activebackground=FACE, bd=F, relief="raised",
                   padx=2 * F, pady=0, highlightthickness=0, takefocus=0)
        tk.Button(tb, text="x", command=self.hide_panel, **btn).pack(side="right", padx=(F, 2 * F))
        self.btn_collapse = tk.Button(tb, text="_", command=self.toggle_collapse, **btn)
        self.btn_collapse.pack(side="right", padx=F)

        # 본문 영역 (축소 시 숨김)
        self.content = tk.Frame(outer, bg=FACE)
        self.content.pack(fill="both", expand=True)
        bar = tk.Frame(self.content, bg=FACE)
        bar.pack(fill="x", padx=3 * F, pady=(2 * F, 3 * F))
        tbtn = dict(font=self.f_small, bg=FACE, activebackground="#d4d0c8", bd=2 * F,
                    relief="raised", padx=4 * F, pady=F, highlightthickness=0, takefocus=0)
        self.btn_onoff = tk.Button(bar, command=self.toggle_enabled, **tbtn)
        self.btn_onoff.pack(side="left")
        tk.Button(bar, text="모두 정리", command=self.clear_all, **tbtn).pack(side="left", padx=3 * F)
        self.btn_expand = tk.Button(bar, command=self.toggle_expand, **tbtn)

        # 탭 (Win95 탭 컨트롤 느낌: 선택된 탭이 더 크고 밝게)
        strip = tk.Frame(self.content, bg=FACE)
        strip.pack(fill="x", padx=3 * F)
        self.tabs = {}
        for view, text in (("alerts", "알림"), ("usage", "사용량")):
            t = tk.Label(strip, text=text, font=self.f_small, bg=FACE, fg=INK, bd=2 * F, relief="raised",
                         padx=6 * F, cursor="hand2")
            t.pack(side="left", anchor="s")
            t.bind("<Button-1>", lambda e, v=view: self.set_view(v))
            self.tabs[view] = t

        well = tk.Frame(self.content, bg=FACE, bd=2 * F, relief="sunken")
        well.pack(fill="both", expand=True, padx=3 * F)
        self.list_cv = tk.Canvas(well, bg="#808080", highlightthickness=0, bd=0,
                                 width=self.panel_width - 14 * F)
        self.list_cv.pack(side="left", fill="both", expand=True)
        self.scroll = tk.Scrollbar(well, orient="vertical", command=self.list_cv.yview, width=14 * F)
        self.list_cv.configure(yscrollcommand=self.scroll.set)
        self.inner = tk.Frame(self.list_cv, bg="#808080")
        self.inner_id = self.list_cv.create_window(0, 0, window=self.inner, anchor="nw")
        self.list_cv.bind("<Configure>", lambda e: self.list_cv.itemconfigure(self.inner_id, width=e.width))
        self.inner.bind("<Configure>", lambda e: self.list_cv.configure(scrollregion=self.list_cv.bbox("all")))
        for w in (self.list_cv, self.inner):
            w.bind("<Enter>", lambda e: self.panel.bind_all("<MouseWheel>", self.on_wheel))
            w.bind("<Leave>", lambda e: self.panel.unbind_all("<MouseWheel>"))

        self.status = tk.Label(self.content, font=self.f_small, bg=FACE, anchor="w", bd=F, relief="sunken")
        self.status.pack(fill="x", padx=3 * F, pady=3 * F)
        if self.settings.get("collapsed"):
            self.content.pack_forget()
            self.btn_collapse.configure(text="□")

    def draw_title(self):
        c = self.title_cv
        c.delete("all")
        w, h = max(1, c.winfo_width()), int(c["height"])
        steps = 10
        a, b = [int(NAVY[i:i + 2], 16) for i in (1, 3, 5)], [int(NAVY2[i:i + 2], 16) for i in (1, 3, 5)]
        for i in range(steps):
            col = "#%02x%02x%02x" % tuple(int(a[k] + (b[k] - a[k]) * i / (steps - 1)) for k in range(3))
            c.create_rectangle(w * i // steps, 0, w * (i + 1) // steps + 1, h, fill=col, outline="")
        # 작은 픽셀 고양이 얼굴 아이콘
        q = self.F * 2
        face = ["K.....K", "KK...KK", "KWWWWWK", "KWDWDWK", "KWWPWWK", ".KKKKK."]
        for y, row in enumerate(face):
            for x, ch in enumerate(row):
                if ch != ".":
                    c.create_rectangle(3 * self.F + x * q, 2 * self.F + y * q, 3 * self.F + (x + 1) * q,
                                       2 * self.F + (y + 1) * q, fill=PET_COLORS[ch], outline="")
        unread = sum(1 for s in self.sessions.values() if s.unread)
        title = "알림함" + (f" ({unread})" if unread else "")
        c.create_text(20 * self.F, h // 2, text=title, fill="#ffffff", font=self.f_bold, anchor="w")

    def on_wheel(self, e):
        if self.expanded:
            self.list_cv.yview_scroll(int(-e.delta / 120) * 2, "units")

    def icon(self, parent, name, color, bg):
        q = max(2, self.F * 2)
        g = ICONS[name]
        c = tk.Canvas(parent, width=7 * q, height=7 * q, bg=bg, highlightthickness=0, bd=0)
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                if ch == "1":
                    c.create_rectangle(x * q, y * q, (x + 1) * q, (y + 1) * q, fill=color, outline="")
        return c

    def sorted_sessions(self):
        return sorted(self.sessions.values(), key=lambda s: s.updated, reverse=True)

    def build_card(self, s):
        F = self.F
        wrap = self.panel_width - 40 * F
        color, tag = CARD_STYLE.get(s.agent, CARD_STYLE["codex"])
        card = tk.Frame(self.inner, bg=FACE, bd=2 * F, relief="raised")
        card.pack(fill="x", padx=2 * F, pady=(2 * F, 0))

        head = tk.Frame(card, bg=color)
        head.pack(fill="x")
        tk.Label(head, text=tag, font=self.f_small,
                 bg=INK, fg="#ffffff").pack(side="left", padx=(2 * F, 3 * F), pady=2 * F)
        tk.Label(head, text=snippet(s.title or s.project, 15), font=self.f_bold,
                 bg=color, fg="#ffffff").pack(side="left")
        close = tk.Label(head, text=" x ", font=self.f_small, bg=FACE, fg=INK, bd=F, relief="raised", cursor="hand2")
        close.pack(side="right", padx=2 * F)
        close.bind("<Button-1>", lambda e, k=s.key: (self.dismiss(k), "break")[1])
        tk.Label(head, text=time.strftime("%H:%M", time.localtime(s.updated)), font=self.f_small,
                 bg=color, fg="#ffffff").pack(side="right", padx=2 * F)
        if s.unread:
            nl = tk.Label(head, text="NEW", font=self.f_small, bg="#ffd23f", fg="#c0102a", padx=F)
            nl.pack(side="right", padx=F)
            self.new_labels.append(nl)

        body = tk.Frame(card, bg=CREAM)
        body.pack(fill="x")
        icon_name, scol, stext = STATUS_STYLE.get(s.status, STATUS_STYLE["working"])
        if s.status == "waiting":
            stext = f"codex 작업 기다리는 중 ({len(s.working_subs())})"
        elif s.status == "attention" and s.attn_label:
            stext = s.attn_label
        elif s.agent == "shell":
            stext = {"working": f"실행 중... {fmt_dur(time.time() - s.started)}째",
                     "done": s.attn_label}.get(s.status, stext)
        row = tk.Frame(body, bg=CREAM)
        row.pack(fill="x", padx=4 * F, pady=(3 * F, F))
        self.icon(row, icon_name, scol, CREAM).pack(side="left", padx=(0, 4 * F))
        tk.Label(row, text=stext, font=self.f_bold, bg=CREAM, fg=scol).pack(side="left")
        where = f"{snippet(s.project, 14)} #{s.sid[:4]}" if s.title else f"#{s.sid[:4]}"
        tk.Label(row, text=where, font=self.f_small, bg=CREAM, fg="#8a8070").pack(side="right")

        expanded = s.key in self.open_cards
        if s.message:
            msg = snippet(s.message, 600 if expanded else 80)
            tk.Label(body, text=msg, font=self.f_body, bg=CREAM, fg=INK, justify="left", anchor="w",
                     wraplength=wrap).pack(fill="x", padx=6 * F, pady=(0, 3 * F))

        subs = sorted(s.subs.values(), key=lambda x: x.updated)
        if subs:
            sb = tk.Frame(body, bg=CREAM)
            sb.pack(fill="x", padx=6 * F, pady=(0, 3 * F))
            for sub in (subs if expanded else subs[-3:]):
                r = tk.Frame(sb, bg=CREAM)
                r.pack(fill="x")
                tk.Label(r, text="└", font=self.f_small, bg=CREAM, fg="#808080").pack(side="left")
                done = sub.status == "done"
                self.icon(r, "check" if done else "hourglass", "#2e8b3e" if done else "#b8860b",
                          CREAM).pack(side="left", padx=2 * F)
                txt = "codex 완료" if done else "codex 작업중..."
                if sub.message:
                    txt += " · " + snippet(sub.message, 300 if expanded else 34)
                tk.Label(r, text=txt, font=self.f_small, bg=CREAM, fg="#4a4a4a", justify="left",
                         anchor="w", wraplength=wrap - 30 * F).pack(side="left", fill="x")
            if not expanded and len(subs) > 3:
                tk.Label(sb, text=f"   … 서브 작업 {len(subs) - 3}개 더", font=self.f_small,
                         bg=CREAM, fg="#808080").pack(anchor="w")

        if s.cmds:
            cb = tk.Frame(body, bg=CREAM)
            cb.pack(fill="x", padx=6 * F, pady=(0, 3 * F))
            for label, started in sorted(s.cmds.values(), key=lambda x: x[1]):
                r = tk.Frame(cb, bg=CREAM)
                r.pack(fill="x")
                tk.Label(r, text="└ $", font=self.f_small, bg=CREAM, fg=SHELL_C).pack(side="left")
                txt = f"실행 중 {fmt_dur(time.time() - started)}째 · " + snippet(label, 300 if expanded else 34)
                tk.Label(r, text=txt, font=self.f_small, bg=CREAM, fg="#4a4a4a", justify="left",
                         anchor="w", wraplength=wrap - 30 * F).pack(side="left", fill="x")

        foot = tk.Frame(body, bg=CREAM)
        foot.pack(fill="x", padx=4 * F, pady=(0, 2 * F))
        jumpable = bool(s.hwnd)
        if jumpable:
            tk.Label(foot, text="▶ 클릭하면 이 세션으로 이동", font=self.f_small, bg=CREAM,
                     fg="#3a6ea5").pack(side="left")
        more = None
        if len(snippet(s.message, 10_000)) > 80 or len(subs) > 3 or expanded:
            more = tk.Label(foot, text="▲ 접기" if expanded else "▼ 자세히", font=self.f_small, bg=FACE,
                            fg=INK, bd=F, relief="raised", padx=2 * F, cursor="hand2")
            more.pack(side="right")
            more.bind("<Button-1>", lambda e, k=s.key: (self.toggle_detail(k), "break")[1])

        def bind_all(w):
            if w is not close and w is not more:
                w.bind("<Button-1>", lambda e, k=s.key: self.on_card_click(k))
                if jumpable:
                    w.configure(cursor="hand2")
                for ch in w.winfo_children():
                    bind_all(ch)
        bind_all(card)

    def render(self):
        self.dirty = False
        self.draw_title()
        enabled = self.settings["enabled"]
        self.btn_onoff.configure(text="알림 ON" if enabled else "알림 OFF",
                                 fg="#1a7a2a" if enabled else "#a01020", relief="raised")
        n_work = sum(1 for s in self.sessions.values() if s.status in ("working", "waiting"))
        n_done = sum(1 for s in self.sessions.values() if s.status == "done")
        n_unread = sum(1 for s in self.sessions.values() if s.unread)
        self.status.configure(text=f" 작업중 {n_work} · 완료 {n_done} · 새 알림 {n_unread}")
        in_usage = self.view == "usage"
        for view, t in self.tabs.items():
            on = view == self.view
            label = ("알림" + (f" ({n_unread})" if n_unread else "")) if view == "alerts" else "사용량"
            t.configure(text=label, font=self.f_bold if on else self.f_small,
                        bg=FACE if on else "#b4b0a8", pady=2 * self.F if on else 0)
        if not self.panel_visible or self.settings.get("collapsed"):
            if self.panel_visible:
                self.place_panel()
            return

        y0 = self.list_cv.yview()[0]
        for w in self.inner.winfo_children():
            w.destroy()
        self.new_labels = []
        sessions = self.sorted_sessions()
        if len(sessions) <= VISIBLE_LIMIT or in_usage:
            self.expanded = False
        shown = [] if in_usage else sessions if self.expanded else sessions[:VISIBLE_LIMIT]
        if in_usage:
            self.build_usage()
        elif not shown:
            tk.Label(self.inner, text="\n  알림이 없어요. zZ\n", font=self.f_body, bg="#808080",
                     fg="#ffffff", anchor="w").pack(fill="x")
        for s in shown:
            self.build_card(s)
        tk.Frame(self.inner, bg="#808080", height=2 * self.F).pack(fill="x")

        extra = 0 if in_usage else len(sessions) - VISIBLE_LIMIT
        if extra > 0:
            self.btn_expand.configure(text="접기 ▲" if self.expanded else f"펼치기 ▼ (+{extra})")
            self.btn_expand.pack(side="right")
        else:
            self.btn_expand.pack_forget()

        self.inner.update_idletasks()
        h = self.inner.winfo_reqheight()
        _l, t, _r, b = work_area()
        maxh = int((b - t) * 0.55)
        if self.expanded and h > maxh:
            self.list_cv.configure(height=maxh)
            self.scroll.pack(side="right", fill="y")
            self.list_cv.update_idletasks()
            self.list_cv.yview_moveto(y0)
        else:
            self.scroll.pack_forget()
            self.list_cv.configure(height=h)
            self.list_cv.yview_moveto(0)
        self.place_panel()

    # ── 사용량 탭 ──
    def build_usage(self):
        F = self.F
        self.usage_drawn = time.time()
        installed = usage.claude_relay_installed()
        for agent, tag, color, u in (("claude", " CLAUDE ", CLAUDE_C, usage.read_claude()),
                                     ("codex", " CODEX ", CODEX_C, usage.read_codex())):
            card = tk.Frame(self.inner, bg=FACE, bd=2 * F, relief="raised")
            card.pack(fill="x", padx=2 * F, pady=(2 * F, 0))
            head = tk.Frame(card, bg=color)
            head.pack(fill="x")
            tk.Label(head, text=tag, font=self.f_small, bg=INK, fg="#ffffff").pack(
                side="left", padx=(2 * F, 3 * F), pady=2 * F)
            title = "사용량" + (f" · {u['plan'].upper()}" if u and u.get("plan") else "")
            tk.Label(head, text=title, font=self.f_bold, bg=color, fg="#ffffff").pack(side="left")
            if u and u["limits"]:
                tk.Label(head, text=usage.fmt_ago(u["ts"]) + " 기준", font=self.f_small,
                         bg=color, fg="#ffffff").pack(side="right", padx=3 * F)
            body = tk.Frame(card, bg=CREAM)
            body.pack(fill="x")
            if u and u["limits"]:
                for label, pct, resets in u["limits"]:
                    self.usage_row(body, label, pct, resets, color)
                tk.Frame(body, bg=CREAM, height=2 * F).pack()
                continue
            if agent == "claude" and not installed:
                hint = "연결이 필요해요.\nClaude Code에서 /pixelpet:usage 를 실행하세요."
            elif agent == "claude":
                hint = "Claude가 한 번 답하면 표시돼요.\n(Pro/Max 구독만 한도 정보가 있어요)"
            else:
                hint = "Codex 사용 기록이 아직 없어요.\nCodex를 한 번 쓰면 표시돼요."
            tk.Label(body, text=hint, font=self.f_small, bg=CREAM, fg="#6a6050", justify="left",
                     anchor="w").pack(fill="x", padx=6 * F, pady=4 * F)
        tk.Label(self.inner, text=" 각 앱이 마지막으로 알려준 값이에요", font=self.f_small,
                 bg="#808080", fg="#e8e8e8", anchor="w").pack(fill="x", pady=(2 * F, 0))

    def usage_row(self, parent, label, pct, resets, color):
        """5시간 [■■■■■□□□□□] 47%  +  초기화 시각 (90년대 세그먼트 진행바)."""
        F = self.F
        row = tk.Frame(parent, bg=CREAM)
        row.pack(fill="x", padx=5 * F, pady=(4 * F, 0))
        tk.Label(row, text=label, font=self.f_bold, bg=CREAM, fg=INK, width=5, anchor="w").pack(side="left")
        tk.Label(row, text=f"{pct:.0f}%", font=self.f_bold, bg=CREAM, width=4, anchor="e",
                 fg="#c0102a" if pct >= 90 else INK).pack(side="right")
        segs, sw, gap, h = 20, 7 * F, F, 9 * F
        bar = tk.Canvas(row, width=segs * (sw + gap) + 3 * F, height=h + 4 * F, bg="#ffffff",
                        highlightthickness=0, bd=F, relief="sunken")
        bar.pack(side="left", padx=4 * F)
        fill = "#e8364f" if pct >= 90 else "#e0a21b" if pct >= 70 else color
        n = max(1, round(pct / 100 * segs)) if pct > 0 else 0
        for i in range(segs):
            x = 2 * F + i * (sw + gap)
            bar.create_rectangle(x, 2 * F, x + sw, 2 * F + h, outline="", fill=fill if i < n else "#e6e1d2")
        reset = usage.fmt_reset(resets)
        if reset:
            tk.Label(parent, text=reset, font=self.f_small, bg=CREAM, fg="#8a8070",
                     anchor="e").pack(fill="x", padx=6 * F)

    def toggle_usage(self):
        self.set_view("alerts" if self.view == "usage" else "usage")

    def set_view(self, view):
        if self.view != view:
            self.view = view
            self.render()

    def place_panel(self):
        self._place_now()
        self.root.after(60, self._place_now)  # 레이아웃 변경이 한 박자 늦게 반영되는 경우 대비

    def _place_now(self):
        p = self.panel
        p.update_idletasks()
        pw, ph = max(p.winfo_reqwidth(), self.panel_width), p.winfo_reqheight()
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        l, t, r, b = work_area()
        gap = 2 * self.F
        x = rx + self.pet_w - pw
        y = ry - ph - gap
        if y < t:
            y = ry + self.pet_h + gap
            if y + ph > b:
                y = max(t, b - ph)
        x = min(max(l, x), r - pw)
        p.geometry(f"{pw}x{ph}+{x}+{y}")

    def show_panel(self):
        if not self.panel_visible:
            self.panel_visible = True
            self.panel.deiconify()
        self.panel.lift()
        self.render()

    def hide_panel(self):
        self.panel_visible = False
        self.panel.unbind_all("<MouseWheel>")
        self.panel.withdraw()

    def toggle_panel(self):
        self.hide_panel() if self.panel_visible else self.show_panel()

    def toggle_collapse(self):
        c = not self.settings.get("collapsed")
        self.settings["collapsed"] = c
        self.save_settings()
        if c:
            self.content.pack_forget()
            self.btn_collapse.configure(text="□")
        else:
            self.content.pack(fill="both", expand=True)
            self.btn_collapse.configure(text="_")
        self.render()

    def toggle_expand(self):
        self.expanded = not self.expanded
        self.render()

    def toggle_enabled(self):
        self.settings["enabled"] = not self.settings["enabled"]
        self.save_settings()
        self.render()

    def toggle_sound(self):
        self.settings["sound"] = not self.settings["sound"]
        self.save_settings()

    def clear_all(self):
        for k in [k for k, s in self.sessions.items() if s.status not in ("working", "waiting")]:
            del self.sessions[k]
        for s in self.sessions.values():
            s.unread = False
        self.open_cards.clear()
        self.expanded = False
        self.view = "alerts"
        self.render()

    def dismiss(self, key):
        self.sessions.pop(key, None)
        self.open_cards.discard(key)
        self.render()

    def on_card_click(self, key):
        """카드 클릭: 읽음 처리 + 해당 세션 터미널로 이동 (이동 불가하면 자세히 보기 토글)."""
        s = self.sessions.get(key)
        if not s:
            return
        s.unread = False
        if s.pid:
            self.refresh_info(s)
        if s.hwnd and winfocus.focus(s.hwnd, s.raw_title or s.title,
                                     pid=s.pid if s.agent in ("claude", "shell") else None):
            self.render()
            return
        self.toggle_detail(key)

    def toggle_detail(self, key):
        s = self.sessions.get(key)
        if s:
            s.unread = False
        if key in self.open_cards:
            self.open_cards.discard(key)
        else:
            self.open_cards.add(key)
        self.render()

    def refresh_info(self, s):
        """세션 이름/터미널 창 갱신. 바뀌면 True."""
        before = (s.title, s.hwnd)
        try:
            if s.agent == "claude" and s.pid:
                raw, hwnd = winfocus.console_info(s.pid)
                if winfocus.clean_title(raw):
                    s.title, s.raw_title = winfocus.clean_title(raw), raw
                s.hwnd = hwnd or s.hwnd or winfocus.ancestor_window(s.pid)
            elif s.agent == "shell" and s.pid and not s.hwnd:   # 제목은 그대로 두고 창만
                _raw, hwnd = winfocus.console_info(s.pid)
                s.hwnd = hwnd or winfocus.ancestor_window(s.pid)
            elif s.agent == "codex" and not s.title and s.sid:
                name = winfocus.codex_thread_name(s.sid)
                s.title = re.sub(r"^Codex Companion Task:\s*", "", name)
        except Exception as ex:
            print("info error:", ex, file=sys.stderr)
        return (s.title, s.hwnd) != before

    # ── 메뉴 ──
    def _build_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, font=self.f_body)
        self.v_enabled = tk.BooleanVar()
        self.v_sound = tk.BooleanVar()
        self.v_auto = tk.BooleanVar()
        self.menu.add_checkbutton(label="알림 켜기", variable=self.v_enabled, command=self.toggle_enabled)
        self.menu.add_checkbutton(label="소리", variable=self.v_sound, command=self.toggle_sound)
        self.v_skin = tk.StringVar(value=self.skin_id())
        skins = tk.Menu(self.menu, tearoff=0, font=self.f_body)
        for sid, sk in SKINS.items():
            if sid == "wibee":  # 위비프렌즈는 구분선 아래에 따로
                skins.add_separator()
            skins.add_radiobutton(label=sk["name"], value=sid, variable=self.v_skin, command=self.set_skin)
        self.menu.add_cascade(label="펫 고르기", menu=skins)
        self.menu.add_separator()
        self.menu.add_command(label="알림함 열기/닫기", command=self.toggle_panel)
        self.menu.add_command(label="모두 정리", command=self.clear_all)
        self.menu.add_command(label="테스트 알림", command=self.test_alert)
        self.menu.add_separator()
        self.menu.add_checkbutton(label="윈도우 시작 시 실행", variable=self.v_auto, command=self.toggle_autostart)
        self.menu.add_command(label="종료", command=self.quit)

    def set_skin(self):
        self.settings["skin"] = self.v_skin.get()
        self.save_settings()
        self.draw_pet()

    def on_menu(self, e):
        self.v_enabled.set(self.settings["enabled"])
        self.v_sound.set(self.settings["sound"])
        self.v_auto.set(autostart.is_enabled())
        self.menu.tk_popup(e.x_root, e.y_root)

    def toggle_autostart(self):
        try:
            autostart.enable() if self.v_auto.get() else autostart.disable()
        except Exception as ex:
            print("autostart error:", ex, file=sys.stderr)

    def test_alert(self):
        s = Session(f"test:{time.time()}", random.choice(["claude", "codex"]), "%04x" % random.randrange(65536))
        s.cwd, s.title = "PixelPet", "테스트 알림"
        s.message = "테스트 알림이에요! 작업이 끝나면 이렇게 알려줄게요."
        self.sessions[s.key] = s
        self.fire(s)

    def quit(self):
        self.save_settings()
        try:
            self.server.shutdown()
        except Exception:
            pass
        self.root.destroy()

    def keep_on_top(self):
        for w in (self.root, self.panel):
            try:
                w.attributes("-topmost", True)
            except Exception:
                pass
        self.root.after(30000, self.keep_on_top)

    def debug_state(self):
        out = {"enabled": self.settings["enabled"], "panel": self.panel_visible,
               "panel_geo": self.panel.winfo_geometry(),
               "panel_req": [self.panel.winfo_reqwidth(), self.panel.winfo_reqheight()], "sessions": [],
               "shell_runs": {str(k): v for k, v in self.shell_runs.items()}}
        for s in list(self.sessions.values()):
            d = {k: v for k, v in vars(s).items() if k != "subs"}
            d["subs"] = [vars(x) for x in list(s.subs.values())]
            out["sessions"].append(d)
        return out

    # ── 알림 발생 ──
    def fire(self, s, kind="done", label=""):
        now = time.time()
        if kind == "attention":
            repeat = s.status == "attention" and now - s.attn_at < 5   # 같은 대기에 훅이 겹쳐 오면 한 번만
            s.attn_label, s.attn_at = label or "확인이 필요해요!", now
            if repeat:
                self.dirty = True
                return
        s.status = "done" if kind == "done" else "attention"
        s.unread = True
        s.updated = now
        s.ready_at = None
        if self.settings["enabled"]:
            self.last_alert = now
            if self.settings["sound"]:
                try:
                    winsound.PlaySound(self.snd_done if kind == "done" else self.snd_attn,
                                       winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                except Exception:
                    pass
            self.view = "alerts"   # 새 알림이 오면 알림 목록으로
            self.show_panel()
        self.dirty = True

    # ── 이벤트 처리 ──
    def claude_session(self, sid, pid):
        key = f"claude:{sid}"
        s = self.sessions.get(key)
        if s is None and pid:
            # codex 훅이 먼저 와서 만든 임시 세션이 있으면 이어받는다
            tmp = self.sessions.pop(f"claude:pid:{pid}", None)
            if tmp:
                tmp.key, tmp.sid = key, sid
                s = tmp
        if s is None:
            s = Session(key, "claude", sid)
        self.sessions[key] = s
        if pid:
            s.pid = pid
        return s

    def codex_parent(self, e):
        """Claude 가 띄운 codex 이벤트의 부모 Claude 세션."""
        csid, cpid = e.get("claude_session_id"), e.get("claude_pid")
        parent = self.sessions.get(f"claude:{csid}") if csid else None
        if parent is None and cpid:
            parent = self.find_claude_by_pid(cpid)
        if parent is None:
            parent = self.claude_session(csid, cpid) if csid else Session(f"claude:pid:{cpid}", "claude", f"pid{cpid}")
            parent.cwd = parent.cwd or e.get("cwd") or ""
            self.sessions[parent.key] = parent
        if cpid and not parent.pid:
            parent.pid = cpid
        return parent

    @staticmethod
    def match_sub(parent, thread, pid):
        """훅(thread id)과 프로세스 감시(pid)로 들어온 같은 codex 작업을 하나로 묶는다."""
        for sub in parent.subs.values():
            if sub.thread == thread or (pid and sub.pid == pid):
                sub.thread = sub.thread or thread
                return sub
        loose = [x for x in parent.subs.values() if x.thread is None and x.status == "working"]
        if loose:
            sub = max(loose, key=lambda x: x.updated)
            sub.thread = thread
            return sub
        key = f"pid:{pid}" if pid else f"sid:{thread}"
        sub = parent.subs[key] = Sub(key, pid)
        sub.thread = thread
        return sub

    def find_claude_by_pid(self, pid):
        cands = [s for s in self.sessions.values() if s.agent == "claude" and s.pid == pid]
        return max(cands, key=lambda s: s.updated) if cands else None

    def handle(self, e):
        cmd = e.get("_cmd")  # 로컬 제어용 (quit 외에는 PIXELPET_DEBUG=1 일 때만)
        if cmd == "quit":         # 업데이트 시 새 버전으로 재시작하기 위해
            self.quit()
            return
        if cmd and not runtime.DEBUG:
            return
        if cmd in ("toggle_expand", "toggle_collapse", "toggle_enabled", "clear_all", "toggle_usage", "show_panel",
                   "hide_panel", "test_alert"):
            getattr(self, cmd)()
            return
        if cmd == "skin" and e.get("skin") in SKINS:
            self.settings["skin"] = e["skin"]
            self.v_skin.set(e["skin"])
            return
        if cmd == "click":
            self.on_card_click(e.get("key", ""))
            return
        src, ev = e.get("source"), e.get("event")
        if src == "shell":
            self.handle_shell(e)
            return
        sid = e.get("session_id") or "unknown"
        msg = e.get("message") or ""
        now = time.time()

        if src == "codex" and (e.get("claude_session_id") or e.get("claude_pid")):
            parent = self.codex_parent(e)
            sub = self.match_sub(parent, sid, e.get("codex_pid"))
            sub.updated = now
            sub.transcript = e.get("transcript_path") or sub.transcript
            if ev == "UserPromptSubmit":
                sub.status = "working"
                self.reopen(parent)
            elif ev == "Stop":
                sub.status = "done"
                sub.message = msg
            elif ev == "PermissionRequest":
                parent.message = msg or parent.message
                self.fire(parent, kind="attention", label="codex 승인이 필요해요!")
                self.dirty = True
                return
            self.evaluate(parent)
            self.dirty = True
            return

        if src == "claude":
            s = self.claude_session(sid, e.get("claude_pid"))
        else:
            key = f"codex:{sid}"
            s = self.sessions.get(key) or Session(key, "codex", sid)
            self.sessions[key] = s
        s.cwd = e.get("cwd") or s.cwd
        s.transcript = e.get("transcript_path") or s.transcript

        if ev == "UserPromptSubmit":
            s.status, s.stopped, s.waited, s.ready_at = "working", False, False, None
            s.unread = False
            s.message = ""
            s.subs = {k: v for k, v in s.subs.items() if v.status == "working"}
            s.updated = now
            self.open_cards.discard(s.key)
        elif ev == "Stop":
            s.message = msg or s.message
            if src == "codex":
                self.fire(s)
            else:
                s.stopped = True
                s.ready_at = None
                self.scan_now(s)
                s.waited = bool(s.working_subs())
                self.evaluate(s)
        elif ev == "Notification":
            ntype = e.get("notification_type") or ""
            if ntype in ("idle_prompt", "auth_success") or "waiting for your input" in msg.lower():
                return
            s.message = msg
            self.fire(s, kind="attention", label="확인이 필요해요!")
        elif ev == "PreToolUse" and e.get("tool_name") == "AskUserQuestion":
            s.message = msg or s.message
            self.fire(s, kind="attention", label="선택이 필요해요!")
        elif ev == "PermissionRequest":           # Codex 승인 요청
            s.message = msg or s.message
            self.fire(s, kind="attention", label="승인이 필요해요!")
        self.refresh_info(s)
        self.dirty = True

    # ── 일반 셸 명령 ──
    # 시작 이벤트는 shell_runs 에만 담아 두고, SHELL_MIN_SEC 을 넘기면 poll 이 세션(카드)으로 올린다
    # → 금방 끝나는 ls, cd 같은 건 화면에 아무것도 안 나타남
    @staticmethod
    def shell_skipped(cmd):
        words = cmd.strip().split()
        if not words:
            return True
        first = os.path.basename(words[0].strip("&'\"")).lower()
        first = first[:-4] if first.endswith((".exe", ".cmd", ".bat", ".ps1")) else first
        return first in SHELL_SKIP or (len(words) == 1 and first in SHELL_SKIP_BARE)

    def handle_shell(self, e):
        try:
            pid, run = int(e.get("pid")), int(e.get("run"))
        except (TypeError, ValueError):
            return
        if e.get("event") == "start":
            if (pid, run) in self.shell_ended:          # 끝 이벤트가 먼저 도착한 짧은 명령
                return
            self.end_shell_card(pid)                   # 같은 창에서 새 명령 → 이전 것은 정리
            cmd = str(e.get("cmd") or "")
            if not self.shell_skipped(cmd):
                self.shell_runs[pid] = {"run": run, "cmd": cmd[:2000], "cwd": e.get("cwd") or "",
                                        "t0": time.time()}
            return
        self.shell_ended.append((pid, run))
        info = self.shell_runs.get(pid)
        if info and info["run"] == run:
            del self.shell_runs[pid]
        s = self.sessions.get(f"shell:{pid}:{run}")
        if not s or s.status != "working":
            return
        dur = fmt_dur(time.time() - s.started)
        code = e.get("code")
        if e.get("ok") is not False:
            s.attn_label = f"명령 완료! ({dur})"
            self.fire(s)
        elif code in CTRL_C_CODES:                     # 사용자가 직접 멈춤 → 알릴 필요 없음
            self.sessions.pop(s.key, None)
            self.dirty = True
        else:
            failed = f"명령 실패 (코드 {code})" if code not in (None, 0) else "명령 실패"
            self.fire(s, kind="attention", label=f"{failed} · {dur}")

    def end_shell_card(self, pid):
        """끝 이벤트를 못 받은 채 남은 카드 정리 (창을 닫았거나 같은 창에서 새 명령)."""
        for s in list(self.sessions.values()):
            if s.agent == "shell" and s.pid == pid and s.status == "working":
                self.sessions.pop(s.key, None)
                self.dirty = True

    def poll_shell(self, procs):
        now = time.time()
        for pid, info in list(self.shell_runs.items()):
            if procs.get(pid, (0, ""))[1] not in SHELL_PROCS:
                del self.shell_runs[pid]               # 창을 닫음
            elif now - info["t0"] >= SHELL_MIN_SEC:
                del self.shell_runs[pid]
                s = Session(f"shell:{pid}:{info['run']}", "shell", str(pid))
                s.pid, s.cwd, s.message, s.started = pid, info["cwd"], info["cmd"], info["t0"]
                self.sessions[s.key] = s
                self.refresh_info(s)
                self.dirty = True
        running = any(s.cmds for s in self.sessions.values())
        for s in list(self.sessions.values()):
            if s.agent == "shell" and s.status == "working":
                running = True
                if procs.get(s.pid, (0, ""))[1] not in SHELL_PROCS:
                    self.end_shell_card(s.pid)
        if running and self.panel_visible and self.view == "alerts" and now - self.shell_drawn > 10:
            self.shell_drawn = now                     # 실행 시간 표시는 10초마다 갱신
            self.dirty = True

    @staticmethod
    def answered(s):
        """승인/선택 대기 후 대화 기록이 다시 쓰이기 시작했으면 = 사용자가 답했고 작업 재개."""
        try:
            return bool(s.transcript) and os.path.getmtime(s.transcript) > s.attn_at + 3
        except OSError:
            return False

    @staticmethod
    def reopen(parent):
        """이미 '완료' 처리된 Claude 세션에서 codex 가 새로 시작됨 → 다시 기다리는 상태로."""
        if parent.status in ("done", "ended") and parent.stopped:
            parent.status, parent.waited, parent.ready_at, parent.unread = "waiting", True, None, False

    def evaluate(self, s):
        """Claude 세션: Claude 가 멈췄고 하위 codex 가 모두 끝났을 때만 알림."""
        if s.agent != "claude" or s.status in ("done", "ended"):
            return
        if not s.stopped:
            if s.status != "attention":
                s.status = "working"
            return
        if s.working_subs():
            s.status, s.waited, s.ready_at = "waiting", True, None
            return
        if s.waited:
            # 백그라운드 codex 가 끝나면 Claude 가 다시 이어서 작업할 수 있으니 잠깐 지켜본다
            now = time.time()
            if s.ready_at is None:
                s.ready_at = now
                return
            if now - s.ready_at < 4:
                return
            try:
                mt = os.path.getmtime(s.transcript) if s.transcript else 0
            except OSError:
                mt = 0
            if mt > s.ready_at + 0.3:
                s.stopped, s.waited, s.ready_at, s.status = False, False, None, "working"
                self.dirty = True
                return
        self.fire(s)

    def drain(self):
        try:
            while True:
                e = self.q.get_nowait()
                try:
                    self.handle(e)
                except Exception as ex:
                    print("event error:", ex, e, file=sys.stderr)
        except queue.Empty:
            pass
        if self.dirty:
            self.render()
        self.root.after(100, self.drain)

    def scan_now(self, s):
        try:
            procs = proctree.snapshot()
            self.scan_session(s, procs, proctree.children_map(procs))
        except Exception as ex:
            print("scan error:", ex, file=sys.stderr)

    def scan_session(self, s, procs, kids):
        """Claude 세션 아래의 codex 프로세스 감시 + 멈춘 서브작업 정리."""
        now = time.time()
        for sub in s.subs.values():
            if sub.status != "working":
                continue
            try:
                last = os.path.getmtime(sub.transcript) if sub.transcript else sub.updated
            except OSError:
                last = sub.updated
            if now - max(last, sub.updated) > 15 * 60:
                sub.status, sub.message = "done", sub.message or "(15분 넘게 응답이 없어 종료로 처리)"
                self.dirty = True
        if not s.pid:
            return
        if procs.get(s.pid, (0, ""))[1] != "claude.exe":
            if s.cmds:
                s.cmds = {}
                self.dirty = True
            for sub in s.subs.values():
                sub.status = "done" if sub.status == "working" else sub.status
            if s.status in ("working", "waiting", "attention"):
                s.status = "ended"
                self.dirty = True
            return
        # Git Bash 경유 실행 등에선 프로세스 트리가 끊겨 못 찾을 수 있다 → 훅이 주 신호, 이건 보조
        roots = set(proctree.root_codex_under(s.pid, procs, kids))
        known = {x.pid for x in s.subs.values()}
        for r in roots - known:
            loose = [x for x in s.subs.values() if x.pid is None and x.status == "working"]
            if loose:
                max(loose, key=lambda x: x.updated).pid = r
            else:
                s.subs[f"pid:{r}"] = Sub(f"pid:{r}", r)
                self.reopen(s)
            self.dirty = True
        for sub in s.subs.values():
            if sub.pid and sub.status == "working" and sub.pid not in roots:
                sub.status, sub.updated = "done", now
                self.dirty = True
        cmds = self.tool_commands(s.pid, procs, kids)
        if cmds.keys() != s.cmds.keys():
            self.dirty = True
        s.cmds = cmds

    def tool_commands(self, claude_pid, procs, kids):
        """Claude 의 Bash/PowerShell 도구로 실행돼 SHELL_MIN_SEC 넘게 도는 명령 (백그라운드 포함)."""
        out, now = {}, time.time()
        for child in kids.get(claude_pid, []):
            name = procs.get(child, (0, ""))[1]
            if name not in ("bash.exe", "cmd.exe"):
                continue
            info = self.tool_cache.get(child)
            if info is None:
                cmd, started = proctree.process_info(child)
                label = ""
                if name == "bash.exe" and "shell-snapshots" in cmd:      # Bash 도구
                    label = tool_command_label(cmd) or "bash 명령"
                elif name == "cmd.exe":                                   # PowerShell 도구: cmd → powershell
                    for g in kids.get(child, []):
                        if procs.get(g, (0, ""))[1] in ("powershell.exe", "pwsh.exe") and \
                                "CLAUDE_CODE_SHELL_LAUNCHER" in proctree.process_info(g)[0]:
                            label = self.first_program(g, procs, kids) or "PowerShell 명령"
                            break
                    else:
                        if kids.get(child):          # 아직 powershell 이 안 떴을 수 있음 → 다음에 다시 확인
                            continue
                info = self.tool_cache[child] = (label, started or now)
            if info[0] and now - info[1] >= SHELL_MIN_SEC:
                out[child] = info
        if len(self.tool_cache) > 500:
            self.tool_cache = {p: v for p, v in self.tool_cache.items() if p in procs}
        return out

    @staticmethod
    def first_program(pid, procs, kids):
        """셸 아래에서 처음 나오는 실제 프로그램의 명령줄."""
        stack = list(kids.get(pid, []))
        while stack:
            p = stack.pop(0)
            if procs.get(p, (0, ""))[1] in SHELL_EXES:
                stack.extend(kids.get(p, []))
                continue
            return short_cmdline(proctree.process_info(p)[0])
        return ""

    def poll(self):
        try:
            procs = proctree.snapshot()
            kids = proctree.children_map(procs)
            for s in list(self.sessions.values()):
                if s.status == "attention" and self.answered(s):
                    s.status, s.stopped = "working", False
                    self.dirty = True
                if s.agent == "codex" and not s.title and self.refresh_info(s):
                    self.dirty = True
                if s.agent != "claude":
                    continue
                self.scan_session(s, procs, kids)
                if s.pid and s.status != "ended" and procs.get(s.pid, (0, ""))[1] == "claude.exe":
                    if self.refresh_info(s):
                        self.dirty = True
                if s.stopped and s.status in ("working", "waiting"):
                    before = s.status
                    self.evaluate(s)
                    if s.status != before:
                        self.dirty = True
            self.poll_shell(procs)
            # 오래된 기록 정리
            if len(self.sessions) > 80:
                for s in sorted(self.sessions.values(), key=lambda s: s.updated)[: len(self.sessions) - 80]:
                    if s.status not in ("working", "waiting"):
                        self.sessions.pop(s.key, None)
            if self.view == "usage" and self.panel_visible and time.time() - self.usage_drawn > 20:
                self.dirty = True   # 사용량 탭은 20초마다 다시 읽는다
        except Exception as ex:
            print("poll error:", ex, file=sys.stderr)
        self.root.after(1500, self.poll)

    def animate(self):
        self.frame_no += 1
        self.draw_pet()
        if self.frame_no % 3 == 0:
            on = (self.frame_no // 3) % 2 == 0
            for nl in self.new_labels:
                try:
                    nl.configure(bg="#ffd23f" if on else "#ff6b3d")
                except tk.TclError:
                    pass
        self.root.after(160, self.animate)

    def run(self):
        self.root.mainloop()


def main():
    set_dpi_aware()
    q = queue.Queue()
    Handler.q = q
    try:
        server = ExclusiveServer(("127.0.0.1", PORT), Handler)
    except OSError:
        return  # 이미 실행 중
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    App(server, q).run()


if __name__ == "__main__":
    main()
