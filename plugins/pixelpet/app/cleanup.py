"""PixelPet 정리: 펫 종료 + Codex 훅 제거 + 시작프로그램 해제 + %LOCALAPPDATA%\\PixelPet 삭제.

플러그인 자체(Claude 훅)는 `/plugin uninstall pixelpet@pixelpet-hyunskki` 로 제거한다.
"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autostart  # noqa: E402
import pet_hook  # noqa: E402
import runtime  # noqa: E402


def main():
    if pet_hook.is_running():
        try:
            pet_hook.post({"_cmd": "quit"})
        except Exception:
            pass
        time.sleep(1)
    subprocess.run([sys.executable, os.path.join(runtime.SRC_APP, "codex_setup.py"), "--remove"])
    autostart.disable()
    shutil.rmtree(runtime.HOME_DIR, ignore_errors=True)
    print("PixelPet: 펫 종료, 시작프로그램 해제, 실행 파일 삭제 완료. / Stopped, removed autostart and runtime files.")
    print("  플러그인 제거 / To remove the plugin: /plugin uninstall pixelpet@pixelpet-hyunskki")


if __name__ == "__main__":
    main()
