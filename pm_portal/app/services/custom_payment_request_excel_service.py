# -*- coding: utf-8 -*-
"""
Generator for Payment Request Excel files (請款單) from extracted document data.
Automatically picks the right sheet template (CX, 712TR, chengfeng, VONMAX...)
based on the customer name and contract details, ensuring 100% layout fidelity.
"""

import os
import re
import openpyxl
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.config import WORKING_DIR

TEMPLATE_PATH = WORKING_DIR / "Bieu Mau" / "đơn yêu cầu NCC thanh toán-Gốc.xlsx"
OUTPUT_DIR = WORKING_DIR / "Ho So Du An" / "Yeu Cau Thanh Toan"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _safe_filename(text: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", str(text or "")).strip()
    return cleaned or "Document"


def generate_payment_request_from_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an official bilingual payment request Excel file from extracted data.
    Chooses the appropriate template sheet (CX for CX Technology, or 712TR / chengfeng).
    """
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file mẫu tại: {TEMPLATE_PATH}")

    wb = openpyxl.load_workbook(str(TEMPLATE_PATH), data_only=False)

    cust_vi = str(data.get("customer_name_vi") or "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)").strip()
    c_code = str(data.get("contract_code") or "HMV151020250001").strip()
    proj_vi = str(data.get("project_name_vi") or "Dự án hệ thống RFID").strip()
    proj_zh = str(data.get("project_name_zh") or "").strip()
    ms_title = str(data.get("milestone_name") or "驗收合格尾款：20%").strip()
    pct = float(data.get("milestone_percentage") or 20.0)
    total_amt = float(data.get("total_contract_amount") or 234000000.0)
    req_amt = float(data.get("payment_amount") or (total_amt * pct / 100.0))
    app_date = str(data.get("request_date") or datetime.now().strftime("%d/%m/%Y")).strip()
    due_date = str(data.get("due_date") or "31/10/2026").strip()
    remarks = str(data.get("payment_terms_summary") or "").strip()

    # Chọn sheet phù hợp
    is_cx = "cx" in cust_vi.lower()
    is_cf = "cheng" in cust_vi.lower() or "feng" in cust_vi.lower()
    is_vonmax = "vonmax" in cust_vi.lower()

    if is_cx and "CX" in wb.sheetnames:
        sheet_name = "CX"
    elif is_cf and "chengfeng" in wb.sheetnames:
        sheet_name = "chengfeng"
    elif is_vonmax and "VONMAX" in wb.sheetnames:
        sheet_name = "VONMAX"
    elif "712TR" in wb.sheetnames:
        sheet_name = "712TR"
    else:
        sheet_name = wb.sheetnames[0]

    ws = wb[sheet_name]

    # Form NO: HM + ddmmyyyy + -001
    now_clean = datetime.now().strftime("%d%m%Y")
    form_no = f"HM{now_clean}-001"
    if ws["H9"]:
        ws["H9"].value = form_no

    # C10: Tên khách hàng
    if ws["C10"]:
        ws["C10"].value = cust_vi

    # I10: Ngày nộp đơn
    if ws["I10"]:
        ws["I10"].value = app_date
        ws["I10"].number_format = "@"

    # C11: Tên dự án & căn cứ hợp đồng
    project_text = (
        f"Căn cứ hợp đồng số : {c_code}\n"
        f"{proj_vi}\n"
        f"根据合同编号：{c_code}\n"
        f"{proj_zh or proj_vi}"
    )
    if ws["C11"]:
        ws["C11"].value = project_text

    # C12: Ngày đến hạn thanh toán
    if ws["C12"]:
        ws["C12"].value = due_date
        ws["C12"].number_format = "@"

    # Row 15: Hạng mục thanh toán đợt này
    ws["A15"].value = 1
    pct_str = f"{pct:.0f}%" if pct.is_integer() else f"{pct}%"
    item_desc = f"{ms_title}\n合約：{c_code}"
    ws["B15"].value = item_desc
    ws["C15"].value = "VND"
    ws["D15"].value = int(total_amt)
    ws["E15"].value = 1
    ws["F15"].value = "=D15*E15"
    ws["G15"].value = None
    ws["H15"].value = "=F15*G15"
    ws["I15"].value = f"=(F15+H15)*{pct_str}"

    # Row 21: Tổng cộng
    ws["F21"].value = "=SUM(I15:I20)"

    # Row 23: Ghi chú điều khoản thanh toán
    if remarks:
        full_remark = f"備註：{remarks}\n\n**以上價格不包含VAT增值稅，稅率依發票開立時的稅率為準。Giá nêu trên chưa bao gồm thuế GTGT (VAT). Thuế suất áp dụng theo mức thuế suất tại thời điểm xuất hóa đơn.\n"
        ws["B23"].value = full_remark

    # Xóa các sheet khác để bảo mật thông tin các đối tác khác
    for s in list(wb.sheetnames):
        if s != sheet_name:
            del wb[s]
    ws.title = f"請款單_{_safe_filename(cust_vi)[:12]}"

    # Lưu file
    safe_cust = _safe_filename(cust_vi)[:30]
    file_name = f"{form_no}_Phiếu_Yêu_Cầu_Thanh_Toán_{safe_cust}_{c_code}.xlsx"
    out_path = OUTPUT_DIR / file_name

    try:
        wb.save(str(out_path))
    except PermissionError:
        file_name = f"{form_no}_Phiếu_Yêu_Cầu_Thanh_Toán_{safe_cust}_{c_code}_v2.xlsx"
        out_path = OUTPUT_DIR / file_name
        wb.save(str(out_path))

    # Lưu thêm 1 bản dự phòng trong thư mục Downloads của người dùng nếu có thể
    user_downloads = Path.home() / "Downloads"
    if user_downloads.exists():
        try:
            import shutil
            shutil.copy2(str(out_path), str(user_downloads / file_name))
        except Exception:
            pass

    return {
        "status": "success",
        "file_name": file_name,
        "file_path": str(out_path),
        "download_url": f"/api/v1/payment-requests/download-custom/{file_name}",
        "customer_name": cust_vi,
        "contract_code": c_code,
        "milestone_name": ms_title,
        "amount": req_amt,
        "total_amount": total_amt,
        "due_date": due_date,
        "form_no": form_no
    }
