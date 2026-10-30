# -*- coding: utf-8 -*-
r"""
Script tạo Biên bản nghiệm thu lắp đặt & bàn giao đưa vào sử dụng
Mẫu chuẩn 1:1 theo: E:\Working\Bieu Mau\Mau_Goc_Nghiem_Thu_Lap_Dat_CX.docx
Dữ liệu nguồn: C:\Users\BANG\Downloads\02_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_.docx
Áp dụng Quy tắc bảo toàn bố cục (Zero-Layout-Distortion Protocol)
"""

import os
import sys
import copy
from pathlib import Path
from typing import Dict, Any, List

import docx
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# Locate the project independently of the drive letter on this computer.
_WORKSPACE_ROOT = next((p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'pm_portal' / 'app').is_dir()), __import__('pathlib').Path.cwd())
def _workspace_path(relative):
    return str(_WORKSPACE_ROOT / relative.replace(chr(92), '/'))

sys.stdout.reconfigure(encoding='utf-8')

WORKING_DIR = Path(_workspace_path(''))
OUTPUTS_DIR = WORKING_DIR / "pm_portal" / "outputs"
DOSSIER_DIR = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"
TEMPLATE_PATH = WORKING_DIR / "Bieu Mau" / "Mau_Goc_Nghiem_Thu_Lap_Dat_CX.docx"


def set_cell_text_and_style(cell, text: str, font_name: str = "微軟正黑體", font_size_pt: float = 8.5, bold: bool = False, color_rgb: RGBColor = None, alignment = None):
    """Gán text cho cell và định dạng run chuẩn xác, không làm vỡ ô."""
    cell.text = ""
    p = cell.paragraphs[0]
    if alignment is not None:
        p.alignment = alignment
    
    # Tách dòng nếu có nhiều dòng
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


def build_installation_acceptance_document(data: Dict[str, Any], template_path: Path, output_path: Path) -> Path:
    """Tạo file Word Biên bản nghiệm thu lắp đặt từ template mẫu, bảo toàn 100% layout."""
    if not template_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file mẫu template tại: {template_path}")

    doc = Document(str(template_path))

    # 1. Cập nhật Footer (Số HĐ trong footer)
    so_hd = data.get("so_hop_dong", "HMV151020250001")
    for sec in doc.sections:
        for p in sec.footer.paragraphs:
            if "HMV100120260001" in p.text:
                for r in p.runs:
                    if "HMV100120260001" in r.text:
                        r.text = r.text.replace("HMV100120260001", so_hd)

    # 2. Cập nhật Table 0 (Số biên bản & Liên quan HĐ)
    t0 = doc.tables[0]
    so_bb = data.get("so_bien_ban", "002_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_")
    t0.rows[0].cells[0].paragraphs[0].text = f"Số biên bản / 文件編號: {so_bb}"
    t0.rows[0].cells[1].paragraphs[0].text = f"Liên quan HĐ / 合約編號: {so_hd}"
    # Đảm bảo font size cho Table 0
    for c in t0.rows[0].cells:
        for p in c.paragraphs:
            for r in p.runs:
                r.font.size = Pt(9.0)

    # 3. Cập nhật Table 1 (Thông tin hợp đồng / Bên A / Bên B / Hệ thống / Ngày ký / Giá trị)
    t1 = doc.tables[1]
    ben_a = data.get("ben_a", {})
    ben_b = data.get("ben_b", {})
    
    # R0: Bên A
    ten_a_vn = ben_a.get("ten_cong_ty", "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)")
    ten_a_tw = ben_a.get("ten_tieng_trung", "")
    t1.rows[0].cells[0].paragraphs[0].text = "Bên A (Bên Mua) / 買方\n" + (ten_a_tw if ten_a_tw else "")
    t1.rows[0].cells[1].paragraphs[0].text = ten_a_vn
    
    # R1: Bên B (Giữ nguyên hoặc cập nhật)
    ten_b_vn = ben_b.get("ten_cong_ty", "CÔNG TY TNHH TOÀN CẦU HONG MING")
    ten_b_tw = ben_b.get("ten_tieng_trung", "浤詺資訊全球有限公司")
    t1.rows[1].cells[0].paragraphs[0].text = f"Bên B (Bên Bán) / 賣方\n{ten_b_tw}"
    t1.rows[1].cells[1].paragraphs[0].text = ten_b_vn
    
    # R2: Hệ thống / Dự án
    he_thong_vn = data.get("ten_he_thong", "RFID 硬體 (RFID Hardware) – Phần mềm tùy chỉnh chức năng hệ thống RFID")
    he_thong_tw = data.get("ten_he_thong_trung", "RFID 系統 / 客製化軟體")
    t1.rows[2].cells[0].paragraphs[0].text = f"Hệ thống / 系統\n{he_thong_tw}"
    t1.rows[2].cells[1].paragraphs[0].text = he_thong_vn
    
    # R3: Ngày ký
    ngay_ky = data.get("ngay_ky_hop_dong", "09/12/2025")
    t1.rows[3].cells[1].paragraphs[0].text = ngay_ky
    
    # R4: Giá trị HĐ
    gia_tri_hd = data.get("gia_tri_hop_dong", "234.000.000 VNĐ")
    t1.rows[4].cells[1].paragraphs[0].text = gia_tri_hd

    # Đảm bảo font size cho Table 1
    for r in t1.rows:
        for c in r.cells:
            for p in c.paragraphs:
                for r_run in p.runs:
                    r_run.font.size = Pt(8.5)

    # 4. Cập nhật Section II (Căn cứ & Nguyên tắc nghiệm thu)
    phu_luc = data.get("can_cu_phu_luc", "Phụ lục 1 – Báo giá khai phá chức năng ưu hóa tùy chỉnh (V1.2.3_VND) kèm theo hợp đồng")
    phu_luc_tw = data.get("can_cu_phu_luc_trung", "附件一「RFID系統客製化功能開發報價單（V1.2.3_VND）」")
    can_cu_kt = data.get("can_cu_ky_thuat", "Biên bản kiểm tra kỹ thuật ngày 04/03/2026 xác nhận hoàn thành lắp đặt và kết quả chạy thử, điều chỉnh, theo dõi vận hành sau đó.")
    can_cu_kt_tw = data.get("can_cu_ky_thuat_trung", "依據 2026/03/04《技術檢驗單》所確認之安裝完成情況，以及其後之試運行、調整及運行觀察結果。")

    p4_text = f"1. Căn cứ Hợp đồng mua bán số {so_hd} ký ngày {ngay_ky} giữa {ten_a_vn} và {ten_b_vn}; {phu_luc}; và {can_cu_kt}"
    p5_text = f"1. 依據 {ten_a_vn} 與 {ten_b_vn} 於 {ngay_ky} 簽訂之第 {so_hd} 號買賣合約書及{phu_luc_tw}；並{can_cu_kt_tw}"
    
    doc.paragraphs[4].text = p4_text
    doc.paragraphs[5].text = p5_text
    for p in [doc.paragraphs[4], doc.paragraphs[5]]:
        for r in p.runs:
            r.font.size = Pt(9.5)

    # 5. Cập nhật Table 2: Bảng Hạng Mục Lắp Đặt & Nghiệm Thu
    items: List[Dict[str, Any]] = data.get("hang_muc", [])
    t2 = doc.tables[2]
    
    # Số dòng hiện tại của Table 2 (trừ header row 0)
    current_data_rows = len(t2.rows) - 1
    target_count = len(items)

    # Nếu số dòng mục tiêu ít hơn, xóa các dòng thừa từ dưới lên
    if current_data_rows > target_count:
        excess = current_data_rows - target_count
        tbl_elm = t2._tbl
        for _ in range(excess):
            tbl_elm.remove(tbl_elm.tr_lst[-1])

    # Nếu số dòng mục tiêu nhiều hơn, clone dòng cuối cùng
    elif current_data_rows < target_count:
        to_add = target_count - current_data_rows
        for _ in range(to_add):
            last_tr = t2._tbl.tr_lst[-1]
            new_tr = copy.deepcopy(last_tr)
            t2._tbl.append(new_tr)

    # Điền nội dung cho từng dòng
    for idx, item in enumerate(items, start=1):
        row = t2.rows[idx]
        
        # Cột 0: Hạng mục / Nội dung
        col0_parts = []
        stt_str = str(item.get("stt", idx))
        ten_sp = item.get("ten_san_pham", "")
        hang_muc = item.get("hang_muc", "")
        noi_dung = item.get("noi_dung", "")
        
        col0_text = f"{stt_str}. {ten_sp}"
        if hang_muc:
            col0_text += f"\n項目類別 / Hạng mục: {hang_muc}"
        if noi_dung:
            col0_text += f"\n產品內容 / Nội dung: {noi_dung}"
        
        # Ghi vào Cột 0
        set_cell_text_and_style(
            row.cells[0],
            col0_text,
            font_name="微軟正黑體",
            font_size_pt=8.5,
            bold=False,
            color_rgb=None,
            alignment=WD_ALIGN_PARAGRAPH.LEFT
        )
        # In đậm dòng tiêu đề đầu tiên trong ô
        if row.cells[0].paragraphs[0].runs:
            # Highlight dòng tiêu đề sản phẩm
            row.cells[0].paragraphs[0].runs[0].bold = True

        # Cột 1: Xác nhận lắp đặt
        lap_dat_text = item.get("xac_nhan_lap_dat", "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用")
        set_cell_text_and_style(
            row.cells[1],
            lap_dat_text,
            font_name="微軟正黑體",
            font_size_pt=7.0,
            bold=True,
            color_rgb=RGBColor(0x1E, 0x7B, 0x34),
            alignment=WD_ALIGN_PARAGRAPH.CENTER
        )

        # Cột 2: Xác nhận nghiệm thu
        nghiem_thu_text = item.get("ket_qua_xac_nhan", "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。")
        set_cell_text_and_style(
            row.cells[2],
            nghiem_thu_text,
            font_name="微軟正黑體",
            font_size_pt=7.0,
            bold=True,
            color_rgb=RGBColor(0x1E, 0x7B, 0x34),
            alignment=WD_ALIGN_PARAGRAPH.CENTER
        )

    # 6. Cập nhật Section IV: Kết quả nghiệm thu
    # Giữ nguyên p11, p12 khẳng định đạt yêu cầu

    # 7. Cập nhật Section V: Đề nghị thanh toán
    giai_doan_tt = data.get("giai_doan_thanh_toan", "Giai đoạn 2 (Sau khi triển khai lắp đặt đưa vào sử dụng - 40%)")
    so_tien_tt = data.get("so_tien_thanh_toan", "93.600.000 VND")
    so_tien_chu_vn = data.get("so_tien_chu_vn", "Chín mươi ba triệu sáu trăm nghìn đồng chẵn.")
    so_tien_chu_tw = data.get("so_tien_chu_tw", "玖仟參佰陸拾萬越盾整")

    doc.paragraphs[13].text = f"V. ĐỀ NGHỊ THANH TOÁN GIAI ĐOẠN 2 / 第二期款項付款申請"
    doc.paragraphs[14].text = f"Căn cứ điều khoản thanh toán của Hợp đồng {so_hd} và kết quả nghiệm thu nêu trên, Bên B đề nghị Bên A thanh toán các khoản sau:"
    doc.paragraphs[15].text = f"依據 {so_hd} 合約付款條款及上述驗收結果，乙方請求甲方支付下列款項："
    
    doc.paragraphs[16].text = f"Giai đoạn 2 / 第二期: {so_tien_chu_vn} 越南盾{so_tien_chu_tw}。"
    doc.paragraphs[17].text = f"Khoản thanh toán đợt này / 本期應付: Tương đương 40% giá trị hợp đồng = {so_tien_tt} / 相當於合約金額 40% ＝ {so_tien_tt}。"
    doc.paragraphs[18].text = f"Tổng cộng / 合計: {so_tien_chu_vn} 越南盾{so_tien_chu_tw}。"
    doc.paragraphs[19].text = "Thuế VAT / 增值稅: Theo quy định tại thời điểm xuất hóa đơn / 依發票開立時之規定另計。"
    
    for p_idx in range(13, 20):
        if p_idx == 13:
            for r in doc.paragraphs[p_idx].runs:
                r.font.size = Pt(13.0)
                r.bold = True
                r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        else:
            for r in doc.paragraphs[p_idx].runs:
                r.font.size = Pt(9.5)

    # 8. Cập nhật Table 3: Bảng tiến độ thanh toán
    t3 = doc.tables[3]
    # Thiết lập bảng 4 dòng: Giai đoạn 1, Giai đoạn 2, Giai đoạn 3, Tổng cộng
    # Điều chỉnh số dòng của Table 3
    payment_stages = data.get("payment_stages", [
        {
            "stage": "GIAI ĐOẠN 1\n第一期",
            "condition": "Sau khi ký kết hợp đồng\n簽約完成時",
            "rate": "40%",
            "amount": "93.600.000 VND"
        },
        {
            "stage": "GIAI ĐOẠN 2 (ĐỢT NÀY)\n第二期（本期款）",
            "condition": "Sau khi triển khai sản phẩm đưa vào sử dụng\n產品安裝後",
            "rate": "40%",
            "amount": "93.600.000 VND"
        },
        {
            "stage": "GIAI ĐOẠN 3 (QUYẾT TOÁN)\n第三期（尾款）",
            "condition": "Khi nghiệm thu đạt tiêu chuẩn\n驗收合格時",
            "rate": "20%",
            "amount": "46.800.000 VND"
        },
        {
            "stage": "TỔNG CỘNG HỢP ĐỒNG\n合約總計",
            "condition": "100% Giá trị Hợp đồng",
            "rate": "100%",
            "amount": gia_tri_hd
        }
    ])
    
    current_t3_rows = len(t3.rows) - 1
    needed_t3_rows = len(payment_stages)
    if current_t3_rows < needed_t3_rows:
        for _ in range(needed_t3_rows - current_t3_rows):
            new_tr = copy.deepcopy(t3._tbl.tr_lst[-1])
            t3._tbl.append(new_tr)
    elif current_t3_rows > needed_t3_rows:
        for _ in range(current_t3_rows - needed_t3_rows):
            t3._tbl.remove(t3._tbl.tr_lst[-1])

    for r_i, stage_info in enumerate(payment_stages, start=1):
        row = t3.rows[r_i]
        set_cell_text_and_style(row.cells[0], stage_info["stage"], font_name="微軟正黑體", font_size_pt=9.0, bold=True if "TỔNG" in stage_info["stage"] or "ĐỢT NÀY" in stage_info["stage"] else False, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text_and_style(row.cells[1], stage_info["condition"], font_name="微軟正黑體", font_size_pt=9.0, bold=False, alignment=WD_ALIGN_PARAGRAPH.LEFT)
        set_cell_text_and_style(row.cells[2], stage_info["rate"], font_name="微軟正黑體", font_size_pt=9.0, bold=True if "TỔNG" in stage_info["stage"] else False, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text_and_style(row.cells[3], stage_info["amount"], font_name="微軟正黑體", font_size_pt=9.0, bold=True if "TỔNG" in stage_info["stage"] or "ĐỢT NÀY" in stage_info["stage"] else False, alignment=WD_ALIGN_PARAGRAPH.RIGHT)

    # 9. Cập nhật Section VI: Kết luận & Xác nhận
    p21_text = (
        f"Hai bên thống nhất xác nhận các hạng mục lắp đặt nêu trên đã hoàn thành và nghiệm thu đạt yêu cầu. "
        f"Việc ký biên bản này là căn cứ xác nhận Bên B đã đáp ứng điều kiện thanh toán Giai đoạn 2 (40%) theo Hợp đồng. "
        f"Bên A thực hiện thanh toán 40% giá trị hợp đồng, tương đương {so_tien_tt}, theo quy định của Hợp đồng."
    )
    p22_text = (
        f"雙方同意確認上述安裝項目已完成並驗收合格。本確認書簽署後，作為乙方已符合合約第二期（40%）付款條件之依據。"
        f"甲方依合約支付 40% 合約金額，即 {so_tien_tt}。"
    )
    doc.paragraphs[20].text = "VI. KẾT LUẬN & XÁC NHẬN / 結論與確認"
    doc.paragraphs[21].text = p21_text
    doc.paragraphs[22].text = p22_text
    
    for r in doc.paragraphs[20].runs:
        r.font.size = Pt(13.0)
        r.bold = True
        r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    for p in [doc.paragraphs[21], doc.paragraphs[22]]:
        for r in p.runs:
            r.font.size = Pt(9.5)

    # 10. Cập nhật Table 4 (Chữ ký xác nhận)
    t4 = doc.tables[4]
    sign_a_text = (
        f"BÊN A (BÊN MUA) / 買方\n"
        f"{ten_a_vn}\n"
        f"Ký tên & Đóng dấu / 簽名蓋章\n\n\n\n\n"
        f"____________________________\n"
        f"Ngày / 日期: _____ / 10 / 2026"
    )
    sign_b_text = (
        f"BÊN B (BÊN BÁN) / 賣方\n"
        f"{ten_b_vn}\n"
        f"{ten_b_tw}\n"
        f"Ký tên & Đóng dấu / 簽名蓋章\n\n\n\n\n"
        f"____________________________\n"
        f"Ông TANG WEI LI – Tổng giám đốc\n"
        f"Ngày / 日期: _____ / 10 / 2026"
    )
    set_cell_text_and_style(t4.rows[0].cells[0], sign_a_text, font_name="微軟正黑體", font_size_pt=9.5, bold=None, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text_and_style(t4.rows[0].cells[1], sign_b_text, font_name="微軟正黑體", font_size_pt=9.5, bold=None, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    # Bold tiêu đề bên A và bên B
    for c in t4.rows[0].cells:
        if c.paragraphs[0].runs:
            c.paragraphs[0].runs[0].bold = True

    # 11. Cập nhật đoạn kết sau Table 4
    if len(doc.paragraphs) > 24:
        p_last = doc.paragraphs[-2] if len(doc.paragraphs) >= 26 else doc.paragraphs[-1]
        p_last.text = (
            f"Biên bản này là một phần không tách rời của Hợp đồng {so_hd} / 本確認書為 {so_hd} 合約不可分割之一部分。\n"
            f"Biên bản được lập thành 02 (hai) bản có giá trị pháp lý như nhau, mỗi bên giữ 01 (một) bản để làm căn cứ thực hiện và thanh toán theo hợp đồng. / "
            f"本確認書一式兩份，雙方各執一份，具有同等效力，作為雙方履約及付款之依據。"
        )
        for r in p_last.runs:
            r.font.size = Pt(8.5)
            r.font.italic = True

    # Nếu có paragraph cuối chứa ảnh MES cũ của mẫu, xóa nội dung ảnh cũ
    if len(doc.paragraphs) >= 26:
        doc.paragraphs[-1].text = ""

    # Lưu file kết quả
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc.save(str(output_path))
    except PermissionError:
        output_path = output_path.with_name(output_path.stem + "_v2.docx")
        doc.save(str(output_path))

    print(f"Đã tạo file nghiệm thu lắp đặt thành công: {output_path}")
    return output_path


if __name__ == "__main__":
    # Dữ liệu trích xuất từ C:\Users\BANG\Downloads\02_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_.docx
    cx_data = {
        "so_hop_dong": "HMV151020250001",
        "so_bien_ban": "002_BIEN_BAN_NGHIEM_THU_BAN_GIAO_CX_",
        "ngay_ky_hop_dong": "09/12/2025",
        "ngay_nghiem_thu": "09/10/2026",
        "gia_tri_hop_dong": "234.000.000 VNĐ",
        "ten_he_thong": "RFID 硬體 (RFID Hardware) – Phần mềm tùy chỉnh chức năng hệ thống RFID",
        "ten_he_thong_trung": "RFID 硬體（RFID Hardware）－ RFID 系統客製化軟體",
        "ben_a": {
            "ten_cong_ty": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
            "ten_tieng_trung": "CX TECHNOLOGY (VN) 股份有限公司",
            "dia_chi": "Số Lô CT 10b-12-14-16-18-20-22-24a, Khu C, KCX Tân Thuận, Phường Tân Thuận, Tp. Hồ Chí Minh, Việt Nam",
            "mst": "0300737556"
        },
        "ben_b": {
            "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
            "ten_tieng_trung": "宏明環球有限公司",
            "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
            "mst": "0318280158",
            "nguoi_dai_dien": "Ông TANG WEI LI",
            "chuc_vu": "Tổng giám đốc"
        },
        "can_cu_phu_luc": "Phụ lục 1 – Báo giá khai phá chức năng ưu hóa tùy chỉnh (V1.2.3_VND) kèm theo hợp đồng",
        "can_cu_phu_luc_trung": "附件一「RFID系統客製化功能開發報價單（V1.2.3_VND）」",
        "can_cu_ky_thuat": "Biên bản kiểm tra kỹ thuật ngày 04/03/2026 xác nhận hoàn thành lắp đặt và kết quả chạy thử, điều chỉnh, theo dõi vận hành sau đó.",
        "can_cu_ky_thuat_trung": "依據 2026/03/04《技術檢驗單》所確認之安裝完成情況，以及其後之試運行、調整及運行觀察結果。",
        "giai_doan_thanh_toan": "Giai đoạn 2 (Sau khi triển khai lắp đặt đưa vào sử dụng - 40%)",
        "so_tien_thanh_toan": "93.600.000 VND",
        "so_tien_chu_vn": "Chín mươi ba triệu sáu trăm nghìn đồng chẵn.",
        "so_tien_chu_tw": "玖仟參佰陸拾萬越盾整",
        "hang_muc": [
            {
                "stt": 1,
                "ten_san_pham": "Concept Development",
                "hang_muc": "1. Xác nhận mở vụ án / 立案確認\n2. Yêu cầu xác nhận / 需求確認",
                "noi_dung": "Nộp hồ sơ dự án, họp thảo luận: lập kế hoạch kiến trúc dự án, lập kế hoạch quy trình và xác nhận nhu cầu. 專案立案、會議討論：專案架構企劃、流程規劃與需求確認。\nXác nhận yêu cầu: họp phát triển để xác nhận yêu cầu thông số kỹ thuật của từng chức năng. 需求確認：開發立會確認各Function規格需求。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
            },
            {
                "stt": 2,
                "ten_san_pham": "加工組 GIA CÔNG 「進站/出站 與 報工」 「Vào/Ra Trạm và Báo Công」",
                "hang_muc": "1. Mỗi máy có thể quét các nhân viên vận hành máy khác nhau khi vào và ra khỏi trạm. 進出站時每個機台都可以掃不同的機台操作者。\n2. Máy quét mã vạch được tối ưu hóa để lựa chọn máy bằng cách nhấp chuột. 掃描機台條碼優化為點選機台方式。",
                "noi_dung": "1-1. Hủy trang quét nhân sự ban đầu; thêm quét số nhân viên tại trang quét nhiều máy, từng máy có thể quét riêng mã nhân viên vận hành. 原本進站的人員掃描頁面取消，改成在多機台掃描頁面增加人員工號掃描。\n1-2. Trang xác nhận quét khi ra trạm thêm chức năng quét mã số nhân viên. 出站同樣機台的掃描確認頁增加人員工號碼掃描。\n1-3. Nhiều máy có thể vào/ra theo từng máy riêng lẻ, từng nhân viên hoặc cùng một nhân viên. 多機台進出站可依個別機台掃描個別人員或同一人員。\n2-1. Khi báo công có thể chọn từng máy, bật cửa sổ sửa số lượng/trọng lượng để điều chỉnh sản lượng thực tế. 報工可點選個別機台，彈出數量/重量修改視窗。\n2-2. Người báo công nhập sản lượng thực tế cần báo công trước khi xác nhận. 由報工人員輸入實際需要報工的產量後確認。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
            },
            {
                "stt": 3,
                "ten_san_pham": "包裝組 ĐÓNG GÓI 「進站/出站」 「Vào/Ra Trạm」",
                "hang_muc": "Quét nhiều ID nhân viên để vào và ra khỏi trạm. 進出站可刷複數人員工號。",
                "noi_dung": "1. Thêm nút cho phép quét nhiều mã nhân viên khi vào/ra trạm; một nhân viên chính thức làm ERP operator và các nhân viên khác được ghi nhận ở trường riêng. 增加可添加複數工號按鈕；需一名正式員工作為ERP操作員，其他人員記錄於新欄位。\n2. Nhiều mã nhân viên chỉ áp dụng cho một trạm/máy tại một thời điểm. 刷多個員工工號進出站僅可對一個工作站/機台。\n3. Dữ liệu RFID trả về hai trường: ERP operator (shb04) và Packer (trường mới). RFID報工資料回壓兩個欄位：ERP操作員(shb04)及包裝員(新欄位)。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
            },
            {
                "stt": 4,
                "ten_san_pham": "通箱資訊查詢 Truy vấn thông tin thùng",
                "hang_muc": "QR條碼掃描 Quét mã vạch QR",
                "noi_dung": "Truy vấn thông tin thùng ban đầu chỉ cung cấp chức năng quét RFID, nay bổ sung chức năng quét QR Code. 通箱資訊查詢原僅提供RFID掃描功能，新增QRCode掃描功能。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
            },
            {
                "stt": 5,
                "ten_san_pham": "報工APP－通箱解除綁定 APP Báo Công – Bỏ ràng buộc thùng",
                "hang_muc": "特定人員解除綁定權限控管 Hủy ràng buộc quyền cho nhân viên cụ thể",
                "noi_dung": "1. RFID APP phân loại người dùng xử lý ngoại lệ: 0000 xử lý ngoại lệ chung; 1111 quản lý ngoại lệ gồm xử lý chung + bỏ ràng buộc thùng. RFID APP使用者Category type區分0000一般異常處理者及1111異常處理管理者。\n2. Người có quyền cụ thể có thể bỏ ràng buộc thùng ở các trạng thái Pending, Using, InProcess, WaitingCheck. 特定權限人員可針對Pending、Using、InProcess、WaitingCheck狀態解除綁定。\n3. Khi hủy, Box_Status được chuyển sang trạng thái bất thường tương ứng để phân biệt bản ghi đã hủy. 取消後Box_Status改為對應異常狀態，以區別已取消之進出站記錄。\n(Lưu ý: Dữ liệu đã gỡ bỏ không thể khôi phục / 特別提醒：已取消綁定資料無法復原)。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
            },
            {
                "stt": 6,
                "ten_san_pham": "RFID離線資料暫存優化 Tối ưu hóa lưu trữ tạm thời dữ liệu ngoại tuyến RFID",
                "hang_muc": "RFID離線模式可以自動切換 Chế độ ngoại tuyến RFID có thể chuyển đổi tự động",
                "noi_dung": "CNTT cung cấp Web Service kiểm tra trước khi tải lên. Khi phát hiện bất thường, RFID giữ dữ liệu tại nền cục bộ và thông báo IT/các bên liên quan về dữ liệu báo công chờ tải lên ERP. IT提供測試用Web Service供RFID上傳前檢查；發現異常時保留本地資料並通知IT及相關人員。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入使用",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入 sử dụng."
            },
            {
                "stt": 7,
                "ten_san_pham": "WEB RFID報表查詢 Truy vấn báo cáo RFID WEB",
                "hang_muc": "增加Run Card查詢條件 Thêm điều kiện truy vấn Run Card",
                "noi_dung": "Sử dụng Run Card và ngày để tìm kiếm (một hoặc cả hai điều kiện); Run Card phải nhập chính xác, không nhập mơ hồ. 用Run Card和日期查詢（二選一或兩個條件皆可）；Run Card須正確輸入，不可模糊輸入。",
                "xac_nhan_lap_dat": "Xác nhận thiết bị đã được đưa vào sử dụng.\n確認已投入 sử dụng",
                "ket_qua_xac_nhan": "Đã nghiệm thu, xác nhận đạt yêu cầu và chính thức đưa vào sử dụng.\n驗收合格，確認正式投入使用。"
            }
        ]
    }

    # 1. Xuất file vào thư mục Hồ Sơ Dự Án / Nghiệm Thu
    out_dossier = DOSSIER_DIR / "Bien_ban_nghiem_thu_HMV151020250001_CX.docx"
    build_installation_acceptance_document(cx_data, TEMPLATE_PATH, out_dossier)

    # 2. Xuất file vào thư mục Downloads của người dùng
    out_downloads = Path(str(__import__('pathlib').Path.home() / 'Downloads/Bien_ban_nghiem_thu_HMV151020250001_CX.docx'))
    build_installation_acceptance_document(cx_data, TEMPLATE_PATH, out_downloads)

    # 3. Xuất file vào thư mục pm_portal/outputs
    out_portal = OUTPUTS_DIR / "Bien_ban_nghiem_thu_HMV151020250001_CX.docx"
    build_installation_acceptance_document(cx_data, TEMPLATE_PATH, out_portal)
