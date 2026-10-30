# -*- coding: utf-8 -*-
"""
Tạo file Master Excel Quản lý Dự án & Công nợ cho Hong Ming Global.
File: e:/Working/DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Locate the project independently of the drive letter on this computer.
_WORKSPACE_ROOT = next((p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'pm_portal' / 'app').is_dir()), __import__('pathlib').Path.cwd())
def _workspace_path(relative):
    return str(_WORKSPACE_ROOT / relative.replace(chr(92), '/'))

wb = openpyxl.Workbook()

# Setup styles
header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")

section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
section_font = Font(name="Segoe UI", size=10, bold=True, color="1F4E79")

data_font = Font(name="Segoe UI", size=10)
bold_font = Font(name="Segoe UI", size=10, bold=True)
alert_font = Font(name="Segoe UI", size=10, bold=True, color="C00000")
ok_font = Font(name="Segoe UI", size=10, bold=True, color="375623")

thin_border = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

# ----------------------------------------------------
# SHEET 1: TỔNG QUAN DỰ ÁN (PROJECT MASTER)
# ----------------------------------------------------
ws1 = wb.active
ws1.title = "Tổng Quan Dự Án 專案總覽"
ws1.views.sheetView[0].showGridLines = True

# Title block
ws1.merge_cells("A1:K1")
ws1["A1"] = "BẢNG THEO DÕI TỔNG QUAN CÁC DỰ ÁN - CÔNG TY TNHH TOÀN CẦU HONG MING (宏明環球有限公司)"
ws1["A1"].font = Font(name="Segoe UI", size=14, bold=True, color="1F4E79")
ws1["A1"].alignment = Alignment(vertical="center")

headers1 = [
    "Mã Dự Án / HĐ\n專案／合約編號",
    "Khách Hàng\n客戶名稱",
    "Tên Dự Án / Hạng Mục\n專案名稱／項目",
    "Kỹ Thuật Phụ Trách\n技術負責人",
    "Ngày Ký HĐ\n簽約日期",
    "Tổng Giá Trị (VND)\n合約總金額",
    "Đã Thu (VND)\n已收金額",
    "Còn Lại (VND)\n未收餘額",
    "Tỷ Lệ Thu\n收款進度",
    "Trạng Thái Dự Án\n專案進度狀態",
    "Ghi Chú & Hành Động Kế Tiếp\n備註及後續工作"
]

for col_num, h in enumerate(headers1, 1):
    cell = ws1.cell(row=3, column=col_num, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Sample projects data from actual files
projects_data = [
    (
        "HMV151020250001",
        "CX Technology (VN)",
        "Dự án RFID Hardware & Custom Software ERP",
        "Jenson Chang (張永吉)",
        "09/12/2025",
        234000000,
        93600000,  # 40% sign deposit paid
        "=F4-G4",
        "=G4/F4",
        "Đang nghiệm thu đưa vào sử dụng (Đợt 2 - 40%)",
        "Đã ký BB nghiệm thu 10/2026, xuất hóa đơn thu 93.600.000 đ"
    ),
    (
        "HMV220920260001",
        "CX Technology (VN)",
        "Cung cấp 500 thẻ RFID Silicon OPP9018",
        "Jenson Chang (張永吉)",
        "22/09/2026",
        19500000,
        9750000,   # 50% deposit paid
        "=F5-G5",
        "=G5/F5",
        "Đang đặt hàng NCC nước ngoài (Lead time 60 ngày)",
        "Chờ hàng về kho kiểm tra giao nhà máy CX"
    ),
    (
        "HMV021020260001",
        "Cheng Feng Le Hua (VN)",
        "Hạ tầng mạng kết nối máy móc toàn xưởng (IoT 1 Tỷ)",
        "Jenson Chang (張永吉)",
        "02/10/2026",
        1000000000,
        300000000,  # 30% advance deposit paid
        "=F6-G6",
        "=G6/F6",
        "Đang chuẩn bị vật tư thi công kéo cáp quang",
        "Đã nhận cọc 30%, tiến hành kéo cáp hoàn thành trước hạn 80 ngày"
    ),
    (
        "HM-QT-202603-V1.5",
        "Vonmax (VN) 弘聲",
        "Dự án IoT SMB Giai đoạn 2 & Hệ thống Tiết kiệm Điện EMS",
        "Jenson Chang (張永吉)",
        "Chờ ký HĐ",
        450000000,
        0,
        "=F7-G7",
        "=G7/F7",
        "Đang chốt báo giá V1.5 và đàm phán hợp đồng",
        "Gửi dự thảo HĐ và xin lịch gặp sếp Hoàng & Quản đốc"
    ),
]

for row_idx, p in enumerate(projects_data, 4):
    for col_idx, val in enumerate(p, 1):
        c = ws1.cell(row=row_idx, column=col_idx, value=val)
        c.font = data_font
        c.border = thin_border
        if col_idx in [6, 7, 8]:
            c.number_format = "#,##0"
            c.alignment = Alignment(horizontal="right", vertical="center")
        elif col_idx == 9:
            c.number_format = "0.0%"
            c.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx in [1, 5]:
            c.alignment = Alignment(horizontal="center", vertical="center")
        else:
            c.alignment = Alignment(horizontal="left", vertical="center")

# Total row
total_row = len(projects_data) + 4
ws1.cell(row=total_row, column=3, value="TỔNG CỘNG / 合計").font = bold_font
ws1.cell(row=total_row, column=3).alignment = Alignment(horizontal="right")
ws1.cell(row=total_row, column=6, value=f"=SUM(F4:F{total_row-1})").font = bold_font
ws1.cell(row=total_row, column=6).number_format = "#,##0"
ws1.cell(row=total_row, column=7, value=f"=SUM(G4:G{total_row-1})").font = bold_font
ws1.cell(row=total_row, column=7).number_format = "#,##0"
ws1.cell(row=total_row, column=8, value=f"=SUM(H4:H{total_row-1})").font = bold_font
ws1.cell(row=total_row, column=8).number_format = "#,##0"
ws1.cell(row=total_row, column=9, value=f"=G{total_row}/F{total_row}").font = bold_font
ws1.cell(row=total_row, column=9).number_format = "0.0%"
ws1.cell(row=total_row, column=9).alignment = Alignment(horizontal="center")

for c_idx in range(1, 12):
    ws1.cell(row=total_row, column=c_idx).border = thin_border
    ws1.cell(row=total_row, column=c_idx).fill = section_fill

# ----------------------------------------------------
# SHEET 2: THEO DÕI CÁC ĐỢT THANH TOÁN (PAYMENT MILESTONES)
# ----------------------------------------------------
ws2 = wb.create_sheet(title="Đợt Thanh Toán 款項明細")
ws2.views.sheetView[0].showGridLines = True

ws2.merge_cells("A1:J1")
ws2["A1"] = "CHI TIẾT TIẾN ĐỘ THANH TOÁN & ĐÔN ĐỐC CÔNG NỢ THEO TỪNG GIAI ĐOẠN"
ws2["A1"].font = Font(name="Segoe UI", size=14, bold=True, color="1F4E79")

headers2 = [
    "Mã Hợp Đồng",
    "Khách Hàng",
    "Đợt TT",
    "Tỷ Lệ (%)",
    "Số Tiền (VND)",
    "Điều Kiện Kích Hoạt",
    "Hạn Thanh Toán (Due Date)",
    "Số Hóa Đơn VAT",
    "Tình Trạng",
    "Hành Động Nhắc Nợ"
]

for col_num, h in enumerate(headers2, 1):
    cell = ws2.cell(row=3, column=col_num, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center")

milestones_data = [
    ("HMV151020250001", "CX Technology", "Đợt 1", "40%", 93600000, "Ký hợp đồng", "15/12/2025", "HD-00124", "ĐÃ THU ĐỦ", "Hoàn thành"),
    ("HMV151020250001", "CX Technology", "Đợt 2", "40%", 93600000, "Bàn giao đưa vào sử dụng", "25/10/2026", "HD-00189", "CHỜ THANH TOÁN", "Gửi BB nghiệm thu + Đề nghị thanh toán"),
    ("HMV151020250001", "CX Technology", "Đợt 3", "20%", 46800000, "Nghiệm thu tiêu chuẩn cuối", "15/12/2026", "Chưa xuất", "CHƯA ĐẾN HẠN", "Chờ chạy thử đạt tiêu chuẩn"),
    
    ("HMV220920260001", "CX Technology", "Đợt 1", "50%", 9750000, "Ký hợp đồng / Đặt hàng", "25/09/2026", "HD-00170", "ĐÃ THU ĐỦ", "Hoàn thành"),
    ("HMV220920260001", "CX Technology", "Đợt 2", "50%", 9750000, "Giao đủ 500 thẻ trong 14 ngày", "30/11/2026", "Chưa xuất", "CHƯA ĐẾN HẠN", "Giao hàng xong phát hành hồ sơ"),
    
    ("HMV021020260001", "Cheng Feng Le Hua", "Đợt 1", "30%", 300000000, "Tạm ứng ký hợp đồng", "05/10/2026", "HD-00180", "ĐÃ THU ĐỦ", "Hoàn thành"),
    ("HMV021020260001", "Cheng Feng Le Hua", "Đợt 2", "30%", 300000000, "Hoàn thành kéo cáp (T/T 30d)", "15/11/2026", "Chưa xuất", "ĐANG THI CÔNG", "Giám sát nghiệm thu kéo cáp"),
    ("HMV021020260001", "Cheng Feng Le Hua", "Đợt 3", "30%", 300000000, "Lắp đặt thiết bị Server (T/T 60d)", "20/12/2026", "Chưa xuất", "CHƯA ĐẾN HẠN", "Chuẩn bị Server Dell & Switch"),
    ("HMV021020260001", "Cheng Feng Le Hua", "Đợt 4", "10%", 100000000, "Nghiệm thu cuối FAC (T/T 60d)", "20/02/2027", "Chưa xuất", "CHƯA ĐẾN HẠN", "Bàn giao hoàn công & HDSD"),
]

for row_idx, m in enumerate(milestones_data, 4):
    for col_idx, val in enumerate(m, 1):
        c = ws2.cell(row=row_idx, column=col_idx, value=val)
        c.font = data_font
        c.border = thin_border
        if col_idx == 5:
            c.number_format = "#,##0"
            c.alignment = Alignment(horizontal="right", vertical="center")
        elif col_idx in [3, 4, 7, 8]:
            c.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx == 9:
            c.alignment = Alignment(horizontal="center", vertical="center")
            if val == "ĐÃ THU ĐỦ":
                c.font = ok_font
            elif val in ["CHỜ THANH TOÁN", "QUÁ HẠN"]:
                c.font = alert_font
            else:
                c.font = data_font

# ----------------------------------------------------
# SHEET 3: QUẢN LÝ MUA HÀNG & NCC (PROCUREMENT)
# ----------------------------------------------------
ws3 = wb.create_sheet(title="Mua Hàng NCC 採購管理")
ws3.views.sheetView[0].showGridLines = True

ws3.merge_cells("A1:I1")
ws3["A1"] = "DANH SÁCH ĐƠN HÀNG MUA VẬT TƯ & THEO DÕI NHÀ CUNG CẤP (PO TRACKING)"
ws3["A1"].font = Font(name="Segoe UI", size=14, bold=True, color="1F4E79")

headers3 = [
    "Số PO / 採購單號",
    "Nhà Cung Cấp / 廠商",
    "Tên Thiết Bị / Vật Tư",
    "SL",
    "Dự Án Sử Dụng",
    "Ngày Đặt Hàng",
    "Hạn Giao Hàng",
    "Tình Trạng Hàng Hóa",
    "Chứng Từ Kèm Theo (CO/CQ/HĐ)"
]

for col_num, h in enumerate(headers3, 1):
    cell = ws3.cell(row=3, column=col_num, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center")

po_data = [
    ("HM-PO-202610-01", "Đại lý Dell Việt Nam", "Dell PowerEdge R760xs Server + WinServer + SQL", 1, "Cheng Feng Bắc Ninh", "06/10/2026", "20/10/2026", "Chờ hãng xuất kho", "CO/CQ chính hãng Dell"),
    ("HM-PO-202610-02", "Nhà máy Thẻ RFID (TW)", "Thẻ RFID Silicon OPP9018 (500 pcs)", 500, "CX Technology", "26/09/2026", "10/11/2026", "Đang vận chuyển quốc tế", "Invoice, PL, Tờ khai HQ"),
    ("HM-PO-202610-03", "Phân phối Cáp Mạng & Quang", "Switch TP-Link, Module quang 1G, cáp Cat6", 1, "Cheng Feng Bắc Ninh", "05/10/2026", "10/10/2026", "Đã nhận kho đủ", "Hóa đơn VAT, Phiếu xuất kho"),
    ("HM-PO-202610-04", "Điện máy Bắc Ninh", "Smart TV TCL 65 Inch + Giá treo", 1, "Cheng Feng Bắc Ninh", "10/10/2026", "15/10/2026", "Sẵn sàng giao công trình", "Hóa đơn VAT bảo hành"),
]

for row_idx, po in enumerate(po_data, 4):
    for col_idx, val in enumerate(po, 1):
        c = ws3.cell(row=row_idx, column=col_idx, value=val)
        c.font = data_font
        c.border = thin_border
        if col_idx == 4:
            c.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx in [1, 6, 7]:
            c.alignment = Alignment(horizontal="center", vertical="center")

# Auto-adjust column widths for all sheets
for sheet in [ws1, ws2, ws3]:
    for col in sheet.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # skip merged title in row 1
            if cell.row == 1:
                continue
            val_str = str(cell.value or "")
            lines = val_str.split("\n")
            for l in lines:
                if len(l) > max_len:
                    max_len = len(l)
        sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

# Specific column adjustments
ws1.column_dimensions['A'].width = 18
ws1.column_dimensions['B'].width = 24
ws1.column_dimensions['C'].width = 38
ws1.column_dimensions['D'].width = 22
ws1.column_dimensions['F'].width = 18
ws1.column_dimensions['G'].width = 18
ws1.column_dimensions['H'].width = 18
ws1.column_dimensions['J'].width = 30
ws1.column_dimensions['K'].width = 40

ws2.column_dimensions['B'].width = 24
ws2.column_dimensions['E'].width = 18
ws2.column_dimensions['F'].width = 32
ws2.column_dimensions['G'].width = 16
ws2.column_dimensions['J'].width = 36

ws3.column_dimensions['B'].width = 25
ws3.column_dimensions['C'].width = 38
ws3.column_dimensions['E'].width = 22

output_file = _workspace_path('DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx')
wb.save(output_file)
print("Master Project Tracker Excel created successfully at: " + output_file)
