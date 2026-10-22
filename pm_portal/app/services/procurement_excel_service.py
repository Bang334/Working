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
    """Generate a high-fidelity, professional Excel workbook from procurement orders with AutoFilter and anti-clipping."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Theo Dõi Mua Hàng"

    # Setup page and gridlines
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    font_family = "Microsoft JhengHei"
    title_font = Font(name=font_family, size=15, bold=True, color="1F4E79")
    company_font = Font(name=font_family, size=10, bold=True, color="475569")
    summary_meta_font = Font(name=font_family, size=9.5, bold=False, color="1E3A8A")
    header_font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    data_font = Font(name=font_family, size=9.5, bold=False, color="1E293B")
    bold_data_font = Font(name=font_family, size=9.5, bold=True, color="1E293B")
    notes_font = Font(name=font_family, size=9, italic=True, color="475569")
    total_font = Font(name=font_family, size=10.5, bold=True, color="1F4E79")

    # Header and stripe fills
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    stripe_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    meta_box_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    total_fill = PatternFill(start_color="E6F0FA", end_color="E6F0FA", fill_type="solid")
    
    # Status fills (màu pastel cao cấp tương phản rõ nét)
    delivered_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    delivered_font = Font(name=font_family, size=9.5, bold=True, color="1E4620")

    in_transit_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    in_transit_font = Font(name=font_family, size=9.5, bold=True, color="8A6D3B")

    delayed_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    delayed_font = Font(name=font_family, size=9.5, bold=True, color="A61C1C")

    pending_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    pending_font = Font(name=font_family, size=9.5, bold=True, color="475569")

    # Borders
    thin_side = Side(style="thin", color="CBD5E1")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    
    header_border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=Side(style="medium", color="0F2D4A")
    )

    total_border = Border(
        left=thin_side,
        right=thin_side,
        top=Side(style="thin", color="1F4E79"),
        bottom=Side(style="double", color="1F4E79")
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center")

    # Stats Calculation
    total_count = len(orders)
    delivered_count = sum(1 for o in orders if o.get("delivery_status") == "DELIVERED")
    in_transit_count = sum(1 for o in orders if o.get("delivery_status") == "IN_TRANSIT")
    delayed_count = sum(1 for o in orders if o.get("delivery_status") == "DELAYED")
    pending_count = sum(1 for o in orders if o.get("delivery_status") == "PENDING")

    # 1. Table Column Headers (Bắt đầu trực tiếp từ Row 1, giữ thuần túy table)
    headers = [
        "STT\n序號",
        "Dự án\n專案名稱",
        "Hạng mục\n項目類別",
        "Tên vật tư / Thiết bị & Quy cách\n物料 / 設備規格",
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

    header_row = 1
    # Chiều cao header 42pt đảm bảo 100% không bị cắt lẹm mép chữ tiếng Việt và tiếng Trung
    ws.row_dimensions[header_row].height = 42

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = header_border

    # 2. Freeze Panes: Ghim cố định 2 cột đầu STT & Dự án và Hàng tiêu đề 1
    ws.freeze_panes = "C2"

    # 3. Populate Data Rows (Bắt đầu từ Row 2)
    current_row = 2
    total_qty = 0.0

    for idx, o in enumerate(orders):
        is_stripe = (idx % 2 == 1)

        # Trích xuất dữ liệu
        stt_val = o.get("order_no") or (idx + 1)
        proj_name = o.get("project_name", "") or "-"
        cat_name = o.get("category", "") or "-"
        
        # Ghép tên thiết bị và quy cách nếu có
        item_raw = o.get("item_name", "") or ""
        desc_raw = o.get("material_desc", "") or ""
        if desc_raw and desc_raw != "-":
            full_item_text = f"{item_raw}\n[Quy cách: {desc_raw}]"
        else:
            full_item_text = item_raw

        qty = float(o.get("quantity") or 1.0)
        total_qty += qty
        unit = o.get("unit", "Bộ") or "Bộ"
        customer = o.get("customer_company", "") or "-"
        supplier = o.get("supplier_name", "") or "-"
        order_date = o.get("order_date") or "-"
        eta_date = o.get("eta_date") or "-"
        actual_date = o.get("actual_delivery_date") or "-"
        payment_status = o.get("supplier_payment_status") or "-"
        status_label = o.get("delivery_status_label") or get_status_label(o.get("delivery_status", "PENDING"))
        notes = o.get("shipping_notes") or "-"

        # Tính toán chiều cao dòng tự động chống cắt chữ
        text_lines = max(
            len(str(proj_name).split("\n")),
            len(str(full_item_text).split("\n")),
            len(str(payment_status).split("\n")),
            len(str(notes).split("\n")),
            1
        )
        # Nếu chữ quá dài thì cộng thêm dòng
        if len(str(full_item_text)) > 70 or len(str(notes)) > 60:
            text_lines = max(text_lines, 2)
        if len(str(full_item_text)) > 140:
            text_lines = max(text_lines, 3)

        calculated_height = max(26, min(120, text_lines * 19 + 6))
        ws.row_dimensions[current_row].height = calculated_height

        d_status = o.get("delivery_status", "PENDING")

        row_cells = [
            (stt_val, align_center, bold_data_font),
            (proj_name, align_left, bold_data_font),
            (cat_name, align_center, data_font),
            (full_item_text, align_left, data_font),
            (qty, align_center, bold_data_font),
            (unit, align_center, data_font),
            (customer, align_left, data_font),
            (supplier, align_left, bold_data_font),
            (order_date, align_center, data_font),
            (eta_date, align_center, bold_data_font),
            (actual_date, align_center, data_font),
            (payment_status, align_left, data_font),
            (status_label, align_center, bold_data_font),
            (notes, align_left, notes_font),
        ]

        for col_idx, (val, alignment, font) in enumerate(row_cells, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font
            cell.alignment = alignment
            cell.border = thin_border

            # Phối màu cột Trạng thái giao và Zebra stripe
            if col_idx == 13:
                if d_status == "DELIVERED":
                    cell.fill = delivered_fill
                    cell.font = delivered_font
                elif d_status == "IN_TRANSIT":
                    cell.fill = in_transit_fill
                    cell.font = in_transit_font
                elif d_status == "DELAYED":
                    cell.fill = delayed_fill
                    cell.font = delayed_font
                elif is_stripe:
                    cell.fill = stripe_fill
                    cell.font = pending_font
                else:
                    cell.fill = pending_fill
                    cell.font = pending_font
            elif is_stripe:
                cell.fill = stripe_fill

        current_row += 1

    last_data_row = current_row - 1

    # 5. Row Tổng Cộng (Summary Row) với viền đôi kế toán
    if orders:
        total_row = current_row
        ws.row_dimensions[total_row].height = 30
        
        ws.merge_cells(f"A{total_row}:D{total_row}")
        total_label_cell = ws.cell(row=total_row, column=1, value="TỔNG CỘNG / 合計")
        total_label_cell.font = total_font
        total_label_cell.alignment = align_center

        # Công thức tính tổng số lượng
        qty_total_cell = ws.cell(row=total_row, column=5, value=f"=SUM(E2:E{last_data_row})")
        qty_total_cell.font = total_font
        qty_total_cell.alignment = align_center

        # Thông tin tổng kết ở cột 13 & 14
        ws.cell(row=total_row, column=6, value="Bộ").alignment = align_center
        ws.cell(row=total_row, column=13, value=f"Đã giao: {delivered_count}/{total_count}").alignment = align_center
        completion_pct = round((delivered_count / total_count * 100), 1) if total_count > 0 else 0
        ws.cell(row=total_row, column=14, value=f"Tỷ lệ giao: {completion_pct}%").alignment = align_left

        for c in range(1, 15):
            cell = ws.cell(row=total_row, column=c)
            cell.font = total_font
            cell.fill = total_fill
            cell.border = total_border

    # 6. KÍCH HOẠT AUTOFILTER TRÊN TOÀN BỘ 14 CỘT TIÊU ĐỀ
    if last_data_row >= header_row:
        ws.auto_filter.ref = f"A{header_row}:N{last_data_row}"

    # 7. Auto-adjust Column Widths (Độ rộng chuẩn xác, không bị cắt lẹm bất kỳ ký tự nào)
    col_widths = {
        1: 7,   # STT
        2: 24,  # Dự án
        3: 18,  # Hạng mục
        4: 42,  # Tên vật tư / Thiết bị & Quy cách
        5: 11,  # Số lượng
        6: 9,   # ĐVT
        7: 24,  # Khách hàng
        8: 20,  # Nhà cung cấp
        9: 16,  # Ngày đặt hàng
        10: 16, # ETA dự kiến
        11: 18, # Ngày giao thực tế
        12: 28, # Thanh toán NCC
        13: 22, # Trạng thái giao
        14: 35, # Ghi chú vận chuyển / Rủi ro
    }
    for col_idx, width in col_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

