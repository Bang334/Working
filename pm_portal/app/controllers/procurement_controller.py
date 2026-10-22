# -*- coding: utf-8 -*-
"""Procurement controller handling API requests for PO tracking, AI extraction, and Excel."""

import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from pydantic import BaseModel

from app.models.procurement_models import (
    ProcurementAIParseRequest,
    ProcurementCreateRequest,
    ProcurementUpdateRequest,
)
from app.services.procurement_ai_service import parse_procurement_ai
from app.services.procurement_excel_service import export_procurement_excel, parse_procurement_excel
from app.services.procurement_service import (
    bulk_import_procurement_orders,
    create_procurement_order,
    delete_all_procurement_orders,
    delete_procurement_order,
    get_procurement_order,
    get_procurement_stats,
    list_procurement_orders,
    update_procurement_order,
    update_procurement_order_notes,
    update_procurement_order_status,
)

class QuickNotesUpdateRequest(BaseModel):
    shipping_notes: Optional[str] = ""

class QuickStatusUpdateRequest(BaseModel):
    delivery_status: str

router = APIRouter(prefix="/api/v1/procurement", tags=["Procurement & PO Tracker"])


@router.get("/orders")
async def get_orders_endpoint(
    status: Optional[str] = Query(None, description="Lọc trạng thái: all, delivered, in_transit, delayed, pending"),
    supplier: Optional[str] = Query(None, description="Lọc nhà cung cấp"),
    project: Optional[str] = Query(None, description="Lọc dự án"),
    search: Optional[str] = Query(None, description="Từ khóa tìm kiếm"),
):
    """Retrieve filtered procurement orders list."""
    try:
        orders = list_procurement_orders(
            status=status,
            supplier=supplier,
            project=project,
            search=search,
        )
        stats = get_procurement_stats()
        return {
            "status": "success",
            "total": len(orders),
            "orders": orders,
            "stats": stats,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi lấy danh sách đơn mua hàng: {str(e)}"},
        )


@router.get("/stats")
async def get_stats_endpoint():
    """Retrieve summary KPI stats."""
    try:
        stats = get_procurement_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi tính toán chỉ số: {str(e)}"},
        )


@router.get("/orders/{order_id}")
async def get_order_endpoint(order_id: int):
    """Retrieve single order details."""
    order = get_procurement_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn mua hàng.")
    return {"status": "success", "order": order}


@router.post("/orders")
async def create_order_endpoint(payload: ProcurementCreateRequest):
    """Create a new procurement order."""
    try:
        order_id = create_procurement_order(payload.dict())
        new_order = get_procurement_order(order_id)
        return {
            "status": "success",
            "message": "Đã thêm đơn mua hàng thành công.",
            "order_id": order_id,
            "order": new_order,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi tạo đơn mua hàng: {str(e)}"},
        )


@router.put("/orders/{order_id}")
async def update_order_endpoint(order_id: int, payload: ProcurementUpdateRequest):
    """Update an existing procurement order."""
    try:
        success = update_procurement_order(order_id, payload.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng cần cập nhật.")
        updated = get_procurement_order(order_id)
        return {
            "status": "success",
            "message": "Đã cập nhật đơn mua hàng thành công.",
            "order": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi cập nhật: {str(e)}"},
        )


@router.patch("/orders/{order_id}/notes")
async def update_order_notes_endpoint(order_id: int, payload: QuickNotesUpdateRequest):
    """Direct inline update of shipping notes/risks without modal."""
    try:
        success = update_procurement_order_notes(order_id, payload.shipping_notes or "")
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng cần cập nhật.")
        updated = get_procurement_order(order_id)
        return {
            "status": "success",
            "message": "Đã lưu ghi chú rủi ro thành công.",
            "order": updated,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi cập nhật ghi chú: {str(e)}"},
        )


@router.patch("/orders/{order_id}/status")
async def update_order_status_endpoint(order_id: int, payload: QuickStatusUpdateRequest):
    """Direct inline update of delivery status dropdown without modal."""
    try:
        success = update_procurement_order_status(order_id, payload.delivery_status)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng cần cập nhật.")
        updated = get_procurement_order(order_id)
        stats = get_procurement_stats()
        return {
            "status": "success",
            "message": "Đã cập nhật trạng thái đơn hàng thành công.",
            "order": updated,
            "stats": stats,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi cập nhật trạng thái: {str(e)}"},
        )


@router.delete("/orders/{order_id}")
async def delete_order_endpoint(order_id: int):
    """Delete a single procurement order."""
    try:
        success = delete_procurement_order(order_id)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng cần xóa.")
        return {"status": "success", "message": "Đã xóa đơn mua hàng thành công."}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi xóa đơn: {str(e)}"},
        )


@router.delete("/orders")
async def clear_all_orders_endpoint():
    """Clear all procurement orders table."""
    try:
        count = delete_all_procurement_orders()
        return {"status": "success", "message": f"Đã xóa toàn bộ {count} đơn hàng trong hệ thống."}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi dọn dẹp dữ liệu: {str(e)}"},
        )


@router.post("/upload-excel")
async def upload_excel_endpoint(
    file: UploadFile = File(...),
    overwrite: bool = Form(False),
):
    """Upload and import Excel file (e.g. QLDA_TRANG_PM_2026 (1).xlsx)."""
    try:
        content = await file.read()
        parsed_orders, metadata = parse_procurement_excel(content)

        if not parsed_orders:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "warning",
                    "message": "Không tìm thấy dữ liệu đơn mua hàng nào trong file Excel vừa tải lên.",
                    "metadata": metadata,
                },
            )

        imported_count = bulk_import_procurement_orders(parsed_orders, overwrite=overwrite)
        stats = get_procurement_stats()

        return {
            "status": "success",
            "message": f"Đã tải lên và nhập thành công {imported_count} đơn mua hàng từ sheet '{metadata.get('sheet_name')}'.",
            "imported_count": imported_count,
            "metadata": metadata,
            "stats": stats,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi xử lý file Excel: {str(e)}"},
        )


@router.get("/export-excel")
async def export_excel_endpoint(
    status: Optional[str] = Query(None),
    supplier: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Export procurement orders to executive Excel file."""
    try:
        orders = list_procurement_orders(
            status=status,
            supplier=supplier,
            project=project,
            search=search,
        )
        stream = export_procurement_excel(orders)
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"THEO_DOI_MUA_HANG_HONG_MING_{date_str}.xlsx"

        return Response(
            content=stream.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi xuất file Excel: {str(e)}"},
        )


@router.post("/ai-extract")
async def ai_extract_endpoint(
    raw_text: Optional[str] = Form(None),
    model_name: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Extract procurement orders from unstructured supplier quotation, text and/or attached file via Gemini AI."""
    try:
        file_bytes = await file.read() if file else None
        filename = file.filename if file else None
        content_type = file.content_type if file else None

        result = parse_procurement_ai(
            raw_text=raw_text,
            preferred_model=model_name,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi AI trích xuất: {str(e)}"},
        )



@router.post("/bulk-save")
async def bulk_save_endpoint(payload: Dict[str, Any]):
    """Bulk save AI extracted items into SQLite database."""
    try:
        items = payload.get("items", [])
        if not items:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Không có danh sách mặt hàng để lưu."},
            )
        imported_count = bulk_import_procurement_orders(items, overwrite=False)
        stats = get_procurement_stats()
        return {
            "status": "success",
            "message": f"Đã lưu thành công {imported_count} đơn mua hàng vào hệ thống.",
            "imported_count": imported_count,
            "stats": stats,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi lưu danh mục: {str(e)}"},
        )
