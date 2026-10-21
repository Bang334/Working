# -*- coding: utf-8 -*-
"""Controller xử lý Đơn Xin Thanh Toán (浤詺付款申请单) và Danh bạ tài khoản thụ hưởng."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.config import WORKING_DIR
from app.services.beneficiary_service import (
    delete_beneficiary,
    list_beneficiaries,
    upsert_beneficiary,
)
from app.services.payment_voucher_ai_service import (
    extract_payment_voucher_data,
    translate_payment_reason,
)
from app.services.payment_voucher_excel_service import (
    OUTPUT_DIR,
    delete_voucher_history,
    generate_payment_voucher_excel,
    get_next_report_code,
    list_voucher_history,
)

logger = logging.getLogger(__name__)


def ai_extract_voucher_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Trích xuất tự động thông tin đơn xin thanh toán từ văn bản thô hoặc tệp đính kèm (PDF, Ảnh, Excel)."""
    raw_text = str(payload.get("raw_text") or "").strip()
    file_base64 = payload.get("file_base64")
    file_mime = payload.get("file_mime")
    file_name = payload.get("file_name")

    if not raw_text and not file_base64:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp văn bản hoặc đính kèm tệp PDF/Ảnh/Excel để AI phân tích.")
    model_name = payload.get("model_name")
    try:
        data = extract_payment_voucher_data(
            raw_text=raw_text,
            preferred_model=model_name,
            file_base64=file_base64,
            file_mime=file_mime,
            file_name=file_name
        )
        return {
            "status": "success",
            "message": "Trích xuất thông tin đơn xin thanh toán thành công.",
            "data": data
        }
    except Exception as exc:
        logger.error("Error in ai_extract_voucher_controller: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi AI trích xuất: {str(exc)}")


def ai_translate_reason_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dịch lý do thanh toán sang tiếng Trung song ngữ."""
    reason_vi = str(payload.get("reason_vi") or "").strip()
    if not reason_vi:
        raise HTTPException(status_code=400, detail="Vui lòng nhập nội dung tiếng Việt cần dịch.")
    model_name = payload.get("model_name")
    try:
        data = translate_payment_reason(reason_vi, preferred_model=model_name)
        return {
            "status": "success",
            "message": "Dịch song ngữ thành công.",
            "data": data
        }
    except Exception as exc:
        logger.error("Error in ai_translate_reason_controller: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi AI dịch thuật: {str(exc)}")


def generate_voucher_excel_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Tạo file Excel đơn xin thanh toán và lưu lịch sử."""
    try:
        result = generate_payment_voucher_excel(payload)
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error("Error in generate_voucher_excel_controller: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi tạo file Excel: {str(exc)}")


def list_beneficiaries_controller(search: Optional[str] = None) -> Dict[str, Any]:
    """Lấy danh sách các tài khoản thụ hưởng đã lưu."""
    bens = list_beneficiaries(search=search, limit=200)
    return {
        "status": "success",
        "total": len(bens),
        "data": bens
    }


def save_beneficiary_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Thêm mới hoặc cập nhật tài khoản thụ hưởng."""
    unit_name = payload.get("unit_name")
    account_number = payload.get("account_number")
    bank_name = payload.get("bank_name")
    short_name = payload.get("short_name")
    default_reason = payload.get("default_reason")
    swift_code = payload.get("swift_code")
    currency = payload.get("currency") or "VND"

    if not unit_name or not account_number or not bank_name:
        raise HTTPException(status_code=400, detail="Thiếu thông tin tên đơn vị, số tài khoản hoặc ngân hàng.")

    try:
        saved = upsert_beneficiary(
            unit_name=unit_name,
            account_number=account_number,
            bank_name=bank_name,
            short_name=short_name,
            default_reason=default_reason,
            swift_code=swift_code,
            currency=currency
        )
        return {
            "status": "success",
            "message": "Đã lưu tài khoản thụ hưởng vào danh bạ.",
            "data": saved
        }
    except Exception as exc:
        logger.error("Error saving beneficiary: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def delete_beneficiary_controller(beneficiary_id: int) -> Dict[str, Any]:
    """Xóa tài khoản thụ hưởng khỏi danh bạ."""
    success = delete_beneficiary(beneficiary_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để xóa.")
    return {
        "status": "success",
        "message": "Đã xóa tài khoản thụ hưởng thành công."
    }


def list_voucher_history_controller(search: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    """Lấy lịch sử các đơn xin thanh toán đã tạo, có hỗ trợ tìm kiếm tra cứu."""
    history = list_voucher_history(search=search, limit=limit)
    return {
        "status": "success",
        "total": len(history),
        "data": history
    }


def delete_voucher_history_controller(voucher_id: int) -> Dict[str, Any]:
    """Xóa 1 bản ghi đơn xin thanh toán khỏi lịch sử."""
    success = delete_voucher_history(voucher_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn thanh toán để xóa.")
    return {
        "status": "success",
        "message": "Đã xóa đơn thanh toán khỏi lịch sử."
    }


def download_voucher_file_controller(filename: str):
    """Tải file Excel đơn xin thanh toán đã tạo."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file trên máy chủ.")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def get_next_report_code_controller(
    employee_code: str = "HVM007",
    target_date: Optional[str] = None
) -> Dict[str, Any]:
    """Sinh mã số báo đơn tiếp theo theo mã nhân viên và ngày."""
    try:
        data = get_next_report_code(employee_code=employee_code, target_date=target_date)
        return {
            "status": "success",
            "message": "Đã tính mã báo đơn tiếp theo thành công.",
            "data": data
        }
    except Exception as exc:
        logger.error("Error in get_next_report_code_controller: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi tính mã báo đơn: {str(exc)}")
