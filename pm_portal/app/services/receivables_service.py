# -*- coding: utf-8 -*-
"""Service module for Project Receivables (AR) management and contract synchronization."""

import os
import re
import io
import json
import uuid
import time
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
    overdue_only: bool = False,
    order_by_urgency: bool = True
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

    # Sắp xếp theo độ gấp / độ ưu tiên giải quyết nếu order_by_urgency=True
    if order_by_urgency:
        def _urgency_sort_key(it):
            is_paid = it.get("collection_status") == "PAID" or bool(it.get("paid_date") and it.get("paid_date") != "-")
            if is_paid:
                p_ts = 0.0
                if it.get("paid_date") and it.get("paid_date") != "-":
                    try:
                        p_ts = datetime.strptime(str(it["paid_date"]).strip(), "%Y-%m-%d").timestamp()
                    except Exception:
                        pass
                return (5, -p_ts, -(float(it.get("gross_amount") or 0.0)))

            days_left = it.get("days_left")
            is_overdue = it.get("collection_status") in ("DELAYED", "OVERDUE") or (days_left is not None and days_left < 0)
            if is_overdue:
                d_ts = 9999999999.0
                if it.get("due_date") and it.get("due_date") != "-":
                    try:
                        d_ts = datetime.strptime(str(it["due_date"]).strip(), "%Y-%m-%d").timestamp()
                    except Exception:
                        pass
                debt = float(it.get("remaining_debt") or it.get("gross_amount") or 0.0)
                return (1, d_ts, -debt)

            is_urgent = it.get("collection_status") == "URGENT" or (days_left is not None and 0 <= days_left <= 7)
            if is_urgent:
                d_ts = 9999999999.0
                if it.get("due_date") and it.get("due_date") != "-":
                    try:
                        d_ts = datetime.strptime(str(it["due_date"]).strip(), "%Y-%m-%d").timestamp()
                    except Exception:
                        pass
                debt = float(it.get("remaining_debt") or it.get("gross_amount") or 0.0)
                return (2, d_ts, -debt)

            if it.get("due_date") and it.get("due_date") != "-":
                d_ts = 9999999999.0
                try:
                    d_ts = datetime.strptime(str(it["due_date"]).strip(), "%Y-%m-%d").timestamp()
                except Exception:
                    pass
                debt = float(it.get("remaining_debt") or it.get("gross_amount") or 0.0)
                return (3, d_ts, -debt)

            debt = float(it.get("remaining_debt") or it.get("gross_amount") or 0.0)
            return (4, 9999999999.0, -debt)

        results.sort(key=_urgency_sort_key)

    return results


def get_receivable(item_id: int) -> Optional[Dict[str, Any]]:
    """Get single receivable by ID (searches SQLite DB, Sample JSON, and Custom Upload datasets)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM project_receivables WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["days_left"] = calculate_days_left(d.get("due_date"))
            return d
    except Exception:
        pass

    # Fallback to Sample JSON dataset
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "receivables_sample_data.json")
    if os.path.exists(sample_path):
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_json = json.load(f)
            for it in sample_json.get("receivables", []):
                r_id = it.get("id") or it.get("order_no")
                if r_id == item_id:
                    d = dict(it)
                    d["id"] = item_id
                    d["days_left"] = calculate_days_left(d.get("due_date"))
                    return d
        except Exception:
            pass

    # Fallback to Uploaded files in CUSTOM_CHARTS_REGISTRY
    for entry in CUSTOM_CHARTS_REGISTRY.values():
        for it in entry.get("items", []):
            r_id = it.get("id") or it.get("order_no")
            if r_id == item_id:
                d = dict(it)
                d["id"] = item_id
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
    # Cập nhật mọi trường trong data kể cả None (để xóa ngày thanh toán / ghi chú / hạn)
    merged.update(data)

    net = float(merged.get("net_amount") or 0.0)
    vat_rate = float(merged.get("vat_rate") or 0.0)
    if "vat_rate" in data or "net_amount" in data:
        vat_amount = round(net * vat_rate, 2)
        gross = round(net + vat_amount, 2)
    else:
        vat_amount = float(merged.get("vat_amount") or round(net * vat_rate, 2))
        gross = float(merged.get("gross_amount") or round(net + vat_amount, 2))

    received = float(merged.get("received_amount") or 0.0)
    if "remaining_debt" in data:
        debt = float(data.get("remaining_debt") or 0.0)
    else:
        debt = max(0.0, gross - received)
    status = data.get("collection_status") or merged.get("collection_status") or determine_collection_status(received, gross, merged.get("due_date"))

    try:
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
                start_date = ?,
                payment_term_days = ?,
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
            merged.get("start_date"),
            merged.get("payment_term_days"),
            merged.get("customer_promised_date"),
            merged.get("due_date"),
            merged.get("paid_date"),
            merged.get("doc_status"),
            status,
            merged.get("notes"),
            item_id,
        ))

        # Synchronize linked contract milestone if exists
        linked_ms_id = merged.get("linked_milestone_id")
        if linked_ms_id:
            if merged.get("paid_date"):
                cursor.execute("""
                    UPDATE payment_milestones SET
                        triggered = 1,
                        status = 'PAID',
                        status_label = 'Đã thanh toán',
                        paid_date = ?
                    WHERE id = ?
                """, (merged.get("paid_date"), linked_ms_id))
            elif "paid_date" in data:
                cursor.execute("""
                    UPDATE payment_milestones SET
                        triggered = 0,
                        status = 'PENDING',
                        status_label = 'Chờ thanh toán',
                        paid_date = NULL
                    WHERE id = ?
                """, (linked_ms_id,))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected > 0:
            return True
    except Exception:
        pass

    # Fallback: update Sample JSON if item exists there
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "receivables_sample_data.json")
    if os.path.exists(sample_path):
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_json = json.load(f)
            found_sample = False
            for idx, it in enumerate(sample_json.get("receivables", [])):
                r_id = it.get("id") or it.get("order_no")
                if r_id == item_id:
                    it.update({
                        "project_name": merged.get("project_name"),
                        "customer_name": merged.get("customer_name"),
                        "contract_code": merged.get("contract_code"),
                        "net_amount": net,
                        "vat_rate": vat_rate,
                        "vat_amount": vat_amount,
                        "gross_amount": gross,
                        "received_amount": received,
                        "remaining_debt": debt,
                        "customer_promised_date": merged.get("customer_promised_date"),
                        "due_date": merged.get("due_date"),
                        "paid_date": merged.get("paid_date"),
                        "doc_status": merged.get("doc_status"),
                        "start_date": merged.get("start_date"),
                        "payment_term_days": merged.get("payment_term_days"),
                        "collection_status": status,
                        "notes": merged.get("notes")
                    })
                    found_sample = True
                    break
            if found_sample:
                with open(sample_path, "w", encoding="utf-8") as f:
                    json.dump(sample_json, f, ensure_ascii=False, indent=2)
                return True
        except Exception:
            pass

    # Fallback: update in CUSTOM_CHARTS_REGISTRY
    for entry in CUSTOM_CHARTS_REGISTRY.values():
        for it in entry.get("items", []):
            r_id = it.get("id") or it.get("order_no")
            if r_id == item_id:
                it.update({
                    "project_name": merged.get("project_name"),
                    "customer_name": merged.get("customer_name"),
                    "contract_code": merged.get("contract_code"),
                    "net_amount": net,
                    "vat_rate": vat_rate,
                    "vat_amount": vat_amount,
                    "gross_amount": gross,
                    "received_amount": received,
                    "remaining_debt": debt,
                    "customer_promised_date": merged.get("customer_promised_date"),
                    "due_date": merged.get("due_date"),
                    "paid_date": merged.get("paid_date"),
                    "doc_status": merged.get("doc_status"),
                    "collection_status": status,
                    "notes": merged.get("notes")
                })
                return True

    return False


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
        # Revert to pending/delayed with debt re-evaluated consistently
        cur_received = float(item.get("received_amount") or 0.0)
        new_received = 0.0 if cur_received >= gross else cur_received
        new_debt = max(0.0, gross - new_received)
        cursor.execute("""
            UPDATE project_receivables SET
                collection_status = ?,
                received_amount = ?,
                remaining_debt = ?,
                paid_date = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, new_received, new_debt, item_id))

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
    """Delete a single receivable milestone record across DB, Sample JSON, and Custom Uploads."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM project_receivables WHERE id = ?", (item_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected > 0:
            return True
    except Exception:
        pass

    # Fallback to Sample JSON
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "receivables_sample_data.json")
    if os.path.exists(sample_path):
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_json = json.load(f)
            orig_len = len(sample_json.get("receivables", []))
            sample_json["receivables"] = [
                it for it in sample_json.get("receivables", [])
                if (it.get("id") or it.get("order_no")) != item_id
            ]
            if len(sample_json["receivables"]) < orig_len:
                with open(sample_path, "w", encoding="utf-8") as f:
                    json.dump(sample_json, f, ensure_ascii=False, indent=2)
                return True
        except Exception:
            pass

    # Fallback to CUSTOM_CHARTS_REGISTRY
    for entry in CUSTOM_CHARTS_REGISTRY.values():
        orig_len = len(entry.get("items", []))
        entry["items"] = [
            it for it in entry.get("items", [])
            if (it.get("id") or it.get("order_no")) != item_id
        ]
        if len(entry["items"]) < orig_len:
            return True

    return False


def sync_from_existing_contracts(clear_first: bool = False, clear_all: bool = False) -> int:
    """Synchronize milestones from 'contracts' and 'payment_milestones' tables into receivables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if clear_all:
        cursor.execute("DELETE FROM project_receivables")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='project_receivables'")
        conn.commit()
    elif clear_first:
        # Chỉ xóa các mốc đồng bộ từ hợp đồng, bảo toàn 100% các công nợ độc lập không liên kết hợp đồng
        cursor.execute("DELETE FROM project_receivables WHERE linked_milestone_id IS NOT NULL")
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


# ==============================================================================
# WEEKLY COMPARISON & HISTORICAL SNAPSHOT SERVICE
# ==============================================================================

def save_weekly_snapshot(snapshot_date: Optional[str] = None, note: Optional[str] = None) -> int:
    """Capture current receivables state into receivables_weekly_snapshots table."""
    if not snapshot_date:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")
    
    dt = datetime.strptime(snapshot_date, "%Y-%m-%d").date()
    iso_year, iso_week, _ = dt.isocalendar()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing snapshot for this exact date to allow idempotent re-snapshots
    cursor.execute("DELETE FROM receivables_weekly_snapshots WHERE snapshot_date = ?", (snapshot_date,))

    cursor.execute("SELECT * FROM project_receivables ORDER BY order_no ASC, id ASC")
    items = cursor.fetchall()

    saved_count = 0
    for r in items:
        item = dict(r)
        cursor.execute("""
            INSERT INTO receivables_weekly_snapshots (
                snapshot_date, week_number, year, receivable_id,
                project_name, customer_name, contract_code,
                gross_amount, received_amount, remaining_debt,
                customer_promised_date, due_date, paid_date,
                collection_status, notes, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_date,
            iso_week,
            iso_year,
            item["id"],
            item.get("project_name") or "",
            item.get("customer_name") or "",
            item.get("contract_code"),
            float(item.get("gross_amount") or 0.0),
            float(item.get("received_amount") or 0.0),
            float(item.get("remaining_debt") or 0.0),
            item.get("customer_promised_date"),
            item.get("due_date"),
            item.get("paid_date"),
            item.get("collection_status") or "PENDING",
            item.get("notes"),
            note
        ))
        saved_count += 1

    conn.commit()
    conn.close()
    return saved_count


def _reconstruct_item_state_at_date(item: Dict[str, Any], as_of_date_str: str) -> Dict[str, Any]:
    """Reconstruct exact financial and status state of a single receivable at as_of_date."""
    as_of = datetime.strptime(as_of_date_str, "%Y-%m-%d").date()
    gross = float(item.get("gross_amount") or 0.0)
    current_received = float(item.get("received_amount") or 0.0)

    paid_date_str = parse_flexible_date(item.get("paid_date"))
    due_date_str = parse_flexible_date(item.get("due_date"))
    promised_date_str = parse_flexible_date(item.get("customer_promised_date"))

    # 1. Determine if already paid on or prior to as_of
    is_paid_at_date = False
    if paid_date_str:
        try:
            p_date = datetime.strptime(paid_date_str, "%Y-%m-%d").date()
            if p_date <= as_of:
                is_paid_at_date = True
        except Exception:
            pass

    if is_paid_at_date:
        rec_at_date = gross if current_received >= gross else current_received
        debt_at_date = max(0.0, gross - rec_at_date)
        status_at_date = "PAID"
        days_left_at_date = None
    else:
        rec_at_date = 0.0
        debt_at_date = gross
        days_left_at_date = None
        status_at_date = "PENDING"

        # Check due date relative to as_of
        if due_date_str:
            try:
                d_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                days_left_at_date = (d_date - as_of).days
                if days_left_at_date < 0:
                    status_at_date = "OVERDUE"
                elif days_left_at_date <= 7:
                    status_at_date = "URGENT"
                else:
                    status_at_date = "PENDING"
            except Exception:
                pass
        elif promised_date_str:
            try:
                pr_date = datetime.strptime(promised_date_str, "%Y-%m-%d").date()
                diff = (pr_date - as_of).days
                if diff < 0:
                    status_at_date = "OVERDUE"
                elif diff <= 7:
                    status_at_date = "URGENT"
            except Exception:
                pass

    return {
        "received_amount": round(rec_at_date, 2),
        "remaining_debt": round(debt_at_date, 2),
        "collection_status": status_at_date,
        "days_left": days_left_at_date,
        "is_paid": is_paid_at_date,
        "is_overdue": status_at_date == "OVERDUE",
    }



# In-memory registry for uploaded standalone department files (zero DB pollution)
CUSTOM_CHARTS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def parse_external_receivables_file(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """Parse an uploaded external Excel (.xlsx/.xls) or JSON file into standardized receivable milestone records.
    Designed to allow any department to upload their own file and instantly generate comparison charts
    WITHOUT touching or altering the main company database.
    """
    filename_lower = filename.lower()
    items: List[Dict[str, Any]] = []

    if filename_lower.endswith(".json"):
        raw = json.loads(file_bytes.decode("utf-8"))
        if isinstance(raw, dict) and "receivables" in raw:
            raw_list = raw["receivables"]
        elif isinstance(raw, list):
            raw_list = raw
        else:
            raw_list = []
        for idx, r in enumerate(raw_list):
            gross = float(r.get("gross_amount") or r.get("amount") or 0.0)
            rec = float(r.get("received_amount") or 0.0)
            debt = float(r.get("remaining_debt") or max(0.0, gross - rec))
            items.append({
                "id": r.get("id") or idx + 1,
                "order_no": r.get("order_no") or idx + 1,
                "project_name": r.get("project_name") or r.get("project") or f"Hạng mục {idx + 1}",
                "customer_name": r.get("customer_name") or r.get("customer") or "Khách hàng",
                "contract_code": r.get("contract_code") or r.get("contract") or "-",
                "gross_amount": gross,
                "gross_formatted": format_currency_vn(gross),
                "received_amount": rec,
                "received_formatted": format_currency_vn(rec),
                "remaining_debt": debt,
                "debt_formatted": format_currency_vn(debt),
                "due_date": parse_flexible_date(r.get("due_date")) or "-",
                "paid_date": parse_flexible_date(r.get("paid_date")) or "-",
                "customer_promised_date": parse_flexible_date(r.get("customer_promised_date")) or "-",
                "doc_status": r.get("doc_status") or "-",
                "collection_status": r.get("collection_status") or "PENDING",
                "notes": r.get("notes") or "-",
            })
        return items

    # Parse Excel Workbook
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    if "3. Theo Dõi Công Nợ Dự Án" in wb.sheetnames:
        ws = wb["3. Theo Dõi Công Nợ Dự Án"]
    else:
        ws = wb.active

    # Detect header row
    header_row = 1
    col_map: Dict[str, int] = {}
    for r in range(1, min(6, ws.max_row + 1)):
        row_vals = [str(ws.cell(r, c).value or "").strip().lower() for c in range(1, min(30, ws.max_column + 1))]
        joined = " ".join(row_vals)
        if any(kw in joined for kw in ["dự án", "khách hàng", "khoản thanh toán", "合約", "專案", "hợp đồng", "phải thu"]):
            header_row = r
            for c_idx, val in enumerate(row_vals, 1):
                if any(k in val for k in ["ngày đã thu", "ngày thu", "paid date", "paid_date", "已收日期", "已收款日期"]):
                    col_map["paid"] = c_idx
                elif any(k in val for k in ["phản hồi", "ngày thanh toán", "khách hẹn", "promised", "約定"]):
                    col_map["promised"] = c_idx
                elif any(k in val for k in ["hạn thanh toán", "ngày đến hạn", "hạn", "due", "deadline", "到期日", "期限"]):
                    col_map["due"] = c_idx
                elif any(k in val for k in ["số tiền nhận được", "tiền nhận được", "đã nhận", "đã thu", "received", "已收"]):
                    col_map["received"] = c_idx
                elif any(k in val for k in ["còn nợ", "chưa thu", "remaining", "debt", "未收"]):
                    col_map["debt"] = c_idx
                elif any(k in val for k in ["dự án", "project", "專案", "hạng mục"]):
                    col_map["project"] = c_idx
                elif any(k in val for k in ["khách hàng", "customer", "客戶"]):
                    col_map["customer"] = c_idx
                elif any(k in val for k in ["tổng giá trị", "giá trị hđ", "tổng hđ"]):
                    col_map["total_contract"] = c_idx
                elif any(k in val for k in ["số hợp đồng", "mã hợp đồng", "mã hđ", "số hđ", "po", "contract_code", "contract", "合約號碼", "合約"]):
                    col_map["contract"] = c_idx
                elif any(k in val for k in ["chưa thuế", "net", "未稅"]):
                    col_map["net"] = c_idx
                elif any(k in val for k in ["vat", "thuế suất", "增值稅"]):
                    col_map["vat"] = c_idx
                elif any(k in val for k in ["phải thu", "khoản thanh toán", "tổng tiền", "gross", "bao gồm thuế", "含稅", "金額"]):
                    col_map["gross"] = c_idx
                elif any(k in val for k in ["chứng từ", "pkl", "inv", "hóa đơn", "單據"]):
                    col_map["doc"] = c_idx
                elif any(k in val for k in ["trạng thái", "status", "狀態"]):
                    col_map["status"] = c_idx
                elif any(k in val for k in ["ghi chú", "đôn đốc", "notes", "note", "備註"]):
                    col_map["notes"] = c_idx
            break

    item_id = 1
    for r in range(header_row + 1, ws.max_row + 1):
        def _get_val(k):
            col = col_map.get(k)
            return ws.cell(r, col).value if col else None

        proj = _get_val("project")
        cust = _get_val("customer")
        c_code = _get_val("contract")
        gross = _get_val("gross") or _get_val("net") or 0.0
        rec = _get_val("received") or 0.0
        debt = _get_val("debt") or 0.0
        due = _get_val("due")
        paid = _get_val("paid")
        promised = _get_val("promised")
        doc = _get_val("doc")
        notes = _get_val("notes")

        if not proj and not cust and not c_code and not gross:
            continue

        try: gross_amt = float(gross)
        except: gross_amt = 0.0

        try: rec_amt = float(rec)
        except: rec_amt = 0.0

        try: debt_amt = float(debt)
        except: debt_amt = max(0.0, gross_amt - rec_amt)

        due_date_str = parse_flexible_date(due)
        paid_date_str = parse_flexible_date(paid)
        promised_date_str = parse_flexible_date(promised)

        if rec_amt >= gross_amt and gross_amt > 0:
            status = "PAID"
        elif paid_date_str:
            status = "PAID"
        elif due_date_str:
            try:
                d_obj = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                if d_obj < today: status = "OVERDUE"
                elif (d_obj - today).days <= 7: status = "URGENT"
                else: status = "PENDING"
            except:
                status = "PENDING"
        else:
            status = "PENDING"

        items.append({
            "id": item_id,
            "order_no": item_id,
            "project_name": str(proj or f"Hạng mục {item_id}").strip(),
            "customer_name": str(cust or "Khách hàng").strip(),
            "contract_code": str(c_code or "-").strip() if c_code else "-",
            "gross_amount": gross_amt,
            "gross_formatted": format_currency_vn(gross_amt),
            "received_amount": rec_amt,
            "received_formatted": format_currency_vn(rec_amt),
            "remaining_debt": debt_amt,
            "debt_formatted": format_currency_vn(debt_amt),
            "due_date": due_date_str or "-",
            "paid_date": paid_date_str or "-",
            "customer_promised_date": promised_date_str or "-",
            "doc_status": str(doc or "-").strip(),
            "collection_status": status,
            "notes": str(notes or "-").strip(),
        })
        item_id += 1

    return items


def register_custom_receivables_file(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Register an uploaded file into in-memory custom charts registry."""
    items = parse_external_receivables_file(file_bytes, filename)
    if not items:
        raise ValueError("Không trích xuất được dữ liệu công nợ hợp lệ từ tập tin này.")
    upload_id = f"upload_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    CUSTOM_CHARTS_REGISTRY[upload_id] = {
        "filename": filename,
        "uploaded_at": datetime.now().isoformat(),
        "items": items
    }
    return upload_id, items

def get_weekly_comparison_data(
    prev_date: Optional[str] = None,
    curr_date: Optional[str] = None,
    customer: Optional[str] = None,
    contract: Optional[str] = None,
    data_source: str = "db",
    upload_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute side-by-side comparison between previous week and current week."""
    from datetime import timedelta
    today = datetime.now().date()

    # Default prev_date = previous Sunday
    if not prev_date:
        days_to_last_sunday = today.weekday() + 1
        prev_date = (today - timedelta(days=days_to_last_sunday)).strftime("%Y-%m-%d")

    # Default curr_date = current Sunday (or today if ahead)
    if not curr_date:
        curr_sunday = today + timedelta(days=(6 - today.weekday()))
        curr_date = curr_sunday.strftime("%Y-%m-%d")

    # Format human-friendly labels (e.g. 'Chủ Nhật, 18/10/2026')
    try:
        p_dt = datetime.strptime(prev_date, "%Y-%m-%d")
        prev_label = f"Cuối Tuần Trước ({p_dt.strftime('%d/%m/%Y')})"
    except Exception:
        prev_label = f"Tuần Trước ({prev_date})"

    try:
        c_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        curr_label = f"Cuối Tuần Này ({c_dt.strftime('%d/%m/%Y')})"
    except Exception:
        curr_label = f"Tuần Này ({curr_date})"

    # Determine Data Source: 'db' (Original live DB), 'sample' (Curated JSON demo), 'upload' (Standalone File)
    data_source_meta = {"type": data_source, "name": "Dữ liệu gốc hệ thống"}

    if data_source == "upload" and upload_id and upload_id in CUSTOM_CHARTS_REGISTRY:
        entry = CUSTOM_CHARTS_REGISTRY[upload_id]
        all_raw_items = [dict(it) for it in entry["items"]]
        data_source_meta = {
            "type": "upload",
            "name": f"File: {entry['filename']}",
            "filename": entry["filename"],
            "upload_id": upload_id,
            "badge": "📂 File Tải Lên (獨立檔案)"
        }
    elif data_source == "sample":
        sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "receivables_sample_data.json")
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_json = json.load(f)
            all_raw_items = [dict(it) for it in sample_json.get("receivables", [])]
        except Exception:
            all_raw_items = list_receivables()
        data_source_meta = {
            "type": "sample",
            "name": "Dữ liệu mẫu chuẩn hóa",
            "badge": "🧪 Dữ Liệu Mẫu (示範數據)"
        }
    else:
        # Default: 'db' (Live SQLite database records)
        all_raw_items = list_receivables(customer=customer, order_by_urgency=False)
        data_source_meta = {
            "type": "db",
            "name": "Dữ liệu gốc thực tế (Database)",
            "badge": "📊 Dữ Liệu Gốc (原始數據)"
        }

    # Apply customer & contract filters
    if customer and customer != "all":
        c_low = customer.lower()
        all_raw_items = [it for it in all_raw_items if c_low in str(it.get("customer_name") or "").lower()]
    if contract and contract != "all":
        all_raw_items = [it for it in all_raw_items if str(it.get("contract_code") or "").strip() == contract.strip()]

    # Check snapshots only for DB data source
    prev_snapshot_rows = {}
    curr_snapshot_rows = {}
    if data_source == "db":
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM receivables_weekly_snapshots WHERE snapshot_date = ?", (prev_date,))
            prev_snapshot_rows = {row["receivable_id"]: dict(row) for row in cursor.fetchall()}
            cursor.execute("SELECT * FROM receivables_weekly_snapshots WHERE snapshot_date = ?", (curr_date,))
            curr_snapshot_rows = {row["receivable_id"]: dict(row) for row in cursor.fetchall()}
            conn.close()
        except Exception:
            pass

    prev_items = []
    curr_items = []
    changes_list = []

    total_gross = 0.0
    prev_total_received = 0.0
    prev_total_debt = 0.0
    curr_total_received = 0.0
    curr_total_debt = 0.0

    prev_counts = {"PAID": 0, "OVERDUE": 0, "URGENT": 0, "PENDING": 0}
    curr_counts = {"PAID": 0, "OVERDUE": 0, "URGENT": 0, "PENDING": 0}

    newly_paid_count = 0
    newly_paid_amount = 0.0
    newly_overdue_count = 0
    newly_overdue_amount = 0.0

    for idx, it in enumerate(all_raw_items):
        rec_id = it.get("id") or it.get("order_no") or (idx + 1)
        it["id"] = rec_id
        gross = float(it.get("gross_amount") or 0.0)
        total_gross += gross

        # Prev State (From snapshot if exists, else reconstructed)
        if rec_id in prev_snapshot_rows:
            snap = prev_snapshot_rows[rec_id]
            st_p = snap.get("collection_status") or "PENDING"
            if st_p == "DELAYED": st_p = "OVERDUE"
            rec_p = float(snap.get("received_amount") or 0.0)
            debt_p = float(snap.get("remaining_debt") or max(0.0, gross - rec_p))
            days_p = calculate_days_left(snap.get("due_date"))
        else:
            rec_state_p = _reconstruct_item_state_at_date(it, prev_date)
            st_p = rec_state_p["collection_status"]
            rec_p = rec_state_p["received_amount"]
            debt_p = rec_state_p["remaining_debt"]
            days_p = rec_state_p["days_left"]

        # Curr State (From snapshot if exists, else reconstructed)
        if rec_id in curr_snapshot_rows:
            snap_c = curr_snapshot_rows[rec_id]
            st_c = snap_c.get("collection_status") or "PENDING"
            if st_c == "DELAYED": st_c = "OVERDUE"
            rec_c = float(snap_c.get("received_amount") or 0.0)
            debt_c = float(snap_c.get("remaining_debt") or max(0.0, gross - rec_c))
            days_c = calculate_days_left(snap_c.get("due_date"))
        else:
            rec_state_c = _reconstruct_item_state_at_date(it, curr_date)
            st_c = rec_state_c["collection_status"]
            rec_c = rec_state_c["received_amount"]
            debt_c = rec_state_c["remaining_debt"]
            days_c = rec_state_c["days_left"]

        prev_total_received += rec_p
        prev_total_debt += debt_p
        curr_total_received += rec_c
        curr_total_debt += debt_c

        prev_counts[st_p] = prev_counts.get(st_p, 0) + 1
        curr_counts[st_c] = curr_counts.get(st_c, 0) + 1

        # Detect changes between prev and curr
        is_newly_paid = (st_p != "PAID" and st_c == "PAID")
        is_newly_overdue = (st_p != "OVERDUE" and st_c == "OVERDUE")
        rec_delta = round(rec_c - rec_p, 2)

        change_type = "UNCHANGED"
        change_badge_text = ""
        change_badge_class = ""

        if is_newly_paid:
            change_type = "NEWLY_PAID"
            change_badge_text = f"🎉 Vừa thu xong (+{format_currency_vn(rec_delta)})"
            change_badge_class = "badge-newly-paid"
            newly_paid_count += 1
            newly_paid_amount += rec_delta
        elif is_newly_overdue:
            change_type = "NEWLY_OVERDUE"
            change_badge_text = "🚨 Đến hạn chưa thu"
            change_badge_class = "badge-newly-overdue"
            newly_overdue_count += 1
            newly_overdue_amount += debt_c
        elif rec_delta > 0:
            change_type = "PARTIAL_PAID"
            change_badge_text = f"💵 Thu thêm (+{format_currency_vn(rec_delta)})"
            change_badge_class = "badge-partial-paid"
            newly_paid_amount += rec_delta
        elif st_p == "PENDING" and st_c == "URGENT":
            change_type = "BECOMING_URGENT"
            change_badge_text = "⚡ Sắp đến hạn (<=7 ngày)"
            change_badge_class = "badge-becoming-urgent"

        # Build clean item representation
        base_info = {
            "id": it["id"],
            "project_name": it.get("project_name"),
            "customer_name": it.get("customer_name"),
            "contract_code": it.get("contract_code") or "-",
            "gross_amount": gross,
            "gross_formatted": format_currency_vn(gross),
            "due_date": it.get("due_date"),
            "paid_date": it.get("paid_date"),
            "customer_promised_date": it.get("customer_promised_date"),
            "doc_status": it.get("doc_status") or "-",
            "notes": it.get("notes") or "-",
        }

        prev_item = dict(base_info)
        prev_item.update({
            "received_amount": rec_p,
            "received_formatted": format_currency_vn(rec_p),
            "remaining_debt": debt_p,
            "debt_formatted": format_currency_vn(debt_p),
            "collection_status": st_p,
            "days_left": days_p,
            "percentage_collected": round((rec_p / gross * 100), 1) if gross > 0 else 0.0,
        })
        prev_items.append(prev_item)

        curr_item = dict(base_info)
        curr_item.update({
            "received_amount": rec_c,
            "received_formatted": format_currency_vn(rec_c),
            "remaining_debt": debt_c,
            "debt_formatted": format_currency_vn(debt_c),
            "collection_status": st_c,
            "days_left": days_c,
            "percentage_collected": round((rec_c / gross * 100), 1) if gross > 0 else 0.0,
            "change_type": change_type,
            "change_badge_text": change_badge_text,
            "change_badge_class": change_badge_class,
            "received_delta": rec_delta,
            "received_delta_formatted": format_currency_vn(rec_delta),
            "is_newly_paid": is_newly_paid,
            "is_newly_overdue": is_newly_overdue,
        })
        curr_items.append(curr_item)

        if change_type != "UNCHANGED":
            changes_list.append({
                "id": it["id"],
                "customer_name": it.get("customer_name"),
                "project_name": it.get("project_name"),
                "contract_code": it.get("contract_code") or "-",
                "gross_amount": gross,
                "gross_formatted": format_currency_vn(gross),
                "status_prev": st_p,
                "status_curr": st_c,
                "change_type": change_type,
                "change_badge_text": change_badge_text,
                "change_badge_class": change_badge_class,
                "received_prev": rec_p,
                "received_curr": rec_c,
                "received_delta": rec_delta,
                "received_delta_formatted": format_currency_vn(rec_delta),
                "due_date": it.get("due_date"),
                "paid_date": it.get("paid_date"),
                "notes": it.get("notes") or "",
            })

    prev_rate = round((prev_total_received / total_gross * 100), 1) if total_gross > 0 else 0.0
    curr_rate = round((curr_total_received / total_gross * 100), 1) if total_gross > 0 else 0.0
    rate_delta = round(curr_rate - prev_rate, 1)

    net_increase = round(curr_total_received - prev_total_received, 2)
    debt_reduction = round(prev_total_debt - curr_total_debt, 2)

    # Build grouped contracts_comparison (1 horizontal bar = 1 Contract/Project, divided into segments by %)
    contract_groups_map: Dict[str, List[int]] = {}
    for idx in range(len(curr_items)):
        c_code = str(curr_items[idx].get("contract_code") or "").strip()
        if not c_code or c_code in ("-", "None", "null"):
            c_key = f"PROJ_{curr_items[idx].get('id')}"
        else:
            c_key = c_code
        contract_groups_map.setdefault(c_key, []).append(idx)

    def _split_bilingual_lines(raw_text: Optional[str]) -> Tuple[str, str]:
        if not raw_text or str(raw_text).strip() in ("-", "None", "null", ""):
            return ("-", "-")
        parts = [p.strip() for p in str(raw_text).split("\n") if p.strip()]
        if len(parts) >= 2:
            return (parts[0], parts[1])
        elif len(parts) == 1:
            return (parts[0], parts[0])
        return ("-", "-")

    def _clean_project_display_name_bilingual(raw_proj: str, c_code: str = "") -> Tuple[str, str]:
        if c_code == "HMV021020260001":
            return ("Hệ thống kết nối máy SMB (Cheng Feng)", "SMB 機聯網系統 (承豐樂華)")
        if c_code == "HMV060620250001":
            return ("Phần cứng kết nối máy SMB (Vonmax)", "SMB 機聯網硬體 (弘聲)")
        if c_code == "HMSY200720260001":
            return ("Phương án nâng cấp trực quan hóa SMB", "SMB 可視化升級方案 (正揚)")
        if c_code == "HMSY200720260002":
            return ("Xây dựng mạng khu vực nhà máy SMB", "SMB 廠區網路建置 (正揚)")
        if c_code == "HMV151020250001":
            return ("Phần mềm quản lý RFID", "RFID 管理軟體系統 (CX-Tech)")
        if c_code == "HMV050520260001":
            return ("Mua phần cứng thẻ RFID (Tag)", "RFID 硬體採購/Tag (CX-Tech)")
        if c_code == "DFV20260505-P1":
            return ("Mở rộng MES Lite giai đoạn 1", "MES Lite 第一階段擴充 (Darfon)")
        if c_code == "HM-EMS-JG-2026":
            return ("Tiết kiệm điện nhà xưởng 1 ép nhựa", "景光1廠注塑區節能專案")
        if c_code == "PO-VM-EMS-001":
            return ("Hệ thống quản lý năng lượng EMS", "弘聲廠 EMS 能源管理系統")
        if c_code == "HMV22092026SY0001":
            return ("Quy hoạch mạng IIoT nhà máy SEIYO", "SEIYO 廠 IIoT 機聯網規劃")
        if c_code == "PO-CX-PIN-01":
            return ("Thẻ RFID chịu nhiệt độ cao đợt 1", "耐高溫 RFID 標籤第一批")
        if c_code == "PO-CX-PIN-02":
            return ("Thẻ RFID chịu nhiệt độ cao đợt 2", "耐高溫 RFID 標籤第二批")
        if c_code == "SC-2026-006":
            return ("Sửa chữa phần cứng thẻ RFID (CX)", "RFID 硬體標籤維修（CX）")
        if c_code == "SC-2026-005":
            return ("Sửa chữa đầu đọc thẻ RFID RFR900 (CX)", "RFR900 RFID 讀卡器維修（CX）")
        if c_code == "HD-20261013-001":
            return ("Hệ thống MES Lite sản xuất", "MES Lite 生產製造管理系統")

        lines = [l.strip() for l in str(raw_proj or "").split("\n") if l.strip()]
        if len(lines) >= 2:
            vi_l, zh_l = lines[0], lines[1]
            vi_clean = re.sub(r"^(Đợt\s*\d+\s*(\(\d+%?\))?\s*[-–:]\s*|\d+%\s*[-–:]?\s*)", "", vi_l, flags=re.IGNORECASE).strip()
            vi_clean = re.sub(r"\s*[-–]\s*\d+%.*$", "", vi_clean).strip()
            vi_clean = re.sub(r"「.*$", "", vi_clean).strip()
            zh_clean = re.sub(r"^(\d+%\s*|第\s*\d+\s*期\s*[-–:]?\s*)", "", zh_l).strip()
            return (vi_clean or vi_l, zh_clean or zh_l)
        elif len(lines) == 1:
            line = lines[0]
            vi_clean = re.sub(r"^(Đợt\s*\d+\s*(\(\d+%?\))?\s*[-–:]\s*|\d+%\s*[-–:]?\s*)", "", line, flags=re.IGNORECASE).strip()
            vi_clean = re.sub(r"\s*[-–]\s*\d+%.*$", "", vi_clean).strip()
            vi_clean = re.sub(r"「.*$", "", vi_clean).strip()
            return (vi_clean or line, vi_clean or line)
        return ("Dự án", "專案")

    def _format_bilingual_customer(cust_raw: str) -> Tuple[str, str]:
        if not cust_raw:
            return ("-", "-")
        cust_s = str(cust_raw).strip()
        low = cust_s.lower()
        if "cheng feng" in low or "承豐樂華" in cust_s:
            return ("CÔNG TY TNHH CHENG FENG LE HUA", "承豐樂華有限責任公司 (Cheng Feng)")
        if "cx technology" in low or "trung hưng" in low:
            return ("CÔNG TY TNHH CX TECHNOLOGY (VIỆT NAM)", "台灣中興電工 (CX Technology VN)")
        if "vonmax" in low or "hoằng thanh" in low or "弘聲" in cust_s:
            return ("CÔNG TY TNHH VONMAX VIỆT NAM", "弘聲科技有限責任公司 (Vonmax VN)")
        if "seiyo" in low or "chính dương" in low or "正揚" in cust_s:
            return ("CÔNG TY TNHH SEIYO VIỆT NAM", "正揚有限責任公司 (SEIYO VN)")
        if "jinxun" in low or "kim tấn" in low or "金迅" in cust_s:
            return ("CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM", "金迅科技有限公司 (Jinxun VN)")
        if "jiyang" in low or "cát dương" in low or "佶陽" in cust_s:
            return ("CÔNG TY TNHH JIYANG VIỆT NAM", "佶陽有限責任公司 (Jiyang VN)")
        if "darfon" in low or "đạt phương" in low or "達方" in cust_s:
            return ("Darfon Electronics", "達方電子 (Darfon Electronics)")
        if "jing guang" in low or "cảnh quang" in low or "景光" in cust_s:
            return ("JING GUANG ELECTRONICS", "景光電子 (Jing Guang Electronics)")
        return (cust_s, cust_s)

    status_dict_bilingual = {
        "PAID": {"vi": "Đã thu xong", "zh": "已全額收款"},
        "OVERDUE": {"vi": "Quá hạn chưa thu", "zh": "已逾期未收款"},
        "URGENT": {"vi": "Sắp đến hạn (<=7 ngày)", "zh": "即將到期（<=7天）"},
        "PENDING": {"vi": "Chưa đến hạn", "zh": "尚未到期"},
    }

    contracts_comparison = []
    for c_key, indices in contract_groups_map.items():
        first_curr = curr_items[indices[0]]
        c_code_disp = first_curr.get("contract_code") if not c_key.startswith("PROJ_") else "-"
        proj_title_vi, proj_title_zh = _clean_project_display_name_bilingual(first_curr.get("project_name") or "", c_code_disp)
        cust_name_vi, cust_name_zh = _format_bilingual_customer(first_curr.get("customer_name") or "-")

        group_gross = sum(float(curr_items[i].get("gross_amount") or 0.0) for i in indices)
        group_prev_rec = sum(float(prev_items[i].get("received_amount") or 0.0) for i in indices)
        group_curr_rec = sum(float(curr_items[i].get("received_amount") or 0.0) for i in indices)

        seg_count = len(indices)
        segments = []
        accum_pct = 0.0
        has_change = False
        has_overdue_curr = False

        # Enforce strict milestone dependency:
        # Giai đoạn 1 chưa thanh toán thì giai đoạn 2 & 3 chưa thể bắt đầu hay đến hạn, bắt buộc là PENDING
        prev_all_paid_p = True
        prev_all_paid_c = True

        for s_idx, item_idx in enumerate(indices):
            p_it = prev_items[item_idx]
            c_it = curr_items[item_idx]
            seg_gross = float(c_it.get("gross_amount") or 0.0)

            # Check milestone sequence for prev week
            p_status = p_it.get("collection_status")
            if not prev_all_paid_p and p_status != "PAID":
                p_status = "PENDING"
            if p_status != "PAID":
                prev_all_paid_p = False

            # Check milestone sequence for curr week
            c_status = c_it.get("collection_status")
            if not prev_all_paid_c and c_status != "PAID":
                c_status = "PENDING"
            if c_status != "PAID":
                prev_all_paid_c = False

            if group_gross > 0:
                if s_idx == seg_count - 1:
                    w_pct = round(max(0.0, 100.0 - accum_pct), 2)
                else:
                    w_pct = round((seg_gross / group_gross) * 100.0, 2)
                    accum_pct += w_pct
            else:
                w_pct = round(100.0 / seg_count, 2)

            ch_type = c_it.get("change_type")
            ch_badge_text = c_it.get("change_badge_text")
            # If sequential rule forced c_status to PENDING from OVERDUE/URGENT, reset change
            if c_status == "PENDING" and c_it.get("collection_status") in ("OVERDUE", "URGENT"):
                ch_type = "UNCHANGED"
                ch_badge_text = ""

            if ch_type != "UNCHANGED":
                has_change = True
            if c_status == "OVERDUE":
                has_overdue_curr = True

            # Parse bilingual fields for segment
            raw_ms_name = c_it.get("project_name") or f"Khoản {s_idx + 1}"
            ms_vi, ms_zh = _split_bilingual_lines(raw_ms_name)
            doc_vi, doc_zh = _split_bilingual_lines(c_it.get("doc_status"))
            notes_vi, notes_zh = _split_bilingual_lines(c_it.get("notes"))

            prev_st_info = status_dict_bilingual.get(p_status, {"vi": p_status, "zh": p_status})
            curr_st_info = status_dict_bilingual.get(c_status, {"vi": c_status, "zh": c_status})

            ch_badge_vi = ch_badge_text or ""
            ch_badge_zh = ""
            rec_delta_fmt = c_it.get("received_delta_formatted") or ""
            if ch_type == "NEWLY_PAID":
                ch_badge_zh = f"🎉 本週成功回收 (+{rec_delta_fmt})"
            elif ch_type == "NEWLY_OVERDUE":
                ch_badge_zh = "🚨 本週到期尚未收款（請優先催討）"
            elif ch_type == "BECOMING_URGENT":
                ch_badge_zh = "⚡ 7天內即將到期（需提前提醒客戶）"
            elif ch_type == "PARTIAL_PAID":
                ch_badge_zh = f"💵 本週部分回款 (+{rec_delta_fmt})"

            segments.append({
                "id": c_it["id"],
                "seg_index": s_idx + 1,
                "seg_total": seg_count,
                "width_pct": w_pct,
                "milestone_name": raw_ms_name,
                "milestone_name_vi": ms_vi,
                "milestone_name_zh": ms_zh,
                "gross_amount": seg_gross,
                "gross_formatted": c_it.get("gross_formatted"),
                "due_date": c_it.get("due_date") or "-",
                "start_date": c_it.get("start_date") or "-",
                "payment_term_days": c_it.get("payment_term_days"),
                "paid_date": c_it.get("paid_date") or "-",
                "customer_promised_date": c_it.get("customer_promised_date") or "-",
                "doc_status": c_it.get("doc_status") or "-",
                "doc_status_vi": doc_vi,
                "doc_status_zh": doc_zh,
                "notes": c_it.get("notes") or "-",
                "notes_vi": notes_vi,
                "notes_zh": notes_zh,
                # Prev Week State
                "prev_status": p_status,
                "prev_status_label_vi": prev_st_info["vi"],
                "prev_status_label_zh": prev_st_info["zh"],
                "prev_received": p_it.get("received_amount"),
                "prev_received_formatted": p_it.get("received_formatted"),
                "prev_debt": p_it.get("remaining_debt"),
                "prev_debt_formatted": p_it.get("debt_formatted"),
                "prev_days_left": p_it.get("days_left"),
                # Curr Week State
                "curr_status": c_status,
                "curr_status_label_vi": curr_st_info["vi"],
                "curr_status_label_zh": curr_st_info["zh"],
                "curr_received": c_it.get("received_amount"),
                "curr_received_formatted": c_it.get("received_formatted"),
                "curr_debt": c_it.get("remaining_debt"),
                "curr_debt_formatted": c_it.get("debt_formatted"),
                "curr_days_left": c_it.get("days_left"),
                "change_type": ch_type,
                "change_badge_text": ch_badge_text,
                "change_badge_text_vi": ch_badge_vi,
                "change_badge_text_zh": ch_badge_zh,
                "received_delta": c_it.get("received_delta"),
                "received_delta_formatted": c_it.get("received_delta_formatted"),
                "is_newly_paid": (p_status != "PAID" and c_status == "PAID"),
                "is_newly_overdue": (p_status != "OVERDUE" and c_status == "OVERDUE"),
            })

        has_urgent_curr = any(s["curr_status"] == "URGENT" for s in segments)
        
        # Các khoản chưa thanh toán xong
        unpaid_segs = [s for s in segments if s.get("curr_status") != "PAID"]
        # Có khoản tiếp theo chưa bắt đầu tính hạn (start_date trống/null và đang chờ lắp đặt/nghiệm thu/PENDING)
        has_unstarted_next = any(
            (not s.get("start_date") or s.get("start_date") == "-") and 
            (not s.get("due_date") or s.get("due_date") == "-" or s.get("curr_status") == "PENDING")
            for s in unpaid_segs
        )
        # Có khoản đang chạy tính hạn T/T (đã có start_date và chưa thanh toán)
        has_calculating_next = any(
            (s.get("start_date") and s.get("start_date") != "-") and s.get("curr_status") != "PAID"
            for s in unpaid_segs
        )
        is_fully_paid = (group_curr_rec >= group_gross - 1.0) and group_gross > 0
        has_remaining_debt = not is_fully_paid
        is_active_attention = bool(has_change or has_overdue_curr or has_urgent_curr or has_unstarted_next)

        contracts_comparison.append({
            "contract_key": c_key,
            "contract_code": c_code_disp,
            "project_title": proj_title_vi,
            "project_title_vi": proj_title_vi,
            "project_title_zh": proj_title_zh,
            "customer_name": cust_name_vi,
            "customer_name_vi": cust_name_vi,
            "customer_name_zh": cust_name_zh,
            "total_gross": group_gross,
            "total_gross_formatted": format_currency_vn(group_gross),
            "prev_received": group_prev_rec,
            "prev_received_formatted": format_currency_vn(group_prev_rec),
            "curr_received": group_curr_rec,
            "curr_received_formatted": format_currency_vn(group_curr_rec),
            "prev_pct_collected": round((group_prev_rec / group_gross * 100.0), 1) if group_gross > 0 else 0.0,
            "curr_pct_collected": round((group_curr_rec / group_gross * 100.0), 1) if group_gross > 0 else 0.0,
            "segment_count": seg_count,
            "has_change": has_change,
            "has_overdue_curr": has_overdue_curr,
            "has_urgent_curr": has_urgent_curr,
            "has_unstarted_next": has_unstarted_next,
            "has_calculating_next": has_calculating_next,
            "is_fully_paid": is_fully_paid,
            "has_remaining_debt": has_remaining_debt,
            "is_active_attention": is_active_attention,
            "segments": segments,
        })

    # Prioritize contracts requiring attention so the chart is immediately focused
    contracts_comparison.sort(
        key=lambda x: (
            0 if x["is_active_attention"] else 1,
            0 if x["has_change"] else 1,
            0 if x["has_overdue_curr"] else 1,
            0 if x["segment_count"] > 1 else 1,
            -x["segment_count"],
        )
    )

    # Next week collection plan / forecast analysis
    planned_targets = []
    planned_target_amount = 0.0
    for c_it in curr_items:
        d_str = c_it.get("due_date")
        is_in_range = False
        if d_str and d_str != "-":
            try:
                d_val = datetime.strptime(d_str, "%Y-%m-%d").date()
                p_val = datetime.strptime(prev_date, "%Y-%m-%d").date()
                c_val = datetime.strptime(curr_date, "%Y-%m-%d").date()
                if p_val < d_val <= c_val and c_it.get("collection_status") != "PAID":
                    is_in_range = True
            except Exception:
                pass
        
        if is_in_range or c_it.get("is_newly_overdue"):
            debt = float(c_it.get("remaining_debt") or c_it.get("gross_amount") or 0.0)
            planned_targets.append({
                "id": c_it["id"],
                "project_name": c_it.get("project_name"),
                "customer_name": c_it.get("customer_name"),
                "contract_code": c_it.get("contract_code") or "-",
                "amount": debt,
                "amount_formatted": format_currency_vn(debt),
                "due_date": c_it.get("due_date"),
                "customer_promised_date": c_it.get("customer_promised_date"),
                "notes": c_it.get("notes") or "",
            })
            planned_target_amount += debt

    return {
        "status": "success",
        "data_source": data_source,
        "data_source_meta": data_source_meta,
        "dates": {
            "prev_date": prev_date,
            "prev_label": prev_label,
            "curr_date": curr_date,
            "curr_label": curr_label,
        },
        "deltas": {
            "net_received_increase": net_increase,
            "net_received_increase_formatted": format_currency_vn(net_increase),
            "debt_reduction": debt_reduction,
            "debt_reduction_formatted": format_currency_vn(debt_reduction),
            "rate_delta": rate_delta,
            "newly_paid_count": newly_paid_count,
            "newly_paid_amount": newly_paid_amount,
            "newly_paid_amount_formatted": format_currency_vn(newly_paid_amount),
            "newly_overdue_count": newly_overdue_count,
            "newly_overdue_amount": newly_overdue_amount,
            "newly_overdue_amount_formatted": format_currency_vn(newly_overdue_amount),
            "total_changes_count": len(changes_list),
        },
        "contracts_comparison": contracts_comparison,
        "plan_next_week": {
            "planned_target_amount": planned_target_amount,
            "planned_target_amount_formatted": format_currency_vn(planned_target_amount),
            "planned_targets_count": len(planned_targets),
            "planned_targets": planned_targets,
        },
        "prev_week": {
            "date": prev_date,
            "label": prev_label,
            "total_receivable": total_gross,
            "total_receivable_formatted": format_currency_vn(total_gross),
            "total_received": prev_total_received,
            "total_received_formatted": format_currency_vn(prev_total_received),
            "total_debt": prev_total_debt,
            "total_debt_formatted": format_currency_vn(prev_total_debt),
            "collection_rate": prev_rate,
            "counts": prev_counts,
            "items": prev_items,
        },
        "curr_week": {
            "date": curr_date,
            "label": curr_label,
            "total_receivable": total_gross,
            "total_receivable_formatted": format_currency_vn(total_gross),
            "total_received": curr_total_received,
            "total_received_formatted": format_currency_vn(curr_total_received),
            "total_debt": curr_total_debt,
            "total_debt_formatted": format_currency_vn(curr_total_debt),
            "collection_rate": curr_rate,
            "counts": curr_counts,
            "items": curr_items,
        },
        "changes": changes_list,
    }
