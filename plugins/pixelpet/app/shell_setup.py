"""PowerShell 연결/해제 — 일반 명령·스크립트 실행도 펫에 표시.

    python shell_setup.py          PowerShell 프로필에 PixelPet 연결 줄 추가
    python shell_setup.py --remove 그 줄만 제거 (프로필의 다른 내용은 그대로)

Windows PowerShell 5.1 과 (설치돼 있으면) PowerShell 7 둘 다. 새로 여는 터미널부터 적용된다.
"""
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runtime  # noqa: E402

BEGIN, END = "# >>> PixelPet >>>", "# <<< PixelPet <<<"
# 경로는 환경변수로 → 사용자 이름이 한글이어도 프로필 줄은 ASCII (5.1 은 BOM 없는 파일을 ANSI 로 읽음)
BLOCK = [
    BEGIN,
    "# Shows long-running commands in PixelPet. Remove with /pixelpet:shell --remove",
    '$__ppShell = Join-Path $env:LOCALAPPDATA "PixelPet\\app\\pixelpet_shell.ps1"',
    "if (Test-Path $__ppShell) { . $__ppShell }",
    "Remove-Variable __ppShell -ErrorAction SilentlyContinue",
    END,
]


def shells():
    """(이름, 실행파일) — 설치된 것만."""
    out = []
    for name, exe in (("Windows PowerShell", "powershell"), ("PowerShell 7", "pwsh")):
        path = shutil.which(exe)
        if path:
            out.append((name, path))
    return out


def ps(exe, command):
    r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", command],
                       capture_output=True, text=True, timeout=30, creationflags=0x08000000)
    return r.stdout.strip()


def read_profile(path):
    """(줄 목록, 인코딩, BOM 바이트)"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return [], "utf-8", b""
    for bom, enc in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"), (b"\xef\xbb\xbf", "utf-8")):
        if raw.startswith(bom):
            return raw[len(bom):].decode(enc).splitlines(), enc, bom
    try:
        return raw.decode("utf-8").splitlines(), "utf-8", b""
    except UnicodeDecodeError:
        return raw.decode("mbcs").splitlines(), "mbcs", b""   # 5.1 이 ANSI 로 저장한 파일


def strip_block(lines):
    out, skip = [], False
    for line in lines:
        if line.strip() == BEGIN:
            skip = True
        elif line.strip() == END and skip:
            skip = False
        elif not skip:
            out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return out


def write_profile(path, lines, enc, bom):
    if os.path.exists(path):
        shutil.copy2(path, f"{path}.bak-pixelpet-{time.strftime('%Y%m%d%H%M%S')}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(bom + ("\r\n".join(lines) + "\r\n").encode(enc))


def main():
    remove = "--remove" in sys.argv
    if not remove and runtime.needs_sync():
        runtime.sync()
    found = shells()
    if not found:
        print("PixelPet: PowerShell 을 찾지 못했어요. / PowerShell not found.")
        return
    for name, exe in found:
        try:
            path = ps(exe, "$PROFILE.CurrentUserCurrentHost")
        except Exception as ex:
            print(f"PixelPet: {name} 프로필 경로를 못 읽었어요 ({ex})")
            continue
        if not path:
            continue
        lines, enc, bom = read_profile(path)
        had = BEGIN in (l.strip() for l in lines)
        lines = strip_block(lines)
        if remove:
            if had:
                write_profile(path, lines, enc, bom)
                print(f"PixelPet: {name} 연결을 제거했어요 → {path}")
            elif "--quiet" not in sys.argv:
                print(f"PixelPet: {name} 에는 연결돼 있지 않아요.")
            continue
        write_profile(path, (lines + [""] if lines else []) + BLOCK, enc, bom)
        print(f"PixelPet: {name} 에 연결했어요 → {path}")
        # Process 범위(이 스크립트를 띄운 셸의 Bypass 등)는 빼고 본 실제 정책. 전부 미지정이면 기본값
        default = "Restricted" if name == "Windows PowerShell" else "RemoteSigned"
        policy = ps(exe, "$p = Get-ExecutionPolicy -List | Where-Object { $_.Scope -ne 'Process' -and "
                         "$_.ExecutionPolicy -ne 'Undefined' } | Select-Object -First 1; "
                         f"if ($p) {{ [string]$p.ExecutionPolicy }} else {{ '{default}' }}")
        if policy in ("Restricted", "AllSigned"):
            print(f"  ! 실행 정책이 {policy} 라 프로필이 실행되지 않아요. PowerShell 에서 한 번 실행하세요:")
            print("    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned")
    if not remove:
        print("  새로 여는 PowerShell 창부터 적용돼요. 10초 넘게 걸리는 명령은 펫에 '작업중'으로 보이고,")
        print("  끝나면 알림이 와요 (Ctrl+C 로 멈춘 건 알리지 않음).")
        print("  Applies to new PowerShell windows: commands running 10s+ show on the pet and notify when done.")


if __name__ == "__main__":
    main()
