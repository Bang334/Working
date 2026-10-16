"""Server runner script for Hong Ming PM Portal."""

import os
import sys

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ["PYTHONIOENCODING"] = "utf-8"

# Add current directory to Python module search path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import uvicorn
from app.config import SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    print("=" * 65)
    print("   HONG MING GLOBAL PM PORTAL - CONTRACT & DOCUMENT HUB")
    print(f"   Python Version : {sys.version.split()[0]}")
    print(f"   Ứng dụng Web   : http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"   Tạo Hợp Đồng   : http://{SERVER_HOST}:{SERVER_PORT}/contracts")
    print(f"   Nghiệm Thu     : http://{SERVER_HOST}:{SERVER_PORT}/acceptance")
    print(f"   Tài Liệu API   : http://{SERVER_HOST}:{SERVER_PORT}/docs")
    print("=" * 65)
    
    uvicorn.run(
        "app.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True
    )
