"""File Manager Service.
Centralized document management across all project folders, outputs, and templates.
"""

import base64
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.config import OUTPUTS_DIR, WORKING_DIR

logger = logging.getLogger(__name__)

# Thư mục gốc hồ sơ dự án
HO_SO_DIR = WORKING_DIR / "Ho So Du An"
BIEU_MAU_DIR = WORKING_DIR / "Bieu Mau"

# Cấu hình danh mục thư mục chuẩn
CATEGORY_CONFIG = {
    "hop_dong": {
        "label": "Hợp Đồng",
        "subdirs": ["Hop Dong"],
        "color": "blue",
        "badge_class": "badge-blue",
        "tab_url": "/contracts",
        "icon": "contract",
        "allow_upload": True,
    },
    "bao_gia": {
        "label": "Báo Giá",
        "subdirs": ["Bao Gia"],
        "color": "cyan",
        "badge_class": "badge-cyan",
        "tab_url": "/quotations",
        "icon": "quote",
        "allow_upload": True,
    },
    "nghiem_thu": {
        "label": "Nghiệm Thu",
        "subdirs": ["Nghiem Thu"],
        "color": "emerald",
        "badge_class": "badge-emerald",
        "tab_url": "/acceptance",
        "icon": "acceptance",
        "allow_upload": True,
    },
    "don_xin_thanh_toan": {
        "label": "Đơn Xin Thanh Toán",
        "subdirs": ["Don Xin Thanh Toan"],
        "color": "indigo",
        "badge_class": "badge-indigo",
        "tab_url": "/payment-requests",
        "icon": "voucher",
        "allow_upload": True,
    },
    "yeu_cau_thanh_toan": {
        "label": "Đề Nghị Thanh Toán",
        "subdirs": ["Yeu Cau Thanh Toan"],
        "color": "amber",
        "badge_class": "badge-amber",
        "tab_url": "/reminders",
        "icon": "receipt",
        "allow_upload": True,
    },
    "xuat_kho": {
        "label": "Xuất Kho & Giao Nhận",
        "subdirs": ["Xuat Kho"],
        "color": "purple",
        "badge_class": "badge-purple",
        "tab_url": "/delivery",
        "icon": "delivery",
        "allow_upload": True,
    },
    "nhac_nho": {
        "label": "Nhắc Nợ & Đính Kèm",
        "subdirs": ["Nhac Nho"],
        "color": "rose",
        "badge_class": "badge-rose",
        "tab_url": "/reminders",
        "icon": "bell",
        "allow_upload": True,
    },
    "test_data": {
        "label": "Dữ Liệu Mẫu & Test",
        "subdirs": ["Dữ liệu test", "Du lieu test"],
        "color": "gray",
        "badge_class": "badge-gray",
        "tab_url": "/files",
        "icon": "folder",
        "allow_upload": True,
    },
    "outputs": {
        "label": "File Vừa Xuất",
        "subdirs": [],
        "color": "teal",
        "badge_class": "badge-teal",
        "tab_url": "/files",
        "icon": "sparkles",
        "allow_upload": False,
    },
    "bieu_mau": {
        "label": "Biểu Mẫu Gốc",
        "subdirs": [],
        "color": "slate",
        "badge_class": "badge-slate",
        "tab_url": "/files",
        "icon": "template",
        "allow_upload": False,
    },
}


def format_size_human(size_in_bytes: int) -> str:
    """Format file byte size to human readable string (KB, MB, GB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    return f"{size_in_bytes / (1024 * 1024 * 1024):.2f} GB"


def encode_file_id(path: Path) -> str:
    """Encode relative path from WORKING_DIR safely as base64 string."""
    rel = path.resolve().relative_to(WORKING_DIR.resolve()).as_posix()
    return base64.urlsafe_b64encode(rel.encode("utf-8")).decode("ascii")


def decode_file_id(file_id: str) -> Path:
    """Decode file_id and verify it resolves safely inside WORKING_DIR."""
    try:
        rel_str = base64.urlsafe_b64decode(file_id.encode("ascii")).decode("utf-8")
        target_path = (WORKING_DIR / rel_str).resolve()
        # Security check: Target must stay inside WORKING_DIR
        working_res = WORKING_DIR.resolve()
        if not str(target_path).startswith(str(working_res)):
            raise ValueError("Đường dẫn file không hợp lệ hoặc nằm ngoài thư mục dự án.")
        return target_path
    except Exception as exc:
        logger.error("Failed to decode file_id '%s': %s", file_id, exc)
        raise ValueError("Mã định danh file không hợp lệ.")


def get_file_icon_type(ext: str) -> str:
    """Return icon type identifier based on extension."""
    ext = ext.lower().lstrip(".")
    if ext in ("docx", "doc"):
        return "word"
    elif ext in ("xlsx", "xls", "csv"):
        return "excel"
    elif ext == "pdf":
        return "pdf"
    elif ext in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"):
        return "image"
    elif ext in ("zip", "rar", "7z", "tar", "gz"):
        return "zip"
    return "generic"


def determine_category_for_path(path: Path) -> str:
    """Determine category key from file path."""
    resolved = path.resolve()
    
    # Check if inside Bieu Mau
    if str(resolved).startswith(str(BIEU_MAU_DIR.resolve())):
        return "bieu_mau"
    
    # Check if inside outputs
    if str(resolved).startswith(str(OUTPUTS_DIR.resolve())):
        return "outputs"
    
    # Check inside Ho So Du An subdirs
    if str(resolved).startswith(str(HO_SO_DIR.resolve())):
        try:
            rel = resolved.relative_to(HO_SO_DIR.resolve())
            top_part = rel.parts[0] if rel.parts else ""
            for cat_key, cfg in CATEGORY_CONFIG.items():
                for s in cfg.get("subdirs", []):
                    if top_part.lower() == s.lower():
                        return cat_key
        except Exception:
            pass
            
    return "other"


def collect_single_file_metadata(p: Path) -> Optional[Dict[str, Any]]:
    """Extract full file metadata dictionary."""
    try:
        if not p.is_file():
            return None
        # Ignore temp lock files and hidden files
        if p.name.startswith("~$") or p.name.startswith("."):
            return None

        stat = p.stat()
        file_size = stat.st_size
        file_ext = p.suffix.lstrip(".").lower()
        category = determine_category_for_path(p)
        cfg = CATEGORY_CONFIG.get(category, {
            "label": "Khác",
            "color": "gray",
            "badge_class": "badge-gray",
            "tab_url": "/files",
            "icon": "folder",
        })

        rel_path = p.resolve().relative_to(WORKING_DIR.resolve()).as_posix()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        ctime = datetime.fromtimestamp(stat.st_ctime)

        is_bieu_mau = (category == "bieu_mau")
        can_preview = file_ext in ("png", "jpg", "jpeg", "gif", "webp", "pdf")

        return {
            "id": encode_file_id(p),
            "file_name": p.name,
            "relative_path": rel_path,
            "folder_name": p.parent.name,
            "folder_relative": p.parent.resolve().relative_to(WORKING_DIR.resolve()).as_posix(),
            "file_size": file_size,
            "file_size_human": format_size_human(file_size),
            "file_ext": file_ext,
            "icon_type": get_file_icon_type(file_ext),
            "category": category,
            "category_label": cfg.get("label", "Khác"),
            "category_color": cfg.get("color", "gray"),
            "category_badge_class": cfg.get("badge_class", "badge-gray"),
            "tab_url": cfg.get("tab_url", "/files"),
            "updated_at": mtime.isoformat(),
            "updated_at_formatted": mtime.strftime("%d/%m/%Y %H:%M"),
            "created_at": ctime.isoformat(),
            "created_at_formatted": ctime.strftime("%d/%m/%Y %H:%M"),
            "can_delete": not is_bieu_mau,
            "can_rename": not is_bieu_mau,
            "can_preview": can_preview,
        }
    except Exception as exc:
        logger.warning("Error reading file metadata for %s: %s", p, exc)
        return None


def list_all_files(
    category: Optional[str] = None,
    search: Optional[str] = None,
    extension: Optional[str] = None,
    sort_by: str = "updated_at_desc"
) -> Dict[str, Any]:
    """Scan and retrieve all files matching search and category criteria."""
    targets = [HO_SO_DIR, BIEU_MAU_DIR, OUTPUTS_DIR]
    all_files: List[Dict[str, Any]] = []
    seen_paths = set()
    seen_signatures = set()

    # Thống kê tổng hợp
    category_counts: Dict[str, int] = {k: 0 for k in CATEGORY_CONFIG.keys()}
    category_counts["other"] = 0
    extension_counts: Dict[str, int] = {
        "word": 0,
        "excel": 0,
        "pdf": 0,
        "image": 0,
        "other": 0,
    }
    total_size = 0

    for target_dir in targets:
        if not target_dir.exists():
            continue
        for p in target_dir.rglob("*"):
            if not p.is_file():
                continue
            # Bỏ qua file tạm, file backup zip của template, và file ẩn
            if p.name.startswith("~$") or p.name.startswith(".") or "_backup" in p.name.lower():
                continue
            if "zip" in p.parts:
                continue

            resolved_str = str(p.resolve())
            if resolved_str in seen_paths:
                continue

            # Chống trùng lặp tuyệt đối (Deduplication):
            # Nếu một file có cùng tên và cùng dung lượng (hoặc file trùng tên từ outputs),
            # hệ thống chỉ giữ 1 bản duy nhất chính thức, loại bỏ hoàn toàn việc nhân đôi hiển thị.
            try:
                fsize = p.stat().st_size
            except Exception:
                fsize = 0

            file_sig = (p.name.lower(), fsize)
            if file_sig in seen_signatures:
                continue

            is_in_outputs = str(p.resolve()).startswith(str(OUTPUTS_DIR.resolve()))
            if is_in_outputs and any(sig[0] == p.name.lower() for sig in seen_signatures):
                continue

            seen_paths.add(resolved_str)
            seen_signatures.add(file_sig)

            meta = collect_single_file_metadata(p)
            if not meta:
                continue

            # Tích lũy thống kê toàn bộ (trước khi filter)
            cat = meta["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
            total_size += meta["file_size"]

            itype = meta["icon_type"]
            if itype in extension_counts:
                extension_counts[itype] += 1
            else:
                extension_counts["other"] += 1

            all_files.append(meta)

    # Áp dụng bộ lọc Category
    filtered = all_files
    if category and category != "all":
        filtered = [f for f in filtered if f["category"] == category]

    # Áp dụng bộ lọc Extension
    if extension and extension != "all":
        ext_clean = extension.lower().lstrip(".")
        if ext_clean == "word":
            filtered = [f for f in filtered if f["file_ext"] in ("docx", "doc")]
        elif ext_clean == "excel":
            filtered = [f for f in filtered if f["file_ext"] in ("xlsx", "xls", "csv")]
        elif ext_clean == "pdf":
            filtered = [f for f in filtered if f["file_ext"] == "pdf"]
        elif ext_clean == "image":
            filtered = [f for f in filtered if f["file_ext"] in ("png", "jpg", "jpeg", "gif", "webp", "bmp")]
        else:
            filtered = [f for f in filtered if f["file_ext"] == ext_clean]

    # Áp dụng tìm kiếm từ khóa (Search Keyword)
    if search and search.strip():
        term = search.strip().lower()
        filtered = [
            f for f in filtered
            if term in f["file_name"].lower()
            or term in f["category_label"].lower()
            or term in f["folder_name"].lower()
            or term in f["file_ext"].lower()
        ]

    # Sắp xếp danh sách
    if sort_by == "updated_at_desc":
        filtered.sort(key=lambda x: x["updated_at"], reverse=True)
    elif sort_by == "updated_at_asc":
        filtered.sort(key=lambda x: x["updated_at"])
    elif sort_by == "name_asc":
        filtered.sort(key=lambda x: x["file_name"].lower())
    elif sort_by == "name_desc":
        filtered.sort(key=lambda x: x["file_name"].lower(), reverse=True)
    elif sort_by == "size_desc":
        filtered.sort(key=lambda x: x["file_size"], reverse=True)
    elif sort_by == "size_asc":
        filtered.sort(key=lambda x: x["file_size"])
    else:
        filtered.sort(key=lambda x: x["updated_at"], reverse=True)

    return {
        "status": "success",
        "total_files": len(all_files),
        "total_filtered": len(filtered),
        "total_size_bytes": total_size,
        "total_size_human": format_size_human(total_size),
        "category_counts": category_counts,
        "extension_counts": extension_counts,
        "files": filtered,
    }


def open_file_directly(file_id: str) -> Dict[str, Any]:
    """Open a file directly with its default associated application (Word, Excel, PDF...) on local machine."""
    target_path = decode_file_id(file_id)
    if not target_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file trên máy: {target_path.name}")

    try:
        if os.name == "nt":
            os.startfile(str(target_path))
        else:
            subprocess.Popen(["xdg-open", str(target_path)])

        return {
            "status": "success",
            "message": f"Đã mở file '{target_path.name}' trên máy tính.",
            "file_name": target_path.name,
            "path": str(target_path),
        }
    except Exception as exc:
        logger.exception("Error opening file directly: %s", exc)
        raise RuntimeError(f"Không thể mở file: {exc}")


def open_file_in_explorer(file_id: str) -> Dict[str, Any]:
    """Open File Explorer on Windows and highlight the target file without falling back to Documents."""
    target_path = decode_file_id(file_id)
    if not target_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file trên máy: {target_path.name}")

    try:
        if os.name == "nt":
            norm = os.path.normpath(str(target_path))
            # Cú pháp chuẩn trên Windows: explorer /select,"<norm_path>" truyền dạng string đơn
            subprocess.Popen(f'explorer /select,"{norm}"')
        else:
            subprocess.Popen(["xdg-open", str(target_path.parent)])

        return {
            "status": "success",
            "message": f"Đã mở vị trí file trên máy: {target_path.name}",
            "file_name": target_path.name,
            "path": str(target_path),
        }
    except Exception as exc:
        logger.exception("Error opening file with select, falling back to folder: %s", exc)
        try:
            if os.name == "nt":
                os.startfile(str(target_path.parent))
            return {
                "status": "success",
                "message": f"Đã mở thư mục chứa file: {target_path.parent.name}",
                "file_name": target_path.name,
                "path": str(target_path.parent),
            }
        except Exception as e2:
            raise RuntimeError(f"Không thể mở thư mục trên máy tính: {e2}")
    except Exception as exc:
        logger.exception("Error opening file in explorer: %s", exc)
        raise RuntimeError(f"Không thể mở thư mục trên máy tính: {exc}")


def open_category_folder(category: str) -> Dict[str, Any]:
    """Open specific category folder directly in File Explorer."""
    folder_path: Path
    if category == "outputs":
        folder_path = OUTPUTS_DIR
    elif category == "bieu_mau":
        folder_path = BIEU_MAU_DIR
    elif category in CATEGORY_CONFIG:
        subdirs = CATEGORY_CONFIG[category].get("subdirs", [])
        if subdirs:
            folder_path = HO_SO_DIR / subdirs[0]
        else:
            folder_path = HO_SO_DIR
    else:
        folder_path = HO_SO_DIR

    folder_path.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            os.startfile(str(folder_path))
        else:
            subprocess.Popen(["xdg-open", str(folder_path)])
            
        return {
            "status": "success",
            "message": f"Đã mở thư mục '{folder_path.name}' trên máy tính.",
            "folder_path": str(folder_path),
        }
    except Exception as exc:
        logger.exception("Error opening category folder: %s", exc)
        raise RuntimeError(f"Không thể mở thư mục: {exc}")


def delete_file(file_id: str) -> Dict[str, Any]:
    """Delete a file safely with anti-template protection."""
    target_path = decode_file_id(file_id)
    if not target_path.exists():
        raise FileNotFoundError("File không tồn tại hoặc đã bị xóa trước đó.")

    # Bảo vệ nghiêm ngặt: Biểu mẫu gốc không được phép xóa
    category = determine_category_for_path(target_path)
    if category == "bieu_mau":
        raise PermissionError("Không thể xóa file Biểu Mẫu Gốc của hệ thống.")

    file_name = target_path.name
    try:
        os.remove(target_path)
        logger.info("Deleted file safely: %s", target_path)
        return {
            "status": "success",
            "message": f"Đã xóa file '{file_name}' thành công.",
            "file_name": file_name,
        }
    except Exception as exc:
        logger.exception("Error deleting file %s: %s", target_path, exc)
        raise RuntimeError(f"Lỗi khi xóa file: {exc}")


def rename_file(file_id: str, new_name: str) -> Dict[str, Any]:
    """Rename a file safely without changing its parent directory."""
    target_path = decode_file_id(file_id)
    if not target_path.exists():
        raise FileNotFoundError("Không tìm thấy file cần đổi tên.")

    category = determine_category_for_path(target_path)
    if category == "bieu_mau":
        raise PermissionError("Không được phép đổi tên file Biểu Mẫu Gốc.")

    cleaned_name = new_name.strip()
    if not cleaned_name:
        raise ValueError("Tên file mới không được để trống.")

    # Đảm bảo giữ nguyên phần mở rộng nếu người dùng không gõ đuôi
    current_ext = target_path.suffix
    if not cleaned_name.lower().endswith(current_ext.lower()):
        cleaned_name = f"{cleaned_name}{current_ext}"

    destination_path = target_path.parent / cleaned_name
    if destination_path.exists() and destination_path != target_path:
        raise ValueError(f"Tên file '{cleaned_name}' đã tồn tại trong thư mục.")

    try:
        target_path.rename(destination_path)
        new_meta = collect_single_file_metadata(destination_path)
        return {
            "status": "success",
            "message": f"Đã đổi tên file thành '{cleaned_name}'.",
            "old_name": target_path.name,
            "new_name": cleaned_name,
            "file": new_meta,
        }
    except Exception as exc:
        logger.exception("Error renaming file %s: %s", target_path, exc)
        raise RuntimeError(f"Không thể đổi tên file: {exc}")


def upload_file_to_category(category: str, file_name: str, file_bytes: bytes) -> Dict[str, Any]:
    """Upload a new document file directly to the appropriate category directory."""
    if not file_name or not file_bytes:
        raise ValueError("File hoặc dữ liệu tải lên không hợp lệ.")

    # Xác định thư mục đích
    subdirs = CATEGORY_CONFIG.get(category, {}).get("subdirs", [])
    if subdirs:
        dest_dir = HO_SO_DIR / subdirs[0]
    else:
        dest_dir = HO_SO_DIR / "Hop Dong"

    dest_dir.mkdir(parents=True, exist_ok=True)
    target_path = dest_dir / file_name

    # Nếu file đã tồn tại, tự động thêm timestamp để không ghi đè
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = dest_dir / f"{stem}_{timestamp}{suffix}"

    try:
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        new_meta = collect_single_file_metadata(target_path)
        return {
            "status": "success",
            "message": f"Đã tải file '{target_path.name}' lên thư mục '{dest_dir.name}'.",
            "file": new_meta,
        }
    except Exception as exc:
        logger.exception("Error uploading file to category %s: %s", category, exc)
        raise RuntimeError(f"Lỗi khi lưu file tải lên: {exc}")
