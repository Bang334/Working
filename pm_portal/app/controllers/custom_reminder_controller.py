"""Controller handling custom personal reminders API endpoints."""

import json
import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.custom_reminder_service import (
    create_custom_reminder,
    delete_custom_reminder,
    get_attachment_by_index,
    get_available_project_documents,
    get_custom_reminders_list,
    get_sidebar_due_stats,
    open_folder_in_os,
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


async def get_sidebar_due_count_controller() -> Dict[str, Any]:
    """Return due/overdue count for sidebar glowing red badge."""
    try:
        return get_sidebar_due_stats()
    except Exception as exc:
        logger.error("Error calculating sidebar due stats: %s", exc)
        return {"status": "success", "today_count": 0, "overdue_count": 0, "total_due": 0, "has_due": False}


async def create_custom_reminder_controller(
    title: str,
    due_date: str,
    description: str = "",
    due_time: str = "09:00",
    priority: str = "NORMAL",
    category: str = "GENERAL",
    files: Optional[List[UploadFile]] = None,
    existing_file_paths: Optional[str] = None,
    file: Optional[UploadFile] = None,
    existing_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new personal reminder with dedicated folder, multiple files, and image attachments."""
    try:
        uploaded_files: List[Tuple[str, bytes]] = []

        # Multi-file list
        if files:
            for f in files:
                if f and f.filename:
                    content = await f.read()
                    uploaded_files.append((f.filename, content))

        # Legacy single file
        if file and file.filename:
            content = await file.read()
            uploaded_files.append((file.filename, content))

        # Parse linked paths
        linked_paths: List[str] = []
        if existing_file_paths and existing_file_paths.strip():
            try:
                parsed = json.loads(existing_file_paths)
                if isinstance(parsed, list):
                    linked_paths.extend([str(p).strip() for p in parsed if str(p).strip()])
                else:
                    linked_paths.append(str(parsed).strip())
            except Exception:
                for line in existing_file_paths.split("\n"):
                    for item in line.split(","):
                        if item.strip():
                            linked_paths.append(item.strip())

        if existing_file_path and existing_file_path.strip():
            linked_paths.append(existing_file_path.strip())

        return create_custom_reminder(
            title=title,
            due_date=due_date,
            description=description,
            due_time=due_time,
            priority=priority,
            category=category,
            uploaded_files=uploaded_files,
            linked_file_paths=linked_paths,
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
    files: Optional[List[UploadFile]] = None,
    existing_file_paths: Optional[str] = None,
    file: Optional[UploadFile] = None,
    existing_file_path: Optional[str] = None,
    remove_attachment: bool = False,
    removed_indices: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing personal reminder and its attachments."""
    try:
        uploaded_files: List[Tuple[str, bytes]] = []
        if files:
            for f in files:
                if f and f.filename:
                    content = await f.read()
                    uploaded_files.append((f.filename, content))

        if file and file.filename:
            content = await file.read()
            uploaded_files.append((file.filename, content))

        linked_paths: List[str] = []
        if existing_file_paths and existing_file_paths.strip():
            try:
                parsed = json.loads(existing_file_paths)
                if isinstance(parsed, list):
                    linked_paths.extend([str(p).strip() for p in parsed if str(p).strip()])
                else:
                    linked_paths.append(str(parsed).strip())
            except Exception:
                for line in existing_file_paths.split("\n"):
                    for item in line.split(","):
                        if item.strip():
                            linked_paths.append(item.strip())

        if existing_file_path and existing_file_path.strip():
            linked_paths.append(existing_file_path.strip())

        removed_idx_list: List[int] = []
        if removed_indices and removed_indices.strip():
            try:
                p_idx = json.loads(removed_indices)
                if isinstance(p_idx, list):
                    removed_idx_list = [int(i) for i in p_idx]
            except Exception:
                pass

        return update_custom_reminder(
            reminder_id=reminder_id,
            title=title,
            description=description,
            due_date=due_date,
            due_time=due_time,
            priority=priority,
            category=category,
            uploaded_files=uploaded_files,
            linked_file_paths=linked_paths,
            remove_attachment=remove_attachment,
            removed_file_indices=removed_idx_list,
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


async def delete_custom_reminder_controller(reminder_id: int, delete_files: bool = False) -> Dict[str, Any]:
    """Delete a personal reminder, and optionally delete its dedicated folder and files."""
    try:
        success = delete_custom_reminder(reminder_id, delete_files)
        if not success:
            raise HTTPException(status_code=404, detail="Không tìm thấy lời nhắc cần xóa.")
        return {
            "status": "success",
            "message": "Đã xóa lời nhắc và tệp tin trong thư mục!" if delete_files else "Đã xóa lời nhắc, tệp tin vẫn được giữ nguyên trên máy tính!"
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting custom reminder %d: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi xóa nhắc nhở: {exc}")


async def download_reminder_attachment_controller(reminder_id: int, index: int = 0):
    """Download attached file by index."""
    try:
        path_obj, filename, _ = get_attachment_by_index(reminder_id, index)
        return FileResponse(
            path=str(path_obj),
            filename=filename,
            media_type="application/octet-stream"
        )
    except (ValueError, IndexError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        logger.error("Error downloading attachment %d (index %d): %s", reminder_id, index, exc)
        raise HTTPException(status_code=500, detail="Lỗi khi tải tệp đính kèm.")


async def preview_reminder_attachment_controller(reminder_id: int, index: int = 0):
    """Preview image or document inline in browser by attachment index."""
    try:
        path_obj, filename, ext = get_attachment_by_index(reminder_id, index)
        mime, _ = mimetypes.guess_type(str(path_obj))
        if not mime:
            mime = "image/png" if ext in ("png", "jpg", "jpeg", "webp", "gif") else "application/octet-stream"

        return FileResponse(
            path=str(path_obj),
            filename=filename,
            media_type=mime,
            content_disposition_type="inline"
        )
    except (ValueError, IndexError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        logger.error("Error previewing attachment %d (index %d): %s", reminder_id, index, exc)
        raise HTTPException(status_code=500, detail="Lỗi khi xem trước tệp.")


async def open_reminder_folder_controller(reminder_id: int) -> Dict[str, Any]:
    """Open the dedicated reminder folder in File Explorer on Windows."""
    try:
        return open_folder_in_os(reminder_id)
    except Exception as exc:
        logger.error("Error opening folder for reminder %d: %s", reminder_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


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
