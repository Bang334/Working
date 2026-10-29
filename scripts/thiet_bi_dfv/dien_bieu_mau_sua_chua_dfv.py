# -*- coding: utf-8 -*-
"""
Script điền danh sách 19 thiết bị từ file Tham_Khao_Danh_Sach_Thiet_Bi_Sua_Chua_DFV_Darfon.xlsx
vào mẫu phiếu gửi sửa chữa 'Copy of danh sach sua lot 3 (1).xlsx'.
Giữ nguyên 100% thông tin người bán, người mua, logo và phần tiêu đề/chân trang.
Đơn giá để trống cho Sếp tự điền, có sẵn công thức sống tính tổng.
"""

import os
import sys
from copy import copy
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

SRC_TEMPLATE = r"C:\Users\BANG\Downloads\Copy of danh sach sua lot 3 (1)_backup.xlsx"
DEST_DOWNLOADS = r"C:\Users\BANG\Downloads\Copy of danh sach sua lot 3 (1).xlsx"
DEST_WORKING = r"E:\Working\Ho So Du An\Cong Ty\DFV_Darfon\Thiet Bi\Phieu_Gui_Sua_Chua_DFV_Darfon.xlsx"

ITEMS_19 = [
    # 3 Máy tính bảng HT10
    {
        "stt": 1,
        "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
        "category": "Phần cứng thân máy\n平板主機",
        "detail": "Model: HT10 | S/N: C3Z03GQ301274 | P/N: 7400100004288M\nHiện trạng: Lỗi mất mạng (断网), thân máy không có pin",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 2,
        "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
        "category": "Phần cứng thân máy\n平板主機",
        "detail": "Model: HT10 | S/N: C3Z03GQ301292 | P/N: 7400100004288M\nHiện trạng: Lỗi mất mạng (断网), thân máy không có pin",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 3,
        "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
        "category": "Phần cứng thân máy\n平板主機",
        "detail": "Model: HT10 | S/N: C3Z03GQ301338 | P/N: 7400100004288M\nHiện trạng: Lỗi mất mạng (断网), thân máy không có pin",
        "dept": "DFV",
        "qty": 1
    },
    # 4 Đế sạc đơn HT10 Cradle S
    {
        "stt": 4,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705592 (1#)\nHiện trạng: Đánh dấu NG, lỗi mất mạng khi kết nối dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 5,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705625 (2#)\nHiện trạng: Đánh dấu NG, lỗi mất mạng khi kết nối dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 6,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705566 (6#)\nHiện trạng: Đánh dấu NG, lỗi mất mạng khi kết nối dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 7,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705615 (7#)\nHiện trạng: Đánh dấu NG, lỗi mất mạng khi kết nối dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    # 4 Bộ nguồn Adapter 12V 2A
    {
        "stt": 8,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520558\nĐi kèm dock sạc 1# | Hiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 9,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520560\nĐi kèm dock sạc 2# | Hiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 10,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520575\nĐi kèm dock sạc 6# | Hiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 11,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520595\nĐi kèm dock sạc 7# | Hiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    # 8 Pin Lithium-ion máy tính bảng
    {
        "stt": 12,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000251 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 13,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000613 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 14,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309001047 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 15,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000337 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 16,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309001215 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 17,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000561 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 18,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309001198 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 19,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2305001525 | P/N: 1ICP6/45/116-2\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    }
]

def fill_workbook():
    wb = openpyxl.load_workbook(SRC_TEMPLATE)
    ws = wb.active
    ws.title = "Chi Tiết 19 Thiết Bị"
    
    # Giữ nguyên 100% dòng 1 đến 10 (Người bán, người mua, tiêu đề, ngày tháng)
    
    # Hủy gộp các ô từ dòng 12 trở xuống của mẫu cũ
    for rng in list(ws.merged_cells.ranges):
        min_c, min_r, max_c, max_r = rng.bounds
        if min_r >= 12:
            ws.unmerge_cells(start_row=min_r, start_column=min_c, end_row=max_r, end_column=max_c)
            
    # Xóa sạch các giá trị cũ từ dòng 12 đến dòng 45 để không bị sót chữ cũ
    for r in range(12, 45):
        for c in range(1, 10):
            ws.cell(r, c).value = None
            
    # Lấy kiểu dáng mẫu từ ô A12 của template
    sample_font = copy(ws.cell(12, 1).font)
    sample_font.name = "微軟正黑體"
    sample_font.size = 12
    font_bold = copy(sample_font)
    font_bold.bold = True
    
    bd_thin = Side(border_style="thin", color="000000")
    border_cell = Border(left=bd_thin, right=bd_thin, top=bd_thin, bottom=bd_thin)
    
    fill_zebra_1 = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra_2 = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    fill_qty = PatternFill(start_color="EAECEE", end_color="EAECEE", fill_type="solid")
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center", wrap_text=True)
    
    fmt_qty = '0" CÁI"'
    fmt_curr = '[$VND] #,##0;[Red][$VND] #,##0'
    
    # -------------------------------------------------------------
    # Đổ 19 thiết bị từ dòng 12 đến dòng 30
    # -------------------------------------------------------------
    start_row = 12
    for i, item in enumerate(ITEMS_19):
        row = start_row + i
        ws.row_dimensions[row].height = 42
        fill_row = fill_zebra_2 if (i % 2 == 1) else fill_zebra_1
        
        # Col A: STT
        cA = ws.cell(row=row, column=1, value=item["stt"])
        cA.alignment = align_center
        cA.font = font_bold
        cA.fill = fill_row
        cA.border = border_cell
        
        # Col B: Tên sản phẩm
        cB = ws.cell(row=row, column=2, value=item["name"])
        cB.alignment = align_left
        cB.font = font_bold
        cB.fill = fill_row
        cB.border = border_cell
        
        # Col C: Hạng mục
        cC = ws.cell(row=row, column=3, value=item["category"])
        cC.alignment = align_center
        cC.font = sample_font
        cC.fill = fill_row
        cC.border = border_cell
        
        # Col D: Nội dung sản phẩm
        cD = ws.cell(row=row, column=4, value=item["detail"])
        cD.alignment = align_left
        cD.font = sample_font
        cD.fill = fill_row
        cD.border = border_cell
        
        # Col E: Bộ phận gửi sửa
        cE = ws.cell(row=row, column=5, value=item["dept"])
        cE.alignment = align_center
        cE.font = sample_font
        cE.fill = fill_row
        cE.border = border_cell
        
        # Col F: Số lượng
        cF = ws.cell(row=row, column=6, value=item["qty"])
        cF.alignment = align_center
        cF.font = font_bold
        cF.fill = fill_row
        cF.border = border_cell
        cF.number_format = fmt_qty
        
        # Col G: Thời gian hoàn thành
        cG = ws.cell(row=row, column=7, value=None)
        cG.alignment = align_center
        cG.font = sample_font
        cG.fill = fill_row
        cG.border = border_cell
        
        # Col H: Đơn giá (để trống cho Sếp tự điền)
        cH = ws.cell(row=row, column=8, value=None)
        cH.alignment = align_right
        cH.font = font_bold
        cH.fill = fill_row
        cH.border = border_cell
        cH.number_format = fmt_curr
        
        # Col I: Tổng giá (công thức = F*H nếu H có giá)
        cI = ws.cell(row=row, column=9, value=f'=IF(H{row}<>"", F{row}*H{row}, "")')
        cI.alignment = align_right
        cI.font = font_bold
        cI.fill = fill_row
        cI.border = border_cell
        cI.number_format = fmt_curr

    end_data_row = start_row + len(ITEMS_19) - 1 # Row 30
    
    # Hàng "Chỗ trống sau đây" tại Row 31
    blank_row = end_data_row + 1 # Row 31
    ws.row_dimensions[blank_row].height = 24
    ws.merge_cells(f"A{blank_row}:I{blank_row}")
    c_blank = ws.cell(row=blank_row, column=1, value="以下空白 Chỗ trống sau đây")
    c_blank.alignment = align_center
    c_blank.font = Font(name="微軟正黑體", size=11, italic=True, color="555555")
    for col in range(1, 10):
        ws.cell(row=blank_row, column=col).border = border_cell
        
    # Hàng Tổng cộng tại Row 32 (giữ nguyên chữ 此致 Công ty cổ phần CX Technology (VN) y như mẫu gốc)
    sum_row = blank_row + 1 # Row 32
    ws.row_dimensions[sum_row].height = 36
    ws.merge_cells(f"A{sum_row}:E{sum_row}")
    c_to = ws.cell(
        row=sum_row, 
        column=1, 
        value="此致\n         Công ty cổ phần CX Technology (VN)"
    )
    c_to.alignment = align_left
    c_to.font = Font(name="微軟正黑體", size=12, bold=True)
    c_to.border = border_cell
    for col in range(2, 6):
        ws.cell(row=sum_row, column=col).border = border_cell
        
    # Tổng số lượng tại cột F
    c_sum_qty = ws.cell(row=sum_row, column=6, value=f"=SUM(F{start_row}:F{end_data_row})")
    c_sum_qty.alignment = align_center
    c_sum_qty.font = Font(name="微軟正黑體", size=14, bold=True)
    c_sum_qty.fill = fill_qty
    c_sum_qty.border = border_cell
    c_sum_qty.number_format = fmt_qty
    
    # Col G trống
    ws.cell(row=sum_row, column=7, value="").border = border_cell
    
    # Col H: TỔNG THÀNH TIỀN
    c_sum_lbl = ws.cell(row=sum_row, column=8, value="TỔNG THÀNH TIỀN \n總價")
    c_sum_lbl.alignment = align_center
    c_sum_lbl.font = Font(name="微軟正黑體", size=13, bold=True)
    c_sum_lbl.border = border_cell
    
    # Col I: Tổng thành tiền
    c_sum_val = ws.cell(row=sum_row, column=9, value=f"=SUM(I{start_row}:I{end_data_row})")
    c_sum_val.alignment = align_right
    c_sum_val.font = Font(name="微軟正黑體", size=13, bold=True)
    c_sum_val.border = border_cell
    c_sum_val.number_format = fmt_curr
    
    # Chữ ký xác nhận tại Row 33 & 34 (giữ nguyên y hệt mẫu gốc)
    sig_row_1 = sum_row + 1 # Row 33
    ws.row_dimensions[sig_row_1].height = 24
    ws.cell(row=sig_row_1, column=1, value="※客戶確認 Xác nhận khách hàng").font = Font(name="微軟正黑體", size=12, bold=True)
    
    sig_row_2 = sig_row_1 + 1 # Row 34
    ws.row_dimensions[sig_row_2].height = 24
    ws.cell(row=sig_row_2, column=1, value="(請簽名用印 Vui lòng ký tên và đóng dấu)").font = Font(name="微軟正黑體", size=11, italic=True)
    
    # -------------------------------------------------------------
    # SHEET 2: BẢNG GỘP 4 NHÓM CHỦNG LOẠI
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Bảng Gộp 4 Nhóm")
    
    # Copy nguyên vẹn 10 hàng đầu tiên sang Sheet 2
    for r in range(1, 11):
        ws2.row_dimensions[r].height = ws.row_dimensions[r].height
        for c in range(1, 10):
            c_src = ws.cell(r, c)
            if c_src.value is not None:
                c_dst = ws2.cell(r, c, c_src.value)
                if c_src.font: c_dst.font = copy(c_src.font)
                if c_src.alignment: c_dst.alignment = copy(c_src.alignment)
                if c_src.fill: c_dst.fill = copy(c_src.fill)
                if c_src.border: c_dst.border = copy(c_src.border)
                
    for rng in list(ws.merged_cells.ranges):
        min_c, min_r, max_c, max_r = rng.bounds
        if max_r <= 10:
            ws2.merge_cells(start_row=min_r, start_column=min_c, end_row=max_r, end_column=max_c)
            
    # Copy header cột
    ws2.row_dimensions[11].height = ws.row_dimensions[11].height
    for c in range(1, 10):
        c_src = ws.cell(11, c)
        c_dst = ws2.cell(11, c, c_src.value)
        if c_src.font: c_dst.font = copy(c_src.font)
        if c_src.fill: c_dst.fill = copy(c_src.fill)
        if c_src.alignment: c_dst.alignment = copy(c_src.alignment)
        if c_src.border: c_dst.border = copy(c_src.border)
        col_letter = get_column_letter(c)
        ws2.column_dimensions[col_letter].width = ws.column_dimensions[col_letter].width
        
    GROUP_ITEMS = [
        {
            "stt": 1,
            "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
            "category": "Phần cứng thân máy\n平板主機",
            "detail": "Model: HT10 | P/N: 7400100004288M | HS: 8471.30.20\n3 S/N: C3Z03GQ301274, C3Z03GQ301292, C3Z03GQ301338\nHiện trạng: Lỗi mất mạng (断网), thân máy không pin",
            "dept": "DFV",
            "qty": 3
        },
        {
            "stt": 2,
            "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
            "category": "Phụ kiện đế sạc\n充電底座",
            "detail": "Model: HT10 Cradle S | HS: 8504.40.19\n4 S/N: C3V01GQ705592 (1#), C3V01GQ705625 (2#), C3V01GQ705566 (6#), C3V01GQ705615 (7#)\nHiện trạng: Đánh dấu NG, lỗi mất mạng khi kết nối dock (断网)",
            "dept": "DFV",
            "qty": 4
        },
        {
            "stt": 3,
            "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
            "category": "Phụ kiện nguồn sạc\n電源配件",
            "detail": "Model: FY1202000 | In: 100-240V | Out: 12V 2A | HS: 8504.40.19\n4 S/N: 9056000619520558, 9056000619520560, 9056000619520575, 9056000619520595\nHiện trạng: Kèm 4 dock sạc 1#, 2#, 6#, 7# để kiểm tra đồng bộ",
            "dept": "DFV",
            "qty": 4
        },
        {
            "stt": 4,
            "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
            "category": "Linh kiện pin sạc\n專用鋰電池",
            "detail": "Model: CLP629 (10000mAh) | P/N: 1ICP6/45/116-2 | HS: 8507.60.90\n8 S/N: C629B2309000251, C629B2309000613, C629B2309001047, C629B2309000337,\nC629B2309001215, C629B2309000561, C629B2309001198, C629B2305001525\nHiện trạng: 8 viên pin đều bị phồng (电池鼓包), đề nghị cấp mới",
            "dept": "DFV",
            "qty": 8
        }
    ]
    
    for i, g in enumerate(GROUP_ITEMS):
        r = 12 + i
        ws2.row_dimensions[r].height = 55
        fill_row = fill_zebra_2 if (i % 2 == 1) else fill_zebra_1
        
        cA = ws2.cell(row=r, column=1, value=g["stt"])
        cA.alignment = align_center
        cA.font = font_bold
        cA.fill = fill_row
        cA.border = border_cell
        
        cB = ws2.cell(row=r, column=2, value=g["name"])
        cB.alignment = align_left
        cB.font = font_bold
        cB.fill = fill_row
        cB.border = border_cell
        
        cC = ws2.cell(row=r, column=3, value=g["category"])
        cC.alignment = align_center
        cC.font = sample_font
        cC.fill = fill_row
        cC.border = border_cell
        
        cD = ws2.cell(row=r, column=4, value=g["detail"])
        cD.alignment = align_left
        cD.font = sample_font
        cD.fill = fill_row
        cD.border = border_cell
        
        cE = ws2.cell(row=r, column=5, value=g["dept"])
        cE.alignment = align_center
        cE.font = sample_font
        cE.fill = fill_row
        cE.border = border_cell
        
        cF = ws2.cell(row=r, column=6, value=g["qty"])
        cF.alignment = align_center
        cF.font = font_bold
        cF.fill = fill_row
        cF.border = border_cell
        cF.number_format = fmt_qty
        
        cG = ws2.cell(row=r, column=7, value=None)
        cG.border = border_cell
        
        cH = ws2.cell(row=r, column=8, value=None)
        cH.alignment = align_right
        cH.font = font_bold
        cH.fill = fill_row
        cH.border = border_cell
        cH.number_format = fmt_curr
        
        cI = ws2.cell(row=r, column=9, value=f'=IF(H{r}<>"", F{r}*H{r}, "")')
        cI.alignment = align_right
        cI.font = font_bold
        cI.fill = fill_row
        cI.border = border_cell
        cI.number_format = fmt_curr

    # Hàng chỗ trống
    ws2.row_dimensions[16].height = 24
    ws2.merge_cells("A16:I16")
    ws2["A16"] = "以下空白 Chỗ trống sau đây"
    ws2["A16"].alignment = align_center
    ws2["A16"].font = Font(name="微軟正黑體", size=11, italic=True, color="555555")
    for col in range(1, 10):
        ws2.cell(row=16, column=col).border = border_cell
        
    # Hàng tổng cộng
    ws2.row_dimensions[17].height = 36
    ws2.merge_cells("A17:E17")
    ws2["A17"] = "此致\n         Công ty cổ phần CX Technology (VN)"
    ws2["A17"].alignment = align_left
    ws2["A17"].font = Font(name="微軟正黑體", size=12, bold=True)
    for col in range(1, 6):
        ws2.cell(row=17, column=col).border = border_cell
        
    ws2["F17"] = "=SUM(F12:F15)"
    ws2["F17"].alignment = align_center
    ws2["F17"].font = Font(name="微軟正黑體", size=14, bold=True)
    ws2["F17"].fill = fill_qty
    ws2["F17"].border = border_cell
    ws2["F17"].number_format = fmt_qty
    
    ws2["G17"] = ""
    ws2["G17"].border = border_cell
    
    ws2["H17"] = "TỔNG THÀNH TIỀN \n總價"
    ws2["H17"].alignment = align_center
    ws2["H17"].font = Font(name="微軟正黑體", size=13, bold=True)
    ws2["H17"].border = border_cell
    
    ws2["I17"] = "=SUM(I12:I15)"
    ws2["I17"].alignment = align_right
    ws2["I17"].font = Font(name="微軟正黑體", size=13, bold=True)
    ws2["I17"].border = border_cell
    ws2["I17"].number_format = fmt_curr
    
    ws2.row_dimensions[18].height = 24
    ws2["A18"] = "※客戶確認 Xác nhận khách hàng"
    ws2["A18"].font = Font(name="微軟正黑體", size=12, bold=True)
    
    ws2.row_dimensions[19].height = 24
    ws2["A19"] = "(請簽名用印 Vui lòng ký tên và đóng dấu)"
    ws2["A19"].font = Font(name="微軟正黑體", size=11, italic=True)

    # Lưu workbook
    temp_file = "temp_filled_output.xlsx"
    wb.save(temp_file)
    wb.close()
    
    import shutil
    # 1. Lưu sang Downloads
    try:
        shutil.copyfile(temp_file, DEST_DOWNLOADS)
        print(f"Saved to Downloads: {DEST_DOWNLOADS}")
    except PermissionError:
        dest_alt = DEST_DOWNLOADS.replace(".xlsx", "_filled.xlsx")
        shutil.copyfile(temp_file, dest_alt)
        print(f"File locked in Downloads, saved to: {dest_alt}")
        
    # 2. Lưu sang Working
    os.makedirs(os.path.dirname(DEST_WORKING), exist_ok=True)
    try:
        shutil.copyfile(temp_file, DEST_WORKING)
        print(f"Saved to Working: {DEST_WORKING}")
    except Exception as e:
        print("Note on working save:", e)
        
    if os.path.exists(temp_file):
        os.remove(temp_file)

if __name__ == "__main__":
    fill_workbook()
