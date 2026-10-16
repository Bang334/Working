"""Process an uploaded repair workbook into the official acceptance template."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

from app.config import (
    OUTPUTS_DIR,
    REPAIR_ACCEPTANCE_SCRIPT,
    REPAIR_ACCEPTANCE_TEMPLATE,
    WORKING_DIR,
)


MAX_REPAIR_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_REPAIR_EXTENSIONS = {".xlsx"}


def _load_generator_module() -> ModuleType:
    if not REPAIR_ACCEPTANCE_SCRIPT.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy script xử lý biên bản sửa chữa: {REPAIR_ACCEPTANCE_SCRIPT}"
        )

    spec = importlib.util.spec_from_file_location(
        "hongming_repair_acceptance_generator", REPAIR_ACCEPTANCE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Không thể nạp bộ xử lý biên bản sửa chữa.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_upload(file_name: str, content: bytes) -> None:
    suffix = Path(file_name or "").suffix.lower()
    if suffix not in ALLOWED_REPAIR_EXTENSIONS:
        raise ValueError("Chỉ chấp nhận file Excel định dạng .xlsx.")
    if not content:
        raise ValueError("File tải lên đang trống.")
    if len(content) > MAX_REPAIR_UPLOAD_BYTES:
        raise ValueError("Dung lượng file vượt quá giới hạn 20 MB.")
    if not content.startswith(b"PK"):
        raise ValueError("File tải lên không phải workbook Excel .xlsx hợp lệ.")


def process_uploaded_repair_file(file_name: str, content: bytes) -> Dict[str, Any]:
    """Generate an acceptance workbook from one uploaded repair workbook."""
    _validate_upload(file_name, content)

    if not REPAIR_ACCEPTANCE_TEMPLATE.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy mẫu biên bản nghiệm thu: {REPAIR_ACCEPTANCE_TEMPLATE}"
        )

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    token = uuid.uuid4().hex[:8]
    output_name = f"Bien_Ban_Nghiem_Thu_Tu_Sua_Chua_{timestamp}_{token}.xlsx"
    output_path = OUTPUTS_DIR / output_name

    with tempfile.TemporaryDirectory(prefix="repair_upload_", dir=str(OUTPUTS_DIR)) as temp_dir:
        source_path = Path(temp_dir) / "bien_ban_sua_chua.xlsx"
        source_path.write_bytes(content)
        shutil.copy2(REPAIR_ACCEPTANCE_TEMPLATE, output_path)

        try:
            generator = _load_generator_module()
            result = generator.generate(source_path, output_path, WORKING_DIR)
        except Exception:
            output_path.unlink(missing_ok=True)
            raise

    saved_path = Path(result.get("saved_path") or output_path)
    if not saved_path.is_file():
        raise RuntimeError("Bộ xử lý không tạo được file biên bản nghiệm thu.")

    assignments = result.get("assignments") or {}
    blank_sheets = result.get("blank_detail_sheets") or []
    note_text = str(result.get("note_text") or "")
    note_line_count = len([line for line in note_text.splitlines() if line.strip()])
    ignored_note_count = max(0, note_line_count - len(assignments))

    return {
        "file_name": saved_path.name,
        "download_url": f"/api/v1/acceptance/download/{saved_path.name}",
        "source_file_name": Path(file_name).name,
        "gemini_model": result.get("gemini_model") or "Gemini",
        "record_count": int(result.get("record_count") or 0),
        "assigned_count": len(assignments),
        "blank_count": len(blank_sheets),
        "ignored_note_count": ignored_note_count,
        "assigned_products": sorted(assignments),
        "blank_products": sorted(blank_sheets),
    }
