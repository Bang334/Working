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


def process_uploaded_repair_file(
    file_name: str,
    content: bytes,
    contract_code: Optional[str] = None
) -> Dict[str, Any]:
    """Generate an acceptance workbook from one uploaded repair workbook, checking contract code."""
    import re
    from app.services.contract_service import find_matching_contract

    _validate_upload(file_name, content)

    if not REPAIR_ACCEPTANCE_TEMPLATE.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy mẫu biên bản nghiệm thu: {REPAIR_ACCEPTANCE_TEMPLATE}"
        )

    target_dir = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    clean_stem = "".join(c for c in Path(file_name).stem if c.isalnum() or c in (" ", "-", "_", "(", ")", ",")).strip()
    clean_stem = clean_stem[:50] if clean_stem else "Tu_Sua_Chua"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Kiểm tra đối chiếu mã hợp đồng nếu người dùng gửi lên
    matched_contract = None
    if contract_code and str(contract_code).strip():
        matched_contract = find_matching_contract(str(contract_code).strip())

    with tempfile.TemporaryDirectory(prefix="repair_upload_", dir=str(target_dir)) as temp_dir:
        source_path = Path(temp_dir) / "bien_ban_sua_chua.xlsx"
        source_path.write_bytes(content)
        generator = _load_generator_module()

        # 2. Nếu người dùng chưa chọn HĐ, thử đọc từ file nguồn xem có mã HĐ khớp hệ thống không
        if not matched_contract:
            try:
                if hasattr(generator, "extract_source_data"):
                    src_meta = generator.extract_source_data(source_path)
                    src_so_hd = (src_meta.get("so_hop_dong") or "").strip()
                    if src_so_hd:
                        matched_contract = find_matching_contract(src_so_hd)
            except Exception:
                pass

        # 3. Phân nhánh: Có liên kết HĐ hoặc độc lập
        if matched_contract:
            final_contract_code = matched_contract["contract_code"]
            final_contract_id = matched_contract["id"]
            cust_name = matched_contract.get("customer_name_vi", "")
            clean_c_code = re.sub(r'[\\/*?:"<>|]', '_', final_contract_code).strip()
            output_name = f"Bien_Ban_Nghiem_Thu_{clean_c_code}_{clean_stem}_{timestamp}.xlsx"
        else:
            final_contract_code = ""
            final_contract_id = None
            cust_name = ""
            output_name = f"Bien_Ban_Nghiem_Thu_{clean_stem}_{timestamp}.xlsx"

        output_path = target_dir / output_name
        shutil.copy2(REPAIR_ACCEPTANCE_TEMPLATE, output_path)

        try:
            try:
                result = generator.generate(
                    source_path,
                    output_path,
                    WORKING_DIR,
                    override_contract_code=final_contract_code or None,
                    override_customer_name=cust_name or None
                )
            except TypeError:
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

    # Ghi nhận tài liệu vào hệ thống (documents table)
    try:
        from app.database import index_single_document
        doc_desc = (
            f"Biên bản nghiệm thu thiết bị [HĐ: {final_contract_code} - {cust_name}]: {Path(file_name).name}"
            if final_contract_code
            else f"Biên bản nghiệm thu thiết bị độc lập: {Path(file_name).name}"
        )
        doc_display_name = (
            f"Biên Bản Nghiệm Thu ({final_contract_code}) - {Path(file_name).name}"
            if final_contract_code
            else f"Biên Bản Nghiệm Thu - {Path(file_name).name}"
        )
        index_single_document(
            contract_code=final_contract_code,
            contract_id=final_contract_id,
            doc_type="NGHIEM_THU",
            doc_name=doc_display_name,
            file_name=saved_path.name,
            file_path=str(saved_path),
            file_size=saved_path.stat().st_size,
            file_format="xlsx",
            description=doc_desc
        )
    except Exception:
        pass

    return {
        "file_name": saved_path.name,
        "file_path": str(saved_path),
        "download_url": f"/api/v1/acceptance/download/{saved_path.name}",
        "source_file_name": Path(file_name).name,
        "gemini_model": result.get("gemini_model") or "Gemini",
        "record_count": int(result.get("record_count") or 0),
        "assigned_count": len(assignments),
        "blank_count": len(blank_sheets),
        "ignored_note_count": ignored_note_count,
        "assigned_products": sorted(assignments),
        "blank_products": sorted(blank_sheets),
        "contract_code": final_contract_code,
        "contract_id": final_contract_id,
        "customer_name": cust_name,
        "is_linked_contract": bool(matched_contract),
    }

