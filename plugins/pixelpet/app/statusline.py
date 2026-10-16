"""Claude Code 상태줄(statusLine) 중계.

Claude Code 가 상태줄 명령에 넘겨주는 JSON 에서 rate_limits(5시간·주간 사용량)만
data/claude_usage.json 에 저장하고, 원래 쓰던 상태줄 명령이 있으면 그대로 실행해 출력을 돌려준다.
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runtime  # noqa: E402

USAGE_FILE = os.path.join(runtime.DATA_DIR, "claude_usage.json")
PREV_FILE = os.path.join(runtime.DATA_DIR, "statusline_prev.json")


def save_usage(raw):
    d = json.loads(raw.decode("utf-8", "replace") or "{}")
    rl = d.get("rate_limits")
    if not isinstance(rl, dict) or not rl:
        return
    os.makedirs(runtime.DATA_DIR, exist_ok=True)
    tmp = f"{USAGE_FILE}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "rate_limits": rl}, f)
    os.replace(tmp, USAGE_FILE)


def git_bash():
    """Claude Code 처럼 Git Bash 로 실행 (WSL 의 System32\\bash.exe 는 피한다)."""
    p = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if p and os.path.exists(p):
        return p
    git = shutil.which("git")
    if git:
        for rel in (r"..\bin\bash.exe", r"..\..\bin\bash.exe"):
            cand = os.path.normpath(os.path.join(os.path.dirname(git), rel))
            if os.path.exists(cand):
                return cand
    return None


def run_prev(raw):
    try:
        with open(PREV_FILE, encoding="utf-8") as f:
            cmd = ((json.load(f) or {}).get("statusLine") or {}).get("command")
    except (OSError, ValueError, AttributeError):
        return
    if not cmd:
        return
    bash = git_bash()
    r = subprocess.run([bash, "-c", cmd] if bash else cmd, shell=not bash, input=raw,
                       capture_output=True, timeout=10, creationflags=0x08000000)  # CREATE_NO_WINDOW
    sys.stdout.buffer.write(r.stdout)
    sys.stdout.flush()


def main():
    raw = sys.stdin.buffer.read()
    try:
        save_usage(raw)
    except Exception:
        pass
    try:
        run_prev(raw)
    except Exception:
        pass


if __name__ == "__main__":
    main()
