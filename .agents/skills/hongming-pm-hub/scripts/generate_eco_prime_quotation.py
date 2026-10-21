# -*- coding: utf-8 -*-
"""
=============================================================================
HONG MING GLOBAL & ECO PRIME - STANDARD QUOTATION GENERATOR (CHUẨN 100% MẪU GỐC)
=============================================================================
Cập nhật nội dung tham khảo chuẩn mực theo ảnh Sếp đưa:
1. Hạng mục 7: Cáp mạng Cat6, cáp RS485 & Vật tư phụ (輔助材料).
2. Hạng mục 8: Chi phí thi công (施工費) với nội dung chi tiết chuyên nghiệp:
   - Cài đặt hệ thống 系統設定
   - Lắp đặt phần cứng 4 trạm biến áp 4座變電站硬體安裝
   - Hiệu chỉnh chức năng & liên động Modbus CC2051 功能調適與通訊聯調
   - Phí quản lý, vận chuyển 管理、運費
   - Thiết kế bản vẽ hoàn công 設計、竣工圖費用
   - Chi phí đi lại, giàn giáo, dụng cụ an toàn 交通費、鷹架、工安具...

Form chuẩn ECO PRIME:
- Toàn bộ 8 hạng mục chữ màu đen rõ ràng, thanh lịch.
- Cột F (Đơn giá USD) & Cột J (Giá vốn USD) để trống cho Sếp tự điền.
- Hàng 22, 23, 24: Số tiền Tạm tính, Thuế VAT 8%, Tổng cộng chữ màu XANH DƯƠNG (#0000FF) bold.
- Hàng 25, 26: Khối chữ ký xác nhận khách hàng chữ màu NÂU VÀNG (#9C6500) bold.
- Hàng 27 (Điều khoản 2): Đoạn "交貨後保固一年" và "Bảo hành 1 năm..." chữ màu XANH DƯƠNG (#0000FF) bold.
- Hàng 28 (Điều khoản 3 - Thanh toán): Toàn bộ chữ màu ĐỎ RỰC (#FF0000) bold.
- Giữ nguyên màu nền theme gốc của workbook (Theme 6 tint 0.8 dịu mắt tự nhiên).
- Khóa chặt vùng in $A$1:$H$28 trên 1 trang A4 dọc duy nhất, scale 38%, không loang viền ngoài.
=============================================================================
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, Color
from openpyxl.cell.rich_text import TextBlock, CellRichText
from openpyxl.cell.text import InlineFont
from copy import copy
import math
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def compute_cell_lines(text, col_width_chars):
    if not text:
        return 1
    paragraphs = str(text).split('\n')
    total_rendered = 0
    usable_width = max(col_width_chars - 2.5, 5.0)
    for p in paragraphs:
        if not p.strip():
            total_rendered += 1
            continue
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

def copy_cell_style(src_cell, dst_cell):
    if src_cell.has_style:
        dst_cell.font = copy(src_cell.font)
        dst_cell.border = copy(src_cell.border)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.number_format = copy(src_cell.number_format)
        dst_cell.protection = copy(src_cell.protection)
        dst_cell.alignment = copy(src_cell.alignment)

def generate_pouhui_with_reference_format(template_path, output_path):
    wb = openpyxl.load_workbook(template_path, data_only=False)
    ws = wb['BHT']
    ws.title = 'PouHui'

    if 'BHT2' in wb.sheetnames:
        del wb['BHT2']

    # 1. Cập nhật thông tin Người mua (Pou Hui Vietnam)
    ws['F2'].value = "CÔNG TY TNHH VIỆT NAM PHỔ HUỆ Y TẾ CÔNG NGHỆ (POU HUI)"
    ws['F3'].value = "Ban Quản lý Dự án & Cơ điện 機電與專案部"
    ws['F4'].value = "(Liên hệ khách hàng)"
    ws['F5'].value = ""
    ws['F6'].value = "Lô D7/I, Đường số 1B, KCN Vĩnh Lộc, Phường Bình Hưng Hòa B, Q. Bình Tân, TP. Hồ Chí Minh"
    ws['F7'].value = "(Email khách hàng)"

    # 2. Cập nhật Tiêu đề Báo giá & Tỷ giá
    ws['A9'].value = "Báo giá hệ thống đo đếm điện năng 4 trạm biến áp 高壓變電站電能計量系統硬體報價訂購確認單"
    ws['A10'].value = "報價日期 Ngày báo giá: 21/10/2026"
    ws['A12'].value = "1) Giải pháp nâng cấp hệ thống đo đếm điện năng và giám sát 4 trạm biến áp cao thế 普惠醫工4座高壓變電站電能計量與能耗監控系統方案"
    ws['H12'].value = 26130

    # 3. Danh mục 8 Hạng mục: 6 Thiết bị + 1 Vật tư phụ (輔助材料) + 1 Chi phí thi công (施工費)
    items = [
        {
            "stt": 1,
            "name": "Đồng hồ đa năng PM210-4-V\nPM210-4-V 三相單迴路多功能需量總表",
            "category": "Đồng hồ đa năng\n多功能電表",
            "desc": "Đồng hồ đo đếm điện năng 3 pha đa chức năng PM210-4-V, đo công suất, điện áp, dòng điện, điện năng tiêu thụ (KWh/KVAh/KVARh), hỗ trợ kết nối trực tiếp biến dòng mềm Rogowski, giao tiếp Modbus RTU/RS485. 1 bộ / trạm biến áp (Trạm 1~Trạm 4).\nPM210-4-V三相單迴路多功能需量總表, 具備電力參數測量、電能計量功能, 直連羅氏線圈比流器, Modbus RTU/RS485通訊。每座變電站配置1台 (1號~4號高壓變電站)。",
            "qty": 4, "unit": "BỘ", "tax_rate": 0.0
        },
        {
            "stt": 2,
            "name": "Biến dòng mềm Rogowski CT-1000RV (1000A)\n三相羅氏比流器 CT-1000RV (1000A)",
            "category": "Biến dòng Rogowski\n羅氏比流器",
            "desc": "Biến dòng kiểu vòng mềm Rogowski coil CT-1000RV, dòng định mức 1000A, độ chính xác cao, lắp đặt kẹp mềm không cần cắt điện dừng máy nhà máy. Dùng cho Trạm 1, Trạm 2, Trạm 3 (máy biến áp 630KVA, cáp XLPE 325mm² x 2 sợi/pha).\nCT-1000RV三相羅氏比流器 (1000A), 柔性開口式線圈, 免停電快速施工安裝。適用於1號、2號、3號高壓變電站 (630KVA變壓器, XLPE 325mm²x2線徑)。",
            "qty": 3, "unit": "BỘ", "tax_rate": 0.20
        },
        {
            "stt": 3,
            "name": "Biến dòng mềm Rogowski CT-2000RV (2000A)\n三相羅氏比流器 CT-2000RV (2000A)",
            "category": "Biến dòng Rogowski\n羅氏比流器",
            "desc": "Biến dòng kiểu vòng mềm Rogowski coil CT-2000RV, dòng định mức 2000A (dải đo dòng sơ cấp 1200A), đường kính vòng lớn luồn qua bó 3 sợi cáp/pha, không cần cắt điện. Dùng cho Trạm 4 (máy biến áp 750KVA, cáp XLPE 250mm² x 3 sợi/pha).\nCT-2000RV三相羅氏比流器 (2000A), 大口徑柔性開口式線圈, 適用於單相3條電纜束線, 免停電快速安裝。適用於4號高壓變電站 (750KVA變壓器, XLPE 250mm²x3線徑)。",
            "qty": 1, "unit": "BỘ", "tax_rate": 0.20
        },
        {
            "stt": 4,
            "name": "Gateway thu thập dữ liệu CC2051\nCC2051 工業級資料收集閘道器",
            "category": "Gateway thu thập dữ liệu\n數據採集網關",
            "desc": "Bộ điều khiển/thu thập dữ liệu biên công nghiệp CC2051 (Edge Gateway), cổng RS-485 Modbus RTU thu thập tín hiệu từ 4 đồng hồ đo điện PM210-4-V của 4 trạm biến áp, chuyển đổi sang Modbus TCP / MQTT qua cổng mạng RJ45 Ethernet kết nối LAN Switch về EMS trung tâm.\nCC2051工業級邊緣計算與資料收集閘道器, 具備RS-485 Modbus RTU接口採集4座變電站PM210電表數據, 經由RJ45以太網轉換為Modbus TCP/MQTT協議, 經由LAN Switch即時上傳至中央能源管理系統 (EMS)。",
            "qty": 1, "unit": "BỘ", "tax_rate": 0.08
        },
        {
            "stt": 5,
            "name": "Bộ nguồn công nghiệp 24VDC (PW)\n工業級電源供應器 (PW)",
            "category": "Nguồn cấp công nghiệp\n電源供應器",
            "desc": "Bộ nguồn công nghiệp gắn Din-rail Meanwell/tương đương, điện áp vào dải rộng AC 85~265V, đầu ra DC 24V ổn định, chống sét lan truyền và quá tải, cấp nguồn liên tục cho Gateway CC2051 và đồng hồ PM210. 1 bộ / trạm biến áp.\n工業級導軌式開關電源供應器, 寬電壓輸入 AC 85~265V, 輸出 DC 24V 穩定電源, 具備過載與防雷保護, 為 PM210 電表及 CC2051 閘道器供電。每座變電站1台。",
            "qty": 4, "unit": "BỘ", "tax_rate": 0.08
        },
        {
            "stt": 6,
            "name": "Bộ chia mạng công nghiệp 5-Port\n工業級5埠乙太網交換機 (LAN SWITCH)",
            "category": "Thiết bị mạng\n網絡設備",
            "desc": "Switch mạng công nghiệp 5 cổng RJ45 10/100Mbps gắn thanh ray, vỏ kim loại chuẩn công nghiệp chống nhiễu điện từ, kết nối truyền dữ liệu từ các Gateway CC2051 về mạng nội bộ LAN nhà máy.\n工業級5埠 10/100Mbps 導軌式交換機, 金屬抗干擾外殼, 適用於工廠高壓變電站環境, 將 CC2051 網關連接至廠區局域網 (LAN)。",
            "qty": 1, "unit": "BỘ", "tax_rate": 0.08
        },
        {
            "stt": 7,
            "name": "Cáp mạng Cat6, cáp RS485 & Vật tư phụ\n網絡線 Cat.6、RS485通訊線及安裝輔材",
            "category": "Vật tư phụ\n輔助材料",
            "desc": "Bao gồm nội dung 內容包含:\n- Cáp mạng Cat6: 網絡線 Category 6 UTP Cable, 4-Pair\n- Cáp truyền thông chống nhiễu chuyên dụng RS485 (UL2464 24AWG 2P 隔離通訊線)\n- Ống luồn bảo vệ chống cháy, dây tiếp địa, cầu chì bảo vệ 阻燃保護套管、接地線、保險絲\n- Đầu cosse bọc cách điện, nhãn đánh dấu dây cáp và toàn bộ phụ kiện đấu nối 冷壓端子、電纜號碼管及全套配線輔材。",
            "qty": 1, "unit": "SET", "tax_rate": 0.08
        },
        {
            "stt": 8,
            "name": "Chi phí thi công\n施工費",
            "category": "Chi phí thi công\n施工費",
            "desc": "Bao gồm nội dung 內容包含:\n- Cài đặt hệ thống 系統設定\n- Lắp đặt phần cứng 4 trạm biến áp 4座高壓變電站硬體安裝\n- Hiệu chỉnh chức năng & liên động Modbus CC2051 功能調適與通訊聯調\n- Phí quản lý, vận chuyển 管理、運費\n- Thiết kế bản vẽ hoàn công 設計、竣工圖費用\n- Chi phí đi lại, giàn giáo, dụng cụ an toàn 交通費、鷹架、工安器具...",
            "qty": 1, "unit": "SET", "tax_rate": 0.08
        }
    ]

    col_widths = {
        'A': 5.33, 'B': 33.33, 'C': 30.44, 'D': 52.78,
        'E': 27.33, 'F': 24.55, 'G': 25.33, 'H': 39.22
    }
    for col_l, w in col_widths.items():
        ws.column_dimensions[col_l].width = w

    # 4. Hủy các vùng merge cũ từ dòng 20 trở đi để tái lập chuẩn xác cho 8 dòng
    for rng in list(ws.merged_cells.ranges):
        if rng.min_row >= 20:
            ws.unmerge_cells(str(rng))

    # 5. Ghi 8 dòng sản phẩm (Hàng 13 đến 20) - TOÀN BỘ CHỮ MÀU ĐEN CHUẨN MỰC
    font_black = Font(name="微軟正黑體", size=12.0, bold=False, color="000000")

    for idx, item in enumerate(items):
        r = 13 + idx
        lines_b = compute_cell_lines(item["name"], col_widths['B'])
        lines_c = compute_cell_lines(item["category"], col_widths['C'])
        lines_d = compute_cell_lines(item["desc"], col_widths['D'])
        max_lines = max(lines_b, lines_c, lines_d)
        ws.row_dimensions[r].height = max(75.0, max_lines * 19.5 + 16.0)

        for c_idx in range(1, 9):
            cell = ws.cell(r, c_idx)
            ref_cell = ws.cell(13, c_idx)
            copy_cell_style(ref_cell, cell)
            cell.font = font_black

        ws.cell(r, 1).value = item["stt"]
        ws.cell(r, 1).alignment = Alignment(horizontal="center", vertical="center")

        ws.cell(r, 2).value = item["name"]
        ws.cell(r, 2).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        ws.cell(r, 3).value = item["category"]
        ws.cell(r, 3).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        ws.cell(r, 4).value = item["desc"]
        ws.cell(r, 4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        ws.cell(r, 5).value = item["qty"]
        ws.cell(r, 5).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(r, 5).number_format = f'0" {item["unit"]} "'

        # Cột F: Để trống cho Sếp tự gõ giá bán
        ws.cell(r, 6).value = None
        ws.cell(r, 6).alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(r, 6).number_format = '"US$"#,##0.0_);\\("US$"#,##0.0\\)'

        # Cột G & H: Công thức sống
        ws.cell(r, 7).value = f"=F{r}*E{r}"
        ws.cell(r, 7).alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(r, 7).number_format = '"US$"#,##0.0_);\\("US$"#,##0.0\\)'

        ws.cell(r, 8).value = f"=G{r}*H12"
        ws.cell(r, 8).alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(r, 8).number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'

        # Cột J đến O: Bảng giá vốn nội bộ
        ws.cell(r, 10).value = None  # Để trống cho Sếp điền giá vốn xuất xưởng
        ws.cell(r, 11).value = item.get("tax_rate", 0.0)
        ws.cell(r, 12).value = f"=J{r}*K{r}"
        ws.cell(r, 13).value = f"=J{r}*0.07"
        ws.cell(r, 14).value = f"=J{r}+L{r}+M{r}"
        ws.cell(r, 15).value = f"=N{r}*E{r}"

    # 6. Hàng 以下空白 (Hàng 21)
    blank_row = 21
    ws.row_dimensions[blank_row].height = 18.0
    for col_idx in range(1, 9):
        c = ws.cell(blank_row, col_idx)
        c.font = Font(name="微軟正黑體", size=10.0, bold=False, color="000000")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = Border(
            top=Side(style='thin', color='000000'),
            bottom=Side(style='medium', color='000000'),
            left=Side(style='medium', color='000000') if col_idx == 1 else None,
            right=Side(style='medium', color='000000') if col_idx == 8 else None
        )
    ws.cell(blank_row, 1).value = "以下空白"
    ws.merge_cells(start_row=blank_row, start_column=1, end_row=blank_row, end_column=8)

    # 7. Khối Tổng Tiền: Tạm tính (22), Thuế VAT 8% (23), Tổng cộng (24)
    font_totals_label = Font(name="Microsoft YaHei", size=12.0, bold=True, color="000000")
    font_totals_blue = Font(name="Arial", size=13.0, bold=True, color="0000FF")
    theme_peach_fill = copy(ws.cell(21, 6).fill)  # Kế thừa fill theme 6 tint 0.8 gốc

    r_sub = 22
    ws.row_dimensions[r_sub].height = 38.0
    ws.cell(r_sub, 6).value = "Tạm tính 小計"
    ws.cell(r_sub, 6).fill = theme_peach_fill
    ws.cell(r_sub, 6).font = font_totals_label
    ws.cell(r_sub, 6).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(r_sub, 6).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    ws.cell(r_sub, 7).value = "=SUM(G13:G20)"
    ws.cell(r_sub, 7).font = font_totals_blue
    ws.cell(r_sub, 7).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(r_sub, 7).number_format = '"US$"#,##0.00_);\\("US$"#,##0.00\\)'
    ws.cell(r_sub, 7).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    ws.cell(r_sub, 8).value = f"=G{r_sub}*H12"
    ws.cell(r_sub, 8).font = font_totals_blue
    ws.cell(r_sub, 8).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(r_sub, 8).number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'
    ws.cell(r_sub, 8).border = Border(left=Side(style='thin'), right=Side(style='medium'), top=Side(style='thin'), bottom=Side(style='thin'))

    r_vat = 23
    ws.row_dimensions[r_vat].height = 38.0
    ws.cell(r_vat, 6).value = "Thuế VAT 8% 增值稅"
    ws.cell(r_vat, 6).fill = theme_peach_fill
    ws.cell(r_vat, 6).font = font_totals_label
    ws.cell(r_vat, 6).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(r_vat, 6).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    ws.cell(r_vat, 7).value = f"=G{r_sub}*0.08"
    ws.cell(r_vat, 7).font = font_totals_blue
    ws.cell(r_vat, 7).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(r_vat, 7).number_format = '"US$"#,##0.00_);\\("US$"#,##0.00\\)'
    ws.cell(r_vat, 7).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    ws.cell(r_vat, 8).value = f"=H{r_sub}*0.08"
    ws.cell(r_vat, 8).font = font_totals_blue
    ws.cell(r_vat, 8).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(r_vat, 8).number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'
    ws.cell(r_vat, 8).border = Border(left=Side(style='thin'), right=Side(style='medium'), top=Side(style='thin'), bottom=Side(style='thin'))

    r_tot = 24
    ws.row_dimensions[r_tot].height = 38.0
    ws.cell(r_tot, 6).value = "Tổng cộng 總金額"
    ws.cell(r_tot, 6).fill = theme_peach_fill
    ws.cell(r_tot, 6).font = font_totals_label
    ws.cell(r_tot, 6).alignment = Alignment(horizontal="center", vertical="center")
    ws.cell(r_tot, 6).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='medium'))

    ws.cell(r_tot, 7).value = f"=G{r_sub}*1.08"
    ws.cell(r_tot, 7).font = font_totals_blue
    ws.cell(r_tot, 7).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(r_tot, 7).number_format = '"US$"#,##0.00_);\\("US$"#,##0.00\\)'
    ws.cell(r_tot, 7).border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='medium'))

    ws.cell(r_tot, 8).value = f"=H{r_sub}*1.08"
    ws.cell(r_tot, 8).font = font_totals_blue
    ws.cell(r_tot, 8).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(r_tot, 8).number_format = '[$VND]\\ #,##0_);\\([$VND]\\ #,##0\\)'
    ws.cell(r_tot, 8).border = Border(left=Side(style='thin'), right=Side(style='medium'), top=Side(style='thin'), bottom=Side(style='medium'))

    # Merge vùng trống A22:E24 bên trái
    for r_m in range(r_sub, r_tot + 1):
        for c_m in range(1, 6):
            cell = ws.cell(r_m, c_m)
            cell.border = Border(
                left=Side(style='medium') if c_m == 1 else None,
                bottom=Side(style='medium') if r_m == r_tot else None
            )
    ws.merge_cells(start_row=r_sub, start_column=1, end_row=r_tot, end_column=5)

    # 8. Hàng 25: Tiêu đề Khách hàng (A25) & Ghi chú (D25)
    r_hdr = 25
    ws.row_dimensions[r_hdr].height = 24.0

    # A25:C25: ※客戶確認 Xác nhận khách hàng (MÀU NÂU VÀNG #9C6500 BOLD)
    for c_idx in range(1, 4):
        c = ws.cell(r_hdr, c_idx)
        c.fill = theme_peach_fill
        c.border = Border(
            left=Side(style='medium') if c_idx == 1 else None,
            right=Side(style='thin') if c_idx == 3 else None,
            top=Side(style='medium'), bottom=None
        )
    ws.cell(r_hdr, 1).value = "※客戶確認 Xác nhận khách hàng"
    ws.cell(r_hdr, 1).font = Font(name="Arial", size=12.0, bold=True, color="9C6500")
    ws.cell(r_hdr, 1).alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(start_row=r_hdr, start_column=1, end_row=r_hdr, end_column=3)

    # D25:H25: ◆ 備註聲明
    for c_idx in range(4, 9):
        c = ws.cell(r_hdr, c_idx)
        c.fill = theme_peach_fill
        c.border = Border(
            left=Side(style='thin') if c_idx == 4 else None,
            right=Side(style='medium') if c_idx == 8 else None,
            top=Side(style='medium'), bottom=None
        )
    ws.cell(r_hdr, 4).value = "◆ 備註聲明"
    ws.cell(r_hdr, 4).font = Font(name="Microsoft YaHei", size=11.0, bold=True, color="000000")
    ws.cell(r_hdr, 4).alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(start_row=r_hdr, start_column=4, end_row=r_hdr, end_column=8)

    # 9. Hàng 26, 27, 28: Khối Chữ ký (A26:C28) & 3 Điều khoản (D26:H28)
    r_n1 = 26
    r_n2 = 27
    r_n3 = 28

    ws.row_dimensions[r_n1].height = 54.0
    ws.row_dimensions[r_n2].height = 54.0
    ws.row_dimensions[r_n3].height = 58.0

    # Khối chữ ký A26:C28 (MÀU NÂU VÀNG #9C6500 BOLD)
    for r_curr in [r_n1, r_n2, r_n3]:
        is_last = (r_curr == r_n3)
        for c_idx in range(1, 4):
            c = ws.cell(r_curr, c_idx)
            c.fill = theme_peach_fill
            c.border = Border(
                left=Side(style='medium') if c_idx == 1 else None,
                right=Side(style='thin') if c_idx == 3 else None,
                bottom=Side(style='medium') if is_last else None
            )
        for c_idx in range(4, 9):
            c = ws.cell(r_curr, c_idx)
            c.fill = theme_peach_fill
            c.border = Border(
                left=Side(style='thin') if c_idx == 4 else None,
                right=Side(style='medium') if c_idx == 8 else None,
                bottom=Side(style='medium') if is_last else None
            )

    ws.cell(r_n1, 1).value = "（請簽名用印） Chữ ký và con dấu"
    ws.cell(r_n1, 1).font = Font(name="Arial", size=11.0, bold=True, color="9C6500")
    ws.cell(r_n1, 1).alignment = Alignment(horizontal="left", vertical="top")
    ws.merge_cells(start_row=r_n1, start_column=1, end_row=r_n3, end_column=3)

    # Điều khoản 1 (D26:H26)
    ws.cell(r_n1, 4).value = "1. 以上報價交期：報價單簽回後，另日程安排後回覆；\n   Thời gian giao hàng của báo giá trên: sau khi báo giá được ký và gửi lại, lịch trình cụ thể sẽ được thông báo sau;"
    ws.cell(r_n1, 4).font = Font(name="Microsoft YaHei", size=10.5, bold=True, color="000000")
    ws.cell(r_n1, 4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=r_n1, start_column=4, end_row=r_n1, end_column=8)

    # Điều khoản 2 (D27:H27 - RICH TEXT CHUẨN MẪU GỐC VỚI ĐOẠN XANH DƯƠNG #0000FF)
    rt_d27 = CellRichText(
        TextBlock(InlineFont(b=True, sz=11, rFont='Microsoft YaHei', color=Color(theme=1)), "2. 報價有效期限：2026/11/21 止，報價簽回視同專案確認，不可任意終止、取消本專案；"),
        TextBlock(InlineFont(b=True, sz=11, rFont='Microsoft YaHei', color=Color(rgb="FF0000FF")), "交貨後保固一年"),
        TextBlock(InlineFont(b=True, sz=11, rFont='Microsoft YaHei', color=Color(theme=1)), "\n    Thời hạn hiệu lực của báo giá: đến hết ngày 21/11/2026. Việc ký và gửi lại báo giá được xem là xác nhận dự án, \n    không được phép đơn phương chấm dứt hoặc hủy bỏ dự án này; "),
        TextBlock(InlineFont(b=True, sz=11, rFont='Microsoft YaHei', color=Color(rgb="FF0000FF")), "Bảo hành 1 năm kể từ ngày giao hàng.")
    )
    ws.cell(r_n2, 4).value = rt_d27
    ws.cell(r_n2, 4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=r_n2, start_column=4, end_row=r_n2, end_column=8)

    # Điều khoản 3 (D28:H28 - TOÀN BỘ CHỮ MÀU ĐỎ RỰC #FF0000 BOLD)
    ws.cell(r_n3, 4).value = "3. 付款方式 : 訂金 35%、 交貨 55%、驗收 10% TT30Day。\n     Điều khoản thanh toán:  [Đặt cọc: 35%, Khi giao hàng: 55%, Sau khi nghiệm thu: Thanh toán 10% còn lại theo điều khoản TT 30 ngày (TT30 Days).]"
    ws.cell(r_n3, 4).font = Font(name="Microsoft YaHei", size=10.5, bold=True, color="FF0000")
    ws.cell(r_n3, 4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=r_n3, start_column=4, end_row=r_n3, end_column=8)

    # 10. Bảng giá vốn nội bộ (Cột N & O)
    ws.cell(r_sub, 14).value = "合計成本"
    ws.cell(r_sub, 15).value = "=SUM(O13:O20)"

    ws.cell(r_vat, 14).value = "利潤"
    ws.cell(r_vat, 15).value = f"=G{r_sub}-O{r_sub}"

    ws.cell(r_tot, 14).value = "% 利潤"
    ws.cell(r_tot, 15).value = f"=O{r_vat}/G{r_sub}"
    ws.cell(r_tot, 15).number_format = "0.0%"

    # Dọn dẹp các cột ngoài P~R
    for r_c in range(13, 30):
        for c_c in range(16, 20):
            ws.cell(r_c, c_c).value = None

    # Khóa chặt vùng in 28 dòng trên 1 trang A4 duy nhất
    ws.print_area = f"$A$1:$H${r_n3}"
    ws.views.sheetView[0].view = "pageBreakPreview"
    ws.views.sheetView[0].zoomScale = 60
    ws.views.sheetView[0].showGridLines = None

    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = 9
    ws.page_setup.scale = 38
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    try:
        wb.save(output_path)
        print(f"[OK] Đã lưu thành công: {output_path}")
    except PermissionError:
        alt = output_path.replace(".xlsx", "_v2.xlsx")
        wb.save(alt)
        print(f"[THÔNG BÁO] File đang mở, đã lưu dự phòng tại: {alt}")

if __name__ == "__main__":
    tmpl = r"E:\Working\Bieu Mau\ECO PRIME_Báo Giá Đồng Hồ Điện_Mẫu Gốc.xlsx"
    out1 = r"E:\Working\ChuaHieu\ECO PRIME_Báo Giá Đồng Hồ Điện & CC2051_Pou Hui_20261021.xlsx"
    out2 = r"E:\Working\ECO PRIME_Báo Giá Đồng Hồ Điện & CC2051_Pou Hui_20261021.xlsx"

    print("Đang tạo file Báo giá Pou Hui chuẩn tham khảo...")
    generate_pouhui_with_reference_format(tmpl, out1)
    generate_pouhui_with_reference_format(tmpl, out2)
