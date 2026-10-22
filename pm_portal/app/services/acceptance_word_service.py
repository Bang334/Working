"""Acceptance Word document (.docx) generator."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.services.acceptance_excel_service import prepare_acceptance_data


def set_cell_shading(cell, color_hex: str):
    """Set background fill for docx table cell."""
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


def generate_acceptance_word(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate professional bilingual Acceptance Word document (.docx)."""
    data = prepare_acceptance_data(raw_data)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    doc = Document()

    # Standard A4 margins
    sections = doc.sections
    for sec in sections:
        sec.top_margin = Inches(0.8)
        sec.bottom_margin = Inches(0.8)
        sec.left_margin = Inches(0.8)
        sec.right_margin = Inches(0.8)

    # National Header
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p_header.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM / 越南社會主義共和國\n")
    r1.bold = True
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(12)

    r2 = p_header.add_run("Độc lập – Tự do – Hạnh phúc / 獨立－自由－幸福\n")
    r2.bold = True
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(11)

    r3 = p_header.add_run("---------------o0o---------------")
    r3.font.name = "Times New Roman"
    r3.font.size = Pt(10)

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t1 = p_title.add_run(f"\n{data['tieu_de_viet']}\n")
    r_t1.bold = True
    r_t1.font.name = "Times New Roman"
    r_t1.font.size = Pt(14)
    r_t1.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    r_t2 = p_title.add_run(f"{data['tieu_de_trung']}\n")
    r_t2.bold = True
    r_t2.font.name = "Times New Roman"
    r_t2.font.size = Pt(13)
    r_t2.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    r_sub = p_title.add_run("*(Xác nhận hoàn thành kiểm tra kỹ thuật – chính thức nghiệm thu & bàn giao)*")
    r_sub.italic = True
    r_sub.font.name = "Times New Roman"
    r_sub.font.size = Pt(10.5)

    # Reference meta
    p_meta = doc.add_paragraph()
    p_meta.add_run(f"• Số Hợp Đồng / 所屬合約編號: ").bold = True
    p_meta.add_run(f"{data['so_hop_dong']}\n")
    p_meta.add_run(f"• Số Biên Bản / 驗收記錄編號: ").bold = True
    p_meta.add_run(f"{data['so_bien_ban']} | Ngày / 日期: {data['ngay_nghiem_thu']}\n")
    p_meta.add_run(f"• Căn cứ: ").bold = True
    p_meta.add_run("Hợp đồng mua bán / sửa chữa đã thỏa thuận và kết quả kiểm tra kỹ thuật thực tế.")

    # Party Information
    p_party = doc.add_paragraph()
    r_pa = p_party.add_run("BÊN A (BÊN NHẬN / KHÁCH HÀNG) / 甲方（確認方）:\n")
    r_pa.bold = True
    r_pa.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    p_party.add_run(f"Tên công ty: {data['ben_a']['ten_cong_ty']}\n")
    if data['ben_a'].get('ten_tieng_trung'):
        p_party.add_run(f"公司名稱: {data['ben_a']['ten_tieng_trung']}\n")
    if data['ben_a'].get('dia_chi'):
        p_party.add_run(f"Địa chỉ: {data['ben_a']['dia_chi']}\n")

    p_party_b = doc.add_paragraph()
    r_pb = p_party_b.add_run("BÊN B (ĐƠN VỊ THI CÔNG / KIỂM TRA) / 乙方（執行方）:\n")
    r_pb.bold = True
    r_pb.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    p_party_b.add_run(f"Tên công ty: {data['ben_b']['ten_cong_ty']} ({data['ben_b']['ten_tieng_trung']})\n")
    p_party_b.add_run(f"Địa chỉ: {data['ben_b']['dia_chi']}\n")
    p_party_b.add_run(f"Mã số thuế: {data['ben_b']['mst']} — Đại diện: {data['ben_b']['nguoi_dai_dien']} ({data['ben_b']['chuc_vu']})")

    # Table of Items
    doc.add_paragraph().add_run("DANH MỤC THIẾT BỊ NGHIỆM THU / 驗收設備清單:").bold = True
    items = data.get("hang_muc") or []
    table = doc.add_table(rows=1 + len(items), cols=6)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers = [
        "STT\n序號",
        "Serial Number\n產品序號",
        "Lỗi ban đầu\n故障說明",
        "Bộ phận\n部門",
        "Hạng mục kiểm tra & xử lý\n檢查項目",
        "Kết quả\n結果"
    ]
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_shading(hdr_cells[i], "2E75B6")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for idx, it in enumerate(items, start=1):
        row_cells = table.rows[idx].cells
        vals = [
            str(it.get("stt") or idx),
            str(it.get("serial_number") or ""),
            str(it.get("loi_ban_dau") or "").replace("\n", " / "),
            str(it.get("bo_phan") or "CNC"),
            str(it.get("hang_muc_kiem_tra") or "").replace("\n", " / "),
            str(it.get("ket_qua") or "Đạt / 合格")
        ]
        for c_i, val in enumerate(vals):
            row_cells[c_i].text = val
            set_cell_margins(row_cells[c_i], top=80, bottom=80, left=90, right=90)
            p = row_cells[c_i].paragraphs[0]
            if c_i in [0, 1, 3, 5]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(9.5)
                if c_i == 1:
                    r.font.bold = True

    # Notes section
    doc.add_paragraph().add_run("\nGHI CHÚ & KẾT LUẬN / 備註與結論:").bold = True
    p_notes = doc.add_paragraph()
    if data.get("ghi_chu_1"):
        p_notes.add_run(f"{data['ghi_chu_1']}\n")
    if data.get("ghi_chu_2"):
        p_notes.add_run(f"{data['ghi_chu_2']}\n")
    if data.get("ghi_chu_3"):
        p_notes.add_run(f"{data['ghi_chu_3']}")

    # Signatures
    p_sig = doc.add_paragraph("\n")
    table_sig = doc.add_table(rows=1, cols=2)
    table_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_a = table_sig.rows[0].cells[0]
    cell_b = table_sig.rows[0].cells[1]

    pa = cell_a.paragraphs[0]
    pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sa = pa.add_run(f"ĐẠI DIỆN BÊN A / 甲方代表\n(Ký xác nhận / 簽字確認)\n\n\n\n\n{data['ben_a']['ten_cong_ty']}")
    r_sa.bold = True
    r_sa.font.name = "Times New Roman"
    r_sa.font.size = Pt(11)
    r_sa.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    pb = cell_b.paragraphs[0]
    pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sb = pb.add_run(f"ĐẠI DIỆN BÊN B / 乙方代表\n(Ký tên, đóng dấu / 簽字蓋章)\n\n\n\n\n{data['ben_b']['ten_cong_ty']}")
    r_sb.bold = True
    r_sb.font.name = "Times New Roman"
    r_sb.font.size = Pt(11)
    r_sb.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    clean_so_hd = re.sub(r'[\\/*?:"<>|]', '_', data["so_hop_dong"])
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"Bien_Ban_Nghiem_Thu_{clean_so_hd}_{date_str}.docx"
    target_dir = WORKING_DIR / "Ho So Du An" / "Nghiem Thu"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_name

    try:
        doc.save(target_path)
    except PermissionError:
        file_name = f"Bien_Ban_Nghiem_Thu_{clean_so_hd}_{date_str}_v2.docx"
        target_path = target_dir / file_name
        doc.save(target_path)

    return {
        "status": "success",
        "file_name": file_name,
        "download_url": f"/api/v1/acceptance/download/{file_name}",
        "total_amount": data["tong_tien_formatted"] + " VND",
        "acceptance_data": data
    }
