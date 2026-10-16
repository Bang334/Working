"""Service managing personal reminders, custom scheduled tasks, dedicated folders, and multi-file attachments."""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import WORKING_DIR
from app.database import get_db_connection
from app.services.time_utils import (
    VIETNAM_TZ,
    format_due_string_vn,
    get_day_of_week_vi,
    get_vietnam_now,
    get_vietnam_time_str,
    get_vietnam_today,
    get_vietnam_today_str,
    parse_date_to_iso,
    WEEKDAYS_VI,
)

logger = logging.getLogger(__name__)

# Base folder for personal reminders
REMINDERS_DIR = WORKING_DIR / "Ho So Du An" / "Nhac Nho"

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"}


def ensure_reminders_dir() -> Path:
    """Ensure Ho So Du An/Nhac Nho folder exists."""
    REMINDERS_DIR.mkdir(parents=True, exist_ok=True)
    return REMINDERS_DIR


def get_reminder_folder(reminder_id: int) -> Path:
    """Get dedicated folder path for a specific reminder."""
    folder = ensure_reminders_dir() / f"reminder_{reminder_id}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def format_size_human(size_bytes: int) -> str:
    """Format file size in KB or MB."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1048576:
        return f"{round(size_bytes / 1024, 1)} KB"
    else:
        return f"{round(size_bytes / 1048576, 2)} MB"


def format_due_string(due_date_str: str, due_time_str: str = "09:00") -> Tuple[str, str, int, bool, bool, bool]:
    """Calculate date relations, day of week, and readable display text in Vietnam timezone."""
    formatted_full, timing_badge, days_diff, is_today, is_overdue, is_upcoming, _ = format_due_string_vn(
        due_date_str, due_time_str
    )
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
        query += " AND (title LIKE ? OR description LIKE ? OR attachment_name LIKE ? OR attachments LIKE ?)"
        params.extend([q, q, q, q])

    query += " ORDER BY CASE WHEN status = 'PENDING' THEN 0 ELSE 1 END, due_date ASC, due_time ASC, id DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()

    # Calculate global statistics
    cursor.execute("SELECT status, due_date FROM custom_reminders")
    all_rows = cursor.fetchall()
    conn.close()

    today_str = get_vietnam_today_str("%Y-%m-%d")
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

        # Parse attachments JSON
        raw_attach = item.get("attachments") or "[]"
        attachments_list: List[Dict[str, Any]] = []
        try:
            parsed = json.loads(raw_attach) if isinstance(raw_attach, str) else raw_attach
            if isinstance(parsed, list):
                attachments_list = parsed
        except Exception:
            attachments_list = []

        # If attachments_list is empty but legacy attachment_path exists, backfill it
        legacy_path = item.get("attachment_path") or ""
        if not attachments_list and legacy_path:
            p_leg = Path(legacy_path)
            ext = p_leg.suffix.lstrip(".").lower()
            sz = item.get("attachment_size") or (p_leg.stat().st_size if p_leg.is_file() else 0)
            attachments_list.append({
                "name": item.get("attachment_name") or p_leg.name,
                "path": str(p_leg),
                "size": sz,
                "size_human": format_size_human(sz),
                "ext": ext,
                "is_image": ext in IMAGE_EXTENSIONS,
                "is_uploaded": "Nhac Nho" in str(p_leg),
                "exists": p_leg.is_file(),
            })

        # Enrich attachment items with exists, download and preview URLs
        for idx, att in enumerate(attachments_list):
            p_att = Path(att.get("path", ""))
            att_exists = p_att.is_file()
            att["exists"] = att_exists
            ext = att.get("ext") or p_att.suffix.lstrip(".").lower()
            att["ext"] = ext
            att["is_image"] = ext in IMAGE_EXTENSIONS
            att["download_url"] = f"/api/v1/custom-reminders/{item['id']}/attachments/{idx}/download"
            att["preview_url"] = f"/api/v1/custom-reminders/{item['id']}/attachments/{idx}/preview"

        item["attachments_list"] = attachments_list
        item["attachments_count"] = len(attachments_list)

        # Primary attachment backward compatibility
        if attachments_list:
            first = attachments_list[0]
            item["attachment_name"] = first.get("name", "")
            item["attachment_path"] = first.get("path", "")
            item["attachment_size"] = first.get("size", 0)
            item["attachment_size_formatted"] = first.get("size_human", "")
            item["attachment_size_human"] = first.get("size_human", "")
            item["attachment_ext"] = first.get("ext", "")
            item["attachment_exists"] = first.get("exists", False)
            item["download_url"] = first.get("download_url", "")
            item["is_linked_from_project"] = not first.get("is_uploaded", False)
        else:
            item["attachment_name"] = ""
            item["attachment_path"] = ""
            item["attachment_size"] = 0
            item["attachment_size_formatted"] = ""
            item["attachment_size_human"] = ""
            item["attachment_ext"] = ""
            item["attachment_exists"] = False
            item["download_url"] = ""
            item["is_linked_from_project"] = False

        # Dedicated folder check
        f_path = item.get("folder_path")
        if not f_path:
            f_path = str(ensure_reminders_dir() / f"reminder_{item['id']}")
            item["folder_path"] = f_path
        item["folder_exists"] = Path(f_path).is_dir()

        reminders.append(item)

    return {
        "status": "success",
        "reminders": reminders,
        "stats": stats,
    }


def get_sidebar_due_stats() -> Dict[str, Any]:
    """Calculate count of pending reminders due today or overdue for the red sidebar alert."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT due_date FROM custom_reminders WHERE status = 'PENDING'")
    rows = cursor.fetchall()
    conn.close()

    today_str = get_vietnam_today_str("%Y-%m-%d")
    today_count = 0
    overdue_count = 0

    for r in rows:
        d_str = parse_date_to_iso(r["due_date"])
        if d_str == today_str:
            today_count += 1
        elif d_str < today_str:
            overdue_count += 1

    total_due = today_count + overdue_count
    return {
        "status": "success",
        "today_count": today_count,
        "overdue_count": overdue_count,
        "total_due": total_due,
        "has_due": total_due > 0,
    }


def create_custom_reminder(
    title: str,
    due_date: str,
    description: str = "",
    due_time: str = "09:00",
    priority: str = "NORMAL",
    category: str = "GENERAL",
    uploaded_files: Optional[List[Tuple[str, bytes]]] = None,
    linked_file_paths: Optional[List[str]] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    existing_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create and persist a new custom reminder with its dedicated folder and multi-file attachments."""
    if not title or not title.strip():
        raise ValueError("Tiêu đề nhắc nhở không được để trống.")

    iso_due_date = parse_date_to_iso(due_date)
    clean_time = (due_time or "09:00").strip()
    clean_priority = (priority or "NORMAL").upper()
    if clean_priority not in ("LOW", "NORMAL", "HIGH", "URGENT"):
        clean_priority = "NORMAL"

    # Step 1: Insert preliminary record to obtain ID
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO custom_reminders (
            title, description, due_date, due_time, priority, category, status,
            attachment_name, attachment_path, attachment_size, folder_path, attachments
        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', '', '', 0, '', '[]')
    """, (title.strip(), description.strip(), iso_due_date, clean_time, clean_priority, category))
    conn.commit()
    new_id = cursor.lastrowid

    # Step 2: Create dedicated folder for this reminder
    reminder_folder = get_reminder_folder(new_id)

    attachments_list: List[Dict[str, Any]] = []

    # Handle legacy single upload if passed
    if file_bytes and file_name:
        if uploaded_files is None:
            uploaded_files = []
        uploaded_files.append((file_name, file_bytes))

    # Handle legacy single linked path if passed
    if existing_file_path and existing_file_path.strip():
        if linked_file_paths is None:
            linked_file_paths = []
        linked_file_paths.append(existing_file_path.strip())

    # Step 3: Save uploaded files directly into reminder_folder
    if uploaded_files:
        for fname, fbytes in uploaded_files:
            if not fname or not fbytes:
                continue
            clean_fname = Path(fname).name
            dest_file = reminder_folder / clean_fname
            # If exists, avoid overwrite by prefixing timestamp
            if dest_file.exists():
                dest_file = reminder_folder / f"{get_vietnam_now().strftime('%H%M%S')}_{clean_fname}"
            dest_file.write_bytes(fbytes)
            ext = dest_file.suffix.lstrip(".").lower()
            sz = len(fbytes)
            attachments_list.append({
                "name": dest_file.name,
                "path": str(dest_file),
                "size": sz,
                "size_human": format_size_human(sz),
                "ext": ext,
                "is_image": ext in IMAGE_EXTENSIONS,
                "is_uploaded": True,
            })

    # Step 4: Add external linked files (from anywhere on PC or Ho So Du An)
    if linked_file_paths:
        for lpath in linked_file_paths:
            if not lpath or not str(lpath).strip():
                continue
            p = Path(str(lpath).strip())
            if p.is_file():
                ext = p.suffix.lstrip(".").lower()
                sz = p.stat().st_size
                attachments_list.append({
                    "name": p.name,
                    "path": str(p),
                    "size": sz,
                    "size_human": format_size_human(sz),
                    "ext": ext,
                    "is_image": ext in IMAGE_EXTENSIONS,
                    "is_uploaded": False,
                })

    # Prepare primary attachment fields for backward compatibility
    primary_name = attachments_list[0]["name"] if attachments_list else ""
    primary_path = attachments_list[0]["path"] if attachments_list else ""
    total_size = sum(a.get("size", 0) for a in attachments_list)

    cursor.execute("""
        UPDATE custom_reminders SET
            attachment_name = ?,
            attachment_path = ?,
            attachment_size = ?,
            folder_path = ?,
            attachments = ?
        WHERE id = ?
    """, (
        primary_name, primary_path, total_size,
        str(reminder_folder), json.dumps(attachments_list, ensure_ascii=False),
        new_id
    ))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Đã tạo lời nhắc nhở thành công!",
        "reminder_id": new_id,
        "folder_path": str(reminder_folder),
        "attachments_count": len(attachments_list),
        "attachment_name": primary_name,
    }


def update_custom_reminder(
    reminder_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    due_time: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    uploaded_files: Optional[List[Tuple[str, bytes]]] = None,
    linked_file_paths: Optional[List[str]] = None,
    file_bytes: Optional[bytes] = None,
    file_name: Optional[str] = None,
    existing_file_path: Optional[str] = None,
    remove_attachment: bool = False,
    removed_file_indices: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Update details, add/remove attachments in dedicated reminder folder."""
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

    # Dedicated folder
    reminder_folder = Path(current.get("folder_path") or get_reminder_folder(reminder_id))
    reminder_folder.mkdir(parents=True, exist_ok=True)

    # Parse existing attachments
    raw_attach = current.get("attachments") or "[]"
    attachments_list: List[Dict[str, Any]] = []
    try:
        parsed = json.loads(raw_attach) if isinstance(raw_attach, str) else raw_attach
        if isinstance(parsed, list):
            attachments_list = parsed
    except Exception:
        attachments_list = []

    # If remove_attachment is requested, remove all
    if remove_attachment:
        attachments_list = []
    elif removed_file_indices:
        # Remove specific items by index
        attachments_list = [att for idx, att in enumerate(attachments_list) if idx not in removed_file_indices]

    # Handle legacy single file args
    if file_bytes and file_name:
        if uploaded_files is None:
            uploaded_files = []
        uploaded_files.append((file_name, file_bytes))

    if existing_file_path and existing_file_path.strip():
        if linked_file_paths is None:
            linked_file_paths = []
        linked_file_paths.append(existing_file_path.strip())

    # Add new uploaded files
    if uploaded_files:
        for fname, fbytes in uploaded_files:
            if not fname or not fbytes:
                continue
            clean_fname = Path(fname).name
            dest_file = reminder_folder / clean_fname
            if dest_file.exists():
                dest_file = reminder_folder / f"{get_vietnam_now().strftime('%H%M%S')}_{clean_fname}"
            dest_file.write_bytes(fbytes)
            ext = dest_file.suffix.lstrip(".").lower()
            sz = len(fbytes)
            attachments_list.append({
                "name": dest_file.name,
                "path": str(dest_file),
                "size": sz,
                "size_human": format_size_human(sz),
                "ext": ext,
                "is_image": ext in IMAGE_EXTENSIONS,
                "is_uploaded": True,
            })

    # Add new linked files
    if linked_file_paths:
        for lpath in linked_file_paths:
            if not lpath or not str(lpath).strip():
                continue
            p = Path(str(lpath).strip())
            if p.is_file():
                ext = p.suffix.lstrip(".").lower()
                sz = p.stat().st_size
                attachments_list.append({
                    "name": p.name,
                    "path": str(p),
                    "size": sz,
                    "size_human": format_size_human(sz),
                    "ext": ext,
                    "is_image": ext in IMAGE_EXTENSIONS,
                    "is_uploaded": False,
                })

    primary_name = attachments_list[0]["name"] if attachments_list else ""
    primary_path = attachments_list[0]["path"] if attachments_list else ""
    total_size = sum(a.get("size", 0) for a in attachments_list)

    cursor.execute("""
        UPDATE custom_reminders SET
            title = ?, description = ?, due_date = ?, due_time = ?,
            priority = ?, category = ?, attachment_name = ?,
            attachment_path = ?, attachment_size = ?,
            folder_path = ?, attachments = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        new_title, new_desc, new_due_date, new_due_time,
        new_priority, new_category, primary_name, primary_path, total_size,
        str(reminder_folder), json.dumps(attachments_list, ensure_ascii=False),
        reminder_id
    ))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Đã cập nhật lời nhắc thành công!",
        "reminder_id": reminder_id,
        "attachments_count": len(attachments_list),
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
    completed_at = get_vietnam_now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "COMPLETED" else None

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


def delete_custom_reminder(reminder_id: int, delete_files: bool = False) -> bool:
    """Delete a custom reminder and optionally unlink files and delete its dedicated folder.
    
    If delete_files is True:
        Deletes the reminder's dedicated folder (e.g. reminder_{id}/) and any files uploaded into it.
        SAFEGUARD: Does NOT delete files linked from other directories (e.g. Ho So Du An/Hop Dong).
    If delete_files is False:
        Deletes the database record, keeps all files and folder intact on disk.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT folder_path, attachment_path, attachments FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    folder_path_str = row["folder_path"]
    attachments_json = row["attachments"] or "[]"

    if delete_files:
        # 1. Delete dedicated folder if it exists and is inside Nhac Nho
        if folder_path_str:
            p_folder = Path(folder_path_str)
            if p_folder.exists() and p_folder.is_dir() and "nhac nho" in str(p_folder).lower():
                try:
                    shutil.rmtree(p_folder, ignore_errors=True)
                    logger.info("Deleted dedicated reminder folder: %s", p_folder)
                except Exception as e:
                    logger.warning("Could not delete reminder folder %s: %s", p_folder, e)

        # 2. Check legacy attachment_path
        leg_path = row["attachment_path"]
        if leg_path:
            p_leg = Path(leg_path)
            if p_leg.exists() and p_leg.is_file() and "nhac nho" in str(p_leg).lower():
                try:
                    p_leg.unlink(missing_ok=True)
                except Exception:
                    pass

    cursor.execute("DELETE FROM custom_reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    return True


def get_attachment_by_index(reminder_id: int, index: int) -> Tuple[Path, str, str]:
    """Retrieve Path, filename, and mime type for an attachment by index."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT attachment_name, attachment_path, attachments FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"Không tìm thấy lời nhắc với ID {reminder_id}")

    raw_attach = row["attachments"] or "[]"
    attachments_list: List[Dict[str, Any]] = []
    try:
        parsed = json.loads(raw_attach) if isinstance(raw_attach, str) else raw_attach
        if isinstance(parsed, list):
            attachments_list = parsed
    except Exception:
        attachments_list = []

    # If index is within list
    if 0 <= index < len(attachments_list):
        item = attachments_list[index]
        p = Path(item["path"])
        if not p.is_file():
            raise FileNotFoundError(f"Tệp tin '{item['name']}' không còn tồn tại trên máy tính.")
        return p, item["name"], item.get("ext", "")

    # Fallback to legacy attachment
    if index == 0 and row["attachment_path"]:
        p = Path(row["attachment_path"])
        if p.is_file():
            return p, row["attachment_name"] or p.name, p.suffix.lstrip(".").lower()

    raise IndexError(f"Không tìm thấy tệp đính kèm số {index} cho lời nhắc này.")


def open_folder_in_os(reminder_id: int) -> Dict[str, Any]:
    """Open the dedicated reminder folder in Windows Explorer."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT folder_path FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError("Lời nhắc không tồn tại.")

    folder_str = row["folder_path"] or str(get_reminder_folder(reminder_id))
    folder = Path(folder_str)
    folder.mkdir(parents=True, exist_ok=True)

    try:
        if os.name == "nt":
            os.startfile(str(folder))
        else:
            subprocess.Popen(["xdg-open", str(folder)])
        return {
            "status": "success",
            "message": f"Đã mở thư mục trên máy tính: {folder.name}",
            "folder_path": str(folder),
        }
    except Exception as exc:
        logger.error("Error opening folder %s: %s", folder, exc)
        return {
            "status": "error",
            "message": f"Không thể tự động mở thư mục: {exc}",
            "folder_path": str(folder),
        }


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
                    "file_size_formatted": format_size_human(fsize),
                    "file_ext": p.suffix.lstrip(".").lower(),
                    "category": category,
                    "category_label": category_label,
                    "updated_at": mtime_str
                })

    # Sort newest first
    docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return docs
