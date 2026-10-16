"""API routes for contracts, AI analysis, and document downloads."""

import logging

from typing import Any, Dict, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import CANDIDATE_MODELS, DEFAULT_MODEL
from app.controllers.acceptance_controller import (
    download_acceptance_file_controller,
    generate_acceptance_excel_controller,
    generate_acceptance_word_controller,
    parse_raw_acceptance_text_controller,
    list_acceptance_files_controller,
    process_repair_workbook_upload_controller,
    render_acceptance_preview_controller,
)
from app.controllers.ai_controller import parse_raw_contract_text_controller
from app.controllers.contract_controller import (
    delete_contract_controller,
    download_contract_file_controller,
    generate_contract_controller,
    get_contract_detail_controller,
    get_contract_dossier_controller,
    list_contracts_controller,
    render_preview_controller,
    save_contract_controller,
)
from app.controllers.reminder_controller import (
    create_gmail_draft_controller,
    parse_raw_reminder_text_controller,
    render_reminder_preview_controller,
    search_google_drive_controller,
    send_gmail_message_controller,
)
from app.models.acceptance_models import AcceptanceAIParseRequest
from app.models.contract_models import AIParseRequest
from app.models.reminder_models import ReminderAIParseRequest
from app.controllers.custom_reminder_controller import (
    create_custom_reminder_controller,
    delete_custom_reminder_controller,
    download_reminder_attachment_controller,
    list_available_project_files_controller,
    list_custom_reminders_controller,
    toggle_reminder_status_controller,
    update_custom_reminder_controller,
)

from app.controllers.quotation_controller import (
    download_quotation_file_controller,
    generate_quotation_excel_controller,
    generate_quotation_word_controller,
    get_quotation_detail_controller,
    get_quotation_history_controller,
    list_quotation_files_controller,
    parse_raw_quotation_text_controller,
    save_quotation_controller,
)
from app.models.quotation_models import QuotationAIParseRequest, QuotationSaveRequest
from app.services.font_service import (
    get_active_font_setting,
    get_all_fonts,
    save_active_font_setting,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Contract, Acceptance, Reminder & AI APIs"])


@router.get("/system/models")
async def get_system_models():
    """Retrieve list of supported AI models."""
    return {
        "candidate_models": CANDIDATE_MODELS,
        "default_model": DEFAULT_MODEL
    }


@router.get("/fonts")
async def list_fonts():
    """Get all 100 fonts and current active font."""
    return {
        "fonts": get_all_fonts(),
        "active_font": get_active_font_setting()
    }


@router.post("/fonts/active")
async def set_active_font(payload: Dict[str, Any]):
    """Persist active font selection."""
    saved = save_active_font_setting(payload)
    return {
        "success": True,
        "message": f"Đã áp dụng font {saved.get('name')} cho toàn bộ hệ thống!",
        "active_font": saved
    }


# ==========================================
# CONTRACT ENDPOINTS
# ==========================================

@router.post("/ai/parse-contract")
async def parse_contract_with_ai(request: AIParseRequest):
    """Analyze raw business text with Gemini AI to extract contract schema."""
    return parse_raw_contract_text_controller(request)


@router.post("/ai/parse-contract-file")
async def parse_contract_file_with_ai(
    file: UploadFile = File(...),
    raw_text: Optional[str] = Form(""),
    model_name: Optional[str] = Form(None)
):
    """Analyze uploaded Excel sheet or image directly with Gemini AI."""
    import base64
    content = await file.read()
    request = AIParseRequest(
        raw_text=raw_text or "",
        file_base64=base64.b64encode(content).decode("ascii"),
        file_name=file.filename,
        file_mime=file.content_type,
        model_name=model_name
    )
    return parse_raw_contract_text_controller(request)

@router.post("/contracts/ai-project-title")
async def summarize_project_title_endpoint(payload: Dict[str, Any]):
    """Summarize project title in VN and CN concisely based on product names."""
    from app.services.ai_service import summarize_project_title_with_ai
    prod_names = payload.get("product_names", [])
    result = summarize_project_title_with_ai(prod_names)
    return {
        "status": "success",
        "data": result
    }


@router.get("/contracts/list")
async def list_contracts_endpoint():
    """Retrieve full list of created contracts from database and exported files."""
    return list_contracts_controller()


@router.get("/contracts/detail/{contract_code_or_id}")
async def get_contract_detail_endpoint(contract_code_or_id: str):
    """Retrieve full contract details to populate back into editor form."""
    return get_contract_detail_controller(contract_code_or_id)


@router.delete("/contracts/{contract_code_or_id}")
async def delete_contract_endpoint(contract_code_or_id: str):
    """Delete a contract record from the system."""
    return delete_contract_controller(contract_code_or_id)


@router.post("/contracts/generate")
async def generate_contract(payload: Dict[str, Any]):
    """Generate Word (.docx) document with Zero Layout Distortion."""
    return generate_contract_controller(payload)


@router.post("/contracts/preview")
async def render_contract_preview(payload: Dict[str, Any]):
    """Recalculate totals and return updated live HTML preview."""
    return render_preview_controller(payload)


@router.get("/contracts/download/{file_name}")
async def download_contract(file_name: str) -> FileResponse:
    """Download generated contract DOCX file."""
    return download_contract_file_controller(file_name)


@router.post("/contracts/save")
async def save_contract_endpoint(payload: Dict[str, Any]):
    """Save generated contract into SQLite dossier with payment milestones and linked documents."""
    return save_contract_controller(payload)


@router.get("/contracts/{identifier}/dossier")
async def get_contract_dossier_endpoint(identifier: str):
    """Retrieve full contract dossier (contract, milestones, and all linked documents)."""
    return get_contract_dossier_controller(identifier)


# ==========================================
# ACCEPTANCE (NGHIỆM THU) ENDPOINTS
# ==========================================

@router.post("/ai/parse-acceptance")
async def parse_acceptance_with_ai(request: AcceptanceAIParseRequest):
    """Analyze raw delivery sheet or repair notes with Gemini AI to extract acceptance items."""
    return parse_raw_acceptance_text_controller(request)


@router.post("/acceptance/generate-excel")
async def generate_acceptance_excel_endpoint(payload: Dict[str, Any]):
    """Generate high-fidelity Acceptance Excel (.xlsx) file matching CX Technology sample 1:1."""
    return generate_acceptance_excel_controller(payload)


@router.post("/acceptance/generate-word")
async def generate_acceptance_word_endpoint(payload: Dict[str, Any]):
    """Generate formal Acceptance Word (.docx) document."""
    return generate_acceptance_word_controller(payload)


@router.post("/acceptance/preview")
async def render_acceptance_preview(payload: Dict[str, Any]):
    """Recalculate and return live HTML acceptance preview."""
    return render_acceptance_preview_controller(payload)


@router.post("/acceptance/process-repair-file")
async def process_repair_workbook_upload(
    file: UploadFile = File(..., description="Biên bản sửa chữa định dạng .xlsx"),
    contract_code: Optional[str] = Form(None, description="Mã hợp đồng liên kết (tùy chọn)"),
):
    """Create an acceptance workbook from an uploaded repair workbook, checking and linking contract."""
    return await process_repair_workbook_upload_controller(file, contract_code)


@router.get("/acceptance/download/{file_name}")
async def download_acceptance_file(file_name: str) -> FileResponse:
    """Download generated acceptance Excel or Word file."""
    return download_acceptance_file_controller(file_name)


@router.get("/acceptance/files")
async def list_acceptance_files():
    """List all created acceptance files in Ho So Du An/Nghiem Thu."""
    return list_acceptance_files_controller()



# ==========================================
# PAYMENT REMINDER & REQUEST (ĐỀ NGHỊ THANH TOÁN & NHẮC NỢ)
# ==========================================

@router.post("/ai/parse-reminder")
async def parse_reminder_with_ai(request: ReminderAIParseRequest):
    """Analyze payment request or reminder notes with Gemini AI."""
    return parse_raw_reminder_text_controller(request)


@router.post("/reminders/preview")
async def render_reminder_preview(payload: Dict[str, Any]):
    """Recalculate totals and return live preview for Email & A4 DXYCTT."""
    return render_reminder_preview_controller(payload)


@router.post("/reminders/gmail/draft")
async def create_gmail_draft_endpoint(payload: Dict[str, Any]):
    """Create draft email in connected Gmail account."""
    return create_gmail_draft_controller(payload)


@router.post("/reminders/gmail/send")
async def send_gmail_endpoint(payload: Dict[str, Any]):
    """Send payment reminder email via connected Gmail account."""
    return send_gmail_message_controller(payload)


@router.post("/reminders/drive/search")
async def search_drive_endpoint(payload: Dict[str, Any]):
    """Search project documents and PDFs on connected Google Drive."""
    return search_google_drive_controller(payload)



# ==========================================
# DASHBOARD & LIVE PROJECT TRACKER
# ==========================================

from fastapi.responses import Response
from app.services.dashboard_service import (
    get_dashboard_overview_data,
    generate_dashboard_excel_report,
    sync_contracts_from_tracker_excel,
)


@router.get("/dashboard/overview")
async def get_dashboard_overview_endpoint():
    """Retrieve live dashboard overview metrics, KPI cards, and project items from SQLite."""
    return get_dashboard_overview_data()


@router.get("/dashboard/export-excel")
async def export_dashboard_excel_endpoint():
    """Export real project portfolio and milestones to executive Excel workbook."""
    from datetime import datetime
    stream = generate_dashboard_excel_report()
    filename = f"BAO_CAO_TIEN_DO_DU_AN_HONG_MING_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/dashboard/sync-excel")
async def sync_dashboard_excel_endpoint():
    """Synchronize historical projects from tracker Excel into SQLite database."""
    return sync_contracts_from_tracker_excel()


# ==========================================
# DOSSIER & SQLITE DOCUMENT MANAGEMENT
# ==========================================

from pathlib import Path
from fastapi import HTTPException
from app.database import (
    get_contracts_dossier,
    get_contract_by_code,
    get_all_documents_by_type,
    get_db_connection,
    delete_contract_dossier,
    activate_payment_milestone,
    reset_payment_milestone,
    mark_milestone_paid,
    unmark_milestone_paid,
    update_contract_status,
)


@router.get("/dossier/contracts")
async def list_contracts_dossier():
    """Retrieve all contracts with milestones and linked documents from SQLite database."""
    contracts = get_contracts_dossier()
    return {
        "status": "success",
        "total": len(contracts),
        "contracts": contracts
    }


@router.get("/dossier/contracts/{contract_code}")
async def get_single_contract_dossier(contract_code: str):
    """Retrieve single contract dossier by code."""
    contract = get_contract_by_code(contract_code)
    if not contract:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng.")
    return {
        "status": "success",
        "contract": contract
    }


@router.post("/dossier/milestones/{milestone_id}/activate")
async def activate_milestone_endpoint(milestone_id: int, payload: Dict[str, Any]):
    """Mark a milestone trigger complete and start its own T/T countdown."""
    trigger_date = payload.get("trigger_date")
    if not trigger_date:
        raise HTTPException(status_code=400, detail="Vui lòng nhập ngày hoàn thành điều kiện.")
    milestone = activate_payment_milestone(milestone_id, str(trigger_date))
    if not milestone:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt thanh toán.")
    return {
        "status": "success",
        "message": f"Đã bắt đầu tính hạn cho {milestone['milestone_name']} đến ngày {milestone['due_date']}.",
        "milestone": milestone,
    }


@router.post("/dossier/milestones/{milestone_id}/reset")
async def reset_milestone_endpoint(milestone_id: int):
    """Reset a milestone back to un-triggered pending state."""
    milestone = reset_payment_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt thanh toán.")
    return {
        "status": "success",
        "message": f"Đã hủy kích hoạt và đặt lại {milestone['milestone_name']} về trạng thái chờ.",
        "milestone": milestone,
    }


@router.post("/dossier/milestones/{milestone_id}/mark-paid")
async def mark_milestone_paid_endpoint(milestone_id: int, payload: Dict[str, Any]):
    """Confirm payment received for a milestone and update contract financial total."""
    paid_date = payload.get("paid_date")
    invoice_no = payload.get("invoice_no")
    actual_amount = payload.get("amount")
    if actual_amount is not None:
        try:
            actual_amount = float(actual_amount)
        except ValueError:
            actual_amount = None

    result = mark_milestone_paid(
        milestone_id=milestone_id,
        paid_date=str(paid_date) if paid_date else None,
        invoice_no=str(invoice_no) if invoice_no else None,
        actual_amount=actual_amount,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt thanh toán.")
    return {
        "status": "success",
        "message": f"Đã xác nhận thanh toán thành công cho {result['milestone']['milestone_name']}!",
        "data": result,
    }


@router.post("/dossier/milestones/{milestone_id}/unmark-paid")
async def unmark_milestone_paid_endpoint(milestone_id: int):
    """Revert a paid milestone back to pending / waiting status."""
    result = unmark_milestone_paid(milestone_id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt thanh toán.")
    return {
        "status": "success",
        "message": f"Đã hoàn tác trạng thái thanh toán cho {result['milestone']['milestone_name']}.",
        "data": result,
    }


@router.post("/dossier/contracts/{contract_code}/status")
async def update_contract_status_endpoint(contract_code: str, payload: Dict[str, Any]):
    """Update contract operational status and notes."""
    new_status = payload.get("status")
    notes = payload.get("notes")
    if not new_status:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp trạng thái mới cho hợp đồng.")
    updated = update_contract_status(contract_code, str(new_status), notes)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy hợp đồng.")
    return {
        "status": "success",
        "message": f"Đã cập nhật trạng thái hợp đồng {contract_code} thành '{new_status}'!",
        "contract": updated,
    }



@router.delete("/dossier/contracts/{contract_code}")
async def delete_contract_endpoint(contract_code: str):
    """Delete a contract and its milestones/documents from dossier."""
    success = delete_contract_dossier(contract_code)
    if not success:
        return {
            "status": "success",
            "message": f"Hợp đồng {contract_code} đã được xóa hoặc không còn tồn tại trên hệ thống."
        }
    return {
        "status": "success",
        "message": f"Đã xóa hợp đồng {contract_code} khỏi hệ thống."
    }




@router.get("/dossier/documents")
async def list_documents_endpoint(doc_type: Optional[str] = None):
    """List indexed documents from database."""
    docs = get_all_documents_by_type(doc_type)
    return {
        "status": "success",
        "total": len(docs),
        "documents": docs
    }


@router.get("/dossier/documents/{doc_id}/download")
async def download_dossier_document(doc_id: int):
    """Download or view a specific document indexed in SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại trong cơ sở dữ liệu.")

    file_path = Path(row["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Tệp vật lý không tồn tại trên ổ đĩa.")

    # Determine media type
    ext = file_path.suffix.lower()
    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".json": "application/json",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type
    )


@router.delete("/dossier/documents/{doc_id}")
async def delete_dossier_document_endpoint(doc_id: int):
    """Delete a document record from database AND delete physical file from disk."""
    from app.database import delete_document_record_and_file
    success = delete_document_record_and_file(doc_id)
    if not success:
        return {
            "status": "success",
            "message": "Tài liệu này đã được xóa trước đó hoặc không còn tồn tại trên hệ thống."
        }
    return {
        "status": "success",
        "message": "Đã xóa tài liệu và tệp trên máy tính thành công."
    }


from app.services.payment_request_excel_service import generate_payment_request_excel

@router.post("/reminders/generate-sheet")
async def generate_payment_request_sheet_endpoint(payload: Dict[str, Any]):
    """Generate payment request with Excel 712TR or DOCX as the selected master template."""
    try:
        contract_code = payload.get("contract_code") or "HMV151020250001"
        milestone_name = payload.get("milestone_name") or "Đợt 2"
        
        result = generate_payment_request_excel(
            contract_code=contract_code,
            milestone_name=milestone_name,
            customer_name_vi=payload.get("customer_name_vi"),
            customer_name_zh=payload.get("customer_name_zh"),
            project_name_vi=payload.get("project_name_vi"),
            project_name_zh=payload.get("project_name_zh"),
            amount=payload.get("amount"),
            total_contract_amount=payload.get("total_contract_amount"),
            percentage=payload.get("percentage"),
            due_date=payload.get("due_date"),
            invoice_no=payload.get("invoice_no"),
            application_date=payload.get("application_date"),
            template_source=payload.get("template_source") or "excel",
        )
        return result
    except Exception as exc:
        logger.exception("Error generating payment request sheet: %s", exc)
        return {
            "status": "error",
            "message": f"Lỗi tạo phiếu yêu cầu thanh toán: {str(exc)}"
        }


@router.post("/system/open-path")
async def open_system_path_endpoint(payload: Dict[str, Any]):
    """Open a file or folder directly in Windows Explorer."""
    import subprocess
    import sys
    raw_path = (payload.get("path") or "").strip()
    if not raw_path:
        return {"status": "error", "message": "Thiếu đường dẫn cần mở."}

    p = Path(raw_path)
    if not p.is_absolute():
        from app.config import WORKING_DIR
        candidate = WORKING_DIR / raw_path
        if candidate.exists():
            p = candidate
        else:
            candidate2 = Path.cwd() / raw_path
            if candidate2.exists():
                p = candidate2

    if not p.exists():
        return {
            "status": "error",
            "message": f"Tệp hoặc thư mục chưa tồn tại trên ổ đĩa: {raw_path}"
        }

    try:
        if sys.platform == "win32":
            import os
            resolved_str = str(p.resolve())
            # Mở trực tiếp file bằng ứng dụng mặc định (Word, Excel...) qua Windows ShellExecute
            # Không dùng explorer /select để tránh lag và mở nhầm thư mục chứa
            os.startfile(resolved_str)
            action_desc = "tệp" if p.is_file() else "thư mục"
            return {
                "status": "success",
                "message": f"Đã mở {action_desc} trên máy tính: {p.name or resolved_str}"
            }
        return {
            "status": "warning",
            "message": "Tính năng mở trực tiếp trên máy tính chỉ áp dụng trên hệ điều hành Windows."
        }
    except Exception as exc:
        logger.exception("Error opening path: %s", exc)
        return {
            "status": "error",
            "message": f"Không thể mở đường dẫn: {str(exc)}"
        }


# ============================================================================
# Quotation Endpoints (Báo Giá - Word, Excel, AI Parse & Version History)
# ============================================================================

@router.post("/quotation/ai-parse")
async def parse_quotation_ai_endpoint(request: QuotationAIParseRequest):
    """Parse unstructured text or uploaded files using Gemini AI for quotation form."""
    return parse_raw_quotation_text_controller(request)


@router.post("/quotation/save")
async def save_quotation_endpoint(payload: Dict[str, Any]):
    """Save quotation with versioning, replacing old active quotation while backing up previous version."""
    return save_quotation_controller(payload)


@router.get("/quotation/history/{quotation_no}")
async def get_quotation_history_endpoint(quotation_no: str):
    """Retrieve full version history for a specific quotation number."""
    return get_quotation_history_controller(quotation_no)


@router.get("/quotation/detail/{identifier}")
async def get_quotation_detail_endpoint(identifier: str):
    """Retrieve complete quotation details (including items) to load into form."""
    return get_quotation_detail_controller(identifier)


@router.post("/quotation/generate-word")
async def generate_quotation_word_endpoint(payload: Dict[str, Any]):
    """Generate official bilingual Word (.docx) quotation."""
    return generate_quotation_word_controller(payload)


@router.post("/quotation/generate-excel")
async def generate_quotation_excel_endpoint(payload: Dict[str, Any]):
    """Generate official bilingual Excel (.xlsx) quotation."""
    return generate_quotation_excel_controller(payload)


@router.get("/quotation/download/{file_name}")
async def download_quotation_file_endpoint(file_name: str):
    """Download generated quotation file (.docx or .xlsx)."""
    return download_quotation_file_controller(file_name)


@router.get("/quotation/files")
async def list_quotation_files_endpoint():
    """Retrieve list of generated quotation files."""
    return list_quotation_files_controller()


# ==========================================
# CUSTOM PERSONAL REMINDERS & SCHEDULE
# ==========================================

@router.get("/custom-reminders")
async def list_custom_reminders_endpoint(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
):
    """Retrieve list of custom personal reminders with stats and filters."""
    return await list_custom_reminders_controller(status=status, priority=priority, search=search)


@router.post("/custom-reminders")
async def create_custom_reminder_endpoint(
    title: str = Form(...),
    due_date: str = Form(...),
    description: str = Form(""),
    due_time: str = Form("09:00"),
    priority: str = Form("NORMAL"),
    category: str = Form("GENERAL"),
    existing_file_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Create a new custom personal reminder with optional file upload or link."""
    return await create_custom_reminder_controller(
        title=title,
        due_date=due_date,
        description=description,
        due_time=due_time,
        priority=priority,
        category=category,
        file=file,
        existing_file_path=existing_file_path,
    )


@router.put("/custom-reminders/{reminder_id}")
async def update_custom_reminder_endpoint(
    reminder_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    due_date: Optional[str] = Form(None),
    due_time: Optional[str] = Form(None),
    priority: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    existing_file_path: Optional[str] = Form(None),
    remove_attachment: bool = Form(False),
    file: Optional[UploadFile] = File(None),
):
    """Update custom personal reminder details or attachment."""
    return await update_custom_reminder_controller(
        reminder_id=reminder_id,
        title=title,
        description=description,
        due_date=due_date,
        due_time=due_time,
        priority=priority,
        category=category,
        file=file,
        existing_file_path=existing_file_path,
        remove_attachment=remove_attachment,
    )


@router.patch("/custom-reminders/{reminder_id}/toggle")
async def toggle_custom_reminder_endpoint(reminder_id: int):
    """Toggle status between PENDING and COMPLETED."""
    return await toggle_reminder_status_controller(reminder_id)


@router.delete("/custom-reminders/{reminder_id}")
async def delete_custom_reminder_endpoint(reminder_id: int, delete_file: bool = False):
    """Delete a custom reminder and optionally its uploaded file."""
    return await delete_custom_reminder_controller(reminder_id, delete_file)


@router.get("/custom-reminders/{reminder_id}/download")
async def download_custom_reminder_attachment_endpoint(reminder_id: int):
    """Download attached file for a custom reminder."""
    return await download_reminder_attachment_controller(reminder_id)


@router.get("/custom-reminders/project-files")
async def list_project_files_for_reminders_endpoint():
    """List available project files from Ho So Du An to link with 1 click."""
    return await list_available_project_files_controller()


