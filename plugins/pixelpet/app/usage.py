"""사용량(요금제 한도) 읽기.

한도는 계정 단위라 다른 PC 에서 쓴 양도 반영되도록, 사용량 탭이 열려 있으면
각 서비스의 사용량 API 를 직접 물어본다 (이 PC 에 로그인된 토큰 사용, 토큰 갱신은 하지 않음).
실패하면 로컬 기록 중 더 최근 것을 쓴다:
- Claude: Claude Code 가 상태줄(statusLine) 명령에 넘겨주는 rate_limits 를
          statusline.py 가 data/claude_usage.json 에 저장해 둔 것 (Pro/Max 구독에서만 값이 있음)
- Codex : ~/.codex/sessions/**/rollout-*.jsonl 의 마지막 token_count 이벤트에 있는 rate_limits
"""
import calendar
import datetime
import json
import os
import threading
import time
import urllib.request

import runtime

CLAUDE_FILE = os.path.join(runtime.DATA_DIR, "claude_usage.json")
CLAUDE_SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
CODEX_SESSIONS = os.path.join(os.path.expanduser("~"), ".codex", "sessions")
RELAY_MARK = "statusline.py"
CLAUDE_CRED = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
CODEX_AUTH = os.path.join(os.path.expanduser("~"), ".codex", "auth.json")
CLAUDE_URL = "https://api.anthropic.com/api/oauth/usage"
CODEX_URL = "https://chatgpt.com/backend-api/wham/usage"
ONLINE_EVERY, ONLINE_BACKOFF = 60, 300   # 성공 시 1분, 실패 시 5분 뒤에 다시

_codex_cache = {}  # path -> (mtime, result)
_online = {}       # agent -> 서버에서 받은 결과
_next_try = {}     # agent -> 다음에 물어볼 시각
_busy = set()
_updated = threading.Event()
_lock = threading.Lock()


def window_label(minutes):
    if not minutes:
        return "한도"
    if minutes == 300:
        return "5시간"
    if minutes == 10080:
        return "주간"
    return f"{minutes // 1440}일" if minutes >= 1440 else f"{max(1, minutes // 60)}시간"


def _limit(label, pct, resets_at):
    """(이름, 사용 %, 초기화 시각 epoch | None). 초기화 시각이 지났으면 0% 로 본다."""
    try:
        pct = float(pct)
    except (TypeError, ValueError):
        return None
    try:
        resets_at = float(resets_at) if resets_at is not None else None
    except (TypeError, ValueError):
        resets_at = None
    if resets_at and resets_at < time.time():
        pct = 0.0
    return label, max(0.0, min(100.0, pct)), resets_at


def claude_relay_installed():
    try:
        with open(CLAUDE_SETTINGS, encoding="utf-8") as f:
            sl = json.load(f).get("statusLine") or {}
        return RELAY_MARK in (sl.get("command") or "")
    except (OSError, ValueError, AttributeError):
        return False


def read_claude():
    """{'ts', 'limits': [...]} 또는 None — 서버 값과 로컬 기록 중 최신."""
    return _newer(_online.get("claude"), _read_claude_local())


def _read_claude_local():
    try:
        with open(CLAUDE_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    rl = d.get("rate_limits") or {}
    limits = []
    for key, label in (("five_hour", "5시간"), ("seven_day", "주간")):
        v = rl.get(key)
        if isinstance(v, dict) and v.get("used_percentage") is not None:
            lim = _limit(label, v["used_percentage"], v.get("resets_at"))
            if lim:
                limits.append(lim)
    return {"ts": d.get("ts") or 0, "limits": limits, "plan": ""}


def _recent_rollouts(max_days=4, max_files=8):
    """가장 최근 날짜 폴더 몇 개에서 rollout 파일을 수정시각 순으로."""
    days = []
    try:
        for y in sorted(os.listdir(CODEX_SESSIONS), reverse=True):
            yp = os.path.join(CODEX_SESSIONS, y)
            for m in sorted(os.listdir(yp), reverse=True) if os.path.isdir(yp) else []:
                mp = os.path.join(yp, m)
                for d in sorted(os.listdir(mp), reverse=True) if os.path.isdir(mp) else []:
                    days.append(os.path.join(mp, d))
                    if len(days) >= max_days:
                        raise StopIteration
    except StopIteration:
        pass
    except OSError:
        return []
    files = []
    for dp in days:
        try:
            for name in os.listdir(dp):
                if name.startswith("rollout-") and name.endswith(".jsonl"):
                    p = os.path.join(dp, name)
                    files.append((os.path.getmtime(p), p))
        except OSError:
            continue
    files.sort(reverse=True)
    return files[:max_files]


def _codex_from_file(path, mtime):
    # Codex 가 파일을 연 채로 쓰는 동안 Windows 는 수정 시각을 늦게 갱신한다
    # → 직접 열어서 잰 실제 크기로 바뀌었는지 판단
    try:
        with open(path, "rb") as f:
            size = f.seek(0, 2)
            hit = _codex_cache.get(path)
            if hit and hit[0] == size:
                return hit[1]
            f.seek(max(0, size - 300_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    result = None
    for line in reversed(lines):
        if '"rate_limits"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        rl = (d.get("payload") or {}).get("rate_limits")
        if not isinstance(rl, dict) or not rl.get("primary"):
            continue
        limits = []
        for key in ("primary", "secondary"):
            v = rl.get(key)
            if isinstance(v, dict):
                lim = _limit(window_label(v.get("window_minutes")), v.get("used_percent"), v.get("resets_at"))
                if lim:
                    limits.append(lim)
        ts = mtime
        try:
            ts = calendar.timegm(time.strptime(d["timestamp"][:19], "%Y-%m-%dT%H:%M:%S"))
        except (KeyError, ValueError, TypeError):
            pass
        result = {"ts": ts, "limits": limits, "plan": rl.get("plan_type") or ""}
        break
    _codex_cache[path] = (size, result)
    return result


def read_codex():
    """서버 값과 로컬 기록 중 최신."""
    return _newer(_online.get("codex"), _read_codex_local())


def _read_codex_local():
    """최근 파일들 중 기록 시각이 가장 늦은 것 (수정 시각 순서는 믿을 수 없어서 전부 비교)."""
    best = None
    for mtime, path in _recent_rollouts():
        r = _codex_from_file(path, mtime)
        if r and (best is None or r["ts"] > best["ts"]):
            best = r
    return best


def _newer(a, b):
    cands = [x for x in (a, b) if x and x.get("limits")]
    return max(cands, key=lambda x: x["ts"]) if cands else (a or b)


# ── 서버에서 직접 읽기 (다른 PC 에서 쓴 사용량까지 반영) ──
def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _claude_token():
    c = (_load_json(CLAUDE_CRED) or {}).get("claudeAiOauth") or {}
    tok, exp = c.get("accessToken"), c.get("expiresAt") or 0
    if not tok or (exp and exp / 1000 < time.time()):   # 만료된 토큰은 Claude Code 가 갱신할 때까지 기다린다
        return None, ""
    return tok, c.get("subscriptionType") or ""


def _codex_token():
    t = (_load_json(CODEX_AUTH) or {}).get("tokens") or {}
    return t.get("access_token"), t.get("account_id")


def has_login(agent):
    return bool((_claude_token() if agent == "claude" else _codex_token())[0])


def _get(url, headers):
    req = urllib.request.Request(url, headers={"User-Agent": "pixelpet", "Accept": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _iso_epoch(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def fetch_claude():
    tok, plan = _claude_token()
    if not tok:
        return None
    d = _get(CLAUDE_URL, {"Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20"})
    limits = []
    for key, label in (("five_hour", "5시간"), ("seven_day", "주간")):
        v = d.get(key)
        if isinstance(v, dict) and v.get("utilization") is not None:
            lim = _limit(label, v["utilization"], _iso_epoch(v.get("resets_at")))
            if lim:
                limits.append(lim)
    return {"ts": time.time(), "limits": limits, "plan": plan}


def fetch_codex():
    tok, account = _codex_token()
    if not tok:
        return None
    headers = {"Authorization": f"Bearer {tok}"}
    if account:
        headers["ChatGPT-Account-Id"] = account
    d = _get(CODEX_URL, headers)
    rl = d.get("rate_limit") or {}
    limits = []
    for key in ("primary_window", "secondary_window"):
        v = rl.get(key)
        if isinstance(v, dict):
            lim = _limit(window_label((v.get("limit_window_seconds") or 0) // 60), v.get("used_percent"),
                         v.get("reset_at"))
            if lim:
                limits.append(lim)
    return {"ts": time.time(), "limits": limits, "plan": d.get("plan_type") or ""}


def _fetch(agent, fn):
    try:
        r = fn()
        ok = bool(r and r["limits"])
        if ok:
            _online[agent] = r
            _updated.set()
    except Exception:
        ok = False
    with _lock:
        _next_try[agent] = time.time() + (ONLINE_EVERY if ok else ONLINE_BACKOFF)
        _busy.discard(agent)


def refresh_online():
    """필요하면 백그라운드에서 서버 사용량을 새로 받는다 (UI 를 막지 않음)."""
    now = time.time()
    for agent, fn in (("claude", fetch_claude), ("codex", fetch_codex)):
        with _lock:
            if agent in _busy or now < _next_try.get(agent, 0):
                continue
            _busy.add(agent)
        threading.Thread(target=_fetch, args=(agent, fn), daemon=True).start()


def take_updated():
    """마지막 확인 이후 서버 값이 새로 들어왔는지."""
    if _updated.is_set():
        _updated.clear()
        return True
    return False


def fmt_reset(ts):
    if not ts:
        return ""
    left = ts - time.time()
    if left <= 0:
        return "초기화됨"
    if left < 3600:
        return f"{max(1, int(left // 60))}분 후 초기화"
    if left < 86400:
        return f"{int(left // 3600)}시간 {int(left % 3600 // 60)}분 후 초기화"
    t = time.localtime(ts)
    wd = "월화수목금토일"[t.tm_wday]
    return f"{t.tm_mon}/{t.tm_mday}({wd}) {t.tm_hour:02d}:{t.tm_min:02d} 초기화"


def fmt_ago(ts):
    if not ts:
        return ""
    d = time.time() - ts
    if d < 60:
        return "방금"
    if d < 3600:
        return f"{int(d // 60)}분 전"
    if d < 86400:
        return f"{int(d // 3600)}시간 전"
    t = time.localtime(ts)
    return f"{t.tm_mon}/{t.tm_mday} {t.tm_hour:02d}:{t.tm_min:02d}"
