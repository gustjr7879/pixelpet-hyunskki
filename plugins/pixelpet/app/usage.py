"""사용량(요금제 한도) 읽기 — 네트워크 없이 로컬 파일만 본다.

- Claude: Claude Code 가 상태줄(statusLine) 명령에 넘겨주는 rate_limits 를
          statusline.py 가 data/claude_usage.json 에 저장해 둔 것 (Pro/Max 구독에서만 값이 있음)
- Codex : ~/.codex/sessions/**/rollout-*.jsonl 의 마지막 token_count 이벤트에 있는 rate_limits
"""
import calendar
import json
import os
import time

import runtime

CLAUDE_FILE = os.path.join(runtime.DATA_DIR, "claude_usage.json")
CLAUDE_SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
CODEX_SESSIONS = os.path.join(os.path.expanduser("~"), ".codex", "sessions")
RELAY_MARK = "statusline.py"

_codex_cache = {}  # path -> (mtime, result)


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
    """{'ts', 'limits': [...]} 또는 None."""
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
    hit = _codex_cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    result = None
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 300_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        lines = []
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
    _codex_cache[path] = (mtime, result)
    return result


def read_codex():
    for mtime, path in _recent_rollouts():
        r = _codex_from_file(path, mtime)
        if r:
            return r
    return None


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
