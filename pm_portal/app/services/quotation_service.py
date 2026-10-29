"""Quotation service handling saving, versioning, backup preservation, and retrieval."""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.database import get_db_connection, index_single_document
from app.services.quotation_excel_service import generate_quotation_excel
from app.services.quotation_word_service import generate_quotation_word
from app.utils.currency_helper import parse_positive_integer

logger = logging.getLogger(__name__)


def get_bao_gia_dirs() -> tuple:
    """Ensure and return the main and history backup directories."""
    main_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
    history_dir = main_dir / "Lich_Su"
    main_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    return main_dir, history_dir


def save_quotation_service(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save quotation with versioning: replaces old active quotation while backing up previous version."""
    quote_no = str(data.get("quotation_no") or data.get("quote_no") or "").strip()
    if not quote_no:
        raise ValueError("Thiếu mã số báo giá (quotation_no).")

    cust_vi = str(data.get("customer_name_vi") or data.get("customer_name") or "KHÁCH HÀNG").strip()
    cust_zh = str(data.get("customer_name_zh") or data.get("customer_name_cn") or "").strip()
    tax_code = str(data.get("tax_code") or "").strip()
    project_name = str(data.get("project_name") or "Dự án Thiết Bị IoT").strip()
    contact_person = str(data.get("contact_person") or "").strip()
    validity = str(data.get("validity") or "30 ngày kể từ ngày phát hành").strip()
    lead_time = str(data.get("lead_time") or "60 - 80 ngày sau khi nhận đủ tiền đặt cọc").strip()
    warranty = str(data.get("warranty") or "12 tháng chính hãng kể từ ngày nghiệm thu").strip()
    payment_terms = str(data.get("payment_terms") or "Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%").strip()
    notes = str(data.get("notes") or "").strip()

    items = data.get("items") or []
    subtotal = 0
    clean_items = []
    for item in items:
        name = str(item.get("name") or "Thiết bị").strip()
        unit = str(item.get("unit") or "Bộ").strip()
        qty = int(parse_positive_integer(item.get("qty")) or 1)
        price = parse_positive_integer(item.get("price")) or 0
        row_total = qty * price
        subtotal += row_total
        clean_items.append({
            "name": name,
            "unit": unit,
            "qty": qty,
            "price": price,
            "total": row_total
        })

    vat_amount = int(round(subtotal * 0.1))
    total_amount = subtotal + vat_amount

    main_dir, history_dir = get_bao_gia_dirs()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Check for existing active quotation
    cursor.execute(
        "SELECT * FROM quotations WHERE quotation_no = ? AND is_current = 1 ORDER BY version DESC LIMIT 1",
        (quote_no,)
    )
    old_row = cursor.fetchone()

    new_version = 1
    previous_backed_up = False

    if old_row:
        old_version = int(old_row["version"] or 1)
        new_version = old_version + 1

        # Backup old files into Lich_Su
        old_docx_path = Path(old_row["docx_file_path"]) if old_row["docx_file_path"] else None
        old_xlsx_path = Path(old_row["xlsx_file_path"]) if old_row["xlsx_file_path"] else None

        new_old_docx_path_str = ""
        new_old_xlsx_path_str = ""

        if old_docx_path and old_docx_path.is_file():
            backup_docx_name = f"{old_docx_path.stem}_backup_v{old_version}_{timestamp_str}{old_docx_path.suffix}"
            dest_docx = history_dir / backup_docx_name
            try:
                shutil.copy2(str(old_docx_path), str(dest_docx))
                new_old_docx_path_str = str(dest_docx)
                previous_backed_up = True
            except Exception as exc:
                logger.warning("Could not backup old docx: %s", exc)

        if old_xlsx_path and old_xlsx_path.is_file():
            backup_xlsx_name = f"{old_xlsx_path.stem}_backup_v{old_version}_{timestamp_str}{old_xlsx_path.suffix}"
            dest_xlsx = history_dir / backup_xlsx_name
            try:
                shutil.copy2(str(old_xlsx_path), str(dest_xlsx))
                new_old_xlsx_path_str = str(dest_xlsx)
                previous_backed_up = True
            except Exception as exc:
                logger.warning("Could not backup old xlsx: %s", exc)

        # Mark old quotation as archived (is_current = 0)
        cursor.execute(
            """
            UPDATE quotations
            SET is_current = 0,
                docx_file_path = COALESCE(NULLIF(?, ''), docx_file_path),
                xlsx_file_path = COALESCE(NULLIF(?, ''), xlsx_file_path),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_old_docx_path_str, new_old_xlsx_path_str, old_row["id"])
        )

    # 2. Generate active Word & Excel files
    # Share one identifier so the Word and Excel files form an obvious pair.
    generation_data = dict(data)
    generation_data["_file_timestamp"] = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    word_res = generate_quotation_word(generation_data)
    excel_res = generate_quotation_excel(generation_data)

    docx_name = word_res.get("file_name", "")
    docx_path = word_res.get("file_path", "")
    xlsx_name = excel_res.get("file_name", "")
    xlsx_path = excel_res.get("file_path", "")

    # 3. Insert new active quotation record
    cursor.execute(
        """
        INSERT INTO quotations (
            quotation_no, customer_name_vi, customer_name_zh, tax_code,
            project_name, contact_person, validity, lead_time, warranty,
            payment_terms, notes, subtotal, vat_amount, total_amount,
            version, is_current, docx_file_name, docx_file_path,
            xlsx_file_name, xlsx_file_path, items_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
        """,
        (
            quote_no, cust_vi, cust_zh, tax_code,
            project_name, contact_person, validity, lead_time, warranty,
            payment_terms, notes, subtotal, vat_amount, total_amount,
            new_version, docx_name, docx_path,
            xlsx_name, xlsx_path, json.dumps(clean_items, ensure_ascii=False)
        )
    )
    quote_id = cursor.lastrowid
    conn.commit()
    conn.close()

    msg = f"Đã lưu báo giá {quote_no} (Phiên bản v{new_version}) thành công!"
    if previous_backed_up:
        msg += f" Bản cũ (v{new_version - 1}) đã được tự động lưu trữ an toàn tại thư mục Lịch Sử (Lich_Su)."

    return {
        "status": "success",
        "message": msg,
        "id": quote_id,
        "quotation_no": quote_no,
        "version": new_version,
        "previous_backed_up": previous_backed_up,
        "customer_name": cust_vi,
        "total_amount": total_amount,
        "total_amount_formatted": f"{total_amount:,}".replace(",", ".") + " VND",
        "docx_file_name": docx_name,
        "docx_download_url": word_res.get("download_url", ""),
        "xlsx_file_name": xlsx_name,
        "xlsx_download_url": excel_res.get("download_url", ""),
    }


def get_quotation_history_service(quotation_no: str) -> List[Dict[str, Any]]:
    """Retrieve full version history for a quotation number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, quotation_no, customer_name_vi, project_name, total_amount,
               version, is_current, docx_file_name, docx_file_path,
               xlsx_file_name, xlsx_file_path, created_at
        FROM quotations
        WHERE quotation_no = ?
        ORDER BY version DESC
        """,
        (quotation_no,)
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "quotation_no": r["quotation_no"],
            "customer_name": r["customer_name_vi"],
            "project_name": r["project_name"],
            "version": r["version"],
            "is_current": bool(r["is_current"]),
            "status_label": "Bản Hiện Hành" if r["is_current"] else f"Bản Lưu Trữ (v{r['version']})",
            "total_amount": r["total_amount"],
            "total_amount_formatted": f"{int(r['total_amount'] or 0):,}".replace(",", ".") + " VND",
            "docx_file_name": r["docx_file_name"],
            "docx_file_path": r["docx_file_path"],
            "docx_download_url": f"/api/v1/quotation/download/{r['docx_file_name']}" if r["docx_file_name"] else "",
            "xlsx_file_name": r["xlsx_file_name"],
            "xlsx_file_path": r["xlsx_file_path"],
            "xlsx_download_url": f"/api/v1/quotation/download/{r['xlsx_file_name']}" if r["xlsx_file_name"] else "",
            "created_at": r["created_at"],
        })
    return history


def get_quotation_detail_service(identifier: str) -> Optional[Dict[str, Any]]:
    """Get complete quotation data to populate into form editor."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if identifier.isdigit():
        cursor.execute("SELECT * FROM quotations WHERE id = ?", (int(identifier),))
    else:
        cursor.execute(
            "SELECT * FROM quotations WHERE quotation_no = ? ORDER BY version DESC LIMIT 1",
            (identifier,)
        )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data = dict(row)
    try:
        data["items"] = json.loads(row["items_json"] or "[]")
    except Exception:
        data["items"] = []
    return data


def get_all_active_quotations_service() -> List[Dict[str, Any]]:
    """List all current quotations with version info and count of archived revisions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query active quotations
    cursor.execute("""
        SELECT q.*,
               (SELECT COUNT(*) FROM quotations q2 WHERE q2.quotation_no = q.quotation_no AND q2.is_current = 0) as history_count
        FROM quotations q
        WHERE q.is_current = 1
        ORDER BY q.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        total = int(r["total_amount"] or 0)
        result.append({
            "id": r["id"],
            "quotation_no": r["quotation_no"],
            "customer_name_vi": r["customer_name_vi"],
            "customer_name_zh": r["customer_name_zh"] or "",
            "project_name": r["project_name"] or "",
            "total_amount": total,
            "total_amount_formatted": f"{total:,}".replace(",", ".") + " VND",
            "version": r["version"],
            "history_count": r["history_count"],
            "docx_file_name": r["docx_file_name"],
            "docx_file_path": r["docx_file_path"],
            "docx_download_url": f"/api/v1/quotation/download/{r['docx_file_name']}" if r["docx_file_name"] else "",
            "xlsx_file_name": r["xlsx_file_name"],
            "xlsx_file_path": r["xlsx_file_path"],
            "xlsx_download_url": f"/api/v1/quotation/download/{r['xlsx_file_name']}" if r["xlsx_file_name"] else "",
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    return result
