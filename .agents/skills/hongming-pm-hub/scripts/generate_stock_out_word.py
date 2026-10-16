# -*- coding: utf-8 -*-
"""
Script tạo Phiếu Xuất Kho kiêm Biên Bản Bàn Giao Thiết Bị chuẩn Word (.docx)
Định dạng Song ngữ Việt - Trung (Phồn thể) chuẩn mực Hong Ming Global.
Đầy đủ Quốc hiệu, Tiêu ngữ, Pháp nhân 2 bên, Bảng thiết bị, Serial No, Mốc thanh toán & 4 ô chữ ký đóng dấu.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Thiết lập padding lề trong cho ô bảng"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex):
    """Tô màu nền ô bảng (ví dụ: '1F497D' hoặc 'F2F5F9')"""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_border(cell, **kwargs):
    """
    Thiết lập đường viền ô bảng.
    kwargs có thể là: top, bottom, left, right với dict:
    {'sz': 4, 'val': 'single', 'color': 'D3D3D3'}
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f'w:{edge}'
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get('val', 'single'))
            element.set(qn('w:sz'), str(edge_data.get('sz', 4)))
            element.set(qn('w:space'), '0')
            element.set(qn('w:color'), edge_data.get('color', 'auto'))
            tcBorders.append(element)
    tcPr.append(tcBorders)

def create_stock_out_docx(output_path):
    doc = docx.Document()

    # Căn lề chuẩn trang A4
    section = doc.sections[0]
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)

    # Đổi font mặc định sang Times New Roman
    style_normal = doc.styles['Normal']
    font_normal = style_normal.font
    font_normal.name = 'Times New Roman'
    font_normal.size = Pt(10.5)
    font_normal.color.rgb = RGBColor(0, 0, 0)

    # 1. Quốc hiệu & Tiêu ngữ (Song ngữ Việt - Trung)
    p_qh = doc.add_paragraph()
    p_qh.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_qh.paragraph_format.space_before = Pt(0)
    p_qh.paragraph_format.space_after = Pt(2)
    p_qh.paragraph_format.line_spacing = 1.15
    run1 = p_qh.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM / 越南社會主義共和國\n")
    run1.bold = True
    run1.font.size = Pt(11)
    run2 = p_qh.add_run("Độc lập – Tự do – Hạnh phúc / 獨立－自由－幸福\n")
    run2.bold = True
    run2.font.size = Pt(10.5)
    run3 = p_qh.add_run("---------------o0o---------------")
    run3.font.size = Pt(9.5)

    # 2. Tiêu đề Văn bản
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(10)
    p_title.paragraph_format.space_after = Pt(3)
    r_t1 = p_title.add_run("PHIẾU XUẤT KHO KIÊM BIÊN BẢN BÀN GIAO THIẾT BỊ\n")
    r_t1.bold = True
    r_t1.font.size = Pt(14)
    r_t1.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
    
    r_t2 = p_title.add_run("出庫單 暨 設備交貨移交確認單\n")
    r_t2.bold = True
    r_t2.font.size = Pt(13)
    r_t2.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

    r_t3 = p_title.add_run("(Xác nhận giao hàng tại công trình – Kích hoạt mốc thanh toán đợt giao phần cứng)\n（工程現場交貨確認－啟動硬體交貨期款）")
    r_t3.italic = True
    r_t3.font.size = Pt(9.5)

    # 3. Thông tin Quản lý Số phiếu & Căn cứ
    p_ref = doc.add_paragraph()
    p_ref.paragraph_format.space_before = Pt(6)
    p_ref.paragraph_format.space_after = Pt(4)
    p_ref.paragraph_format.line_spacing = 1.2
    
    p_ref.add_run("• Số phiếu / 出庫單號: ").bold = True
    p_ref.add_run("HM-XK-20261009-001               ")
    p_ref.add_run("• Ngày xuất / 出庫日期: ").bold = True
    p_ref.add_run("09/10/2026\n")

    p_ref.add_run("• Căn cứ Hợp đồng / 依據合約: ").bold = True
    p_ref.add_run("Hợp đồng mua bán số HMV021020260001 (Dự án SMB IoT Cheng Feng 1.000.000.000 VNĐ)\n")
    
    p_ref.add_run("• Đợt giao hàng / 交貨批次: ").bold = True
    p_ref.add_run("Đợt 2 – Bàn giao thiết bị phần cứng nhà máy (Mốc giải ngân 30% giá trị hợp đồng)")

    # 4. Bảng Thông tin Hai Bên (Bên Giao & Bên Nhận)
    p_party_title = doc.add_paragraph()
    p_party_title.paragraph_format.space_before = Pt(8)
    p_party_title.paragraph_format.space_after = Pt(4)
    r_party_hdr = p_party_title.add_run("I. THÔNG TIN CÁC BÊN GIAO NHẬN / 一、交接雙方資訊")
    r_party_hdr.bold = True
    r_party_hdr.font.size = Pt(11)

    tbl_parties = doc.add_table(rows=5, cols=2)
    tbl_parties.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_parties.autofit = False

    party_headers = [
        ("BÊN BÁN / BÊN XUẤT KHO (BÊN B)\n乙方（出庫方／供應方）：", "BÊN MUA / BÊN NHẬN HÀNG (BÊN A)\n甲方（收貨方／買方）："),
        ("Tên đơn vị: CÔNG TY TNHH TOÀN CẦU HONG MING\n(宏明環球有限公司)", "Tên đơn vị: CÔNG TY TNHH CHENG FENG LE HUA (VN)\n(越南成峰樂華有限公司)"),
        ("Địa chỉ: Lầu 2, số 68 Nguyễn Huệ, P. Sài Gòn, TP.HCM\n(胡志明市西貢坊阮惠街68號2樓)", "Địa chỉ: KCN Hòa Phú, Xã Mai Đình, Hiệp Hòa, Bắc Giang\n(北江省洽和市社和富工業區)"),
        ("MST: 0318280158 | ĐT: +84 966 687 109", "MST: 2301124568 | ĐT: 0988.xxx.xxx"),
        ("Đại diện giao: Kỹ sư Triển khai / Thủ kho Hong Ming", "Đại diện nhận: Kỹ sư Cơ điện ME / Quản lý kho nhà máy")
    ]

    border_spec = {'sz': 4, 'val': 'single', 'color': 'CCCCCC'}

    for row_idx, (col0_text, col1_text) in enumerate(party_headers):
        row = tbl_parties.rows[row_idx]
        
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Cm(9.0)
        c1.width = Cm(9.0)
        
        c0.text = col0_text
        c1.text = col1_text

        set_cell_margins(c0, 80, 80, 120, 120)
        set_cell_margins(c1, 80, 80, 120, 120)

        set_cell_border(c0, top=border_spec, bottom=border_spec, left=border_spec, right=border_spec)
        set_cell_border(c1, top=border_spec, bottom=border_spec, left=border_spec, right=border_spec)

        if row_idx == 0:
            set_cell_shading(c0, "1F497D")
            set_cell_shading(c1, "1F497D")
            for c in (c0, c1):
                for p in c.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for r in p.runs:
                        r.bold = True
                        r.font.size = Pt(10)
                        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            for c in (c0, c1):
                for p in c.paragraphs:
                    p.paragraph_format.line_spacing = 1.15
                    for r in p.runs:
                        r.font.size = Pt(9.5)

    # 5. Bảng Danh Mục Thiết Bị Bàn Giao
    p_dev_title = doc.add_paragraph()
    p_dev_title.paragraph_format.space_before = Pt(12)
    p_dev_title.paragraph_format.space_after = Pt(4)
    r_dev_hdr = p_dev_title.add_run("II. DANH MỤC THIẾT BỊ VÀ TÌNH TRẠNG BÀN GIAO / 二、設備交貨明細與品質確認")
    r_dev_hdr.bold = True
    r_dev_hdr.font.size = Pt(11)

    items_data = [
        ("STT\n序號", "Tên thiết bị & Quy cách\n設備品名與型號規格", "Mã Serial (S/N)\n產品序號", "ĐVT\n單位", "SL HĐ\n合約數", "Thực xuất\n實出數", "Tình trạng\n品質狀況", "Ghi chú\n備註"),
        ("1", "Máy chủ ứng dụng & CSDL Dell PowerEdge R760xs\n(Xeon Silver 4509Y, 64GB DDR5, 2x960GB SAS Enterprise)\n伺服器主機", "SN: 8F9QX24-VN", "Bộ\n台", "1", "1", "Mới 100%, Nguyên seal", "Kèm cáp nguồn zin"),
        ("2", "Máy trạm giám sát xưởng Asus ExpertCenter D701MER\n(Core i5-14500, 16GB RAM, 512GB SSD NVMe)\n工作站電腦", "SN: N6PMC009123", "Bộ\n台", "1", "1", "Mới 100%, Thùng zin", "Kèm phím + chuột"),
        ("3", "Switch quản lý TP-Link TL-SG3428\n(24 Port GbE L2 Managed + 4 Khe cắm SFP 1G)\n管理型交換器", "SN: 2248100101\nSN: 2248100102\nSN: 2248100103", "Chiếc\n台", "3", "3", "Mới 100%, Nguyên hộp", "Lắp tủ trung tâm"),
        ("4", "Bộ I/O Gateway công nghiệp Hong Ming HMGW-2026\n(RS-485 Modbus RTU, LAN RJ45, Nguồn 24VDC)\n機聯網閘道器", "SN: HMGW2610-01\nđến HMGW2610-10", "Bộ\n套", "10", "10", "Mới 100%, Hoạt động tốt", "Gắn trạm máy dập"),
        ("5", "Đèn tháp trạng thái 3 màu Đỏ-Vàng-Xanh + Còi 24VDC\n三色狀態警示燈", "Theo lô\nBatch Lot", "Bộ\n支", "10", "10", "Mới 100%, Nguyên kiện", "Kèm chân đỡ L"),
        ("6", "Rơ-le trung gian 24VDC Omron MY2N-GS + Đế ray\n繼電器含底座", "Theo lô\nBatch Lot", "Bộ\n組", "20", "20", "Mới 100%, Nguyên kiện", "Cách ly tín hiệu"),
        ("7", "Tủ mạng treo tường 6U D400 + Thanh nguồn PDU 6 port\n6U壁掛機櫃", "HM-RK6U-01, 02", "Tủ\n個", "2", "2", "Mới 100%, Sơn đẹp", "Treo xưởng 1, 2"),
        ("8", "Cáp mạng Alantek Cat6 UTP 4-Pair 23AWG (Cuộn 305m)\nCat6 網路線", "Lot: 202608-AT", "Thùng\n箱", "2", "2", "Mới 100%, Nguyên cuộn", "Kéo mạng LAN"),
        ("9", "Cáp chống nhiễu Alantek RS-485 1 Pair (Cuộn 200m)\nRS-485 隔離信號線", "Lot: 202609-RS", "Cuộn\n卷", "2", "2", "Mới 100%, Nguyên cuộn", "Kết nối máy tiện"),
        ("CỘNG", "TỔNG CỘNG / 合計 (9 Hạng mục thiết bị phần cứng bàn giao)", "", "", "41", "41", "Đạt 100% hợp đồng", "")
    ]

    tbl_items = doc.add_table(rows=len(items_data), cols=8)
    tbl_items.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_items.autofit = False

    col_widths_cm = [1.0, 5.8, 2.6, 1.2, 1.3, 1.3, 2.8, 2.0]

    for r_idx, row_vals in enumerate(items_data):
        row = tbl_items.rows[r_idx]
        is_hdr = (r_idx == 0)
        is_total = (r_idx == len(items_data) - 1)

        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = Cm(col_widths_cm[c_idx])
            cell.text = val
            set_cell_margins(cell, 60, 60, 80, 80)

            # Borders
            b_color = "1F497D" if is_hdr else "CCCCCC"
            set_cell_border(cell, 
                            top={'sz': 6 if is_hdr else 4, 'val': 'single', 'color': b_color},
                            bottom={'sz': 6 if is_hdr else 4, 'val': 'single', 'color': b_color},
                            left={'sz': 4, 'val': 'single', 'color': b_color},
                            right={'sz': 4, 'val': 'single', 'color': b_color})

            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)

            if is_hdr:
                set_cell_shading(cell, "1F497D")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            elif is_total:
                set_cell_shading(cell, "EAEEF3")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx in [0, 4, 5] else WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(9.0)
            else:
                if r_idx % 2 == 1:
                    set_cell_shading(cell, "F9FAFB")
                if c_idx in [0, 2, 3, 4, 5, 6]:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.size = Pt(8.5)

    # 6. Chứng từ đi kèm & Cam kết pháp lý
    p_notes_title = doc.add_paragraph()
    p_notes_title.paragraph_format.space_before = Pt(10)
    p_notes_title.paragraph_format.space_after = Pt(3)
    r_n_hdr = p_notes_title.add_run("III. CHỨNG TỪ ĐI KÈM & CĂN CỨ THANH TOÁN / 三、隨貨文件與付款依據")
    r_n_hdr.bold = True
    r_n_hdr.font.size = Pt(11)

    notes = [
        ("1. Chứng từ kỹ thuật đi kèm:", "Bản sao Giấy chứng nhận xuất xứ (CO) và Chất lượng (CQ) của Server Dell, Switch TP-Link; Phiếu kiểm tra ngoại quan và xuất xưởng (QC Inspection Pass) của Hong Ming Global."),
        ("2. Tình trạng bàn giao:", "Toàn bộ thiết bị phần cứng được bàn giao đầy đủ số lượng, nguyên đai nguyên kiện, mới 100%, không bị nứt vỡ hay trầy xước ngoại quan, đúng thông số kỹ thuật cam kết."),
        ("3. Giá trị pháp lý & Mốc thanh toán:", "Biên bản bàn giao này được lập thành 04 (bốn) bản có giá trị pháp lý như nhau (Bên Mua giữ 02 bản, Bên Bán giữ 02 bản). Đây là chứng từ hoàn tất nghĩa vụ giao hàng của Bên B và là căn cứ để Bên A kích hoạt thanh toán Đợt 2: 30% giá trị hợp đồng tương đương 300.000.000 VNĐ (Ba trăm triệu đồng chẵn) theo Điều 3 Hợp đồng số HMV021020260001.")
    ]

    for n_title, n_desc in notes:
        p_note = doc.add_paragraph()
        p_note.paragraph_format.space_before = Pt(2)
        p_note.paragraph_format.space_after = Pt(2)
        p_note.paragraph_format.line_spacing = 1.15
        r_nt = p_note.add_run(f"• {n_title} ")
        r_nt.bold = True
        r_nt.font.size = Pt(9.5)
        r_nd = p_note.add_run(n_desc)
        r_nd.font.size = Pt(9.5)

    # 7. Khối Chữ Ký 4 Bên (Table chữ ký)
    p_sig_title = doc.add_paragraph()
    p_sig_title.paragraph_format.space_before = Pt(12)
    p_sig_title.paragraph_format.space_after = Pt(4)
    r_s_hdr = p_sig_title.add_run("IV. ĐẠI DIỆN CÁC BÊN KÝ XÁC NHẬN / 四、各方代表簽字確認")
    r_s_hdr.bold = True
    r_s_hdr.font.size = Pt(11)

    tbl_sig = doc.add_table(rows=4, cols=4)
    tbl_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_sig.autofit = False

    sig_headers = [
        "NGƯỜI LẬP PHIẾU / PM\n製單人 (專案經理)",
        "THỦ KHO XUẤT HÀNG\n出庫倉管員",
        "NGƯỜI GIAO HÀNG\n送貨人 / 運送工程師",
        "ĐẠI DIỆN KHÁCH HÀNG\n收貨單位簽收 (客戶)"
    ]

    for c_idx, text in enumerate(sig_headers):
        tbl_sig.rows[0].cells[c_idx].width = Cm(4.5)
        tbl_sig.rows[1].cells[c_idx].width = Cm(4.5)
        tbl_sig.rows[2].cells[c_idx].width = Cm(4.5)
        tbl_sig.rows[3].cells[c_idx].width = Cm(4.5)

        # Row 0: Chức danh
        c0 = tbl_sig.rows[0].cells[c_idx]
        c0.text = text
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p0.runs:
            r.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)

        # Row 1: Ghi chú ký tên
        c1 = tbl_sig.rows[1].cells[c_idx]
        c1.text = "(Ký, ghi rõ họ tên / 簽名)" if c_idx < 3 else "(Ký tên, đóng dấu / 簽章)"
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p1.runs:
            r.italic = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F)

        # Row 2: Khoảng trống ký tên
        c2 = tbl_sig.rows[2].cells[c_idx]
        c2.text = "\n\n\n"

        # Row 3: Họ tên đơn vị
        c3 = tbl_sig.rows[3].cells[c_idx]
        unit_names = [
            "Project Manager\nHong Ming Global",
            "Bộ phận Kho Vận\nHong Ming Global",
            "Kỹ sư Triển khai\nHong Ming Global",
            "Đại diện Bên Mua (Bên A)\nCheng Feng Le Hua (VN)"
        ]
        c3.text = unit_names[c_idx]
        p3 = c3.paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p3.runs:
            r.bold = True
            r.font.size = Pt(9.0)

    # Viền mờ cho bảng chữ ký
    for r in tbl_sig.rows:
        for c in r.cells:
            set_cell_margins(c, 40, 40, 60, 60)
            set_cell_border(c, 
                            top={'sz': 4, 'val': 'dotted', 'color': 'D9D9D9'},
                            bottom={'sz': 4, 'val': 'dotted', 'color': 'D9D9D9'},
                            left={'sz': 4, 'val': 'dotted', 'color': 'D9D9D9'},
                            right={'sz': 4, 'val': 'dotted', 'color': 'D9D9D9'})

    doc.save(output_path)
    print(f"Xuat file Word thanh cong tai: {output_path}")

if __name__ == "__main__":
    out_file = r"e:\Working\PHIEU_XUAT_KHO_KIEM_BAN_GIAO_THIET_BI.docx"
    create_stock_out_docx(out_file)
