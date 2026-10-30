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

# Gemini configuration: environment overrides private machine-local fallback keys.
import json
_LOCAL_KEYS_PATH = WORKING_DIR / "database" / "local_gemini_keys.json"
try:
    _local_keys = json.loads(_LOCAL_KEYS_PATH.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _local_keys = []
DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
DEFAULT_GEMINI_KEYS = list(dict.fromkeys(
    ([DEFAULT_GEMINI_KEY] if DEFAULT_GEMINI_KEY else [])
    + [key for key in _local_keys if isinstance(key, str) and key]
))
DEFAULT_GEMINI_KEY = DEFAULT_GEMINI_KEYS[0] if DEFAULT_GEMINI_KEYS else ""
# Chuỗi Model Gemini ưu tiên tốc độ cao & tương thích cả 2 API Key
CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-pro",
]
DEFAULT_MODEL = CANDIDATE_MODELS[0]

# Server settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8032
