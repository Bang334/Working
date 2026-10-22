"""Acceptance Excel service generating 1:1 pixel-perfect bilingual acceptance records.

Strictly adheres to AGENTS.md 10 golden control points:
1. Freeze panes (A6)
2. Sheet view & fit-to-page (Portrait A4, scale=52%, print area, showGridLines=None in PageBreakPreview)
3. Uniform photo columns (exact identical width and row height)
4. Per-row thin black borders only for data blocks (no unnecessary borders for titles/notes/signatures)
5. Times New Roman font standard across all sections
6. Corporate color palette (#1F4E79, #2E75B6, #D6E4F0, #F2F2F2, #E2EFDA, #FFFFF2CC)
7. Merged cells and proper text alignment with wrap_text=True
8. Live 2-way hyperlinks between summary sheet and every detail photo sheet
9. Anti-clipping dynamic row heights for Vietnamese & CJK characters
10. Safe saving with PermissionError fallback
"""

import math
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

# ==============================================================================
# DESIGN SYSTEM & PALETTE (Matching Hong Ming Global standard 1:1)
# ==============================================================================
FONT_FAMILY = "Times New Roman"

FONT_TITLE_1 = Font(name=FONT_FAMILY, size=14, bold=True, color="FFFFFFFF")
FONT_TITLE_2 = Font(name=FONT_FAMILY, size=13, bold=True, color="FFFFFFFF")
FONT_HDR_INFO = Font(name=FONT_FAMILY, size=12, bold=True, color="FF1F4E79")
FONT_PARTY_INFO = Font(name=FONT_FAMILY, size=14, bold=False, color="FF000000")
FONT_TABLE_HDR = Font(name=FONT_FAMILY, size=12, bold=True, color="FFFFFFFF")

FONT_DATA_STT = Font(name=FONT_FAMILY, size=12, bold=True, color="FF000000")
FONT_DATA_TEXT = Font(name=FONT_FAMILY, size=11, bold=False, color="FF000000")
FONT_DATA_RESULT = Font(name=FONT_FAMILY, size=12, bold=True, color="FF375623")
FONT_DATA_LINK = Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79")

FONT_NOTE_HDR = Font(name=FONT_FAMILY, size=14, bold=True, color="FF1F4E79")
FONT_NOTE_BODY = Font(name=FONT_FAMILY, size=12, bold=False, color="FF000000")
FONT_SIG = Font(name=FONT_FAMILY, size=12, bold=True, color="FF1F4E79")

# Detail sheet fonts
FONT_DET_TITLE = Font(name=FONT_FAMILY, size=13, bold=True, color="FFFFFFFF")
FONT_DET_SUB1 = Font(name=FONT_FAMILY, size=12, bold=True, color="FF1F4E79")
FONT_DET_SUB2 = Font(name=FONT_FAMILY, size=12, bold=False, color="FF000000")
FONT_DET_GUIDE = Font(name=FONT_FAMILY, size=10, bold=False, italic=True, color="FF7F7F7F")
FONT_DET_BACK = Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79")

# Fills
FILL_DARK_BLUE = PatternFill("solid", fgColor="FF1F4E79")
FILL_LIGHT_BLUE = PatternFill("solid", fgColor="FFD6E4F0")
FILL_LIGHT_GRAY = PatternFill("solid", fgColor="FFF2F2F2")
FILL_HEADER_BLUE = PatternFill("solid", fgColor="FF2E75B6")
FILL_WHITE = PatternFill("solid", fgColor="FFFFFFFF")
FILL_GREEN_PASS = PatternFill("solid", fgColor="FFE2EFDA")
FILL_YELLOW_IMG = PatternFill("solid", fgColor="FFFFF2CC")

# Borders
BORDER_THIN_BLACK = Border(
    left=Side(style='thin', color='FF000000'),
    right=Side(style='thin', color='FF000000'),
    top=Side(style='thin', color='FF000000'),
    bottom=Side(style='thin', color='FF000000')
)


def apply_range_style(ws, min_col, min_row, max_col, max_row, font=None, fill=None, border=None, alignment=None):
    """Helper to apply formatting across a 2D range of cells uniformly."""
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            cell = ws.cell(r, c)
            if font:
                cell.font = font
            if fill:
                cell.fill = fill
            if border is not None:
                cell.border = border
            if alignment:
                cell.alignment = alignment


def calculate_row_height(text: str, col_width: float, base_line_height: float = 18.0) -> float:
    """Calculate safe row height preventing text clipping for Vietnamese and CJK characters."""
    if not text:
        return 48.75
    lines = str(text).split("\n")
    total_visual_lines = 0
    for line in lines:
        visual_len = sum(2 if ord(c) > 127 else 1 for c in line)
        wrap_lines = max(1, math.ceil(visual_len / max(col_width * 1.5, 10.0)))
        total_visual_lines += wrap_lines

    return max(48.75, total_visual_lines * base_line_height + 12.0)


def sanitize_sheet_name(name: str) -> str:
    """Clean serial or title to conform with Excel sheet name restrictions."""
    cleaned = re.sub(r'[\\/*?:\[\]]', '_', str(name)).strip()
    return cleaned[:31] if cleaned else "Sheet"


def prepare_acceptance_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and format raw acceptance input with numbers and Chinese words."""
    data = dict(raw_data)

    # Defaults for Party B (Hong Ming Global)
    ben_b = data.get("ben_b") or {}
    data["ben_b"] = {
        "ten_cong_ty": ben_b.get("ten_cong_ty") or "CÔNG TY TNHH TOÀN CẦU HONG MING",
        "ten_tieng_trung": ben_b.get("ten_tieng_trung") or "宏明環球有限公司",
        "dia_chi": ben_b.get("dia_chi") or "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh",
        "mst": ben_b.get("mst") or "0318280158",
        "nguoi_dai_dien": ben_b.get("nguoi_dai_dien") or "TANG WEI LI",
        "chuc_vu": ben_b.get("chuc_vu") or "Tổng Giám Đốc",
        "chuc_vu_trung": ben_b.get("chuc_vu_trung") or "總經理"
    }

    # Party A defaults
    ben_a = data.get("ben_a") or {}
    data["ben_a"] = {
        "ten_cong_ty": ben_a.get("ten_cong_ty") or "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
        "ten_tieng_trung": ben_a.get("ten_tieng_trung") or "CX Technology (VN) 股份有限公司",
        "dia_chi": ben_a.get("dia_chi") or "KCX Tân Thuận, Phường Tân Thuận Đông, Quận 7, TP.HCM",
        "mst": ben_a.get("mst") or "",
        "nguoi_dai_dien": ben_a.get("nguoi_dai_dien") or "",
        "chuc_vu": ben_a.get("chuc_vu") or "Đại diện khách hàng"
    }

    # Monetary calculation
    raw_amount = data.get("tong_tien_so") or "0"
    amount_int = parse_positive_integer(raw_amount)

    items = data.get("hang_muc") or []
    # If amount is 0, sum from items if available
    if amount_int == 0 and items:
        total_items_sum = 0
        for it in items:
            p = parse_positive_integer(it.get("tong_gia") or it.get("don_gia") or 0)
            total_items_sum += p
        if total_items_sum > 0:
            amount_int = total_items_sum

    data["tong_tien_int"] = amount_int
    data["tong_tien_formatted"] = f"{amount_int:,}".replace(",", ".")
    data["tong_tien_chu_viet"] = number_to_vietnamese_words(amount_int)
    data["tong_tien_chu_trung"] = number_to_chinese_words(amount_int)

    # General metadata
    data["so_hop_dong"] = data.get("so_hop_dong") or "HM-FINEPRO-20261009.001"
    data["so_bien_ban"] = data.get("so_bien_ban") or "001/2026/BBNT-SC"
    data["ngay_nghiem_thu"] = data.get("ngay_nghiem_thu") or datetime.now().strftime("%d/%m/%Y")
    data["tieu_de_viet"] = data.get("tieu_de_viet") or "BIÊN BẢN KIỂM TRA & NGHIỆM THU THIẾT BỊ SAU SỬA CHỮA"
    data["tieu_de_trung"] = data.get("tieu_de_trung") or "維修設備檢查及驗收記錄"

    # Notes: Default is completely empty as requested. Never insert prices or boilerplate
    data["ghi_chu"] = str(data.get("ghi_chu") or "").strip()

    return data


def build_summary_sheet(ws, data: Dict[str, Any]) -> int:
    """Build summary sheet 'Nghiệm Thu' strictly following 1:1 sample specifications."""
    ws.title = "Nghiệm Thu"

    # Workbook template uses a 14.4 pt default row height.  Keeping this value is
    # important for the deliberately blank spacer row before the signature block.
    ws.sheet_format.defaultRowHeight = 14.4

    # 1. Freeze Panes A6
    ws.freeze_panes = 'A6'

    # 2. PageBreakPreview & Zoom 85% exactly matching original
    ws.views.sheetView[0].view = "pageBreakPreview"
    ws.views.sheetView[0].zoomScale = 85
    ws.views.sheetView[0].zoomScaleNormal = 100
    ws.views.sheetView[0].zoomScaleSheetLayoutView = 85
    # Do NOT set showGridLines to True in PageBreakPreview to avoid white fringe outside data area
    ws.views.sheetView[0].showGridLines = None

    # Column widths matching original
    widths = {
        'A': 6.0,
        'B': 28.0,
        'C': 36.33,
        'D': 14.0,
        'E': 32.0,
        'F': 14.0,
        'G': 35.11
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # Row 1: Vietnamese Title
    ws.row_dimensions[1].height = 30.0
    ws.merge_cells('A1:G1')
    apply_range_style(ws, 1, 1, 7, 1, font=FONT_TITLE_1, fill=FILL_DARK_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A1'].value = data["tieu_de_viet"]

    # Row 2: Traditional Chinese Title
    ws.row_dimensions[2].height = 24.0
    ws.merge_cells('A2:G2')
    apply_range_style(ws, 1, 2, 7, 2, font=FONT_TITLE_2, fill=FILL_DARK_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A2'].value = data["tieu_de_trung"]

    # Row 3: Contract No & Date / Report No (No border)
    ws.row_dimensions[3].height = 31.5
    ws.merge_cells('A3:D3')
    ws.merge_cells('E3:G3')
    apply_range_style(ws, 1, 3, 4, 3, font=FONT_HDR_INFO, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    apply_range_style(ws, 5, 3, 7, 3, font=FONT_HDR_INFO, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    ws['A3'].value = f"Số HĐ / 合約編號: {data['so_hop_dong']}"
    ws['E3'].value = f"Ngày / 日期: {data['ngay_nghiem_thu']}          Số BB: {data['so_bien_ban']}"

    # Row 4: Party A & Party B (No border)
    ws.row_dimensions[4].height = 42.0
    ws.merge_cells('A4:D4')
    ws.merge_cells('E4:G4')
    apply_range_style(ws, 1, 4, 4, 4, font=FONT_PARTY_INFO, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    apply_range_style(ws, 5, 4, 7, 4, font=FONT_PARTY_INFO, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    ws['A4'].value = f"Bên A / 甲方: {data['ben_a']['ten_cong_ty']}"
    ws['E4'].value = f"Bên B / 乙方: {data['ben_b']['ten_cong_ty']}"

    # Row 5: Table Header (With thin black border)
    ws.row_dimensions[5].height = 38.1
    headers = [
        "STT\n序號",
        "Serial Number\n產品序號",
        "Lỗi ban đầu\n故障說明",
        "Bộ phận\n部門",
        "Hạng mục kiểm tra\n檢查項目",
        "Kết quả\n結果",
        "Sheet hình ảnh\n圖片工作表"
    ]
    for idx, hdr in enumerate(headers, start=1):
        cell = ws.cell(5, idx)
        cell.value = hdr
        cell.font = FONT_TABLE_HDR
        cell.fill = FILL_HEADER_BLUE
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER_THIN_BLACK

    # Rows 6..N: Devices data rows
    items = data.get("hang_muc") or []
    current_row = 6

    for idx, item in enumerate(items, start=1):
        stt = item.get("stt") or idx
        serial = str(item.get("serial_number") or item.get("serial") or f"DEV-{stt}").strip()
        loi = str(item.get("loi_ban_dau") or item.get("loi") or "").strip()
        bo_phan = str(item.get("bo_phan") or "CNC").strip()
        hang_muc = str(item.get("hang_muc_kiem_tra") or item.get("hang_muc") or "").strip()
        ket_qua = str(item.get("ket_qua") or "Đạt / 合格").strip()

        # Dynamic row height preventing clipping
        max_text = max([loi, hang_muc, serial], key=len)
        row_h = calculate_row_height(max_text, col_width=32.0, base_line_height=18.0)
        ws.row_dimensions[current_row].height = max(48.75, row_h)

        bg_fill = FILL_WHITE if (current_row % 2 == 0) else FILL_LIGHT_GRAY

        # Col 1: STT
        c1 = ws.cell(current_row, 1, str(stt))
        c1.font = FONT_DATA_STT
        c1.fill = bg_fill
        c1.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c1.border = BORDER_THIN_BLACK

        # Col 2: Serial Number
        c2 = ws.cell(current_row, 2, serial)
        c2.font = FONT_DATA_TEXT
        c2.fill = bg_fill
        c2.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c2.border = BORDER_THIN_BLACK

        # Col 3: Lỗi ban đầu
        c3 = ws.cell(current_row, 3, loi)
        c3.font = FONT_DATA_TEXT
        c3.fill = bg_fill
        c3.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        c3.border = BORDER_THIN_BLACK

        # Col 4: Bộ phận
        c4 = ws.cell(current_row, 4, bo_phan)
        c4.font = FONT_DATA_TEXT
        c4.fill = bg_fill
        c4.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c4.border = BORDER_THIN_BLACK

        # Col 5: Hạng mục kiểm tra
        c5 = ws.cell(current_row, 5, hang_muc)
        c5.font = FONT_DATA_TEXT
        c5.fill = bg_fill
        c5.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        c5.border = BORDER_THIN_BLACK

        # Col 6: Kết quả (Green Pass highlight)
        c6 = ws.cell(current_row, 6, ket_qua)
        c6.font = FONT_DATA_RESULT
        c6.fill = FILL_GREEN_PASS
        c6.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c6.border = BORDER_THIN_BLACK

        # Col 7: Sheet hình ảnh link
        sheet_target = sanitize_sheet_name(serial)
        c7 = ws.cell(current_row, 7, f"→ {sheet_target}")
        c7.font = FONT_DATA_LINK
        c7.fill = FILL_LIGHT_BLUE
        c7.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c7.border = BORDER_THIN_BLACK
        c7.hyperlink = f"#'{sheet_target}'!A1"

        current_row += 1

    # Row Notes Title (No border)
    note_hdr_row = current_row
    ws.row_dimensions[note_hdr_row].height = 36.0
    ws.merge_cells(f"A{note_hdr_row}:G{note_hdr_row}")
    ws[f"A{note_hdr_row}"].value = "GHI CHÚ / 備註:"
    ws[f"A{note_hdr_row}"].font = FONT_NOTE_HDR
    apply_range_style(
        ws, 1, note_hdr_row, 7, note_hdr_row,
        font=FONT_NOTE_HDR,
        fill=FILL_WHITE,
        alignment=Alignment(horizontal='left', vertical='center', wrap_text=True),
    )

    # Row Notes Body (No border) - Để trống hoàn toàn theo yêu cầu
    note_body_row = note_hdr_row + 1
    actual_note = str(data.get("ghi_chu") or "").strip()

    # The reference form reserves an 81 pt note area even when it is empty.
    # Retaining the same space prevents the signature block from shifting upward.
    note_lines_count = len(actual_note.split("\n")) if actual_note else 0
    ws.row_dimensions[note_body_row].height = max(81.0, note_lines_count * 27.0)
    ws.merge_cells(f"A{note_body_row}:G{note_body_row}")
    apply_range_style(
        ws, 1, note_body_row, 7, note_body_row,
        font=Font(name=FONT_FAMILY, size=14, bold=False, color="FF000000"),
        fill=FILL_WHITE,
        alignment=Alignment(horizontal='left', vertical='top', wrap_text=True),
    )
    ws[f"A{note_body_row}"].value = actual_note or None

    blank_row = note_body_row + 1

    # Dòng đệm của mẫu được tô trắng toàn hàng để không lộ lưới ô.
    apply_range_style(ws, 1, blank_row, 7, blank_row, fill=FILL_WHITE)

    sig_row = blank_row + 1
    ws.row_dimensions[sig_row].height = 107.25
    ws.merge_cells(f"A{sig_row}:C{sig_row}")
    ws.merge_cells(f"E{sig_row}:G{sig_row}")

    # Tô trắng toàn hàng chữ ký, bao gồm cả cột D ngăn giữa hai bên.
    apply_range_style(ws, 1, sig_row, 7, sig_row, fill=FILL_WHITE)

    ws[f"A{sig_row}"].value = (
        "ĐẠI DIỆN BÊN A / 甲方代表\n"
        "(Ký xác nhận / 簽字確認)\n\n\n"
        f"{data['ben_a']['ten_cong_ty']}"
    )
    ws[f"A{sig_row}"].font = FONT_SIG
    ws[f"A{sig_row}"].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    ws[f"E{sig_row}"].value = (
        "ĐẠI DIỆN BÊN B / 乙方代表\n"
        "(Ký tên, đóng dấu / 簽字蓋章)\n\n\n"
        f"{data['ben_b']['ten_cong_ty']}"
    )
    ws[f"E{sig_row}"].font = FONT_SIG
    ws[f"E{sig_row}"].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Page setup: Portrait A4, scale = 52, exactly 1 page width
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.scale = 52
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    # Mẫu gốc luôn chừa phần trắng cuối trang đến tối thiểu hàng 30.
    # Với danh sách dài hơn, vẫn giữ tối thiểu 8 hàng trắng sau khối chữ ký.
    print_end_row = max(30, sig_row + 8)
    apply_range_style(ws, 1, sig_row + 1, 7, print_end_row, fill=FILL_WHITE)
    ws.print_area = f"A1:G{print_end_row}"

    return sig_row


def build_detail_sheet(ws, dev: Dict[str, Any], index: int):
    """Build individual product inspection detail sheet with photo placeholders and back link."""
    stt = dev.get("stt") or index
    serial = str(dev.get("serial_number") or dev.get("serial") or f"DEV-{stt}").strip()
    sheet_title = sanitize_sheet_name(serial)
    ws.title = sheet_title
    ws.sheet_format.defaultRowHeight = 14.4

    # Detect device series: RF (3 photos) vs EF/others (5 photos)
    is_rf_series = ("RFR" in serial.upper() or "RF" in serial.upper() or dev.get("type") == "RF")

    if is_rf_series:
        max_col = 4
        col_letters = ['A', 'B', 'C', 'D']
        ws.column_dimensions['A'].width = 34.44
        ws.column_dimensions['B'].width = 34.44
        ws.column_dimensions['C'].width = 34.44
        ws.column_dimensions['D'].width = 25.33
        headers = ["Hình 1 / 圖片1", "Hình 2 / 圖片2", "Hình 3 / 圖片3", "Ghi chú / 備註"]
        img_cols = ['A', 'B', 'C']
        note_col = 'D'
    else:
        max_col = 6
        col_letters = ['A', 'B', 'C', 'D', 'E', 'F']
        ws.column_dimensions['A'].width = 37.11
        ws.column_dimensions['B'].width = 37.11
        ws.column_dimensions['C'].width = 37.11
        ws.column_dimensions['D'].width = 37.11
        ws.column_dimensions['E'].width = 37.11
        ws.column_dimensions['F'].width = 14.0
        headers = ["Hình 1 / 圖片1", "Hình 2 / 圖片2", "Hình 3 / 圖片3", "Hình 4 / 圖片4", "Hình 5 / 圖片5", "Ghi chú / 備註"]
        img_cols = ['A', 'B', 'C', 'D', 'E']
        note_col = 'F'

    end_col_letter = col_letters[-1]

    # Row 1: Header (No outer border)
    ws.row_dimensions[1].height = 27.9
    ws.merge_cells(f"A1:{end_col_letter}1")
    apply_range_style(ws, 1, 1, max_col, 1, font=FONT_DET_TITLE, fill=FILL_DARK_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A1'].value = f"HÌNH ẢNH KIỂM TRA / 檢查圖片 — {serial}"

    # Row 2: Sub-info STT, Department, Result (No outer border)
    ws.row_dimensions[2].height = 18.0
    ws.merge_cells(f"A2:{end_col_letter}2")
    apply_range_style(ws, 1, 2, max_col, 2, font=FONT_DET_SUB1, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    bp_clean = str(dev.get("bo_phan") or "CNC").replace("\n", " / ")
    kq_clean = str(dev.get("ket_qua") or "Đạt / 合格").replace("\n", " / ")
    ws['A2'].value = f"STT: {stt}    |    Bộ phận / 部門: {bp_clean}    |    Kết quả / 結果: {kq_clean}"

    # Row 3: Initial issue (No outer border)
    ws.row_dimensions[3].height = 18.0
    ws.merge_cells(f"A3:{end_col_letter}3")
    apply_range_style(ws, 1, 3, max_col, 3, font=FONT_DET_SUB2, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    loi_clean = str(dev.get("loi_ban_dau") or dev.get("loi") or "Kiểm tra định kỳ").replace("\n", " / ")
    ws['A3'].value = f"Lỗi ban đầu / 故障說明: {loi_clean}"

    # Row 4: Inspection items (No outer border)
    ws.row_dimensions[4].height = 18.0
    ws.merge_cells(f"A4:{end_col_letter}4")
    apply_range_style(ws, 1, 4, max_col, 4, font=FONT_DET_SUB2, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    hm_clean = str(dev.get("hang_muc_kiem_tra") or dev.get("hang_muc") or "Kiểm tra toàn diện chức năng").replace("\n", " / ")
    ws['A4'].value = f"Hạng mục KT / 檢查項目: {hm_clean}"

    # Row 5: Column headers (Thin black border)
    ws.row_dimensions[5].height = 30.0
    for idx, hdr in enumerate(headers, start=1):
        cell = ws.cell(5, idx)
        cell.value = hdr
        cell.font = FONT_TABLE_HDR
        cell.fill = FILL_HEADER_BLUE
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER_THIN_BLACK

    # Row 6: Photo placeholders (Height 284.25, yellow fill #FFFFF2CC, ready for Place in Cell)
    row6_h = 284.25
    ws.row_dimensions[6].height = row6_h

    for c_letter in img_cols:
        cell = ws[f"{c_letter}6"]
        cell.value = None
        cell.fill = FILL_YELLOW_IMG
        cell.border = BORDER_THIN_BLACK
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Note cell must remain completely empty.  Prices, repair actions and fallback
    # text belong to the source data, not to the image-sheet note box.
    cell_note = ws[f"{note_col}6"]
    cell_note.value = None
    cell_note.font = FONT_DATA_TEXT
    cell_note.fill = FILL_WHITE
    cell_note.border = BORDER_THIN_BLACK
    cell_note.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Row 7: Placement instruction (No border)
    ws.row_dimensions[7].height = 14.1
    ws.merge_cells(f"A7:{end_col_letter}7")
    apply_range_style(ws, 1, 7, max_col, 7, font=FONT_DET_GUIDE, fill=None,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A7'].value = "⬆  Chèn hình ảnh vào ô màu vàng: Insert → Pictures → Place in Cell  /  請將圖片插入黃色儲存格"

    # Row 8: Back link to Summary sheet (No border, live hyperlink)
    ws.row_dimensions[8].height = 15.9
    ws.merge_cells(f"A8:{end_col_letter}8")
    apply_range_style(ws, 1, 8, max_col, 8, font=FONT_DET_BACK, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True),
                      border=None)
    ws['A8'].value = '← Quay về bảng tổng hợp "Nghiệm Thu" / 返回總表'
    ws['A8'].hyperlink = "#'Nghiệm Thu'!A1"

    # Page setup
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins = PageMargins(
        left=0.4,
        right=0.4,
        top=0.4,
        bottom=0.4,
        header=0.2,
        footer=0.2,
    )


def generate_acceptance_excel(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate high-fidelity Excel (.xlsx) matching CX Technology sample 1:1 with all product sheets."""
    data = prepare_acceptance_data(raw_data)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()

    # 1. Sheet Nghiệm Thu
    ws_summary = wb.active
    build_summary_sheet(ws_summary, data)

    # 2. Tạo đủ các sheet chi tiết cho toàn bộ danh mục thiết bị
    items = data.get("hang_muc") or []
    created_sheet_names = set()

    for idx, item in enumerate(items, start=1):
        serial = str(item.get("serial_number") or item.get("serial") or f"DEV-{idx}").strip()
        safe_name = sanitize_sheet_name(serial)
        if safe_name in created_sheet_names or safe_name == "Nghiệm Thu":
            safe_name = f"{safe_name[:28]}_{idx}"
        created_sheet_names.add(safe_name)

        ws_det = wb.create_sheet(title=safe_name)
        build_detail_sheet(ws_det, item, idx)

    # Safe File Naming & Saving
    clean_so_hd = re.sub(r'[\\/*?:"<>|]', '_', data["so_hop_dong"]).strip()
    file_name = f"Biên Bản Nghiệm Thu_維修設備驗收記錄_{clean_so_hd}.xlsx"
    target_dir = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_name

    # Save to official Nghiem Thu directory with PermissionError fallback
    try:
        wb.save(target_path)
    except PermissionError:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"Biên Bản Nghiệm Thu_維修設備驗收記錄_{clean_so_hd}_{date_str}.xlsx"
        target_path = target_dir / file_name
        wb.save(target_path)

    return {
        "status": "success",
        "file_name": file_name,
        "download_url": f"/api/v1/acceptance/download/{file_name}",
        "total_amount": data["tong_tien_formatted"] + " VND",
        "acceptance_data": data,
        "detail_sheets_count": len(items)
    }
