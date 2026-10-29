"""Application configuration settings."""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
WORKING_DIR = BASE_DIR.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
TEMPLATE_DOCX = WORKING_DIR / "Bieu Mau" / "Mau_Goc_Hop_Dong_Mua_Ban.docx"
REPAIR_ACCEPTANCE_TEMPLATE = WORKING_DIR / "Bieu Mau" / "Mau_Goc_Nghiem_Thu_Sua_Chua.xlsx"
REPAIR_ACCEPTANCE_SCRIPT = (
    WORKING_DIR
    / ".agents"
    / "skills"
    / "hongming-pm-hub"
    / "scripts"
    / "generate_repair_acceptance_from_source.py"
)

# Ensure output directory exists
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Gemini API configuration
DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
DEFAULT_GEMINI_KEYS = [DEFAULT_GEMINI_KEY] if DEFAULT_GEMINI_KEY else []

# Chuỗi Model Gemini ưu tiên tốc độ cao & ổn định (ưu tiên 3.5-flash-lite, 3.1-flash-lite)
CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]
DEFAULT_MODEL = CANDIDATE_MODELS[0]

# Server settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8032
