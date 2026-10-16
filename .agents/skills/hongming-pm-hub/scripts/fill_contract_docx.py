# -*- coding: utf-8 -*-
"""
Script điền thông tin hợp đồng tự động trên mẫu Word (.docx)
BẢO TOÀN TUYỆT ĐỐI 100% BỐ CỤC (ZERO-LAYOUT-DISTORTION PROTOCOL)
- Giữ nguyên toàn bộ margins, font chữ, cỡ chữ, bold, italic, màu sắc.
- Giữ nguyên cấu trúc bảng biểu, độ rộng cột, viền bảng, header, footer.
- Thuật toán thay thế ký tự liên-run (Cross-Run Placeholder Replacement)
  giải quyết triệt để lỗi Word chia nhỏ thẻ placeholder thành nhiều XML runs.
- Hỗ trợ cú pháp thẻ: {{TEN_TRUONG}} hoặc [TEN_TRUONG].
- Tích hợp bộ chuyển đổi số thành chữ song ngữ Việt - Trung (Phồn thể/Giản thể).
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, Any, List

try:
    import docx
    from docx import Document
except ImportError:
    print("Vui lòng cài đặt thư viện python-docx: pip install python-docx")
    sys.exit(1)


# ==============================================================================
# 1. HÀM CHUYỂN ĐỔI SỐ TIỀN THÀNH CHỮ SONG NGỮ (VIỆT - TRUNG)
# ==============================================================================

def number_to_vietnamese_words(n: int) -> str:
    """Chuyển đổi số nguyên thành chữ tiếng Việt chuẩn kế toán/hợp đồng"""
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


def number_to_chinese_words(n: int, traditional: bool = True) -> str:
    """Chuyển đổi số nguyên thành chữ tiếng Trung chuẩn số tiền hoa thị (大寫金額)"""
    if n == 0:
        return "零越盾整"
    
    if traditional:
        digits = ["零", "壹", "貳", "參", "肆", "伍", "陸", "柒", "捌", "玖"]
        units = ["", "拾", "佰", "仟"]
        big_units = ["", "萬", "億", "兆"]
        currency = "越盾整"
    else:
        digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
        units = ["", "拾", "佰", "仟"]
        big_units = ["", "万", "亿", "兆"]
        currency = "越盾整"

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

    res = "".join(result_parts) + currency
    return res


# ==============================================================================
# 2. THUẬT TOÁN THAY THẾ CHUẨN XÁC KHÔNG LÀM VỠ BỐ CỤC / STYLES (RUN-LEVEL ENGINE)
# ==============================================================================

def replace_in_paragraph(paragraph, replacements: Dict[str, str]) -> int:
    """
    Thay thế các placeholders trong paragraph mà BẢO TOÀN NGUYÊN VẸN FORMAT của runs.
    Xử lý triệt để trường hợp Word cắt 1 thẻ placeholder (như {{TEN_A}}) thành nhiều runs.
    """
    if not paragraph.runs:
        return 0
    
    full_text = "".join(r.text for r in paragraph.runs)
    if not full_text:
        return 0
    
    replaced_count = 0
    
    for key, val in replacements.items():
        val_str = str(val) if val is not None else ""
        
        # Thử tìm thẻ theo nhiều định dạng: {{KEY}}, [KEY], KEY
        patterns = [
            f"{{{{{key}}}}}",  # {{KEY}}
            f"\\[{key}\\]",    # [KEY]
        ]
        
        for pat in patterns:
            if not re.search(pat, full_text):
                continue
            
            # Lặp lại tìm và thay thế tất cả các xuất hiện của placeholder
            while True:
                full_text = "".join(r.text for r in paragraph.runs)
                match = re.search(pat, full_text)
                if not match:
                    break
                
                start_char, end_char = match.span()
                
                # Xác định các run chứa đoạn khớp này
                current_len = 0
                run_start_idx = None
                run_end_idx = None
                char_in_start_run = None
                char_in_end_run = None
                
                for idx, r in enumerate(paragraph.runs):
                    r_len = len(r.text)
                    r_start = current_len
                    r_end = current_len + r_len
                    
                    if r_start <= start_char < r_end and run_start_idx is None:
                        run_start_idx = idx
                        char_in_start_run = start_char - r_start
                    
                    if r_start < end_char <= r_end and run_end_idx is None:
                        run_end_idx = idx
                        char_in_end_run = end_char - r_start
                        break
                    
                    current_len = r_end
                
                if run_start_idx is None or run_end_idx is None:
                    break
                
                # Tiến hành thay thế:
                # 1. Đoạn đầu: giữ phần trước placeholder trong run_start
                prefix = paragraph.runs[run_start_idx].text[:char_in_start_run]
                # 2. Đoạn cuối: giữ phần sau placeholder trong run_end
                suffix = paragraph.runs[run_end_idx].text[char_in_end_run:]
                
                if run_start_idx == run_end_idx:
                    # Nằm trọn vẹn trong 1 run duy nhất
                    paragraph.runs[run_start_idx].text = prefix + val_str + suffix
                else:
                    # Nằm vắt ngang qua nhiều runs
                    paragraph.runs[run_start_idx].text = prefix + val_str
                    # Các runs ở giữa bị xóa trắng text
                    for mid_idx in range(run_start_idx + 1, run_end_idx):
                        paragraph.runs[mid_idx].text = ""
                    paragraph.runs[run_end_idx].text = suffix
                
                replaced_count += 1
                
    return replaced_count


def process_table(table, replacements: Dict[str, str]) -> int:
    """Duyệt đệ quy toàn bộ ô trong bảng và bảng lồng nhau"""
    total_replaced = 0
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                total_replaced += replace_in_paragraph(p, replacements)
            # Kiểm tra bảng lồng bên trong cell
            for nested_table in cell.tables:
                total_replaced += process_table(nested_table, replacements)
    return total_replaced


def process_document_sections(doc, replacements: Dict[str, str]) -> int:
    """Xử lý Header và Footer của tất cả các Section"""
    total_replaced = 0
    for section in doc.sections:
        # Header chính
        if section.header:
            for p in section.header.paragraphs:
                total_replaced += replace_in_paragraph(p, replacements)
            for t in section.header.tables:
                total_replaced += process_table(t, replacements)
        
        # Footer chính
        if section.footer:
            for p in section.footer.paragraphs:
                total_replaced += replace_in_paragraph(p, replacements)
            for t in section.footer.tables:
                total_replaced += process_table(t, replacements)
                
        # Header/Footer trang đầu (nếu có tách biệt)
        if section.different_first_page_header_footer:
            if section.first_page_header:
                for p in section.first_page_header.paragraphs:
                    total_replaced += replace_in_paragraph(p, replacements)
                for t in section.first_page_header.tables:
                    total_replaced += process_table(t, replacements)
            if section.first_page_footer:
                for p in section.first_page_footer.paragraphs:
                    total_replaced += replace_in_paragraph(p, replacements)
                for t in section.first_page_footer.tables:
                    total_replaced += process_table(t, replacements)
                    
    return total_replaced


# ==============================================================================
# 3. HÀM CHÍNH: FILL CONTRACT DOCUMENT
# ==============================================================================

def fill_contract_document(
    template_path: str,
    output_path: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Điền dữ liệu vào file hợp đồng mẫu Word (.docx), bảo toàn 100% layout.
    
    Args:
        template_path: Đường dẫn tới file Word hợp đồng mẫu.
        output_path: Đường dẫn lưu file hoàn chỉnh sau khi điền.
        data: Dictionary chứa các cặp khóa-giá trị cần điền.
        
    Returns:
        dict: Thống kê kết quả thay thế và đường dẫn file đã lưu.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Không tìm thấy file mẫu: {template_path}")
        
    # Chuẩn bị dữ liệu thay thế và tự động tính toán số tiền bằng chữ nếu có
    replacements = dict(data)
    
    # Tự động sinh số tiền bằng chữ nếu người dùng đưa tổng tiền dạng số
    for key in list(replacements.keys()):
        val = replacements[key]
        if "TIEN" in key.upper() or "TONG_GIA_TRI" in key.upper() or "AMOUNT" in key.upper():
            try:
                # Làm sạch chuỗi số
                clean_num = int(str(val).replace(".", "").replace(",", "").replace("VND", "").strip())
                # Tự động bổ sung nếu chưa có trường bằng chữ
                viet_key = f"{key}_CHU"
                if viet_key not in replacements:
                    replacements[viet_key] = number_to_vietnamese_words(clean_num)
                chinese_key = f"{key}_TRUNG"
                if chinese_key not in replacements:
                    replacements[chinese_key] = number_to_chinese_words(clean_num, traditional=True)
            except (ValueError, TypeError):
                pass

    doc = Document(template_path)
    total_replacements = 0
    
    # 1. Duyệt tất cả các đoạn văn trong thân văn bản
    for p in doc.paragraphs:
        total_replacements += replace_in_paragraph(p, replacements)
        
    # 2. Duyệt tất cả các bảng trong thân văn bản
    for t in doc.tables:
        total_replacements += process_table(t, replacements)
        
    # 3. Duyệt Headers và Footers
    total_replacements += process_document_sections(doc, replacements)
    
    # 4. Lưu file an toàn (Bảo vệ chống PermissionError nếu đang mở trong Word)
    actual_output = output_path
    try:
        doc.save(output_path)
    except PermissionError:
        base, ext = os.path.splitext(output_path)
        actual_output = f"{base}_v2{ext}"
        print(f"[CẢNH BÁO] File {output_path} đang mở trong Word/WPS! Tự động lưu bản dự phòng: {actual_output}")
        doc.save(actual_output)

    return {
        "status": "success",
        "template": template_path,
        "output_path": actual_output,
        "total_replaced_instances": total_replacements,
        "keys_applied": list(replacements.keys())
    }


# ==============================================================================
# 4. GIAO DIỆN DÒNG LỆNH (CLI)
# ==============================================================================

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(
        description="Điền dữ liệu vào file hợp đồng mẫu Word (.docx) bảo toàn 100% bố cục."
    )
    parser.add_argument("--template", "-t", required=True, help="Đường dẫn file Word mẫu (.docx)")
    parser.add_argument("--data", "-d", required=True, help="Đường dẫn file JSON dữ liệu hoặc chuỗi JSON")
    parser.add_argument("--output", "-o", required=True, help="Đường dẫn lưu file Word sau khi điền (.docx)")
    
    args = parser.parse_args()
    
    # Đọc dữ liệu
    if os.path.isfile(args.data):
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.loads(args.data)
        
    result = fill_contract_document(args.template, args.output, data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
