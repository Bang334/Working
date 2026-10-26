# -*- coding: utf-8 -*-
"""
Script điền thông tin từ file DANH_SACH_THIET_BI_SUA_CHUA_THAY_THE_DFV_DARFON.xlsx
vào mẫu Phiếu yêu cầu sửa chữa phần cứng (Copy of danh sach sua lot 3 (1).xlsx)
cho đối tác DFV (Darfon Việt Nam).
Đơn giá và thành tiền để trống (có sẵn công thức) để Sếp Trương tự điền.
"""

import os
import sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

TEMPLATE_PATH = r"C:\Users\BANG\Downloads\Copy of danh sach sua lot 3 (1).xlsx"
SOURCE_PATH = r"E:\Working\Bieu Mau\26 10 Làm file liệt kê thiết bị\DANH_SACH_THIET_BI_SUA_CHUA_THAY_THE_DFV_DARFON.xlsx"

OUT_PATH_WORKING = r"E:\Working\Bieu Mau\26 10 Làm file liệt kê thiết bị\PHIEU_GUI_SUA_CHUA_THIET_BI_DFV_DARFON.xlsx"
OUT_PATH_DOWNLOADS = r"C:\Users\BANG\Downloads\PHIEU_GUI_SUA_CHUA_THIET_BI_DFV_DARFON.xlsx"

# 19 thiết bị chi tiết
ITEMS = [
    # 3 Máy tính bảng HT10
    {
        "stt": 1,
        "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
        "category": "Phần cứng thân máy\n平板主機",
        "detail": "Model: HT10 | S/N: C3Z03GQ301274\nP/N: 7400100004288M | HS: 8471.30.20\nHiện trạng: Lỗi mất mạng (断网), máy không có pin",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 2,
        "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
        "category": "Phần cứng thân máy\n平板主機",
        "detail": "Model: HT10 | S/N: C3Z03GQ301292\nP/N: 7400100004288M | HS: 8471.30.20\nHiện trạng: Lỗi mất mạng (断网), máy không có pin",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 3,
        "name": "Máy tính bảng công nghiệp AMobile 10\"\nAMobile 10\" 工業級平板電腦",
        "category": "Phần cứng thân máy\n平板主機",
        "detail": "Model: HT10 | S/N: C3Z03GQ301338\nP/N: 7400100004288M | HS: 8471.30.20\nHiện trạng: Lỗi mất mạng (断网), máy không có pin",
        "dept": "DFV",
        "qty": 1
    },
    # 4 Đế sạc HT10 Cradle S
    {
        "stt": 4,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705592\nNhãn: 1#, NG | HS: 8504.40.19\nHiện trạng: Lỗi mất mạng khi cắm dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 5,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705625\nNhãn: 2#, NG | HS: 8504.40.19\nHiện trạng: Lỗi mất mạng khi cắm dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 6,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705566\nNhãn: 6#, NG | HS: 8504.40.19\nHiện trạng: Lỗi mất mạng khi cắm dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 7,
        "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
        "category": "Phụ kiện đế sạc\n充電底座",
        "detail": "Model: HT10 Cradle S | S/N: C3V01GQ705615\nNhãn: 7#, NG | HS: 8504.40.19\nHiện trạng: Lỗi mất mạng khi cắm dock (断网)",
        "dept": "DFV",
        "qty": 1
    },
    # 4 Adapter nguồn 12V 2A
    {
        "stt": 8,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520558\nĐi kèm dock sạc 1# | HS: 8504.40.19\nHiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 9,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520560\nĐi kèm dock sạc 2# | HS: 8504.40.19\nHiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 10,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520575\nĐi kèm dock sạc 6# | HS: 8504.40.19\nHiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 11,
        "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
        "category": "Phụ kiện nguồn sạc\n電源配件",
        "detail": "Model: FY1202000 | S/N: 9056000619520595\nĐi kèm dock sạc 7# | HS: 8504.40.19\nHiện trạng: Gửi kèm đồng bộ để kiểm tra / đổi mới",
        "dept": "DFV",
        "qty": 1
    },
    # 8 Pin Lithium-ion máy tính bảng
    {
        "stt": 12,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000251\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 13,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000613\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 14,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309001047\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 15,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000337\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 16,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309001215\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 17,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309000561\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 18,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2309001198\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    },
    {
        "stt": 19,
        "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
        "category": "Linh kiện pin sạc\n專用鋰電池",
        "detail": "Model: CLP629 (10000mAh) | S/N: C629B2305001525\nP/N: 1ICP6/45/116-2 | HS: 8507.60.90\nHiện trạng: Pin phồng rộp (电池鼓包), đề nghị cấp mới",
        "dept": "DFV",
        "qty": 1
    }
]

def build_dfv_form():
    wb = openpyxl.load_workbook(TEMPLATE_PATH)
    ws = wb.active
    ws.title = "Phiếu Gửi Sửa Chữa DFV"
    
    # 1. Cập nhật thông tin bên mua (Bên gửi sửa: DFV - Darfon Việt Nam)
    ws["H2"] = "Công ty TNHH Điện tử Darfon (Việt Nam) / 達方電子 (越南) 有限公司"
    ws["H3"] = "Jessica (碧娟 - 台灣採購&財務主管) / Bộ phận tiếp nhận DFV"
    ws["H4"] = "Liên hệ qua Jessica / Đại diện DFV"
    ws["H6"] = "KCN Darfon Electronics Vietnam"
    ws["H7"] = "Đồng bộ qua Jessica (達方採購部)"
    
    # 2. Cập nhật ngày yêu cầu tại A10
    ws["A10"] = "Ngày yêu cầu.要求日期：26/10/2026"
    ws["A10"].font = Font(name="微軟正黑體", size=14, bold=True)
    
    # Định dạng cell
    font_content = Font(name="微軟正黑體", size=11, color="111111")
    font_content_bold = Font(name="微軟正黑體", size=11, bold=True, color="111111")
    font_sn = Font(name="Consolas", size=10.5, bold=True, color="002060")
    font_summary = Font(name="微軟正黑體", size=13, bold=True, color="000000")
    
    bd_thin = Side(border_style="thin", color="000000")
    border_cell = Border(left=bd_thin, right=bd_thin, top=bd_thin, bottom=bd_thin)
    
    fill_zebra_1 = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra_2 = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    fill_header_qty = PatternFill(start_color="EAECEE", end_color="EAECEE", fill_type="solid")
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center", wrap_text=True)
    
    # Hủy gộp các ô từ dòng 12 trở xuống của mẫu cũ để không bị lỗi MergedCell
    for rng in list(ws.merged_cells.ranges):
        min_c, min_r, max_c, max_r = rng.bounds
        if min_r >= 12:
            ws.unmerge_cells(start_row=min_r, start_column=min_c, end_row=max_r, end_column=max_c)
            
    # 3. Đổ dữ liệu 19 thiết bị từ Hàng 12 đến Hàng 30
    start_row = 12
    for i, item in enumerate(ITEMS):
        row = start_row + i
        ws.row_dimensions[row].height = 42
        fill_row = fill_zebra_2 if (i % 2 == 1) else fill_zebra_1
        
        # Col A: STT
        cA = ws.cell(row=row, column=1, value=item["stt"])
        cA.alignment = align_center
        cA.font = font_content_bold
        cA.fill = fill_row
        cA.border = border_cell
        
        # Col B: Tên Sản Phẩm
        cB = ws.cell(row=row, column=2, value=item["name"])
        cB.alignment = align_left
        cB.font = font_content_bold
        cB.fill = fill_row
        cB.border = border_cell
        
        # Col C: Hạng Mục
        cC = ws.cell(row=row, column=3, value=item["category"])
        cC.alignment = align_center
        cC.font = font_content
        cC.fill = fill_row
        cC.border = border_cell
        
        # Col D: Nội Dung Sản Phẩm (Model, S/N, lỗi)
        cD = ws.cell(row=row, column=4, value=item["detail"])
        cD.alignment = align_left
        cD.font = font_content
        cD.fill = fill_row
        cD.border = border_cell
        
        # Col E: Bộ phận gửi sửa
        cE = ws.cell(row=row, column=5, value=item["dept"])
        cE.alignment = align_center
        cE.font = font_content
        cE.fill = fill_row
        cE.border = border_cell
        
        # Col F: Số lượng
        cF = ws.cell(row=row, column=6, value=item["qty"])
        cF.alignment = align_center
        cF.font = font_content_bold
        cF.fill = fill_row
        cF.border = border_cell
        
        # Col G: Thời gian hoàn thành (để trống)
        cG = ws.cell(row=row, column=7, value="")
        cG.alignment = align_center
        cG.font = font_content
        cG.fill = fill_row
        cG.border = border_cell
        
        # Col H: Đơn Giá (Sếp tự điền)
        cH = ws.cell(row=row, column=8, value=None)
        cH.alignment = align_right
        cH.font = font_content_bold
        cH.fill = fill_row
        cH.border = border_cell
        cH.number_format = "#,##0"
        
        # Col I: Tổng Giá (Công thức sống = F*H)
        cI = ws.cell(row=row, column=9, value=f"=IF(H{row}>0, F{row}*H{row}, \"\")")
        cI.alignment = align_right
        cI.font = font_content_bold
        cI.fill = fill_row
        cI.border = border_cell
        cI.number_format = "#,##0"

    end_data_row = start_row + len(ITEMS) - 1 # Row 30
    
    # 4. Hàng "Chỗ trống sau đây" (以下空白) tại Row 31
    blank_row = end_data_row + 1 # Row 31
    ws.row_dimensions[blank_row].height = 24
    ws.merge_cells(f"A{blank_row}:I{blank_row}")
    c_blank = ws.cell(row=blank_row, column=1, value="以下空白 Chỗ trống sau đây")
    c_blank.alignment = align_center
    c_blank.font = Font(name="微軟正黑體", size=11, italic=True, color="555555")
    for col in range(1, 10):
        ws.cell(row=blank_row, column=col).border = border_cell
        
    # 5. Hàng Tổng cộng tại Row 32
    sum_row = blank_row + 1 # Row 32
    ws.row_dimensions[sum_row].height = 36
    ws.merge_cells(f"A{sum_row}:E{sum_row}")
    c_to = ws.cell(
        row=sum_row, 
        column=1, 
        value="此致\n         Công ty TNHH Điện tử Darfon (Việt Nam) / 達方電子 (越南) 有限公司"
    )
    c_to.alignment = align_left
    c_to.font = Font(name="微軟正黑體", size=12, bold=True)
    c_to.border = border_cell
    for col in range(2, 6):
        ws.cell(row=sum_row, column=col).border = border_cell
        
    # Tổng số lượng tại cột F
    c_sum_qty = ws.cell(row=sum_row, column=6, value=f"=SUM(F{start_row}:F{end_data_row})")
    c_sum_qty.alignment = align_center
    c_sum_qty.font = font_summary
    c_sum_qty.fill = fill_header_qty
    c_sum_qty.border = border_cell
    
    # Col G trống
    ws.cell(row=sum_row, column=7, value="").border = border_cell
    
    # Col H: TỔNG THÀNH TIỀN
    c_sum_lbl = ws.cell(row=sum_row, column=8, value="TỔNG THÀNH TIỀN \n總價")
    c_sum_lbl.alignment = align_center
    c_sum_lbl.font = font_summary
    c_sum_lbl.border = border_cell
    
    # Col I: Tổng thành tiền (SUM)
    c_sum_val = ws.cell(row=sum_row, column=9, value=f"=SUM(I{start_row}:I{end_data_row})")
    c_sum_val.alignment = align_right
    c_sum_val.font = font_summary
    c_sum_val.border = border_cell
    c_sum_val.number_format = "#,##0"
    
    # 6. Khối chữ ký xác nhận của khách hàng DFV tại Row 33 & 34
    sig_row_1 = sum_row + 1 # Row 33
    ws.row_dimensions[sig_row_1].height = 24
    ws.cell(row=sig_row_1, column=1, value="※客戶確認 Xác nhận khách hàng").font = Font(name="微軟正黑體", size=12, bold=True)
    
    sig_row_2 = sig_row_1 + 1 # Row 34
    ws.row_dimensions[sig_row_2].height = 24
    ws.cell(row=sig_row_2, column=1, value="(請簽名用印 Vui lòng ký tên và đóng dấu)").font = Font(name="微軟正黑體", size=11, italic=True)
    
    # Thiết lập độ rộng cột tối ưu
    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 24
    ws.column_dimensions["D"].width = 46
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 20
    ws.column_dimensions["H"].width = 20
    ws.column_dimensions["I"].width = 24
    
    # -----------------------------------------------------------------
    # SHEET 2: BẢNG GỘP NHÓM (4 CHỦNG LOẠI TỔNG HỢP CHO SẾP CHỌN BÁO GIÁ)
    # -----------------------------------------------------------------
    ws2 = wb.create_sheet(title="Bảng Gộp 4 Nhóm Báo Giá")
    
    from copy import copy
    # Sao chép header thông tin công ty sang Sheet 2
    for r in range(1, 8):
        for c in range(1, 10):
            val = ws.cell(r, c).value
            if val is not None:
                ws2.cell(r, c, val)
                if ws.cell(r, c).font:
                    ws2.cell(r, c).font = copy(ws.cell(r, c).font)
                if ws.cell(r, c).alignment:
                    ws2.cell(r, c).alignment = copy(ws.cell(r, c).alignment)
                
    for rng in list(ws.merged_cells.ranges):
        min_c, min_r, max_c, max_r = rng.bounds
        if max_r <= 7:
            ws2.merge_cells(start_row=min_r, start_column=min_c, end_row=max_r, end_column=max_c)
            
    ws2["A9"] = "Phiếu yêu cầu sửa chữa phần cứng (Bảng tổng hợp theo chủng loại)\n硬體維修申請單 (依設備類別匯總表)"
    if ws["A9"].font: ws2["A9"].font = copy(ws["A9"].font)
    ws2.row_dimensions[9].height = ws.row_dimensions[9].height
    
    ws2["A10"] = "Ngày yêu cầu.要求日期：26/10/2026"
    if ws["A10"].font: ws2["A10"].font = copy(ws["A10"].font)
    ws2.row_dimensions[10].height = ws.row_dimensions[10].height
    
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
            "detail": "Model: HT10 | P/N: 7400100004288M | HS: 8471.30.20\nDanh sách 3 S/N: C3Z03GQ301274, C3Z03GQ301292, C3Z03GQ301338\nHiện trạng: Lỗi mất mạng (断网), thân máy không có pin đi kèm",
            "dept": "DFV",
            "qty": 3
        },
        {
            "stt": 2,
            "name": "Đế sạc đơn máy tính bảng HT10\nAMobile HT10 單座充電底座",
            "category": "Phụ kiện đế sạc\n充電底座",
            "detail": "Model: HT10 Cradle S | HS: 8504.40.19\nDanh sách 4 S/N: C3V01GQ705592 (1#), C3V01GQ705625 (2#), C3V01GQ705566 (6#), C3V01GQ705615 (7#)\nHiện trạng: Đánh dấu NG, lỗi mất mạng khi kết nối dock (断网)",
            "dept": "DFV",
            "qty": 4
        },
        {
            "stt": 3,
            "name": "Bộ nguồn sạc Adapter 12V 2A\n電源適應器 (Power Supply)",
            "category": "Phụ kiện nguồn sạc\n電源配件",
            "detail": "Model: FY1202000 | In: 100-240V | Out: 12V 2A | HS: 8504.40.19\nDanh sách 4 S/N: 9056000619520558, 9056000619520560, 9056000619520575, 9056000619520595\nHiện trạng: Kèm theo 4 dock sạc 1#, 2#, 6#, 7# để kiểm tra đồng bộ",
            "dept": "DFV",
            "qty": 4
        },
        {
            "stt": 4,
            "name": "Pin sạc máy tính bảng HT10\nHT10 平板專用鋰離子電池",
            "category": "Linh kiện pin sạc\n專用鋰電池",
            "detail": "Model: CLP629 (10000mAh) | P/N: 1ICP6/45/116-2 | HS: 8507.60.90\nDanh sách 8 S/N: C629B2309000251, C629B2309000613, C629B2309001047, C629B2309000337,\nC629B2309001215, C629B2309000561, C629B2309001198, C629B2305001525\nHiện trạng: 8 viên pin đều bị phồng (电池鼓包), đề nghị cấp mới",
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
        cA.font = font_content_bold
        cA.fill = fill_row
        cA.border = border_cell
        
        cB = ws2.cell(row=r, column=2, value=g["name"])
        cB.alignment = align_left
        cB.font = font_content_bold
        cB.fill = fill_row
        cB.border = border_cell
        
        cC = ws2.cell(row=r, column=3, value=g["category"])
        cC.alignment = align_center
        cC.font = font_content
        cC.fill = fill_row
        cC.border = border_cell
        
        cD = ws2.cell(row=r, column=4, value=g["detail"])
        cD.alignment = align_left
        cD.font = font_content
        cD.fill = fill_row
        cD.border = border_cell
        
        cE = ws2.cell(row=r, column=5, value=g["dept"])
        cE.alignment = align_center
        cE.font = font_content
        cE.fill = fill_row
        cE.border = border_cell
        
        cF = ws2.cell(row=r, column=6, value=g["qty"])
        cF.alignment = align_center
        cF.font = font_content_bold
        cF.fill = fill_row
        cF.border = border_cell
        
        cG = ws2.cell(row=r, column=7, value="")
        cG.border = border_cell
        
        cH = ws2.cell(row=r, column=8, value=None)
        cH.alignment = align_right
        cH.font = font_content_bold
        cH.fill = fill_row
        cH.border = border_cell
        cH.number_format = "#,##0"
        
        cI = ws2.cell(row=r, column=9, value=f"=IF(H{r}>0, F{r}*H{r}, \"\")")
        cI.alignment = align_right
        cI.font = font_content_bold
        cI.fill = fill_row
        cI.border = border_cell
        cI.number_format = "#,##0"

    ws2.row_dimensions[16].height = 24
    ws2.merge_cells("A16:I16")
    ws2["A16"] = "以下空白 Chỗ trống sau đây"
    ws2["A16"].alignment = align_center
    ws2["A16"].font = Font(name="微軟正黑體", size=11, italic=True, color="555555")
    for col in range(1, 10):
        ws2.cell(row=16, column=col).border = border_cell
        
    ws2.row_dimensions[17].height = 36
    ws2.merge_cells("A17:E17")
    ws2["A17"] = "此致\n         Công ty TNHH Điện tử Darfon (Việt Nam) / 達方電子 (越南) 有限公司"
    ws2["A17"].alignment = align_left
    ws2["A17"].font = Font(name="微軟正黑體", size=12, bold=True)
    for col in range(1, 6):
        ws2.cell(row=17, column=col).border = border_cell
        
    ws2["F17"] = "=SUM(F12:F15)"
    ws2["F17"].alignment = align_center
    ws2["F17"].font = font_summary
    ws2["F17"].fill = fill_header_qty
    ws2["F17"].border = border_cell
    
    ws2["G17"] = ""
    ws2["G17"].border = border_cell
    
    ws2["H17"] = "TỔNG THÀNH TIỀN \n總價"
    ws2["H17"].alignment = align_center
    ws2["H17"].font = font_summary
    ws2["H17"].border = border_cell
    
    ws2["I17"] = "=SUM(I12:I15)"
    ws2["I17"].alignment = align_right
    ws2["I17"].font = font_summary
    ws2["I17"].border = border_cell
    ws2.cell(row=17, column=9).number_format = "#,##0"
    
    ws2.row_dimensions[18].height = 24
    ws2["A18"] = "※客戶確認 Xác nhận khách hàng"
    ws2["A18"].font = Font(name="微軟正黑體", size=12, bold=True)
    
    ws2.row_dimensions[19].height = 24
    ws2["A19"] = "(請簽名用印 Vui lòng ký tên và đóng dấu)"
    ws2["A19"].font = Font(name="微軟正黑體", size=11, italic=True)

    # Lưu workbook
    wb.save(OUT_PATH_WORKING)
    wb.save(OUT_PATH_DOWNLOADS)
    print("Successfully built both files!")

if __name__ == "__main__":
    build_dfv_form()
