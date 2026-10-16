"""Contract controller handling document generation, preview, and download requests."""

import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.services.contract_service import (
    delete_contract_service,
    generate_contract_docx,
    get_all_contracts_list,
    get_contract_detail_by_id_or_code,
    prepare_contract_data,
)
from app.services.preview_service import generate_contract_preview_html

logger = logging.getLogger(__name__)


def generate_contract_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to create contract DOCX document and return status."""
    try:
        result = generate_contract_docx(data)
        return {
            "status": "success",
            "message": "Đã tạo hợp đồng Word (.docx) thành công bảo toàn 100% bố cục!",
            "file_name": result["file_name"],
            "file_path": result.get("file_path", ""),
            "folder_path": result.get("folder_path", ""),
            "download_url": result["download_url"],
            "total_amount": result["total_amount"],
            "company_name": result["company_name"],
            "preview_html": result["preview_html"],
            "contract_data": result["contract_data"]
        }
    except Exception as exc:
        logger.exception("Error generating contract docx: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tài liệu hợp đồng: {str(exc)}",
            "download_url": "",
            "file_name": ""
        }


def render_preview_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to recalculate and refresh live preview HTML without writing files."""
    try:
        sanitized = prepare_contract_data(data)
        preview_html = generate_contract_preview_html(sanitized)
        return {
            "status": "success",
            "preview_html": preview_html,
            "data": sanitized
        }
    except Exception as exc:
        logger.exception("Error rendering preview: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "preview_html": f"<div class='alert alert-danger'>Lỗi cập nhật xem trước: {str(exc)}</div>"
        }


def download_contract_file_controller(file_name: str) -> FileResponse:
    """Controller to stream the generated DOCX file for browser download."""
    clean_name = os.path.basename(file_name)
    candidate_paths = [
        WORKING_DIR / "Ho So Du An" / "Hop Dong" / clean_name,
        WORKING_DIR / "outputs" / "hop_dong" / clean_name,
        OUTPUTS_DIR / clean_name,
    ]

    target_path = None
    for cp in candidate_paths:
        if cp.is_file():
            target_path = cp
            break

    if not target_path:
        # Search via SQLite documents table
        try:
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM documents WHERE file_name = ? ORDER BY id DESC LIMIT 1", (clean_name,))
            row = cursor.fetchone()
            conn.close()
            if row and row["file_path"]:
                p = Path(row["file_path"])
                if p.is_file():
                    target_path = p
        except Exception:
            pass

    if not target_path or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp hợp đồng đã tạo.")

    return FileResponse(
        path=str(target_path),
        filename=clean_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def save_contract_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to save generated contract into SQLite dossier and link with reminders."""
    try:
        from app.services.contract_service import save_contract_to_database
        result = save_contract_to_database(data)
        return result
    except Exception as exc:
        logger.exception("Error saving contract to database: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi lưu hợp đồng vào hệ thống: {str(exc)}"
        }


def list_contracts_controller() -> Dict[str, Any]:
    """Controller to retrieve all created contracts across SQLite and physical project folders."""
    try:
        items = get_all_contracts_list()
        return {
            "status": "success",
            "total": len(items),
            "data": items
        }
    except Exception as exc:
        logger.exception("Error fetching contracts list: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tải danh sách hợp đồng: {str(exc)}",
            "total": 0,
            "data": []
        }


def get_contract_detail_controller(identifier: str) -> Dict[str, Any]:
    """Controller to retrieve full contract data for populating into web editor form."""
    try:
        detail = get_contract_detail_by_id_or_code(identifier)
        return {
            "status": "success",
            "data": detail
        }
    except Exception as exc:
        logger.exception("Error fetching contract detail for %s: %s", identifier, exc)
        return {
            "status": "error",
            "message": str(exc),
            "data": None
        }


def delete_contract_controller(identifier: str) -> Dict[str, Any]:
    """Controller to remove a contract record from the system."""
    try:
        return delete_contract_service(identifier)
    except Exception as exc:
        logger.exception("Error deleting contract %s: %s", identifier, exc)
        return {
            "status": "error",
            "message": f"Lỗi xóa hợp đồng: {str(exc)}"
        }

