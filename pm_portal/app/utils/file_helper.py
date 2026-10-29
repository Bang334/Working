"""File helper utilities."""

import re
import unicodedata
from datetime import datetime
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """Sanitize string for safe cross-platform file naming."""
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r"[^\w\s\.-]", "", name)
    name = re.sub(r"[\s]+", "_", name.strip())
    return name[:100] or "contract_output"


def generate_contract_filename(company_name: str, contract_no: str = "") -> str:
    """Generate standardized filename for contracts."""
    safe_company = sanitize_filename(company_name)
    safe_no = sanitize_filename(contract_no) if contract_no else "NEW"
    if contract_no and safe_no != "NEW":
        return f"Hop_Dong_{safe_company}_{safe_no}.docx"
    date_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Hop_Dong_{safe_company}_{safe_no}_{date_stamp}.docx"


def document_filename(kind: str, customer: str = "", reference: str = "",
                      extension: str = "xlsx", stamp: str = "") -> str:
    """Readable, safe name for newly generated documents without changing templates."""
    def clean(value, limit):
        value = unicodedata.normalize("NFC", str(value or "")).strip()
        value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", value)
        value = re.sub(r"\s+", "_", value)
        return value.strip(" ._")[:limit].rstrip(" ._")

    parts = [clean(kind, 35), clean(customer, 45), clean(reference, 45)]
    parts = [part for part in parts if part]
    parts.append(stamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    ext = re.sub(r"[^a-zA-Z0-9]", "", extension)
    return "_".join(parts) + "." + ext
