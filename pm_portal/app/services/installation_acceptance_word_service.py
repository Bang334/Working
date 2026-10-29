# -*- coding: utf-8 -*-
"""
Installation Acceptance Word document (.docx) generator.
Preserves 100% layout, styles, fonts, margins, headers, and footers
from template: E:\\Working\\Bieu Mau\\Mau_Goc_Nghiem_Thu_Lap_Dat_CX.docx
"""

import copy
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import docx
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt, RGBColor

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)

logger = logging.getLogger(__name__)

TEMPLATE_PATH = WORKING_DIR / "Bieu Mau" / "Mau_Goc_Nghiem_Thu_Lap_Dat_CX.docx"
DOSSIER_DIR = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"

COLOR_BLUE = RGBColor(0x1F, 0x4E, 0x79)       # #1F4E79 (Màu xanh đậm tiêu đề của template mẫu)
COLOR_GREEN = RGBColor(0x1E, 0x7B, 0x34)      # #1E7B34 (Màu xanh lá cho chữ Đạt yêu cầu)
COLOR_GRAY = RGBColor(0x66, 0x66, 0x66)       # #666666 (Màu xám phụ đề tiếng Trung)
COLOR_MUTED = RGBColor(0x80, 0x80, 0x80)      # #808080 (Màu ghi chú nhỏ cuối trang)


def set_cell_background(cell, fill_hex: str):
    """Set background color of a table cell (e.g. FFC000 for gold)."""
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith("shd"):
            tcPr.remove(child)
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shading_elm)


def set_cell_text_and_style(
    cell,
    text: str,
    font_name: str = "微軟正黑體",
    font_size_pt: float = 8.5,
    bold: Optional[bool] = False,
    color_rgb: Optional[RGBColor] = None,
    alignment=None,
):
    """Set text for cell and format runs properly without breaking borders or margins."""
    cell.text = ""
    p = cell.paragraphs[0]
    if alignment is not None:
        p.alignment = alignment

    lines = text.split("\n")
    for idx, line in enumerate(lines):
        r = p.add_run(line)
        if font_name:
            r.font.name = font_name
        if font_size_pt:
            r.font.size = Pt(font_size_pt)
        if bold is not None:
            r.bold = bold
        if color_rgb:
            r.font.color.rgb = color_rgb
        if idx < len(lines) - 1:
            p.add_run("\n")


def prepare_installation_acceptance_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and format installation acceptance data before generation."""
    data = dict(raw)

    so_hd = (data.get("so_hop_dong") or "HMV151020250001").strip()
    data["so_hop_dong"] = so_hd
    data["so_bien_ban"] = (data.get("so_bien_ban") or "BB-NT-2026-001").strip()
    data["ngay_ky_hop_dong"] = (data.get("ngay_ky_hop_dong") or "09/12/2025").strip()
    data["ngay_nghiem_thu"] = (data.get("ngay_nghiem_thu") or datetime.now().strftime("%d/%m/%Y")).strip()
    data["gia_tri_hop_dong"] = (data.get("gia_tri_hop_dong") or "234.000.000 VND").strip()

    data["ten_he_thong"] = (data.get("ten_he_thong") or "Phần mềm tùy chỉnh chức năng hệ thống RFID").strip()
    data["ten_he_thong_trung"] = (data.get("ten_he_thong_trung") or "RFID 系統功能客製化軟體").strip()

    ben_a = data.get("ben_a") or {}
    if not isinstance(ben_a, dict):
        ben_a = {}
    data["ben_a"] = {
        "ten_cong_ty": ben_a.get("ten_cong_ty") or "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
        "ten_tieng_trung": ben_a.get("ten_tieng_trung") or "CX TECHNOLOGY (VN) 股份有限公司",
        "dia_chi": ben_a.get("dia_chi") or "Số Lô CT 10b-12-14-16-18-20-22-24a, Khu C, KCX Tân Thuận, Phường Tân Thuận, Tp. Hồ Chí Minh, Việt Nam",
        "mst": ben_a.get("mst") or "0300737556",
        "nguoi_dai_dien": ben_a.get("nguoi_dai_dien") or "",
        "chuc_vu": ben_a.get("chuc_vu") or "",
    }

    ben_b = data.get("ben_b") or {}
    if not isinstance(ben_b, dict):
        ben_b = {}
    data["ben_b"] = {
        "ten_cong_ty": ben_b.get("ten_cong_ty") or "CÔNG TY TNHH TOÀN CẦU HONG MING",
        "ten_tieng_trung": ben_b.get("ten_tieng_trung") or "宏明環球有限公司",
        "dia_chi": ben_b.get("dia_chi") or "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
        "mst": ben_b.get("mst") or "0318280158",
        "nguoi_dai_dien": ben_b.get("nguoi_dai_dien") or "Ông TANG WEI LI",
        "chuc_vu": ben_b.get("chuc_vu") or "Tổng giám đốc",
    }

    data["can_cu_phu_luc"] = (data.get("can_cu_phu_luc") or "Phụ lục 1 - Báo giá Phần mềm tùy chỉnh chức năng hệ thống RFID").strip()
    data["can_cu_phu_luc_trung"] = (data.get("can_cu_phu_luc_trung") or "附件一「RFID 系統功能客製化軟體」").strip()

    # Hang muc
    raw_items = data.get("hang_muc") or []
    sanitized_items = []
    for idx, item in enumerate(raw_items, start=1):
        if isinstance(item, dict):
            # Ưu tiên lấy trực tiếp hang_muc nếu đã có format chuẩn ngắn gọn
            hm_text = item.get("hang_muc") or item.get("ten_san_pham") or ""
            sanitized_items.append({
                "stt": item.get("stt") or idx,
                "ten_san_pham": (item.get("ten_san_pham") or "").strip(),
                "hang_muc": hm_text.strip(),
                "noi_dung": (item.get("noi_dung") or "").strip(),
                "xac_nhan_lap_dat": item.get("xac_nhan_lap_dat") or "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": item.get("ket_qua_xac_nhan") or "Đã nghiệm thu, xác nhận đạt yêu cầu.\n驗收合格，確認符合需求",
            })
    data["hang_muc"] = sanitized_items

    # Payment stages
    raw_stages = data.get("payment_stages") or []
    sanitized_stages = []
    zh_stage_map = {1: "第一期", 2: "第二期", 3: "第三期", 4: "第四期", 5: "第五期"}

    for idx, s in enumerate(raw_stages, start=1):
        if isinstance(s, dict):
            st_name = (s.get("stage") or f"GIAI ĐOẠN {idx}\n{zh_stage_map.get(idx, f'第{idx}期')}").strip()
            # Bỏ qua hàng tổng cộng nếu có
            if any(kw in st_name.lower() for kw in ["tổng cộng", "tổng giá trị", "合計", "總計"]) or str(s.get("rate") or "").strip() == "100%":
                continue
            cond = (s.get("condition") or "").strip()
            rate = (s.get("rate") or "").strip()
            amount = (s.get("amount") or "").strip()
            selected = bool(s.get("selected"))

            m = re.search(r'(?:GIAI\s*ĐOẠN|ĐỢT)\s*([0-9]+)', st_name, re.IGNORECASE)
            num = int(m.group(1)) if m else idx

            sanitized_stages.append({
                "stage_id": str(s.get("stage_id") or num),
                "stage_num": num,
                "stage": st_name,
                "condition": cond,
                "rate": rate,
                "amount": amount,
                "selected": selected
            })

    if not sanitized_stages:
        sanitized_stages = [
            {
                "stage_id": "1",
                "stage_num": 1,
                "stage": "GIAI ĐOẠN 1\n第一期",
                "condition": "Sau khi ký kết hợp đồng\n簽約完成時",
                "rate": "40%",
                "amount": "93.600.000 VND",
                "selected": False
            },
            {
                "stage_id": "2",
                "stage_num": 2,
                "stage": "GIAI ĐOẠN 2\n第二期",
                "condition": "Sau khi triển khai sản phẩm đưa vào sử dụng\n產品安裝後",
                "rate": "40%",
                "amount": "93.600.000 VND",
                "selected": False
            },
            {
                "stage_id": "3",
                "stage_num": 3,
                "stage": "GIAI ĐOẠN 3\n第三期",
                "condition": "Nghiệm thu đạt tiêu chuẩn\n驗收合格時",
                "rate": "20%",
                "amount": "46.800.000 VND",
                "selected": True
            }
        ]

    selected_stages = [st for st in sanitized_stages if st["selected"]]
    if not selected_stages:
        selected_stages = [st for st in sanitized_stages if st["stage_num"] == 3]
        if not selected_stages:
            selected_stages = [sanitized_stages[-1]]
        for st in selected_stages:
            st["selected"] = True

    # Calculate totals
    total_rate_val = 0
    total_amount_val = 0
    for st in selected_stages:
        r_num = parse_positive_integer(st["rate"])
        total_rate_val += r_num
        a_num = parse_positive_integer(st["amount"])
        total_amount_val += a_num
        st["words_vn"] = number_to_vietnamese_words(a_num)
        st["words_tw"] = number_to_chinese_words(a_num)

    total_rate_str = f"{total_rate_val}%"
    total_amount_str = format_currency_vnd(total_amount_val)
    total_words_vn = number_to_vietnamese_words(total_amount_val)
    total_words_tw = number_to_chinese_words(total_amount_val)

    nums = sorted([st["stage_num"] for st in selected_stages])
    zh_nums = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五"}

    if len(selected_stages) == 1:
        s_num = nums[0]
        s_zh = zh_nums.get(s_num, str(s_num))
        section_v_title = f"V. ĐỀ NGHỊ THANH TOÁN GIAI ĐOẠN {s_num} / {s_zh}期款項付款申請"
        cl_vn = f"Giai đoạn {s_num} ({total_rate_str})"
        cl_tw = f"第三期（{total_rate_str}）" if s_num == 3 else f"第{zh_nums.get(s_num, str(s_num))}期（{total_rate_str}）"
        conclusion_vn = (
            f"Hai bên thống nhất xác nhận các hạng mục lắp đặt nêu trên đã hoàn thành và nghiệm thu đạt yêu cầu. "
            f"Việc ký biên bản này là căn cứ xác nhận Bên B đã đáp ứng điều kiện thanh toán {cl_vn} theo Hợp đồng. "
            f"Bên A thực hiện thanh toán tổng cộng {total_rate_str} giá trị hợp đồng, tương đương {total_amount_str}, theo quy định của Hợp đồng."
        )
        conclusion_tw = (
            f"雙方同意確認上述安裝項目已完成並驗收合格。本確認書簽署後，作為乙方已符合合約{cl_tw}付款條件之依據。"
            f"甲方依合約規定支付合計 {total_rate_str} 合約金額，即 {total_amount_str}。"
        )
    else:
        vn_nums_str = " & ".join([str(n) for n in nums]) if len(nums) == 2 else ", ".join([str(n) for n in nums])
        tw_nums_str = "、".join([zh_nums.get(n, str(n)) for n in nums])
        section_v_title = f"V. ĐỀ NGHỊ THANH TOÁN GIAI ĐOẠN {vn_nums_str} / 第{tw_nums_str}期款項付款申請"

        parts_vn = [f"Giai đoạn {st['stage_num']} ({st['rate']})" for st in selected_stages]
        cl_vn = " và ".join(parts_vn)
        parts_tw = [f"第{zh_nums.get(st['stage_num'], str(st['stage_num']))}期（{st['rate']}）" for st in selected_stages]
        cl_tw = "及".join(parts_tw)

        conclusion_vn = (
            f"Hai bên thống nhất xác nhận các hạng mục lắp đặt nêu trên đã hoàn thành và nghiệm thu đạt yêu cầu. "
            f"Việc ký biên bản này là căn cứ xác nhận Bên B đã đáp ứng điều kiện thanh toán {cl_vn} theo Hợp đồng. "
            f"Bên A thực hiện thanh toán tổng cộng {total_rate_str} giá trị hợp đồng, tương đương {total_amount_str}, theo quy định của Hợp đồng."
        )
        conclusion_tw = (
            f"雙方同意確認上述安裝項目已完成並驗收合格。本確認書簽署後，作為乙方已符合合約{cl_tw}付款條件之依據。"
            f"甲方依合約規定支付合計 {total_rate_str} 合約金額，即 {total_amount_str}。"
        )

    data["payment_stages"] = sanitized_stages
    data["selected_stages"] = selected_stages
    data["total_rate_str"] = total_rate_str
    data["total_amount_str"] = total_amount_str
    data["total_words_vn"] = total_words_vn
    data["total_words_tw"] = total_words_tw
    data["section_v_title"] = section_v_title
    data["conclusion_vn"] = conclusion_vn
    data["conclusion_tw"] = conclusion_tw
    data["so_tien_thanh_toan"] = total_amount_str
    data["so_tien_chu_vn"] = total_words_vn
    data["so_tien_chu_tw"] = total_words_tw

    return data


def generate_installation_acceptance_word(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate professional installation acceptance Word document (.docx) strictly preserving template."""
    data = prepare_installation_acceptance_data(raw_data)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    DOSSIER_DIR.mkdir(parents=True, exist_ok=True)

    template_file = TEMPLATE_PATH
    if not template_file.exists():
        raise FileNotFoundError(f"Không tìm thấy template mẫu: {template_file}")

    doc = Document(str(template_file))
    so_hd = data["so_hop_dong"]
    so_bb = data["so_bien_ban"]
    ten_a_vn = data["ben_a"].get("ten_cong_ty", "")
    ten_a_tw = data["ben_a"].get("ten_tieng_trung", "")
    ten_b_vn = data["ben_b"].get("ten_cong_ty", "CÔNG TY TNHH TOÀN CẦU HONG MING")
    ten_b_tw = data["ben_b"].get("ten_tieng_trung", "宏明環球有限公司")
    ngay_ky = data.get("ngay_ky_hop_dong", "")
    gia_tri_hd = data.get("gia_tri_hop_dong", "")
    ten_ht_vn = data.get("ten_he_thong", "")
    ten_ht_tw = data.get("ten_he_thong_trung", "")

    # 1. FOOTER: Cập nhật số hợp đồng
    for sec in doc.sections:
        for p in sec.footer.paragraphs:
            if "HMV100120260001" in p.text:
                for r in p.runs:
                    if "HMV100120260001" in r.text:
                        r.text = r.text.replace("HMV100120260001", so_hd)

    # 2. TABLE 0: Số biên bản & Liên quan HĐ (Giữ nguyên font, size 10.0 pt, bold=True, color 1F4E79)
    t0 = doc.tables[0]
    t0.rows[0].cells[0].paragraphs[0].text = f"Số biên bản / 文件編號: {so_bb}"
    t0.rows[0].cells[1].paragraphs[0].text = f"Liên quan HĐ / 合約編號: {so_hd}"
    for c in t0.rows[0].cells:
        for p in c.paragraphs:
            for r in p.runs:
                r.font.name = "微軟正黑體"
                r.font.size = Pt(10.0)
                r.bold = True
                r.font.color.rgb = COLOR_BLUE

    # 3. TABLE 1: THÔNG TIN HỢP ĐỒNG (Bên A, Bên B, Hệ thống, Ngày ký, Giá trị)
    t1 = doc.tables[1]
    # Row 0: Bên A
    t1.rows[0].cells[0].paragraphs[0].text = "Bên A (Bên Mua) / 買方\n" + (ten_a_tw if ten_a_tw else "金迅科技（越南）有限公司")
    if len(t1.rows[0].cells[0].paragraphs[0].runs) > 0:
        t1.rows[0].cells[0].paragraphs[0].runs[0].font.size = Pt(9.5)
        t1.rows[0].cells[0].paragraphs[0].runs[0].font.color.rgb = COLOR_BLUE
    t1.rows[0].cells[1].paragraphs[0].text = ten_a_vn
    if len(t1.rows[0].cells[1].paragraphs[0].runs) > 0:
        t1.rows[0].cells[1].paragraphs[0].runs[0].font.size = Pt(8.5)

    # Row 1: Bên B
    t1.rows[1].cells[0].paragraphs[0].text = "Bên B (Bên Bán) / 賣方\n浤詺資訊全球有限公司"
    if len(t1.rows[1].cells[0].paragraphs[0].runs) > 0:
        t1.rows[1].cells[0].paragraphs[0].runs[0].font.size = Pt(9.5)
        t1.rows[1].cells[0].paragraphs[0].runs[0].font.color.rgb = COLOR_BLUE
    t1.rows[1].cells[1].paragraphs[0].text = f"{ten_b_vn} ({ten_b_tw})" if ten_b_tw else ten_b_vn
    if len(t1.rows[1].cells[1].paragraphs[0].runs) > 0:
        t1.rows[1].cells[1].paragraphs[0].runs[0].font.size = Pt(8.5)

    # Row 2: Hệ thống
    t1.rows[2].cells[0].paragraphs[0].text = f"Hệ thống / 系統\n{ten_ht_tw}"
    if len(t1.rows[2].cells[0].paragraphs[0].runs) > 0:
        t1.rows[2].cells[0].paragraphs[0].runs[0].font.size = Pt(9.5)
        t1.rows[2].cells[0].paragraphs[0].runs[0].font.color.rgb = COLOR_BLUE
    t1.rows[2].cells[1].paragraphs[0].text = ten_ht_vn
    if len(t1.rows[2].cells[1].paragraphs[0].runs) > 0:
        t1.rows[2].cells[1].paragraphs[0].runs[0].font.size = Pt(8.5)

    # Row 3: Ngày ký
    t1.rows[3].cells[1].paragraphs[0].text = ngay_ky
    if len(t1.rows[3].cells[1].paragraphs[0].runs) > 0:
        t1.rows[3].cells[1].paragraphs[0].runs[0].font.size = Pt(9.5)

    # Row 4: Giá trị
    t1.rows[4].cells[1].paragraphs[0].text = gia_tri_hd
    if len(t1.rows[4].cells[1].paragraphs[0].runs) > 0:
        t1.rows[4].cells[1].paragraphs[0].runs[0].font.size = Pt(9.5)

    # 4. SECTION II: Căn cứ hợp đồng (P04 & P05)
    doc.paragraphs[4].text = f"1. Căn cứ Hợp đồng số {so_hd} ký ngày {ngay_ky} và Phụ lục 1 - Báo giá {ten_ht_vn}"
    for r in doc.paragraphs[4].runs:
        r.font.name = "微軟正黑體"
        r.font.size = Pt(9.5)
        r.font.color.rgb = None

    ngay_ky_tw = ngay_ky
    m_d = re.match(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', ngay_ky)
    if m_d:
        ngay_ky_tw = f"{m_d.group(3)}/{m_d.group(2).zfill(2)}/{m_d.group(1).zfill(2)}"

    doc.paragraphs[5].text = f"1. 依據 {ngay_ky_tw} 簽訂之合約 {so_hd} 及附件一「{ten_ht_tw}」。"
    for r in doc.paragraphs[5].runs:
        r.font.name = "微軟正黑體"
        r.font.size = Pt(9.5)
        r.font.color.rgb = COLOR_GRAY

    # P06, P07, P08, P09, P10, P11, P12 giữ nguyên 100% như mẫu gốc!

    # 5. TABLE 2: BẢNG HẠNG MỤC LẮP ĐẶT & NGHIỆM THU
    items: List[Dict[str, Any]] = data.get("hang_muc", [])
    t2 = doc.tables[2]
    current_data_rows = len(t2.rows) - 1
    target_count = len(items)

    if current_data_rows > target_count:
        for _ in range(current_data_rows - target_count):
            t2._tbl.remove(t2._tbl.tr_lst[-1])
    elif current_data_rows < target_count:
        for _ in range(target_count - current_data_rows):
            new_tr = copy.deepcopy(t2._tbl.tr_lst[-1])
            t2._tbl.append(new_tr)

    for idx, item in enumerate(items, start=1):
        row = t2.rows[idx]
        hm_content = item.get("hang_muc") or item.get("ten_san_pham") or ""
        # Nếu chưa có tiền tố số thứ tự thì thêm
        if not re.match(r'^\d+\.', hm_content.strip()):
            hm_content = f"{idx}. {hm_content.strip()}"

        set_cell_text_and_style(
            row.cells[0],
            hm_content,
            font_name="微軟正黑體",
            font_size_pt=8.5,
            bold=False,
            color_rgb=None,
            alignment=WD_ALIGN_PARAGRAPH.LEFT
        )
        set_cell_text_and_style(
            row.cells[1],
            "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
            font_name="微軟正黑體",
            font_size_pt=7.0,
            bold=True,
            color_rgb=COLOR_GREEN,
            alignment=WD_ALIGN_PARAGRAPH.CENTER
        )
        set_cell_text_and_style(
            row.cells[2],
            "Đã nghiệm thu, xác nhận đạt yêu cầu.\n驗收合格，確認符合需求",
            font_name="微軟正黑體",
            font_size_pt=7.0,
            bold=True,
            color_rgb=COLOR_GREEN,
            alignment=WD_ALIGN_PARAGRAPH.CENTER
        )

    # 6. DẪN NHẬP MỤC V (P14 & P15)
    doc.paragraphs[14].text = f"Căn cứ điều khoản thanh toán của Hợp đồng {so_hd} và kết quả nghiệm thu nêu trên, Bên B đề nghị Bên A thanh toán các khoản sau:"
    for r in doc.paragraphs[14].runs:
        r.font.name = "微軟正黑體"
        r.font.size = Pt(9.5)

    doc.paragraphs[15].text = f"依據 {so_hd} 合約付款條款及上述驗收結果，乙方請求甲方支付下列款項："
    for r in doc.paragraphs[15].runs:
        r.font.name = "微軟正黑體"
        r.font.size = Pt(9.5)
        r.font.color.rgb = COLOR_GRAY

    # 7. SECTION V & TABLE 3 & PARAGRAPHS TIỀN BẰNG CHỮ
    selected_stages = data["selected_stages"]
    is_single_stage_3 = (len(selected_stages) == 1 and selected_stages[0]["stage_num"] == 3)

    t3 = doc.tables[3]
    needed_t3_rows = len(selected_stages) + 1
    current_t3_rows = len(t3.rows) - 1

    if current_t3_rows < needed_t3_rows:
        for _ in range(needed_t3_rows - current_t3_rows):
            new_tr = copy.deepcopy(t3._tbl.tr_lst[-1])
            t3._tbl.append(new_tr)
    elif current_t3_rows > needed_t3_rows:
        for _ in range(current_t3_rows - needed_t3_rows):
            t3._tbl.remove(t3._tbl.tr_lst[-1])

    # Header Row Table 3
    for cell in t3.rows[0].cells:
        set_cell_background(cell, "1F4E79")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.name = "微軟正黑體"
                r.font.size = Pt(9.0)
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Fill data rows for selected stages
    for r_i, st in enumerate(selected_stages, start=1):
        row = t3.rows[r_i]
        set_cell_text_and_style(row.cells[0], st["stage"], font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text_and_style(row.cells[1], st["condition"], font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.LEFT)
        set_cell_text_and_style(row.cells[2], st["rate"], font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text_and_style(row.cells[3], st["amount"], font_name="微軟正黑體", font_size_pt=9.5, bold=False, alignment=WD_ALIGN_PARAGRAPH.RIGHT)
        for c in row.cells:
            tcPr = c._tc.get_or_add_tcPr()
            for child in list(tcPr):
                if child.tag.endswith("shd"):
                    tcPr.remove(child)

    # Final Total Row Table 3 (Gold #FFC000)
    total_row = t3.rows[needed_t3_rows]
    set_cell_text_and_style(total_row.cells[0], "TỔNG CỘNG\n合計", font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text_and_style(total_row.cells[1], "", font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    set_cell_text_and_style(total_row.cells[2], data["total_rate_str"], font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text_and_style(total_row.cells[3], data["total_amount_str"], font_name="微軟正黑體", font_size_pt=9.5, bold=False, alignment=WD_ALIGN_PARAGRAPH.RIGHT)
    for c in total_row.cells:
        set_cell_background(c, "FFC000")

    # Reconstruct paragraphs between Table 3 and Table 4
    body = doc._body._body
    t3_elm = t3._tbl
    t4_elm = doc.tables[4]._tbl

    sig_elm = None
    for i in range(body.index(t3_elm) + 1, body.index(t4_elm)):
        child = body[i]
        if child.tag.endswith('p') and 'CHỮ KÝ XÁC NHẬN' in docx.text.paragraph.Paragraph(child, doc).text:
            sig_elm = child
            break

    if sig_elm is not None:
        to_remove = []
        curr = sig_elm.getprevious()
        while curr != t3_elm:
            to_remove.append(curr)
            curr = curr.getprevious()
        for elm in to_remove:
            body.remove(elm)

        def add_p_before_sig(runs_spec: List[tuple]):
            p = doc.add_paragraph()
            for text, bold, size, color in runs_spec:
                r = p.add_run(text)
                r.font.name = "微軟正黑體"
                if bold is not None:
                    r.bold = bold
                if size:
                    r.font.size = Pt(size)
                if color:
                    r.font.color.rgb = color
            body.remove(p._p)
            sig_elm.addprevious(p._p)

        zh_nums_map = {1: "第一期", 2: "第二期", 3: "第三期", 4: "第四期", 5: "第五期"}

        # Cập nhật tiêu đề Mục V (P13 nằm trước Table 3)
        doc.paragraphs[13].text = ""
        r_v = doc.paragraphs[13].add_run(data["section_v_title"])
        r_v.font.name = "微軟正黑體"
        r_v.font.size = Pt(13.0)
        r_v.bold = True
        r_v.font.color.rgb = COLOR_BLUE

        # Paragraphs tiền bằng chữ (sau Table 3)
        for st in selected_stages:
            st_zh = zh_nums_map.get(st["stage_num"], f"第{st['stage_num']}期")
            label = f"Giai đoạn {st['stage_num']} / {st_zh}: "
            words = f"{st['words_vn']} {st['words_tw']}。"
            add_p_before_sig([
                (label, True, 9.0, COLOR_BLUE),
                (words, False, 9.0, None)
            ])

        add_p_before_sig([
            ("Tổng cộng / 合計: ", True, 9.0, COLOR_BLUE),
            (f"{data['total_words_vn']} {data['total_words_tw']}。", False, 9.0, None)
        ])

        add_p_before_sig([
            ("Thuế VAT / 增值稅: ", True, 9.0, None),
            ("Theo quy định tại thời điểm xuất hóa đơn / 依發票開立時之規定另計。", False, 9.0, None)
        ])

        # Section VI
        add_p_before_sig([("VI. KẾT LUẬN & XÁC NHẬN / 結論與確認", True, 13.0, COLOR_BLUE)])
        add_p_before_sig([(data["conclusion_vn"], False, 9.5, None)])
        add_p_before_sig([(data["conclusion_tw"], False, 9.5, None)])
        add_p_before_sig([("", False, 9.5, None)])
        add_p_before_sig([("", False, 9.5, None)])

    # 8. TABLE 4: CHỮ KÝ XÁC NHẬN (GIỮ NGUYÊN 100% STYLE RUNS GỐC CỦA MẪU)
    t4 = doc.tables[4]
    cell_a = t4.rows[0].cells[0]
    cell_b = t4.rows[0].cells[1]

    # Cell A (Bên Mua): Chỉ cập nhật tên Bên A ở paragraph 1, giữ nguyên Header, Ký tên, Đường kẻ và Ngày tháng
    if len(cell_a.paragraphs) > 1:
        cell_a.paragraphs[1].text = ""
        r1 = cell_a.paragraphs[1].add_run(ten_a_vn)
        r1.font.name = "微軟正黑體"
        r1.font.size = Pt(9.5)
        r1.bold = True
        cell_a.paragraphs[1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Cell B (Bên Bán): Giữ nguyên 100% như mẫu gốc (BÊN B, HONG MING, 浤詺資訊全球有限公司, Ký tên, Đường kẻ, Ngày tháng, KHÔNG có tên CEO)
    # Không cần can thiệp cell_b vì mẫu gốc đã hoàn hảo chuẩn xác 1:1!

    # 9. ĐOẠN CUỐI CÙNG SAU BẢNG CHỮ KÝ (P25)
    for p in doc.paragraphs:
        if "Biên bản này là một phần không tách rời" in p.text:
            p.text = ""
            r_c1 = p.add_run(f"Biên bản này là một phần không tách rời của Hợp đồng {so_hd} / 本確認書為 {so_hd} 合約不可分割之一部分,\n")
            r_c1.font.name = "微軟正黑體"
            r_c1.font.size = Pt(8.0)
            r_c1.font.color.rgb = COLOR_MUTED

            r_c2 = p.add_run(f"Bên dưới là hình ảnh trong {ten_ht_vn}.下面是 {ten_ht_tw} 中的畫面。")
            r_c2.font.name = "微軟正黑體"
            r_c2.font.size = Pt(8.0)
            r_c2.bold = True
            r_c2.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
            break

    # 10. LƯU TÀI LIỆU
    clean_so_hd = re.sub(r'[^A-Za-z0-9_-]', '_', so_hd)
    from app.utils.file_helper import document_filename
    file_name = document_filename("Nghiem_Thu_Lap_Dat", (data.get("ben_a") or {}).get("ten_cong_ty", ""), clean_so_hd, "docx")
    output_path = DOSSIER_DIR / file_name

    try:
        doc.save(str(output_path))
    except PermissionError:
        output_path = DOSSIER_DIR / f"{output_path.stem}_v2.docx"
        file_name = output_path.name
        doc.save(str(output_path))

    return {
        "status": "success",
        "file_name": file_name,
        "file_path": str(output_path),
        "download_url": f"/api/v1/acceptance/download/{file_name}",
        "total_amount": data["total_amount_str"],
        "acceptance_data": data
    }
