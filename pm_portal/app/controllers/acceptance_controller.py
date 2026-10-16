"""Acceptance controller handling document generation, preview, AI parsing, and download."""

import logging
import os
from typing import Any, Dict

from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.config import OUTPUTS_DIR
from app.models.acceptance_models import AcceptanceAIParseRequest
from app.services.acceptance_ai_service import parse_acceptance_text
from app.services.acceptance_excel_service import (
    generate_acceptance_excel,
    prepare_acceptance_data,
)
from app.services.acceptance_preview_service import generate_acceptance_preview_html
from app.services.acceptance_repair_upload_service import (
    MAX_REPAIR_UPLOAD_BYTES,
    process_uploaded_repair_file,
)
from app.services.acceptance_word_service import generate_acceptance_word

logger = logging.getLogger(__name__)


async def process_repair_workbook_upload_controller(file: UploadFile) -> Dict[str, Any]:
    """Validate and process one uploaded repair workbook without blocking the event loop."""
    try:
        content = await file.read(MAX_REPAIR_UPLOAD_BYTES + 1)
        result = await run_in_threadpool(
            process_uploaded_repair_file,
            file.filename or "bien_ban_sua_chua.xlsx",
            content,
        )
        return {
            "status": "success",
            "message": (
                "Đã phân tích file sửa chữa và tạo biên bản nghiệm thu thành công. "
                f"Đã nhập đủ {result.get('record_count', 0)} bản ghi và gán đúng "
                f"{result['assigned_count']} ghi chú theo sản phẩm."
            ),
            **result,
        }
    except Exception as exc:
        logger.exception("Repair workbook upload failed: %s", exc)
        return {
            "status": "error",
            "message": f"Không thể xử lý file biên bản sửa chữa: {str(exc)}",
        }
    finally:
        await file.close()


def generate_acceptance_excel_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to create Acceptance Excel (.xlsx) file matching CX Technology sample 1:1."""
    try:
        result = generate_acceptance_excel(data)
        preview_html = generate_acceptance_preview_html(result["acceptance_data"])
        return {
            "status": "success",
            "message": "Đã tạo Biên bản nghiệm thu Excel (.xlsx) chuẩn 1:1 thành công!",
            "file_name": result["file_name"],
            "download_url": result["download_url"],
            "total_amount": result["total_amount"],
            "preview_html": preview_html,
            "acceptance_data": result["acceptance_data"]
        }
    except Exception as exc:
        logger.exception("Error generating acceptance excel: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tệp Excel nghiệm thu: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def generate_acceptance_word_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to create Acceptance Word (.docx) document."""
    try:
        result = generate_acceptance_word(data)
        return {
            "status": "success",
            "message": "Đã tạo Biên bản nghiệm thu Word (.docx) chuẩn hành chính thành công!",
            "file_name": result["file_name"],
            "download_url": result["download_url"],
            "total_amount": result["total_amount"],
            "acceptance_data": result["acceptance_data"]
        }
    except Exception as exc:
        logger.exception("Error generating acceptance docx: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo tài liệu Word nghiệm thu: {str(exc)}",
            "file_name": "",
            "download_url": ""
        }


def render_acceptance_preview_controller(data: Dict[str, Any]) -> Dict[str, Any]:
    """Controller to recalculate and refresh live acceptance preview HTML without writing files."""
    try:
        sanitized = prepare_acceptance_data(data)
        preview_html = generate_acceptance_preview_html(sanitized)
        return {
            "status": "success",
            "preview_html": preview_html,
            "data": sanitized
        }
    except Exception as exc:
        logger.exception("Error rendering acceptance preview: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "preview_html": f"<div class='alert alert-danger'>Lỗi cập nhật xem trước: {str(exc)}</div>"
        }


def parse_raw_acceptance_text_controller(request: AcceptanceAIParseRequest) -> Dict[str, Any]:
    """Analyze delivery sheet or repair notes with Gemini AI to extract acceptance items."""
    try:
        raw_text = request.raw_text.strip()
        if not raw_text:
            raise ValueError("Văn bản đầu vào không được để trống.")

        parsed_data = parse_acceptance_text(
            raw_input_text=raw_text,
            preferred_model=request.model_name
        )

        executed_model = parsed_data.pop("_executed_model", request.model_name or "Gemini")
        sanitized_data = prepare_acceptance_data(parsed_data)
        preview_html = generate_acceptance_preview_html(sanitized_data)

        return {
            "status": "success",
            "message": f"AI ({executed_model}) đã bóc tách dữ liệu nghiệm thu & tạo bản xem trước thành công!",
            "executed_model": executed_model,
            "data": sanitized_data,
            "preview_html": preview_html
        }
    except Exception as exc:
        logger.exception("Acceptance AI parse failed: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi phân tích AI: {str(exc)}",
            "data": None,
            "preview_html": ""
        }


def download_acceptance_file_controller(file_name: str) -> FileResponse:
    """Stream generated Excel or Word file for browser download."""
    clean_name = os.path.basename(file_name)
    file_path = OUTPUTS_DIR / clean_name

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp nghiệm thu đã tạo.")

    if clean_name.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif clean_name.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=clean_name,
        media_type=media_type
    )
