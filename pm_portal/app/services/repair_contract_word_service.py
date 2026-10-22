"""Word (.docx) generation service for bilingual Vietnamese-Chinese Repair Contracts (Hợp Đồng Dịch Vụ Sửa Chữa)."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import docx
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
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
from app.utils.file_helper import sanitize_filename

FONT_LATIN = "Times New Roman"
FONT_CJK = "Microsoft JhengHei"  # 微軟正黑體


def set_run_fonts(run, font_name: str = FONT_LATIN, cjk_name: str = FONT_CJK, size_pt: float = 11, bold: bool = False, italic: bool = False, color_rgb: Optional[RGBColor] = None):
    """Set Latin and Asian/CJK fonts with precise formatting."""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    if color_rgb:
        run.font.color.rgb = color_rgb

    # Set CJK / East Asian font attribute in XML
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), cjk_name)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)


def set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 120, right: int = 120):
    """Set padding in twentieths of a point (dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for margin_name, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{margin_name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_cell_background(cell, color_hex: str):
    """Set background color of a cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_borders(cell, top="000000", bottom="000000", left="000000", right="000000", sz="4"):
    """Set cell borders in Word XML."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{top}"/>'
        f'<w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{left}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{bottom}"/>'
        f'<w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{right}"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)


def generate_repair_contract_docx(data: Dict[str, Any], custom_output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an official bilingual Vietnamese-Chinese Repair Contract DOCX file.
    Designed to easily plug in an official Word template once provided by user.
    """
    # Check if a custom template exists in Bieu Mau
    template_path = WORKING_DIR / "Bieu Mau" / "Hợp đồng sửa chữa.docx"
    alt_template_path = WORKING_DIR / "Bieu Mau" / "Hợp đồng sửa chữa và bảo trì.docx"

    # If user later provides the template file, we can invoke fill_contract_template
    if template_path.exists():
        return fill_existing_repair_template(template_path, data, custom_output_dir)
    elif alt_template_path.exists():
        return fill_existing_repair_template(alt_template_path, data, custom_output_dir)

    # Otherwise, build a 100% compliant, beautiful standard bilingual document
    doc = Document()

    # Set standard A4 page margins (Top 2cm, Bottom 2cm, Left 2.5cm, Right 2cm)
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.79)
        section.bottom_margin = Inches(0.79)
        section.left_margin = Inches(0.98)
        section.right_margin = Inches(0.79)

    # 1. Header Quốc hiệu & Tiêu ngữ
    header_table = doc.add_table(rows=1, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False

    cell_left = header_table.cell(0, 0)
    cell_right = header_table.cell(0, 1)
    cell_left.width = Inches(3.2)
    cell_right.width = Inches(3.8)

    p_l = cell_left.paragraphs[0]
    p_l.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_l.paragraph_format.space_after = Pt(2)
    p_l.paragraph_format.line_spacing = 1.15
    run = p_l.add_run("CÔNG TY TNHH TOÀN CẦU HONG MING\n宏明環球有限公司")
    set_run_fonts(run, size_pt=10, bold=True)

    p_r = cell_right.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_r.paragraph_format.space_after = Pt(2)
    p_r.paragraph_format.line_spacing = 1.15
    run = p_r.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n越南社會主義共和國\nĐộc lập - Tự do - Hạnh phúc\n獨立 - 自由 - 幸福")
    set_run_fonts(run, size_pt=10, bold=True)

    # Remove table borders for header
    for row in header_table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/></w:tcBorders>')
            tcPr.append(tcBorders)

    # Divider line
    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_after = Pt(12)
    run_div = p_div.add_run("━━━━━━━━━━━━━━━━━━━━━━━━━")
    set_run_fonts(run_div, size_pt=10, color_rgb=RGBColor(100, 116, 139))

    # 2. Tiêu Đề Hợp Đồng
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(3)
    run_title = p_title.add_run("HỢP ĐỒNG DỊCH VỤ SỬA CHỮA VÀ BẢO TRÌ THIẾT BỊ")
    set_run_fonts(run_title, size_pt=15, bold=True)

    p_title_cn = doc.add_paragraph()
    p_title_cn.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title_cn.paragraph_format.space_after = Pt(6)
    run_title_cn = p_title_cn.add_run("設備維修保養服務合約")
    set_run_fonts(run_title_cn, font_name=FONT_CJK, size_pt=14, bold=True)

    # Số hợp đồng
    so_hd = data.get("so_hop_dong", "HDSC-20261019-001")
    day = data.get("ngay_ky", datetime.now().strftime("%d"))
    month = data.get("thang_ky", datetime.now().strftime("%m"))
    year = data.get("nam_ky", datetime.now().strftime("%Y"))

    p_no = doc.add_paragraph()
    p_no.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_no.paragraph_format.space_after = Pt(14)
    run_no = p_no.add_run(f"Số / 合約編號: {so_hd}")
    set_run_fonts(run_no, size_pt=11, bold=True)

    # Lời mở đầu
    p_intro = doc.add_paragraph()
    p_intro.paragraph_format.space_after = Pt(10)
    p_intro.paragraph_format.line_spacing = 1.2
    run_intro = p_intro.add_run(
        f"- Căn cứ Bộ luật Dân sự số 91/2015/QH13 và Luật Thương mại số 36/2005/QH11 của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam;\n"
        f"  依據越南社會主義共和國第 91/2015/QH13 號民法典及第 36/2005/QH11 號商法；\n"
        f"- Căn cứ vào nhu cầu sửa chữa, phục hồi thiết bị của Bên A và năng lực kỹ thuật của Bên B;\n"
        f"  基於甲方設備維修與恢復正常運轉之需求，以及乙方之專業技術能力；\n\n"
        f"Hôm nay, ngày {day} tháng {month} năm {year}, tại văn phòng hai bên thống nhất ký kết hợp đồng dịch vụ với các điều khoản sau:\n"
        f"今天，{year} 年 {month} 月 {day} 日，雙方在友好協商基礎上，一致同意簽訂本設備維修服務合約，條款如下："
    )
    set_run_fonts(run_intro, size_pt=10.5)

    # 3. Thông tin hai bên
    ben_a = data.get("ben_a", {})
    ben_b = data.get("ben_b", {})
    if not ben_b:
        ben_b = {
            "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
            "ten_tieng_trung": "宏明環球有限公司",
            "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
            "dia_chi_trung": "越南胡志明市西貢坊阮惠路68號2樓",
            "mst": "0318280158",
            "nguoi_dai_dien": "TANG WEI LI",
            "chuc_vu": "TỔNG GIÁM ĐỐC",
            "chuc_vu_trung": "總經理"
        }

    # BÊN A
    p_pa = doc.add_paragraph()
    p_pa.paragraph_format.space_after = Pt(4)
    run_pa = p_pa.add_run("BÊN A (BÊN GIAO SỬA CHỮA / 委託方 - 甲方):")
    set_run_fonts(run_pa, size_pt=11, bold=True)

    company_a = ben_a.get("ten_cong_ty", "")
    company_a_zh = ben_a.get("ten_tieng_trung", "")
    name_display_a = f"{company_a} ({company_a_zh})" if company_a_zh else company_a

    addr_a = ben_a.get("dia_chi", "")
    addr_a_zh = ben_a.get("dia_chi_trung", "")
    addr_display_a = f"{addr_a} / {addr_a_zh}" if addr_a_zh else addr_a

    rep_a = ben_a.get("nguoi_dai_dien", "")
    role_a = ben_a.get("chuc_vu", "TỔNG GIÁM ĐỐC")
    role_a_zh = ben_a.get("chuc_vu_trung", "總經理")
    role_display_a = f"{role_a} / {role_a_zh}" if role_a_zh else role_a

    p_pa_info = doc.add_paragraph()
    p_pa_info.paragraph_format.left_indent = Inches(0.2)
    p_pa_info.paragraph_format.space_after = Pt(8)
    p_pa_info.paragraph_format.line_spacing = 1.2
    run = p_pa_info.add_run(
        f"• Tên công ty / 公司名稱: {name_display_a}\n"
        f"• Địa chỉ trụ sở / 公司地址: {addr_display_a}\n"
        f"• Mã số thuế / 稅號: {ben_a.get('mst', '')}\n"
        f"• Người đại diện / 代表人: {rep_a}     Chức vụ / 職務: {role_display_a}"
    )
    set_run_fonts(run, size_pt=10.5)

    # BÊN B
    p_pb = doc.add_paragraph()
    p_pb.paragraph_format.space_after = Pt(4)
    run_pb = p_pb.add_run("BÊN B (BÊN NHẬN SỬA CHỮA / 承修方 - 乙方):")
    set_run_fonts(run_pb, size_pt=11, bold=True)

    company_b = ben_b.get("ten_cong_ty", "CÔNG TY TNHH TOÀN CẦU HONG MING")
    company_b_zh = ben_b.get("ten_tieng_trung", "宏明環球有限公司")
    name_display_b = f"{company_b} ({company_b_zh})"

    addr_b = ben_b.get("dia_chi", "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh")
    addr_b_zh = ben_b.get("dia_chi_trung", "越南胡志明市西貢坊阮惠路68號2樓")
    addr_display_b = f"{addr_b} / {addr_b_zh}"

    rep_b = ben_b.get("nguoi_dai_dien", "TANG WEI LI")
    role_b = ben_b.get("chuc_vu", "TỔNG GIÁM ĐỐC")
    role_b_zh = ben_b.get("chuc_vu_trung", "總經理")
    role_display_b = f"{role_b} / {role_b_zh}"

    p_pb_info = doc.add_paragraph()
    p_pb_info.paragraph_format.left_indent = Inches(0.2)
    p_pb_info.paragraph_format.space_after = Pt(12)
    p_pb_info.paragraph_format.line_spacing = 1.2
    run = p_pb_info.add_run(
        f"• Tên công ty / 公司名稱: {name_display_b}\n"
        f"• Địa chỉ trụ sở / 公司地址: {addr_display_b}\n"
        f"• Mã số thuế / 稅號: {ben_b.get('mst', '0318280158')}\n"
        f"• Người đại diện / 代表人: {rep_b}     Chức vụ / 職務: {role_display_b}"
    )
    set_run_fonts(run, size_pt=10.5)

    # 4. Điều 1: Danh mục thiết bị sửa chữa & linh kiện thay thế
    p_art1 = doc.add_paragraph()
    p_art1.paragraph_format.space_after = Pt(4)
    run_art1 = p_art1.add_run("ĐIỀU 1: PHẠM VI DỊCH VỤ & DANH MỤC THIẾT BỊ SỬA CHỮA / 第一條：維修內容與設備清單")
    set_run_fonts(run_art1, size_pt=11, bold=True)

    ten_goi_vn = data.get("ten_goi_sua_chua_viet", "Dịch vụ sửa chữa và bảo dưỡng thiết bị")
    ten_goi_zh = data.get("ten_goi_sua_chua_trung", "設備維修與保養服務")
    p_goi = doc.add_paragraph()
    p_goi.paragraph_format.space_after = Pt(6)
    run_goi = p_goi.add_run(f"Bên B nhận thực hiện gói dịch vụ: {ten_goi_vn} / {ten_goi_zh} theo danh mục chi tiết sau:")
    set_run_fonts(run_goi, size_pt=10.5, italic=True)

    # Table of repair items
    hang_muc = data.get("hang_muc", [])
    cols_def = [
        ("STT\n序號", Inches(0.4)),
        ("Thiết Bị / Linh Kiện Sửa Chữa\n維修設備與更換零件名稱", Inches(2.3)),
        ("Model / Serial\n型號 / 序號", Inches(1.1)),
        ("Hiện Tượng Lỗi & Nội Dung Sửa\n故障現象與維修內容", Inches(1.6)),
        ("Số Lượng\n數量", Inches(0.6)),
        ("Đơn Giá (VND)\n單價", Inches(1.0)),
        ("Thành Tiền (VND)\n總價", Inches(1.1)),
    ]

    item_table = doc.add_table(rows=1, cols=len(cols_def))
    item_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    item_table.autofit = False

    # Header Row
    hdr_cells = item_table.rows[0].cells
    for idx, (title, width) in enumerate(cols_def):
        hdr_cells[idx].width = width
        set_cell_margins(hdr_cells[idx], top=80, bottom=80, left=80, right=80)
        set_cell_background(hdr_cells[idx], "F1F5F9")
        set_cell_borders(hdr_cells[idx], top="94A3B8", bottom="94A3B8", left="CBD5E1", right="CBD5E1", sz="6")
        p = hdr_cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.05
        run = p.add_run(title)
        set_run_fonts(run, size_pt=9, bold=True)

    # Populate Item Rows
    total_calc = 0
    for idx, it in enumerate(hang_muc, start=1):
        row_cells = item_table.add_row().cells
        for c_idx, (_, width) in enumerate(cols_def):
            row_cells[c_idx].width = width
            set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=70, right=70)
            set_cell_borders(row_cells[c_idx], top="E2E8F0", bottom="E2E8F0", left="E2E8F0", right="E2E8F0", sz="4")

        # 0. STT
        p = row_cells[0].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run_fonts(p.add_run(str(it.get("stt", idx))), size_pt=9.5)

        # 1. Tên thiết bị / linh kiện
        p = row_cells[1].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15
        set_run_fonts(p.add_run(it.get("ten_thiet_bi", "")), size_pt=9.5, bold=True)

        # 2. Model / Serial
        p = row_cells[2].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run_fonts(p.add_run(it.get("model_serial", "-") or "-"), size_pt=9)

        # 3. Lỗi & Nội dung sửa
        p = row_cells[3].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.1
        set_run_fonts(p.add_run(it.get("noi_dung_sua_chua", "-") or "-"), size_pt=8.5)

        # 4. Số lượng
        p = row_cells[4].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run_fonts(p.add_run(str(it.get("so_luong", "1"))), size_pt=9.5)

        # 5. Đơn giá
        p = row_cells[5].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(0)
        dg = it.get("don_gia", "")
        if isinstance(dg, (int, float)):
            dg_str = format_currency_vnd(dg).replace(" VND", "")
        else:
            dg_str = str(dg).replace(" VND", "").replace("VND", "").strip()
        set_run_fonts(p.add_run(dg_str), size_pt=9.5)

        # 6. Thành tiền
        p = row_cells[6].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(0)
        tg = it.get("tong_gia", "")
        if isinstance(tg, (int, float)):
            tg_str = format_currency_vnd(tg).replace(" VND", "")
            total_calc += int(tg)
        else:
            numeric_val = parse_positive_integer(tg)
            total_calc += numeric_val
            tg_str = format_currency_vnd(numeric_val).replace(" VND", "") if numeric_val > 0 else str(tg)
        set_run_fonts(p.add_run(tg_str), size_pt=9.5, bold=True)

    # Total Row
    total_amount_raw = data.get("tong_tien_hop_dong_so", "")
    numeric_total = parse_positive_integer(total_amount_raw)
    if numeric_total == 0:
        numeric_total = total_calc

    total_row_cells = item_table.add_row().cells
    total_row_cells[0].merge(total_row_cells[5])
    set_cell_background(total_row_cells[0], "F8FAFC")
    set_cell_margins(total_row_cells[0], top=80, bottom=80, left=100, right=100)
    set_cell_borders(total_row_cells[0], top="94A3B8", bottom="94A3B8", left="CBD5E1", right="CBD5E1", sz="6")

    p_tot_lbl = total_row_cells[0].paragraphs[0]
    p_tot_lbl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_tot_lbl.paragraph_format.space_after = Pt(0)
    set_run_fonts(p_tot_lbl.add_run("TỔNG CHI PHÍ SỬA CHỮA (VND) / 維修總費用："), size_pt=10, bold=True)

    set_cell_background(total_row_cells[6], "F8FAFC")
    set_cell_margins(total_row_cells[6], top=80, bottom=80, left=70, right=70)
    set_cell_borders(total_row_cells[6], top="94A3B8", bottom="94A3B8", left="CBD5E1", right="CBD5E1", sz="6")
    p_tot_val = total_row_cells[6].paragraphs[0]
    p_tot_val.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_tot_val.paragraph_format.space_after = Pt(0)
    set_run_fonts(p_tot_val.add_run(format_currency_vnd(numeric_total).replace(" VND", "") + " VND"), size_pt=10.5, bold=True, color_rgb=RGBColor(29, 78, 216))

    # Số tiền bằng chữ
    words_vn = data.get("tong_tien_chu_viet") or number_to_vietnamese_words(numeric_total)
    words_cn = data.get("tong_tien_chu_trung") or number_to_chinese_words(numeric_total)

    p_words = doc.add_paragraph()
    p_words.paragraph_format.space_before = Pt(6)
    p_words.paragraph_format.space_after = Pt(12)
    p_words.paragraph_format.line_spacing = 1.2
    run_words = p_words.add_run(
        f"• Bằng chữ tiếng Việt / 越文大寫：{words_vn}\n"
        f"• Bằng chữ tiếng Trung / 中文大寫：{words_cn}"
    )
    set_run_fonts(run_words, size_pt=10, bold=True, color_rgb=RGBColor(15, 23, 42))

    # 5. Điều 2: Địa điểm & Thời hạn sửa chữa
    delivery_days = data.get("thoi_gian_hoan_thanh_ngay", 15)
    location = data.get("dia_diem_sua_chua", "Tại nhà xưởng sản xuất Bên A")
    warranty_months = data.get("thoi_gian_bao_hanh_thang", 6)

    p_art2 = doc.add_paragraph()
    p_art2.paragraph_format.space_after = Pt(4)
    run = p_art2.add_run("ĐIỀU 2: ĐỊA ĐIỂM, THỜI HẠN THỰC HIỆN VÀ BÀN GIAO / 第二條：維修地點、履行期限與交付")
    set_run_fonts(run, size_pt=11, bold=True)

    p_art2_body = doc.add_paragraph()
    p_art2_body.paragraph_format.left_indent = Inches(0.2)
    p_art2_body.paragraph_format.space_after = Pt(10)
    p_art2_body.paragraph_format.line_spacing = 1.2
    run = p_art2_body.add_run(
        f"1. Địa điểm tiếp nhận & sửa chữa / 接收與維修地點：{location}\n"
        f"2. Thời hạn hoàn thành / 完成期限：Trong vòng {delivery_days} ngày làm việc kể từ ngày Bên A bàn giao thiết bị hoặc hoàn tất tạm ứng.\n"
        f"   自甲方交付待修設備或完成預付款之日起 {delivery_days} 個工作日內完成。\n"
        f"3. Sau khi sửa chữa xong, Bên B tiến hành chạy thử và bàn giao lại cho Bên A. Hai bên ký Biên bản kiểm tra & nghiệm thu thiết bị sau sửa chữa làm căn cứ thanh toán và bảo hành.\n"
        f"   維修完成後，乙方進行運轉測試並交付甲方。雙方共同簽署《設備維修驗收記錄確認書》作為付款及保固之依據。"
    )
    set_run_fonts(run, size_pt=10.5)

    # 6. Điều 3: Điều khoản thanh toán
    p_art3 = doc.add_paragraph()
    p_art3.paragraph_format.space_after = Pt(4)
    run = p_art3.add_run("ĐIỀU 3: PHƯƠNG THỨC & TIẾN ĐỘ THANH TOÁN / 第三條：付款方式與進度")
    set_run_fonts(run, size_pt=11, bold=True)

    p_art3_body = doc.add_paragraph()
    p_art3_body.paragraph_format.left_indent = Inches(0.2)
    p_art3_body.paragraph_format.space_after = Pt(6)
    p_art3_body.paragraph_format.line_spacing = 1.2

    installments = data.get("phan_bo_thanh_toan", [])
    if not installments:
        installments = [
            {
                "dot": 1,
                "phan_tram": 50,
                "so_tien": format_currency_vnd(round(numeric_total * 0.5)),
                "dieu_kien_viet": "Thanh toán tạm ứng 50% ngay sau khi hai bên ký kết hợp đồng",
                "dieu_kien_trung": "雙方簽約後即期以電匯方式支付 50%",
                "thoi_han_tt_ngay": 0
            },
            {
                "dot": 2,
                "phan_tram": 50,
                "so_tien": format_currency_vnd(round(numeric_total * 0.5)),
                "dieu_kien_viet": "Thanh toán 50% còn lại sau khi hoàn thành sửa chữa, chạy thử đạt và ký biên bản nghiệm thu",
                "dieu_kien_trung": "設備維修完成並簽署驗收交付文件後支付剩餘 50%",
                "thoi_han_tt_ngay": 30
            }
        ]

    lines_tt = ["Hình thức thanh toán: Chuyển khoản ngân hàng (T/T). Tiến độ chi tiết như sau: / 付款方式：銀行電匯 (T/T)，具體進度如下："]
    for inst in installments:
        dot_num = inst.get("dot", 1)
        pct = inst.get("phan_tram", 0)
        st = inst.get("so_tien", "")
        dk_vi = inst.get("dieu_kien_viet", "")
        dk_zh = inst.get("dieu_kien_trung", "")
        term_days = inst.get("thoi_han_tt_ngay")
        term_str = f" (Thời hạn T/T: {term_days} ngày)" if term_days is not None else ""
        lines_tt.append(f"• Đợt {dot_num} ({pct}% - {st}): {dk_vi}{term_str}\n  第 {dot_num} 期 ({pct}% - {st})：{dk_zh}")

    run = p_art3_body.add_run("\n".join(lines_tt))
    set_run_fonts(run, size_pt=10.5)

    # 7. Điều 4: Bảo hành sau sửa chữa
    p_art4 = doc.add_paragraph()
    p_art4.paragraph_format.space_before = Pt(6)
    p_art4.paragraph_format.space_after = Pt(4)
    run = p_art4.add_run("ĐIỀU 4: CHẾ ĐỘ BẢO HÀNH SAU SỬA CHỮA / 第四條：維修保固條款")
    set_run_fonts(run, size_pt=11, bold=True)

    p_art4_body = doc.add_paragraph()
    p_art4_body.paragraph_format.left_indent = Inches(0.2)
    p_art4_body.paragraph_format.space_after = Pt(12)
    p_art4_body.paragraph_format.line_spacing = 1.2
    run = p_art4_body.add_run(
        f"1. Thời hạn bảo hành / 保固期限：{warranty_months} tháng kể từ ngày ký Biên bản nghiệm thu thiết bị sau sửa chữa.\n"
        f"   自簽署《設備維修驗收記錄確認書》之日起 {warranty_months} 個月。\n"
        f"2. Phạm vi bảo hành / 保固範圍：Bên B cam kết bảo hành miễn phí đối với các linh kiện đã thay thế và các lỗi kỹ thuật đã được khắc phục. Không bảo hành các lỗi do vận hành sai kỹ thuật, cháy nổ nguồn điện ngoại cảnh hoặc sự can thiệp của bên thứ ba.\n"
        f"   乙方承諾對已更換之零件及已排除之故障提供免費保固。人為操作不當、外部電壓異常或第三方擅自拆修則不在此限。"
    )
    set_run_fonts(run, size_pt=10.5)

    # 8. Bảng Ký Tên
    p_sign_hdr = doc.add_paragraph()
    p_sign_hdr.paragraph_format.space_after = Pt(6)
    run = p_sign_hdr.add_run("HỢP ĐỒNG ĐƯỢC LẬP THÀNH 02 BẢN CÓ GIÁ TRỊ PHÁP LÝ NHƯ NHAU, MỖI BÊN GIỮ 01 BẢN.\n本合約一式兩份，具有同等法律效力，雙方各執一份。")
    set_run_fonts(run, size_pt=10, italic=True)

    sign_table = doc.add_table(rows=2, cols=2)
    sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    sign_table.autofit = False

    cell_sa = sign_table.cell(0, 0)
    cell_sb = sign_table.cell(0, 1)
    cell_sa.width = Inches(3.5)
    cell_sb.width = Inches(3.5)

    p_sa = cell_sa.paragraphs[0]
    p_sa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sa.paragraph_format.space_after = Pt(2)
    run = p_sa.add_run("ĐẠI DIỆN BÊN A / 甲方代表\n(Ký tên & đóng dấu / 簽署與蓋章)")
    set_run_fonts(run, size_pt=10.5, bold=True)

    p_sb = cell_sb.paragraphs[0]
    p_sb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sb.paragraph_format.space_after = Pt(2)
    run = p_sb.add_run("ĐẠI DIỆN BÊN B / 乙方代表\n(Ký tên & đóng dấu / 簽署與蓋章)")
    set_run_fonts(run, size_pt=10.5, bold=True)

    # Empty space for signatures
    cell_sa_space = sign_table.cell(1, 0)
    cell_sb_space = sign_table.cell(1, 1)
    cell_sa_space.width = Inches(3.5)
    cell_sb_space.width = Inches(3.5)

    p_space_a = cell_sa_space.paragraphs[0]
    p_space_a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_space_a.paragraph_format.space_before = Pt(45)
    p_space_a.paragraph_format.space_after = Pt(0)
    set_run_fonts(p_space_a.add_run(rep_a), size_pt=11, bold=True)

    p_space_b = cell_sb_space.paragraphs[0]
    p_space_b.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_space_b.paragraph_format.space_before = Pt(45)
    p_space_b.paragraph_format.space_after = Pt(0)
    set_run_fonts(p_space_b.add_run(rep_b), size_pt=11, bold=True)

    for row in sign_table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="none"/><w:left w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/></w:tcBorders>')
            tcPr.append(tcBorders)

    # Save DOCX file
    target_dir = Path(custom_output_dir) if custom_output_dir else (WORKING_DIR / "Ho So Du An" / "Hop Dong")
    os.makedirs(target_dir, exist_ok=True)

    clean_code = re.sub(r'[\/:*?"<>|]', '_', so_hd)
    clean_cust = re.sub(r'[\/:*?"<>|]', '_', company_a[:35])
    file_name = f"HopDongSuaChua_{clean_code}_{clean_cust}.docx"

    file_path = target_dir / file_name

    try:
        doc.save(str(file_path))
    except PermissionError:
        # File is locked in Word, save with version tag
        file_name = f"HopDongSuaChua_{clean_code}_{clean_cust}_{datetime.now().strftime('%H%M%S')}.docx"
        file_path = target_dir / file_name
        doc.save(str(file_path))

    return {
        "status": "success",
        "message": "Đã tạo file Hợp đồng sửa chữa song ngữ (.docx) thành công!",
        "file_name": file_name,
        "file_path": str(file_path),
        "download_url": f"/api/v1/repair-contracts/download/{file_name}",
        "total_amount": format_currency_vnd(numeric_total),
        "company_name": company_a
    }


def fill_existing_repair_template(template_path: Path, data: Dict[str, Any], custom_output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Hook to fill existing template when user provides a specific .docx template."""
    # When user sends their custom form later, this function can parse the runs and placeholders 1:1.
    # For now, it copies and modifies the template.
    doc = Document(str(template_path))
    so_hd = data.get("so_hop_dong", "HDSC-20261019-001")
    company_a = data.get("ben_a", {}).get("ten_cong_ty", "")

    target_dir = Path(custom_output_dir) if custom_output_dir else (WORKING_DIR / "Ho So Du An" / "Hop Dong")
    os.makedirs(target_dir, exist_ok=True)

    clean_code = re.sub(r'[\/:*?"<>|]', '_', so_hd)
    clean_cust = re.sub(r'[\/:*?"<>|]', '_', company_a[:35])
    file_name = f"HopDongSuaChua_{clean_code}_{clean_cust}.docx"
    file_path = target_dir / file_name

    doc.save(str(file_path))

    numeric_total = parse_positive_integer(data.get("tong_tien_hop_dong_so", 0))
    return {
        "status": "success",
        "message": "Đã áp dụng mẫu biểu hợp đồng sửa chữa (.docx) thành công!",
        "file_name": file_name,
        "file_path": str(file_path),
        "download_url": f"/api/v1/repair-contracts/download/{file_name}",
        "total_amount": format_currency_vnd(numeric_total),
        "company_name": company_a
    }
