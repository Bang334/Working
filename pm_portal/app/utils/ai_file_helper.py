# -*- coding: utf-8 -*-
"""Helper for extracting text or preparing multimodal inlineData from uploaded files for Gemini AI."""

import base64
import io
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def process_uploaded_file_for_ai(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Process an uploaded file for Gemini AI.
    Returns:
        (extracted_text, inline_data_part)
        - extracted_text: str text if file is Excel (.xlsx/.xls), Word (.docx), or text (.txt/.csv).
        - inline_data_part: dict {"inlineData": {"mimeType": ..., "data": base64}} if file is Image or PDF.
    """
    if not file_bytes:
        return None, None

    fn_lower = (filename or "").lower()
    c_type = (content_type or "").lower()

    # 1. Images (PNG, JPG, JPEG, WEBP)
    if fn_lower.endswith((".png", ".jpg", ".jpeg", ".webp")) or c_type.startswith("image/"):
        mime = "image/png" if fn_lower.endswith(".png") else "image/jpeg"
        if fn_lower.endswith(".webp"):
            mime = "image/webp"
        b64_str = base64.b64encode(file_bytes).decode("utf-8")
        return None, {"inlineData": {"mimeType": mime, "data": b64_str}}

    # 2. PDF Documents
    if fn_lower.endswith(".pdf") or "application/pdf" in c_type:
        b64_str = base64.b64encode(file_bytes).decode("utf-8")
        return None, {"inlineData": {"mimeType": "application/pdf", "data": b64_str}}

    # 3. Excel Spreadsheets (.xlsx, .xls)
    if fn_lower.endswith((".xlsx", ".xls")) or "spreadsheet" in c_type or "excel" in c_type:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            lines = [f"[NỘI DUNG TẬP TIN EXCEL: {filename}]"]
            for sname in wb.sheetnames[:4]:  # Read up to first 4 sheets
                ws = wb[sname]
                lines.append(f"\n--- SHEET: {sname} ---")
                row_count = 0
                for row in ws.iter_rows(values_only=True):
                    if any(c is not None and str(c).strip() for c in row):
                        row_vals = [str(c).strip() if c is not None else "" for c in row]
                        lines.append(" | ".join(row_vals))
                        row_count += 1
                        if row_count >= 150:  # Cap at 150 non-empty rows per sheet
                            lines.append("... (đã rút gọn các dòng tiếp theo)")
                            break
            return "\n".join(lines), None
        except Exception as e:
            logger.warning("Failed to parse Excel file %s: %s", filename, e)
            return f"[Lỗi đọc file Excel {filename}: {e}]", None

    # 4. Word Documents (.docx)
    if fn_lower.endswith(".docx") or "wordprocessingml" in c_type:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            lines = [f"[NỘI DUNG TẬP TIN WORD: {filename}]"]
            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt:
                    lines.append(txt)
            for tbl in doc.tables:
                lines.append("\n[BẢNG DỮ LIỆU WORD]")
                for r in tbl.rows:
                    cells_txt = [c.text.strip().replace("\n", " ") for c in r.cells]
                    lines.append(" | ".join(cells_txt))
            return "\n".join(lines), None
        except Exception as e:
            logger.warning("Failed to parse Word file %s: %s", filename, e)
            return f"[Lỗi đọc file Word {filename}: {e}]", None

    # 5. Plain Text / CSV / JSON
    try:
        decoded_text = file_bytes.decode("utf-8")
        return f"[NỘI DUNG TẬP TIN: {filename}]\n{decoded_text}", None
    except UnicodeDecodeError:
        try:
            decoded_text = file_bytes.decode("cp1258", errors="ignore")
            return f"[NỘI DUNG TẬP TIN: {filename}]\n{decoded_text}", None
        except Exception:
            return f"[Không thể đọc dạng text từ tập tin nhị phân: {filename}]", None
