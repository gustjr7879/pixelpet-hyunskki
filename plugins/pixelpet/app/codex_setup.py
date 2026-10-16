"""Codex 훅 연결/해제.

    python codex_setup.py          ~/.codex/hooks.json 에 PixelPet 훅 추가
    python codex_setup.py --remove PixelPet 훅만 제거 (다른 훅은 그대로)

Codex 는 새 훅을 사용자가 승인(trust)해야 실행한다 → 설정 후 `codex` 를 열어 승인.
"""
import ctypes
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runtime  # noqa: E402

CODEX_HOOKS = os.path.join(os.path.expanduser("~"), ".codex", "hooks.json")
EVENTS = ["UserPromptSubmit", "Stop", "PermissionRequest"]  # PermissionRequest: 승인 요청 알림
MARK = "pet_hook.py"


def no_space_path(path):
    """공백이 있으면 8.3 짧은 경로로 (Codex 가 어떤 셸로 실행해도 안전하도록)."""
    if " " not in path:
        return path.replace("\\", "/")
    buf = ctypes.create_unicode_buffer(1024)
    if ctypes.windll.kernel32.GetShortPathNameW(path, buf, 1024) and " " not in buf.value:
        return buf.value.replace("\\", "/")
    return '"%s"' % path.replace("\\", "/")


def pythonw():
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else sys.executable


def load():
    try:
        with open(CODEX_HOOKS, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def strip_ours(hooks):
    for ev in list(hooks):
        groups = []
        for g in hooks[ev]:
            hs = [h for h in g.get("hooks", []) if MARK not in h.get("command", "")]
            if hs:
                groups.append(dict(g, hooks=hs))
        if groups:
            hooks[ev] = groups
        else:
            del hooks[ev]
    return hooks


def save(data):
    if os.path.exists(CODEX_HOOKS):
        shutil.copy2(CODEX_HOOKS, f"{CODEX_HOOKS}.bak-pixelpet-{time.strftime('%Y%m%d%H%M%S')}")
    os.makedirs(os.path.dirname(CODEX_HOOKS), exist_ok=True)
    with open(CODEX_HOOKS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    remove = "--remove" in sys.argv
    data = load()
    hooks = strip_ours(data.get("hooks", {}))
    if not remove:
        if runtime.needs_sync():
            runtime.sync()
        cmd = f"{no_space_path(pythonw())} {no_space_path(os.path.join(runtime.RUNTIME_APP, 'pet_hook.py'))} codex"
        for ev in EVENTS:
            hooks.setdefault(ev, []).append({"hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    save(data)
    if remove:
        print("PixelPet: Codex 훅을 제거했어요. / Removed the Codex hooks.")
    else:
        print("PixelPet: Codex 훅을 추가했어요 →", CODEX_HOOKS)
        print("  다음 단계: 터미널에서 `codex` 를 한 번 열고, 훅 검토 화면에서 PixelPet 훅을 승인하세요.")
        print("  Next: open `codex` once in a terminal and approve (trust) the PixelPet hooks.")


if __name__ == "__main__":
    main()
