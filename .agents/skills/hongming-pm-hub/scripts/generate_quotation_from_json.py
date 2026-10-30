# -*- coding: utf-8 -*-
"""
Perfect 1:1 Quotation Generator for Hong Ming Global
Generates quotation workbook based on '節能專案報價' template from JSON.
Preserves logo, fonts, theme colors, borders, formulas, and ensures NO clipped text.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import json
import math
import os
import sys

# Locate the project independently of the drive letter on this computer.
_WORKSPACE_ROOT = next((p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'pm_portal' / 'app').is_dir()), __import__('pathlib').Path.cwd())
def _workspace_path(relative):
    return str(_WORKSPACE_ROOT / relative.replace(chr(92), '/'))

def compute_cell_lines(text, col_width_chars):
    if not text:
        return 1
    paragraphs = str(text).split('\n')
    total_rendered = 0
    # Effective width in character units
    usable_width = max(col_width_chars - 2.5, 5.0)
    for p in paragraphs:
        if not p.strip():
            total_rendered += 1
            continue
        # In Excel font 微軟正黑體 12pt:
        # CJK characters (ord > 1279 or ideographs) take ~1.9 units
        # Latin uppercase ~1.2, lowercase ~0.95
        weight = 0.0
        for ch in p:
            code = ord(ch)
            if (0x4E00 <= code <= 0x9FFF) or (0x3400 <= code <= 0x4DBF) or (0xF900 <= code <= 0xFAFF) or code > 1279:
                weight += 1.95
            elif ch.isupper():
                weight += 1.2
            else:
                weight += 0.95
        lines_for_p = max(1, math.ceil(weight / usable_width))
        total_rendered += lines_for_p
    return max(1, total_rendered)

def compute_item_row_height(item, col_widths):
    lines_b = compute_cell_lines(item.get("product_name", ""), col_widths.get('B', 27.5))
    lines_c = compute_cell_lines(item.get("category", ""), col_widths.get('C', 23.5))
    lines_d = compute_cell_lines(item.get("description", ""), col_widths.get('D', 60.0))
    
    max_lines = max(lines_b, lines_c, lines_d)
    # 12pt font with 1.25 line height + top/bottom padding
    height = max_lines * 19.5 + 16.0
    return max(38.0, height)

def generate_perfect_energy_quotation(json_path, output_excel_path):
    with open(json_path, 'r', encoding='utf-8') as jf:
        data = json.load(jf)
        
    template_path = _workspace_path('HM浤詺資訊_Vonmax弘聲 機聯網暨工廠節能 第二階段 硬體報價單_202603_V1.5.xlsx')
    wb = openpyxl.load_workbook(template_path)
    
    # Keep only the target sheet '節能專案報價'
    for sname in list(wb.sheetnames):
        if sname != '節能專案報價':
            del wb[sname]
            
    ws = wb['節能專案報價']
    
    # 1. Ensure Column Widths are generous to prevent horizontal clipping
    col_widths = {
        'A': 5.33,
        'B': 28.0,
        'C': 24.0,
        'D': 60.0,
        'E': 17.5,
        'F': 28.0,
        'G': 27.0
    }
    for col_l, w in col_widths.items():
        ws.column_dimensions[col_l].width = w

    # 2. Update Header / Seller / Buyer info
    seller = data.get("seller_info", {})
    if seller.get("company_name"):
        ws["D4"].value = seller["company_name"]
    if seller.get("contact_person"):
        ws["D5"].value = seller["contact_person"]
    if seller.get("phone"):
        ws["D6"].value = str(seller["phone"])
    if seller.get("fax"):
        ws["D7"].value = str(seller["fax"])
    if seller.get("address"):
        ws["D8"].value = seller["address"]
    if seller.get("email"):
        ws["D9"].value = seller["email"]

    buyer = data.get("buyer_info", {})
    if buyer.get("company_name"):
        ws["F4"].value = buyer["company_name"]
    if buyer.get("contact_person"):
        ws["F5"].value = buyer["contact_person"]
    if buyer.get("phone"):
        ws["F6"].value = str(buyer["phone"])
    if buyer.get("fax"):
        ws["F7"].value = str(buyer["fax"])
    if buyer.get("address"):
        ws["F8"].value = buyer["address"]
    if buyer.get("email"):
        ws["F9"].value = buyer["email"]

    # Adjust row 8 height if addresses are long
    addr_lines_d = compute_cell_lines(ws["D8"].value, col_widths['D'])
    addr_lines_f = compute_cell_lines(ws["F8"].value, col_widths['F'] + col_widths['G'])
    ws.row_dimensions[8].height = max(45.6, max(addr_lines_d, addr_lines_f) * 16.0 + 10.0)

    # Quotation Date
    meta = data.get("quotation_header", {})
    if meta.get("quotation_date"):
        ws["A12"].value = f"報價日期Ngày báo giá: {meta['quotation_date']}"

    # 3. Clean and unmerge previous dynamic rows below row 13
    for rng in list(ws.merged_cells.ranges):
        if rng.min_row >= 14:
            ws.unmerge_cells(str(rng))

    # Section header style
    sec_fill = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")
    sec_font = Font(name="微軟正黑體", size=14.0, bold=True)
    
    # Medium outer border side & Thin inner border side
    medium_side = Side(style='medium', color='000000')
    thin_side = Side(style='thin', color='000000')

    # 4. Populate Section and Item Rows dynamically
    cur_row = 14
    item_rows = []

    for section in data.get("sections", []):
        sec_title = section.get("section_title", "")
        # Render Section Header Row
        ws.row_dimensions[cur_row].height = 24.0
        for col_idx in range(1, 8):
            c = ws.cell(cur_row, col_idx)
            c.fill = sec_fill
            c.font = sec_font
            c.alignment = Alignment(horizontal="left", vertical="center")
            c.border = Border(
                left=medium_side if col_idx == 1 else None,
                right=medium_side if col_idx == 7 else None,
                top=medium_side,
                bottom=thin_side
            )
        ws.cell(cur_row, 1).value = sec_title
        ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=7)
        cur_row += 1

        for item in section.get("items", []):
            item_rows.append(cur_row)
            # Compute perfect height to ensure NO CLIPPING
            r_height = compute_item_row_height(item, col_widths)
            ws.row_dimensions[cur_row].height = r_height

            for col_idx in range(1, 8):
                c = ws.cell(cur_row, col_idx)
                c.font = Font(name="微軟正黑體", size=12.0, bold=False)
                c.fill = PatternFill(fill_type=None)
                
                # Borders: medium on left/right outer boundaries, thin inside
                c.border = Border(
                    left=medium_side if col_idx == 1 else thin_side,
                    right=medium_side if col_idx == 7 else thin_side,
                    top=thin_side,
                    bottom=thin_side
                )

            # Cell values & alignments
            c_a = ws.cell(cur_row, 1)
            c_a.value = str(item.get("stt", ""))
            c_a.alignment = Alignment(horizontal="center", vertical="center")

            c_b = ws.cell(cur_row, 2)
            c_b.value = item.get("product_name", "")
            c_b.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            c_c = ws.cell(cur_row, 3)
            c_c.value = item.get("category", "")
            c_c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            c_d = ws.cell(cur_row, 4)
            c_d.value = item.get("description", "")
            c_d.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            qty = item.get("quantity", 1)
            unit_str = item.get("unit", "CÁI")
            c_e = ws.cell(cur_row, 5)
            c_e.value = qty
            c_e.font = Font(name="微軟正黑體", size=11.0, bold=False)
            c_e.alignment = Alignment(horizontal="center", vertical="center")
            c_e.number_format = f'0\\ "{unit_str}"\\ '

            price = item.get("unit_price", 0)
            c_f = ws.cell(cur_row, 6)
            c_f.value = price
            c_f.alignment = Alignment(horizontal="right", vertical="center")
            c_f.number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'

            c_g = ws.cell(cur_row, 7)
            c_g.value = f"=F{cur_row}*E{cur_row}"
            c_g.alignment = Alignment(horizontal="right", vertical="center")
            c_g.number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'

            cur_row += 1

    # 5. Row: 以下空白
    ws.row_dimensions[cur_row].height = 18.0
    for col_idx in range(1, 8):
        c = ws.cell(cur_row, col_idx)
        c.font = Font(name="微軟正黑體", size=10.0, bold=False)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = Border(
            left=medium_side if col_idx == 1 else thin_side,
            right=medium_side if col_idx == 7 else thin_side,
            top=thin_side,
            bottom=thin_side
        )
    ws.cell(cur_row, 1).value = "以下空白"
    ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=7)
    cur_row += 1

    # 6. Total Row: TỔNG THÀNH TIỀN 總價
    total_row = cur_row
    ws.row_dimensions[total_row].height = 24.0
    for col_idx in range(1, 8):
        c = ws.cell(total_row, col_idx)
        c.border = Border(
            left=medium_side if col_idx == 1 else thin_side,
            right=medium_side if col_idx == 7 else thin_side,
            top=thin_side,
            bottom=medium_side
        )
    # Merge A to E for aesthetic balance
    ws.cell(total_row, 1).value = ""
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=5)

    c_tot_lbl = ws.cell(total_row, 6)
    c_tot_lbl.value = "TỔNG THÀNH TIỀN 總價"
    c_tot_lbl.fill = PatternFill(start_color="FFFFFF00", end_color="FFFFFF00", fill_type="solid")
    c_tot_lbl.font = Font(name="Arial", size=11.0, bold=True, color="0000FF")
    c_tot_lbl.alignment = Alignment(horizontal="center", vertical="center")

    first_item_row = item_rows[0] if item_rows else 14
    last_item_row = item_rows[-1] if item_rows else 14
    c_tot_val = ws.cell(total_row, 7)
    c_tot_val.value = f"=SUM(G{first_item_row}:G{last_item_row})"
    c_tot_val.font = Font(name="Arial", size=12.0, bold=True)
    c_tot_val.alignment = Alignment(horizontal="right", vertical="center")
    c_tot_val.number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'
    cur_row += 1

    # 7. Customer Confirmation Header & Notes Header
    header_notes_row = cur_row
    ws.row_dimensions[header_notes_row].height = 28.2
    
    # Left header: ※客戶確認 Xác nhận khách hàng
    # Soft Peach fill (#FCE4D6)
    peach_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    for col_idx in range(1, 4):
        c = ws.cell(header_notes_row, col_idx)
        c.fill = peach_fill
        c.font = Font(name="Arial", size=11.0, bold=False, color="9C6500")
        c.alignment = Alignment(horizontal="left", vertical="center")
        c.border = Border(
            left=medium_side if col_idx == 1 else None,
            right=thin_side if col_idx == 3 else None,
            top=medium_side,
            bottom=None
        )
    ws.cell(header_notes_row, 1).value = "※客戶確認 Xác nhận khách hàng"
    ws.merge_cells(start_row=header_notes_row, start_column=1, end_row=header_notes_row, end_column=3)

    # Right header: ◆ 備註聲明 Ghi Chú và Tuyên Bố
    # Soft Blue fill (#D9E1F2)
    soft_blue_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    for col_idx in range(4, 8):
        c = ws.cell(header_notes_row, col_idx)
        c.fill = soft_blue_fill
        c.font = Font(name="Microsoft YaHei", size=11.0, bold=True, color="1F4E79")
        c.alignment = Alignment(horizontal="left", vertical="center")
        c.border = Border(
            left=thin_side if col_idx == 4 else None,
            right=medium_side if col_idx == 7 else None,
            top=medium_side,
            bottom=None
        )
    ws.cell(header_notes_row, 4).value = "◆ 備註聲明 Ghi Chú và Tuyên Bố"
    ws.merge_cells(start_row=header_notes_row, start_column=4, end_row=header_notes_row, end_column=7)
    cur_row += 1

    # 8. Notes Rows (D:G) & Signature Box (A:C)
    notes = data.get("terms_and_notes", [])
    sig_start_row = cur_row
    
    # Specific colors for each note as in original template:
    # Note 1: Black/Bold
    # Note 2: Black/Bold
    # Note 3: Red/Bold (#FF0000)
    # Note 4: Blue/Bold (#0000FF)
    # Note 5: Red/Bold (#FF0000)
    note_colors = ["000000", "000000", "FF0000", "0000FF", "FF0000"]

    for idx, note_text in enumerate(notes):
        n_row = cur_row
        # Compute lines in note text (across cols D to G = width ~ 132 chars)
        note_lines = compute_cell_lines(note_text, 130.0)
        ws.row_dimensions[n_row].height = max(52.0, note_lines * 18.0 + 16.0)

        # Style signature col A-C
        is_last_note = (idx == len(notes) - 1)
        for col_idx in range(1, 4):
            c = ws.cell(n_row, col_idx)
            c.fill = peach_fill
            c.font = Font(name="Arial", size=11.0, bold=False, color="9C6500")
            c.border = Border(
                left=medium_side if col_idx == 1 else None,
                right=thin_side if col_idx == 3 else None,
                top=None,
                bottom=medium_side if is_last_note else None
            )

        # Style note col D-G
        n_color = note_colors[min(idx, len(note_colors)-1)]
        for col_idx in range(4, 8):
            c = ws.cell(n_row, col_idx)
            c.fill = soft_blue_fill
            c.font = Font(name="Microsoft YaHei", size=11.0, bold=True, color=n_color)
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            c.border = Border(
                left=thin_side if col_idx == 4 else None,
                right=medium_side if col_idx == 7 else None,
                top=None,
                bottom=medium_side if is_last_note else None
            )

        ws.cell(n_row, 4).value = note_text
        ws.merge_cells(start_row=n_row, start_column=4, end_row=n_row, end_column=7)
        cur_row += 1

    # Merge signature block A:C across all note rows
    sig_end_row = cur_row - 1
    ws.cell(sig_start_row, 1).value = "（請簽名用印） Chữ ký và con dấu"
    ws.cell(sig_start_row, 1).alignment = Alignment(horizontal="left", vertical="top")
    ws.merge_cells(start_row=sig_start_row, start_column=1, end_row=sig_end_row, end_column=3)

    # 9. Clean any leftover rows below cur_row (if template had more rows originally)
    if cur_row <= ws.max_row:
        for r_clean in range(cur_row, ws.max_row + 1):
            for c_clean in range(1, 8):
                c = ws.cell(r_clean, c_clean)
                c.value = None
                c.fill = PatternFill(fill_type=None)
                c.border = Border()

    # 10. Set View to Page Break Preview & Print Area for the clean blue border!
    ws.views.sheetView[0].view = "pageBreakPreview"
    ws.views.sheetView[0].showGridLines = True
    ws.print_area = f"$A$1:$G${cur_row-1}"
    
    # Page Setup
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    wb.save(output_excel_path)
    print(f"Perfect 1:1 quotation excel generated at: {output_excel_path}")

if __name__ == "__main__":
    json_in = _workspace_path('du_lieu_bao_gia_mau.json')
    excel_out = _workspace_path('BAO_GIA_TIET_KIEM_DIEN_TU_JSON.xlsx')
    generate_perfect_energy_quotation(json_in, excel_out)
