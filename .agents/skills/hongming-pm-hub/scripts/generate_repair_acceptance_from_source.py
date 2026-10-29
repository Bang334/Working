# -*- coding: utf-8 -*-
"""Chuyển ghi chú từ biên bản sửa chữa sang biên bản nghiệm thu.

Quy tắc nghiệp vụ:
- Chỉ đọc ghi chú từ workbook biên bản sửa chữa; không dùng ghi chú cũ của
  workbook nghiệm thu làm dữ liệu đầu vào.
- Gemini phân tích và gán ghi chú cho đúng sheet sản phẩm.
- Chỉ gán khi ghi chú nguồn nêu rõ mã sản phẩm/serial có sheet tương ứng.
- Ghi chú không nêu rõ sản phẩm không được gán; ô ghi chú chi tiết để trống.
- Chỉ thay giá trị ô ghi chú, không thay bố cục hay định dạng workbook mẫu.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from openpyxl import load_workbook


LOGGER = logging.getLogger("repair_acceptance_notes")
DEFAULT_SOURCE = Path(r"E:\Working\Bieu Mau\Biên bản sữa chữa.xlsx")
DEFAULT_TARGET = Path(r"E:\Working\Bieu Mau\Mau_Goc_Nghiem_Thu_Sua_Chua.xlsx")

NOTE_LABELS = ("ghi chú", "備註")
STOP_MARKERS = (
    "chữ ký",
    "ký nhận",
    "雙方簽收",
    "đại diện bên",
    "甲方",
    "乙方",
)

GEMINI_PROMPT = """Bạn là AI kiểm soát dữ liệu biên bản sửa chữa song ngữ Việt - Trung.

Nhiệm vụ: đọc phần ghi chú nguồn và ánh xạ từng ghi chú tới đúng sheet sản phẩm.

Quy tắc bắt buộc:
1. Chỉ tạo assignment khi chính dòng ghi chú có nêu rõ mã sản phẩm/serial.
2. sheet_name phải là một tên trong danh sách sheet hợp lệ được cung cấp.
3. Không suy đoán sản phẩm từ ngữ cảnh, thứ tự, model chung hoặc nội dung lỗi.
4. Ghi chú không nêu mã sản phẩm phải đưa vào ignored_notes, không assignment.
5. note phải giữ nguyên nội dung song ngữ đứng sau mã sản phẩm/model và dấu gạch ngang; không rút gọn, không dịch lại, không bổ sung.
6. source_line phải chép nguyên văn đúng dòng nguồn.
7. Chỉ trả JSON hợp lệ, không giải thích ngoài JSON.

Định dạng:
{
  "assignments": [
    {
      "sheet_name": "RFR900NA55RSVHBA036",
      "serial": "RFR900NA55RSVHBA036",
      "note": "Không có pin trước khi nhận sửa chữa / 送修前無電池",
      "source_line": "1. RFR900NA55RSVHBA036 (BF606-1677) – Không có pin trước khi nhận sửa chữa / 送修前無電池"
    }
  ],
  "ignored_notes": []
}
"""


def _configure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")


def _normalize(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _clean_json(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Gemini không trả về một JSON object.")
    return data


def _load_gemini_config(workspace: Path) -> Tuple[List[str], List[str]]:
    """Nạp khóa/model từ biến môi trường hoặc cấu hình portal hiện có."""
    keys: List[str] = []
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        keys.append(env_key)

    models: List[str] = []
    portal_root = workspace / "pm_portal"
    if portal_root.is_dir():
        sys.path.insert(0, str(portal_root))
        try:
            from app.config import (  # type: ignore
                CANDIDATE_MODELS,
                DEFAULT_GEMINI_KEY,
                DEFAULT_GEMINI_KEYS,
            )

            for key in [DEFAULT_GEMINI_KEY, *DEFAULT_GEMINI_KEYS]:
                if key and key not in keys:
                    keys.append(key)
            models.extend(str(model) for model in CANDIDATE_MODELS if model)
        except Exception as exc:  # pragma: no cover - depends on local portal setup
            LOGGER.warning("Không nạp được cấu hình Gemini của portal: %s", exc)

    if not models:
        models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    if not keys:
        raise RuntimeError(
            "Không tìm thấy GEMINI_API_KEY và cũng không nạp được khóa từ pm_portal/app/config.py."
        )
    return keys, models


def _call_gemini(
    note_text: str,
    valid_sheets: Sequence[str],
    workspace: Path,
) -> Tuple[Dict[str, Any], str]:
    keys, models = _load_gemini_config(workspace)
    user_text = (
        GEMINI_PROMPT
        + "\nDanh sách sheet sản phẩm hợp lệ:\n"
        + json.dumps(list(valid_sheets), ensure_ascii=False)
        + "\n\nPhần ghi chú nguồn:\n---\n"
        + note_text
        + "\n---"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error: Optional[Exception] = None

    for key in keys:
        for model in models:
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={key}"
            )
            request = urllib.request.Request(
                endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=35) as response:
                    result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates") or []
                if not candidates:
                    raise ValueError("Gemini không trả về candidate.")
                response_text = candidates[0]["content"]["parts"][0]["text"]
                return _clean_json(response_text), model
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 403:
                    break
                if exc.code in (404, 429, 503):
                    continue
            except Exception as exc:  # pragma: no cover - network/model dependent
                last_error = exc
                continue

    raise RuntimeError(f"Không thể gọi Gemini để phân tích ghi chú: {last_error}")


def _is_note_label(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return any(label in text for label in NOTE_LABELS)


def _unique_texts(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def extract_source_note(source_path: Path) -> Tuple[str, str, str]:
    """Trả về (ghi chú, tên sheet, ô nhãn ghi chú)."""
    workbook = load_workbook(source_path, data_only=False, read_only=False)
    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                if not _is_note_label(cell.value):
                    continue

                collected: List[str] = []
                for row_index in range(cell.row + 1, worksheet.max_row + 1):
                    row_texts = _unique_texts(
                        worksheet.cell(row_index, col_index).value
                        for col_index in range(1, worksheet.max_column + 1)
                    )
                    joined = "\n".join(row_texts).strip()
                    if any(marker in joined.lower() for marker in STOP_MARKERS):
                        break
                    if joined:
                        collected.extend(row_texts)
                    elif collected:
                        break

                note_text = "\n".join(collected).strip()
                if note_text:
                    return note_text, worksheet.title, cell.coordinate

    raise ValueError("Không tìm thấy phần Ghi chú / 備註 có nội dung trong file sửa chữa.")


def _find_summary_sheet(workbook):
    for worksheet in workbook.worksheets:
        normalized = worksheet.title.strip().lower()
        if "nghiệm thu" in normalized or "nghiem thu" in normalized:
            return worksheet
    return workbook.worksheets[0]


def _find_summary_note_cell(worksheet):
    for row in worksheet.iter_rows():
        for cell in row:
            if _is_note_label(cell.value):
                return worksheet.cell(cell.row + 1, cell.column)
    raise ValueError(f"Không tìm thấy vùng Ghi chú / 備註 trên sheet {worksheet.title!r}.")


def _ensure_summary_note_height(worksheet, note_cell, note_text: str) -> None:
    """Increase only the summary-note row when explicit lines would be clipped."""
    if not note_text:
        return
    line_count = max(1, len(note_text.splitlines()))
    required_height = line_count * 19.5 + 16.0
    row_dimension = worksheet.row_dimensions[note_cell.row]
    current_height = row_dimension.height or worksheet.sheet_format.defaultRowHeight or 15.0
    if required_height > current_height:
        row_dimension.height = required_height


def _find_detail_note_cell(worksheet):
    for row in worksheet.iter_rows():
        for cell in row:
            if _is_note_label(cell.value):
                return worksheet.cell(cell.row + 1, cell.column)
    return None


def _line_for_serial(note_text: str, serial: str) -> Optional[str]:
    normalized_serial = _normalize(serial)
    for line in note_text.splitlines():
        if normalized_serial and normalized_serial in _normalize(line):
            return line.strip()
    return None


def _exact_note_from_source_line(line: str, serial: str) -> Optional[str]:
    pattern = re.compile(
        rf"{re.escape(serial)}\s*(?:\([^)]*\))?\s*[–—-]\s*(.+)$",
        re.IGNORECASE,
    )
    match = pattern.search(line)
    if not match:
        return None
    note = match.group(1).strip()
    return note or None


def validate_assignments(
    gemini_data: Dict[str, Any],
    note_text: str,
    valid_sheets: Sequence[str],
) -> Dict[str, str]:
    """Chặn suy đoán/hallucination; nội dung ghi ra luôn lấy nguyên văn nguồn."""
    allowed = {name: _normalize(name) for name in valid_sheets}
    assignments: Dict[str, str] = {}

    raw_assignments = gemini_data.get("assignments") or []
    if not isinstance(raw_assignments, list):
        raise ValueError("Gemini trả sai cấu trúc assignments.")

    for item in raw_assignments:
        if not isinstance(item, dict):
            continue
        sheet_name = str(item.get("sheet_name") or "").strip()
        serial = str(item.get("serial") or sheet_name).strip()
        if sheet_name not in allowed:
            continue
        if _normalize(serial) != allowed[sheet_name]:
            continue

        source_line = _line_for_serial(note_text, sheet_name)
        if not source_line:
            continue
        exact_note = _exact_note_from_source_line(source_line, sheet_name)
        if exact_note:
            assignments[sheet_name] = exact_note

    # Kiểm soát completeness: mọi dòng nguồn nêu đúng một sheet hợp lệ phải được
    # Gemini nhận diện. Nếu thiếu, dừng thay vì phát hành biên bản không đầy đủ.
    explicit_sheets = {
        name for name in valid_sheets if _line_for_serial(note_text, name) is not None
    }
    missing = sorted(explicit_sheets - set(assignments))
    if missing:
        raise ValueError(
            "Gemini chưa ánh xạ đủ các mã sản phẩm nêu rõ trong ghi chú: "
            + ", ".join(missing)
        )
    return assignments


def _fallback_path(target_path: Path) -> Path:
    return target_path.with_name(f"{target_path.stem}_v2{target_path.suffix}")


def _safe_save(workbook, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target_path.stem}_",
        suffix=target_path.suffix,
        dir=str(target_path.parent),
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        workbook.save(temp_path)
        try:
            os.replace(temp_path, target_path)
            return target_path
        except PermissionError:
            fallback = _fallback_path(target_path)
            try:
                os.replace(temp_path, fallback)
            except PermissionError:
                numbered = target_path.with_name(
                    f"{target_path.stem}_v2_{os.getpid()}{target_path.suffix}"
                )
                os.replace(temp_path, numbered)
                return numbered
            return fallback
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _find_source_table(workbook):
    """Locate the repair-item table by its bilingual business headers."""
    for worksheet in workbook.worksheets:
        for row_index in range(1, worksheet.max_row + 1):
            first = _normalized_text(worksheet.cell(row_index, 1).value)
            second = _normalized_text(worksheet.cell(row_index, 2).value)
            third = _normalized_text(worksheet.cell(row_index, 3).value)
            if (
                first == "stt"
                and ("tên sản phẩm" in second or "產品名稱" in second)
                and ("hạng mục" in third or "檢查" in third)
            ):
                return worksheet, row_index
    raise ValueError("Không tìm thấy bảng thiết bị sửa chữa có các cột STT và Tên Sản Phẩm.")


def _parse_stt(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and int(value) == value:
        return int(value)
    text = str(value or "").strip()
    return int(text) if text.isdigit() else None


def _extract_labeled_value(text: str) -> str:
    parts = re.split(r"[:：]", text, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def _extract_source_date(workbook) -> str:
    # The signed date is authoritative when present (for example 2026年10月09日).
    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                text = str(cell.value or "")
                match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
                if match:
                    year, month, day = map(int, match.groups())
                    return datetime(year, month, day).strftime("%d/%m/%Y")

    # Fall back to the first explicit dd/mm/yyyy date in the source workbook.
    for worksheet in workbook.worksheets:
        for row in worksheet.iter_rows():
            for cell in row:
                text = str(cell.value or "")
                match = re.search(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", text)
                if match:
                    day, month, year = map(int, match.groups())
                    return datetime(year, month, day).strftime("%d/%m/%Y")
    return ""


def extract_source_data(source_path: Path) -> Dict[str, Any]:
    """Read all device rows and core metadata from an uploaded repair workbook."""
    workbook = load_workbook(source_path, data_only=False, read_only=False)
    worksheet, header_row = _find_source_table(workbook)

    items: List[Dict[str, Any]] = []
    for row_index in range(header_row + 1, worksheet.max_row + 1):
        stt = _parse_stt(worksheet.cell(row_index, 1).value)
        serial = str(worksheet.cell(row_index, 2).value or "").strip()
        if stt is None:
            if items:
                break
            continue
        if not serial:
            raise ValueError(f"Dòng STT {stt} không có mã sản phẩm/serial.")
        items.append(
            {
                "stt": stt,
                "serial_number": serial,
                "loi_ban_dau": worksheet.cell(row_index, 3).value or "",
                "bo_phan": worksheet.cell(row_index, 4).value or "",
                "hang_muc_kiem_tra": worksheet.cell(row_index, 5).value or "",
                "ket_qua": "Đạt / 合格",
                "so_luong": worksheet.cell(row_index, 6).value,
                "don_gia": worksheet.cell(row_index, 7).value,
                "tong_gia": worksheet.cell(row_index, 8).value,
            }
        )

    if not items:
        raise ValueError("Bảng sửa chữa không có bản ghi thiết bị hợp lệ.")

    metadata = {
        "so_hop_dong": "",
        "ben_a": "",
        "ben_b": "",
        "ngay_nghiem_thu": _extract_source_date(workbook),
    }
    for row in worksheet.iter_rows():
        for cell in row:
            text = str(cell.value or "").strip()
            normalized = _normalized_text(text)
            if not metadata["so_hop_dong"] and ("số hợp đồng" in normalized or "合約編號" in text):
                metadata["so_hop_dong"] = _extract_labeled_value(text)
            if not metadata["ben_a"] and ("bên mua" in normalized or "甲方" in text):
                metadata["ben_a"] = _extract_labeled_value(text)
            if not metadata["ben_b"] and ("bên bán" in normalized or "乙方" in text):
                metadata["ben_b"] = _extract_labeled_value(text)

    workbook.close()
    metadata["items"] = items
    metadata["source_sheet"] = worksheet.title
    return metadata


def _sanitize_sheet_name(value: str) -> str:
    cleaned = re.sub(r'[\\/*?:\[\]]', "_", str(value)).strip()
    return cleaned[:31] or "Thiết bị"


def _unique_sheet_names(items: Sequence[Dict[str, Any]]) -> List[str]:
    used = {"Nghiệm Thu"}
    result: List[str] = []
    for index, item in enumerate(items, start=1):
        base = _sanitize_sheet_name(str(item["serial_number"]))
        candidate = base
        suffix = 2
        while candidate in used:
            suffix_text = f"_{suffix}"
            candidate = f"{base[:31 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        used.add(candidate)
        result.append(candidate)
    return result


def _copy_cell_style(source, target) -> None:
    target._style = copy(source._style)
    if source.has_style:
        target.font = copy(source.font)
        target.fill = copy(source.fill)
        target.border = copy(source.border)
        target.alignment = copy(source.alignment)
        target.protection = copy(source.protection)
        target.number_format = source.number_format


def _set_times_new_roman(cell) -> None:
    """Change only the font family while preserving size and other styling."""
    font = copy(cell.font)
    font.name = "Times New Roman"
    cell.font = font


def _safe_row_height(item: Dict[str, Any]) -> float:
    """Conservative anti-clipping height for Vietnamese and CJK text."""
    capacities = ((str(item.get("loi_ban_dau") or ""), 50), (str(item.get("hang_muc_kiem_tra") or ""), 44))
    needed_lines = 1
    for value, capacity in capacities:
        lines = 0
        for logical_line in value.splitlines() or [""]:
            visual_width = sum(2 if ord(char) > 127 else 1 for char in logical_line)
            lines += max(1, (visual_width + capacity - 1) // capacity)
        needed_lines = max(needed_lines, lines)
    return max(48.75, needed_lines * 17.0 + 10.0)


def _shift_range_rows(coordinate: str, delta: int) -> str:
    match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", coordinate)
    if not match:
        return coordinate
    col1, row1, col2, row2 = match.groups()
    return f"{col1}{int(row1) + delta}:{col2}{int(row2) + delta}"


def _replace_after_colon(original: Any, value: str) -> str:
    text = str(original or "")
    if not value:
        return text
    parts = re.split(r"([:：])", text, maxsplit=1)
    if len(parts) >= 3:
        return f"{parts[0]}{parts[1]} {value}"
    return value


def _update_summary_sheet(worksheet, source_data: Dict[str, Any], sheet_names: Sequence[str]) -> None:
    items = source_data["items"]
    note_label = _find_summary_note_cell(worksheet)
    old_note_header_row = note_label.row - 1
    data_start_row = 6
    old_data_row_count = old_note_header_row - data_start_row
    delta = len(items) - old_data_row_count

    # Capture the official alternating row styles before removing the template data.
    style_rows = []
    for template_row in (6, 7):
        style_rows.append([copy(worksheet.cell(template_row, col)._style) for col in range(1, 8)])

    footer_merges = []
    for merged_range in list(worksheet.merged_cells.ranges):
        if merged_range.min_row >= old_note_header_row:
            footer_merges.append(str(merged_range))
            worksheet.unmerge_cells(str(merged_range))
        elif merged_range.max_row >= data_start_row:
            worksheet.unmerge_cells(str(merged_range))

    footer_heights = {
        row: worksheet.row_dimensions[row].height
        for row in range(old_note_header_row, worksheet.max_row + 1)
        if worksheet.row_dimensions[row].height is not None
    }

    if delta > 0:
        worksheet.insert_rows(old_note_header_row, amount=delta)
    elif delta < 0:
        worksheet.delete_rows(old_note_header_row + delta, amount=-delta)

    new_note_header_row = old_note_header_row + delta
    for coordinate in footer_merges:
        worksheet.merge_cells(_shift_range_rows(coordinate, delta))
    for old_row, height in footer_heights.items():
        worksheet.row_dimensions[old_row + delta].height = height

    for row_index in range(data_start_row, new_note_header_row):
        for col in range(1, 8):
            cell = worksheet.cell(row_index, col)
            cell.value = None
            cell.hyperlink = None

    for offset, (item, sheet_name) in enumerate(zip(items, sheet_names)):
        row_index = data_start_row + offset
        style_index = offset % 2
        for col in range(1, 8):
            worksheet.cell(row_index, col)._style = copy(style_rows[style_index][col - 1])
        values = [
            item["stt"],
            item["serial_number"],
            item["loi_ban_dau"],
            item["bo_phan"],
            item["hang_muc_kiem_tra"],
            item["ket_qua"],
            f"→ {sheet_name}",
        ]
        for col, value in enumerate(values, start=1):
            worksheet.cell(row_index, col).value = value
        worksheet.cell(row_index, 7).hyperlink = f"#'{sheet_name}'!A1"
        worksheet.row_dimensions[row_index].height = _safe_row_height(item)

    if source_data.get("so_hop_dong"):
        worksheet["A3"].value = _replace_after_colon(worksheet["A3"].value, source_data["so_hop_dong"])
    else:
        worksheet["A3"].value = "Số HĐ / 合約編號: ---"
    if source_data.get("ngay_nghiem_thu"):
        original = str(worksheet["E3"].value or "")
        worksheet["E3"].value = re.sub(
            r"(?<=Ngày / 日期:)\s*[^\s]+",
            f" {source_data['ngay_nghiem_thu']}",
            original,
            count=1,
        )
    if source_data.get("ben_a"):
        worksheet["A4"].value = _replace_after_colon(worksheet["A4"].value, source_data["ben_a"])
    if source_data.get("ben_b"):
        worksheet["E4"].value = _replace_after_colon(worksheet["E4"].value, source_data["ben_b"])

    # Keep the template's page-view settings and extend only the print height.
    print_area = str(worksheet.print_area or "")
    end_match = re.search(r"\$G\$(\d+)", print_area)
    if end_match:
        new_end = max(int(end_match.group(1)) + delta, new_note_header_row + 11)
        worksheet.print_area = f"A1:G{new_end}"

    # Update party name inside the shifted signature cells without touching styles.
    signature_row = new_note_header_row + 3
    if source_data.get("ben_a") and worksheet.cell(signature_row, 1).value:
        lines = str(worksheet.cell(signature_row, 1).value).splitlines()
        lines[-1] = source_data["ben_a"]
        worksheet.cell(signature_row, 1).value = "\n".join(lines)
    if source_data.get("ben_b") and worksheet.cell(signature_row, 5).value:
        lines = str(worksheet.cell(signature_row, 5).value).splitlines()
        lines[-1] = source_data["ben_b"]
        worksheet.cell(signature_row, 5).value = "\n".join(lines)


def _populate_detail_sheet(worksheet, item: Dict[str, Any], sheet_name: str) -> None:
    serial = str(item["serial_number"])
    max_col = worksheet.max_column
    note_col = max_col
    worksheet.cell(1, 1).value = f"HÌNH ẢNH KIỂM TRA / 檢查圖片 — {serial}"
    department = str(item.get("bo_phan") or "").replace("\n", " / ")
    result = str(item.get("ket_qua") or "Đạt / 合格").replace("\n", " / ")
    worksheet.cell(2, 1).value = (
        f"STT: {item['stt']}    |    Bộ phận / 部門: {department}    |    Kết quả / 結果: {result}"
    )
    initial_issue = str(item.get("loi_ban_dau") or "").replace("\n", " / ")
    inspection = str(item.get("hang_muc_kiem_tra") or "").replace("\n", " / ")
    worksheet.cell(3, 1).value = f"Lỗi ban đầu / 故障說明: {initial_issue}"
    worksheet.cell(4, 1).value = f"Hạng mục KT / 檢查項目: {inspection}"
    worksheet.cell(6, note_col).value = None
    _set_times_new_roman(worksheet.cell(6, note_col))
    worksheet.cell(8, 1).hyperlink = "#'Nghiệm Thu'!A1"


def synchronize_acceptance_from_source(
    source_path: Path,
    target_path: Path,
    override_contract_code: Optional[str] = None,
    override_customer_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Rebuild the template's device data and detail sheets from the upload."""
    source_data = extract_source_data(source_path)
    if override_contract_code is not None:
        source_data["so_hop_dong"] = override_contract_code
    if override_customer_name is not None:
        source_data["ben_a"] = override_customer_name
    items = source_data["items"]
    sheet_names = _unique_sheet_names(items)

    workbook = load_workbook(target_path, data_only=False, read_only=False)
    summary_sheet = _find_summary_sheet(workbook)
    original_details = [ws for ws in workbook.worksheets if ws.title != summary_sheet.title]
    if not original_details:
        raise ValueError("Mẫu nghiệm thu không có sheet chi tiết thiết bị để nhân bản.")

    rf_template = next((ws for ws in original_details if ws.max_column == 4), None)
    ef_template = next((ws for ws in original_details if ws.max_column == 6 and ws.max_row == 8), None)
    if rf_template is None or ef_template is None:
        raise ValueError("Mẫu nghiệm thu thiếu sheet chuẩn RF hoặc EF.")

    new_details = []
    for index, (item, final_name) in enumerate(zip(items, sheet_names), start=1):
        serial = str(item["serial_number"]).upper()
        template = rf_template if serial.startswith("RF") else ef_template
        worksheet = workbook.copy_worksheet(template)
        worksheet.title = f"TMP_{index:03d}"
        new_details.append((worksheet, item, final_name))

    for worksheet in original_details:
        workbook.remove(worksheet)

    for worksheet, item, final_name in new_details:
        worksheet.title = final_name
        _populate_detail_sheet(worksheet, item, final_name)

    _update_summary_sheet(summary_sheet, source_data, sheet_names)
    saved_path = _safe_save(workbook, target_path)
    source_data["saved_path"] = str(saved_path)
    source_data["detail_sheet_names"] = sheet_names
    return source_data


def generate(
    source_path: Path,
    target_path: Path,
    workspace: Path,
    override_contract_code: Optional[str] = None,
    override_customer_name: Optional[str] = None,
) -> Dict[str, Any]:
    source_data = synchronize_acceptance_from_source(
        source_path,
        target_path,
        override_contract_code=override_contract_code,
        override_customer_name=override_customer_name,
    )
    note_text, source_sheet, source_label_cell = extract_source_note(source_path)

    workbook = load_workbook(target_path, data_only=False, read_only=False)
    summary_sheet = _find_summary_sheet(workbook)
    detail_cells: Dict[str, Any] = {}
    for worksheet in workbook.worksheets:
        if worksheet.title == summary_sheet.title:
            continue
        note_cell = _find_detail_note_cell(worksheet)
        if note_cell is not None:
            detail_cells[worksheet.title] = note_cell

    if not detail_cells:
        raise ValueError("File nghiệm thu không có sheet sản phẩm với cột Ghi chú / 備註.")

    gemini_data, model_name = _call_gemini(
        note_text=note_text,
        valid_sheets=list(detail_cells),
        workspace=workspace,
    )
    assignments = validate_assignments(gemini_data, note_text, list(detail_cells))

    # Bỏ hoàn toàn ghi chú cũ trong file nghiệm thu trước khi gán dữ liệu nguồn.
    for cell in detail_cells.values():
        cell.value = None
        _set_times_new_roman(cell)

    # Vùng ghi chú tổng hợp cũng lấy từ file sửa chữa, không giữ dữ liệu cũ.
    summary_note_cell = _find_summary_note_cell(summary_sheet)
    summary_note_cell.value = note_text or None
    _ensure_summary_note_height(summary_sheet, summary_note_cell, note_text)

    for sheet_name, note in assignments.items():
        detail_cells[sheet_name].value = note

    saved_path = _safe_save(workbook, target_path)
    return {
        "source_path": str(source_path),
        "source_sheet": source_sheet,
        "source_label_cell": source_label_cell,
        "target_path": str(target_path),
        "saved_path": str(saved_path),
        "gemini_model": model_name,
        "note_text": note_text,
        "assignments": assignments,
        "blank_detail_sheets": sorted(set(detail_cells) - set(assignments)),
        "record_count": len(source_data["items"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dùng Gemini phân tích ghi chú sửa chữa và điền đúng sheet nghiệm thu."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--workspace", type=Path, default=Path(r"E:\Working"))
    parser.add_argument(
        "--result-json",
        type=Path,
        help="Tùy chọn lưu báo cáo kết quả JSON để kiểm tra/audit.",
    )
    return parser


def main() -> int:
    _configure_stdout()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()
    result = generate(args.source, args.target, args.workspace)
    if args.result_json:
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        args.result_json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
