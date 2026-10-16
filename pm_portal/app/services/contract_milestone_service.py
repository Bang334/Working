# -*- coding: utf-8 -*-
"""
Service: contract_milestone_service.py
Quản lý danh sách hợp đồng đang lưu và theo dõi chi tiết các mốc thời hạn thanh toán (AR Milestones).
Đọc trực tiếp từ file DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx và biểu mẫu lưu trữ của công ty.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import openpyxl

from app.config import WORKING_DIR

TRACKER_EXCEL_PATH = WORKING_DIR / "DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx"
TEMPLATE_EXCEL_PATH = WORKING_DIR / "Bieu Mau" / "đơn yêu cầu NCC thanh toán-Gốc.xlsx"
GENERATED_CX_EXCEL = WORKING_DIR / "đơn yêu cầu thanh toán - CX Technology - HMV151020250001.xlsx"

SIMULATED_TODAY = datetime(2026, 10, 15)


def parse_date_str(date_val: Any) -> Optional[datetime]:
    """Parse various date representations into a datetime object."""
    if isinstance(date_val, datetime):
        return date_val
    if not date_val:
        return None
    date_str = str(date_val).strip()
    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def calculate_days_left(due_date_str: str) -> Optional[int]:
    """Calculate days remaining from SIMULATED_TODAY to due_date."""
    due = parse_date_str(due_date_str)
    if not due:
        return None
    delta = (due.date() - SIMULATED_TODAY.date()).days
    return delta


def get_all_saved_contracts_with_milestones() -> List[Dict[str, Any]]:
    """Retrieve all saved contracts and their detailed payment milestones."""
    contracts: List[Dict[str, Any]] = []

    # 1. Try reading from DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx
    if TRACKER_EXCEL_PATH.exists():
        try:
            wb = openpyxl.load_workbook(str(TRACKER_EXCEL_PATH), data_only=True)
            
            # Map overview data
            overview_map = {}
            if "Tổng Quan Dự Án 專案總覽" in wb.sheetnames:
                ws_ov = wb["Tổng Quan Dự Án 專案總覽"]
                for r in range(4, ws_ov.max_row + 1):
                    c_code = ws_ov.cell(r, 1).value
                    if c_code:
                        c_code = str(c_code).strip()
                        overview_map[c_code] = {
                            "so_hop_dong": c_code,
                            "khach_hang_vi": str(ws_ov.cell(r, 2).value or "").strip(),
                            "ten_du_an_vi": str(ws_ov.cell(r, 3).value or "").strip(),
                            "ky_thuat": str(ws_ov.cell(r, 4).value or "").strip(),
                            "ngay_ky": str(ws_ov.cell(r, 5).value or "").strip(),
                            "tong_gia_tri": ws_ov.cell(r, 6).value or 0,
                            "da_thu": ws_ov.cell(r, 7).value or 0,
                            "trang_thai_du_an": str(ws_ov.cell(r, 10).value or "").strip(),
                            "ghi_chu": str(ws_ov.cell(r, 11).value or "").strip(),
                        }

            # Map milestones
            milestones_map: Dict[str, List[Dict[str, Any]]] = {}
            if "Đợt Thanh Toán 款項明細" in wb.sheetnames:
                ws_ms = wb["Đợt Thanh Toán 款項明細"]
                for r in range(4, ws_ms.max_row + 1):
                    c_code = ws_ms.cell(r, 1).value
                    if c_code:
                        c_code = str(c_code).strip()
                        khach = str(ws_ms.cell(r, 2).value or "").strip()
                        dot_tt = str(ws_ms.cell(r, 3).value or "").strip()
                        ty_le = str(ws_ms.cell(r, 4).value or "").strip()
                        so_tien = ws_ms.cell(r, 5).value or 0
                        dieu_kien = str(ws_ms.cell(r, 6).value or "").strip()
                        han_tt = str(ws_ms.cell(r, 7).value or "").strip()
                        hoa_don = str(ws_ms.cell(r, 8).value or "").strip()
                        tinh_trang = str(ws_ms.cell(r, 9).value or "").strip().upper()
                        hanh_dong = str(ws_ms.cell(r, 10).value or "").strip()

                        days_left = calculate_days_left(han_tt)

                        # Determine badge status
                        if tinh_trang == "ĐÃ THU ĐỦ":
                            status_code = "PAID"
                            status_label = "Đã thu đủ"
                            badge_color = "green"
                        elif tinh_trang == "CHỜ THANH TOÁN":
                            if days_left is not None and days_left <= 10:
                                status_code = "URGENT"
                                status_label = f"Sắp đến hạn (Còn {days_left} ngày)"
                                badge_color = "amber"
                            else:
                                status_code = "PAYMENT_WAIT"
                                status_label = "Chờ thanh toán"
                                badge_color = "blue"
                        elif tinh_trang == "ĐANG THI CÔNG":
                            status_code = "IN_PROGRESS"
                            status_label = "Đang thi công"
                            badge_color = "purple"
                        else:
                            status_code = "UPCOMING"
                            status_label = "Chưa đến hạn"
                            badge_color = "gray"

                        ms_obj = {
                            "so_hop_dong": c_code,
                            "khach_hang": khach,
                            "dot_thanh_toan": dot_tt,
                            "ty_le": ty_le,
                            "so_tien": so_tien,
                            "dieu_kien_kich_hoat": dieu_kien,
                            "han_thanh_toan": han_tt,
                            "days_left": days_left,
                            "hoa_don_vat": hoa_don,
                            "tinh_trang": tinh_trang,
                            "hanh_dong": hanh_dong,
                            "status_code": status_code,
                            "status_label": status_label,
                            "badge_color": badge_color,
                        }

                        if c_code not in milestones_map:
                            milestones_map[c_code] = []
                        milestones_map[c_code].append(ms_obj)

            # Build contract list
            for c_code, ov in overview_map.items():
                ms_list = milestones_map.get(c_code, [])
                
                # Metadata enhancements
                khach_vi = ov["khach_hang_vi"]
                khach_zh = "客戶公司"
                email_to = "nguyensykimbang321@gmail.com"
                email_cc = "pm02@hongming-global.com, sales@hongming-global.com"

                if "CX" in khach_vi:
                    khach_vi = "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)"
                    khach_zh = "越南CX科技股份有限公司"
                    email_to = "nguyensykimbang321@gmail.com"
                elif "Cheng Feng" in khach_vi:
                    khach_vi = "CÔNG TY TNHH CÔNG NGHỆ CHENG FENG LE HUA (VIỆT NAM)"
                    khach_zh = "晟峰樂華（越南）科技有限公司"
                    email_to = "purchasing@chengfeng-vn.com"
                elif "Vonmax" in khach_vi:
                    khach_vi = "CÔNG TY TNHH VONMAX INDUSTRIAL (VIỆT NAM)"
                    khach_zh = "弘聲精密工業（越南）有限公司"
                    email_to = "admin@vonmax.com.vn"

                # Check if there is an urgent milestone
                has_urgent = any(m["status_code"] in ("URGENT", "OVERDUE") for m in ms_list)
                has_waiting = any(m["status_code"] == "PAYMENT_WAIT" for m in ms_list)

                # Has generated request Excel file?
                has_excel_file = (c_code == "HMV151020250001" and GENERATED_CX_EXCEL.exists())
                excel_download_url = (
                    f"/api/v1/reminders/download-request-excel/{c_code}" if has_excel_file else None
                )

                contracts.append({
                    "so_hop_dong": c_code,
                    "khach_hang_vi": khach_vi,
                    "khach_hang_zh": khach_zh,
                    "email_to": email_to,
                    "email_cc": email_cc,
                    "ten_du_an_vi": ov["ten_du_an_vi"],
                    "ky_thuat": ov["ky_thuat"],
                    "ngay_ky": ov["ngay_ky"],
                    "tong_gia_tri": ov["tong_gia_tri"],
                    "da_thu": ov["da_thu"],
                    "con_lai": max(0, (ov["tong_gia_tri"] or 0) - (ov["da_thu"] or 0)),
                    "ty_le_thu": (
                        f"{int((ov['da_thu'] / ov['tong_gia_tri']) * 100)}%"
                        if ov["tong_gia_tri"] and ov["da_thu"]
                        else "0%"
                    ),
                    "trang_thai_du_an": ov["trang_thai_du_an"],
                    "ghi_chu": ov["ghi_chu"],
                    "has_urgent": has_urgent,
                    "has_waiting": has_waiting,
                    "has_excel_file": has_excel_file,
                    "excel_download_url": excel_download_url,
                    "milestones": ms_list,
                })
        except Exception as exc:
            print(f"Error reading tracker excel: {exc}")

    # 2. Add fallback or complementary contracts from historical files if needed
    if not any(c["so_hop_dong"] == "HMV060620250001" for c in contracts):
        contracts.append({
            "so_hop_dong": "HMV060620250001",
            "khach_hang_vi": "CÔNG TY TNHH VONMAX INDUSTRIAL (VIỆT NAM)",
            "khach_hang_zh": "弘聲精密工業（越南）有限公司",
            "email_to": "admin@vonmax.com.vn",
            "email_cc": "pm02@hongming-global.com, sales@hongming-global.com",
            "ten_du_an_vi": "Tùy chỉnh hệ thống phần mềm IoT Visual SMB tại nhà máy Vonmax Bắc Ninh",
            "ky_thuat": "Jenson Chang (張永吉)",
            "ngay_ky": "06/06/2025",
            "tong_gia_tri": 1100000000,
            "da_thu": 990000000,
            "con_lai": 110000000,
            "ty_le_thu": "90%",
            "trang_thai_du_an": "Chờ nghiệm thu đợt cuối (10%)",
            "ghi_chu": "Hoàn tất bàn giao, đôn đốc thanh toán 110.000.000đ",
            "has_urgent": True,
            "has_waiting": True,
            "has_excel_file": False,
            "excel_download_url": None,
            "milestones": [
                {
                    "so_hop_dong": "HMV060620250001",
                    "khach_hang": "Vonmax Industrial",
                    "dot_thanh_toan": "Đợt 1",
                    "ty_le": "30%",
                    "so_tien": 330000000,
                    "dieu_kien_kich_hoat": "Ký hợp đồng",
                    "han_thanh_toan": "20/06/2025",
                    "days_left": -480,
                    "hoa_don_vat": "HD-00088",
                    "tinh_trang": "ĐÃ THU ĐỦ",
                    "hanh_dong": "Hoàn thành",
                    "status_code": "PAID",
                    "status_label": "Đã thu đủ",
                    "badge_color": "green",
                },
                {
                    "so_hop_dong": "HMV060620250001",
                    "khach_hang": "Vonmax Industrial",
                    "dot_thanh_toan": "Đợt 2",
                    "ty_le": "60%",
                    "so_tien": 660000000,
                    "dieu_kien_kich_hoat": "Lắp đặt xong sản phẩm",
                    "han_thanh_toan": "15/09/2025",
                    "days_left": -395,
                    "hoa_don_vat": "HD-00115",
                    "tinh_trang": "ĐÃ THU ĐỦ",
                    "hanh_dong": "Hoàn thành",
                    "status_code": "PAID",
                    "status_label": "Đã thu đủ",
                    "badge_color": "green",
                },
                {
                    "so_hop_dong": "HMV060620250001",
                    "khach_hang": "Vonmax Industrial",
                    "dot_thanh_toan": "Đợt 3",
                    "ty_le": "10%",
                    "so_tien": 110000000,
                    "dieu_kien_kich_hoat": "Nghiệm thu đạt tiêu chuẩn",
                    "han_thanh_toan": "19/10/2026",
                    "days_left": 4,
                    "hoa_don_vat": "HD-00185",
                    "tinh_trang": "CHỜ THANH TOÁN",
                    "hanh_dong": "Đôn đốc thanh toán 110.000.000 đ",
                    "status_code": "URGENT",
                    "status_label": "Sắp đến hạn (Còn 4 ngày)",
                    "badge_color": "amber",
                },
            ],
        })

    # Sort so urgent/waiting contracts are on top
    contracts.sort(key=lambda c: (not c["has_urgent"], not c["has_waiting"]))
    return contracts


def get_milestone_prefill_payload(contract_no: str, milestone_name: str) -> Optional[Dict[str, Any]]:
    """Build ready-to-fill payload when user clicks a specific milestone."""
    contracts = get_all_saved_contracts_with_milestones()
    for c in contracts:
        if c["so_hop_dong"] == contract_no:
            target_ms = None
            for ms in c["milestones"]:
                if milestone_name in ms["dot_thanh_toan"] or ms["dot_thanh_toan"] in milestone_name:
                    target_ms = ms
                    break
            if not target_ms and c["milestones"]:
                target_ms = c["milestones"][0]

            if target_ms:
                so_tien_val = target_ms["so_tien"]
                so_tien_str = f"{int(so_tien_val):,}".replace(",", ".") if isinstance(so_tien_val, (int, float)) else str(so_tien_val)
                
                so_hd = c["so_hop_dong"]
                dot = target_ms["dot_thanh_toan"]
                hang_muc = f"{c['ten_du_an_vi']} ({dot} - {target_ms['ty_le']})"
                
                # Subject line
                subject = (
                    f"【宏明環球】合約編號 {so_hd} {dot}款項到期提醒 / "
                    f"Yêu cầu hỗ trợ thanh toán {dot} HĐ {so_hd} ({c['khach_hang_vi']})"
                )

                item_obj = {
                    "so_hop_dong": so_hd,
                    "hang_muc": hang_muc,
                    "noi_dung": f"{dot} ({target_ms['dieu_kien_kich_hoat']})",
                    "so_tien": so_tien_str,
                    "vat_info": "Chưa gồm VAT" if target_ms.get("hoa_don_vat") else "Đã gồm VAT",
                    "han_thanh_toan": target_ms["han_thanh_toan"],
                }

                return {
                    "khach_hang_vi": c["khach_hang_vi"],
                    "khach_hang_zh": c["khach_hang_zh"],
                    "email_to": c["email_to"],
                    "email_cc": c["email_cc"],
                    "email_subject": subject,
                    "doc_code": f"HM-PR-{datetime.now().strftime('%Y%m%d')}-{so_hd[-3:]}",
                    "item": item_obj,
                    "contract_summary": {
                        "so_hop_dong": so_hd,
                        "tong_gia_tri": c["tong_gia_tri"],
                        "da_thu": c["da_thu"],
                        "con_lai": c["con_lai"],
                        "milestone_info": target_ms,
                    }
                }
    return None
