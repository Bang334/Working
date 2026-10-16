"""Quotation Word document (.docx) generator for Hong Ming Global."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)


def set_cell_shading(cell, color_hex: str):
    """Set background fill color for docx table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    """Set inner cell padding in dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_table_borders(table, color="B0C4DE", sz="4", val="single"):
    """Apply neat professional borders to Word table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def sanitize_filename(name: str) -> str:
    """Make safe filename removing invalid characters."""
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', str(name or "")).strip()
    cleaned = re.sub(r'\s+', '_', cleaned)
    return cleaned[:60] if cleaned else "Bao_Gia"


def generate_quotation_word(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate official bilingual Vietnamese - Traditional Chinese Quotation Word document (.docx)."""
    target_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Prepare data & calculations
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

    # 2. Build Document
    doc = Document()

    # Standard A4 margins (0.6 in left/right, 0.7 in top/bottom)
    for sec in doc.sections:
        sec.top_margin = Inches(0.7)
        sec.bottom_margin = Inches(0.7)
        sec.left_margin = Inches(0.65)
        sec.right_margin = Inches(0.65)

    # Company Header (Bên Bán - Hong Ming Global)
    p_comp = doc.add_paragraph()
    p_comp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_comp.paragraph_format.space_after = Pt(2)
    p_comp.paragraph_format.line_spacing = 1.15

    r_c1 = p_comp.add_run("CÔNG TY TNHH TOÀN CẦU HONG MING\n")
    r_c1.bold = True
    r_c1.font.name = "Times New Roman"
    r_c1.font.size = Pt(13)
    r_c1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    r_c2 = p_comp.add_run("宏明環球有限公司 — HONG MING GLOBAL CO., LTD.\n")
    r_c2.bold = True
    r_c2.font.name = "Times New Roman"
    r_c2.font.size = Pt(11)
    r_c2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    r_c3 = p_comp.add_run(
        "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh, Việt Nam\n"
        "MST / 統一編號: 0318280158  |  Hotline: +84 966 687 109  |  Email: sales@hongming-global.com\n"
    )
    r_c3.font.name = "Times New Roman"
    r_c3.font.size = Pt(9.5)
    r_c3.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    r_div = p_comp.add_run("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    r_div.font.size = Pt(8)
    r_div.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(8)
    p_title.paragraph_format.space_after = Pt(10)

    r_t1 = p_title.add_run("BẢNG BÁO GIÁ THIẾT BỊ & DỊCH VỤ KỸ THUẬT\n")
    r_t1.bold = True
    r_t1.font.name = "Times New Roman"
    r_t1.font.size = Pt(15)
    r_t1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    r_t2 = p_title.add_run("設備及工程服務報價單 (QUOTATION)\n")
    r_t2.bold = True
    r_t2.font.name = "Times New Roman"
    r_t2.font.size = Pt(12.5)
    r_t2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    r_t3 = p_title.add_run(f"Dự Án / 專案: {project_name}")
    r_t3.italic = True
    r_t3.font.name = "Times New Roman"
    r_t3.font.size = Pt(11)

    # Customer & Meta Information Table (4-column sleek table)
    meta_table = doc.add_table(rows=4, cols=4)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(meta_table, color="D1D5DB", sz="4")

    # Set column widths
    meta_widths = [Inches(1.5), Inches(2.2), Inches(1.3), Inches(2.07)]
    for row in meta_table.rows:
        for idx, w in enumerate(meta_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=80, bottom=80, left=100, right=100)

    # Row 0: Khách hàng & Số báo giá
    c00 = meta_table.cell(0, 0)
    c00.paragraphs[0].add_run("Kính gửi / 買方:").bold = True
    c00.paragraphs[0].runs[0].font.name = "Times New Roman"
    c00.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c00, "F8FAFC")

    c01 = meta_table.cell(0, 1)
    c01.paragraphs[0].add_run(f"{cust_vi}\n{cust_zh}").bold = True
    c01.paragraphs[0].runs[0].font.name = "Times New Roman"
    c01.paragraphs[0].runs[0].font.size = Pt(9.5)

    c02 = meta_table.cell(0, 2)
    c02.paragraphs[0].add_run("Số Báo Giá / 報價編號:").bold = True
    c02.paragraphs[0].runs[0].font.name = "Times New Roman"
    c02.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c02, "F8FAFC")

    c03 = meta_table.cell(0, 3)
    c03.paragraphs[0].add_run(quote_no).bold = True
    c03.paragraphs[0].runs[0].font.name = "Times New Roman"
    c03.paragraphs[0].runs[0].font.size = Pt(10)
    c03.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    # Row 1: MST & Ngày phát hành
    c10 = meta_table.cell(1, 0)
    c10.paragraphs[0].add_run("MST / 統一編號:").bold = True
    c10.paragraphs[0].runs[0].font.name = "Times New Roman"
    c10.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c10, "F8FAFC")

    c11 = meta_table.cell(1, 1)
    c11.paragraphs[0].add_run(tax_code or "Theo thông tin hợp đồng")
    c11.paragraphs[0].runs[0].font.name = "Times New Roman"
    c11.paragraphs[0].runs[0].font.size = Pt(9.5)

    c12 = meta_table.cell(1, 2)
    c12.paragraphs[0].add_run("Ngày Báo Giá / 報價日期:").bold = True
    c12.paragraphs[0].runs[0].font.name = "Times New Roman"
    c12.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c12, "F8FAFC")

    c13 = meta_table.cell(1, 3)
    c13.paragraphs[0].add_run(quote_date)
    c13.paragraphs[0].runs[0].font.name = "Times New Roman"
    c13.paragraphs[0].runs[0].font.size = Pt(9.5)

    # Row 2: Người liên hệ & Hiệu lực
    c20 = meta_table.cell(2, 0)
    c20.paragraphs[0].add_run("Người liên hệ / 聯絡人:").bold = True
    c20.paragraphs[0].runs[0].font.name = "Times New Roman"
    c20.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c20, "F8FAFC")

    c21 = meta_table.cell(2, 1)
    c21.paragraphs[0].add_run(contact_person or "Ban Giám Đốc / Phòng Mua Hàng")
    c21.paragraphs[0].runs[0].font.name = "Times New Roman"
    c21.paragraphs[0].runs[0].font.size = Pt(9.5)

    c22 = meta_table.cell(2, 2)
    c22.paragraphs[0].add_run("Thời Hạn Hiệu Lực / 有效期:").bold = True
    c22.paragraphs[0].runs[0].font.name = "Times New Roman"
    c22.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c22, "F8FAFC")

    c23 = meta_table.cell(2, 3)
    c23.paragraphs[0].add_run(validity)
    c23.paragraphs[0].runs[0].font.name = "Times New Roman"
    c23.paragraphs[0].runs[0].font.size = Pt(9.5)

    # Row 3: Đơn vị chào giá (Hong Ming Global)
    c30 = meta_table.cell(3, 0)
    c30.paragraphs[0].add_run("Đơn vị báo giá / 賣方:").bold = True
    c30.paragraphs[0].runs[0].font.name = "Times New Roman"
    c30.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c30, "F8FAFC")

    c31 = meta_table.cell(3, 1)
    c31.paragraphs[0].add_run("CÔNG TY TNHH TOÀN CẦU HONG MING (浤詺資訊)")
    c31.paragraphs[0].runs[0].font.name = "Times New Roman"
    c31.paragraphs[0].runs[0].font.size = Pt(9.5)

    c32 = meta_table.cell(3, 2)
    c32.paragraphs[0].add_run("Đại diện KD / 業務窗口:").bold = True
    c32.paragraphs[0].runs[0].font.name = "Times New Roman"
    c32.paragraphs[0].runs[0].font.size = Pt(9.5)
    set_cell_shading(c32, "F8FAFC")

    c33 = meta_table.cell(3, 3)
    c33.paragraphs[0].add_run("Jenson Chang (+84 966 687 109)")
    c33.paragraphs[0].runs[0].font.name = "Times New Roman"
    c33.paragraphs[0].runs[0].font.size = Pt(9.5)

    # Spacing
    p_sp1 = doc.add_paragraph()
    p_sp1.paragraph_format.space_before = Pt(8)
    p_sp1.paragraph_format.space_after = Pt(2)
    p_sp1_run = p_sp1.add_run("DANH MỤC THIẾT BỊ, VẬT TƯ & CHI PHÍ THI CÔNG / 項目規格及報價明細:")
    p_sp1_run.bold = True
    p_sp1_run.font.name = "Times New Roman"
    p_sp1_run.font.size = Pt(11)
    p_sp1_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    # 3. Items Table
    col_widths = [Inches(0.45), Inches(3.12), Inches(0.65), Inches(0.55), Inches(1.15), Inches(1.15)]
    table = doc.add_table(rows=1 + len(items) + 4, cols=6)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="1F4E79", sz="4")

    # Header Row
    headers = [
        "STT\n序號",
        "Tên Thiết Bị / Quy Cách Kỹ Thuật\n產品名稱及規格說明",
        "ĐVT\n單位",
        "SL\n數量",
        "Đơn Giá (VND)\n單價",
        "Thành Tiền (VND)\n金額"
    ]
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=60, right=60)
        set_cell_shading(hdr_cells[i], "1F4E79")
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data Rows
    for idx, item in enumerate(items, start=1):
        row_cells = table.rows[idx].cells
        for col_idx, w in enumerate(col_widths):
            row_cells[col_idx].width = w
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=70, right=70)
            if idx % 2 == 0:
                set_cell_shading(row_cells[col_idx], "F8FAFC")

        # STT
        p0 = row_cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(item["stt"]))
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(9.5)

        # Name
        p1 = row_cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p1.add_run(item["name"])
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(9.5)

        # Unit
        p2 = row_cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(item["unit"])
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(9.5)

        # Qty
        p3 = row_cells[3].paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = p3.add_run(str(item["qty"]))
        r3.font.name = "Times New Roman"
        r3.font.size = Pt(9.5)

        # Unit Price
        p4 = row_cells[4].paragraphs[0]
        p4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r4 = p4.add_run(f"{item['price']:,}".replace(",", "."))
        r4.font.name = "Times New Roman"
        r4.font.size = Pt(9.5)

        # Row Total
        p5 = row_cells[5].paragraphs[0]
        p5.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r5 = p5.add_run(f"{item['total']:,}".replace(",", "."))
        r5.bold = True
        r5.font.name = "Times New Roman"
        r5.font.size = Pt(9.5)

    # Summary Row 1: Subtotal (merge cells 0 to 4)
    r_sub_idx = 1 + len(items)
    row_sub = table.rows[r_sub_idx]
    row_sub.cells[0].merge(row_sub.cells[4])
    set_cell_margins(row_sub.cells[0], top=80, bottom=80, left=100, right=100)
    set_cell_margins(row_sub.cells[5], top=80, bottom=80, left=70, right=70)
    set_cell_shading(row_sub.cells[0], "F1F5F9")
    set_cell_shading(row_sub.cells[5], "F1F5F9")

    p_sub_lbl = row_sub.cells[0].paragraphs[0]
    p_sub_lbl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_sub_l = p_sub_lbl.add_run("Tổng cộng tiền hàng (Chưa thuế VAT) / 小計 (未含稅): ")
    r_sub_l.bold = True
    r_sub_l.font.name = "Times New Roman"
    r_sub_l.font.size = Pt(9.5)

    p_sub_val = row_sub.cells[5].paragraphs[0]
    p_sub_val.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_sub_v = p_sub_val.add_run(f"{subtotal:,}".replace(",", ".") + " VND")
    r_sub_v.bold = True
    r_sub_v.font.name = "Times New Roman"
    r_sub_v.font.size = Pt(9.5)

    # Summary Row 2: VAT 10%
    r_vat_idx = r_sub_idx + 1
    row_vat = table.rows[r_vat_idx]
    row_vat.cells[0].merge(row_vat.cells[4])
    set_cell_margins(row_vat.cells[0], top=80, bottom=80, left=100, right=100)
    set_cell_margins(row_vat.cells[5], top=80, bottom=80, left=70, right=70)
    set_cell_shading(row_vat.cells[0], "F1F5F9")
    set_cell_shading(row_vat.cells[5], "F1F5F9")

    p_vat_lbl = row_vat.cells[0].paragraphs[0]
    p_vat_lbl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_vat_l = p_vat_lbl.add_run("Thuế suất GTGT (VAT 10%) / 增值稅 (10%): ")
    r_vat_l.bold = True
    r_vat_l.font.name = "Times New Roman"
    r_vat_l.font.size = Pt(9.5)

    p_vat_val = row_vat.cells[5].paragraphs[0]
    p_vat_val.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_vat_v = p_vat_val.add_run(f"{vat:,}".replace(",", ".") + " VND")
    r_vat_v.bold = True
    r_vat_v.font.name = "Times New Roman"
    r_vat_v.font.size = Pt(9.5)

    # Summary Row 3: Grand Total
    r_gt_idx = r_vat_idx + 1
    row_gt = table.rows[r_gt_idx]
    row_gt.cells[0].merge(row_gt.cells[4])
    set_cell_margins(row_gt.cells[0], top=100, bottom=100, left=100, right=100)
    set_cell_margins(row_gt.cells[5], top=100, bottom=100, left=70, right=70)
    set_cell_shading(row_gt.cells[0], "E0F2FE")
    set_cell_shading(row_gt.cells[5], "E0F2FE")

    p_gt_lbl = row_gt.cells[0].paragraphs[0]
    p_gt_lbl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_gt_l = p_gt_lbl.add_run("TỔNG CỘNG THANH TOÁN (ĐÃ VAT) / 總計 (含稅): ")
    r_gt_l.bold = True
    r_gt_l.font.name = "Times New Roman"
    r_gt_l.font.size = Pt(10.5)
    r_gt_l.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    p_gt_val = row_gt.cells[5].paragraphs[0]
    p_gt_val.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_gt_v = p_gt_val.add_run(f"{grand_total:,}".replace(",", ".") + " VND")
    r_gt_v.bold = True
    r_gt_v.font.name = "Times New Roman"
    r_gt_v.font.size = Pt(11)
    r_gt_v.font.color.rgb = RGBColor(0x15, 0x80, 0x3D)

    # Summary Row 4: Amount in Words (Vietnamese & Chinese)
    r_words_idx = r_gt_idx + 1
    row_words = table.rows[r_words_idx]
    row_words.cells[0].merge(row_words.cells[5])
    set_cell_margins(row_words.cells[0], top=90, bottom=90, left=100, right=100)
    set_cell_shading(row_words.cells[0], "F8FAFC")

    p_words = row_words.cells[0].paragraphs[0]
    p_words.paragraph_format.line_spacing = 1.2
    rw1 = p_words.add_run("• Số tiền bằng chữ: ")
    rw1.bold = True
    rw1.font.name = "Times New Roman"
    rw1.font.size = Pt(9.5)
    rw1_val = p_words.add_run(f"{vietnamese_words}\n")
    rw1_val.italic = True
    rw1_val.font.name = "Times New Roman"
    rw1_val.font.size = Pt(9.5)

    rw2 = p_words.add_run("• 大寫金額 (中文): ")
    rw2.bold = True
    rw2.font.name = "Times New Roman"
    rw2.font.size = Pt(9.5)
    rw2_val = p_words.add_run(chinese_words)
    rw2_val.italic = True
    rw2_val.font.name = "Times New Roman"
    rw2_val.font.size = Pt(9.5)

    # 4. Commercial Terms & Warranty
    p_terms = doc.add_paragraph()
    p_terms.paragraph_format.space_before = Pt(10)
    p_terms.paragraph_format.space_after = Pt(2)
    p_terms.paragraph_format.line_spacing = 1.25

    rt_hdr = p_terms.add_run("ĐIỀU KHOẢN THƯƠNG MẠI & BẢO HÀNH / 商務條款及保固說明:\n")
    rt_hdr.bold = True
    rt_hdr.font.name = "Times New Roman"
    rt_hdr.font.size = Pt(10.5)
    rt_hdr.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    terms_list = [
        ("1. Thời hạn hiệu lực / 報價有效期: ", validity),
        ("2. Thời gian giao hàng / 交貨期: ", lead_time),
        ("3. Thời hạn bảo hành / 保固期: ", warranty),
        ("4. Điều kiện thanh toán / 付款條件: ", payment_terms),
    ]
    if notes:
        terms_list.append(("5. Ghi chú kỹ thuật bổ sung / 備註: ", notes))

    for label, val in terms_list:
        p_t = doc.add_paragraph()
        p_t.paragraph_format.space_before = Pt(1)
        p_t.paragraph_format.space_after = Pt(2)
        r_lbl = p_t.add_run(f"• {label}")
        r_lbl.bold = True
        r_lbl.font.name = "Times New Roman"
        r_lbl.font.size = Pt(9.5)
        r_val = p_t.add_run(val)
        r_val.font.name = "Times New Roman"
        r_val.font.size = Pt(9.5)

    # 5. Signature Table
    sig_table = doc.add_table(rows=2, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_widths = [Inches(3.5), Inches(3.57)]
    for r in sig_table.rows:
        for idx, w in enumerate(sig_widths):
            r.cells[idx].width = w

    # Row 0: Titles
    p_s0 = sig_table.cell(0, 0).paragraphs[0]
    p_s0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_s0.paragraph_format.space_before = Pt(12)
    rs0 = p_s0.add_run("ĐẠI DIỆN BÊN MUA (BÊN A)\n買方代表簽署確認\n")
    rs0.bold = True
    rs0.font.name = "Times New Roman"
    rs0.font.size = Pt(10.5)
    rs0_sub = p_s0.add_run("(Ký tên, đóng dấu & ghi rõ họ tên / 簽名蓋章)")
    rs0_sub.italic = True
    rs0_sub.font.name = "Times New Roman"
    rs0_sub.font.size = Pt(9)

    p_s1 = sig_table.cell(0, 1).paragraphs[0]
    p_s1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_s1.paragraph_format.space_before = Pt(12)
    rs1 = p_s1.add_run("ĐẠI DIỆN BÊN BÁN (BÊN B)\nCÔNG TY TNHH TOÀN CẦU HONG MING\n宏明環球有限公司\n")
    rs1.bold = True
    rs1.font.name = "Times New Roman"
    rs1.font.size = Pt(10.5)
    rs1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    rs1_sub = p_s1.add_run("(Tổng Giám Đốc: TANG WEI LI / 總經理)")
    rs1_sub.italic = True
    rs1_sub.font.name = "Times New Roman"
    rs1_sub.font.size = Pt(9)

    # Row 1: Space for physical signature
    p_sp0 = sig_table.cell(1, 0).paragraphs[0]
    p_sp0.paragraph_format.space_before = Pt(50)
    p_sp0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sp0.add_run("______________________________\nNgày / 日期: ..... / ..... / 2026").font.size = Pt(9)

    p_sp1 = sig_table.cell(1, 1).paragraphs[0]
    p_sp1.paragraph_format.space_before = Pt(50)
    p_sp1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sp1.add_run("______________________________\nNgày / 日期: ..... / ..... / 2026").font.size = Pt(9)

    # 6. Save File with PermissionError fallback
    clean_cust = sanitize_filename(cust_vi)
    clean_quote = sanitize_filename(quote_no)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"Bao_Gia_{clean_cust}_{clean_quote}_{timestamp}.docx"
    output_path = target_dir / file_name

    try:
        doc.save(str(output_path))
    except PermissionError:
        file_name = f"Bao_Gia_{clean_cust}_{clean_quote}_{timestamp}_v2.docx"
        output_path = target_dir / file_name
        doc.save(str(output_path))

    # 7. Index into SQLite documents table
    file_size = output_path.stat().st_size if output_path.is_file() else 0
    try:
        from app.database import index_single_document
        index_single_document(
            contract_code="",
            doc_type="BAO_GIA",
            doc_name=f"Báo Giá ({quote_no}) - {cust_vi}",
            file_name=file_name,
            file_path=str(output_path),
            file_size=file_size,
            file_format="docx",
            description=f"Bảng báo giá thiết bị: {cust_vi} [Số: {quote_no}]"
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"Đã xuất thành công Báo giá Word (.docx) cho {cust_vi}!",
        "file_name": file_name,
        "file_path": str(output_path),
        "download_url": f"/api/v1/quotation/download/{file_name}",
        "total_amount": grand_total,
        "total_amount_formatted": f"{grand_total:,}".replace(",", ".") + " VND",
        "customer_name": cust_vi,
        "quotation_no": quote_no,
    }
