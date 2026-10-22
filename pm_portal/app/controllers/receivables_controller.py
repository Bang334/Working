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
from app.services.receivables_ai_service import get_ai_receivables_digest
from app.services.receivables_excel_service import export_receivables_excel
from app.services.receivables_service import (
    create_receivable,
    delete_receivable,
    get_receivable_by_id,
    get_receivables_stats,
    import_receivables_from_sheet3,
    list_receivables,
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
                if clean_str:
                    update_dict["collection_status"] = "PAID"
                else:
                    # Nếu xóa ngày thanh toán, tự tính lại trạng thái
                    cur_item = get_receivable_by_id(item_id)
                    gross = float((cur_item or {}).get("gross_amount") or 0.0)
                    rec = float((cur_item or {}).get("received_amount") or 0.0)
                    due = (cur_item or {}).get("due_date")
                    from app.services.receivables_service import determine_collection_status
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
