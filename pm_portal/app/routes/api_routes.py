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
    process_repair_workbook_upload_controller,
    render_acceptance_preview_controller,
)
from app.controllers.ai_controller import parse_raw_contract_text_controller
from app.controllers.contract_controller import (
    delete_contract_controller,
    download_contract_file_controller,
    generate_contract_controller,
    get_contract_detail_controller,
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
):
    """Create an acceptance workbook from an uploaded repair workbook."""
    return await process_repair_workbook_upload_controller(file)


@router.get("/acceptance/download/{file_name}")
async def download_acceptance_file(file_name: str) -> FileResponse:
    """Download generated acceptance Excel or Word file."""
    return download_acceptance_file_controller(file_name)


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
    clear_all_contracts,
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



@router.post("/dossier/contracts/clear-all")
async def clear_all_contracts_endpoint():
    """Clear all dummy/test contracts from database for a clean slate."""
    deleted_count = clear_all_contracts()
    return {
        "status": "success",
        "deleted_count": deleted_count,
        "message": f"Đã xóa toàn bộ {deleted_count} hợp đồng mẫu/rác. Hệ thống đã sẵn sàng cho dữ liệu thực tế!"
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
