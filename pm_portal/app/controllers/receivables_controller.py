# -*- coding: utf-8 -*-
"""Receivables controller handling API requests for AR debt tracking, AI risk digest, and Excel export."""

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.models.receivables_models import (
    ReceivableCreateRequest,
    ReceivableQuickNotesUpdate,
    ReceivableQuickStatusUpdate,
    ReceivableUpdateRequest,
)
from app.services.receivables_ai_service import get_ai_receivables_digest, parse_receivables_ai
from app.services.receivables_excel_service import export_receivables_excel
from app.services.receivables_report_service import (
    generate_receivables_ppt_presentation,
    generate_receivables_word_report,
    prepare_receivables_management_data,
)
from app.services.receivables_service import (
    create_receivable,
    delete_receivable,
    get_receivable_by_id,
    get_receivables_stats,
    get_weekly_comparison_data,
    register_custom_receivables_file,
    import_receivables_from_sheet3,
    list_receivables,
    save_weekly_snapshot,
    sync_from_existing_contracts,
    update_receivable,
    update_receivable_notes,
    update_receivable_status,
)

router = APIRouter(prefix="/api/v1/receivables", tags=["Project Receivables & AR Tracker"])


@router.get("")
async def get_receivables_endpoint(
    customer: Optional[str] = Query(None, description="Lọc theo khách hàng"),
    status: Optional[str] = Query(None, description="Lọc trạng thái: PAID, PENDING, URGENT, DELAYED"),
    search: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
    overdue_only: bool = Query(False, description="Chỉ lấy các khoản nợ quá hạn"),
):
    """Retrieve filtered project receivables."""
    try:
        items = list_receivables(
            customer=customer,
            status=status,
            search=search,
            overdue_only=overdue_only,
        )
        stats = get_receivables_stats()
        return {
            "status": "success",
            "total": len(items),
            "receivables": items,
            "stats": stats,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/stats")
async def get_receivables_stats_endpoint():
    """Retrieve summary statistics of project receivables."""
    try:
        stats = get_receivables_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/ai-digest")
async def get_ai_digest_endpoint():
    """Analyze debt portfolio and retrieve Gemini AI risk digest and action items."""
    try:
        digest = get_ai_receivables_digest()
        return {"status": "success", "digest": digest}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.patch("/{item_id}/status")
async def update_status_endpoint(item_id: int, payload: ReceivableQuickStatusUpdate):
    """Fast inline update of collection status (PAID, PENDING, URGENT, DELAYED)."""
    try:
        paid_date = datetime.date.today().strftime("%Y-%m-%d") if payload.collection_status == "PAID" else None
        success = update_receivable_status(item_id, payload.collection_status, paid_date=paid_date)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy mốc công nợ.")
        return {"status": "success", "message": "Đã cập nhật trạng thái thu tiền thành công."}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.patch("/{item_id}/notes")
async def update_notes_endpoint(item_id: int, payload: ReceivableQuickNotesUpdate):
    """Fast inline update of follow-up notes."""
    try:
        success = update_receivable_notes(item_id, payload.notes or "")
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy mốc công nợ.")
        return {"status": "success", "message": "Đã lưu ghi chú tiến độ thành công."}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/sync")
async def sync_contracts_endpoint(clear_first: bool = Query(True, description="Làm sạch và đồng bộ lại từ hợp đồng DB")):
    """Sync payment milestones from existing database contracts into project receivables."""
    try:
        synced_count = sync_from_existing_contracts(clear_first=clear_first)
        return {
            "status": "success",
            "message": f"Đã đồng bộ chính xác {synced_count} mốc thanh toán từ Hợp đồng trong Database sang Bảng Công nợ.",
            "synced_count": synced_count,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/import-sheet3")
async def import_sheet3_endpoint():
    """Disabled endpoint: Sheet 3 external import is discontinued to preserve strict database source of truth."""
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": "Tính năng nhập từ Sheet 3 đã dừng hoạt động. Bảng công nợ hiện được lấy trực tiếp 100% từ dữ liệu Hợp đồng trong Database.",
        }
    )


@router.get("/export-excel")
async def export_excel_endpoint(
    customer: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
):
    """Download live-formula Excel spreadsheet matching 1:1 Sheet 3 format."""
    try:
        excel_bytes = export_receivables_excel(
            customer=customer,
            status=status,
            search=search,
            overdue_only=overdue_only,
        )
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Bang_Theo_Doi_Cong_No_Du_An_{now_str}.xlsx"
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


def _clean_param(val: Any) -> Optional[str]:
    if val is None or not isinstance(val, str):
        return None
    s = val.strip()
    return s if s and s != "all" else None


def _clean_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ["true", "1", "yes"]
    return False


@router.get("/export-word")
async def export_word_endpoint(
    customer: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
):
    """Download executive Word report (.docx) conforming to Boss's 3 rules."""
    try:
        data = prepare_receivables_management_data(
            customer=_clean_param(customer),
            status=_clean_param(status),
            search=_clean_param(search),
            overdue_only=_clean_bool(overdue_only),
        )
        docx_bytes = generate_receivables_word_report(data)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Bao_Cao_Cong_No_Dieu_Hanh_{now_str}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/export-ppt")
async def export_ppt_endpoint(
    customer: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
):
    """Download executive PowerPoint presentation (.pptx) conforming to Boss's 3 rules."""
    try:
        data = prepare_receivables_management_data(
            customer=_clean_param(customer),
            status=_clean_param(status),
            search=_clean_param(search),
            overdue_only=_clean_bool(overdue_only),
        )
        pptx_bytes = generate_receivables_ppt_presentation(data)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Bao_Cao_Cong_No_Slide_Dieu_Hanh_{now_str}.pptx"
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/weekly-comparison")
async def get_weekly_comparison_endpoint(
    prev_date: Optional[str] = Query(None, description="Mốc cuối tuần trước (YYYY-MM-DD)"),
    curr_date: Optional[str] = Query(None, description="Mốc cuối tuần này (YYYY-MM-DD)"),
    customer: Optional[str] = Query(None, description="Lọc theo khách hàng"),
    contract: Optional[str] = Query(None, description="Lọc theo mã hợp đồng"),
    data_source: str = Query("db", description="Nguồn dữ liệu: 'db' (gốc), 'sample' (mẫu), hoặc 'upload'"),
    upload_id: Optional[str] = Query(None, description="ID của file upload độc lập"),
):
    """Retrieve side-by-side weekly debt comparison data from DB, Sample JSON, or Uploaded file."""
    try:
        data = get_weekly_comparison_data(
            prev_date=_clean_param(prev_date),
            curr_date=_clean_param(curr_date),
            customer=_clean_param(customer),
            contract=_clean_param(contract),
            data_source=_clean_param(data_source) or "db",
            upload_id=_clean_param(upload_id),
        )
        return data
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi so sánh công nợ tuần: {str(e)}"})


@router.post("/upload-custom-chart")
async def upload_custom_chart_endpoint(
    file: UploadFile = File(...),
    prev_date: Optional[str] = Form(None),
    curr_date: Optional[str] = Form(None),
):
    """Upload an external Excel (.xlsx/.xls) or JSON file from another department to generate standalone comparison charts
    WITHOUT touching, overwriting, or altering the main company database.
    """
    try:
        filename = file.filename or "uploaded_receivables.xlsx"
        file_bytes = await file.read()
        if not file_bytes:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Tập tin rỗng."})

        upload_id, items = register_custom_receivables_file(file_bytes, filename)
        comp_data = get_weekly_comparison_data(
            prev_date=_clean_param(prev_date),
            curr_date=_clean_param(curr_date),
            data_source="upload",
            upload_id=upload_id,
        )

        return {
            "status": "success",
            "message": f"Tải lên và xử lý thành công file '{filename}' ({len(items)} mốc thanh toán).",
            "upload_id": upload_id,
            "filename": filename,
            "total_items": len(items),
            "comparison_data": comp_data,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi xử lý tập tin độc lập: {str(e)}"})


class WeeklySnapshotRequest(BaseModel):
    snapshot_date: Optional[str] = None
    note: Optional[str] = None


@router.post("/weekly-snapshot")
async def save_weekly_snapshot_endpoint(payload: Optional[WeeklySnapshotRequest] = None):
    """Capture snapshot of current receivables for weekly historical comparison."""
    try:
        s_date = payload.snapshot_date if payload else None
        s_note = payload.note if payload else None
        saved_count = save_weekly_snapshot(snapshot_date=s_date, note=s_note)
        return {
            "status": "success",
            "message": f"Đã lưu chốt thành công snapshot cho {saved_count} đợt công nợ.",
            "saved_count": saved_count,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi lưu snapshot tuần: {str(e)}"})


@router.get("/{item_id}")
async def get_receivable_detail_endpoint(item_id: int):
    """Get single receivable details."""
    item = get_receivable_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy mốc công nợ.")
    return {"status": "success", "receivable": item}


class InlineUpdateRequest(BaseModel):
    field: str
    value: Any


@router.post("")
async def create_receivable_endpoint(payload: ReceivableCreateRequest):
    """Create a new receivable milestone."""
    try:
        data = payload.dict()
        new_id = create_receivable(data)
        item = get_receivable_by_id(new_id)
        return {
            "status": "success",
            "message": "Đã thêm mới đợt thanh toán thành công.",
            "receivable": item,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.put("/{item_id}")
async def update_receivable_endpoint(item_id: int, payload: ReceivableUpdateRequest):
    """Update full receivable details including tax, dates, amounts, and notes."""
    try:
        data = payload.dict(exclude_unset=True)
        success = update_receivable(item_id, data)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy mốc công nợ.")
        updated = get_receivable_by_id(item_id)
        return {
            "status": "success",
            "message": "Đã cập nhật mốc công nợ thành công.",
            "receivable": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.patch("/{item_id}/inline")
async def update_inline_field_endpoint(item_id: int, payload: InlineUpdateRequest):
    """Fast inline edit of single field: vat_rate, due_date, customer_promised_date, paid_date, received_amount, doc_status."""
    try:
        field = payload.field
        val = payload.value
        update_dict: Dict[str, Any] = {}

        if field == "vat_rate":
            update_dict["vat_rate"] = float(val or 0.0)
        elif field in ["due_date", "customer_promised_date", "paid_date", "doc_status"]:
            clean_str = str(val).strip() if val and str(val).strip() not in ["", "-", "null", "undefined"] else None
            update_dict[field] = clean_str
            if field == "paid_date":
                cur_item = get_receivable_by_id(item_id)
                gross = float((cur_item or {}).get("gross_amount") or 0.0)
                rec = float((cur_item or {}).get("received_amount") or 0.0)
                due = (cur_item or {}).get("due_date")
                from app.services.receivables_service import determine_collection_status
                if clean_str:
                    update_dict["collection_status"] = "PAID"
                    if rec <= 0 and gross > 0:
                        update_dict["received_amount"] = gross
                        update_dict["remaining_debt"] = 0.0
                else:
                    # Nếu xóa ngày thanh toán, revert số tiền đã nhận nếu trước đó đã nhận đủ
                    if rec >= gross and gross > 0:
                        update_dict["received_amount"] = 0.0
                        update_dict["remaining_debt"] = gross
                        rec = 0.0
                    update_dict["collection_status"] = determine_collection_status(rec, gross, due)
        elif field == "received_amount":
            update_dict["received_amount"] = float(val or 0.0)
        elif field == "net_amount":
            update_dict["net_amount"] = float(val or 0.0)
        elif field == "gross_amount":
            update_dict["gross_amount"] = float(val or 0.0)
        else:
            update_dict[field] = val

        success = update_receivable(item_id, update_dict)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy mốc công nợ.")
        updated = get_receivable_by_id(item_id)
        return {
            "status": "success",
            "message": f"Đã cập nhật {field} thành công.",
            "receivable": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.delete("/{item_id}")
async def delete_receivable_endpoint(item_id: int):
    """Delete a single receivable milestone."""
    success = delete_receivable(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy mốc công nợ để xóa.")
    return {"status": "success", "message": "Đã xóa mốc công nợ thành công."}


@router.post("/ai-extract")
async def ai_extract_receivables_endpoint(
    raw_text: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Extract receivable milestones from unstructured text and/or attached file via Gemini AI."""
    try:
        file_bytes = await file.read() if file else None
        filename = file.filename if file else None
        content_type = file.content_type if file else None

        result = parse_receivables_ai(
            raw_text=raw_text,
            preferred_model=model_name,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi AI trích xuất công nợ: {str(e)}"})


@router.post("/bulk-save")
async def bulk_save_receivables_endpoint(payload: Dict[str, Any]):
    """Bulk save AI extracted receivable milestones into database."""
    try:
        items = payload.get("items", [])
        if not items:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Không có danh sách mốc công nợ để lưu."})

        saved_ids = []
        for it in items:
            # Note: contract_code is completely OPTIONAL (can be None/empty for standalone receivables)
            c_code = it.get("contract_code")
            if c_code and str(c_code).strip() in ["", "-", "null", "None"]:
                it["contract_code"] = None
            nid = create_receivable(it)
            saved_ids.append(nid)

        stats = get_receivables_stats()
        return {
            "status": "success",
            "message": f"Đã lưu thành công {len(saved_ids)} đợt công nợ vào hệ thống.",
            "saved_count": len(saved_ids),
            "stats": stats,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi lưu danh mục công nợ: {str(e)}"})



