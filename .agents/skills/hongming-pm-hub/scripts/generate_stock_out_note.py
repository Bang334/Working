# -*- coding: utf-8 -*-
"""
Script tạo Phiếu Xuất Kho kiêm Biên Bản Bàn Giao Thiết Bị chuẩn song ngữ Việt - Trung
Dành cho Quản lý Dự án (PM) Công ty TNHH Toàn Cầu Hong Ming (宏明環球有限公司)
Đảm bảo chuẩn in A4, logo, font 微軟正黑體, đường viền, không cắt chữ.
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image
from openpyxl.utils import get_column_letter

def create_stock_out_excel(output_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Phiếu Xuất Kho - 出庫單"

    # Chế độ xem trang in
    ws.views.sheetView[0].showGridLines = True

    # Độ rộng các cột tối ưu cho khổ giấy A4
    col_widths = {
        'A': 6.0,   # STT / 序號
        'B': 26.0,  # Tên thiết bị / 設備名稱
        'C': 34.0,  # Model & Thông số kỹ thuật / 型號與技術規格
        'D': 18.0,  # Mã Serial / S/N 序號
        'E': 8.0,   # ĐVT / 單位
        'F': 10.0,  # SL HĐ / 合約數
        'G': 10.0,  # Thực xuất / 實出數
        'H': 15.0,  # Tình trạng / 外觀狀況
        'I': 14.0   # Ghi chú / 備註
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # Định nghĩa Font và Style
    font_family = "微軟正黑體"
    f_company = Font(name=font_family, size=13, bold=True, color="1F497D")
    f_company_sub = Font(name=font_family, size=9.5, color="404040")
    f_title = Font(name=font_family, size=16, bold=True, color="002060")
    f_subtitle = Font(name=font_family, size=11, bold=True, color="1F497D")
    f_meta_bold = Font(name=font_family, size=9.5, bold=True, color="000000")
    f_meta_val = Font(name=font_family, size=9.5, color="1A1A1A")
    f_header = Font(name=font_family, size=9.5, bold=True, color="FFFFFF")
    f_data = Font(name=font_family, size=9.0, color="000000")
    f_data_bold = Font(name=font_family, size=9.0, bold=True, color="000000")
    f_sign_title = Font(name=font_family, size=10, bold=True, color="002060")
    f_sign_sub = Font(name=font_family, size=8.5, italic=True, color="595959")

    # Màu nền
    fill_header = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_meta = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
    fill_zebra = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    fill_summary = PatternFill(start_color="EAEEF3", end_color="EAEEF3", fill_type="solid")

    # Viền ô
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )
    box_border = Border(
        left=Side(style='medium', color='1F497D'),
        right=Side(style='medium', color='1F497D'),
        top=Side(style='medium', color='1F497D'),
        bottom=Side(style='medium', color='1F497D')
    )
    header_border = Border(
        left=Side(style='thin', color='FFFFFF'),
        right=Side(style='thin', color='FFFFFF'),
        top=Side(style='medium', color='1F497D'),
        bottom=Side(style='medium', color='1F497D')
    )

    # 1. Chèn Logo
    logo_path = r"E:\Working\.agents\skills\hongming-pm-hub\resources\images\image2.png"
    if os.path.exists(logo_path):
        img = Image(logo_path)
        img.width = 160
        img.height = 78
        ws.add_image(img, "A1")

    # 2. Thông tin Công ty Hong Ming (Cột C -> I)
    ws.merge_cells("C1:I1")
    ws["C1"] = "CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"
    ws["C1"].font = f_company
    ws["C1"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("C2:I2")
    ws["C2"] = "Địa chỉ / 地址: Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, TP. Hồ Chí Minh, Việt Nam"
    ws["C2"].font = f_company_sub
    ws["C2"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("C3:I3")
    ws["C3"] = "MST / 稅號: 0318280158 | Tel / 電話: +84 966 687 109 | Email: sales@hongming-global.com"
    ws["C3"].font = f_company_sub
    ws["C3"].alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 18
    ws.row_dimensions[4].height = 10

    # 3. Tiêu đề Phiếu
    ws.merge_cells("A5:I5")
    ws["A5"] = "PHIẾU XUẤT KHO KIÊM BIÊN BẢN BÀN GIAO THIẾT BỊ"
    ws["A5"].font = f_title
    ws["A5"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A6:I6")
    ws["A6"] = "出庫單 暨 設備交貨移交確認單 (GOODS ISSUE & DELIVERY NOTE)"
    ws["A6"].font = f_subtitle
    ws["A6"].alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[5].height = 26
    ws.row_dimensions[6].height = 20
    ws.row_dimensions[7].height = 8

    # 4. Khối Thông tin Quản lý / Dự án (Rows 8 to 11)
    meta_data = [
        ("Số phiếu / 單號:", "HM-XK-20261009-001", "Ngày xuất / 出庫日期:", "09/10/2026"),
        ("Căn cứ HĐ / 依據合約:", "HMV021020260001 (Dự án IoT Cheng Feng 1 Tỷ)", "Đợt giao / 交貨批次:", "Đợt 2 - Giao phần cứng (30% GT HĐ)"),
        ("Đơn vị nhận / 接收單位:", "CÔNG TY TNHH CHENG FENG LE HUA (VIỆT NAM) / 越南成峰樂華有限公司", "MST / 稅號:", "2301124568"),
        ("Địa điểm giao / 交貨地點:", "KCN Hòa Phú, Xã Mai Đình, Thị xã Hiệp Hòa, Tỉnh Bắc Giang / Bắc Ninh", "Đầu mối nhận / 聯絡窗口:", "Mr. Trương (ME) - 0988.xxx.xxx")
    ]

    cur_row = 8
    for row_info in meta_data:
        ws.row_dimensions[cur_row].height = 21
        # Label 1
        ws.merge_cells(f"A{cur_row}:B{cur_row}")
        ws[f"A{cur_row}"] = row_info[0]
        ws[f"A{cur_row}"].font = f_meta_bold
        ws[f"A{cur_row}"].fill = fill_meta
        ws[f"A{cur_row}"].alignment = Alignment(horizontal="left", vertical="center")
        
        # Value 1
        ws.merge_cells(f"C{cur_row}:E{cur_row}")
        ws[f"C{cur_row}"] = row_info[1]
        ws[f"C{cur_row}"].font = f_meta_val
        ws[f"C{cur_row}"].alignment = Alignment(horizontal="left", vertical="center")
        
        # Label 2
        ws[f"F{cur_row}"] = row_info[2]
        ws[f"F{cur_row}"].font = f_meta_bold
        ws[f"F{cur_row}"].fill = fill_meta
        ws[f"F{cur_row}"].alignment = Alignment(horizontal="left", vertical="center")
        
        # Value 2
        ws.merge_cells(f"G{cur_row}:I{cur_row}")
        ws[f"G{cur_row}"] = row_info[3]
        ws[f"G{cur_row}"].font = f_meta_val
        ws[f"G{cur_row}"].alignment = Alignment(horizontal="left", vertical="center")

        # Viền nhẹ cho khối meta
        for c in range(1, 10):
            col_letter = get_column_letter(c)
            cell = ws[f"{col_letter}{cur_row}"]
            cell.border = thin_border

        cur_row += 1

    ws.row_dimensions[cur_row].height = 10
    cur_row += 1

    # 5. Header Bảng Hàng Hóa (Row 13)
    headers = [
        ("A", "STT\n序號"),
        ("B", "Tên thiết bị\n品名"),
        ("C", "Quy cách kỹ thuật & Nhãn hiệu\n規格型號與品牌"),
        ("D", "Mã Serial / S/N\n產品序號"),
        ("E", "ĐVT\n單位"),
        ("F", "SL HĐ\n合約數"),
        ("G", "Thực xuất\n實出數"),
        ("H", "Tình trạng\n品質狀況"),
        ("I", "Ghi chú\n備註")
    ]
    ws.row_dimensions[cur_row].height = 32
    for col_l, text in headers:
        cell = ws[f"{col_l}{cur_row}"]
        cell.value = text
        cell.font = f_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = header_border

    cur_row += 1

    # 6. Danh sách Thiết bị xuất kho thực tế (Dự án Cheng Feng)
    items = [
        (
            1,
            "Máy chủ ứng dụng & CSDL\n伺服器主機",
            "Dell PowerEdge R760xs (Xeon Silver 4509Y, 64GB DDR5, 2x960GB SAS Enterprise)",
            "SN: 8F9QX24-VN",
            "Bộ/台",
            1, 1,
            "Mới 100%, Nguyên seal",
            "Kèm cáp nguồn"
        ),
        (
            2,
            "Máy trạm giám sát xưởng\n工作站電腦",
            "Asus ExpertCenter D701MER (Core i5-14500, 16GB RAM, 512GB SSD NVMe)",
            "SN: N6PMC009123",
            "Bộ/台",
            1, 1,
            "Mới 100%, Thùng zin",
            "Kèm bàn phím, chuột"
        ),
        (
            3,
            "Switch chuyển mạch quản lý\n管理型交換器",
            "TP-Link TL-SG3428 (24 Port Gigabit L2 Managed + 4 Khe cắm SFP 1G)",
            "SN: 2248100101-03\n(3 chiếc)",
            "Chiếc/台",
            3, 3,
            "Mới 100%, Đầy đủ tai rack",
            "Lắp tủ trung tâm"
        ),
        (
            4,
            "Bộ I/O Gateway công nghiệp\n機台聯網閘道器",
            "Hong Ming Industrial Edge Gateway HMGW-2026 (RS-485 Modbus, RJ45 LAN, Input 24VDC)",
            "SN: HMGW2610-01\nđến HMGW2610-10",
            "Bộ/套",
            10, 10,
            "Mới 100%, Hoạt động tốt",
            "Gắn trạm máy dập"
        ),
        (
            5,
            "Đèn tháp trạng thái 3 màu\n三色狀態警示燈",
            "Đèn LED 3 tầng Đỏ-Vàng-Xanh kèm còi buzzer báo động 24VDC (Phi 50)",
            "Theo lô / Batch",
            "Bộ/支",
            10, 10,
            "Mới 100%, Nguyên kiện",
            "Kèm chân đỡ L"
        ),
        (
            6,
            "Rơ-le trung gian 24VDC\n繼電器含底座",
            "Omron MY2N-GS 24VDC (2 Cặp tiếp điểm 5A) + Đế cắm gắn ray Din-rail",
            "Theo lô / Batch",
            "Bộ/組",
            20, 20,
            "Mới 100%, Nguyên kiện",
            "Cách ly tín hiệu"
        ),
        (
            7,
            "Tủ mạng phân phối xưởng 6U\n6U壁掛機櫃",
            "Tủ Rack 6U D400 sơn tĩnh điện màu đen + Thanh nguồn PDU 6 ổ cắm 10A",
            "HM-RK6U-01, 02",
            "Tủ/個",
            2, 2,
            "Mới 100%, Không trầy xước",
            "Treo tường xưởng 1, 2"
        ),
        (
            8,
            "Dây cáp mạng Cat6 UTP\nCat6 網路線",
            "Cáp mạng Alantek Cat6 4-Pair UTP 23AWG lõi đồng nguyên chất (Cuộn 305m)",
            "Lot: 202608-AT",
            "Thùng/箱",
            2, 2,
            "Mới 100%, Nguyên cuộn",
            "Kéo tín hiệu LAN"
        ),
        (
            9,
            "Cáp tín hiệu chống nhiễu\nRS-485 隔離信號線",
            "Cáp Alantek 1 Pair 24AWG bọc màng bạc chống nhiễu chuyên dụng RS-485 (200m/cuộn)",
            "Lot: 202609-RS",
            "Cuộn/卷",
            2, 2,
            "Mới 100%, Nguyên cuộn",
            "Kết nối máy tiện/dập"
        )
    ]

    start_item_row = cur_row
    for item in items:
        ws.row_dimensions[cur_row].height = 36
        fill_cur = fill_zebra if item[0] % 2 == 0 else PatternFill(fill_type=None)

        ws[f"A{cur_row}"] = item[0]
        ws[f"A{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")
        
        ws[f"B{cur_row}"] = item[1]
        ws[f"B{cur_row}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws[f"B{cur_row}"].font = f_data_bold
        
        ws[f"C{cur_row}"] = item[2]
        ws[f"C{cur_row}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        ws[f"D{cur_row}"] = item[3]
        ws[f"D{cur_row}"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        ws[f"E{cur_row}"] = item[4]
        ws[f"E{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")
        
        ws[f"F{cur_row}"] = item[5]
        ws[f"F{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")
        
        ws[f"G{cur_row}"] = item[6]
        ws[f"G{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"G{cur_row}"].font = f_data_bold
        
        ws[f"H{cur_row}"] = item[7]
        ws[f"H{cur_row}"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        ws[f"I{cur_row}"] = item[8]
        ws[f"I{cur_row}"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        for c in range(1, 10):
            col_letter = get_column_letter(c)
            cell = ws[f"{col_letter}{cur_row}"]
            if col_letter in ['B', 'G']:
                cell.font = f_data_bold
            else:
                cell.font = f_data
            if fill_cur.fill_type:
                cell.fill = fill_cur
            cell.border = thin_border

        cur_row += 1

    end_item_row = cur_row - 1

    # Dòng Tổng Cộng
    ws.row_dimensions[cur_row].height = 24
    ws.merge_cells(f"A{cur_row}:E{cur_row}")
    ws[f"A{cur_row}"] = "TỔNG CỘNG / 合計 (9 Hạng mục thiết bị bàn giao)"
    ws[f"A{cur_row}"].font = f_meta_bold
    ws[f"A{cur_row}"].alignment = Alignment(horizontal="right", vertical="center")

    ws[f"F{cur_row}"] = f"=SUM(F{start_item_row}:F{end_item_row})"
    ws[f"F{cur_row}"].font = f_meta_bold
    ws[f"F{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")

    ws[f"G{cur_row}"] = f"=SUM(G{start_item_row}:G{end_item_row})"
    ws[f"G{cur_row}"].font = f_meta_bold
    ws[f"G{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(f"H{cur_row}:I{cur_row}")
    ws[f"H{cur_row}"] = "Đạt 100% số lượng HĐ đợt 2"
    ws[f"H{cur_row}"].font = f_meta_bold
    ws[f"H{cur_row}"].alignment = Alignment(horizontal="center", vertical="center")

    for c in range(1, 10):
        col_letter = get_column_letter(c)
        cell = ws[f"{col_letter}{cur_row}"]
        cell.fill = fill_summary
        cell.border = thin_border

    cur_row += 1

    # 7. Chứng từ kèm theo & Ghi chú điều kiện
    ws.row_dimensions[cur_row].height = 10
    cur_row += 1

    ws.merge_cells(f"A{cur_row}:I{cur_row}")
    ws[f"A{cur_row}"] = "CHỨNG TỪ ĐI KÈM KHI GIAO HÀNG / 隨貨檢附文件:"
    ws[f"A{cur_row}"].font = f_meta_bold
    ws[f"A{cur_row}"].alignment = Alignment(horizontal="left", vertical="center")
    cur_row += 1

    doc_notes = [
        "1. Bản sao Chứng nhận xuất xứ (CO) & Chứng nhận chất lượng (CQ) của Server Dell, Switch TP-Link.",
        "2. Phiếu kiểm tra ngoại quan và xuất xưởng (QC Inspection Pass) của Gateway Hong Ming.",
        "3. Biên bản bàn giao này là căn cứ để kích hoạt điều khoản thanh toán Đợt 2 (30% giá trị hợp đồng) theo Điều 3 Hợp đồng số HMV021020260001."
    ]
    for note in doc_notes:
        ws.row_dimensions[cur_row].height = 18
        ws.merge_cells(f"A{cur_row}:I{cur_row}")
        ws[f"A{cur_row}"] = f"   - {note}"
        ws[f"A{cur_row}"].font = f_meta_val
        ws[f"A{cur_row}"].alignment = Alignment(horizontal="left", vertical="center")
        cur_row += 1

    ws.row_dimensions[cur_row].height = 12
    cur_row += 1

    # 8. Khối Chữ Ký 4 Bên (Rows cur_row -> cur_row + 5)
    ws.merge_cells(f"A{cur_row}:B{cur_row}")
    ws[f"A{cur_row}"] = "NGƯỜI LẬP PHIẾU / PM\n製單人 (專案經理)"
    
    ws.merge_cells(f"C{cur_row}:D{cur_row}")
    ws[f"C{cur_row}"] = "THỦ KHO XUẤT HÀNG\n出庫倉管員"

    ws.merge_cells(f"E{cur_row}:G{cur_row}")
    ws[f"E{cur_row}"] = "NGƯỜI GIAO HÀNG / VẬN CHUYỂN\n送貨人 / 運送工程師"

    ws.merge_cells(f"H{cur_row}:I{cur_row}")
    ws[f"H{cur_row}"] = "ĐẠI DIỆN KHÁCH HÀNG NHẬN HÀNG\n收貨單位簽收 (客戶代表)"

    ws.row_dimensions[cur_row].height = 28
    for c in [("A", "B"), ("C", "D"), ("E", "G"), ("H", "I")]:
        start_c = c[0]
        cell = ws[f"{start_c}{cur_row}"]
        cell.font = f_sign_title
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    cur_row += 1
    
    # Dòng ghi chú ký tên
    ws.merge_cells(f"A{cur_row}:B{cur_row}")
    ws[f"A{cur_row}"] = "(Ký, ghi rõ họ tên / 簽名)"
    
    ws.merge_cells(f"C{cur_row}:D{cur_row}")
    ws[f"C{cur_row}"] = "(Ký, ghi rõ họ tên / 簽名)"

    ws.merge_cells(f"E{cur_row}:G{cur_row}")
    ws[f"E{cur_row}"] = "(Ký, ghi rõ họ tên / 簽名)"

    ws.merge_cells(f"H{cur_row}:I{cur_row}")
    ws[f"H{cur_row}"] = "(Ký tên, đóng dấu / 簽章)"

    ws.row_dimensions[cur_row].height = 18
    for c in [("A", "B"), ("C", "D"), ("E", "G"), ("H", "I")]:
        start_c = c[0]
        cell = ws[f"{start_c}{cur_row}"]
        cell.font = f_sign_sub
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Khoảng trống để ký tên (4 dòng)
    for _ in range(4):
        cur_row += 1
        ws.row_dimensions[cur_row].height = 16

    cur_row += 1
    # Tên người ký dự kiến
    ws.merge_cells(f"A{cur_row}:B{cur_row}")
    ws[f"A{cur_row}"] = "Project Manager\nHong Ming Global"
    
    ws.merge_cells(f"C{cur_row}:D{cur_row}")
    ws[f"C{cur_row}"] = "Bộ phận Kho vận\n倉儲物流部"

    ws.merge_cells(f"E{cur_row}:G{cur_row}")
    ws[f"E{cur_row}"] = "Kỹ sư Triển khai\n現場實施工程師"

    ws.merge_cells(f"H{cur_row}:I{cur_row}")
    ws[f"H{cur_row}"] = "Kỹ sư ME / Quản lý kho\nCheng Feng Le Hua (VN)"

    ws.row_dimensions[cur_row].height = 28
    for c in [("A", "B"), ("C", "D"), ("E", "G"), ("H", "I")]:
        start_c = c[0]
        cell = ws[f"{start_c}{cur_row}"]
        cell.font = f_meta_bold
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Đặt vùng in & lề in vừa trang A4
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_area = f"$A$1:$I${cur_row}"

    wb.save(output_path)
    print(f"Xuat file thanh cong tai: {output_path}")

if __name__ == "__main__":
    out_file = r"e:\Working\PHIEU_XUAT_KHO_KIEM_BAN_GIAO_THIET_BI.xlsx"
    create_stock_out_excel(out_file)
