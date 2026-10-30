"""Service to generate 100% template-perfect ECO PRIME Excel Quotations."""

from __future__ import annotations

import io
import math
import os
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Color, Font, PatternFill, Side

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.models.eco_prime_models import EcoPrimeItem, EcoPrimeQuotationData

ECO_PRIME_TEMPLATE_PATH = WORKING_DIR / "Bieu Mau" / "Mau_Goc_Bao_Gia_ECO_PRIME_Dong_Ho_Dien.xlsx"


def compute_cell_lines(text: str, col_width_chars: float) -> int:
    """Tính số dòng render thực tế chống cắt chữ tiếng Việt & chữ Hán 2-byte."""
    if not text:
        return 1
    paragraphs = str(text).split("\n")
    total_rendered = 0
    usable_width = max(col_width_chars - 2.5, 5.0)
    for p in paragraphs:
        if not p.strip():
            total_rendered += 1
            continue
        weight = 0.0
        for ch in p:
            code = ord(ch)
            if (
                (0x4E00 <= code <= 0x9FFF)
                or (0x3400 <= code <= 0x4DBF)
                or (0xF900 <= code <= 0xFAFF)
                or code > 1279
            ):
                weight += 1.95
            elif ch.isupper():
                weight += 1.2
            else:
                weight += 0.95
        lines_for_p = max(1, math.ceil(weight / usable_width))
        total_rendered += lines_for_p
    return max(1, total_rendered)


def copy_cell_style(src_cell, dst_cell):
    """Sao chép toàn bộ thuộc tính style của ô gốc."""
    if src_cell.has_style:
        dst_cell.font = copy(src_cell.font)
        dst_cell.border = copy(src_cell.border)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.number_format = copy(src_cell.number_format)
        dst_cell.protection = copy(src_cell.protection)
        dst_cell.alignment = copy(src_cell.alignment)


def generate_eco_prime_excel(
    quote_data: EcoPrimeQuotationData,
    save_to_disk: bool = True,
    custom_output_filename: Optional[str] = None
) -> Dict[str, Any]:
    """Tạo file Excel Báo Giá ECO PRIME chuẩn 1:1 từ phôi mẫu gốc bất biến."""
    template_path = ECO_PRIME_TEMPLATE_PATH
    if not template_path.is_file():
        # Fallback thử tìm ở thư mục cha
        fallback_path = WORKING_DIR / "Bieu Mau" / "Mau_Goc_Bao_Gia_ECO_PRIME_Dong_Ho_Dien.xlsx"
        if fallback_path.is_file():
            template_path = fallback_path
        else:
            raise FileNotFoundError(f"Không tìm thấy file phôi mẫu gốc: {template_path}")

    wb = openpyxl.load_workbook(str(template_path), data_only=False)
    sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]
    
    # Đổi tên sheet sang tên dự án hoặc 'ECO_PRIME'
    clean_cust = "".join(c for c in (quote_data.customer_name or "ECO_PRIME") if c.isalnum() or c in ("_", "-")).strip()
    ws.title = (clean_cust[:20] if clean_cust else "Quotation")

    if len(wb.sheetnames) > 1:
        for sname in wb.sheetnames:
            if sname != ws.title:
                del wb[sname]

    thin_border = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )

    # 1. Cập nhật thông tin Người mua & Đảm bảo merge F2:H2..F7:H7 liền mạch đến hết cột H
    for r in (3, 4, 5):
        for rng in list(ws.merged_cells.ranges):
            if rng.min_row == r and rng.min_col == 6 and rng.max_col == 7:
                ws.unmerge_cells(str(rng))
        ws.merge_cells(start_row=r, start_column=6, end_row=r, end_column=8)

    if quote_data.customer_name:
        ws["F2"].value = str(quote_data.customer_name).strip()
    if quote_data.customer_dept:
        ws["F3"].value = str(quote_data.customer_dept).strip()
    if quote_data.customer_contact:
        ws["F4"].value = str(quote_data.customer_contact).strip()
    ws["F5"].value = str(quote_data.customer_phone or "").strip()
    if quote_data.customer_address:
        ws["F6"].value = str(quote_data.customer_address).strip()
    ws["F7"].value = str(quote_data.customer_email or "").strip()

    # Kẻ viền (border) cho khối Người bán (C1:D7) và Người mua (E1:H7)
    for r in range(1, 8):
        for col_idx in range(3, 9):  # Cột C (3) đến cột H (8)
            ws.cell(r, col_idx).border = thin_border

    # 2. Cập nhật Tiêu đề Báo giá & Ngày tháng & Tỷ giá
    if quote_data.quote_title:
        ws["A9"].value = str(quote_data.quote_title).strip()
    
    quote_date_str = quote_data.quote_date or datetime.now().strftime("%d/%m/%Y")
    ws["A10"].value = f"報價日期 Ngày báo giá: {quote_date_str}"
    
    if quote_data.project_solution:
        ws["A12"].value = str(quote_data.project_solution).strip()
    
    ex_rate = quote_data.exchange_rate if quote_data.exchange_rate > 0 else 26130.0
    ws["H12"].value = ex_rate

    # 3. Điền các dòng hạng mục thiết bị
    items = quote_data.items
    num_items = len(items)
    orig_num_items = 7
    diff = num_items - orig_num_items

    if diff > 0:
        ws.insert_rows(20, amount=diff)
        for i in range(diff):
            r = 20 + i
            for col in range(1, 16):
                src = ws.cell(19, col)
                dst = ws.cell(r, col)
                copy_cell_style(src, dst)
    elif diff < 0:
        # Nếu ít hơn 7 dòng, xóa bớt
        ws.delete_rows(13 + num_items, amount=abs(diff))

    thin_border = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )
    font_item_black = Font(name="Times New Roman", size=11, bold=False, color="000000")

    # Xác định các dòng sau bảng sản phẩm
    r_empty = 13 + num_items
    r_subtotal = r_empty + 1
    r_vat = r_subtotal + 1
    r_total = r_vat + 1
    r_sign_title = r_total + 1
    r_sign_box = r_sign_title + 1
    r_term2 = r_sign_box + 1
    r_term3 = r_term2 + 1

    # Điền từng dòng sản phẩm
    for idx, item in enumerate(items):
        r = 13 + idx
        ws.cell(r, 1).value = item.stt or (idx + 1)
        ws.cell(r, 2).value = item.name or ""
        ws.cell(r, 3).value = item.category or ""
        ws.cell(r, 4).value = item.desc or ""
        ws.cell(r, 5).value = item.qty
        
        # Cột F (Đơn giá bán USD): Để None cho Sếp điền nếu chưa có giá
        ws.cell(r, 6).value = item.unit_price_usd if item.unit_price_usd is not None else None
        
        # Cột G (Thành tiền USD): =E*F
        ws.cell(r, 7).value = f"=E{r}*F{r}"
        
        # Cột H (Thành tiền VND): =G*H$12
        ws.cell(r, 8).value = f"=G{r}*H$12"
        
        # Cột J:O (Bảng giá vốn nội bộ)
        ws.cell(r, 10).value = item.unit_cost_usd if item.unit_cost_usd is not None else None
        ws.cell(r, 11).value = item.tax_rate
        ws.cell(r, 12).value = f"=J{r}*(1+K{r})"
        ws.cell(r, 13).value = f"=L{r}*E{r}"
        ws.cell(r, 14).value = f"=F{r}-L{r}"
        ws.cell(r, 15).value = f"=G{r}-M{r}"

        # Đảm bảo viền thin và font chữ màu đen chuẩn
        for col_idx in range(1, 9):
            c = ws.cell(r, col_idx)
            c.border = thin_border
            c.font = font_item_black
            if col_idx in (1, 5):
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif col_idx in (2, 3, 4):
                c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            else:
                c.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)

        for col_idx in range(9, 16):
            c = ws.cell(r, col_idx)
            c.border = Border()  # Cột J:O (Bảng giá vốn nội bộ) là NO BORDER theo mẫu gốc
            c.font = font_item_black
            c.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)

        # Tính toán chiều cao dòng chống cắt chữ
        d_text = str(item.desc or "")
        lines_d = compute_cell_lines(d_text, ws.column_dimensions["D"].width or 52.0)
        lines_b = compute_cell_lines(str(item.name or ""), ws.column_dimensions["B"].width or 33.0)
        lines_c = compute_cell_lines(str(item.category or ""), ws.column_dimensions["C"].width or 30.0)
        max_lines = max(lines_d, lines_b, lines_c, 3)
        ws.row_dimensions[r].height = max(75.0, max_lines * 19.5 + 16.0)

    # 4. Cập nhật dòng "以下空白 / Dưới đây để trống"
    ws.merge_cells(start_row=r_empty, start_column=1, end_row=r_empty, end_column=8)
    cell_empty = ws.cell(r_empty, 1)
    cell_empty.value = "以下空白"
    cell_empty.alignment = Alignment(horizontal="center", vertical="center")
    cell_empty.font = Font(name="Times New Roman", size=10, bold=False, color="595959")
    for col_idx in range(1, 9):
        ws.cell(r_empty, col_idx).border = thin_border
    ws.row_dimensions[r_empty].height = 20.0

    # 5. Cập nhật các dòng Tổng kết & Công thức sống
    # 5.1 Tạm tính (Subtotal)
    ws.cell(r_subtotal, 6).value = " Tạm tính 小計"
    ws.cell(r_subtotal, 7).value = f"=SUM(G13:G{12 + num_items})"
    ws.cell(r_subtotal, 8).value = f"=G{r_subtotal}*H$12"
    ws.cell(r_subtotal, 13).value = f"=SUM(M13:M{12 + num_items})"
    ws.cell(r_subtotal, 15).value = f"=SUM(O13:O{12 + num_items})"
    ws.row_dimensions[r_subtotal].height = 25.0

    # 5.2 VAT 8%
    ws.cell(r_vat, 6).value = " Thuế VAT 8% 增值稅"
    ws.cell(r_vat, 7).value = f"=G{r_subtotal}*0.08"
    ws.cell(r_vat, 8).value = f"=H{r_subtotal}*0.08"
    ws.row_dimensions[r_vat].height = 25.0

    # 5.3 Tổng cộng (Total)
    ws.cell(r_total, 6).value = " Tổng cộng 總金額"
    ws.cell(r_total, 7).value = f"=G{r_subtotal}*1.08"
    ws.cell(r_total, 8).value = f"=H{r_subtotal}*1.08"
    ws.row_dimensions[r_total].height = 28.0

    # Format màu sắc chuẩn 100% mẫu gốc cho 3 dòng tổng: Màu XANH DƯƠNG bold (#0000FF)
    font_total_blue = Font(name="Times New Roman", size=11, bold=True, color="0000FF")
    theme_fill = copy(ws.cell(r_subtotal, 6).fill)
    for r_idx in [r_subtotal, r_vat, r_total]:
        for col_idx in [6, 7, 8]:
            c = ws.cell(r_idx, col_idx)
            c.font = font_total_blue
            c.border = thin_border
            c.fill = theme_fill
            if col_idx == 6:
                c.alignment = Alignment(horizontal="left", vertical="center")
            else:
                c.alignment = Alignment(horizontal="right", vertical="center")

    # 6. Khối chữ ký xác nhận khách hàng: Màu NÂU VÀNG bold (#9C6500)
    font_sign_brown = Font(name="Times New Roman", size=11, bold=True, color="9C6500")
    ws.cell(r_sign_title, 1).value = "※客戶確認 Xác nhận khách hàng"
    ws.cell(r_sign_title, 1).font = font_sign_brown
    ws.cell(r_sign_title, 1).alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[r_sign_title].height = 22.0

    ws.cell(r_sign_box, 1).value = "簽名 (Ký tên)：\n\n日期 (Ngày)："
    ws.cell(r_sign_box, 1).font = font_sign_brown
    ws.cell(r_sign_box, 1).alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws.row_dimensions[r_sign_box].height = 55.0

    # 7. Điều khoản 2 (Bảo hành 1 năm): Chữ xanh dương bold lồng trong câu chữ đen
    # Tính ngày hết hạn (30 ngày sau ngày báo giá)
    try:
        dt = datetime.strptime(quote_date_str, "%d/%m/%Y")
        from datetime import timedelta
        exp_date = (dt + timedelta(days=31)).strftime("%Y/%m/%d")
    except Exception:
        exp_date = "2026/11/21"

    if_regular = InlineFont(rFont="Times New Roman", sz=11, color=Color(rgb="00000000"), b=False)
    if_blue_bold = InlineFont(rFont="Times New Roman", sz=11, color=Color(rgb="000000FF"), b=True)

    rt2 = CellRichText([
        TextBlock(if_regular, f"2. 報價有效期限：{exp_date} 止，報價簽回視同專案確認，不可任意終止、取消本專案；"),
        TextBlock(if_blue_bold, "交貨後保固一年\n"),
        TextBlock(if_regular, f"    Thời hạn hiệu lực của báo giá: đến hết ngày {exp_date.replace('/', '-')}. Việc ký và gửi lại báo giá được xem là xác nhận dự án, \n    không được phép đơn phương chấm dứt hoặc hủy bỏ dự án này; "),
        TextBlock(if_blue_bold, "Bảo hành 1 năm kể từ ngày giao hàng.")
    ])
    ws.cell(r_term2, 4).value = rt2
    ws.cell(r_term2, 4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[r_term2].height = 42.0

    # 8. Điều khoản 3 (Thanh toán): Toàn bộ chữ màu ĐỎ RỰC bold (#FF0000)
    font_payment_red = Font(name="Times New Roman", size=11, bold=True, color="FF0000")
    payment_text = quote_data.notes_payment or "3. 付款方式 : 訂金 35%、 交貨 55%、驗收 10% TT3"
    ws.cell(r_term3, 4).value = payment_text
    ws.cell(r_term3, 4).font = font_payment_red
    ws.cell(r_term3, 4).alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[r_term3].height = 25.0

    # 9. Khóa chặt vùng in & Cấu hình Page Setup A4
    # Mẫu gốc không dùng freeze_panes (báo giá 1 trang chuẩn A4).
    # Đặt topLeftCell = "A1" để mở từ đầu trang (A1), tránh bị kẹt góc nhìn ở dòng A11.
    ws.freeze_panes = None
    ws.print_area = f"'{ws.title}'!$A$1:$H${r_term3}"
    ws.page_setup.paperSize = 9  # A4
    ws.page_setup.orientation = "portrait"
    ws.page_setup.scale = 38
    ws.sheet_properties.pageSetUpPr.fitToPage = False

    ws.sheet_view.topLeftCell = "A1"
    if hasattr(ws, "views") and hasattr(ws.views, "sheetView") and ws.views.sheetView:
        for sv in ws.views.sheetView:
            sv.view = "pageBreakPreview"
            sv.showGridLines = False
            sv.topLeftCell = "A1"
            sv.zoomScale = 60
            sv.pane = None
            if hasattr(sv, "selection") and sv.selection:
                sv.selection[0].pane = None
                sv.selection[0].activeCell = "A1"
                sv.selection[0].sqref = "A1"
    ws.sheet_view.zoomScale = 60

    # 10. Lưu workbook vào byte_stream một lần duy nhất
    # (openpyxl đóng stream file ảnh trong workbook khi save, không được gọi wb.save lần 2)
    byte_stream = io.BytesIO()
    wb.save(byte_stream)
    content_bytes = byte_stream.getvalue()
    byte_stream.seek(0)

    from app.utils.file_helper import document_filename
    fname = document_filename("Bao_Gia_ECO_PRIME", quote_data.customer_name or "", "", "xlsx")
    if custom_output_filename:
        if (Path(custom_output_filename).name != custom_output_filename
                or any(ch in custom_output_filename for ch in '\\/:*?"<>|')
                or not custom_output_filename.lower().endswith(".xlsx")):
            raise ValueError("Tên file ECO PRIME không hợp lệ.")
        fname = custom_output_filename
    saved_file_path = None
    if save_to_disk:
        target_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
        target_dir.mkdir(parents=True, exist_ok=True)
        out_file = target_dir / fname
        # Preserve any existing version, including when a custom name is supplied.
        counter = 2
        while out_file.exists():
            out_file = target_dir / f"{Path(fname).stem}_v{counter}.xlsx"
            counter += 1
        try:
            out_file.write_bytes(content_bytes)
        except PermissionError:
            out_file = target_dir / f"{out_file.stem}_v2.xlsx"
            out_file.write_bytes(content_bytes)
        saved_file_path = str(out_file)
        fname = out_file.name

    return {
        "file_name": fname,
        "file_path": saved_file_path,
        "bytes_io": byte_stream,
        "content_bytes": content_bytes,
        "sheet_title": ws.title,
        "item_count": num_items,
        "last_row": r_term3,
    }
