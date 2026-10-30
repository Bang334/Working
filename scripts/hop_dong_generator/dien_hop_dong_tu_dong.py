# -*- coding: utf-8 -*-
"""
HỆ THỐNG TỰ ĐỘNG ĐIỀN HỢP ĐỒNG MUA BÁN & TRIỂN KHAI DỰ ÁN
BẢO TOÀN TUYỆT ĐỐI 100% BỐ CỤC (ZERO-LAYOUT-DISTORTION PROTOCOL)
Tệp: dien_hop_dong_tu_dong.py
Thư mục: e:\\Working\\scripts\\hop_dong_generator\\

Tính năng:
1. Đọc file mẫu gốc (.docx).
2. Tích hợp AI (Google Gemini API) để tự động phân tích mọi dạng dữ liệu đầu vào.
3. Tự động tính toán số tiền bằng chữ song ngữ (Việt - Trung Phồn thể).
4. Tự động tính toán chia các đợt thanh toán theo % hợp đồng.
5. Cập nhật Bảng sản phẩm và Bảng chữ ký mà không làm vỡ format bảng, font chữ hay căn lề.
"""

import os
import sys
import re
import json
import argparse
from copy import deepcopy
from typing import Dict, Any, List, Optional

import docx
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

# Import bộ phân tích AI nếu có
# Locate the project independently of the drive letter on this computer.
_WORKSPACE_ROOT = next((p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'pm_portal' / 'app').is_dir()), __import__('pathlib').Path.cwd())
def _workspace_path(relative):
    return str(_WORKSPACE_ROOT / relative.replace(chr(92), '/'))

try:
    from ai_contract_parser import parse_contract_info_with_ai
except ImportError:
    # Nếu chạy từ thư mục khác
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from ai_contract_parser import parse_contract_info_with_ai

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


# ==============================================================================
# 1. HÀM CHUYỂN ĐỔI SỐ TIỀN THÀNH CHỮ SONG NGỮ (VIỆT - TRUNG PHỒN THỂ)
# ==============================================================================

def number_to_vietnamese_words(n: int) -> str:
    """Chuyển số nguyên thành chữ tiếng Việt chuẩn kế toán/hợp đồng"""
    if n == 0:
        return "Không đồng"
    
    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
    
    def read_three_digits(num_str: str, is_first: bool = False) -> str:
        num = int(num_str)
        h = num // 100
        t = (num % 100) // 10
        u = num % 10
        parts = []
        
        if h > 0 or not is_first:
            parts.append(digits[h] + " trăm")
        
        if t == 0 and u != 0:
            if h > 0 or not is_first:
                parts.append("lẻ")
            parts.append(digits[u])
        elif t == 1:
            parts.append("mười")
            if u == 1:
                parts.append("một")
            elif u == 5:
                parts.append("lăm")
            elif u != 0:
                parts.append(digits[u])
        elif t > 1:
            parts.append(digits[t] + " mươi")
            if u == 1:
                parts.append("mốt")
            elif u == 4:
                parts.append("tư")
            elif u == 5:
                parts.append("lăm")
            elif u != 0:
                parts.append(digits[u])
        
        return " ".join(parts)

    s = str(abs(n))
    groups = []
    while len(s) > 3:
        groups.insert(0, s[-3:])
        s = s[:-3]
    groups.insert(0, s)
    
    res = []
    total_groups = len(groups)
    for i, g in enumerate(groups):
        if int(g) == 0:
            continue
        g_words = read_three_digits(g, is_first=(i == 0))
        unit_idx = total_groups - 1 - i
        unit = units[unit_idx]
        if g_words:
            res.append(g_words + (" " + unit if unit else ""))
            
    result = " ".join(res).strip()
    result = result[0].upper() + result[1:] + " đồng chẵn."
    return result


def number_to_chinese_words(n: int) -> str:
    """Chuyển số nguyên thành chữ tiếng Trung đại tả (大寫金額) chuẩn Phồn thể"""
    if n == 0:
        return "零越盾整"
    
    digits = ["零", "壹", "貳", "參", "肆", "伍", "陸", "柒", "捌", "玖"]
    units = ["", "拾", "佰", "仟"]
    big_units = ["", "萬", "億", "兆"]

    s = str(abs(n))
    groups = []
    while len(s) > 4:
        groups.insert(0, s[-4:])
        s = s[:-4]
    groups.insert(0, s)

    result_parts = []
    total_groups = len(groups)
    for i, g in enumerate(groups):
        g_num = int(g)
        if g_num == 0:
            continue
        g_str = f"{g_num:04d}" if i > 0 else str(g_num)
        group_words = ""
        zero_flag = False
        l = len(g_str)
        for j, ch in enumerate(g_str):
            digit_val = int(ch)
            pos = l - 1 - j
            if digit_val == 0:
                zero_flag = True
            else:
                if zero_flag:
                    group_words += digits[0]
                    zero_flag = False
                group_words += digits[digit_val] + units[pos]
        
        big_unit_idx = total_groups - 1 - i
        group_words += big_units[big_unit_idx]
        result_parts.append(group_words)

    return "越南盾" + "".join(result_parts) + "整"


def parse_positive_integer(value: Any) -> int:
    """Đọc số nguyên từ chuỗi tiền/số lượng có dấu chấm và hậu tố VND/SET."""
    digits = re.sub(r"[^\d]", "", str(value or ""))
    return int(digits) if digits else 0


# ==============================================================================
# 2. HÀM THAY THẾ TEXT TRONG RUN GIỮ NGUYÊN FORMAT GỐC
# ==============================================================================

def set_paragraph_text_preserve_font(paragraph, new_text: str, bold=None, align=None):
    """
    Cập nhật text của đoạn văn bản nhưng giữ nguyên font family và font size của Run đầu tiên.
    """
    font_name = "Times New Roman"
    font_size = Pt(11)
    is_bold = bold
    color = None
    
    if paragraph.runs:
        first_run = paragraph.runs[0]
        if first_run.font.name:
            font_name = first_run.font.name
        if first_run.font.size:
            font_size = first_run.font.size
        if bold is None and first_run.font.bold is not None:
            is_bold = first_run.font.bold
        if first_run.font.color and first_run.font.color.rgb:
            color = first_run.font.color.rgb
            
    paragraph.text = ""
    run = paragraph.add_run(new_text)
    run.font.name = font_name
    run.font.size = font_size
    if is_bold is not None:
        run.font.bold = is_bold
    if color is not None:
        run.font.color.rgb = color
    if align is not None:
        paragraph.alignment = align


def set_cell_text_preserve_style(cell, text: str, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, font_size_pt=10):
    """Thiết lập văn bản trong ô bảng với font Times New Roman chuẩn xác"""
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    lines = text.split("\n")
    for i, line in enumerate(lines):
        run = p.add_run(line)
        run.font.name = "Times New Roman"
        run.font.size = Pt(font_size_pt)
        run.font.bold = bold
        if i < len(lines) - 1:
            p.add_run("\n")


def get_paragraph_all_text(paragraph) -> str:
    """Đọc cả chữ nằm trong textbox/shape lồng bên trong một paragraph."""
    return "".join(
        node.text or "" for node in paragraph._p.iter(qn("w:t"))
    )


def remove_paragraph(paragraph) -> None:
    """Xóa hẳn paragraph, bao gồm thuộc tính đánh số tự động của Word."""
    element = paragraph._p
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)


def replace_text_span_in_nodes(text_nodes, start: int, end: int, replacement: str) -> None:
    """Thay một khoảng ký tự có thể bị Word chia qua nhiều ``w:t``."""
    cursor = 0
    touched = []
    for node in text_nodes:
        value = node.text or ""
        node_start = cursor
        node_end = cursor + len(value)
        cursor = node_end
        if node_end <= start or node_start >= end:
            continue
        touched.append((node, value, node_start))

    if not touched:
        return

    first_node, first_value, first_start = touched[0]
    _, last_value, last_start = touched[-1]
    prefix = first_value[: max(0, start - first_start)]
    suffix = last_value[max(0, end - last_start) :]
    first_node.text = prefix + replacement + suffix
    for node, _, _ in touched[1:]:
        node.text = ""


def replace_regex_across_text_nodes(text_nodes, pattern: str, replacement: str) -> bool:
    """Thay regex đầu tiên kể cả khi placeholder bị tách giữa nhiều run."""
    full_text = "".join(node.text or "" for node in text_nodes)
    match = re.search(pattern, full_text, flags=re.IGNORECASE)
    if not match:
        return False
    replace_text_span_in_nodes(
        text_nodes,
        match.start(),
        match.end(),
        match.expand(replacement),
    )
    return True


def replace_next_placeholder_preserve_style(paragraph, replacement: str) -> bool:
    """Thay placeholder đầu tiên và dùng style của phần nội dung bên trong.

    Dấu ``{{``/``}}`` thường nằm ở run thường, còn nội dung mẫu bên trong có
    thể in đậm hoặc là hyperlink. Vì vậy không đặt chữ mới vào run dấu ngoặc;
    chữ mới được đặt vào ``w:t`` có nội dung thực để giữ đúng định dạng mẫu.
    """
    text_nodes = list(paragraph._p.iter(qn("w:t")))
    full_text = "".join(node.text or "" for node in text_nodes)
    match = re.search(r"\{\{.*?\}\}", full_text, flags=re.DOTALL)
    if not match:
        return False

    cursor = 0
    touched = []
    for node in text_nodes:
        value = node.text or ""
        node_start = cursor
        node_end = cursor + len(value)
        cursor = node_end
        if node_end <= match.start() or node_start >= match.end():
            continue
        touched.append((node, value, node_start))

    if not touched:
        return False

    first_node, first_value, first_start = touched[0]
    last_node, last_value, last_start = touched[-1]
    prefix = first_value[: max(0, match.start() - first_start)]
    suffix = last_value[max(0, match.end() - last_start) :]
    anchor_node = next(
        (
            node
            for node, value, _ in touched
            if re.sub(r"[{}\s]", "", value)
        ),
        touched[0][0],
    )

    for node, _, _ in touched:
        node.text = ""
    if first_node is last_node:
        first_node.text = prefix + replacement + suffix
    else:
        first_node.text = prefix
        last_node.text = suffix
        if anchor_node is first_node:
            anchor_node.text = prefix + replacement
        elif anchor_node is last_node:
            anchor_node.text = replacement + suffix
        else:
            anchor_node.text = replacement
    return True


def strip_placeholder_braces(doc) -> None:
    """Bỏ dấu ``{{``/``}}`` còn lại sau khi các trường đã được điền.

    Bản mẫu chuyển từ DOC sang DOCX có thể tách hai dấu ngoặc sang nhiều run,
    thậm chí thành paragraph riêng. Chỉ bỏ ký hiệu bao, không xóa nội dung bên
    trong, để không làm thay đổi lời văn cố định của mẫu.
    """
    for paragraph_element in doc.element.body.iter(qn("w:p")):
        text_nodes = list(paragraph_element.iter(qn("w:t")))
        for pattern in (r"\{\{", r"\}\}"):
            while replace_regex_across_text_nodes(text_nodes, pattern, ""):
                pass


def update_party_a_tax_line(doc, tax_id: str, representative: str) -> bool:
    """Cập nhật dòng MST tiếng Trung của Bên A ngay trong textbox mẫu.

    Dòng này không xuất hiện trong ``paragraph.text`` nên trước đây bị bỏ sót,
    làm MST cũ còn nguyên và chương trình chèn thêm một MST mới ở dòng sau.
    Hàm chỉ sửa các text node cần thiết để giữ nguyên textbox và định dạng.
    """
    inside_party_a = False

    for paragraph in doc.paragraphs:
        full_text = get_paragraph_all_text(paragraph).strip()
        if full_text.startswith("Bên A"):
            inside_party_a = True
            continue
        if inside_party_a and full_text.startswith("Bên B"):
            break
        if not inside_party_a:
            continue
        if not ("MST" in full_text and ("稅號" in full_text or "税号" in full_text)):
            continue

        text_nodes = list(paragraph._p.iter(qn("w:t")))

        # Ưu tiên placeholder có nhãn. Cách thay này vẫn hoạt động khi Word
        # chia ``{{...}}`` thành nhiều run/w:t khác nhau.
        replaced_tax_id = replace_regex_across_text_nodes(
            text_nodes,
            r"(MST\s*(?:稅號|税号)?\s*[:：]?\s*)\{\{.*?\}\}",
            rf"\g<1>{tax_id}",
        )
        if not replaced_tax_id:
            replaced_tax_id = replace_regex_across_text_nodes(
                text_nodes,
                r"\{\{\s*\d{10}\s*\}\}",
                tax_id,
            )
        if not replaced_tax_id:
            replaced_tax_id = replace_regex_across_text_nodes(
                text_nodes,
                r"(?<!\d)\d{10}(?!\d)",
                tax_id,
            )

        if representative:
            replace_regex_across_text_nodes(
                text_nodes,
                r"(代表人\s*[:：]\s*)\{\{.*?\}\}",
                rf"\g<1>{representative}",
            )

        return replaced_tax_id

    return False


def set_content_control_text(doc, tag_value: str, new_text: str) -> bool:
    """Thay nội dung một content control theo tag, giữ nguyên khung SDT."""
    for content_control in doc.element.body.iter(qn("w:sdt")):
        tag_nodes = list(content_control.iter(qn("w:tag")))
        if not any(
            node.get(qn("w:val")) == tag_value for node in tag_nodes
        ):
            continue

        text_nodes = list(content_control.iter(qn("w:t")))
        if not text_nodes:
            return False
        text_nodes[0].text = new_text
        for node in text_nodes[1:]:
            node.text = ""
        return True
    return False


def resolve_chinese_project_title(
    ten_du_an_cn: str,
    ten_du_an_vn: str,
    hang_muc: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Xác định tên dự án / báo giá tiếng Trung chuẩn mực cho hợp đồng song ngữ.
    Đảm bảo 100% luôn có tên tiếng Trung kết thúc bằng '報價單', không dùng danh sách hardcode.
    """
    cn = str(ten_du_an_cn or "").strip()
    if cn:
        if "報價" in cn:
            return cn
        return f"{cn} 報價單"

    # Lọc toàn bộ tên sản phẩm để đưa cho AI khái quát hóa tên dự án ngắn gọn
    if hang_muc:
        prod_names = [
            str(hm.get("ten_san_pham", "") or hm.get("ten_hang_muc", "")).strip()
            for hm in hang_muc
            if str(hm.get("ten_san_pham", "") or hm.get("ten_hang_muc", "")).strip()
        ]
        if prod_names:
            try:
                # Gọi AI tổng hợp tên dự án ngắn gọn song ngữ từ danh sách sản phẩm
                from app.services.ai_service import summarize_project_title_with_ai
                ai_result = summarize_project_title_with_ai(prod_names)
                ai_cn = str(ai_result.get("ten_du_an_trung", "")).strip()
                if ai_cn:
                    return ai_cn if "報價" in ai_cn else f"{ai_cn} 報價單"
            except Exception:
                pass

            # Nếu không gọi được AI, trích xuất cụm tên hệ thống có sẵn trong tên sản phẩm
            for pname in prod_names:
                cjk_match = re.search(r"([\u4e00-\u9fffA-Za-z0-9\s\-_]+系統|[\u4e00-\u9fffA-Za-z0-9\s\-_]+廠區)", pname)
                if cjk_match:
                    extracted = cjk_match.group(1).strip()
                    return extracted if "報價" in extracted else f"{extracted} 報價單"

    # Fallback tự nhiên không hardcode từ khóa
    clean_vn = re.sub(r"^(báo giá triển khai|báo giá|dự án|hệ thống)\s*", "", str(ten_du_an_vn or "").strip(), flags=re.IGNORECASE)
    return f"{clean_vn} 報價單" if clean_vn else "專案系統報價單"


# ==============================================================================
# 3. ĐIỀN HỢP ĐỒNG BẢO TOÀN LAYOUT 100%
# ==============================================================================

def fill_contract(
    template_path: str,
    output_path: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Điền dữ liệu vào file hợp đồng mẫu Word (.docx), bảo toàn 100% layout.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Không tìm thấy file mẫu: {template_path}")
        
    doc = Document(template_path)
    
    # 1. Trích xuất thông tin chung
    so_hd = str(data.get("so_hop_dong", "")).strip()
    ngay_ky = str(data.get("ngay_ky", "")).strip()
    thang_ky = str(data.get("thang_ky", "")).strip()
    nam_ky = str(data.get("nam_ky", "")).strip()
    
    ben_a = data.get("ben_a", {})
    ten_a_vn = str(ben_a.get("ten_cong_ty", "")).strip()
    ten_a_cn = str(ben_a.get("ten_tieng_trung", "")).strip()
    dia_chi_a = str(ben_a.get("dia_chi", "")).strip()
    dia_chi_a_cn = str(ben_a.get("dia_chi_trung", "")).strip()
    mst_a = str(ben_a.get("mst", "")).strip()
    dai_dien_a = str(ben_a.get("nguoi_dai_dien", "")).strip()
    chuc_vu_a = str(ben_a.get("chuc_vu", "")).strip()
    # Loại bỏ phần chữ Hán và chuẩn hóa in hoa toàn bộ theo yêu cầu hợp đồng
    chuc_vu_a = re.sub(r"\s*/\s*[\u4e00-\u9fff\s]+.*$", "", chuc_vu_a)
    chuc_vu_a = re.sub(r"[\u4e00-\u9fff]+", "", chuc_vu_a).strip().upper()
    if not chuc_vu_a:
        chuc_vu_a = "TỔNG GIÁM ĐỐC"
    chuc_vu_a_cn = str(ben_a.get("chuc_vu_trung", "")).strip()
    
    du_an = data.get("du_an", {})
    ten_du_an_vn = str(
        du_an.get("ten_du_an_viet", du_an.get("ten_du_an", ""))
    ).strip()
    ten_du_an_cn = str(du_an.get("ten_du_an_trung", "")).strip()

    required_fields = {
        "so_hop_dong": so_hd,
        "ben_a.ten_cong_ty": ten_a_vn,
        "ben_a.dia_chi": dia_chi_a,
        "ben_a.mst": mst_a,
        "ben_a.nguoi_dai_dien": dai_dien_a,
        "ben_a.chuc_vu": chuc_vu_a,
        "du_an.ten_du_an_viet": ten_du_an_vn,
    }
    missing_fields = [name for name, value in required_fields.items() if not value]
    if missing_fields:
        raise ValueError(
            "Thiếu dữ liệu bắt buộc; hệ thống không tự suy đoán: "
            + ", ".join(missing_fields)
        )
    
    # Tính toán tổng tiền
    tong_tien_str = str(
        data.get("tong_tien_hop_dong_so", data.get("tong_tien_so", ""))
    ).strip()
    if not tong_tien_str or not re.search(r"\d", tong_tien_str):
        raise ValueError("Thiếu tổng tiền hợp đồng; hệ thống không tự suy đoán.")
    clean_num = int(re.sub(r"[^\d]", "", tong_tien_str))
    tong_tien_formatted = f"{clean_num:,}".replace(",", ".")
    tien_chu_viet = number_to_vietnamese_words(clean_num)
    tien_chu_trung = number_to_chinese_words(clean_num)
    


    # Cập nhật đúng dòng MST nằm trong textbox của Bên A trước khi sửa dòng đại diện.
    party_a_tax_updated = update_party_a_tax_line(doc, mst_a, dai_dien_a)
    hang_muc_list = data.get("hang_muc", [])
    proj_cn_title = resolve_chinese_project_title(ten_du_an_cn, ten_du_an_vn, hang_muc_list)
    chinese_project_reference = (
        f"雙方就 {proj_cn_title} 內容達成共識，並同意簽訂本合約，"
        "共同遵守執行合約內容如下:"
    )
    set_content_control_text(doc, "goog_rdk_5", chinese_project_reference)

    party_a_start = next(
        (i for i, p in enumerate(doc.paragraphs) if p.text.strip().startswith("Bên A")),
        -1,
    )
    party_b_start = next(
        (i for i, p in enumerate(doc.paragraphs) if p.text.strip().startswith("Bên B")),
        len(doc.paragraphs),
    )

    # 2. Cập nhật các đoạn văn bản (Paragraphs)
    for paragraph_index, p in enumerate(doc.paragraphs):
        txt = p.text.strip()
        inside_party_a = party_a_start <= paragraph_index < party_b_start
        
        # Số HĐ
        if "Số HĐ" in txt and "合約編號" in txt:
            set_paragraph_text_preserve_font(p, f"Số HĐ /合約編號: {so_hd}", bold=True)
            
        # Bên A - Tên công ty
        elif inside_party_a and txt.startswith("Bên A"):
            if not replace_next_placeholder_preserve_style(p, ten_a_vn):
                set_paragraph_text_preserve_font(p, f"Bên A (買方):  {ten_a_vn}", bold=True)
            
        # Bên A - Địa chỉ
        elif inside_party_a and txt.startswith("Địa chỉ"):
            if not replace_next_placeholder_preserve_style(p, dia_chi_a):
                set_paragraph_text_preserve_font(p, f"Địa chỉ 地址 : {dia_chi_a}")
            
        # Bên A - MST và Người đại diện
        elif inside_party_a and "Người đại diện" in txt:
            representative_replaced = replace_next_placeholder_preserve_style(p, dai_dien_a)
            role_replaced = replace_next_placeholder_preserve_style(p, chuc_vu_a)
            if not representative_replaced or not role_replaced:
                rep_text = f"Người đại diện: {dai_dien_a}\t\t          Chức vụ: {chuc_vu_a}"
                if not party_a_tax_updated:
                    rep_text = f"MST 稅號: {mst_a}\n" + rep_text
                set_paragraph_text_preserve_font(p, rep_text)

        # Căn cứ báo giá tiếng Trung. Luôn đảm bảo hiển thị chuẩn song ngữ 1:1 như mẫu gốc
        elif ("雙方就" in txt) and ("內容達成共識" in txt):
            set_paragraph_text_preserve_font(p, chinese_project_reference)
            
        # Căn cứ Báo giá tiếng Việt
        elif "Hai bên đã thống nhất thỏa thuận dựa trên nội dung Báo giá" in txt:
            quotation_name = ten_du_an_vn
            if not quotation_name.casefold().startswith("báo giá"):
                quotation_name = f"Báo giá triển khai {quotation_name}"
            ref_text = f"Hai bên đã thống nhất thỏa thuận dựa trên nội dung {quotation_name}, và ký kết hợp đồng này. Hai bên cùng cam kết tuân thủ và thực hiện các điều khoản nội dung hợp đồng như sau:"
            set_paragraph_text_preserve_font(p, ref_text)
            
        # Tổng tiền: 1 dòng tiếng Việt ở trên, 1 dòng tiếng Trung ở dưới chuẩn theo mẫu gốc
        elif "Tổng cộng số tiền phải thanh toán" in txt:
            set_paragraph_text_preserve_font(
                p,
                f"Tổng cộng số tiền phải thanh toán: {tong_tien_formatted} VND ({tien_chu_viet.rstrip('.')})",
                bold=True
            )
            
        elif (re.search(r"總\s*金\s*額\s*[:：]", txt) or "壹拾億元整" in txt) and "支付合約總金額" not in txt:
            set_paragraph_text_preserve_font(
                p,
                f"總金額: {tong_tien_formatted} VND ({tien_chu_trung})",
                bold=True
            )


    # 3. Cập nhật các đợt thanh toán (Installments)
    phan_bo = data.get("phan_bo_thanh_toan", [])
    if phan_bo:
        percentages = [int(item.get("phan_tram", 0)) for item in phan_bo]
        if sum(percentages) != 100:
            raise ValueError(
                f"Tổng tỷ lệ thanh toán phải bằng 100%, hiện là {sum(percentages)}%."
            )
        installment_amounts = [clean_num * pct // 100 for pct in percentages]
        installment_amounts[-1] += clean_num - sum(installment_amounts)

        # Tìm riêng các vị trí tiếng Việt và tiếng Trung. Mẫu gốc đặt mỗi
        # ngôn ngữ ở một paragraph độc lập; trước đây chỉ cập nhật dòng Việt
        # nên điều kiện T/T cũ ở dòng Trung vẫn bị sót.
        all_vietnamese_payment_paragraphs = []
        all_chinese_payment_paragraphs = []
        all_body_paragraphs = [
            Paragraph(element, doc._body)
            for element in doc.element.body.iter(qn("w:p"))
        ]
        for idx, p in enumerate(all_body_paragraphs):
            txt = get_paragraph_all_text(p).strip()
            if txt.startswith("Đợt 1") or txt.startswith("Đợt 2") or txt.startswith("Đợt 3") or txt.startswith("Đợt 4"):
                all_vietnamese_payment_paragraphs.append((idx, p))
            elif "支付合約總金額" in txt:
                all_chinese_payment_paragraphs.append((idx, p))

        # Mẫu gốc có một cặp đợt lắp đặt bị lặp bằng chữ thường (không có
        # đánh số Word). Chọn đúng các dòng danh sách tự động của mẫu:
        # 簽約定金, 設備安裝款, 驗收尾款. Sau đó ghép với dòng Việt ngay sau nó.
        numbered_chinese_paragraphs = [
            item
            for item in all_chinese_payment_paragraphs
            if item[1]._p.pPr is not None and item[1]._p.pPr.numPr is not None
        ]
        dot_paragraphs_cn = (
            numbered_chinese_paragraphs
            if len(numbered_chinese_paragraphs) >= len(phan_bo)
            else all_chinese_payment_paragraphs
        )[:len(phan_bo)]

        dot_paragraphs = []
        used_vietnamese_elements = set()
        for cn_index, _ in dot_paragraphs_cn:
            match = next(
                (
                    (vn_index, vn_paragraph)
                    for vn_index, vn_paragraph in all_vietnamese_payment_paragraphs
                    if vn_index > cn_index
                    and id(vn_paragraph._p) not in used_vietnamese_elements
                ),
                None,
            )
            if match is not None:
                dot_paragraphs.append(match)
                used_vietnamese_elements.add(id(match[1]._p))
                
        # Cập nhật theo phân bổ thực tế của hợp đồng
        for i, dot_info in enumerate(phan_bo):
            if i < len(dot_paragraphs):
                p_target = dot_paragraphs[i][1]
                pct = percentages[i]
                amount = installment_amounts[i]
                amount_formatted = f"{amount:,}".replace(",", ".")
                amount_viet = number_to_vietnamese_words(amount)
                amount_cn = number_to_chinese_words(amount)
                
                dk_vn = str(dot_info.get("dieu_kien_viet", "")).strip().lstrip(" ,.-").rstrip(".")
                dk_cn = str(dot_info.get("dieu_kien_trung", "")).strip().lstrip("，,。").rstrip("。")
                
                total_dots = len(phan_bo)
                chinese_title = str(dot_info.get("tieu_de_trung", "")).strip()
                if not chinese_title:
                    combined_dk = f"{dk_cn} {dk_vn}".lower()
                    if any(k in combined_dk for k in ["佈線", "配線", "kéo dây", "kéo cáp", "hạ tầng"]):
                        chinese_title = "佈線工程款"
                    elif any(k in combined_dk for k in ["設備安裝", "調測", "lắp đặt", "cài đặt", "chạy thử"]):
                        chinese_title = "設備安裝款"
                    elif any(k in combined_dk for k in ["驗收", "fac", "nghiệm thu", "bàn giao"]):
                        chinese_title = "驗收尾款"
                    elif any(k in combined_dk for k in ["簽約", "tạm ứng", "ký hợp đồng"]):
                        chinese_title = "簽約定金"
                    elif i == 0:
                        chinese_title = "簽約定金"
                    elif i == total_dots - 1:
                        chinese_title = "驗收尾款"
                    elif total_dots == 4 and i == 1:
                        chinese_title = "佈線工程款"
                    elif total_dots == 4 and i == 2:
                        chinese_title = "設備安裝款"
                    elif total_dots == 3 and i == 1:
                        chinese_title = "設備安裝款"
                    else:
                        original_chinese_text = get_paragraph_all_text(dot_paragraphs_cn[i][1]).strip()
                        chinese_title = original_chinese_text.split("：", 1)[0].split(":", 1)[0].strip() or f"第{i+1}期款"

                tieu_de = str(dot_info.get("tieu_de", "")).strip()
                if not tieu_de:
                    if chinese_title == "簽約定金":
                        tieu_de = f"Đợt {i+1} (Tạm ứng {pct}%)"
                    elif chinese_title == "佈線工程款":
                        tieu_de = f"Đợt {i+1} ({pct}% Thi công kéo dây/hạ tầng)"
                    elif chinese_title == "設備安裝款":
                        tieu_de = f"Đợt {i+1} ({pct}% Lắp đặt thiết bị)"
                    elif chinese_title == "驗收尾款":
                        tieu_de = f"Đợt {i+1} ({pct}% Nghiệm thu cuối cùng)"
                    else:
                        tieu_de = f"Đợt {i+1} ({pct}%)"

                vn_condition = f" {dk_vn}." if dk_vn else "."
                cn_condition = f"，{dk_cn}。" if dk_cn else "。"
                
                amount_viet_clean = amount_viet.rstrip(".")
                dot_text = f"{tieu_de}: Thanh toán {pct}% giá trị hợp đồng ({amount_formatted} VND – {amount_viet_clean}.){vn_condition}"
                set_paragraph_text_preserve_font(p_target, dot_text)

                if i < len(dot_paragraphs_cn):
                    dot_text_cn = f"{chinese_title}: 支付合約總金額之 {pct}%, 即 {amount_formatted} VND ({amount_cn}){cn_condition}"
                    set_paragraph_text_preserve_font(dot_paragraphs_cn[i][1], dot_text_cn)

        # Đồng nhất numId, ind, tabs để các dòng tiếng Trung và tiếng Việt được Word hiển thị liên tục
        # thành 1, 2, 3 và căn lề thẳng hàng 100%, khắc phục triệt để lỗi mục 3 bị lệch trái.
        if dot_paragraphs_cn:
            source_p_pr = dot_paragraphs_cn[0][1]._p.pPr
            source_num_pr = source_p_pr.numPr if source_p_pr is not None else None
            source_ind = source_p_pr.find(qn("w:ind")) if source_p_pr is not None else None
            source_tabs = source_p_pr.find(qn("w:tabs")) if source_p_pr is not None else None
            source_jc = source_p_pr.find(qn("w:jc")) if source_p_pr is not None else None

            for _, paragraph in dot_paragraphs_cn[1:]:
                paragraph_properties = paragraph._p.get_or_add_pPr()
                if source_num_pr is not None:
                    existing_num_pr = paragraph_properties.numPr
                    if existing_num_pr is not None:
                        paragraph_properties.remove(existing_num_pr)
                    paragraph_properties.append(deepcopy(source_num_pr))
                if source_ind is not None:
                    existing_ind = paragraph_properties.find(qn("w:ind"))
                    if existing_ind is not None:
                        paragraph_properties.remove(existing_ind)
                    paragraph_properties.append(deepcopy(source_ind))
                if source_tabs is not None:
                    existing_tabs = paragraph_properties.find(qn("w:tabs"))
                    if existing_tabs is not None:
                        paragraph_properties.remove(existing_tabs)
                    paragraph_properties.append(deepcopy(source_tabs))
                if source_jc is not None:
                    existing_jc = paragraph_properties.find(qn("w:jc"))
                    if existing_jc is not None:
                        paragraph_properties.remove(existing_jc)
                    paragraph_properties.append(deepcopy(source_jc))

        if dot_paragraphs:
            vn_source_p_pr = dot_paragraphs[0][1]._p.pPr
            vn_source_ind = vn_source_p_pr.find(qn("w:ind")) if vn_source_p_pr is not None else None
            vn_source_tabs = vn_source_p_pr.find(qn("w:tabs")) if vn_source_p_pr is not None else None
            vn_source_jc = vn_source_p_pr.find(qn("w:jc")) if vn_source_p_pr is not None else None

            for _, vn_paragraph in dot_paragraphs[1:]:
                vn_properties = vn_paragraph._p.get_or_add_pPr()
                if vn_source_ind is not None:
                    existing_vn_ind = vn_properties.find(qn("w:ind"))
                    if existing_vn_ind is not None:
                        vn_properties.remove(existing_vn_ind)
                    vn_properties.append(deepcopy(vn_source_ind))
                if vn_source_tabs is not None:
                    existing_vn_tabs = vn_properties.find(qn("w:tabs"))
                    if existing_vn_tabs is not None:
                        vn_properties.remove(existing_vn_tabs)
                    vn_properties.append(deepcopy(vn_source_tabs))
                if vn_source_jc is not None:
                    existing_vn_jc = vn_properties.find(qn("w:jc"))
                    if existing_vn_jc is not None:
                        vn_properties.remove(existing_vn_jc)
                    vn_properties.append(deepcopy(vn_source_jc))

        kept_elements = {
            id(paragraph._p)
            for _, paragraph in dot_paragraphs + dot_paragraphs_cn
        }
        redundant_payment_paragraphs = [
            paragraph
            for _, paragraph in (
                all_vietnamese_payment_paragraphs + all_chinese_payment_paragraphs
            )
            if id(paragraph._p) not in kept_elements
        ]
        for paragraph in reversed(redundant_payment_paragraphs):
            remove_paragraph(paragraph)

    # 4. Cập nhật Bảng sản phẩm (Table 0)
    hang_muc = data.get("hang_muc", [])
    if hang_muc and len(doc.tables) >= 1:
        table_prod = doc.tables[0]

        # Kiểm tra chéo đơn giá x số lượng = tổng giá từng dòng và tổng bảng.
        # Nếu dữ liệu sai, dừng ngay thay vì âm thầm tạo hợp đồng sai tiền.
        calculated_total = 0
        calculated_quantity = 0
        for row_index, item in enumerate(hang_muc, start=1):
            unit_price = parse_positive_integer(item.get("don_gia"))
            quantity = parse_positive_integer(item.get("so_luong"))
            line_total = parse_positive_integer(item.get("tong_gia"))
            if unit_price and quantity and line_total != unit_price * quantity:
                raise ValueError(
                    f"Hàng {row_index}: tổng giá {line_total:,} không bằng "
                    f"đơn giá {unit_price:,} x số lượng {quantity}."
                )
            calculated_total += line_total
            calculated_quantity += quantity

        stated_pre_discount_total = parse_positive_integer(
            data.get("tong_tien_truoc_giam")
            or data.get("tong_tien_hop_dong_so")
        )
        if stated_pre_discount_total and calculated_total != stated_pre_discount_total:
            raise ValueError(
                f"Tổng 10/hoặc N dòng sản phẩm là {calculated_total:,}, "
                f"không khớp tổng đã khai báo {stated_pre_discount_total:,}."
            )

        stated_quantity = parse_positive_integer(data.get("tong_so_luong"))
        if stated_quantity and calculated_quantity != stated_quantity:
            raise ValueError(
                f"Tổng số lượng là {calculated_quantity}, "
                f"không khớp số lượng đã khai báo {stated_quantity}."
            )

        # Mẫu DOCX chuyển từ DOC chỉ có: header + 1 dòng dữ liệu + 1 dòng
        # tổng. Nhân bản đúng dòng dữ liệu gốc để đủ 3 sản phẩm, giữ nguyên
        # chiều rộng, viền, lề ô và định dạng của mẫu.
        summary_index = next(
            (
                index
                for index, row in enumerate(table_prod.rows[1:], start=1)
                if "總共" in " ".join(cell.text for cell in row.cells)
                or "Tổng Cộng" in " ".join(cell.text for cell in row.cells)
            ),
            len(table_prod.rows) - 1,
        )
        if summary_index < 2:
            raise ValueError("Mẫu hợp đồng không có dòng dữ liệu sản phẩm để nhân bản.")

        data_row_template = deepcopy(table_prod.rows[1]._tr)
        while summary_index - 1 < len(hang_muc):
            table_prod.rows[summary_index]._tr.addprevious(deepcopy(data_row_template))
            summary_index += 1
        while summary_index - 1 > len(hang_muc):
            table_prod._tbl.remove(table_prod.rows[len(hang_muc) + 1]._tr)
            summary_index -= 1

        for row_idx, item in enumerate(hang_muc):
            target_row_idx = row_idx + 1
            row = table_prod.rows[target_row_idx]
            set_cell_text_preserve_style(row.cells[0], str(item.get("stt", row_idx + 1)), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_text_preserve_style(row.cells[1], str(item.get("ten_san_pham", "")))
            set_cell_text_preserve_style(row.cells[2], str(item.get("don_gia", "")), align=WD_ALIGN_PARAGRAPH.RIGHT)
            set_cell_text_preserve_style(row.cells[3], str(item.get("so_luong", "1 SET")), align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_text_preserve_style(row.cells[4], str(item.get("tong_gia", "")), align=WD_ALIGN_PARAGRAPH.RIGHT)

        # Dòng tổng cộng bảng sản phẩm:
        # - Có giảm giá (Hình 1): Tổng trước giảm | Sau Giảm Giá 優惠價 | Tổng sau giảm
        # - Không giảm giá (Hình 2): Rỗng | Tổng số lượng | Tổng tiền hợp đồng (Bỏ phần sau giảm giá đi)
        tong_truoc = data.get("tong_tien_truoc_giam", "")
        tong_sau = data.get("tong_tien_sau_giam", "")
        tong_so_luong = str(data.get("tong_so_luong", "")).strip()

        tien_truoc_val = parse_positive_integer(tong_truoc)
        tien_sau_val = parse_positive_integer(tong_sau) if tong_sau else clean_num

        if data.get("has_discount") is True:
            has_discount = True
        elif data.get("has_discount") is False:
            has_discount = False
        elif tien_truoc_val > 0 and clean_num > 0 and clean_num < tien_truoc_val:
            has_discount = True
        elif tien_truoc_val > 0 and tien_sau_val > 0 and tien_sau_val < tien_truoc_val:
            has_discount = True
        else:
            has_discount = False

        summary_row = table_prod.rows[len(hang_muc) + 1]
        summary_tcs = summary_row._tr.tc_lst
        first_tc_grid_span = summary_tcs[0].tcPr.find(qn("w:gridSpan"))
        if len(summary_tcs) == 3 and first_tc_grid_span is not None:
            first_tc_grid_span.set(qn("w:val"), "2")
            price_tc = deepcopy(table_prod.rows[1]._tr.tc_lst[2])
            summary_tcs[0].addnext(price_tc)
        elif len(summary_tcs) == 5:
            summary_row.cells[0].merge(summary_row.cells[1])

        summary_row = table_prod.rows[len(hang_muc) + 1]
        set_cell_text_preserve_style(summary_row.cells[0], "總共 Tổng Cộng", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

        if not has_discount:
            # TRƯỜNG HỢP KHÔNG GIẢM GIÁ (Chuẩn Hình 2):
            # Cột 2 (Đơn giá): Rỗng
            # Cột 3 (Số lượng): Tổng số lượng (ví dụ: 1 SET, 33 CÁI...)
            # Cột 4 (Tổng Giá): Tổng tiền hợp đồng
            set_cell_text_preserve_style(summary_row.cells[2], "", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
            display_qty = tong_so_luong or (f"{calculated_quantity} SET" if calculated_quantity else "")
            set_cell_text_preserve_style(summary_row.cells[3], display_qty, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_text_preserve_style(
                summary_row.cells[4],
                f"{tong_tien_formatted} VND",
                bold=True,
                align=WD_ALIGN_PARAGRAPH.RIGHT,
            )
        else:
            # TRƯỜNG HỢP CÓ GIẢM GIÁ (Chuẩn Hình 1):
            # Cột 2 (Đơn giá): Tổng trước giảm
            # Cột 3 (Số lượng): "Sau Giảm Giá\n優惠價"
            # Cột 4 (Tổng Giá): Tổng sau giảm
            tong_truoc_str = tong_truoc or (f"{tien_truoc_val:,}".replace(",", ".") + " VND")
            tong_sau_str = tong_sau or f"{tong_tien_formatted} VND"
            set_cell_text_preserve_style(summary_row.cells[2], tong_truoc_str, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
            set_cell_text_preserve_style(summary_row.cells[3], "Sau Giảm Giá\n優惠價", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_text_preserve_style(summary_row.cells[4], tong_sau_str, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)

    # 5. Cập nhật Bảng chữ ký (Table 1)
    if len(doc.tables) >= 2:
        table_sig = doc.tables[1]
        # Hàng 0: Tên 2 công ty
        ten_a_sig = ten_a_vn
        signature_company_paragraph = table_sig.rows[0].cells[0].paragraphs[0]
        if not replace_next_placeholder_preserve_style(signature_company_paragraph, ten_a_sig.replace("\n", " ")):
            set_cell_text_preserve_style(table_sig.rows[0].cells[0], ten_a_sig, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        
        # Hàng 1: Tên 2 người đại diện
        signature_representative_paragraph = table_sig.rows[1].cells[0].paragraphs[0]
        if not replace_next_placeholder_preserve_style(signature_representative_paragraph, dai_dien_a):
            set_cell_text_preserve_style(table_sig.rows[1].cells[0], dai_dien_a, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    # 6. Loại bỏ ký hiệu placeholder còn sót từ bản mẫu chuyển đổi DOC → DOCX.
    strip_placeholder_braces(doc)

    # 7. Lưu file an toàn
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    actual_output_path = output_path
    saved = False
    v_idx = 1
    base, extension = os.path.splitext(output_path)
    clean_base = re.sub(r"_v\d+$", "", base)
    while not saved:
        try:
            doc.save(actual_output_path)
            saved = True
            if v_idx > 1:
                print(
                    f"[CẢNH BÁO] File đích đang mở trong Word/WPS. Đã lưu bản dự phòng: {actual_output_path}"
                )
        except PermissionError:
            v_idx += 1
            actual_output_path = f"{clean_base}_v{v_idx}{extension}"
            if v_idx > 20:
                raise
    
    return {
        "status": "success",
        "output_path": os.path.abspath(actual_output_path),
        "ben_a": ten_a_vn,
        "tong_tien": f"{tong_tien_formatted} VND",
        "so_hop_dong": so_hd
    }


# ==============================================================================
# 4. GIAO DIỆN DÒNG LỆNH (CLI)
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Điền hợp đồng tự động bảo toàn 100% bố cục - tích hợp AI phân tích."
    )
    parser.add_argument("--template", "-t", default=_workspace_path('Bieu Mau\\Mau_Goc_Hop_Dong_Mua_Ban.docx'), help="File Word mẫu (.docx)")
    parser.add_argument("--data", "-d", help="File JSON chứa dữ liệu hợp đồng")
    parser.add_argument("--ai-text", "-a", help="Đoạn văn bản tự do để AI tự động phân tích và điền")
    default_output = os.path.join(
        os.path.dirname(__file__), "outputs", "final", "Hop_Dong_Hoan_Tat.docx"
    )
    parser.add_argument("--output", "-o", default=default_output, help="Đường dẫn file Word đầu ra")
    
    args = parser.parse_args()
    
    # 1. Thu thập dữ liệu hợp đồng
    if args.ai_text:
        print("[*] Đang sử dụng Gemini AI để phân tích dữ liệu đầu vào...")
        contract_data = parse_contract_info_with_ai(args.ai_text)
        print("[OK] AI đã bóc tách dữ liệu thành công!")
    elif args.data:
        if os.path.isfile(args.data):
            with open(args.data, "r", encoding="utf-8") as f:
                contract_data = json.load(f)
        else:
            contract_data = json.loads(args.data)
    else:
        print(
            "Vui lòng cung cấp --data/--ai-text, hoặc chạy "
            "generate_jinxun_mes_contract.py cho hợp đồng JINXUN."
        )
        sys.exit(1)
            
    print(f"[*] Tiến hành điền hợp đồng cho: {contract_data.get('ben_a', {}).get('ten_cong_ty', '')}")
    result = fill_contract(args.template, args.output, contract_data)
    print("\n==========================================")
    print("XUẤT HỢP ĐỒNG THÀNH CÔNG (100% BẢO TOÀN LAYOUT)!")
    print(f"- File kết quả: {result['output_path']}")
    print(f"- Bên A: {result['ben_a']}")
    print(f"- Tổng giá trị: {result['tong_tien']}")
    print(f"- Số hợp đồng: {result['so_hop_dong']}")
    print("==========================================")


if __name__ == "__main__":
    main()
