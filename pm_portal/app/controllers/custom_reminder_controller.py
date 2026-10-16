"""Controller handling custom personal reminders API endpoints."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.custom_reminder_service import (
    create_custom_reminder,
    delete_custom_reminder,
    get_available_project_documents,
    get_custom_reminders_list,
    toggle_custom_reminder_status,
    update_custom_reminder,
)

logger = logging.getLogger(__name__)


async def list_custom_reminders_controller(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Return filtered list of custom personal reminders."""
    try:
        return get_custom_reminders_list(status, priority, search)
    except Exception as exc:
        logger.error("Error listing custom reminders: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn nhắc nhở: {exc}")


async def create_custom_reminder_controller(
    title: str,
    due_date: str,
    description: str = "",
    due_time: str = "09:00",
    priority: str = "NORMAL",
    category: str = "GENERAL",
    file: Optional[UploadFile] = None,
    existing_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new personal reminder with optional file upload or link."""
    try:
        file_bytes = None
        file_name = None
        if file and file.filename:
            file_bytes = await file.read()
            file_name = file.filename

        return create_custom_reminder(
            title=title,
            due_date=due_date,
            description=description,
            due_time=due_time,
            priority=priority,
            category=category,
            file_bytes=file_bytes,
            file_name=file_name,
            existing_file_path=existing_file_path,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error("Error creating custom reminder: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi tạo nhắc nhở: {exc}")


async def update_custom_reminder_controller(
    reminder_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    due_time: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    file: Optional[UploadFile] = None,
    existing_file_path: Optional[str] = None,
    remove_attachment: bool = False,
) -> Dict[str, Any]:
    """Update an existing personal reminder."""
    try:
        file_bytes = None
        file_name = None
        if file and file.filename:
            file_bytes = await file.read()
            file_name = file.filename

        return update_custom_reminder(
            reminder_id=reminder_id,
            title=title,
            description=description,
            due_date=due_date,
            due_time=due_time,
            priority=priority,
            category=category,
            file_bytes=file_bytes,
            file_name=file_name,
            existing_file_path=existing_file_path,
            remove_attachment=remove_attachment,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error("Error updating custom reminder %d: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật nhắc nhở: {exc}")


async def toggle_reminder_status_controller(reminder_id: int) -> Dict[str, Any]:
    """Toggle completed/pending status."""
    try:
        return toggle_custom_reminder_status(reminder_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as exc:
        logger.error("Error toggling reminder %d: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi đổi trạng thái nhắc nhở: {exc}")


async def delete_custom_reminder_controller(reminder_id: int, delete_file: bool = False) -> Dict[str, Any]:
    """Delete a personal reminder."""
    try:
        success = delete_custom_reminder(reminder_id, delete_file)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy lời nhắc cần xóa.")
        return {
            "status": "success",
            "message": "Đã xóa lời nhắc thành công!"
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting custom reminder %d: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi xóa nhắc nhở: {exc}")


async def download_reminder_attachment_controller(reminder_id: int):
    """Download attached file for a reminder."""
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT attachment_name, attachment_path FROM custom_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row["attachment_path"]:
        raise HTTPException(status_code=404, detail="Lời nhắc này không có file đính kèm.")

    p = Path(row["attachment_path"])
    if not p.is_file():
        raise HTTPException(status_code=404, detail="File đính kèm không còn tồn tại trên máy tính.")

    return FileResponse(
        path=str(p),
        filename=row["attachment_name"] or p.name,
        media_type="application/octet-stream"
    )


async def list_available_project_files_controller() -> Dict[str, Any]:
    """List project files available for linking to reminders."""
    try:
        files = get_available_project_documents()
        return {
            "status": "success",
            "files": files,
            "total": len(files)
        }
    except Exception as exc:
        logger.error("Error listing project files: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi quét danh sách file: {exc}")
