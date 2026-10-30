# -*- coding: utf-8 -*-
r"""
Script tạo Biên bản nghiệm thu thiết bị sau sửa chữa cho CX Technology (VN)
Dựa trên form mẫu: C:\Users\BANG\Downloads\Biên Bản Nghiệm Thu_維修設備驗收記錄_HDSC-HMV06032026001.xlsx
Đổ dữ liệu từ: C:\Users\BANG\Downloads\CX Technology貨物交接單,貨物價值為13,700,000越南盾(VND) (1).xlsx

Đặc điểm cập nhật chuẩn 100%:
1. Cố định 5 hàng đầu tiên không di chuyển (Freeze Panes A6) cho sheet Nghiệm Thu.
2. Bỏ rìa ngoài bảng: thiết lập PageBreakPreview chuẩn, không hiển thị gridlines ngoài vùng in.
3. Các khung ảnh đều nhau chính xác (độ rộng các cột ảnh bằng nhau 100%).
4. Liên kết 2 chiều (Hyperlink) giữa bảng tổng hợp và 6 sheet chi tiết.
5. Ô vàng chèn ảnh sạch sẽ sẵn sàng chèn ảnh (Insert -> Pictures -> Place in Cell).
"""

import os
import sys
import shutil
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties

# Locate the project independently of the drive letter on this computer.
_WORKSPACE_ROOT = next((p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'pm_portal' / 'app').is_dir()), __import__('pathlib').Path.cwd())
def _workspace_path(relative):
    return str(_WORKSPACE_ROOT / relative.replace(chr(92), '/'))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 6 thiết bị từ file giao nhận của CX Technology
DEVICES_DATA = [
    {
        "stt": 1,
        "serial": "RFR900NA55RSWLBA574",
        "loi": "Cò bắn không nhả\n扳機扣住不鬆",
        "bo_phan": "CNC",
        "hang_muc": "Kiểm tra cò bắn & chức năng quét trigger scan\n檢查扳機及掃描功能",
        "ket_qua": "Đạt / 合格",
        "xu_ly": "No error founds\n(Không phát hiện lỗi phát sinh)",
        "type": "RF"
    },
    {
        "stt": 2,
        "serial": "EF550RA4LAWBHI677",
        "loi": "Màn hình lỗi\n螢幕故障",
        "bo_phan": "CNC",
        "hang_muc": "Kiểm tra hiển thị màn hình & đầu quét barcode\n檢查螢幕顯示及條碼掃描功能",
        "ket_qua": "Đạt / 合格",
        "xu_ly": "Barcode\n(Xử lý & thay cụm Barcode)",
        "type": "EF"
    },
    {
        "stt": 3,
        "serial": "RFR900NA55RSWLBA565",
        "loi": "Cò bắn không nhả\n扳機扣住不鬆",
        "bo_phan": "CNC",
        "hang_muc": "Kiểm tra cò bắn & gá chuyển đổi Mounting Adapter\n檢查扳機及轉接支架功能",
        "ket_qua": "Đạt / 合格",
        "xu_ly": "Mounting Adapter\n(Thay thế Mounting Adapter)",
        "type": "RF"
    },
    {
        "stt": 4,
        "serial": "EF550RA4LAWBHI641",
        "loi": "Cò bắn & Sạc không vô điện\n扳機故障及無法充電",
        "bo_phan": "Xi treo\n吊鍍",
        "hang_muc": "Kiểm tra cò bắn & chức năng sạc pin\n檢查扳機及電池充電功能",
        "ket_qua": "Đạt / 合格",
        "xu_ly": "No error founds\n(Không phát hiện lỗi phát sinh)",
        "type": "EF"
    },
    {
        "stt": 5,
        "serial": "EF550RA4LAWBHI657",
        "loi": "Cò bắn & Sạc không vô điện\n扳機故障及無法充電",
        "bo_phan": "Xi treo\n吊鍍",
        "hang_muc": "Kiểm tra cò bắn & chức năng sạc pin\n檢查扳機及電池充電功能",
        "ket_qua": "Đạt / 合格",
        "xu_ly": "No error founds\n(Không phát hiện lỗi phát sinh)",
        "type": "EF"
    },
    {
        "stt": 6,
        "serial": "EF550RA4LAWBHI650",
        "loi": "Cò bắn & Sạc không vô điện\n扳機故障及無法充電",
        "bo_phan": "Xi treo\n吊鍍",
        "hang_muc": "Kiểm tra cò bắn & chức năng sạc pin\n檢查扳機及電池充電功能",
        "ket_qua": "Đạt / 合格",
        "xu_ly": "No error founds\n(Không phát hiện lỗi phát sinh)",
        "type": "EF"
    }
]

CONTRACT_NO = "HM-FINEPRO-20261009.001"
ACCEPTANCE_DATE = "09/10/2026"
REPORT_NO = "001/2026/BBNT-SC"

FONT_FAMILY = "Times New Roman"

# Fonts
FONT_TITLE_1 = Font(name=FONT_FAMILY, size=14, bold=True, color="FFFFFFFF")
FONT_TITLE_2 = Font(name=FONT_FAMILY, size=13, bold=True, color="FFFFFFFF")
FONT_HDR_INFO = Font(name=FONT_FAMILY, size=12, bold=True, color="FF1F4E79")
FONT_PARTY_INFO = Font(name=FONT_FAMILY, size=14, bold=False, color="FF000000")
FONT_TABLE_HDR = Font(name=FONT_FAMILY, size=12, bold=True, color="FFFFFFFF")

FONT_DATA_STT = Font(name=FONT_FAMILY, size=12, bold=True, color="FF000000")
FONT_DATA_TEXT = Font(name=FONT_FAMILY, size=11, bold=False, color="FF000000")
FONT_DATA_RESULT = Font(name=FONT_FAMILY, size=12, bold=True, color="FF375623")
FONT_DATA_LINK = Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79")

FONT_NOTE_HDR = Font(name=FONT_FAMILY, size=14, bold=True, color="FF1F4E79")
FONT_NOTE_BODY = Font(name=FONT_FAMILY, size=12, bold=False, color="FF000000")
FONT_SIG = Font(name=FONT_FAMILY, size=12, bold=True, color="FF1F4E79")

# Detail sheet fonts
FONT_DET_TITLE = Font(name=FONT_FAMILY, size=13, bold=True, color="FFFFFFFF")
FONT_DET_SUB1 = Font(name=FONT_FAMILY, size=12, bold=True, color="FF1F4E79")
FONT_DET_SUB2 = Font(name=FONT_FAMILY, size=12, bold=False, color="FF000000")
FONT_DET_GUIDE = Font(name=FONT_FAMILY, size=10, bold=False, italic=True, color="FF7F7F7F")
FONT_DET_BACK = Font(name=FONT_FAMILY, size=11, bold=True, color="FF1F4E79")

# Fills
FILL_DARK_BLUE = PatternFill("solid", fgColor="FF1F4E79")
FILL_LIGHT_BLUE = PatternFill("solid", fgColor="FFD6E4F0")
FILL_LIGHT_GRAY = PatternFill("solid", fgColor="FFF2F2F2")
FILL_HEADER_BLUE = PatternFill("solid", fgColor="FF2E75B6")
FILL_WHITE = PatternFill("solid", fgColor="FFFFFFFF")
FILL_GREEN_PASS = PatternFill("solid", fgColor="FFE2EFDA")
FILL_YELLOW_IMG = PatternFill("solid", fgColor="FFFFF2CC")

# Borders
BORDER_THIN_BLACK = Border(
    left=Side(style='thin', color='FF000000'),
    right=Side(style='thin', color='FF000000'),
    top=Side(style='thin', color='FF000000'),
    bottom=Side(style='thin', color='FF000000')
)

def apply_range_style(ws, min_col, min_row, max_col, max_row, font=None, fill=None, border=None, alignment=None):
    for r in range(min_row, max_row + 1):
        for c in range(min_col, max_col + 1):
            cell = ws.cell(r, c)
            if font:
                cell.font = font
            if fill:
                cell.fill = fill
            if border is not None:
                cell.border = border
            if alignment:
                cell.alignment = alignment

def build_summary_sheet(ws):
    ws.title = "Nghiệm Thu"
    ws.sheet_format.defaultRowHeight = 14.4
    
    # 1. Cố định 5 hàng đầu tiên không di chuyển (Freeze Panes A6)
    ws.freeze_panes = 'A6'
    
    # 2. Chế độ PageBreakPreview & Zoom 85% đúng chuẩn mẫu gốc
    ws.views.sheetView[0].view = "pageBreakPreview"
    ws.views.sheetView[0].zoomScale = 85
    ws.views.sheetView[0].zoomScaleNormal = 100
    ws.views.sheetView[0].zoomScaleSheetLayoutView = 85
    # Không bật showGridLines để ngoài bảng là màu xám thuần không bị rìa lưới
    ws.views.sheetView[0].showGridLines = None

    # Kích thước cột chuẩn mẫu gốc
    widths = {
        'A': 6.0,
        'B': 28.0,
        'C': 36.33,
        'D': 14.0,
        'E': 32.0,
        'F': 14.0,
        'G': 35.11
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # Row 1: Tiêu đề Tiếng Việt
    ws.row_dimensions[1].height = 30.0
    ws.merge_cells('A1:G1')
    apply_range_style(ws, 1, 1, 7, 1, font=FONT_TITLE_1, fill=FILL_DARK_BLUE, 
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A1'].value = "BIÊN BẢN KIỂM TRA & NGHIỆM THU THIẾT BỊ SAU SỬA CHỮA"

    # Row 2: Tiêu đề Tiếng Trung
    ws.row_dimensions[2].height = 24.0
    ws.merge_cells('A2:G2')
    apply_range_style(ws, 1, 2, 7, 2, font=FONT_TITLE_2, fill=FILL_DARK_BLUE, 
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A2'].value = "維修設備檢查及驗收記錄"

    # Row 3: Hợp đồng và Ngày tháng (Không có viền ngoài)
    ws.row_dimensions[3].height = 31.5
    ws.merge_cells('A3:D3')
    ws.merge_cells('E3:G3')
    apply_range_style(ws, 1, 3, 4, 3, font=FONT_HDR_INFO, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    apply_range_style(ws, 5, 3, 7, 3, font=FONT_HDR_INFO, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    ws['A3'].value = f"Số HĐ / 合約編號: {CONTRACT_NO}"
    ws['E3'].value = f"Ngày / 日期: {ACCEPTANCE_DATE}          Số BB: {REPORT_NO}"

    # Row 4: Bên A và Bên B (Không có viền ngoài)
    ws.row_dimensions[4].height = 42.0
    ws.merge_cells('A4:D4')
    ws.merge_cells('E4:G4')
    apply_range_style(ws, 1, 4, 4, 4, font=FONT_PARTY_INFO, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    apply_range_style(ws, 5, 4, 7, 4, font=FONT_PARTY_INFO, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    ws['A4'].value = "Bên A / 甲方: CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)"
    ws['E4'].value = "Bên B / 乙方: CÔNG TY TNHH TOÀN CẦU HONG MING"

    # Row 5: Table Header (Bắt đầu có viền bảng chuẩn thin)
    ws.row_dimensions[5].height = 38.1
    headers = [
        "STT\n序號",
        "Serial Number\n產品序號",
        "Lỗi ban đầu\n故障說明",
        "Bộ phận\n部門",
        "Hạng mục kiểm tra\n檢查項目",
        "Kết quả\n結果",
        "Sheet hình ảnh\n圖片工作表"
    ]
    for idx, hdr in enumerate(headers, start=1):
        cell = ws.cell(5, idx)
        cell.value = hdr
        cell.font = FONT_TABLE_HDR
        cell.fill = FILL_HEADER_BLUE
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER_THIN_BLACK

    # Rows 6..11: Data rows
    for i, dev in enumerate(DEVICES_DATA, start=6):
        ws.row_dimensions[i].height = 48.75
        bg_fill = FILL_WHITE if (i % 2 == 0) else FILL_LIGHT_GRAY
        
        # Col 1: STT
        c1 = ws.cell(i, 1, str(dev["stt"]))
        c1.font = FONT_DATA_STT
        c1.fill = bg_fill
        c1.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c1.border = BORDER_THIN_BLACK
        
        # Col 2: Serial
        c2 = ws.cell(i, 2, dev["serial"])
        c2.font = FONT_DATA_TEXT
        c2.fill = bg_fill
        c2.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c2.border = BORDER_THIN_BLACK

        # Col 3: Lỗi ban đầu
        c3 = ws.cell(i, 3, dev["loi"])
        c3.font = FONT_DATA_TEXT
        c3.fill = bg_fill
        c3.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        c3.border = BORDER_THIN_BLACK

        # Col 4: Bộ phận
        c4 = ws.cell(i, 4, dev["bo_phan"])
        c4.font = FONT_DATA_TEXT
        c4.fill = bg_fill
        c4.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c4.border = BORDER_THIN_BLACK

        # Col 5: Hạng mục kiểm tra
        c5 = ws.cell(i, 5, dev["hang_muc"])
        c5.font = FONT_DATA_TEXT
        c5.fill = bg_fill
        c5.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        c5.border = BORDER_THIN_BLACK

        # Col 6: Kết quả (Green Pass)
        c6 = ws.cell(i, 6, dev["ket_qua"])
        c6.font = FONT_DATA_RESULT
        c6.fill = FILL_GREEN_PASS
        c6.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c6.border = BORDER_THIN_BLACK

        # Col 7: Sheet hình ảnh link
        sheet_target = dev["serial"]
        c7 = ws.cell(i, 7, f"→ {sheet_target}")
        c7.font = FONT_DATA_LINK
        c7.fill = FILL_LIGHT_BLUE
        c7.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        c7.border = BORDER_THIN_BLACK
        c7.hyperlink = f"#'{sheet_target}'!A1"

    # Row 12: Tiêu đề Ghi chú (Không có viền)
    ws.row_dimensions[12].height = 36.0
    ws.merge_cells('A12:G12')
    apply_range_style(
        ws, 1, 12, 7, 12,
        font=FONT_NOTE_HDR,
        fill=FILL_WHITE,
        alignment=Alignment(horizontal='left', vertical='center', wrap_text=True),
    )
    ws['A12'].value = "GHI CHÚ / 備註:"

    # Row 13: Phần ghi chú để trống hoàn toàn theo yêu cầu (Không ghi giá tiền)
    ws.row_dimensions[13].height = 81.0
    ws.merge_cells('A13:G13')
    apply_range_style(
        ws, 1, 13, 7, 13,
        font=Font(name=FONT_FAMILY, size=14, bold=False, color="FF000000"),
        fill=FILL_WHITE,
        alignment=Alignment(horizontal='left', vertical='top', wrap_text=True),
    )
    ws['A13'].value = None

    # Row 14: Dòng đệm trắng, không lộ lưới ô.
    apply_range_style(ws, 1, 14, 7, 14, fill=FILL_WHITE)
    # Row 15: Chữ ký 2 bên (Không có viền)
    ws.row_dimensions[15].height = 107.25
    ws.merge_cells('A15:C15')
    ws.merge_cells('E15:G15')
    apply_range_style(ws, 1, 15, 7, 15, fill=FILL_WHITE)
    
    ws['A15'].value = "ĐẠI DIỆN BÊN A / 甲方代表\n(Ký xác nhận / 簽字確認)\n\n\nCÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)"
    ws['A15'].font = FONT_SIG
    ws['A15'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    ws['E15'].value = "ĐẠI DIỆN BÊN B / 乙方代表\n(Ký tên, đóng dấu / 簽字蓋章)\n\n\nCÔNG TY TNHH TOÀN CẦU HONG MING"
    ws['E15'].font = FONT_SIG
    ws['E15'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Page setup chuẩn xác A4 dọc - Scale 52% vừa khít 1 trang duy nhất, KHÔNG có đường xanh đứt đoạn chia trang
    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.scale = 52
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    # Giữ phần trắng cuối trang đến hàng 30 giống hệt mẫu gốc.
    apply_range_style(ws, 1, 16, 7, 30, fill=FILL_WHITE)
    ws.print_area = "A1:G30"

def build_detail_sheet(ws, dev):
    sname = dev["serial"]
    ws.title = sname
    ws.sheet_format.defaultRowHeight = 14.4
    
    dev_type = dev["type"]
    
    # Thiết lập kích thước khung ảnh lớn chuẩn 1:1 theo mẫu gốc
    if dev_type == "RF":
        # Dòng RF: 3 khung ảnh lớn đều nhau (width = 34.44), Cột D Ghi chú (width = 25.33)
        max_col = 4
        col_letters = ['A', 'B', 'C', 'D']
        ws.column_dimensions['A'].width = 34.44
        ws.column_dimensions['B'].width = 34.44
        ws.column_dimensions['C'].width = 34.44
        ws.column_dimensions['D'].width = 25.33
        headers = ["Hình 1 / 圖片1", "Hình 2 / 圖片2", "Hình 3 / 圖片3", "Ghi chú / 備註"]
        img_cols = ['A', 'B', 'C']
        note_col = 'D'
    else:
        # Dòng EF: 5 khung ảnh lớn đều nhau (width = 37.11), Cột F Ghi chú (width = 14.0)
        max_col = 6
        col_letters = ['A', 'B', 'C', 'D', 'E', 'F']
        ws.column_dimensions['A'].width = 37.11
        ws.column_dimensions['B'].width = 37.11
        ws.column_dimensions['C'].width = 37.11
        ws.column_dimensions['D'].width = 37.11
        ws.column_dimensions['E'].width = 37.11
        ws.column_dimensions['F'].width = 14.0
        headers = ["Hình 1 / 圖片1", "Hình 2 / 圖片2", "Hình 3 / 圖片3", "Hình 4 / 圖片4", "Hình 5 / 圖片5", "Ghi chú / 備註"]
        img_cols = ['A', 'B', 'C', 'D', 'E']
        note_col = 'F'

    end_col_letter = col_letters[-1]

    # Row 1: Header ảnh (Không viền ngoài)
    ws.row_dimensions[1].height = 27.9
    ws.merge_cells(f"A1:{end_col_letter}1")
    apply_range_style(ws, 1, 1, max_col, 1, font=FONT_DET_TITLE, fill=FILL_DARK_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A1'].value = f"HÌNH ẢNH KIỂM TRA / 檢查圖片 — {dev['serial']}"

    # Row 2: STT, Bộ phận, Kết quả (Không viền ngoài)
    ws.row_dimensions[2].height = 18.0
    ws.merge_cells(f"A2:{end_col_letter}2")
    apply_range_style(ws, 1, 2, max_col, 2, font=FONT_DET_SUB1, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    bp_clean = dev['bo_phan'].replace('\n', ' / ')
    ws['A2'].value = f"STT: {dev['stt']}    |    Bộ phận / 部門: {bp_clean}    |    Kết quả / 結果: {dev['ket_qua']}"

    # Row 3: Lỗi ban đầu (Không viền ngoài)
    ws.row_dimensions[3].height = 18.0
    ws.merge_cells(f"A3:{end_col_letter}3")
    apply_range_style(ws, 1, 3, max_col, 3, font=FONT_DET_SUB2, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    loi_clean = dev['loi'].replace('\n', ' / ')
    ws['A3'].value = f"Lỗi ban đầu / 故障說明: {loi_clean}"

    # Row 4: Hạng mục kiểm tra (Không viền ngoài)
    ws.row_dimensions[4].height = 18.0
    ws.merge_cells(f"A4:{end_col_letter}4")
    apply_range_style(ws, 1, 4, max_col, 4, font=FONT_DET_SUB2, fill=FILL_LIGHT_GRAY,
                      alignment=Alignment(horizontal='left', vertical='center', wrap_text=True))
    hm_clean = dev['hang_muc'].replace('\n', ' / ')
    ws['A4'].value = f"Hạng mục KT / 檢查項目: {hm_clean}"

    # Row 5: Tiêu đề cột ảnh (Viền thin chuẩn)
    ws.row_dimensions[5].height = 30.0
    for idx, hdr in enumerate(headers, start=1):
        cell = ws.cell(5, idx)
        cell.value = hdr
        cell.font = FONT_TABLE_HDR
        cell.fill = FILL_HEADER_BLUE
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER_THIN_BLACK

    # Row 6: Ô màu vàng chờ chèn ảnh + Ghi chú (Chiều cao và viền đều nhau chuẩn 1:1)
    row6_h = 284.25
    ws.row_dimensions[6].height = row6_h

    # Khung ảnh màu vàng #FFFFF2CC viền thin đen chuẩn mẫu gốc
    for c_letter in img_cols:
        cell = ws[f"{c_letter}6"]
        cell.value = None
        cell.fill = FILL_YELLOW_IMG
        cell.border = BORDER_THIN_BLACK
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Ô ghi chú của sheet ảnh luôn để trống theo mẫu chuẩn.
    cell_note = ws[f"{note_col}6"]
    cell_note.value = None
    cell_note.fill = FILL_WHITE
    cell_note.border = BORDER_THIN_BLACK
    cell_note.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Row 7: Hướng dẫn chèn ảnh (Không viền)
    ws.row_dimensions[7].height = 14.1
    ws.merge_cells(f"A7:{end_col_letter}7")
    apply_range_style(ws, 1, 7, max_col, 7, font=FONT_DET_GUIDE, fill=None,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True))
    ws['A7'].value = "⬆  Chèn hình ảnh vào ô màu vàng: Insert → Pictures → Place in Cell  /  請將圖片插入黃色儲存格"

    # Row 8: Nút quay về kèm Hyperlink (Không có viền ngoài giống mẫu gốc)
    ws.row_dimensions[8].height = 15.9
    ws.merge_cells(f"A8:{end_col_letter}8")
    apply_range_style(ws, 1, 8, max_col, 8, font=FONT_DET_BACK, fill=FILL_LIGHT_BLUE,
                      alignment=Alignment(horizontal='center', vertical='center', wrap_text=True),
                      border=None)
    ws['A8'].value = '← Quay về bảng tổng hợp "Nghiệm Thu" / 返回總表'
    ws['A8'].hyperlink = "#'Nghiệm Thu'!A1"

    # Page setup
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins = PageMargins(
        left=0.4,
        right=0.4,
        top=0.4,
        bottom=0.4,
        header=0.2,
        footer=0.2,
    )

def generate_acceptance_file():
    print("=" * 60)
    print("Bắt đầu tạo Biên bản nghiệm thu thiết bị CX Technology (Bản chuẩn 1:1)...")
    
    wb = openpyxl.Workbook()
    
    # 1. Sheet Nghiệm Thu
    ws_summary = wb.active
    build_summary_sheet(ws_summary)
    print("✓ Đã khởi tạo Sheet 'Nghiệm Thu' (Freeze panes A6, PageBreakPreview chuẩn, bỏ rìa ngoài).")

    # 2. Tạo 6 Sheet chi tiết hình ảnh với khung ảnh đều nhau 100%
    for dev in DEVICES_DATA:
        ws_det = wb.create_sheet()
        build_detail_sheet(ws_det, dev)
        print(f"✓ Đã tạo Sheet chi tiết '{dev['serial']}' (Khung ảnh đều nhau 100%, độ rộng cố định).")

    # Đường dẫn xuất file
    downloads_dir = str(__import__('pathlib').Path.home() / 'Downloads')
    output_filename = f"Biên Bản Nghiệm Thu_維修設備驗收記錄_{CONTRACT_NO}.xlsx"
    out_path_downloads = os.path.join(downloads_dir, output_filename)
    out_path_working = os.path.join(_workspace_path(''), output_filename)

    # Lưu file trước sang Workspace
    wb.save(out_path_working)
    print(f"\n✓ Đã lưu thành công vào Workspace: {out_path_working}")

    # Cố gắng lưu đè vào Downloads
    try:
        wb.save(out_path_downloads)
        print(f"✓ Đã lưu thành công vào Downloads: {out_path_downloads}")
    except PermissionError:
        out_path_v2 = os.path.join(downloads_dir, f"Biên Bản Nghiệm Thu_維修設備驗收記錄_{CONTRACT_NO}_v2.xlsx")
        wb.save(out_path_v2)
        print(f"⚠️ Lưu ý: File '{output_filename}' đang được mở trong Excel.")
        print(f"✓ Đã lưu bản cập nhật mới vào: {out_path_v2}")
        print("  (Vui lòng đóng file cũ trong Excel nếu muốn lưu đúng tên gốc)")

    print("=" * 60)
    print("HOÀN TẤT THÀNH CÔNG!")
    return out_path_downloads

if __name__ == "__main__":
    generate_acceptance_file()
