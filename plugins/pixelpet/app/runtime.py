"""경로/설정 공용 모듈.

플러그인은 버전마다 다른 캐시 폴더에 설치되므로, 실제로 실행되는 앱은
%LOCALAPPDATA%\\PixelPet 에 복사해 두고 쓴다 (Codex 훅·시작프로그램이 고정 경로를 가리키도록).
"""
import hashlib
import os
import shutil

VERSION = "0.2.3"
PORT = int(os.environ.get("PIXELPET_PORT", "47321"))
DEBUG = os.environ.get("PIXELPET_DEBUG") == "1"
AUTH_HEADER = "X-PixelPet"   # 브라우저 등 다른 출처의 위조 요청 차단용 (커스텀 헤더는 CORS 사전요청이 필요)

HOME_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "PixelPet")
RUNTIME_APP = os.path.join(HOME_DIR, "app")
RUNTIME_ASSETS = os.path.join(HOME_DIR, "assets")
DATA_DIR = os.path.join(HOME_DIR, "data")

SRC_APP = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.dirname(SRC_APP)


def _signature(folder):
    h = hashlib.sha1()
    for name in sorted(os.listdir(folder)):
        p = os.path.join(folder, name)
        if os.path.isfile(p) and name.endswith((".py", ".ps1")):
            with open(p, "rb") as f:
                h.update(name.encode() + f.read())
    return h.hexdigest()


def needs_sync():
    """플러그인 쪽 앱 파일이 실행용 복사본과 다르면 True."""
    if os.path.normcase(SRC_APP) == os.path.normcase(RUNTIME_APP):
        return False
    if not os.path.isdir(RUNTIME_APP):
        return True
    return _signature(SRC_APP) != _signature(RUNTIME_APP)


def sync():
    """플러그인 → %LOCALAPPDATA%\\PixelPet 로 앱/폰트 복사."""
    os.makedirs(RUNTIME_APP, exist_ok=True)
    os.makedirs(RUNTIME_ASSETS, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    for name in os.listdir(SRC_APP):
        src = os.path.join(SRC_APP, name)
        if os.path.isfile(src) and name.endswith((".py", ".ps1")):
            shutil.copy2(src, os.path.join(RUNTIME_APP, name))
    src_assets = os.path.join(SRC_ROOT, "assets")
    if os.path.isdir(src_assets):
        for name in os.listdir(src_assets):
            src, dst = os.path.join(src_assets, name), os.path.join(RUNTIME_ASSETS, name)
            if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
                shutil.copy2(src, dst)
