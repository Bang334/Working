# -*- coding: utf-8 -*-
"""
Script tạo bảng kê thiết bị sửa chữa, báo hỏng & đề nghị bổ sung thay thế cho DFV (Darfon)
Bao gồm hình ảnh thực tế, mã S/N, P/N, IMEI, thông số và bảng tra cứu HS Code nhập khẩu.
"""

import os
import sys
from PIL import Image
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter

# Đường dẫn thư mục ảnh gốc
IMG_DIR = r"C:\Users\BANG\Downloads\My Documents [26-10-2026 13_34]"
THUMB_DIR = r"E:\Working\.tmp\thiet_bi_dfv_thumbnails"
os.makedirs(THUMB_DIR, exist_ok=True)

# Danh sách dữ liệu thiết bị
DEVICES = [
    # Nhóm 1: Máy tính bảng HT10
    {
        "stt": 1,
        "img_file": "1d3e671f292aa974f03b11.jpg",
        "category_vi": "Máy tính bảng công nghiệp",
        "category_zh": "工業級平板電腦",
        "name_model": "AMobile 10\" Rugged Tablet\nModel: HT10",
        "pn": "7400100004288M",
        "sn": "C3Z03GQ301274",
        "specs": "IMEI 1: 355480071877810\nIMEI 2: 355480071877828\nInput: 5V 2A / 9V 2A\nFCC ID: 2AZNT-HT10\nMade in Taiwan",
        "hs_code": "8471.30.20",
        "fault_vi": "Lỗi mất mạng (断网). Máy gửi về hiện không có pin đi kèm.",
        "fault_zh": "無法聯網 (斷網)。設備無隨附電池。",
        "marking": "Dán băng keo: \"断网\"\n(Pin phồng đã thông báo qua email)",
        "marking_zh": "貼標: \"断网\"\n(電池鼓包，郵件已說明)",
        "is_portrait": True
    },
    {
        "stt": 2,
        "img_file": "3b8c45a80b9d8bc3d28c10.jpg",
        "category_vi": "Máy tính bảng công nghiệp",
        "category_zh": "工業級平板電腦",
        "name_model": "AMobile 10\" Rugged Tablet\nModel: HT10",
        "pn": "7400100004288M",
        "sn": "C3Z03GQ301292",
        "specs": "IMEI 1: 355480071878172\nIMEI 2: 355480071878180\nInput: 5V 2A / 9V 2A\nFCC ID: 2AZNT-HT10\nMade in Taiwan",
        "hs_code": "8471.30.20",
        "fault_vi": "Lỗi mất mạng (断网). Máy gửi về hiện không có pin đi kèm.",
        "fault_zh": "無法聯網 (斷網)。設備無隨附電池。",
        "marking": "Dán băng keo: \"断网\"\n(Pin phồng đã thông báo qua email)",
        "marking_zh": "貼標: \"断网\"\n(電池鼓包，郵件已說明)",
        "is_portrait": True
    },
    {
        "stt": 3,
        "img_file": "9262fd4cb37933276a689.jpg",
        "category_vi": "Máy tính bảng công nghiệp",
        "category_zh": "工業級平板電腦",
        "name_model": "AMobile 10\" Rugged Tablet\nModel: HT10",
        "pn": "7400100004288M",
        "sn": "C3Z03GQ301338",
        "specs": "IMEI 1: 355480071879097\nIMEI 2: 355480071879105\nInput: 5V 2A / 9V 2A\nFCC ID: 2AZNT-HT10\nMade in Taiwan",
        "hs_code": "8471.30.20",
        "fault_vi": "Lỗi mất mạng (断网). Máy gửi về hiện không có pin đi kèm.",
        "fault_zh": "無法聯網 (斷網)。設備無隨附電池。",
        "marking": "Dán băng keo: \"断网\"\n(Pin phồng đã thông báo qua email)",
        "marking_zh": "貼標: \"断网\"\n(電池鼓包，郵件已說明)",
        "is_portrait": True
    },
    # Nhóm 2: Đế sạc HT10 Cradle S
    {
        "stt": 4,
        "img_file": "b7294f1f012a8174d83b2.jpg",
        "category_vi": "Đế sạc đơn máy tính bảng",
        "category_zh": "單座充電底座",
        "name_model": "AMobile Single Slot Base Cradle\nModel: HT10 Cradle S",
        "pn": "-",
        "sn": "C3V01GQ705592",
        "specs": "Input: 5V 2A / 9V 2A\nOutput: 5V 2A / 9V 2A\nCE / FC Certified\nMade in Taiwan",
        "hs_code": "8504.40.19",
        "fault_vi": "Lỗi mất mạng (khi kết nối qua dock sạc). Ghi nhận NG.",
        "fault_zh": "底座連線斷網。標記 NG。",
        "marking": "Bút xanh: \"1#\", \"NG\"\nBăng keo: \"断网\"",
        "marking_zh": "手寫標記: \"1#\", \"NG\"\n膠帶標記: \"断网\"",
        "is_portrait": False
    },
    {
        "stt": 5,
        "img_file": "159f4fb5018081ded8914.jpg",
        "category_vi": "Đế sạc đơn máy tính bảng",
        "category_zh": "單座充電底座",
        "name_model": "AMobile Single Slot Base Cradle\nModel: HT10 Cradle S",
        "pn": "-",
        "sn": "C3V01GQ705625",
        "specs": "Input: 5V 2A / 9V 2A\nOutput: 5V 2A / 9V 2A\nCE / FC Certified\nMade in Taiwan",
        "hs_code": "8504.40.19",
        "fault_vi": "Lỗi mất mạng (khi kết nối qua dock sạc). Ghi nhận NG.",
        "fault_zh": "底座連線斷網。標記 NG。",
        "marking": "Bút xanh: \"2#\", \"NG\"\nBăng keo: \"断网\"",
        "marking_zh": "手寫標記: \"2#\", \"NG\"\n膠帶標記: \"断网\"",
        "is_portrait": False
    },
    {
        "stt": 6,
        "img_file": "e5794b470572852cdc631.jpg",
        "category_vi": "Đế sạc đơn máy tính bảng",
        "category_zh": "單座充電底座",
        "name_model": "AMobile Single Slot Base Cradle\nModel: HT10 Cradle S",
        "pn": "-",
        "sn": "C3V01GQ705566",
        "specs": "Input: 5V 2A / 9V 2A\nOutput: 5V 2A / 9V 2A\nCE / FC Certified\nMade in Taiwan",
        "hs_code": "8504.40.19",
        "fault_vi": "Lỗi mất mạng (khi kết nối qua dock sạc). Ghi nhận NG.",
        "fault_zh": "底座連線斷網。標記 NG。",
        "marking": "Bút xanh: \"6#\", \"NG\"\nBăng keo: \"断网\"",
        "marking_zh": "手寫標記: \"6#\", \"NG\"\n膠帶標記: \"断网\"",
        "is_portrait": False
    },
    {
        "stt": 7,
        "img_file": "09be848ccab94ae713a83.jpg",
        "category_vi": "Đế sạc đơn máy tính bảng",
        "category_zh": "單座充電底座",
        "name_model": "AMobile Single Slot Base Cradle\nModel: HT10 Cradle S",
        "pn": "-",
        "sn": "C3V01GQ705615",
        "specs": "Input: 5V 2A / 9V 2A\nOutput: 5V 2A / 9V 2A\nCE / FC Certified\nMade in Taiwan",
        "hs_code": "8504.40.19",
        "fault_vi": "Lỗi mất mạng (khi kết nối qua dock sạc). Ghi nhận NG.",
        "fault_zh": "底座連線斷網。標記 NG。",
        "marking": "Bút xanh: \"7#\", \"NG\"\nBăng keo: \"断网\"",
        "marking_zh": "手寫標記: \"7#\", \"NG\"\n膠帶標記: \"断网\"",
        "is_portrait": False
    },
    # Nhóm 3: Bộ nguồn Adapter
    {
        "stt": 8,
        "img_file": "4e436a6c2459a407fd486.jpg",
        "category_vi": "Nguồn sạc / Adapter",
        "category_zh": "電源適應器",
        "name_model": "Power Supply Adapter\nModel: FY1202000",
        "pn": "-",
        "sn": "9056000619520558",
        "specs": "Input: 100-240V ~ 50/60Hz 0.8A\nOutput: 12V == 2.0A\nĐi kèm cáp AC & giắc cắm DC",
        "hs_code": "8504.40.19",
        "fault_vi": "Bộ nguồn kèm dock sạc 1#.\nGửi kèm đồng bộ để kiểm tra / đổi mới.",
        "fault_zh": "配套 1# 底座電源。\n整套寄回原廠檢測/換新。",
        "marking": "Đi kèm đế sạc 1#",
        "marking_zh": "配對 1# 底座",
        "is_portrait": False
    },
    {
        "stt": 9,
        "img_file": "80a14c8202b782e9dba68.jpg",
        "category_vi": "Nguồn sạc / Adapter",
        "category_zh": "電源適應器",
        "name_model": "Power Supply Adapter\nModel: FY1202000",
        "pn": "-",
        "sn": "9056000619520560",
        "specs": "Input: 100-240V ~ 50/60Hz 0.8A\nOutput: 12V == 2.0A\nĐi kèm cáp AC & giắc cắm DC",
        "hs_code": "8504.40.19",
        "fault_vi": "Bộ nguồn kèm dock sạc 2#.\nGửi kèm đồng bộ để kiểm tra / đổi mới.",
        "fault_zh": "配套 2# 底座電源。\n整套寄回原廠檢測/換新。",
        "marking": "Đi kèm đế sạc 2#",
        "marking_zh": "配對 2# 底座",
        "is_portrait": False
    },
    {
        "stt": 10,
        "img_file": "ffab0a8044b5c4eb9da47.jpg",
        "category_vi": "Nguồn sạc / Adapter",
        "category_zh": "電源適應器",
        "name_model": "Power Supply Adapter\nModel: FY1202000",
        "pn": "-",
        "sn": "9056000619520575",
        "specs": "Input: 100-240V ~ 50/60Hz 0.8A\nOutput: 12V == 2.0A\nĐi kèm cáp AC & giắc cắm DC",
        "hs_code": "8504.40.19",
        "fault_vi": "Bộ nguồn kèm dock sạc 6#.\nGửi kèm đồng bộ để kiểm tra / đổi mới.",
        "fault_zh": "配套 6# 底座電源。\n整套寄回原廠檢測/換新。",
        "marking": "Đi kèm đế sạc 6#",
        "marking_zh": "配對 6# 底座",
        "is_portrait": False
    },
    {
        "stt": 11,
        "img_file": "a5fc94d7dae25abc03f35.jpg",
        "category_vi": "Nguồn sạc / Adapter",
        "category_zh": "電源適應器",
        "name_model": "Power Supply Adapter\nModel: FY1202000",
        "pn": "-",
        "sn": "9056000619520595",
        "specs": "Input: 100-240V ~ 50/60Hz 0.8A\nOutput: 12V == 2.0A\nĐi kèm cáp AC & giắc cắm DC",
        "hs_code": "8504.40.19",
        "fault_vi": "Bộ nguồn kèm dock sạc 7#.\nGửi kèm đồng bộ để kiểm tra / đổi mới.",
        "fault_zh": "配套 7# 底座電源。\n整套寄回原廠檢測/換新。",
        "marking": "Đi kèm đế sạc 7#",
        "marking_zh": "配對 7# 底座",
        "is_portrait": False
    }
]

def make_thumbnails():
    """Tạo thumbnail chất lượng cao với kích thước tối ưu cho ô Excel"""
    thumb_paths = {}
    for dev in DEVICES:
        orig = os.path.join(IMG_DIR, dev["img_file"])
        thumb_file = f"thumb_{dev['stt']}_{dev['img_file']}"
        thumb_dest = os.path.join(THUMB_DIR, thumb_file)
        
        im = Image.open(orig)
        if dev["is_portrait"]:
            # Ảnh dọc 720x1280: scale về width ~65, height ~115
            target_size = (65, 115)
        else:
            # Ảnh ngang 1280x720: scale về width ~130, height ~73
            target_size = (130, 73)
            
        im_resized = im.resize(target_size, Image.LANCZOS)
        im_resized.save(thumb_dest, "JPEG", quality=90)
        thumb_paths[dev["stt"]] = (thumb_dest, target_size, orig)
    return thumb_paths

def build_excel(out_path):
    wb = openpyxl.Workbook()
    
    # -------------------------------------------------------------
    # SHEET 1: CHI TIẾT THIẾT BỊ (DEVICES LIST)
    # -------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Danh Sách Thiết Bị (明細表)"
    ws1.views.sheetView[0].showGridLines = True
    
    # Định nghĩa Styles & Màu sắc chuyên nghiệp
    FONT_FAMILY = "Microsoft JhengHei"
    
    font_corp = Font(name=FONT_FAMILY, size=14, bold=True, color="1F4E79")
    font_title = Font(name=FONT_FAMILY, size=13, bold=True, color="002060")
    font_subtitle = Font(name=FONT_FAMILY, size=11, bold=True, color="333333")
    font_meta = Font(name=FONT_FAMILY, size=10, italic=False, color="444444")
    font_header = Font(name=FONT_FAMILY, size=10, bold=True, color="FFFFFF")
    font_data = Font(name=FONT_FAMILY, size=9.5, color="111111")
    font_data_bold = Font(name=FONT_FAMILY, size=9.5, bold=True, color="111111")
    font_sn = Font(name="Consolas", size=10.5, bold=True, color="002060")
    font_hs = Font(name="Consolas", size=10.5, bold=True, color="0B5394")
    font_fault = Font(name=FONT_FAMILY, size=9, bold=False, color="900C3F")
    font_summary = Font(name=FONT_FAMILY, size=10.5, bold=True, color="1F4E79")
    
    fill_header = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    fill_meta = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
    fill_zebra_1 = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_zebra_2 = PatternFill(start_color="F9FBFC", end_color="F9FBFC", fill_type="solid")
    fill_hs = PatternFill(start_color="E8F4F8", end_color="E8F4F8", fill_type="solid")
    fill_fault = PatternFill(start_color="FDF2E9", end_color="FDF2E9", fill_type="solid")
    fill_summary = PatternFill(start_color="EAECEE", end_color="EAECEE", fill_type="solid")
    
    bd_thin = Side(border_style="thin", color="D0D7DE")
    border_cell = Border(left=bd_thin, right=bd_thin, top=bd_thin, bottom=bd_thin)
    border_header = Border(
        left=Side(style="thin", color="4F81BD"),
        right=Side(style="thin", color="4F81BD"),
        top=Side(style="medium", color="1F4E79"),
        bottom=Side(style="medium", color="1F4E79")
    )
    border_summary = Border(
        top=Side(style="thin", color="1F4E79"),
        bottom=Side(style="double", color="1F4E79"),
        left=bd_thin,
        right=bd_thin
    )
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_center_top = Alignment(horizontal="center", vertical="top", wrap_text=True)
    align_left_top = Alignment(horizontal="left", vertical="top", wrap_text=True)
    
    # 1. Header công ty & Tiêu đề
    ws1.merge_cells("A1:J1")
    ws1["A1"] = "CÔNG TY TNHH TOÀN CẦU HONG MING / 浤詺全體顧問有限公司 (HONG MING GLOBAL CO., LTD.)"
    ws1["A1"].font = font_corp
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 25
    
    ws1.merge_cells("A2:J2")
    ws1["A2"] = "BẢNG KÊ THIẾT BỊ BÁO HỎNG & ĐỀ NGHỊ BỔ SUNG THAY THẾ (DARFON / DFV)"
    ws1["A2"].font = font_title
    ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 22
    
    ws1.merge_cells("A3:J3")
    ws1["A3"] = "達方電子 (DFV) 故障設備更換清單及台灣工廠維修備品補充分類表"
    ws1["A3"].font = font_subtitle
    ws1["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[3].height = 20
    
    # Metadata info bar
    ws1.merge_cells("A4:J4")
    ws1["A4"] = "Dự án: DFV (Darfon Vietnam) | Ngày lập: 26/10/2026 | Người lập: Nguyễn Sỹ Kim Bằng (PM) | Phê duyệt: Jenson (張總) | Tiếp nhận: Jessica (台灣採購/財務主管)"
    ws1["A4"].font = font_meta
    ws1["A4"].fill = fill_meta
    ws1["A4"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[4].height = 20
    
    # 2. Tiêu đề các cột (Column Headers)
    headers = [
        ("STT\n序號", 6),
        ("Hình Ảnh Thực Tế (Gốc 100%)\n實物照片 (原圖)", 30),
        ("Chủng Loại\n設備類別", 18),
        ("Tên Sản Phẩm & Model\n產品名稱及型號", 24),
        ("Mã Linh Kiện P/N\n產品料號", 17),
        ("Số Serial (S/N)\n產品序號", 20),
        ("IMEI / Thông Số Kỹ Thuật\n規格及參數", 26),
        ("Mã HS Code\n海關編碼", 14),
        ("Hiện Trạng Lỗi Ghi Nhận\n故障情況說明", 26),
        ("Đánh Dấu & Ghi Chú\n標記及備註說明", 24),
    ]
    
    header_row = 5
    ws1.row_dimensions[header_row].height = 36
    for col_idx, (h_text, col_w) in enumerate(headers, start=1):
        cell = ws1.cell(row=header_row, column=col_idx, value=h_text)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_header
        col_letter = get_column_letter(col_idx)
        ws1.column_dimensions[col_letter].width = col_w
        
    # 3. Đổ dữ liệu 11 thiết bị
    start_row = 6
    for i, dev in enumerate(DEVICES):
        row = start_row + i
        ws1.row_dimensions[row].height = 120  # Chiều cao rộng rãi hiển thị ảnh to rõ nét
        fill_row = fill_zebra_2 if (i % 2 == 1) else fill_zebra_1
        
        # Col 1: STT
        c1 = ws1.cell(row=row, column=1, value=dev["stt"])
        c1.alignment = align_center
        c1.font = font_data_bold
        c1.fill = fill_row
        c1.border = border_cell
        
        # Col 2: Ảnh gốc độ phân giải cao 100% (giữ nguyên gốc không nén)
        c2 = ws1.cell(row=row, column=2, value="")
        c2.alignment = align_center
        c2.fill = fill_row
        c2.border = border_cell
        
        orig_path = os.path.join(IMG_DIR, dev["img_file"])
        c2.hyperlink = orig_path
        
        # Nhúng trực tiếp file ảnh gốc nguyên bản vào Excel
        xl_img = XLImage(orig_path)
        if dev["is_portrait"]:
            # Ảnh dọc 720x1280: hiển thị khung to rõ (rộng 79px, cao 140px)
            xl_img.width = 79
            xl_img.height = 140
        else:
            # Ảnh ngang 1280x720: hiển thị to rõ nét (rộng 196px, cao 110px)
            xl_img.width = 196
            xl_img.height = 110
            
        cell_coord = f"B{row}"
        ws1.add_image(xl_img, cell_coord)
        
        # Col 3: Chủng loại
        cat_text = f"{dev['category_vi']}\n{dev['category_zh']}"
        c3 = ws1.cell(row=row, column=3, value=cat_text)
        c3.alignment = align_center
        c3.font = font_data_bold
        c3.fill = fill_row
        c3.border = border_cell
        
        # Col 4: Tên & Model
        c4 = ws1.cell(row=row, column=4, value=dev["name_model"])
        c4.alignment = align_left
        c4.font = font_data_bold
        c4.fill = fill_row
        c4.border = border_cell
        
        # Col 5: P/N
        c5 = ws1.cell(row=row, column=5, value=dev["pn"])
        c5.alignment = align_center
        c5.font = font_data
        c5.fill = fill_row
        c5.border = border_cell
        
        # Col 6: S/N
        c6 = ws1.cell(row=row, column=6, value=dev["sn"])
        c6.alignment = align_center
        c6.font = font_sn
        c6.fill = fill_row
        c6.border = border_cell
        
        # Col 7: IMEI & Specs
        c7 = ws1.cell(row=row, column=7, value=dev["specs"])
        c7.alignment = align_left
        c7.font = font_data
        c7.fill = fill_row
        c7.border = border_cell
        
        # Col 8: HS Code
        c8 = ws1.cell(row=row, column=8, value=dev["hs_code"])
        c8.alignment = align_center
        c8.font = font_hs
        c8.fill = fill_hs
        c8.border = border_cell
        
        # Col 9: Hiện trạng lỗi
        fault_text = f"{dev['fault_vi']}\n{dev['fault_zh']}"
        c9 = ws1.cell(row=row, column=9, value=fault_text)
        c9.alignment = align_left
        c9.font = font_fault
        c9.fill = fill_fault
        c9.border = border_cell
        
        # Col 10: Đánh dấu & Ghi chú
        mark_text = f"{dev['marking']}\n{dev['marking_zh']}"
        c10 = ws1.cell(row=row, column=10, value=mark_text)
        c10.alignment = align_left
        c10.font = font_data
        c10.fill = fill_row
        c10.border = border_cell

    # 4. Dòng tổng cộng (Summary Row)
    sum_row = start_row + len(DEVICES)
    ws1.row_dimensions[sum_row].height = 28
    ws1.merge_cells(f"A{sum_row}:C{sum_row}")
    c_sum = ws1.cell(row=sum_row, column=1, value="TỔNG CỘNG / 合計")
    c_sum.alignment = align_center
    c_sum.font = font_summary
    c_sum.fill = fill_summary
    c_sum.border = border_summary
    for col in range(2, 4):
        ws1.cell(row=sum_row, column=col).fill = fill_summary
        ws1.cell(row=sum_row, column=col).border = border_summary
        
    ws1.merge_cells(f"D{sum_row}:J{sum_row}")
    c_sum_detail = ws1.cell(
        row=sum_row, 
        column=4, 
        value="11 Thiết bị & Phụ kiện (3 Máy tính bảng HT10 + 4 Đế sạc HT10 Cradle S + 4 Bộ nguồn Adapter 12V 2A)\n合計 11 件設備及配件（3台HT10平板 + 4個充電底座 + 4個12V 2A電源適應器）"
    )
    c_sum_detail.alignment = align_left
    c_sum_detail.font = font_summary
    c_sum_detail.fill = fill_summary
    c_sum_detail.border = border_summary
    for col in range(5, 11):
        ws1.cell(row=sum_row, column=col).fill = fill_summary
        ws1.cell(row=sum_row, column=col).border = border_summary

    # Ghim 5 hàng đầu tiên
    ws1.freeze_panes = "A6"
    ws1.print_area = f"A1:J{sum_row}"
    ws1.page_setup.orientation = ws1.ORIENTATION_LANDSCAPE
    ws1.page_setup.paperSize = ws1.PAPERSIZE_A4
    ws1.sheet_properties.pageSetUpPr.fitToPage = True
    ws1.page_setup.fitToWidth = 1
    ws1.page_setup.fitToHeight = 0

    # -------------------------------------------------------------
    # SHEET 2: BẢNG TỔNG HỢP NHẬP KHẨU & HS CODE (IMPORT SUMMARY)
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Tổng Hợp HS Code & Nhập Khẩu")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2.merge_cells("A1:I1")
    ws2["A1"] = "BẢNG TỔNG HỢP MÃ HS CODE & ĐỀ NGHỊ BỔ SUNG THAY THẾ (DARFON / DFV)"
    ws2["A1"].font = font_title
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 24
    
    ws2.merge_cells("A2:I2")
    ws2["A2"] = "進口報關海關編碼 (HS Code) 及台灣工廠備品補充匯總表"
    ws2["A2"].font = font_subtitle
    ws2["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[2].height = 20
    
    ws2.merge_cells("A3:I3")
    ws2["A3"] = "Căn cứ chỉ đạo Sếp Trương (Jenson): Tổng hợp danh mục & mã HS Code phục vụ bộ phận Mua hàng & Tài chính (Jessica - 碧娟) làm thủ tục nhập khẩu bổ sung từ Đài Loan."
    ws2["A3"].font = font_meta
    ws2["A3"].fill = fill_meta
    ws2["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[3].height = 20
    
    s2_headers = [
        ("STT\n序號", 6),
        ("Hạng Mục Hàng Hóa\n貨品名稱 (中/越)", 28),
        ("Model / Quy Cách\n型號及規格", 22),
        ("Số Lượng\n數量", 10),
        ("ĐVT\n單位", 8),
        ("Mã HS Code VN\n海關編碼", 16),
        ("Thuế Suất NK / VAT\n進口稅率/增值稅", 18),
        ("Xuất Xứ\n產地", 12),
        ("Mục Đích & Hiện Trạng Nghiệp Vụ\n補充原因及業務說明", 36),
    ]
    
    ws2.row_dimensions[4].height = 32
    for col_idx, (h_text, col_w) in enumerate(s2_headers, start=1):
        cell = ws2.cell(row=4, column=col_idx, value=h_text)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_header
        ws2.column_dimensions[get_column_letter(col_idx)].width = col_w
        
    s2_data = [
        {
            "stt": 1,
            "name": "Máy tính bảng công nghiệp 10.1\"\nAMobile 10\" 工業級平板電腦",
            "model": "AMobile HT10\nP/N: 7400100004288M",
            "qty": 3,
            "unit": "Chiếc\n台",
            "hs": "8471.30.20",
            "tax": "NK: 0% | VAT: 8% (hoặc 10%)",
            "origin": "Taiwan\n(台灣)",
            "purpose": "Đổi mới/Bảo hành: 3 thân máy bị lỗi ngắt mạng (断网). Đề nghị nhà máy Đài Loan gửi gấp 3 thân máy mới sang thay thế."
        },
        {
            "stt": 2,
            "name": "Pin thay thế máy tính bảng HT10\nHT10 平板專用鋰離子電池",
            "model": "HT10 Battery Pack\n(Rechargeable Li-ion)",
            "qty": 3,
            "unit": "Viên\n顆",
            "hs": "8507.60.90",
            "tax": "NK: 0% | VAT: 8% (hoặc 10%)",
            "origin": "Taiwan / China",
            "purpose": "Bổ sung mới: 3 viên pin cũ bị phồng nghiêm trọng (电池鼓包), không đảm bảo an toàn vận chuyển cùng máy. Cần bổ sung 3 viên pin mới đi kèm máy mới."
        },
        {
            "stt": 3,
            "name": "Đế sạc đơn máy tính bảng\nAMobile HT10 單座充電底座",
            "model": "AMobile HT10 Cradle S\nInput/Output: 5V 2A / 9V 2A",
            "qty": 4,
            "unit": "Chiếc\n個",
            "hs": "8504.40.19\n(hoặc 8473.30.90)",
            "tax": "NK: 0% | VAT: 8% (hoặc 10%)",
            "origin": "Taiwan\n(台灣)",
            "purpose": "Đổi mới/Bảo hành: 4 đế sạc bị lỗi kết nối mạng (1#, 2#, 6#, 7# đều bị 断网). Cần nhà máy Đài Loan gửi 4 đế sạc mới."
        },
        {
            "stt": 4,
            "name": "Bộ nguồn sạc / Adapter nguồn\n電源適應器 (Power Supply)",
            "model": "FY1202000\nIn: 100-240V | Out: 12V 2A",
            "qty": 4,
            "unit": "Bộ\n套",
            "hs": "8504.40.19",
            "tax": "NK: 0% | VAT: 8% (hoặc 10%)",
            "origin": "Taiwan / China",
            "purpose": "Đi kèm đồng bộ: 4 bộ sạc adapter tương ứng với 4 đế sạc để bàn (gửi kèm để kiểm tra đồng bộ nguồn và dock sạc)."
        }
    ]
    
    for row_idx, item in enumerate(s2_data, start=5):
        ws2.row_dimensions[row_idx].height = 42
        fill_row = fill_zebra_2 if (row_idx % 2 == 1) else fill_zebra_1
        
        c1 = ws2.cell(row=row_idx, column=1, value=item["stt"])
        c1.alignment = align_center
        c1.font = font_data_bold
        c1.fill = fill_row
        c1.border = border_cell
        
        c2 = ws2.cell(row=row_idx, column=2, value=item["name"])
        c2.alignment = align_left
        c2.font = font_data_bold
        c2.fill = fill_row
        c2.border = border_cell
        
        c3 = ws2.cell(row=row_idx, column=3, value=item["model"])
        c3.alignment = align_left
        c3.font = font_data
        c3.fill = fill_row
        c3.border = border_cell
        
        c4 = ws2.cell(row=row_idx, column=4, value=item["qty"])
        c4.alignment = align_center
        c4.font = font_data_bold
        c4.fill = fill_row
        c4.border = border_cell
        
        c5 = ws2.cell(row=row_idx, column=5, value=item["unit"])
        c5.alignment = align_center
        c5.font = font_data
        c5.fill = fill_row
        c5.border = border_cell
        
        c6 = ws2.cell(row=row_idx, column=6, value=item["hs"])
        c6.alignment = align_center
        c6.font = font_hs
        c6.fill = fill_hs
        c6.border = border_cell
        
        c7 = ws2.cell(row=row_idx, column=7, value=item["tax"])
        c7.alignment = align_center
        c7.font = font_data
        c7.fill = fill_row
        c7.border = border_cell
        
        c8 = ws2.cell(row=row_idx, column=8, value=item["origin"])
        c8.alignment = align_center
        c8.font = font_data
        c8.fill = fill_row
        c8.border = border_cell
        
        c9 = ws2.cell(row=row_idx, column=9, value=item["purpose"])
        c9.alignment = align_left
        c9.font = font_data
        c9.fill = fill_row
        c9.border = border_cell
        
    # Dòng tổng kết
    s2_sum_row = 5 + len(s2_data)
    ws2.row_dimensions[s2_sum_row].height = 28
    ws2.merge_cells(f"A{s2_sum_row}:C{s2_sum_row}")
    c_s2_sum = ws2.cell(row=s2_sum_row, column=1, value="TỔNG SỐ LƯỢNG YÊU CẦU BỔ SUNG / 合計申請補充數量")
    c_s2_sum.alignment = align_center
    c_s2_sum.font = font_summary
    c_s2_sum.fill = fill_summary
    c_s2_sum.border = border_summary
    for col in range(2, 4):
        ws2.cell(row=s2_sum_row, column=col).fill = fill_summary
        ws2.cell(row=s2_sum_row, column=col).border = border_summary
        
    c_qty = ws2.cell(row=s2_sum_row, column=4, value="=SUM(D5:D8)")
    c_qty.alignment = align_center
    c_qty.font = font_summary
    c_qty.fill = fill_summary
    c_qty.border = border_summary
    
    ws2.merge_cells(f"E{s2_sum_row}:I{s2_sum_row}")
    c_sum_txt = ws2.cell(row=s2_sum_row, column=5, value="14 Hạng mục thiết bị & linh kiện (Bao gồm 11 món gửi bảo hành + 3 viên pin cấp mới thay thế)")
    c_sum_txt.alignment = align_left
    c_sum_txt.font = font_summary
    c_sum_txt.fill = fill_summary
    c_sum_txt.border = border_summary
    for col in range(6, 10):
        ws2.cell(row=s2_sum_row, column=col).fill = fill_summary
        ws2.cell(row=s2_sum_row, column=col).border = border_summary
        
    # Khối ghi chú & Chữ ký phía dưới
    note_start = s2_sum_row + 2
    ws2.merge_cells(f"A{note_start}:I{note_start}")
    ws2.cell(row=note_start, column=1, value="* Ghi chú quan trọng cho bộ phận Thu mua & Tài chính (Jessica - 碧娟):").font = Font(name=FONT_FAMILY, size=10, bold=True, color="002060")
    
    notes = [
        "1. Theo phản hồi từ nhóm hiện trường và Sếp Trương (Jenson), các máy tính bảng HT10 hiện tại bị lỗi mất mạng và 3 viên pin đi kèm đã bị phồng nghiêm trọng (电池鼓包), không thể gửi kèm theo đường hàng không/chuyển phát nhanh.",
        "2. Đề nghị nhà máy Đài Loan (達方 / AMobile) chuẩn bị sẵn 3 thân máy HT10 mới, 3 viên pin mới nguyên seal và 4 đế sạc mới để đổi bù bảo hành.",
        "3. Mã HS Code đã được tra cứu chuẩn xác theo Biểu thuế XNK Việt Nam (Máy tính bảng: 8471.30.20, Pin: 8507.60.90, Đế sạc & Adapter: 8504.40.19) để tiện làm thủ tục thông quan nhập khẩu."
    ]
    for n_idx, n_text in enumerate(notes, start=note_start+1):
        ws2.merge_cells(f"A{n_idx}:I{n_idx}")
        c_n = ws2.cell(row=n_idx, column=1, value=n_text)
        c_n.font = Font(name=FONT_FAMILY, size=9.5, italic=True, color="555555")
        ws2.row_dimensions[n_idx].height = 20

    # Khối chữ ký xác nhận
    sig_row = note_start + 5
    ws2.row_dimensions[sig_row].height = 20
    ws2.cell(row=sig_row, column=2, value="NGƯỜI LẬP BIỂU / 填表人").font = font_summary
    ws2.cell(row=sig_row, column=2).alignment = align_center
    ws2.cell(row=sig_row, column=6, value="PHÊ DUYỆT / 主管審批").font = font_summary
    ws2.cell(row=sig_row, column=6).alignment = align_center
    ws2.cell(row=sig_row, column=8, value="ĐẠI DIỆN ĐÀI LOAN / 台灣對接").font = font_summary
    ws2.cell(row=sig_row, column=8).alignment = align_center
    
    ws2.row_dimensions[sig_row+1].height = 18
    ws2.cell(row=sig_row+1, column=2, value="(Ký & ghi rõ họ tên)").font = font_meta
    ws2.cell(row=sig_row+1, column=2).alignment = align_center
    ws2.cell(row=sig_row+1, column=6, value="(Ký & ghi rõ họ tên)").font = font_meta
    ws2.cell(row=sig_row+1, column=6).alignment = align_center
    ws2.cell(row=sig_row+1, column=8, value="(Ký & ghi rõ họ tên)").font = font_meta
    ws2.cell(row=sig_row+1, column=8).alignment = align_center
    
    ws2.row_dimensions[sig_row+4].height = 20
    ws2.cell(row=sig_row+4, column=2, value="Nguyễn Sỹ Kim Bằng\n(PM Hong Ming)").font = font_data_bold
    ws2.cell(row=sig_row+4, column=2).alignment = align_center
    ws2.cell(row=sig_row+4, column=6, value="Jenson (Trương Tổng)\n(CEO / General Director)").font = font_data_bold
    ws2.cell(row=sig_row+4, column=6).alignment = align_center
    ws2.cell(row=sig_row+4, column=8, value="Jessica (碧娟)\n(台灣採購部&財務部主管)").font = font_data_bold
    ws2.cell(row=sig_row+4, column=8).alignment = align_center

    ws2.freeze_panes = "A5"
    ws2.print_area = f"A1:I{sig_row+5}"
    ws2.page_setup.orientation = ws2.ORIENTATION_LANDSCAPE
    ws2.page_setup.paperSize = ws2.PAPERSIZE_A4
    ws2.sheet_properties.pageSetUpPr.fitToPage = True
    ws2.page_setup.fitToWidth = 1
    ws2.page_setup.fitToHeight = 0

    # Lưu file
    wb.save(out_path)
    print(f"Workbook successfully saved to: {out_path}")

if __name__ == "__main__":
    from datetime import datetime
    target_dir = r"E:\Working\Ho So Du An\Cong Ty\DFV_Darfon\Thiet Bi"
    os.makedirs(target_dir, exist_ok=True)
    if not os.path.isdir(IMG_DIR):
        raise FileNotFoundError("Thiếu thư mục ảnh nguồn: " + IMG_DIR)
    output = os.path.join(target_dir, "Danh_Sach_Thiet_Bi_Sua_Chua_DFV_Darfon_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".xlsx")
    try:
        build_excel(output)
    except PermissionError:
        build_excel(output[:-5] + "_v2.xlsx")
