"""Controller for Payment Requests and AR Reminders."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.models.reminder_models import ReminderAIParseRequest
from app.services.google_integration_service import (
    create_gmail_draft,
    search_drive_files,
    send_gmail_message,
)
from app.services.reminder_ai_service import parse_reminder_text
from app.services.reminder_service import (
    prepare_reminder_data,
    render_dxyctt_preview_html,
    render_email_client_preview_html,
)

logger = logging.getLogger(__name__)


def parse_raw_reminder_text_controller(request: ReminderAIParseRequest) -> Dict[str, Any]:
    """Parse unstructured payment notes or emails using Gemini AI."""
    try:
        raw_text = request.raw_text.strip()
        if not raw_text:
            raise ValueError("Văn bản phân tích không được để trống.")
            
        parsed_data = parse_reminder_text(
            raw_input_text=raw_text,
            preferred_model=request.model_name,
            contract_code=request.contract_code,
            milestone_name=request.milestone_name,
            match_contract=request.match_contract
        )
        executed_model = parsed_data.pop("_executed_model", request.model_name or "Gemini")
        sanitized = prepare_reminder_data(parsed_data)
        
        email_preview_html = render_email_client_preview_html(sanitized)
        dxyctt_preview_html = render_dxyctt_preview_html(sanitized)
        
        return {
            "status": "success",
            "message": f"Gemini AI ({executed_model}) đã bóc tách dữ liệu đề nghị thanh toán thành công!",
            "data": sanitized,
            "email_preview_html": email_preview_html,
            "dxyctt_preview_html": dxyctt_preview_html
        }
    except Exception as exc:
        logger.exception("Error parsing reminder text with AI: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi phân tích AI: {str(exc)}"
        }


def render_reminder_preview_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recalculate totals and refresh live HTML previews for Email and A4 Document."""
    try:
        sanitized = prepare_reminder_data(payload)
        email_preview_html = render_email_client_preview_html(sanitized)
        dxyctt_preview_html = render_dxyctt_preview_html(sanitized)
        
        return {
            "status": "success",
            "data": sanitized,
            "email_preview_html": email_preview_html,
            "dxyctt_preview_html": dxyctt_preview_html
        }
    except Exception as exc:
        logger.exception("Error rendering reminder preview: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "email_preview_html": f"<div class='alert alert-danger'>Lỗi cập nhật xem trước email: {str(exc)}</div>",
            "dxyctt_preview_html": f"<div class='alert alert-danger'>Lỗi cập nhật xem trước văn bản: {str(exc)}</div>"
        }


def _ensure_payment_request_excel(data: Dict[str, Any], payload: Dict[str, Any]) -> List[str]:
    """Ensure the 712TR Excel and matching Word payment requests are primary attachments."""
    from pathlib import Path
    from app.services.payment_request_excel_service import generate_payment_request_excel
    attachments = list(data.get("danh_sach_dinh_kem") or [])
    
    items = data.get("khoan_thanh_toan") or []
    first_item = items[0] if items else {}
    contract_code = first_item.get("so_hop_dong") or payload.get("contract_code") or ""
    
    # If no contract code found, return attachments as is
    if not contract_code:
        return attachments

    khach = data.get("khach_hang", {})
    cust_vi = khach.get("ten_khach_hang") or payload.get("customer_name_vi")
    cust_zh = khach.get("ten_tieng_trung") or payload.get("customer_name_zh")
    ms_name = first_item.get("hang_muc") or payload.get("milestone_name") or "Đợt 2"
    if "(" in ms_name:
        parts = ms_name.split("(")
        if len(parts) > 1:
            ms_name = parts[1].split("-")[0].replace(")", "").strip()

    amt = first_item.get("so_tien") or payload.get("amount")
    due_date = first_item.get("han_thanh_toan") or payload.get("due_date")
    inv_no = first_item.get("vat_info") or payload.get("invoice_no")
    if inv_no and "HĐ" in inv_no:
        inv_no = inv_no.replace("HĐ", "").strip()

    try:
        gen_result = generate_payment_request_excel(
            contract_code=contract_code,
            milestone_name=ms_name,
            customer_name_vi=cust_vi,
            customer_name_zh=cust_zh,
            amount=amt,
            due_date=due_date,
            invoice_no=inv_no,
            template_source=payload.get("template_source") or "excel",
        )
        gen_filename = gen_result.get("file_name")
        gen_path = gen_result.get("file_path")
        word_filename = gen_result.get("word_file_name")
        word_path = gen_result.get("word_file_path")

        # Clean attachments list: remove mismatched or outdated payment request filenames
        cleaned_attachments = []
        for att in attachments:
            att_str = str(att).strip()
            # Remove existing payment request files that might belong to another contract
            if "đơn yêu cầu" in att_str.lower() or "yeu cau thanh toan" in att_str.lower():
                continue
            cleaned_attachments.append(att_str)

        excel_attachment = str(gen_path) if gen_path and Path(gen_path).exists() else gen_filename
        word_attachment = str(word_path) if word_path and Path(word_path).exists() else word_filename
        generated_attachments = [excel_attachment, word_attachment]
        if gen_result.get("template_source") == "word":
            generated_attachments.reverse()
        for index, attachment in enumerate(item for item in generated_attachments if item):
            cleaned_attachments.insert(index, attachment)

        logger.info("Auto-ensured payment request Excel + Word attachments: %s, %s", gen_filename, word_filename)
        return cleaned_attachments
    except Exception as exc:
        logger.warning("Could not auto-generate payment request Excel: %s", exc)
        return attachments


def create_gmail_draft_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a draft email in the user's connected Gmail account."""
    try:
        data = prepare_reminder_data(payload)
        khach = data.get("khach_hang", {})
        to_list = khach.get("email_to", [])
        cc_list = khach.get("email_cc", [])
        subject = data.get("tieu_de_email", "")
        plain_body = data.get("email_plain_body", "")
        html_body = data.get("email_html_body", "")
        
        # Ensure 1:1 Excel payment request is generated and attached
        attachments = _ensure_payment_request_excel(data, payload)
        
        if not to_list:
            raise ValueError("Vui lòng nhập ít nhất một địa chỉ email người nhận (To).")
        if not subject:
            raise ValueError("Tiêu đề email không được để trống.")
            
        result = create_gmail_draft(
            to=to_list,
            cc=cc_list,
            subject=subject,
            body_text=plain_body,
            html_body=html_body,
            attachments=attachments
        )
        if result.get("status") == "success":
            result["attachments"] = [Path(a).name for a in attachments]
        return result
    except Exception as exc:
        logger.exception("Error creating Gmail draft: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo bản nháp trên Gmail: {str(exc)}"
        }


def send_gmail_message_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email directly through the connected Gmail account."""
    try:
        data = prepare_reminder_data(payload)
        khach = data.get("khach_hang", {})
        to_list = khach.get("email_to", [])
        cc_list = khach.get("email_cc", [])
        subject = data.get("tieu_de_email", "")
        plain_body = data.get("email_plain_body", "")
        html_body = data.get("email_html_body", "")
        
        # Ensure 1:1 Excel payment request is generated and attached
        attachments = _ensure_payment_request_excel(data, payload)
        
        if not to_list:
            raise ValueError("Vui lòng nhập ít nhất một địa chỉ email người nhận (To).")
            
        result = send_gmail_message(
            to=to_list,
            cc=cc_list,
            subject=subject,
            body_text=plain_body,
            html_body=html_body,
            attachments=attachments
        )
        if result.get("status") == "success":
            result["attachments"] = [Path(a).name for a in attachments]
        return result
    except Exception as exc:
        logger.exception("Error sending email via Gmail: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi gửi thư qua Gmail: {str(exc)}"
        }


def search_google_drive_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Search files in the connected Google Drive account."""
    try:
        query = str(payload.get("query") or "").strip()
        files = search_drive_files(query=query)
        return {
            "status": "success",
            "files": files,
            "count": len(files)
        }
    except Exception as exc:
        logger.exception("Error searching Google Drive: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tìm kiếm trên Google Drive: {str(exc)}",
            "files": []
        }
