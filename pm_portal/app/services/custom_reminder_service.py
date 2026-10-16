"""Service managing personal reminders, custom scheduled tasks, and file attachments."""

import logging
import os
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import WORKING_DIR
from app.database import get_db_connection

logger = logging.getLogger(__name__)

# Thư mục lưu trữ các file đính kèm nhắc nhở riêng
REMINDERS_DIR = WORKING_DIR / "Ho So Du An" / "Nhac Nho"

WEEKDAYS_VI = [
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
    "Chủ Nhật",
]


def ensure_reminders_dir() -> Path:
    """Ensure Ho So Du An/Nhac Nho folder exists."""
    REMINDERS_DIR.mkdir(parents=True, exist_ok=True)
    return REMINDERS_DIR


def parse_date_to_iso(date_str: str) -> str:
    """Standardize date string into YYYY-MM-DD."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    clean_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean_str


def get_day_of_week_vi(dt: date) -> str:
    """Return Vietnamese weekday name (e.g. Thứ Hai)."""
    return WEEKDAYS_VI[dt.weekday()]


def format_due_string(due_date_str: str, due_time_str: str = "09:00") -> Tuple[str, str, int, bool, bool, bool]:
    """Calculate date relations, day of week, and readable display text.
    
    Returns:
        (formatted_full, timing_badge_text, days_diff, is_today, is_overdue, is_upcoming)
    """
    iso_date = parse_date_to_iso(due_date_str)
    today = datetime.now().date()
    try:
        due_d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except Exception:
        due_d = today

    days_diff = (due_d - today).days
    day_name = get_day_of_week_vi(due_d)
    date_display = due_d.strftime("%d/%m/%Y")
    time_display = due_time_str or "09:00"

    is_today = (days_diff == 0)
    is_overdue = (days_diff < 0)
    is_upcoming = (days_diff > 0)

    formatted_full = f"{day_name}, {date_display} ({time_display})"

    if is_today:
        timing_badge = "Hôm nay"
    elif days_diff == 1:
        timing_badge = "Ngày mai"
    elif days_diff == -1:
        timing_badge = "Hôm qua (Quá hạn 1 ngày)"
    elif days_diff < -1:
        timing_badge = f"Quá hạn {abs(days_diff)} ngày"
    elif days_diff <= 7:
        timing_badge = f"{day_name} tới ({days_diff} ngày nữa)"
    else:
        timing_badge = f"Còn {days_diff} ngày"

    return formatted_full, timing_badge, days_diff, is_today, is_overdue, is_upcoming


def get_custom_reminders_list(
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve and categorize personal reminders with live stats and file checks."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM custom_reminders WHERE 1=1"
    params: List[Any] = []

    if status_filter and status_filter.upper() != "ALL":
        query += " AND status = ?"
        params.append(status_filter.upper())

    if priority_filter and priority_filter.upper() != "ALL":
        query += " AND priority = ?"
        params.append(priority_filter.upper())

    if search_query and search_query.strip():
        q = f"%{search_query.strip()}%"
        query += " AND (title LIKE ? OR description LIKE ? OR attachment_name LIKE ?)"
        params.extend([q, q, q])

    query += " ORDER BY CASE WHEN status = 'PENDING' THEN 0 ELSE 1 END, due_date ASC, due_time ASC, id DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    # Also calculate global statistics
    cursor.execute("SELECT status, due_date FROM custom_reminders")
    all_rows = cursor.fetchall()
    conn.close()

    today_str = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "total": len(all_rows),
        "pending": 0,
        "today": 0,
        "overdue": 0,
        "upcoming": 0,
        "completed": 0,
    }

    for r in all_rows:
        st = r["status"]
        d_str = parse_date_to_iso(r["due_date"])
        if st == "COMPLETED":
            stats["completed"] += 1
        else:
            stats["pending"] += 1
            if d_str == today_str:
                stats["today"] += 1
            elif d_str < today_str:
                stats["overdue"] += 1
            else:
                stats["upcoming"] += 1

    reminders = []
    for r in rows:
        item = dict(r)
        d_full, t_badge, d_diff, is_today, is_overdue, is_upcoming = format_due_string(
            item.get("due_date", ""), item.get("due_time", "09:00")
        )

        item["formatted_due"] = d_full
        item["due_date_formatted"] = d_full
        item["timing_badge"] = t_badge
        item["days_diff"] = d_diff
        item["days_remaining"] = d_diff
        item["is_today"] = is_today
        item["is_overdue"] = is_overdue if item.get("status") != "COMPLETED" else False
        item["is_upcoming"] = is_upcoming

        # Check attachment
        att_path_str = item.get("attachment_path") or ""
        att_exists = False
        att_size = item.get("attachment_size") or 0
        att_ext = ""
        if att_path_str:
            p = Path(att_path_str)
            att_exists = p.is_file()
            if att_exists:
                att_size = p.stat().st_size
                att_ext = p.suffix.lstrip(".").lower()

        item["attachment_exists"] = att_exists
        item["attachment_size"] = att_size
        size_human = f"{round(att_size / 1024, 1)} KB" if att_size < 1048576 else f"{round(att_size / 1048576, 2)} MB"
        item["attachment_size_formatted"] = size_human
        item["attachment_size_human"] = size_human
        item["attachment_ext"] = att_ext
        item["download_url"] = f"/api/v1/custom-reminders/{item['id']}/download" if att_exists else ""
        item["is_linked_from_project"] = bool("Ho So Du An" in att_path_str and "Nhac Nho" not in att_path_str)

        reminders.append(item)

    return {
        "status": "success",
        "reminders": reminders,
        "stats": stats,
    }


def create_custom_reminder(
    title: str,
    due_date: str,
    description: str = "",
    due_time: str = "09:00",
    priority: str = "NORMAL",
    category: str = "GENERAL",
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    existing_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create and persist a new custom reminder with optional attachment."""
    if not title or not title.strip():
        raise ValueError("Tiêu đề nhắc nhở không được để trống.")

    iso_due_date = parse_date_to_iso(due_date)
    clean_time = (due_time or "09:00").strip()
    clean_priority = (priority or "NORMAL").upper()
    if clean_priority not in ("LOW", "NORMAL", "HIGH", "URGENT"):
        clean_priority = "NORMAL"

    att_name = ""
    att_path_str = ""
    att_size = 0

    # 1. New file upload
    if file_bytes and file_name:
        folder = ensure_reminders_dir()
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(file_name).name}"
        dest_path = folder / safe_name
        dest_path.write_bytes(file_bytes)
        att_name = Path(file_name).name
        att_path_str = str(dest_path)
        att_size = len(file_bytes)
    # 2. Link existing project file
    elif existing_file_path and existing_file_path.strip():
        p = Path(existing_file_path.strip())
        if p.is_file():
            att_name = p.name
            att_path_str = str(p)
            att_size = p.stat().st_size

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO custom_reminders (
            title, description, due_date, due_time, priority, category, status,
            attachment_name, attachment_path, attachment_size
        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?)
    """, (
        title.strip(), description.strip(), iso_due_date, clean_time, clean_priority,
        category, att_name, att_path_str, att_size
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return {
        "status": "success",
        "message": "Đã tạo lời nhắc nhở thành công!",
        "reminder_id": new_id,
        "attachment_name": att_name,
    }


def update_custom_reminder(
    reminder_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    due_time: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    existing_file_path: Optional[str] = None,
    remove_attachment: bool = False,
) -> Dict[str, Any]:
    """Update details or attachment of an existing reminder."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Không tìm thấy lời nhắc với ID {reminder_id}")

    current = dict(row)
    new_title = title.strip() if title is not None else current["title"]
    new_desc = description.strip() if description is not None else current["description"]
    new_due_date = parse_date_to_iso(due_date) if due_date is not None else current["due_date"]
    new_due_time = (due_time or current.get("due_time") or "09:00").strip()
    new_priority = (priority or current.get("priority") or "NORMAL").upper()
    new_category = category or current.get("category") or "GENERAL"

    att_name = current.get("attachment_name") or ""
    att_path_str = current.get("attachment_path") or ""
    att_size = current.get("attachment_size") or 0

    if remove_attachment:
        att_name = ""
        att_path_str = ""
        att_size = 0
    elif file_bytes and file_name:
        folder = ensure_reminders_dir()
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(file_name).name}"
        dest_path = folder / safe_name
        dest_path.write_bytes(file_bytes)
        att_name = Path(file_name).name
        att_path_str = str(dest_path)
        att_size = len(file_bytes)
    elif existing_file_path and existing_file_path.strip():
        p = Path(existing_file_path.strip())
        if p.is_file():
            att_name = p.name
            att_path_str = str(p)
            att_size = p.stat().st_size

    cursor.execute("""
        UPDATE custom_reminders SET
            title = ?, description = ?, due_date = ?, due_time = ?,
            priority = ?, category = ?, attachment_name = ?,
            attachment_path = ?, attachment_size = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        new_title, new_desc, new_due_date, new_due_time,
        new_priority, new_category, att_name, att_path_str, att_size,
        reminder_id
    ))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Đã cập nhật lời nhắc thành công!",
        "reminder_id": reminder_id
    }


def toggle_custom_reminder_status(reminder_id: int) -> Dict[str, Any]:
    """Toggle between PENDING and COMPLETED status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Không tìm thấy lời nhắc với ID {reminder_id}")

    curr_status = row["status"]
    new_status = "COMPLETED" if curr_status == "PENDING" else "PENDING"
    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "COMPLETED" else None

    cursor.execute("""
        UPDATE custom_reminders SET
            status = ?, completed_at = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, completed_at, reminder_id))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "new_status": new_status,
        "message": "Đã đánh dấu hoàn thành!" if new_status == "COMPLETED" else "Đã chuyển về trạng thái đang chờ thực hiện."
    }


def delete_custom_reminder(reminder_id: int, delete_file: bool = False) -> bool:
    """Delete a custom reminder and optionally unlink attachment file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT attachment_path FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    att_path = row["attachment_path"]
    if delete_file and att_path:
        p = Path(att_path)
        # SAFEGUARD: only delete files physically located in Ho So Du An/Nhac Nho
        if p.exists() and p.is_file() and "nhac nho" in str(p).lower():
            try:
                p.unlink(missing_ok=True)
                logger.info("Deleted reminder attachment: %s", p)
            except Exception as e:
                logger.warning("Could not delete reminder attachment %s: %s", p, e)

    cursor.execute("DELETE FROM custom_reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    return True


def get_available_project_documents() -> List[Dict[str, Any]]:
    """Scan Ho So Du An subdirectories so user can attach existing project files with 1 click."""
    folders = [
        ("HOP_DONG", "Hợp Đồng", WORKING_DIR / "Ho So Du An" / "Hop Dong"),
        ("BAO_GIA", "Báo Giá", WORKING_DIR / "Ho So Du An" / "Bao Gia"),
        ("NGHIEM_THU", "Nghiệm Thu", WORKING_DIR / "Ho So Du An" / "Nghiem Thu"),
        ("YEU_CAU_THANH_TOAN", "Đề Nghị Thanh Toán", WORKING_DIR / "Ho So Du An" / "Yeu Cau Thanh Toan"),
        ("XUAT_KHO", "Xuất Kho", WORKING_DIR / "Ho So Du An" / "Xuat Kho"),
        ("NHAC_NHO", "Đính Kèm Nhắc Nhở", REMINDERS_DIR),
    ]

    docs: List[Dict[str, Any]] = []
    seen = set()

    for category, category_label, pdir in folders:
        if not pdir.exists():
            continue
        for p in pdir.glob("*.*"):
            if p.is_file() and not p.name.startswith("~$") and p.name not in seen:
                seen.add(p.name)
                fsize = p.stat().st_size
                mtime_str = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                docs.append({
                    "file_name": p.name,
                    "file_path": str(p),
                    "file_size": fsize,
                    "file_size_formatted": f"{round(fsize / 1024, 1)} KB" if fsize < 1048576 else f"{round(fsize / 1048576, 2)} MB",
                    "file_ext": p.suffix.lstrip(".").lower(),
                    "category": category,
                    "category_label": category_label,
                    "updated_at": mtime_str
                })

    # Sort newest first
    docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return docs
