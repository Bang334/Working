# -*- coding: utf-8 -*-
"""Excel parser and exporter service for Procurement Orders."""

import datetime
import io
import re
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.services.procurement_service import format_delivery_status, get_status_label


def _clean_str(val: Any) -> Optional[str]:
    """Clean string values and remove trailing newlines."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _format_date(val: Any) -> Optional[str]:
    """Format various date types to YYYY-MM-DD."""
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.strftime("%Y-%m-%d")
    
    val_str = str(val).strip()
    if not val_str or val_str in ("..", "None", "#VALUE!"):
        return None
    
    # Try match YYYY-MM-DD or DD/MM/YYYY
    match_iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", val_str)
    if match_iso:
        y, m, d = match_iso.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    
    match_vn = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", val_str)
    if match_vn:
        d, m, y = match_vn.groups()
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    return val_str


def parse_procurement_excel(file_bytes_or_path: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse uploaded Excel file. Specifically locates Sheet 2 'Theo Dõi Mua Hàng'
    or finds the sheet with procurement columns.
    """
    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes_or_path), data_only=True)
    else:
        wb = openpyxl.load_workbook(file_bytes_or_path, data_only=True)

    target_ws = None
    target_sheet_name = ""

    # Priority 1: Exact or substring match for "Theo Dõi Mua Hàng" or "采购"
    for name in wb.sheetnames:
        clean_name = name.lower()
        if "mua hàng" in clean_name or "mua hang" in clean_name or "采购" in clean_name or "theo dõi mua" in clean_name:
            target_ws = wb[name]
            target_sheet_name = name
            break

    # Priority 2: Sheet 2 if at least 2 sheets exist
    if target_ws is None and len(wb.sheetnames) >= 2:
        target_ws = wb[wb.sheetnames[1]]
        target_sheet_name = wb.sheetnames[1]

    # Priority 3: First sheet
    if target_ws is None:
        target_ws = wb.active
        target_sheet_name = wb.sheetnames[0]

    # Find header row (usually Row 1 or 2 or 3)
    header_row_idx = 1
    found_header = False
    for r in range(1, min(target_ws.max_row + 1, 10)):
        row_vals = [str(target_ws.cell(r, c).value or "").lower() for c in range(1, 15)]
        if any("vật tư" in v or "thiết bị" in v or "nhà cung cấp" in v or "dự án" in v for v in row_vals):
            header_row_idx = r
            found_header = True
            break

    data_start_row = header_row_idx + 1 if found_header else 2
    orders: List[Dict[str, Any]] = []

    for r in range(data_start_row, target_ws.max_row + 1):
        # Column mapping based on standard Sheet 2:
        # Col 1: STT
        # Col 2: Dự án
        # Col 3: Hạng mục
        # Col 4: Tên vật tư / Thiết bị
        # Col 5: Số lượng
        # Col 6: Công ty KH
        # Col 7: Nhà cung cấp
        # Col 8: Ngày đặt hàng
        # Col 9: Ngày giao dự kiến (ETA)
        # Col 10: Ngày giao thực tế
        # Col 11: Vật liệu / Quy cách
        # Col 12: Tình trạng thanh toán NCC
        # Col 13: Trạng thái giao hàng
        # Col 14: Ghi chú vận chuyển / Rủi ro
        raw_vals = [target_ws.cell(r, c).value for c in range(1, 15)]
        if not any(v is not None for v in raw_vals):
            continue

        item_name = _clean_str(raw_vals[3])
        project_name = _clean_str(raw_vals[1])
        supplier = _clean_str(raw_vals[6])

        # Skip rows without project, item, and supplier
        if not item_name and not project_name and not supplier:
            continue

        # If item_name is missing, try use category or project
        if not item_name:
            item_name = _clean_str(raw_vals[2]) or "Vật tư phụ / Thiết bị"

        stt_val = raw_vals[0]
        try:
            order_no = int(float(stt_val)) if stt_val is not None else len(orders) + 1
        except Exception:
            order_no = len(orders) + 1

        qty_val = raw_vals[4]
        try:
            quantity = float(qty_val) if qty_val is not None else 1.0
        except Exception:
            quantity = 1.0

        order_date = _format_date(raw_vals[7])
        eta_date = _format_date(raw_vals[8])
        actual_date = _format_date(raw_vals[9])
        shipping_notes = _clean_str(raw_vals[13])
        delivery_raw = _clean_str(raw_vals[12])

        deliv_status = format_delivery_status(delivery_raw, eta_date, actual_date, shipping_notes)

        order_obj = {
            "order_no": order_no,
            "project_name": project_name or "Dự án chung",
            "category": _clean_str(raw_vals[2]),
            "item_name": item_name,
            "quantity": quantity,
            "unit": "Bộ",
            "customer_company": _clean_str(raw_vals[5]),
            "supplier_name": supplier or "NCC",
            "order_date": order_date,
            "eta_date": eta_date,
            "actual_delivery_date": actual_date,
            "material_desc": _clean_str(raw_vals[10]),
            "supplier_payment_status": _clean_str(raw_vals[11]),
            "delivery_status": deliv_status,
            "delivery_status_label": get_status_label(deliv_status),
            "shipping_notes": shipping_notes,
            "unit_price": 0.0,
            "total_amount": 0.0,
            "currency": "VND",
        }
        orders.append(order_obj)

    metadata = {
        "sheet_name": target_sheet_name,
        "total_parsed": len(orders),
        "total_sheets": len(wb.sheetnames),
        "all_sheets": wb.sheetnames,
    }

    return orders, metadata


def export_procurement_excel(orders: List[Dict[str, Any]]) -> io.BytesIO:
    """Generate a high-fidelity, professional Excel workbook from procurement orders."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Theo Dõi Mua Hàng"

    # Setup page and gridlines
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    font_family = "Microsoft JhengHei"
    title_font = Font(name=font_family, size=14, bold=True, color="1F4E79")
    sub_font = Font(name=font_family, size=11, bold=True, color="595959")
    header_font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    data_font = Font(name=font_family, size=10, bold=False)
    bold_data_font = Font(name=font_family, size=10, bold=True)
    notes_font = Font(name=font_family, size=9, italic=True, color="555555")

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    stripe_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    
    # Status fills
    delivered_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    in_transit_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    delayed_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center")

    # Title Block
    ws.merge_cells("A1:N1")
    ws["A1"] = "CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"
    ws["A1"].font = sub_font
    ws["A1"].alignment = align_left

    ws.merge_cells("A2:N2")
    ws["A2"] = "BẢNG THEO DÕI ĐƠN MUA HÀNG VẬT TƯ & NHÀ CUNG CẤP (PROCUREMENT TRACKER)"
    ws["A2"].font = title_font
    ws["A2"].alignment = align_left

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    ws.merge_cells("A3:N3")
    ws["A3"] = f"Thời điểm xuất báo cáo: {now_str} · Tổng số đơn: {len(orders)} hạng mục"
    ws["A3"].font = notes_font
    ws["A3"].alignment = align_left

    # Table Headers
    headers = [
        "STT\n序號",
        "Dự án\n專案",
        "Hạng mục\n項目類別",
        "Tên vật tư / Thiết bị\n物料 / 設備名稱",
        "Số lượng\n數量",
        "ĐVT\n單位",
        "Khách hàng\n客戶公司",
        "Nhà cung cấp\n供應商",
        "Ngày đặt hàng\n下單日期",
        "ETA dự kiến\n預計交貨日",
        "Ngày giao thực tế\n實際交貨日",
        "Thanh toán NCC\n供應商付款",
        "Trạng thái giao\n交貨狀態",
        "Ghi chú vận chuyển / Rủi ro\n運輸備註 / 風險",
    ]

    header_row = 5
    ws.row_dimensions[header_row].height = 30
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = thin_border

    # Freeze panes below headers
    ws.freeze_panes = "A6"

    # Populate Data Rows
    current_row = header_row + 1
    for idx, o in enumerate(orders):
        ws.row_dimensions[current_row].height = 26
        is_stripe = (idx % 2 == 1)

        row_cells = [
            (idx + 1, align_center, bold_data_font),
            (o.get("project_name", ""), align_left, bold_data_font),
            (o.get("category", "") or "-", align_center, data_font),
            (o.get("item_name", ""), align_left, data_font),
            (o.get("quantity", 1), align_center, bold_data_font),
            (o.get("unit", "Bộ"), align_center, data_font),
            (o.get("customer_company", "") or "-", align_left, data_font),
            (o.get("supplier_name", ""), align_left, bold_data_font),
            (o.get("order_date") or "-", align_center, data_font),
            (o.get("eta_date") or "-", align_center, bold_data_font),
            (o.get("actual_delivery_date") or "-", align_center, data_font),
            (o.get("supplier_payment_status") or "-", align_left, data_font),
            (o.get("delivery_status_label") or get_status_label(o.get("delivery_status", "PENDING")), align_center, bold_data_font),
            (o.get("shipping_notes") or "-", align_left, notes_font),
        ]

        d_status = o.get("delivery_status", "PENDING")

        for col_idx, (val, alignment, font) in enumerate(row_cells, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font
            cell.alignment = alignment
            cell.border = thin_border
            
            # Row stripe or status badge styling
            if col_idx == 13:  # Status column
                if d_status == "DELIVERED":
                    cell.fill = delivered_fill
                elif d_status == "IN_TRANSIT":
                    cell.fill = in_transit_fill
                elif d_status == "DELAYED":
                    cell.fill = delayed_fill
                elif is_stripe:
                    cell.fill = stripe_fill
            elif is_stripe:
                cell.fill = stripe_fill

        current_row += 1

    # Auto-adjust column widths
    col_widths = {
        1: 7,   # STT
        2: 22,  # Dự án
        3: 16,  # Hạng mục
        4: 38,  # Tên vật tư
        5: 10,  # Số lượng
        6: 8,   # ĐVT
        7: 24,  # Khách hàng
        8: 18,  # NCC
        9: 14,  # Ngày đặt
        10: 14, # ETA
        11: 15, # Giao thực tế
        12: 24, # Thanh toán NCC
        13: 20, # Trạng thái giao
        14: 30, # Ghi chú
    }
    for col_idx, width in col_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
