"""Claude Code / Codex 훅에서 호출되는 스크립트.

    python pet_hook.py start           SessionStart: 앱 파일 동기화 + 펫이 꺼져 있으면 실행
    python pet_hook.py claude|codex    stdin 의 훅 JSON 을 펫 앱(127.0.0.1:47321)에 전달

어떤 경우에도 에이전트 작업을 막지 않도록 조용히 실패하고 exit 0 한다.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runtime  # noqa: E402

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 시스템 프록시 우회


def post(payload, timeout=1.5):
    req = urllib.request.Request(
        f"http://127.0.0.1:{runtime.PORT}/event",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", runtime.AUTH_HEADER: "1"},
        method="POST",
    )
    _opener.open(req, timeout=timeout).read()


def is_running():
    try:
        _opener.open(f"http://127.0.0.1:{runtime.PORT}/", timeout=0.5).read()
        return True
    except Exception:
        return False


def pythonw():
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else sys.executable


def launch():
    pet = os.path.join(runtime.RUNTIME_APP, "pet.py")
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    for extra in (0x01000000, 0):    # CREATE_BREAKAWAY_FROM_JOB — 훅이 끝나도 펫이 살아있도록
        try:
            subprocess.Popen([pythonw(), pet], cwd=runtime.RUNTIME_APP, creationflags=flags | extra,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            continue


def start():
    updated = False
    if runtime.needs_sync():
        if is_running():                       # 새 버전이 오면 기존 펫을 내리고 다시 띄운다
            try:
                post({"_cmd": "quit"})
            except Exception:
                pass
            for _ in range(20):
                if not is_running():
                    break
                time.sleep(0.1)
        runtime.sync()
        updated = True
    marker = os.path.join(runtime.DATA_DIR, "autostart_initialized")
    if not os.path.exists(marker):             # 첫 실행 때만 시작프로그램 등록 (이후엔 메뉴에서 끄고 켬)
        try:
            import autostart
            autostart.enable(os.path.join(runtime.RUNTIME_APP, "pet.py"))
        except Exception:
            pass
        os.makedirs(runtime.DATA_DIR, exist_ok=True)
        open(marker, "w").close()
    if updated or not is_running():
        launch()


def last_text_from_transcript(path):
    """Claude transcript(JSONL) 끝부분에서 마지막 assistant 텍스트를 찾는다."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        content = (d.get("message") or {}).get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            text = "\n".join(t for t in texts if t.strip())
            if text:
                return text
    return ""


def forward(source):
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    event = data.get("hook_event_name") or ""
    msg = data.get("last_assistant_message") or ""
    if source == "claude" and event == "Stop" and not msg and data.get("transcript_path"):
        msg = last_text_from_transcript(data["transcript_path"])
    if event == "Notification":
        msg = data.get("message") or msg
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    if event in ("PreToolUse", "PermissionRequest"):
        qs = tool_input.get("questions") or []
        if qs and isinstance(qs[0], dict):
            msg = qs[0].get("question") or msg                      # Claude 선택지 질문
        msg = msg or tool_input.get("command") or tool_input.get("description") or ""
        if isinstance(msg, list):
            msg = " ".join(map(str, msg))

    # Claude 가 띄운 codex 라면 Claude 의 환경변수를 물려받는다 (가장 확실한 연결 고리)
    claude_sid = os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_COMPANION_SESSION_ID") or ""
    env_pid = os.environ.get("CLAUDE_PID", "")
    claude_pid = int(env_pid) if env_pid.isdigit() else None
    codex_pid = None
    try:
        import proctree
        for pid, name in proctree.ancestors(os.getpid())[1:]:
            if name == "claude.exe":
                claude_pid = claude_pid or pid
                break
            if name == "codex.exe":
                codex_pid = pid  # 계속 올라가며 갱신 → claude 바로 아래(최상위) codex 가 남는다
    except Exception:
        pass

    post({
        "source": source,
        "event": event,
        "session_id": data.get("session_id") or "",
        "turn_id": data.get("turn_id") or "",
        "cwd": data.get("cwd") or os.getcwd(),
        "transcript_path": data.get("transcript_path") or "",
        "notification_type": data.get("notification_type") or "",
        "tool_name": data.get("tool_name") or "",
        "message": msg[:4000],
        "claude_pid": claude_pid,
        "claude_session_id": claude_sid if source == "codex" else "",
        "codex_pid": codex_pid,
        "ts": time.time(),
    })


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "claude"
    if mode == "start":
        start()
    else:
        forward(mode)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
