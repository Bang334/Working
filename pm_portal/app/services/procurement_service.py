# -*- coding: utf-8 -*-
"""Service for CRUD operations and stats calculation on Procurement Orders."""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database import get_db_connection


def format_delivery_status(status_raw: Optional[str], eta: Optional[str], actual: Optional[str], notes: Optional[str]) -> str:
    """Helper to determine standard delivery status code and label."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    notes_upper = (notes or "").upper()
    status_raw_upper = (status_raw or "").upper()

    if actual or "ĐÃ GIAO" in notes_upper or "已交貨" in notes_upper or "ĐÃ GIAO" in status_raw_upper:
        return "DELIVERED"
    
    if eta:
        try:
            if eta < today_str:
                return "DELAYED"
            else:
                return "IN_TRANSIT"
        except Exception:
            pass

    if "CHỜ" in status_raw_upper or "PENDING" in status_raw_upper:
        return "PENDING"

    return "IN_TRANSIT" if eta else "PENDING"


def get_status_label(code: str) -> str:
    mapping = {
        "DELIVERED": "Đã giao / 已交貨",
        "IN_TRANSIT": "Đang vận chuyển / 運輸中",
        "DELAYED": "Trễ hạn / 延遲",
        "PENDING": "Chờ xử lý / 待處理",
    }
    return mapping.get(code, "Đang xử lý")


def list_procurement_orders(
    status: Optional[str] = None,
    supplier: Optional[str] = None,
    project: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve filtered procurement orders from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM procurement_orders WHERE 1=1"
    params: List[Any] = []

    if status and status != "all":
        query += " AND delivery_status = ?"
        params.append(status.upper())

    if supplier and supplier != "all":
        query += " AND supplier_name LIKE ?"
        params.append(f"%{supplier}%")

    if project and project != "all":
        query += " AND (project_name LIKE ? OR customer_company LIKE ?)"
        params.append(f"%{project}%")
        params.append(f"%{project}%")

    if search and search.strip():
        s = f"%{search.strip()}%"
        query += " AND (item_name LIKE ? OR project_name LIKE ? OR supplier_name LIKE ? OR customer_company LIKE ? OR category LIKE ? OR shipping_notes LIKE ?)"
        params.extend([s, s, s, s, s, s])

    query += " ORDER BY COALESCE(order_no, id) ASC, id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    orders = []
    for r in rows:
        d = dict(r)
        d["delivery_status_label"] = get_status_label(d.get("delivery_status", "PENDING"))
        orders.append(d)

    return orders


def get_procurement_order(order_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve single order by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM procurement_orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["delivery_status_label"] = get_status_label(d.get("delivery_status", "PENDING"))
        return d
    return None


def create_procurement_order(data: Dict[str, Any]) -> int:
    """Insert a single procurement order into database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    deliv_status = data.get("delivery_status") or format_delivery_status(
        None, data.get("eta_date"), data.get("actual_delivery_date"), data.get("shipping_notes")
    )
    status_label = get_status_label(deliv_status)

    cursor.execute("""
        INSERT INTO procurement_orders (
            order_no, project_name, category, item_name, quantity, unit,
            customer_company, supplier_name, order_date, eta_date,
            actual_delivery_date, material_desc, supplier_payment_status,
            delivery_status, delivery_status_label, shipping_notes,
            unit_price, total_amount, currency
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("order_no"),
        data.get("project_name", "").strip(),
        data.get("category", "").strip() if data.get("category") else None,
        data.get("item_name", "").strip(),
        float(data.get("quantity") or 1.0),
        data.get("unit", "Bộ"),
        data.get("customer_company", "").strip() if data.get("customer_company") else None,
        data.get("supplier_name", "").strip(),
        data.get("order_date"),
        data.get("eta_date"),
        data.get("actual_delivery_date"),
        data.get("material_desc"),
        data.get("supplier_payment_status"),
        deliv_status,
        status_label,
        data.get("shipping_notes"),
        float(data.get("unit_price") or 0.0),
        float(data.get("total_amount") or 0.0),
        data.get("currency", "VND"),
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_procurement_order(order_id: int, data: Dict[str, Any]) -> bool:
    """Update fields of an existing procurement order safely."""
    existing = get_procurement_order(order_id)
    if not existing:
        return False

    merged = dict(existing)
    merged.update({k: v for k, v in data.items() if v is not None})

    deliv_status = data.get("delivery_status")
    if not deliv_status:
        deliv_status = format_delivery_status(
            None, merged.get("eta_date"), merged.get("actual_delivery_date"), merged.get("shipping_notes")
        )
    status_label = get_status_label(deliv_status)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE procurement_orders SET
            order_no = ?,
            project_name = ?,
            category = ?,
            item_name = ?,
            quantity = ?,
            unit = ?,
            customer_company = ?,
            supplier_name = ?,
            order_date = ?,
            eta_date = ?,
            actual_delivery_date = ?,
            material_desc = ?,
            supplier_payment_status = ?,
            delivery_status = ?,
            delivery_status_label = ?,
            shipping_notes = ?,
            unit_price = ?,
            total_amount = ?,
            currency = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        merged.get("order_no"),
        merged.get("project_name"),
        merged.get("category"),
        merged.get("item_name"),
        merged.get("quantity"),
        merged.get("unit"),
        merged.get("customer_company"),
        merged.get("supplier_name"),
        merged.get("order_date"),
        merged.get("eta_date"),
        merged.get("actual_delivery_date"),
        merged.get("material_desc"),
        merged.get("supplier_payment_status"),
        deliv_status,
        status_label,
        merged.get("shipping_notes"),
        merged.get("unit_price"),
        merged.get("total_amount"),
        merged.get("currency"),
        order_id,
    ))

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def update_procurement_order_notes(order_id: int, notes: str) -> bool:
    """Directly update shipping notes / risk comments for quick inline editing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE procurement_orders SET
            shipping_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (notes, order_id))

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def update_procurement_order_status(order_id: int, status: str) -> bool:
    """Directly update delivery status and its label from inline dropdown."""
    label = get_status_label(status)
    conn = get_db_connection()
    cursor = conn.cursor()

    # If status is DELIVERED and actual_delivery_date is empty, optionally auto-fill today's date
    if status == "DELIVERED":
        cursor.execute("SELECT actual_delivery_date FROM procurement_orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if row and (not row["actual_delivery_date"] or row["actual_delivery_date"] == "-"):
            today_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                UPDATE procurement_orders SET
                    delivery_status = ?,
                    delivery_status_label = ?,
                    actual_delivery_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, label, today_str, order_id))
        else:
            cursor.execute("""
                UPDATE procurement_orders SET
                    delivery_status = ?,
                    delivery_status_label = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, label, order_id))
    else:
        cursor.execute("""
            UPDATE procurement_orders SET
                delivery_status = ?,
                delivery_status_label = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, label, order_id))

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0



def delete_procurement_order(order_id: int) -> bool:
    """Delete a single procurement order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM procurement_orders WHERE id = ?", (order_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_all_procurement_orders() -> int:
    """Clear all procurement orders table (for re-importing)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM procurement_orders")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def bulk_import_procurement_orders(orders: List[Dict[str, Any]], overwrite: bool = False) -> int:
    """Import multiple orders into database."""
    if overwrite:
        delete_all_procurement_orders()

    conn = get_db_connection()
    cursor = conn.cursor()
    imported_count = 0

    for idx, o in enumerate(orders):
        order_no = o.get("order_no") or (idx + 1)
        deliv_status = o.get("delivery_status") or format_delivery_status(
            o.get("delivery_status_raw"),
            o.get("eta_date"),
            o.get("actual_delivery_date"),
            o.get("shipping_notes"),
        )
        status_label = get_status_label(deliv_status)

        cursor.execute("""
            INSERT INTO procurement_orders (
                order_no, project_name, category, item_name, quantity, unit,
                customer_company, supplier_name, order_date, eta_date,
                actual_delivery_date, material_desc, supplier_payment_status,
                delivery_status, delivery_status_label, shipping_notes,
                unit_price, total_amount, currency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_no,
            (o.get("project_name") or "Dự án chung").strip(),
            (o.get("category") or "").strip() or None,
            (o.get("item_name") or "Vật tư thiết bị").strip(),
            float(o.get("quantity") or 1.0),
            o.get("unit") or "Bộ",
            (o.get("customer_company") or "").strip() or None,
            (o.get("supplier_name") or "NCC").strip(),
            o.get("order_date"),
            o.get("eta_date"),
            o.get("actual_delivery_date"),
            o.get("material_desc"),
            o.get("supplier_payment_status"),
            deliv_status,
            status_label,
            o.get("shipping_notes"),
            float(o.get("unit_price") or 0.0),
            float(o.get("total_amount") or 0.0),
            o.get("currency") or "VND",
        ))
        imported_count += 1

    conn.commit()
    conn.close()
    return imported_count


def get_procurement_stats() -> Dict[str, Any]:
    """Calculate summary statistics for dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM procurement_orders")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM procurement_orders WHERE delivery_status = 'DELIVERED'")
    delivered = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM procurement_orders WHERE delivery_status = 'IN_TRANSIT'")
    in_transit = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM procurement_orders WHERE delivery_status = 'DELAYED'")
    delayed = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM procurement_orders 
        WHERE supplier_payment_status LIKE '%Chờ%' 
           OR supplier_payment_status LIKE '%待%'
           OR supplier_payment_status LIKE '%50%%'
    """)
    pending_payment = cursor.fetchone()[0]

    cursor.execute("SELECT DISTINCT supplier_name FROM procurement_orders WHERE supplier_name IS NOT NULL AND supplier_name != '' ORDER BY supplier_name")
    suppliers = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT project_name FROM procurement_orders WHERE project_name IS NOT NULL AND project_name != '' ORDER BY project_name")
    projects = [r[0] for r in cursor.fetchall()]

    conn.close()

    return {
        "total_orders": total,
        "delivered_count": delivered,
        "in_transit_count": in_transit,
        "delayed_count": delayed,
        "pending_payment_count": pending_payment,
        "suppliers": suppliers,
        "projects": projects,
    }
