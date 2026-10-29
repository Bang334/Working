"""Quotation Excel workbook (.xlsx) generator for Hong Ming Global."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)

# Colors & Fonts
FONT_FAMILY = "Times New Roman"
FONT_CORP_NAME = Font(name=FONT_FAMILY, size=13, bold=True, color="FF1F4E79")
FONT_CORP_SUB = Font(name=FONT_FAMILY, size=10, bold=True, color="FF2E75B6")
FONT_CORP_INFO = Font(name=FONT_FAMILY, size=9, bold=False, color="FF64748B")

FONT_DOC_TITLE = Font(name=FONT_FAMILY, size=15, bold=True, color="FF1F4E79")
FONT_DOC_SUB = Font(name=FONT_FAMILY, size=11, bold=True, color="FF2E75B6")

FONT_META_LABEL = Font(name=FONT_FAMILY, size=10, bold=True, color="FF1E293B")
FONT_META_VALUE = Font(name=FONT_FAMILY, size=10, bold=False, color="FF0F172A")

FONT_HDR = Font(name=FONT_FAMILY, size=10, bold=True, color="FFFFFFFF")
FONT_DATA_STT = Font(name=FONT_FAMILY, size=10, bold=False, color="FF64748B")
FONT_DATA = Font(name=FONT_FAMILY, size=10, bold=False, color="FF0F172A")
FONT_DATA_BOLD = Font(name=FONT_FAMILY, size=10, bold=True, color="FF0F172A")

FONT_SUM_LABEL = Font(name=FONT_FAMILY, size=10, bold=True, color="FF1E293B")
FONT_SUM_VALUE = Font(name=FONT_FAMILY, size=10, bold=True, color="FF1E293B")
FONT_GRAND_LABEL = Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79")
FONT_GRAND_VALUE = Font(name=FONT_FAMILY, size=12, bold=True, color="FF15803D")

FONT_WORDS_LABEL = Font(name=FONT_FAMILY, size=9.5, bold=True, color="FF334155")
FONT_WORDS_VALUE = Font(name=FONT_FAMILY, size=9.5, italic=True, color="FF1E293B")

FONT_TERMS_HDR = Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79")
FONT_TERMS_ITEM = Font(name=FONT_FAMILY, size=9.5, bold=False, color="FF1E293B")

FONT_SIG_HDR = Font(name=FONT_FAMILY, size=10.5, bold=True, color="FF1F4E79")
FONT_SIG_SUB = Font(name=FONT_FAMILY, size=9, italic=True, color="FF64748B")

# Fills
FILL_DARK_BLUE = PatternFill("solid", fgColor="FF1F4E79")
FILL_HEADER_BLUE = PatternFill("solid", fgColor="FF2E75B6")
FILL_LIGHT_BLUE = PatternFill("solid", fgColor="FFE0F2FE")
FILL_LIGHT_GRAY = PatternFill("solid", fgColor="FFF8FAFC")
FILL_SUMMARY_BG = PatternFill("solid", fgColor="FFF1F5F9")
FILL_WHITE = PatternFill("solid", fgColor="FFFFFFFF")

# Borders
BORDER_THIN = Border(
    left=Side(style='thin', color='FFCBD5E1'),
    right=Side(style='thin', color='FFCBD5E1'),
    top=Side(style='thin', color='FFCBD5E1'),
    bottom=Side(style='thin', color='FFCBD5E1')
)
BORDER_HEADER = Border(
    left=Side(style='thin', color='FF1F4E79'),
    right=Side(style='thin', color='FF1F4E79'),
    top=Side(style='thin', color='FF1F4E79'),
    bottom=Side(style='thin', color='FF1F4E79')
)


def apply_cell_style(cell, font=None, fill=None, border=None, alignment=None, number_format=None):
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if border is not None:
        cell.border = border
    if alignment:
        cell.alignment = alignment
    if number_format:
        cell.number_format = number_format


def generate_quotation_excel(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate professional bilingual Quotation Excel workbook (.xlsx)."""
    target_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
    target_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data
    cust_vi = str(data.get("customer_name_vi") or data.get("customer_name") or "KHÁCH HÀNG").strip()
    cust_zh = str(data.get("customer_name_zh") or data.get("customer_name_cn") or "").strip()
    tax_code = str(data.get("tax_code") or "").strip()
    quote_no = str(data.get("quotation_no") or data.get("quote_no") or "HM-QT-001").strip()
    quote_date = str(data.get("quotation_date") or data.get("quote_date") or datetime.now().strftime("%d/%m/%Y")).strip()
    project_name = str(data.get("project_name") or "Dự án Cung Cấp Thiết Bị & Dịch Vụ IoT").strip()
    contact_person = str(data.get("contact_person") or "").strip()

    validity = str(data.get("validity") or "30 ngày kể từ ngày phát hành").strip()
    lead_time = str(data.get("lead_time") or "60 - 80 ngày sau khi xác nhận đơn hàng").strip()
    warranty = str(data.get("warranty") or "12 tháng chính hãng kể từ ngày nghiệm thu").strip()
    payment_terms = str(data.get("payment_terms") or "Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%").strip()
    notes = str(data.get("notes") or "").strip()

    raw_items = data.get("items") or []
    items = []
    subtotal = 0
    for idx, it in enumerate(raw_items, start=1):
        name = str(it.get("name") or it.get("product_name") or f"Thiết bị {idx}").strip()
        unit = str(it.get("unit") or "Bộ").strip()
        qty = parse_positive_integer(it.get("qty") or it.get("quantity") or 1)
        if qty <= 0:
            qty = 1
        price = parse_positive_integer(it.get("price") or it.get("unit_price") or 0)
        total = qty * price
        subtotal += total
        items.append({
            "stt": idx,
            "name": name,
            "unit": unit,
            "qty": qty,
            "price": price,
            "total": total
        })

    vat = round(subtotal * 0.1)
    grand_total = subtotal + vat
    vietnamese_words = number_to_vietnamese_words(grand_total)
    chinese_words = number_to_chinese_words(grand_total)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Báo Giá"
    ws.views.sheetView[0].showGridLines = True

    # Column dimensions
    col_widths = {
        'A': 6.5,    # STT
        'B': 45.0,   # Tên thiết bị / quy cách
        'C': 10.0,   # ĐVT
        'D': 9.0,    # SL
        'E': 18.0,   # Đơn giá
        'F': 20.0,   # Thành tiền
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # Row 1: Company Header VI
    ws.merge_cells("A1:F1")
    ws['A1'].value = "CÔNG TY TNHH TOÀN CẦU HONG MING"
    apply_cell_style(ws['A1'], font=FONT_CORP_NAME, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[1].height = 20

    # Row 2: Company Header ZH / EN
    ws.merge_cells("A2:F2")
    ws['A2'].value = "宏明環球有限公司 — HONG MING GLOBAL CO., LTD."
    apply_cell_style(ws['A2'], font=FONT_CORP_SUB, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[2].height = 17

    # Row 3: Company contact info
    ws.merge_cells("A3:F3")
    ws['A3'].value = "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP.HCM | MST: 0318280158 | Hotline: +84 966 687 109"
    apply_cell_style(ws['A3'], font=FONT_CORP_INFO, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[3].height = 16

    # Row 4: Empty space
    ws.row_dimensions[4].height = 6

    # Row 5: Document Title
    ws.merge_cells("A5:F5")
    ws['A5'].value = "BẢNG BÁO GIÁ THIẾT BỊ & DỊCH VỤ KỸ THUẬT"
    apply_cell_style(ws['A5'], font=FONT_DOC_TITLE, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[5].height = 24

    # Row 6: Subtitle
    ws.merge_cells("A6:F6")
    ws['A6'].value = f"設備及工程服務報價單  |  Dự án / 專案: {project_name}"
    apply_cell_style(ws['A6'], font=FONT_DOC_SUB, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[6].height = 18

    # Row 7: Empty space
    ws.row_dimensions[7].height = 6

    # Rows 8-9: Meta Information
    # Row 8: Customer & Quote No
    ws.merge_cells("A8:B8")
    ws['A8'].value = f"Khách hàng / 買方: {cust_vi} ({cust_zh})"
    apply_cell_style(ws['A8'], font=FONT_META_LABEL, alignment=Alignment(horizontal='left', vertical='center'))

    ws['C8'].value = "Số báo giá:"
    apply_cell_style(ws['C8'], font=FONT_META_LABEL, alignment=Alignment(horizontal='right', vertical='center'))

    ws.merge_cells("D8:F8")
    ws['D8'].value = quote_no
    apply_cell_style(ws['D8'], font=Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79"),
                     alignment=Alignment(horizontal='left', vertical='center'))
    ws.row_dimensions[8].height = 19

    # Row 9: Tax Code & Date
    ws.merge_cells("A9:B9")
    ws['A9'].value = f"MST / 統一編號: {tax_code or 'Theo hợp đồng'}"
    apply_cell_style(ws['A9'], font=FONT_META_VALUE, alignment=Alignment(horizontal='left', vertical='center'))

    ws['C9'].value = "Ngày phát hành:"
    apply_cell_style(ws['C9'], font=FONT_META_LABEL, alignment=Alignment(horizontal='right', vertical='center'))

    ws.merge_cells("D9:F9")
    ws['D9'].value = quote_date
    apply_cell_style(ws['D9'], font=FONT_META_VALUE, alignment=Alignment(horizontal='left', vertical='center'))
    ws.row_dimensions[9].height = 19

    # Row 10: Empty space before table
    ws.row_dimensions[10].height = 8

    # Row 11: Table Headers
    hdr_row = 11
    headers = [
        ("A", "STT\n序號"),
        ("B", "Tên Thiết Bị / Quy Cách Kỹ Thuật\n產品名稱及規格說明"),
        ("C", "ĐVT\n單位"),
        ("D", "SL\n數量"),
        ("E", "Đơn Giá (VND)\n單價"),
        ("F", "Thành Tiền (VND)\n金額"),
    ]
    for col_let, text in headers:
        cell = ws[f"{col_let}{hdr_row}"]
        cell.value = text
        apply_cell_style(cell, font=FONT_HDR, fill=FILL_DARK_BLUE, border=BORDER_HEADER,
                         alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws.row_dimensions[hdr_row].height = 28

    # Freeze panes below header
    ws.freeze_panes = f"A{hdr_row + 1}"

    # Items Rows
    curr_row = hdr_row + 1
    for idx, item in enumerate(items, start=1):
        ws.row_dimensions[curr_row].height = 24
        row_fill = FILL_LIGHT_GRAY if idx % 2 == 0 else FILL_WHITE

        # A: STT
        cA = ws[f"A{curr_row}"]
        cA.value = item["stt"]
        apply_cell_style(cA, font=FONT_DATA_STT, fill=row_fill, border=BORDER_THIN,
                         alignment=Alignment(horizontal='center', vertical='center'))

        # B: Name
        cB = ws[f"B{curr_row}"]
        cB.value = item["name"]
        apply_cell_style(cB, font=FONT_DATA, fill=row_fill, border=BORDER_THIN,
                         alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))

        # C: Unit
        cC = ws[f"C{curr_row}"]
        cC.value = item["unit"]
        apply_cell_style(cC, font=FONT_DATA, fill=row_fill, border=BORDER_THIN,
                         alignment=Alignment(horizontal='center', vertical='center'))

        # D: Qty
        cD = ws[f"D{curr_row}"]
        cD.value = item["qty"]
        apply_cell_style(cD, font=FONT_DATA_BOLD, fill=row_fill, border=BORDER_THIN,
                         alignment=Alignment(horizontal='center', vertical='center'),
                         number_format="#,##0")

        # E: Price
        cE = ws[f"E{curr_row}"]
        cE.value = item["price"]
        apply_cell_style(cE, font=FONT_DATA, fill=row_fill, border=BORDER_THIN,
                         alignment=Alignment(horizontal='right', vertical='center'),
                         number_format="#,##0")

        # F: Total
        cF = ws[f"F{curr_row}"]
        cF.value = f"=D{curr_row}*E{curr_row}"
        apply_cell_style(cF, font=FONT_DATA_BOLD, fill=row_fill, border=BORDER_THIN,
                         alignment=Alignment(horizontal='right', vertical='center'),
                         number_format="#,##0")

        curr_row += 1

    # Summary Row 1: Subtotal
    r_sub = curr_row
    ws.merge_cells(f"A{r_sub}:E{r_sub}")
    for col_idx in range(1, 6):
        col_letter = get_column_letter(col_idx)
        apply_cell_style(ws[f"{col_letter}{r_sub}"], fill=FILL_SUMMARY_BG, border=BORDER_THIN)
    ws[f"A{r_sub}"].value = "Tổng cộng tiền hàng (Chưa thuế VAT) / 小計 (未含稅):"
    apply_cell_style(ws[f"A{r_sub}"], font=FONT_SUM_LABEL, fill=FILL_SUMMARY_BG, border=BORDER_THIN,
                     alignment=Alignment(horizontal='right', vertical='center'))

    ws[f"F{r_sub}"].value = f"=SUM(F{hdr_row + 1}:F{r_sub - 1})"
    apply_cell_style(ws[f"F{r_sub}"], font=FONT_SUM_VALUE, fill=FILL_SUMMARY_BG, border=BORDER_THIN,
                     alignment=Alignment(horizontal='right', vertical='center'),
                     number_format="#,##0")
    ws.row_dimensions[r_sub].height = 22
    curr_row += 1

    # Summary Row 2: VAT 10%
    r_vat = curr_row
    ws.merge_cells(f"A{r_vat}:E{r_vat}")
    for col_idx in range(1, 6):
        col_letter = get_column_letter(col_idx)
        apply_cell_style(ws[f"{col_letter}{r_vat}"], fill=FILL_SUMMARY_BG, border=BORDER_THIN)
    ws[f"A{r_vat}"].value = "Thuế suất GTGT (VAT 10%) / 增值稅 (10%):"
    apply_cell_style(ws[f"A{r_vat}"], font=FONT_SUM_LABEL, fill=FILL_SUMMARY_BG, border=BORDER_THIN,
                     alignment=Alignment(horizontal='right', vertical='center'))

    ws[f"F{r_vat}"].value = f"=F{r_sub}*0.1"
    apply_cell_style(ws[f"F{r_vat}"], font=FONT_SUM_VALUE, fill=FILL_SUMMARY_BG, border=BORDER_THIN,
                     alignment=Alignment(horizontal='right', vertical='center'),
                     number_format="#,##0")
    ws.row_dimensions[r_vat].height = 22
    curr_row += 1

    # Summary Row 3: Grand Total
    r_gt = curr_row
    ws.merge_cells(f"A{r_gt}:E{r_gt}")
    for col_idx in range(1, 6):
        col_letter = get_column_letter(col_idx)
        apply_cell_style(ws[f"{col_letter}{r_gt}"], fill=FILL_LIGHT_BLUE, border=BORDER_THIN)
    ws[f"A{r_gt}"].value = "TỔNG CỘNG THANH TOÁN (ĐÃ VAT) / 總計 (含稅):"
    apply_cell_style(ws[f"A{r_gt}"], font=FONT_GRAND_LABEL, fill=FILL_LIGHT_BLUE, border=BORDER_THIN,
                     alignment=Alignment(horizontal='right', vertical='center'))

    ws[f"F{r_gt}"].value = f"=F{r_sub}+F{r_vat}"
    apply_cell_style(ws[f"F{r_gt}"], font=FONT_GRAND_VALUE, fill=FILL_LIGHT_BLUE, border=BORDER_THIN,
                     alignment=Alignment(horizontal='right', vertical='center'),
                     number_format="#,##0")
    ws.row_dimensions[r_gt].height = 26
    curr_row += 1

    # Summary Row 4: Amount in Words (Vietnamese & Chinese)
    r_w = curr_row
    ws.merge_cells(f"A{r_w}:F{r_w}")
    ws[f"A{r_w}"].value = f"• Số tiền bằng chữ: {vietnamese_words}\n• 大寫金額 (中文): {chinese_words}"
    for col_idx in range(1, 7):
        col_letter = get_column_letter(col_idx)
        apply_cell_style(ws[f"{col_letter}{r_w}"], fill=FILL_LIGHT_GRAY, border=BORDER_THIN)
    apply_cell_style(ws[f"A{r_w}"], font=FONT_WORDS_LABEL, fill=FILL_LIGHT_GRAY, border=BORDER_THIN,
                     alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    ws.row_dimensions[r_w].height = 36
    curr_row += 2

    # Commercial Terms
    ws.merge_cells(f"A{curr_row}:F{curr_row}")
    ws[f"A{curr_row}"].value = "ĐIỀU KHOẢN THƯƠNG MẠI & BẢO HÀNH / 商務條款及保固說明:"
    apply_cell_style(ws[f"A{curr_row}"], font=FONT_TERMS_HDR, alignment=Alignment(horizontal='left', vertical='center'))
    ws.row_dimensions[curr_row].height = 20
    curr_row += 1

    terms = [
        f"1. Thời hạn hiệu lực / 報價有效期: {validity}",
        f"2. Thời gian giao hàng / 交貨期: {lead_time}",
        f"3. Thời hạn bảo hành / 保固期: {warranty}",
        f"4. Điều kiện thanh toán / 付款條件: {payment_terms}",
    ]
    if notes:
        terms.append(f"5. Ghi chú kỹ thuật bổ sung / 備註: {notes}")

    for t in terms:
        ws.merge_cells(f"A{curr_row}:F{curr_row}")
        ws[f"A{curr_row}"].value = f"• {t}"
        apply_cell_style(ws[f"A{curr_row}"], font=FONT_TERMS_ITEM,
                         alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
        ws.row_dimensions[curr_row].height = 19
        curr_row += 1

    curr_row += 1
    # Signature Block
    ws.merge_cells(f"A{curr_row}:C{curr_row}")
    ws[f"A{curr_row}"].value = "ĐẠI DIỆN BÊN MUA (BÊN A) / 買方代表簽署"
    apply_cell_style(ws[f"A{curr_row}"], font=FONT_SIG_HDR, alignment=Alignment(horizontal='center', vertical='center'))

    ws.merge_cells(f"D{curr_row}:F{curr_row}")
    ws[f"D{curr_row}"].value = "ĐẠI DIỆN BÊN BÁN (BÊN B) / 賣方代表簽署"
    apply_cell_style(ws[f"D{curr_row}"], font=FONT_SIG_HDR, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[curr_row].height = 20
    curr_row += 1

    ws.merge_cells(f"A{curr_row}:C{curr_row}")
    ws[f"A{curr_row}"].value = "(Ký tên, đóng dấu & ghi rõ họ tên / 簽名蓋章)"
    apply_cell_style(ws[f"A{curr_row}"], font=FONT_SIG_SUB, alignment=Alignment(horizontal='center', vertical='center'))

    ws.merge_cells(f"D{curr_row}:F{curr_row}")
    ws[f"D{curr_row}"].value = "CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司)"
    apply_cell_style(ws[f"D{curr_row}"], font=FONT_SIG_SUB, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[curr_row].height = 17
    curr_row += 5

    ws.merge_cells(f"A{curr_row}:C{curr_row}")
    ws[f"A{curr_row}"].value = "Ngày / 日期: ..... / ..... / 2026"
    apply_cell_style(ws[f"A{curr_row}"], font=FONT_SIG_SUB, alignment=Alignment(horizontal='center', vertical='center'))

    ws.merge_cells(f"D{curr_row}:F{curr_row}")
    ws[f"D{curr_row}"].value = "Tổng Giám Đốc: TANG WEI LI (Đường Vĩ Lực / 總經理)"
    apply_cell_style(ws[f"D{curr_row}"], font=FONT_SIG_SUB, alignment=Alignment(horizontal='center', vertical='center'))
    ws.row_dimensions[curr_row].height = 17

    # Page Setup (A4 Portrait, fit to page width)
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_area = f"A1:F{curr_row}"
    ws.page_margins = PageMargins(left=0.4, right=0.4, top=0.5, bottom=0.5, header=0.2, footer=0.2)

    # Save File
    from app.utils.file_helper import document_filename
    timestamp = str(data.get("_file_timestamp") or "")
    if not re.fullmatch(r"\d{8}_\d{6}_\d{6}", timestamp):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_name = document_filename("Bao_Gia", cust_vi, quote_no, "xlsx", timestamp)
    output_path = target_dir / file_name

    try:
        wb.save(str(output_path))
    except PermissionError:
        file_name = f"{output_path.stem}_v2.xlsx"
        output_path = target_dir / file_name
        wb.save(str(output_path))

    # Index into SQLite documents table
    file_size = output_path.stat().st_size if output_path.is_file() else 0
    try:
        from app.database import index_single_document
        index_single_document(
            contract_code="",
            doc_type="BAO_GIA",
            doc_name=f"Báo Giá Excel ({quote_no}) - {cust_vi}",
            file_name=file_name,
            file_path=str(output_path),
            file_size=file_size,
            file_format="xlsx",
            description=f"Bảng báo giá thiết bị Excel: {cust_vi} [Số: {quote_no}]"
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"Đã xuất thành công Báo giá Excel (.xlsx) cho {cust_vi}!",
        "file_name": file_name,
        "file_path": str(output_path),
        "download_url": f"/api/v1/quotation/download/{file_name}",
        "total_amount": grand_total,
        "total_amount_formatted": f"{grand_total:,}".replace(",", ".") + " VND",
        "customer_name": cust_vi,
        "quotation_no": quote_no,
    }
