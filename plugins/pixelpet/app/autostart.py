"""Windows 시작프로그램 바로가기 관리."""
import os
import subprocess
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
LNK_PATH = os.path.join(STARTUP_DIR, "PixelPet.lnk")


def pythonw_exe():
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else sys.executable


def is_enabled():
    return os.path.exists(LNK_PATH)


def enable(pet_path=None):
    pet_path = pet_path or os.path.join(APP_DIR, "pet.py")
    env = dict(os.environ,
               PP_LNK=LNK_PATH,
               PP_TARGET=pythonw_exe(),
               PP_ARGS=f'"{pet_path}"',
               PP_DIR=os.path.dirname(pet_path))
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:PP_LNK);"
          "$s.TargetPath=$env:PP_TARGET;$s.Arguments=$env:PP_ARGS;"
          "$s.WorkingDirectory=$env:PP_DIR;$s.Description='PixelPet';$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   env=env, check=True, creationflags=0x08000000)


def disable():
    try:
        os.remove(LNK_PATH)
    except FileNotFoundError:
        pass
