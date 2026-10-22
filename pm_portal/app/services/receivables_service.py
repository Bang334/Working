# -*- coding: utf-8 -*-
"""Service module for Project Receivables (AR) management and contract synchronization."""

import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl

from app.database import get_db_connection


def format_currency_vn(amount: float) -> str:
    """Format numeric amount into Vietnamese currency string."""
    try:
        return f"{int(round(amount)):,} ₫".replace(",", ".")
    except Exception:
        return "0 ₫"


def parse_flexible_date(val: Any) -> Optional[str]:
    """Parse string/datetime into YYYY-MM-DD string safely."""
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if s in ["#VALUE!", "-", "", "None"]:
        return None
    # Matches YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # Matches DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
    if m:
        day, month, year = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return s


def calculate_days_left(due_date_str: Optional[str]) -> Optional[int]:
    """Calculate days remaining until due date (negative means overdue)."""
    if not due_date_str:
        return None
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", due_date_str):
            due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            return (due - today).days
    except Exception:
        pass
    return None


def determine_collection_status(received: float, gross: float, due_date_str: Optional[str], raw_status: Optional[str] = None) -> str:
    """Determine standardized collection status code: PAID, DELAYED, URGENT, PENDING."""
    if gross > 0 and (received >= gross or round(gross - received) <= 0):
        return "PAID"
    
    if raw_status:
        s_low = raw_status.lower()
        if "đã thanh toán" in s_low or "đã thu" in s_low or "已付款" in s_low or "已收款" in s_low:
            if received >= gross:
                return "PAID"

    days = calculate_days_left(due_date_str)
    if days is not None:
        if days < 0:
            return "DELAYED"
        if days <= 7:
            return "URGENT"

    return "PENDING"


def list_receivables(
    customer: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    overdue_only: bool = False
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    # If table is empty, automatically initialize by syncing from database contracts
    cursor.execute("SELECT COUNT(*) FROM project_receivables")
    if cursor.fetchone()[0] == 0:
        conn.close()
        sync_from_existing_contracts(clear_first=False)
        conn = get_db_connection()
        cursor = conn.cursor()

    query = "SELECT * FROM project_receivables WHERE 1=1"
    params = []

    if customer and customer != "all":
        query += " AND (customer_name LIKE ? OR customer_name = ?)"
        params.extend([f"%{customer}%", customer])

    if status and status != "all":
        query += " AND collection_status = ?"
        params.append(status)

    if search:
        s = f"%{search.strip()}%"
        query += """ AND (
            project_name LIKE ? OR 
            customer_name LIKE ? OR 
            contract_code LIKE ? OR 
            notes LIKE ?
        )"""
        params.extend([s, s, s, s])

    query += " ORDER BY order_no ASC, id ASC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        gross = float(d.get("gross_amount") or 0.0)
        received = float(d.get("received_amount") or 0.0)
        debt = float(d.get("remaining_debt") or 0.0)
        # Ensure remaining debt calculation is accurate
        if debt == 0 and gross > 0 and received < gross:
            debt = max(0.0, gross - received)
            d["remaining_debt"] = debt

        due = d.get("due_date")
        days = calculate_days_left(due)
        d["days_left"] = days
        d["is_overdue"] = days is not None and days < 0 and d.get("collection_status") != "PAID"

        if overdue_only and not d["is_overdue"]:
            continue

        results.append(d)

    return results


def get_receivable(item_id: int) -> Optional[Dict[str, Any]]:
    """Get single receivable by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_receivables WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["days_left"] = calculate_days_left(d.get("due_date"))
        return d
    return None


get_receivable_by_id = get_receivable


def get_receivables_stats() -> Dict[str, Any]:
    """Calculate summary statistics and KPI metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_receivables")
    rows = cursor.fetchall()
    conn.close()

    total_receivable = 0.0
    total_received = 0.0
    total_debt = 0.0
    paid_count = 0
    pending_count = 0
    overdue_count = 0
    urgent_count = 0
    customers = set()
    contracts = set()

    for r in rows:
        d = dict(r)
        gross = float(d.get("gross_amount") or 0.0)
        received = float(d.get("received_amount") or 0.0)
        debt = float(d.get("remaining_debt") or 0.0)
        status = d.get("collection_status") or "PENDING"
        due = d.get("due_date")

        total_receivable += gross
        total_received += received
        total_debt += debt

        if d.get("customer_name"):
            customers.add(d["customer_name"].strip())
        if d.get("contract_code"):
            contracts.add(d["contract_code"].strip())

        days = calculate_days_left(due)
        if status == "PAID" or (gross > 0 and received >= gross):
            paid_count += 1
        elif days is not None and days < 0:
            overdue_count += 1
        elif days is not None and days <= 7:
            urgent_count += 1
        else:
            pending_count += 1

    completion_rate = round((total_received / total_receivable * 100), 1) if total_receivable > 0 else 0.0

    return {
        "total_receivable": round(total_receivable, 2),
        "total_receivable_formatted": format_currency_vn(total_receivable),
        "total_received": round(total_received, 2),
        "total_received_formatted": format_currency_vn(total_received),
        "total_debt": round(total_debt, 2),
        "total_debt_formatted": format_currency_vn(total_debt),
        "total_milestones": len(rows),
        "paid_count": paid_count,
        "pending_count": pending_count,
        "overdue_count": overdue_count,
        "urgent_count": urgent_count,
        "completion_rate": completion_rate,
        "customers": sorted(list(customers)),
        "contracts": sorted(list(contracts)),
    }


def create_receivable(data: Dict[str, Any]) -> int:
    """Insert a new receivable record."""
    net = float(data.get("net_amount") or 0.0)
    vat_rate = float(data.get("vat_rate") or 0.0)
    vat_amount = float(data.get("vat_amount") or (net * vat_rate))
    gross = float(data.get("gross_amount") or (net + vat_amount))
    received = float(data.get("received_amount") or 0.0)
    debt = max(0.0, gross - received)

    status = data.get("collection_status") or determine_collection_status(received, gross, data.get("due_date"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_receivables (
            order_no, project_name, customer_name, contract_code,
            total_contract_amount, net_amount, vat_rate, vat_amount,
            gross_amount, received_amount, remaining_debt,
            customer_promised_date, due_date, paid_date,
            doc_status, collection_status, notes, linked_milestone_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("order_no"),
        data.get("project_name", "").strip(),
        data.get("customer_name", "").strip(),
        data.get("contract_code"),
        float(data.get("total_contract_amount") or 0.0),
        net,
        vat_rate,
        vat_amount,
        gross,
        received,
        debt,
        data.get("customer_promised_date"),
        data.get("due_date"),
        data.get("paid_date"),
        data.get("doc_status"),
        status,
        data.get("notes"),
        data.get("linked_milestone_id"),
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_receivable(item_id: int, data: Dict[str, Any]) -> bool:
    """Update fields of an existing receivable record."""
    existing = get_receivable(item_id)
    if not existing:
        return False

    merged = dict(existing)
    merged.update({k: v for k, v in data.items() if v is not None})

    net = float(merged.get("net_amount") or 0.0)
    vat_rate = float(merged.get("vat_rate") or 0.0)
    if "vat_rate" in data or "net_amount" in data:
        vat_amount = round(net * vat_rate, 2)
        gross = round(net + vat_amount, 2)
    else:
        vat_amount = float(merged.get("vat_amount") or round(net * vat_rate, 2))
        gross = float(merged.get("gross_amount") or round(net + vat_amount, 2))

    received = float(merged.get("received_amount") or 0.0)
    debt = max(0.0, gross - received)
    status = merged.get("collection_status") or determine_collection_status(received, gross, merged.get("due_date"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE project_receivables SET
            order_no = ?,
            project_name = ?,
            customer_name = ?,
            contract_code = ?,
            total_contract_amount = ?,
            net_amount = ?,
            vat_rate = ?,
            vat_amount = ?,
            gross_amount = ?,
            received_amount = ?,
            remaining_debt = ?,
            customer_promised_date = ?,
            due_date = ?,
            paid_date = ?,
            doc_status = ?,
            collection_status = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        merged.get("order_no"),
        merged.get("project_name"),
        merged.get("customer_name"),
        merged.get("contract_code"),
        float(merged.get("total_contract_amount") or 0.0),
        net,
        vat_rate,
        vat_amount,
        gross,
        received,
        debt,
        merged.get("customer_promised_date"),
        merged.get("due_date"),
        merged.get("paid_date"),
        merged.get("doc_status"),
        status,
        merged.get("notes"),
        item_id,
    ))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def update_receivable_status(item_id: int, status: str, paid_date: Optional[str] = None) -> bool:
    """Quick update of collection status from inline dropdown."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM project_receivables WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    item = dict(row)
    gross = float(item.get("gross_amount") or 0.0)

    if status == "PAID":
        actual_paid_date = paid_date or datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            UPDATE project_receivables SET
                collection_status = 'PAID',
                received_amount = ?,
                remaining_debt = 0,
                paid_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (gross, actual_paid_date, item_id))

        # Synchronize linked contract milestone if exists
        linked_ms_id = item.get("linked_milestone_id")
        if linked_ms_id:
            cursor.execute("""
                UPDATE payment_milestones SET
                    triggered = 1,
                    status = 'PAID',
                    status_label = 'Đã thanh toán',
                    paid_date = ?
                WHERE id = ?
            """, (actual_paid_date, linked_ms_id))

    else:
        # Revert to pending/delayed with debt re-evaluated
        cursor.execute("""
            UPDATE project_receivables SET
                collection_status = ?,
                remaining_debt = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, gross, item_id))

    conn.commit()
    conn.close()
    return True


def update_receivable_notes(item_id: int, notes: str) -> bool:
    """Directly update collection follow-up notes inline."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE project_receivables SET
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (notes, item_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_receivable(item_id: int) -> bool:
    """Delete a single receivable milestone record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_receivables WHERE id = ?", (item_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def sync_from_existing_contracts(clear_first: bool = False) -> int:
    """Synchronize milestones from 'contracts' and 'payment_milestones' tables into receivables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if clear_first:
        cursor.execute("DELETE FROM project_receivables")
        conn.commit()

    cursor.execute("""
        SELECT m.id AS ms_id, m.contract_code, m.milestone_name, m.percentage, m.amount,
               m.trigger_condition, m.due_date, m.paid_date, m.invoice_no, m.status AS ms_status,
               c.customer_name_vi, c.project_name_vi, c.total_amount
        FROM payment_milestones m
        JOIN contracts c ON c.contract_code = m.contract_code
        ORDER BY c.id ASC, m.id ASC
    """)
    milestones = cursor.fetchall()

    added_count = 0
    order_counter = 1
    for ms in milestones:
        m = dict(ms)
        ms_id = m["ms_id"]
        c_code = m["contract_code"]
        ms_name = m["milestone_name"]

        # Check if already in project_receivables
        cursor.execute("SELECT id FROM project_receivables WHERE linked_milestone_id = ?", (ms_id,))
        existing = cursor.fetchone()

        pct = float(m.get("percentage") or 0.0)
        amt = float(m.get("amount") or 0.0)
        tot = float(m.get("total_amount") or 0.0)
        p_name = f"{ms_name} ({int(pct)}%) - {m.get('project_name_vi') or ''}".strip()
        due_str = parse_flexible_date(m.get("due_date"))
        paid_str = parse_flexible_date(m.get("paid_date"))

        # Contract amounts are milestone contract values (VAT determined at time of invoice issuance)
        vat_rate = 0.0
        net_amt = amt
        vat_amt = 0.0
        gross_amt = amt

        is_paid = m.get("ms_status") == "PAID" or bool(paid_str)
        rec_amt = amt if is_paid else 0.0
        rem_debt = 0.0 if is_paid else amt
        col_status = "PAID" if is_paid else determine_collection_status(rec_amt, amt, due_str)
        doc_st = m.get("invoice_no") or ("Đã xuất HĐ" if is_paid else "Chờ xuất HĐ / BB nghiệm thu")
        notes_str = m.get("trigger_condition") or ""

        if not existing:
            cursor.execute("""
                INSERT INTO project_receivables (
                    order_no, project_name, customer_name, contract_code,
                    total_contract_amount, net_amount, vat_rate, vat_amount,
                    gross_amount, received_amount, remaining_debt,
                    due_date, paid_date, doc_status, collection_status, notes,
                    linked_milestone_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_counter,
                p_name,
                m.get("customer_name_vi") or "Khách hàng",
                c_code,
                tot,
                net_amt,
                vat_rate,
                vat_amt,
                gross_amt,
                rec_amt,
                rem_debt,
                due_str,
                paid_str,
                doc_st,
                col_status,
                notes_str,
                ms_id,
            ))
            added_count += 1
            order_counter += 1

    conn.commit()
    conn.close()
    return added_count


def import_receivables_from_sheet3(excel_path: str, overwrite: bool = True) -> int:
    """Parse and load 47 milestones from Sheet 3 of QLDA_TRANG_PM_2026 into database."""
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    if "3. Theo Dõi Công Nợ Dự Án" not in wb.sheetnames:
        raise ValueError("Không tìm thấy Sheet '3. Theo Dõi Công Nợ Dự Án' trong file Excel.")

    ws = wb["3. Theo Dõi Công Nợ Dự Án"]

    conn = get_db_connection()
    cursor = conn.cursor()

    if overwrite:
        cursor.execute("DELETE FROM project_receivables")
        conn.commit()

    imported_count = 0

    for r in range(2, 49):
        stt = ws.cell(r, 1).value
        project = ws.cell(r, 2).value
        client = ws.cell(r, 3).value
        c_code = ws.cell(r, 4).value
        contract_val = ws.cell(r, 5).value or 0
        net = ws.cell(r, 6).value or 0
        vat = ws.cell(r, 7).value or 0
        tax = ws.cell(r, 8).value or 0
        gross = ws.cell(r, 9).value or 0
        rec = ws.cell(r, 10).value or 0
        debt = ws.cell(r, 11).value or 0
        reply = ws.cell(r, 12).value
        due = ws.cell(r, 13).value
        paid = ws.cell(r, 14).value
        doc = ws.cell(r, 15).value
        status_raw = ws.cell(r, 16).value
        notes = ws.cell(r, 17).value

        # Skip completely blank rows
        if not project and not client and not c_code:
            continue

        # Data cleaning for missing project names in Darfon rows 27, 28, 29
        project_str = str(project or "").strip()
        client_str = str(client or "").strip()
        if not project_str and client_str:
            if r == 27:
                project_str = "30% Mở rộng MES Lite giai đoạn 2\n30% MES Lite 第二階段擴充"
            elif r == 28:
                project_str = "60% Mở rộng MES Lite giai đoạn 2\n60% MES Lite 第二階段擴充"
            elif r == 29:
                project_str = "10% Mở rộng MES Lite giai đoạn 2\n10% MES Lite 第二階段擴充"
            else:
                project_str = f"Hạng mục {client_str}"

        # Clean numeric
        try: net_val = float(net)
        except: net_val = 0.0

        try: vat_rate = float(vat)
        except: vat_rate = 0.0

        try: vat_amt = float(tax)
        except: vat_amt = round(net_val * vat_rate, 2)

        try: gross_val = float(gross)
        except: gross_val = round(net_val + vat_amt, 2)

        try:
            # FIX FORMULA BUG: In rows with =G+I, rec is gross + vat_rate (e.g. 5832000.08)
            # If rec is slightly over gross by vat_rate, round it down to gross
            rec_val = float(rec)
            if abs(rec_val - (gross_val + vat_rate)) < 0.5:
                rec_val = gross_val
        except:
            rec_val = 0.0

        try:
            debt_val = float(debt)
            if debt_val < 0 and debt_val > -1:  # Fix -0.08 bug
                debt_val = 0.0
        except:
            debt_val = max(0.0, gross_val - rec_val)

        # Standardize dates
        due_date_str = parse_flexible_date(due)
        paid_date_str = parse_flexible_date(paid)
        promised_date_str = parse_flexible_date(reply)

        # Determine clean status
        col_status = determine_collection_status(rec_val, gross_val, due_date_str, str(status_raw or ""))

        cursor.execute("""
            INSERT INTO project_receivables (
                order_no, project_name, customer_name, contract_code,
                total_contract_amount, net_amount, vat_rate, vat_amount,
                gross_amount, received_amount, remaining_debt,
                customer_promised_date, due_date, paid_date,
                doc_status, collection_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(stt) if stt and isinstance(stt, (int, float)) else None,
            project_str,
            client_str,
            str(c_code or "").strip() or None,
            float(contract_val or 0.0),
            net_val,
            vat_rate,
            vat_amt,
            gross_val,
            rec_val,
            debt_val,
            promised_date_str,
            due_date_str,
            paid_date_str,
            str(doc or "").strip() or None,
            col_status,
            str(notes or "").strip() or None,
        ))
        imported_count += 1

    conn.commit()
    conn.close()
    return imported_count
