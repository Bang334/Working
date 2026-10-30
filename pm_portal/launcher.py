"""Quick desktop launcher for Hong Ming PM Portal."""
import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

PORTAL_DIR = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8032/quotations"
LOG_PATH = PORTAL_DIR / ".tmp" / "portal_startup.log"


def is_port_open(host="127.0.0.1", port=8032) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def is_server_ready():
    try:
        with urlopen(URL, timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def start_server():
    if is_server_ready():
        return
    process = None
    if not is_port_open():
        # pythonw has no stdout/stderr; use python with explicit file streams.
        python_exe = Path(sys.executable)
        if python_exe.name.lower() == "pythonw.exe":
            python_exe = python_exe.with_name("python.exe")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PM_PORTAL_RELOAD="0")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(
                [str(python_exe), "-u", str(PORTAL_DIR / "run.py")],
                cwd=str(PORTAL_DIR), env=env, creationflags=flags,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            )
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if is_server_ready():
            return
        if process is not None and process.poll() is not None:
            raise RuntimeError("Máy chủ đã dừng trong khi khởi động.")
        time.sleep(0.5)
    raise RuntimeError("Ứng dụng chưa sẵn sàng sau 45 giây.")


def main():
    try:
        start_server()
    except Exception as exc:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log:
            log.write(f"\nLauncher: {exc}\n")
        if os.name == "nt":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, f"Không thể mở Hong Ming PM Portal.\n{exc}\n\nNhật ký: {LOG_PATH}",
                "Hong Ming PM Portal", 0x10,
            )
        return 1
    webbrowser.open(URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
