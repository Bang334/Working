"""Quotation controller handling document generation, AI parsing, saving with versioning, and download."""

import base64
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.models.quotation_models import QuotationAIParseRequest
from app.services.quotation_ai_service import parse_quotation_text
from app.services.quotation_excel_service import generate_quotation_excel
from app.services.quotation_service import (
    get_all_active_quotations_service,
    get_quotation_detail_service,
    get_quotation_history_service,
    save_quotation_service,
)
from app.services.quotation_word_service import generate_quotation_word

logger = logging.getLogger(__name__)


def generate_quotation_word_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to generate bilingual Word (.docx) quotation document."""
    try:
        result = generate_quotation_word(data)
        return {
            "status": "success",
            "message": result.get("message", "Đã tạo báo giá Word (.docx) thành công!"),
            "file_name": result["file_name"],
            "file_path": result.get("file_path", ""),
            "download_url": result["download_url"],
            "total_amount": result.get("total_amount", 0),
            "total_amount_formatted": result.get("total_amount_formatted", ""),
            "customer_name": result.get("customer_name", ""),
            "quotation_no": result.get("quotation_no", "")
        }
    except Exception as exc:
        logger.exception("Error generating quotation word: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tệp Word báo giá: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def generate_quotation_excel_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to generate bilingual Excel (.xlsx) quotation workbook."""
    try:
        result = generate_quotation_excel(data)
        return {
            "status": "success",
            "message": result.get("message", "Đã tạo báo giá Excel (.xlsx) thành công!"),
            "file_name": result["file_name"],
            "file_path": result.get("file_path", ""),
            "download_url": result["download_url"],
            "total_amount": result.get("total_amount", 0),
            "total_amount_formatted": result.get("total_amount_formatted", ""),
            "customer_name": result.get("customer_name", ""),
            "quotation_no": result.get("quotation_no", "")
        }
    except Exception as exc:
        logger.exception("Error generating quotation excel: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tệp Excel báo giá: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def save_quotation_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to save quotation into database, replacing old version while preserving backup history."""
    try:
        result = save_quotation_service(data)
        return result
    except Exception as exc:
        logger.exception("Error saving quotation: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi lưu trữ báo giá: {str(exc)}"
        }


def get_quotation_history_controller(quotation_no: str) -> Dict[str, Any]:
    """Controller to retrieve version history for a specific quotation number."""
    try:
        history = get_quotation_history_service(quotation_no)
        return {
            "status": "success",
            "quotation_no": quotation_no,
            "total_versions": len(history),
            "history": history
        }
    except Exception as exc:
        logger.exception("Error retrieving quotation history for %s: %s", quotation_no, exc)
        return {
            "status": "error",
            "message": f"Lỗi tải lịch sử phiên bản báo giá: {str(exc)}",
            "history": []
        }


def get_quotation_detail_controller(identifier: str) -> Dict[str, Any]:
    """Controller to retrieve complete quotation details (including items) to load into form."""
    try:
        detail = get_quotation_detail_service(identifier)
        if not detail:
            return {
                "status": "error",
                "message": f"Không tìm thấy báo giá với định danh: {identifier}",
                "data": None
            }
        return {
            "status": "success",
            "data": detail
        }
    except Exception as exc:
        logger.exception("Error retrieving quotation detail %s: %s", identifier, exc)
        return {
            "status": "error",
            "message": f"Lỗi đọc chi tiết báo giá: {str(exc)}",
            "data": None
        }


def parse_raw_quotation_text_controller(request: QuotationAIParseRequest) -> Dict[str, Any]:
    """Parse unstructured user quotation request or survey sheet using Gemini AI."""
    try:
        raw_text = (request.raw_text or "").strip()
        file_bytes = None
        if request.file_base64:
            b64_str = request.file_base64
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            file_bytes = base64.b64decode(b64_str)

        if not raw_text and not file_bytes:
            raise ValueError("Vui lòng nhập văn bản yêu cầu báo giá hoặc đính kèm tệp để AI phân tích.")

        parsed_data = parse_quotation_text(
            raw_input_text=raw_text,
            file_bytes=file_bytes,
            file_mime_type=request.file_mime,
            file_name=request.file_name,
            preferred_model=request.model_name
        )

        executed_model = parsed_data.pop("_executed_model", request.model_name or "Gemini")
        return {
            "status": "success",
            "message": f"AI ({executed_model}) đã phân tích và bóc tách thành công {len(parsed_data.get('items', []))} hạng mục thiết bị!",
            "executed_model": executed_model,
            "data": parsed_data
        }
    except Exception as exc:
        logger.exception("Quotation AI parse failed: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi phân tích AI báo giá: {str(exc)}",
            "data": None
        }


def download_quotation_file_controller(file_name: str) -> FileResponse:
    """Controller to download generated quotation file (Word or Excel), checking both active and backup dirs."""
    clean_name = os.path.basename(file_name)
    bao_gia_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
    history_dir = bao_gia_dir / "Lich_Su"

    candidate_paths = [
        bao_gia_dir / clean_name,
        history_dir / clean_name,
        OUTPUTS_DIR / clean_name,
    ]

    target_path = None
    for cp in candidate_paths:
        if cp.is_file():
            target_path = cp
            break

    if not target_path:
        # Search via SQLite quotations table or documents table
        try:
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT docx_file_path, xlsx_file_path FROM quotations WHERE docx_file_name = ? OR xlsx_file_name = ? ORDER BY id DESC LIMIT 1",
                (clean_name, clean_name)
            )
            row = cursor.fetchone()
            if row:
                for col in ("docx_file_path", "xlsx_file_path"):
                    if row[col]:
                        p = Path(row[col])
                        if p.is_file():
                            target_path = p
                            break

            if not target_path:
                cursor.execute(
                    "SELECT file_path FROM documents WHERE file_name = ? AND doc_type = 'BAO_GIA' ORDER BY id DESC LIMIT 1",
                    (clean_name,)
                )
                drow = cursor.fetchone()
                if drow and drow["file_path"]:
                    dp = Path(drow["file_path"])
                    if dp.is_file():
                        target_path = dp
            conn.close()
        except Exception:
            pass

    if not target_path or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp báo giá đã tạo.")

    if clean_name.lower().endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif clean_name.lower().endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(target_path),
        filename=clean_name,
        media_type=media_type
    )


def list_quotation_files_controller() -> Dict[str, Any]:
    """Controller to retrieve all active quotations and generated files with version history."""
    bao_gia_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
    bao_gia_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch active quotations from DB with history count
    active_quotes = []
    try:
        active_quotes = get_all_active_quotations_service()
    except Exception as exc:
        logger.warning("Could not fetch active quotations from DB: %s", exc)

    # 2. Map existing documents
    doc_map = {}
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_name, doc_name, description, file_format, created_at FROM documents WHERE doc_type = 'BAO_GIA'")
        for row in cursor.fetchall():
            doc_map[row["file_name"]] = dict(row)
        conn.close()
    except Exception:
        pass

    files = []
    for pattern in ("*.docx", "*.xlsx"):
        for f in bao_gia_dir.glob(pattern):
            if f.is_file() and not f.name.startswith("~$"):
                stat = f.stat()
                mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
                doc_info = doc_map.get(f.name) or {}
                ext = f.suffix.lstrip(".").lower()

                files.append({
                    "file_name": f.name,
                    "file_path": str(f.resolve()),
                    "file_format": ext,
                    "file_size": stat.st_size,
                    "file_size_formatted": f"{stat.st_size / 1024:.1f} KB",
                    "modified_time": mtime_str,
                    "mtime_ts": stat.st_mtime,
                    "download_url": f"/api/v1/quotation/download/{f.name}",
                    "doc_name": doc_info.get("doc_name") or f.name,
                    "description": doc_info.get("description") or "",
                })

    files.sort(key=lambda x: x["mtime_ts"], reverse=True)
    return {
        "status": "success",
        "total": len(files),
        "files": files,
        "active_quotations": active_quotes
    }


def list_outlook_quotation_files_controller() -> Dict[str, Any]:
    """Controller to list all real quotation files downloaded from Outlook (From_Outlook)."""
    outlook_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia" / "From_Outlook"
    outlook_dir.mkdir(parents=True, exist_ok=True)

    meta_map = {
        "Inbox_61_報價單-茂鼎科技-20260721-越南ECOPRIME-橘子亞洲-電表設備.pdf": {
            "title": "Báo Giá Thiết Bị Đo Điện Năng DAE (Mao Ding / ECO PRIME)",
            "partner": "ECO PRIME / 茂鼎科技 / Orange Asia",
            "preset_key": "pouhui"
        },
        "Inbox_56_DAE設備-牌價表-越南總經銷報價.pdf": {
            "title": "Bảng Giá Đại Lý Phân Phối Thiết Bị DAE Tại VN (USD)",
            "partner": "DAE Technology / 總經銷",
            "preset_key": "daeusd"
        },
        "Inbox_58_22202-260600005.pdf": {
            "title": "Đơn Hàng Sửa Chữa Thiết Bị RFID RFR900 (CX PO)",
            "partner": "CX Technology (VN) Co., Ltd.",
            "preset_key": "cxrepair"
        },
        "CX_RFID_Bao_gia_sua_loi_202609_V1.1.xlsx": {
            "title": "Báo Giá Sửa Lỗi Thiết Bị RFID RFR900 (13.7M VND)",
            "partner": "CX Technology (VN) Co., Ltd.",
            "preset_key": "cxrepair"
        },
        "ECO PRIME_Báo Giá Đồng Hồ Điện & CC2051_Pou Hui_20261021.xlsx": {
            "title": "Báo Giá Đồng Hồ Điện & Gateway CC2051 (4 Trạm Biến Áp)",
            "partner": "ECO PRIME / Pou Hui (Phổ Huệ)",
            "preset_key": "pouhui"
        }
    }

    files = []
    for f in outlook_dir.glob("*.*"):
        if f.is_file() and not f.name.startswith("~$"):
            stat = f.stat()
            ext = f.suffix.lstrip(".").lower()
            meta = meta_map.get(f.name, {})

            files.append({
                "file_name": f.name,
                "file_path": str(f.resolve()),
                "file_format": ext,
                "file_size": stat.st_size,
                "file_size_formatted": f"{stat.st_size / 1024:.1f} KB",
                "title": meta.get("title") or f.name,
                "partner": meta.get("partner") or "Đối tác Hong Ming Global",
                "preset_key": meta.get("preset_key") or "",
                "download_url": f"/api/v1/quotation/download-outlook/{f.name}"
            })

    files.sort(key=lambda x: x["file_size"], reverse=True)
    return {
        "status": "success",
        "total": len(files),
        "files": files
    }


def download_outlook_quotation_file_controller(file_name: str) -> FileResponse:
    """Controller to download real quotation files from Outlook archive."""
    clean_name = os.path.basename(file_name)
    target_path = WORKING_DIR / "Ho So Du An" / "Bao Gia" / "From_Outlook" / clean_name

    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp báo giá từ Outlook.")

    if clean_name.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif clean_name.lower().endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif clean_name.lower().endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(target_path),
        filename=clean_name,
        media_type=media_type
    )
