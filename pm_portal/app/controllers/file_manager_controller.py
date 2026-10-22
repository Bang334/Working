"""Controller handling Document and File Manager actions."""

import logging
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.services.file_manager_service import (
    decode_file_id,
    delete_file,
    list_all_files,
    open_category_folder,
    open_file_directly,
    open_file_in_explorer,
    rename_file,
    upload_file_to_category,
)

logger = logging.getLogger(__name__)


def get_files_controller(
    category: Optional[str] = None,
    search: Optional[str] = None,
    extension: Optional[str] = None,
    sort_by: str = "updated_at_desc",
) -> Dict[str, Any]:
    """Retrieve full file list with filters and metadata."""
    try:
        return list_all_files(
            category=category,
            search=search,
            extension=extension,
            sort_by=sort_by,
        )
    except Exception as exc:
        logger.exception("Error listing files: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi quét danh sách file: {str(exc)}")


def download_file_controller(file_id: str) -> FileResponse:
    """Download a file by file_id safely with UTF-8 filename header."""
    try:
        file_path = decode_file_id(file_id)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Không tìm thấy file trên hệ thống.")

        encoded_filename = quote(file_path.name)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            headers=headers,
        )
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error downloading file %s: %s", file_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi tải file: {str(exc)}")


def preview_file_controller(file_id: str) -> FileResponse:
    """Preview a document or image inline in the browser."""
    try:
        file_path = decode_file_id(file_id)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Không tìm thấy file trên hệ thống.")

        ext = file_path.suffix.lstrip(".").lower()
        media_type = "application/octet-stream"
        if ext == "pdf":
            media_type = "application/pdf"
        elif ext in ("png", "jpg", "jpeg", "webp", "gif"):
            media_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"

        encoded_filename = quote(file_path.name)
        headers = {
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
        }
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            headers=headers,
        )
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.exception("Error previewing file %s: %s", file_id, exc)
        raise HTTPException(status_code=500, detail=f"Lỗi xem trước file: {str(exc)}")


def open_file_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open file directly on user's computer with default program (Word, Excel, PDF...)."""
    file_id = payload.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Thiếu mã file (file_id).")
    try:
        return open_file_directly(file_id)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as exc:
        logger.exception("Error opening file directly: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def open_explorer_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open File Explorer at file location on Windows."""
    file_id = payload.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Thiếu mã file (file_id).")
    try:
        return open_file_in_explorer(file_id)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as exc:
        logger.exception("Error opening file in explorer: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def open_folder_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open category folder directly in File Explorer."""
    category = payload.get("category", "all")
    try:
        return open_category_folder(category)
    except Exception as exc:
        logger.exception("Error opening category folder: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def delete_file_controller(file_id: str) -> Dict[str, Any]:
    """Delete a document file safely."""
    try:
        return delete_file(file_id)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except PermissionError as perm:
        raise HTTPException(status_code=403, detail=str(perm))
    except Exception as exc:
        logger.exception("Error deleting file: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


def rename_file_controller(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rename a document file safely."""
    file_id = payload.get("file_id")
    new_name = payload.get("new_name")
    if not file_id or not new_name:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp file_id và tên mới.")
    try:
        return rename_file(file_id, new_name)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except PermissionError as perm:
        raise HTTPException(status_code=403, detail=str(perm))
    except ValueError as val:
        raise HTTPException(status_code=400, detail=str(val))
    except Exception as exc:
        logger.exception("Error renaming file: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


async def upload_file_controller(file: UploadFile, category: str) -> Dict[str, Any]:
    """Upload new document file into specified category."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không tìm thấy tên file tải lên.")
    try:
        content = await file.read()
        return upload_file_to_category(category, file.filename, content)
    except Exception as exc:
        logger.exception("Error uploading file: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
