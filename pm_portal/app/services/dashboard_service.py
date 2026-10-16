# -*- coding: utf-8 -*-
"""
Dashboard Service for Hong Ming Global PM Portal.
Provides aggregated analytics, real project overview, milestone status distribution,
action item prioritization, and Excel export based on live SQLite database and files.
"""

import io
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.config import WORKING_DIR
from app.database import (
    get_contracts_dossier,
    get_db_connection,
    scan_and_index_documents,
)

TRACKER_EXCEL_PATH = WORKING_DIR / "DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx"


def format_currency_vnd(amount: Optional[float]) -> str:
    """Format numeric amount into Vietnamese currency string (e.g. 807.583.184 ₫)."""
    if amount is None or amount == 0:
        return "0 ₫"
    return f"{amount:,.0f} ₫".replace(",", ".")


def format_millions_vnd(amount: Optional[float]) -> str:
    """Format numeric amount into concise millions string (e.g. 807,6)."""
    if not amount:
        return "0,0"
    val = amount / 1_000_000
    if val >= 1000:
        val_bil = amount / 1_000_000_000
        return f"{val_bil:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{val:,.1f}".replace(".", ",")


def parse_date_flexible(date_val: Any) -> Optional[datetime]:
    """Parse flexible date string or datetime object."""
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


def get_dashboard_overview_data() -> Dict[str, Any]:
    """
    Compile live overview metrics and projects list from the real database.
    Does not use any static mock data.
    """
    contracts = get_contracts_dossier()

    total_projects = len(contracts)
    total_contract_value = sum(float(c.get("total_amount") or 0) for c in contracts)
    total_paid_value = sum(float(c.get("paid_amount") or 0) for c in contracts)
    total_remaining_value = max(0.0, total_contract_value - total_paid_value)
    
    collection_rate = (
        round((total_paid_value / total_contract_value) * 100, 1)
        if total_contract_value > 0
        else 0.0
    )

    # Categories breakdown
    running_contracts = []
    waiting_contracts = []
    done_contracts = []

    action_items: List[Dict[str, Any]] = []
    portfolio_bars: List[Dict[str, Any]] = []

    # Palette for bar chart
    bar_colors = ["blue", "indigo", "cyan", "green", "amber", "purple"]

    max_project_val = (
        max((float(c.get("total_amount") or 0) for c in contracts), default=1.0)
        or 1.0
    )

    # Analyze each real contract
    for idx, c in enumerate(contracts):
        c_code = c.get("contract_code") or ""
        cust_vi = c.get("customer_name_vi") or ""
        cust_zh = c.get("customer_name_zh") or ""
        proj_vi = c.get("project_name_vi") or ""
        status_text = c.get("status") or "Đang triển khai"
        total_amt = float(c.get("total_amount") or 0)
        paid_amt = float(c.get("paid_amount") or 0)
        remaining_amt = max(0.0, total_amt - paid_amt)
        percent_paid = (
            int((paid_amt / total_amt) * 100) if total_amt > 0 else 0
        )

        # Categorize into Running / Waiting / Done
        st_lower = status_text.lower()
        if "hoàn tất" in st_lower or "thanh lý" in st_lower or (paid_amt >= total_amt and total_amt > 0):
            done_contracts.append(c)
            filter_cat = "done"
            status_pill = {"text": "Đã hoàn tất", "class": "done"}
        elif c.get("has_urgent") or "chờ" in st_lower or "thu nợ" in st_lower or "sắp đến hạn" in st_lower:
            waiting_contracts.append(c)
            filter_cat = "payment"
            status_pill = {"text": status_text if len(status_text) < 25 else "Chờ thu nợ", "class": "payment"}
        else:
            running_contracts.append(c)
            filter_cat = "running"
            status_pill = {"text": status_text if len(status_text) < 25 else "Đang triển khai", "class": "running"}

        # Bar chart representation
        bar_pct = round((total_amt / max_project_val) * 100, 1)
        # Short label for customer
        short_cust = cust_vi.replace("CÔNG TY TNHH", "").replace("CÔNG TY CỔ PHẦN", "").replace("CÔNG TY", "").strip()
        if len(short_cust) > 18:
            short_cust = short_cust[:16] + "…"

        portfolio_bars.append({
            "contract_code": c_code,
            "customer_short": short_cust or cust_vi[:16],
            "customer_full": cust_vi,
            "project_short": proj_vi[:25] + ("…" if len(proj_vi) > 25 else ""),
            "total_amount": total_amt,
            "formatted_amount": format_millions_vnd(total_amt),
            "bar_percentage": bar_pct,
            "color_class": bar_colors[idx % len(bar_colors)],
        })

        # Process milestone actions
        milestones = c.get("milestones") or []
        current_milestone_info = None

        for m in milestones:
            m_name = m.get("milestone_name") or "Đợt TT"
            m_amt = float(m.get("amount") or 0)
            m_status = m.get("status") or ""
            days_left = m.get("days_left")
            due_date = m.get("due_date") or ""

            # Detect current active milestone
            if current_milestone_info is None and m_status != "PAID":
                if days_left is not None and days_left < 0:
                    current_milestone_info = {
                        "name": m_name,
                        "text": f"Quá hạn {abs(days_left)} ngày",
                        "dot_color": "amber",
                        "badge": "Quá hạn",
                    }
                elif days_left is not None and days_left <= 10:
                    current_milestone_info = {
                        "name": m_name,
                        "text": f"Còn {days_left} ngày ({due_date})",
                        "dot_color": "amber",
                        "badge": f"Còn {days_left}d",
                    }
                elif m_status == "WAITING":
                    current_milestone_info = {
                        "name": m_name,
                        "text": f"Đến hạn {due_date}",
                        "dot_color": "blue",
                        "badge": "Đang chờ",
                    }
                elif m_status == "PENDING_TRIGGER":
                    cond = m.get("trigger_condition") or "Chờ nghiệm thu"
                    cond_short = cond[:22] + "…" if len(cond) > 22 else cond
                    current_milestone_info = {
                        "name": m_name,
                        "text": cond_short,
                        "dot_color": "purple",
                        "badge": "Điều kiện",
                    }
                else:
                    current_milestone_info = {
                        "name": m_name,
                        "text": m.get("status_label") or "Chưa đến hạn",
                        "dot_color": "blue",
                        "badge": "Kế hoạch",
                    }

            # Generate urgent or pending action items
            if m_status in ("URGENT", "OVERDUE") or (days_left is not None and days_left <= 10 and m_status != "PAID"):
                severity = "danger" if (days_left is not None and days_left < 0) else "warning"
                badge_text = "Quá hạn" if (days_left is not None and days_left < 0) else "Ưu tiên"
                action_items.append({
                    "contract_code": c_code,
                    "customer_name": cust_vi,
                    "title": f"Thu hồi công nợ {short_cust or cust_vi[:16]}",
                    "detail": f"{m_name} · {format_currency_vnd(m_amt)} · {m.get('status_label') or (f'Hạn {due_date}')}",
                    "severity": severity,
                    "badge_text": badge_text,
                    "action_url": f"/reminders?contract_code={c_code}&milestone_name={m_name}",
                })
            elif m_status == "PENDING_TRIGGER":
                cond = m.get("trigger_condition") or "nghiệm thu"
                action_items.append({
                    "contract_code": c_code,
                    "customer_name": cust_vi,
                    "title": f"Theo dõi mốc {m_name} · {short_cust or cust_vi[:16]}",
                    "detail": f"Điều kiện: {cond[:40]}…",
                    "severity": "info",
                    "badge_text": "Điều kiện",
                    "action_url": "/acceptance" if "nghiệm thu" in cond.lower() else f"/contracts",
                })

        # Fallback if all milestones paid or no milestones
        if not current_milestone_info:
            if paid_amt >= total_amt and total_amt > 0:
                current_milestone_info = {
                    "name": "Hoàn tất",
                    "text": "Đã tất toán đủ 100%",
                    "dot_color": "green",
                    "badge": "Hoàn tất",
                }
            else:
                current_milestone_info = {
                    "name": "Kế hoạch",
                    "text": status_text,
                    "dot_color": "blue",
                    "badge": "Tiến độ",
                }

        c["current_milestone_info"] = current_milestone_info
        c["filter_cat"] = filter_cat
        c["status_pill"] = status_pill
        c["percent_paid"] = percent_paid
        c["formatted_total"] = format_currency_vnd(total_amt)
        c["formatted_paid"] = format_currency_vnd(paid_amt)
        c["formatted_remaining"] = format_currency_vnd(remaining_amt)

    # Sort portfolio bars by value desc
    portfolio_bars.sort(key=lambda x: x["total_amount"], reverse=True)

    # Sort action items: danger first, then warning, then info
    severity_order = {"danger": 0, "warning": 1, "info": 2}
    action_items.sort(key=lambda x: severity_order.get(x["severity"], 3))
    # Cap to top 6 items
    top_actions = action_items[:6]

    # Status distribution for donut chart
    count_running = len(running_contracts)
    count_waiting = len(waiting_contracts)
    count_done = len(done_contracts)

    if total_projects > 0:
        pct_running = round((count_running / total_projects) * 100)
        pct_waiting = round((count_waiting / total_projects) * 100)
        pct_done = max(0, 100 - pct_running - pct_waiting)
        active_rate = round(((count_running + count_waiting) / total_projects) * 100)
    else:
        pct_running, pct_waiting, pct_done = 0, 0, 0
        active_rate = 0

    # Build conic-gradient CSS stops for Donut
    # e.g.: conic-gradient(#2563eb 0% 50%, #f59e0b 50% 75%, #10b981 75% 100%)
    stop1 = pct_running
    stop2 = pct_running + pct_waiting
    donut_gradient = (
        f"conic-gradient(#2563eb 0% {stop1}%, #f59e0b {stop1}% {stop2}%, #10b981 {stop2}% 100%)"
        if total_projects > 0
        else "conic-gradient(#e2e8f0 0% 100%)"
    )

    # Current report date info
    now = datetime.now()
    report_period = f"Tháng {now.month:02d}/{now.year}"
    report_date_str = now.strftime("%d/%m/%Y")

    return {
        "status": "success",
        "summary": {
            "total_projects": total_projects,
            "total_contract_value": total_contract_value,
            "total_contract_value_formatted": format_currency_vnd(total_contract_value),
            "total_contract_value_millions": format_millions_vnd(total_contract_value),
            "total_paid_value": total_paid_value,
            "total_paid_value_formatted": format_currency_vnd(total_paid_value),
            "total_remaining_value": total_remaining_value,
            "total_remaining_value_formatted": format_currency_vnd(total_remaining_value),
            "collection_rate": collection_rate,
            "running_count": count_running,
            "waiting_count": count_waiting,
            "done_count": count_done,
            "urgent_count": len([a for a in action_items if a["severity"] in ("danger", "warning")]),
            "active_rate": active_rate,
            "report_period": report_period,
            "report_date": report_date_str,
        },
        "portfolio_bars": portfolio_bars,
        "donut": {
            "gradient": donut_gradient,
            "active_rate": active_rate,
            "pct_running": pct_running,
            "pct_waiting": pct_waiting,
            "pct_done": pct_done,
            "count_running": count_running,
            "count_waiting": count_waiting,
            "count_done": count_done,
        },
        "action_items": top_actions,
        "contracts": contracts,
    }


def sync_contracts_from_tracker_excel() -> Dict[str, Any]:
    """
    Synchronize historical contracts and milestones from DANH_SACH_THEO_DOI_DU_AN_HONG_MING.xlsx
    into SQLite database without overwriting or duplicating existing user-created contracts.
    """
    if not TRACKER_EXCEL_PATH.exists():
        return {
            "status": "error",
            "message": f"Không tìm thấy file Excel theo dõi tại: {TRACKER_EXCEL_PATH.name}",
            "synced_count": 0,
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get existing contract codes to avoid duplicates
    cursor.execute("SELECT contract_code FROM contracts")
    existing_codes = {row["contract_code"] for row in cursor.fetchall()}

    wb = openpyxl.load_workbook(str(TRACKER_EXCEL_PATH), data_only=True)
    synced_contracts = 0
    synced_milestones = 0

    # 1. Read Overview Sheet
    overview_rows: Dict[str, Dict[str, Any]] = {}
    if "Tổng Quan Dự Án 專案總覽" in wb.sheetnames:
        ws_ov = wb["Tổng Quan Dự Án 專案總覽"]
        for r in range(4, ws_ov.max_row + 1):
            c_code = ws_ov.cell(r, 1).value
            if not c_code:
                continue
            c_code = str(c_code).strip()
            if not c_code or "TỔNG CỘNG" in c_code.upper():
                continue

            cust_raw = str(ws_ov.cell(r, 2).value or "").strip()
            # Infer bilingual customer name
            cust_vi = cust_raw
            cust_zh = ""
            if "CX" in cust_raw:
                cust_vi = "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)"
                cust_zh = "越南CX科技股份有限公司"
            elif "Cheng Feng" in cust_raw:
                cust_vi = "CÔNG TY TNHH CÔNG NGHỆ CHENG FENG LE HUA (VIỆT NAM)"
                cust_zh = "晟峰樂華（越南）科技有限公司"
            elif "Vonmax" in cust_raw:
                cust_vi = "CÔNG TY TNHH VONMAX INDUSTRIAL (VIỆT NAM)"
                cust_zh = "弘聲精密工業（越南）有限公司"

            overview_rows[c_code] = {
                "contract_code": c_code,
                "customer_name_vi": cust_vi,
                "customer_name_zh": cust_zh,
                "project_name_vi": str(ws_ov.cell(r, 3).value or "").strip(),
                "project_name_zh": "",
                "lead_engineer": str(ws_ov.cell(r, 4).value or "Jenson Chang (張永吉)").strip(),
                "signed_date": str(ws_ov.cell(r, 5).value or "").strip(),
                "total_amount": float(ws_ov.cell(r, 6).value or 0),
                "paid_amount": float(ws_ov.cell(r, 7).value or 0),
                "status": str(ws_ov.cell(r, 10).value or "Đang triển khai").strip(),
                "notes": str(ws_ov.cell(r, 11).value or "").strip(),
            }

    # 2. Read Milestones Sheet
    milestones_by_code: Dict[str, List[Dict[str, Any]]] = {}
    if "Đợt Thanh Toán 款項明細" in wb.sheetnames:
        ws_ms = wb["Đợt Thanh Toán 款項明細"]
        for r in range(4, ws_ms.max_row + 1):
            c_code = ws_ms.cell(r, 1).value
            if not c_code:
                continue
            c_code = str(c_code).strip()
            if not c_code:
                continue

            dot_name = str(ws_ms.cell(r, 3).value or "Đợt 1").strip()
            pct_raw = str(ws_ms.cell(r, 4).value or "0").replace("%", "").strip()
            try:
                pct = float(pct_raw)
            except ValueError:
                pct = 0.0

            amt = float(ws_ms.cell(r, 5).value or 0)
            trigger_cond = str(ws_ms.cell(r, 6).value or "").strip()
            due_date = str(ws_ms.cell(r, 7).value or "").strip()
            invoice = str(ws_ms.cell(r, 8).value or "Chưa xuất").strip()
            tinh_trang = str(ws_ms.cell(r, 9).value or "").strip().upper()
            action_req = str(ws_ms.cell(r, 10).value or "").strip()

            if tinh_trang == "ĐÃ THU ĐỦ":
                status = "PAID"
                status_label = "Đã thu đủ"
                paid_date = due_date
            elif tinh_trang in ("CHỜ THANH TOÁN", "SẮP ĐẾN HẠN"):
                status = "URGENT"
                status_label = "Chờ thanh toán"
                paid_date = None
            else:
                status = "UPCOMING"
                status_label = "Chưa đến hạn"
                paid_date = None

            milestones_by_code.setdefault(c_code, []).append({
                "milestone_name": dot_name,
                "percentage": pct,
                "amount": amt,
                "trigger_condition": trigger_cond,
                "due_date": due_date,
                "invoice_no": invoice,
                "status": status,
                "status_label": status_label,
                "action_required": action_req,
                "paid_date": paid_date,
            })

    # 3. Insert newly discovered contracts
    for c_code, c_data in overview_rows.items():
        if c_code not in existing_codes:
            cursor.execute("""
                INSERT INTO contracts (
                    contract_code, customer_name_vi, customer_name_zh, project_name_vi,
                    project_name_zh, lead_engineer, signed_date, total_amount, paid_amount,
                    status, contact_email, contact_cc, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c_code, c_data["customer_name_vi"], c_data["customer_name_zh"],
                c_data["project_name_vi"], c_data["project_name_zh"], c_data["lead_engineer"],
                c_data["signed_date"], c_data["total_amount"], c_data["paid_amount"],
                c_data["status"], "sales@hongming-global.com", "pm02@hongming-global.com",
                c_data["notes"]
            ))
            contract_id = cursor.lastrowid
            synced_contracts += 1

            # Insert milestones for this contract
            for ms in milestones_by_code.get(c_code, []):
                cursor.execute("""
                    INSERT INTO payment_milestones (
                        contract_id, contract_code, milestone_name, percentage, amount,
                        trigger_condition, due_date, invoice_no, status, status_label,
                        action_required, paid_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    contract_id, c_code, ms["milestone_name"], ms["percentage"],
                    ms["amount"], ms["trigger_condition"], ms["due_date"], ms["invoice_no"],
                    ms["status"], ms["status_label"], ms["action_required"], ms["paid_date"]
                ))
                synced_milestones += 1

    conn.commit()
    # Re-scan documents on disk to map links
    scan_and_index_documents(conn)
    conn.close()

    return {
        "status": "success",
        "message": f"Đã đồng bộ {synced_contracts} hợp đồng mới và {synced_milestones} đợt thanh toán từ file Excel theo dõi!",
        "synced_contracts": synced_contracts,
        "synced_milestones": synced_milestones,
    }


def generate_dashboard_excel_report() -> io.BytesIO:
    """
    Export current real portfolio and milestones into an executive Excel workbook.
    Follows Hong Ming PM Zero-Layout-Distortion standards and 10 control points.
    """
    contracts = get_contracts_dossier()

    wb = openpyxl.Workbook()
    # Sheet 1: Overview
    ws_ov = wb.active
    ws_ov.title = "Tổng Quan Dự Án"
    ws_ov.views.sheetView[0].showGridLines = True
    ws_ov.freeze_panes = "A5"

    # Sheet 2: Payment Milestones
    ws_ms = wb.create_sheet(title="Đợt Thanh Toán")
    ws_ms.views.sheetView[0].showGridLines = True
    ws_ms.freeze_panes = "A5"

    # Styling tokens
    font_family = "微軟正黑體"
    title_font = Font(name=font_family, size=14, bold=True, color="1E3A8A")
    sub_font = Font(name=font_family, size=10, italic=True, color="475569")
    header_font = Font(name=font_family, size=9.5, bold=True, color="FFFFFF")
    data_font = Font(name=font_family, size=9)
    bold_data_font = Font(name=font_family, size=9, bold=True)
    num_font = Font(name="Consolas", size=9)
    bold_num_font = Font(name="Consolas", size=9, bold=True)

    header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    sub_header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    total_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )
    double_bottom_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="double", color="1E40AF"),
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center")

    # ==========================
    # POPULATE SHEET 1: OVERVIEW
    # ==========================
    ws_ov["A1"] = "BÁO CÁO TỔNG QUAN DANH MỤC DỰ ÁN & HỢP ĐỒNG - CÔNG TY TNHH TOÀN CẦU HONG MING"
    ws_ov["A1"].font = title_font
    now = datetime.now()
    ws_ov["A2"] = f"宏明環球 · Xuất dữ liệu vận hành thực tế ngày {now.strftime('%d/%m/%Y %H:%M')}"
    ws_ov["A2"].font = sub_font

    headers_ov = [
        "STT", "Mã Hợp Đồng\n合約編號", "Khách Hàng\n客戶名稱", "Dự Án / Hạng Mục\n專案項目",
        "Kỹ Thuật\n技術人員", "Ngày Ký\n簽約日", "Tổng Giá Trị\n合約總金額 (VND)",
        "Đã Thu\n已收 (VND)", "Còn Lại\n未收餘額 (VND)", "Tỷ Lệ Thu\n進度 (%)",
        "Trạng Thái Dự Án\n狀態", "Ghi Chú\n備註"
    ]

    for col_idx, h_text in enumerate(headers_ov, start=1):
        cell = ws_ov.cell(row=4, column=col_idx, value=h_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = thin_border
    ws_ov.row_dimensions[4].height = 28

    row_idx = 5
    sum_total = 0.0
    sum_paid = 0.0

    for i, c in enumerate(contracts, start=1):
        tot = float(c.get("total_amount") or 0)
        paid = float(c.get("paid_amount") or 0)
        rem = max(0.0, tot - paid)
        rate = round((paid / tot) * 100, 1) if tot > 0 else 0.0
        sum_total += tot
        sum_paid += paid

        ws_ov.cell(row=row_idx, column=1, value=i).alignment = align_center
        ws_ov.cell(row=row_idx, column=2, value=c.get("contract_code") or "").alignment = align_center
        ws_ov.cell(row=row_idx, column=3, value=c.get("customer_name_vi") or "").alignment = align_left
        ws_ov.cell(row=row_idx, column=4, value=c.get("project_name_vi") or "").alignment = align_left
        ws_ov.cell(row=row_idx, column=5, value=c.get("lead_engineer") or "").alignment = align_center
        ws_ov.cell(row=row_idx, column=6, value=c.get("signed_date") or "").alignment = align_center
        
        c7 = ws_ov.cell(row=row_idx, column=7, value=tot)
        c7.number_format = "#,##0"
        c7.alignment = align_right

        c8 = ws_ov.cell(row=row_idx, column=8, value=paid)
        c8.number_format = "#,##0"
        c8.alignment = align_right

        c9 = ws_ov.cell(row=row_idx, column=9, value=rem)
        c9.number_format = "#,##0"
        c9.alignment = align_right

        c10 = ws_ov.cell(row=row_idx, column=10, value=f"{rate}%")
        c10.alignment = align_center

        ws_ov.cell(row=row_idx, column=11, value=c.get("status") or "").alignment = align_center
        ws_ov.cell(row=row_idx, column=12, value=c.get("notes") or "").alignment = align_left

        for col_idx in range(1, 13):
            cell = ws_ov.cell(row=row_idx, column=col_idx)
            cell.font = data_font if col_idx not in (2, 7, 8, 9) else num_font
            cell.border = thin_border
            if i % 2 == 0:
                cell.fill = zebra_fill

        ws_ov.row_dimensions[row_idx].height = 22
        row_idx += 1

    # Total row
    sum_rem = max(0.0, sum_total - sum_paid)
    sum_rate = round((sum_paid / sum_total) * 100, 1) if sum_total > 0 else 0.0

    ws_ov.cell(row=row_idx, column=1, value="")
    ws_ov.cell(row=row_idx, column=2, value="")
    c_tot_label = ws_ov.cell(row=row_idx, column=3, value="TỔNG CỘNG / 合計")
    c_tot_label.alignment = align_left

    c_tot7 = ws_ov.cell(row=row_idx, column=7, value=sum_total)
    c_tot7.number_format = "#,##0"
    c_tot7.alignment = align_right

    c_tot8 = ws_ov.cell(row=row_idx, column=8, value=sum_paid)
    c_tot8.number_format = "#,##0"
    c_tot8.alignment = align_right

    c_tot9 = ws_ov.cell(row=row_idx, column=9, value=sum_rem)
    c_tot9.number_format = "#,##0"
    c_tot9.alignment = align_right

    ws_ov.cell(row=row_idx, column=10, value=f"{sum_rate}%").alignment = align_center
    ws_ov.cell(row=row_idx, column=11, value="")
    ws_ov.cell(row=row_idx, column=12, value="")

    for col_idx in range(1, 13):
        cell = ws_ov.cell(row=row_idx, column=col_idx)
        cell.font = bold_num_font if col_idx in (7, 8, 9) else bold_data_font
        cell.fill = total_fill
        cell.border = double_bottom_border
    ws_ov.row_dimensions[row_idx].height = 24

    # Auto column width for sheet 1
    col_widths_ov = {1: 6, 2: 20, 3: 36, 4: 38, 5: 22, 6: 14, 7: 18, 8: 18, 9: 18, 10: 12, 11: 28, 12: 32}
    for col_i, w in col_widths_ov.items():
        ws_ov.column_dimensions[get_column_letter(col_i)].width = w

    # ==========================
    # POPULATE SHEET 2: MILESTONES
    # ==========================
    ws_ms["A1"] = "CHI TIẾT TIẾN ĐỘ THANH TOÁN THEO CÁC ĐỢT (AR MILESTONES)"
    ws_ms["A1"].font = title_font
    ws_ms["A2"] = f"Hong Ming PM Portal · Danh sách đợt thanh toán cập nhật ngày {now.strftime('%d/%m/%Y')}"
    ws_ms["A2"].font = sub_font

    headers_ms = [
        "STT", "Mã Hợp Đồng", "Khách Hàng", "Đợt TT", "Tỷ Lệ (%)",
        "Số Tiền (VND)", "Điều Kiện Kích Hoạt", "Hạn Thanh Toán",
        "Số Hóa Đơn", "Tình Trạng", "Hành Động Nhắc Nợ"
    ]

    for col_idx, h_text in enumerate(headers_ms, start=1):
        cell = ws_ms.cell(row=4, column=col_idx, value=h_text)
        cell.font = header_font
        cell.fill = sub_header_fill
        cell.alignment = align_center
        cell.border = thin_border
    ws_ms.row_dimensions[4].height = 26

    ms_row_idx = 5
    ms_count = 0
    for c in contracts:
        c_code = c.get("contract_code") or ""
        cust = c.get("customer_name_vi") or ""
        for m in (c.get("milestones") or []):
            ms_count += 1
            amt = float(m.get("amount") or 0)
            ws_ms.cell(row=ms_row_idx, column=1, value=ms_count).alignment = align_center
            ws_ms.cell(row=ms_row_idx, column=2, value=c_code).alignment = align_center
            ws_ms.cell(row=ms_row_idx, column=3, value=cust).alignment = align_left
            ws_ms.cell(row=ms_row_idx, column=4, value=m.get("milestone_name") or "").alignment = align_center
            ws_ms.cell(row=ms_row_idx, column=5, value=f"{m.get('percentage') or 0}%").alignment = align_center

            c6 = ws_ms.cell(row=ms_row_idx, column=6, value=amt)
            c6.number_format = "#,##0"
            c6.alignment = align_right

            ws_ms.cell(row=ms_row_idx, column=7, value=m.get("trigger_condition") or "").alignment = align_left
            ws_ms.cell(row=ms_row_idx, column=8, value=m.get("due_date") or "").alignment = align_center
            ws_ms.cell(row=ms_row_idx, column=9, value=m.get("invoice_no") or "Chưa xuất").alignment = align_center
            ws_ms.cell(row=ms_row_idx, column=10, value=m.get("status_label") or "").alignment = align_center
            ws_ms.cell(row=ms_row_idx, column=11, value=m.get("action_required") or "").alignment = align_left

            for col_idx in range(1, 12):
                cell = ws_ms.cell(row=ms_row_idx, column=col_idx)
                cell.font = data_font if col_idx not in (2, 6) else num_font
                cell.border = thin_border
                if ms_count % 2 == 0:
                    cell.fill = zebra_fill

            ws_ms.row_dimensions[ms_row_idx].height = 20
            ms_row_idx += 1

    col_widths_ms = {1: 6, 2: 20, 3: 36, 4: 12, 5: 12, 6: 18, 7: 35, 8: 16, 9: 15, 10: 22, 11: 35}
    for col_i, w in col_widths_ms.items():
        ws_ms.column_dimensions[get_column_letter(col_i)].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
