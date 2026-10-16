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
    date_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = sanitize_filename(company_name)
    safe_no = sanitize_filename(contract_no) if contract_no else "NEW"
    return f"Hop_Dong_{safe_company}_{safe_no}_{date_stamp}.docx"
