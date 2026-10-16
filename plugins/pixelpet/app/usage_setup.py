"""Claude 사용량 표시 연결/해제.

    python usage_setup.py          ~/.claude/settings.json 의 statusLine 을 PixelPet 중계 스크립트로 감싼다
    python usage_setup.py --remove 원래 statusLine 으로 되돌린다

원래 상태줄 명령이 있었다면 중계 스크립트가 그대로 실행해 주므로 화면은 바뀌지 않는다.
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runtime  # noqa: E402
from codex_setup import no_space_path  # noqa: E402

SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
PREV_FILE = os.path.join(runtime.DATA_DIR, "statusline_prev.json")
MARK = "statusline.py"


def load():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save(data):
    if os.path.exists(SETTINGS):
        shutil.copy2(SETTINGS, f"{SETTINGS}.bak-pixelpet-{time.strftime('%Y%m%d%H%M%S')}")
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def is_ours(sl):
    return isinstance(sl, dict) and MARK in (sl.get("command") or "")


def remove(data):
    if not is_ours(data.get("statusLine")):
        print("PixelPet: 사용량 연결이 설정되어 있지 않아요. / Usage relay is not installed.")
        return
    try:
        with open(PREV_FILE, encoding="utf-8") as f:
            prev = json.load(f).get("statusLine")
    except (OSError, ValueError):
        prev = None
    if prev:
        data["statusLine"] = prev
    else:
        data.pop("statusLine", None)
    save(data)
    for p in (PREV_FILE, os.path.join(runtime.DATA_DIR, "claude_usage.json")):
        try:
            os.remove(p)
        except OSError:
            pass
    print("PixelPet: 상태줄을 원래대로 되돌렸어요. / Restored the original status line.")


def install(data):
    if runtime.needs_sync():
        runtime.sync()
    cur = data.get("statusLine")
    if not is_ours(cur):   # 원래 상태줄 기억 (없으면 null)
        os.makedirs(runtime.DATA_DIR, exist_ok=True)
        with open(PREV_FILE, "w", encoding="utf-8") as f:
            json.dump({"statusLine": cur}, f, ensure_ascii=False, indent=2)
    new = dict(cur) if isinstance(cur, dict) else {}
    new.update(type="command", command=f"{no_space_path(sys.executable)} "
               f"{no_space_path(os.path.join(runtime.RUNTIME_APP, 'statusline.py'))}")
    data["statusLine"] = new
    save(data)
    print("PixelPet: Claude 사용량 연결 완료 →", SETTINGS)
    if isinstance(cur, dict) and cur.get("command") and not is_ours(cur):
        print("  기존 상태줄은 그대로 표시돼요. / Your existing status line is kept.")
    print("  Claude에게 메시지를 한 번 보내면 펫 알림함의 [사용량] 탭에 표시돼요 (Pro/Max 구독).")
    print("  Send Claude a message once and it shows up in the pet's [사용량] tab (Pro/Max plans).")


def main():
    data = load()
    remove(data) if "--remove" in sys.argv else install(data)


if __name__ == "__main__":
    main()
