# -*- coding: utf-8 -*-
"""Service tạo và xuất file Excel Đơn Xin Thanh Toán (浤詺付款申请单) chuẩn 1:1."""

import logging
import math
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import openpyxl

from app.config import WORKING_DIR
from app.database import get_db_connection
from app.services.beneficiary_service import record_beneficiary_usage
from app.services.reminder_service import (
    format_amount_display,
    number_to_chinese_words,
    number_to_vietnamese_words,
)
from app.utils.currency_helper import parse_positive_integer

logger = logging.getLogger(__name__)

TEMPLATE_MASTER = WORKING_DIR / "Bieu Mau" / "DON_XIN_THANH_TOAN_TEMPLATE.xlsx"
FALLBACK_TEMPLATE = WORKING_DIR / "Bieu Mau" / "ĐƠN XIN THANH TOÁN.xlsx"
OUTPUT_DIR = WORKING_DIR / "Ho So Du An" / "Don Xin Thanh Toan"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự không hợp lệ trong tên file Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", str(name or "")).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean[:80] or "Phieu_Thanh_Toan"


def _calculate_row_height(text: str, col_width: float = 43.0, min_height: float = 110.0) -> float:
    """Tính toán chiều cao hàng chống cắt chữ (Anti-clipping) cho ô lý do thanh toán F6."""
    if not text:
        return min_height
    lines = text.split("\n")
    total_visual_lines = 0
    for line in lines:
        line_len = 0
        for char in line:
            # Ký tự CJK / tiếng Trung / dấu tiếng Việt tính 1.8 đơn vị
            if ord(char) > 127:
                line_len += 1.8
            else:
                line_len += 1.0
        visual_lines = max(1, math.ceil(line_len / col_width))
        total_visual_lines += visual_lines

    calculated = float(total_visual_lines * 22.0 + 15.0)
    return max(min_height, min(calculated, 350.0))


def _attach_signature(ws, signer_name: str) -> None:
    """Chèn ảnh chữ ký vào ô G14 (制单 / Prepared by) chuẩn tọa độ theo mẫu GBL1."""
    try:
        norm = str(signer_name or "").upper()
        if "BANG" in norm or "BẰNG" in norm:
            sig_file = WORKING_DIR / "pm_portal" / "app" / "static" / "img" / "signatures" / "signature_bang.png"
            if not sig_file.exists():
                sig_file = WORKING_DIR / "Bieu Mau" / "signatures" / "signature_bang.png"
            if not sig_file.exists():
                return

            # Nếu ws đã có ảnh trong _images thì không chèn trùng lặp
            if getattr(ws, "_images", None) and len(ws._images) > 0:
                return

            from openpyxl.drawing.image import Image
            from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
            from openpyxl.drawing.xdr import XDRPositiveSize2D

            # Tọa độ chuẩn 1:1 trích xuất từ sheet GBL1 mẫu gốc:
            # col: 6 (cột G), colOff: 547034, row: 13 (hàng 14), rowOff: 358588
            # kích thước: cx: 665250, cy: 466161 (tương đương 70pt x 49pt)
            _from = AnchorMarker(col=6, colOff=547034, row=13, rowOff=358588)
            img = Image(str(sig_file))
            img.anchor = OneCellAnchor(_from=_from, ext=XDRPositiveSize2D(665250, 466161))
            ws.add_image(img)
    except Exception as exc:
        logger.warning("Không thể chèn ảnh chữ ký vào file Excel: %s", exc)


def get_next_report_code(
    employee_code: str = "HVM007",
    target_date: Optional[Union[str, datetime, date]] = None
) -> Dict[str, Any]:
    """
    Sinh mã số báo đơn tiếp theo theo định dạng:
    报单号：{mã_nhân_viên}-{YYYYMMDD}-{số_thứ_tự_trong_ngày}

    Quy tắc:
    - employee_code: Mã nhân viên (mặc định HVM007 - NGUYỄN SỸ KIM BẰNG).
    - target_date: Ngày lập đơn (YYYY-MM-DD, dd/mm/yyyy hoặc datetime/date).
    - seq: Số thứ tự bản trong ngày (tự động đếm các bản đã làm trong ngày đó + 1).
      Ví dụ ngày đó đã làm 2 bản rồi thì bản tiếp theo là 3 (HVM007-20261020-3).
    """
    emp = re.sub(r"[^A-Za-z0-9]", "", str(employee_code or "HVM007")).upper() or "HVM007"

    date_obj = None
    if isinstance(target_date, (datetime, date)):
        date_obj = target_date
    elif target_date:
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                date_obj = datetime.strptime(str(target_date).strip(), fmt)
                break
            except Exception:
                pass
    if not date_obj:
        date_obj = datetime.now()

    date_str = date_obj.strftime("%Y%m%d")
    date_formatted = date_obj.strftime("%Y-%m-%d")

    # 1. Quét trong database các bản ghi đã lập
    existing_seqs = set()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        rows = cursor.execute("SELECT report_code FROM payment_voucher_requests").fetchall()
        conn.close()

        pattern = re.compile(rf"{re.escape(emp)}[-_]{date_str}[-_](\d+)", re.IGNORECASE)
        for r in rows:
            val = str(r["report_code"] or "")
            m = pattern.search(val)
            if m:
                existing_seqs.add(int(m.group(1)))
    except Exception as exc:
        logger.warning("Could not query database for report code sequences: %s", exc)

    # 2. Quét thêm thư mục lưu trữ file Excel để đảm bảo không trùng số đã xuất
    try:
        if OUTPUT_DIR.exists():
            pattern = re.compile(rf"{re.escape(emp)}[-_]{date_str}[-_](\d+)", re.IGNORECASE)
            for f in OUTPUT_DIR.glob("*.xlsx"):
                m = pattern.search(f.name)
                if m:
                    existing_seqs.add(int(m.group(1)))
    except Exception as exc:
        logger.warning("Could not scan output dir for report code sequences: %s", exc)

    max_seq = max(existing_seqs) if existing_seqs else 0
    next_seq = max_seq + 1

    code_only = f"{emp}-{date_str}-{next_seq}"
    full_code = f"报单号：{code_only}"

    return {
        "employee_code": emp,
        "date": date_formatted,
        "date_str": date_str,
        "seq": next_seq,
        "code": code_only,
        "full_code": full_code
    }


def generate_payment_voucher_excel(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tạo file Excel Đơn xin thanh toán 1:1 theo mẫu gốc.
    """
    # 1. Chuẩn bị dữ liệu
    beneficiary_name = str(payload.get("beneficiary_name") or "").strip()
    if not beneficiary_name:
        raise ValueError("Tên đơn vị thụ hưởng không được để trống.")

    account_number = str(payload.get("account_number") or "").strip()
    bank_name = str(payload.get("bank_name") or "").strip()

    raw_amount = payload.get("amount")
    amount = parse_positive_integer(raw_amount) if raw_amount else 0
    currency = str(payload.get("currency") or "VND").upper().strip()

    exchange_rate = float(payload.get("exchange_rate") or 26000)
    if exchange_rate <= 0:
        exchange_rate = 26000.0

    reason_vi = str(payload.get("reason_vi") or "").strip()
    reason_zh = str(payload.get("reason_zh") or "").strip()
    full_reason = str(payload.get("full_reason") or "").strip()
    if not full_reason:
        if reason_vi and reason_zh:
            full_reason = f"{reason_vi}\n{reason_zh}"
        elif reason_vi:
            full_reason = reason_vi
        elif reason_zh:
            full_reason = reason_zh
        else:
            full_reason = "Thanh toán theo hợp đồng và hóa đơn đính kèm."

    employee_code = str(payload.get("employee_code") or "HVM007").strip()

    # Xử lý ngày lập đơn trước để tính mã báo đơn chính xác
    request_date_raw = str(payload.get("request_date") or "").strip()
    req_date_obj = None
    if request_date_raw:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                req_date_obj = datetime.strptime(request_date_raw, fmt)
                break
            except Exception:
                pass
    if not req_date_obj:
        req_date_obj = datetime.now()

    # Xử lý Mã báo đơn theo quy tắc: {mã_NV}-{YYYYMMDD}-{seq}
    report_code = str(payload.get("report_code") or "").strip()
    if not report_code or "HMV002-" in report_code:
        # Nếu chưa có hoặc còn mã mẫu HMV002 cũ -> tự động sinh theo ngày và mã nhân viên
        next_info = get_next_report_code(employee_code=employee_code, target_date=req_date_obj)
        report_code = next_info["code"]
        full_report_code = next_info["full_code"]
    else:
        if not report_code.startswith("报单号：") and not report_code.startswith("报单"):
            full_report_code = f"报单号：{report_code}"
        else:
            full_report_code = report_code
        # Lưu lại report_code chuẩn (bỏ tiền tố 报单号：)
        report_code = full_report_code.replace("报单号：", "").replace("报单号:", "").strip()

    prepared_by = str(payload.get("prepared_by") or "NGUYỄN SỸ KIM BẰNG").strip()
    supervisor = str(payload.get("supervisor") or "").strip()
    checker = str(payload.get("checker") or "").strip()
    accountant = str(payload.get("accountant") or "").strip()
    director = str(payload.get("director") or "").strip()
    attachment_note = str(payload.get("attachment_note") or "").strip()

    # 2. Mở file template
    if TEMPLATE_MASTER.exists():
        wb = openpyxl.load_workbook(str(TEMPLATE_MASTER))
        ws = wb.active
    elif FALLBACK_TEMPLATE.exists():
        wb = openpyxl.load_workbook(str(FALLBACK_TEMPLATE))
        ws = wb["FINEPRO"] if "FINEPRO" in wb.sheetnames else wb.active
    else:
        raise FileNotFoundError(f"Không tìm thấy file mẫu tại {TEMPLATE_MASTER} hoặc {FALLBACK_TEMPLATE}")

    # Đổi tên sheet hiển thị thân thiện
    sheet_title = _sanitize_filename(payload.get("beneficiary_short_name") or beneficiary_name)[:30]
    try:
        ws.title = sheet_title
    except Exception:
        ws.title = "ĐƠN XIN THANH TOÁN"

    # 3. Điền các ô dữ liệu chính xác theo layout gốc
    # A4: Ngày lập phiếu - Mẫu gốc chuẩn 1:1 sử dụng công thức sống =TODAY() định dạng mm-dd-yy
    today_str = datetime.now().strftime("%Y-%m-%d")
    is_today = (not request_date_raw) or (req_date_obj and req_date_obj.strftime("%Y-%m-%d") == today_str)

    if is_today:
        ws["A4"].value = "=TODAY()"
        ws["A4"].number_format = "mm-dd-yy"
    else:
        ws["A4"].value = req_date_obj
        ws["A4"].number_format = "mm-dd-yy"

    # F4: Mã báo đơn
    ws["F4"].value = full_report_code

    # B5: Đơn vị thụ hưởng
    ws["B5"].value = beneficiary_name

    # B6: Số tài khoản ngân hàng
    ws["B6"].value = account_number

    # B7: Ngân hàng mở tài khoản
    ws["B7"].value = bank_name

    # F6: Nội dung lý do thanh toán song ngữ
    ws["F6"].value = full_reason

    # G7 & F8:H11 - Xử lý trường hợp có nhiều dòng con (Breakdown Items như mẫu THÁI SƠN)
    breakdown_items = payload.get("breakdown_items") or []
    valid_items = [it for it in breakdown_items if (it.get("desc") or it.get("amount"))] if isinstance(breakdown_items, list) else []

    if valid_items:
        total_sub_amt = 0
        for idx in range(4):
            r_idx = 8 + idx
            if idx < len(valid_items):
                item = valid_items[idx]
                desc_text = str(item.get("desc") or "").strip()
                sub_val = parse_positive_integer(item.get("amount")) if item.get("amount") else 0
                total_sub_amt += sub_val

                ws[f"F{r_idx}"].value = desc_text
                ws[f"G{r_idx}"].value = sub_val
                ws[f"G{r_idx}"].number_format = '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-'
                ws[f"H{r_idx}"].value = currency
            else:
                ws[f"F{r_idx}"].value = None
                ws[f"G{r_idx}"].value = None
                ws[f"H{r_idx}"].value = None

        # G7: Công thức tính tổng tự động từ các dòng con =SUM(G8:G...) y hệt mẫu THÁI SƠN
        end_r = 7 + len(valid_items[:4])
        ws["G7"].value = f"=SUM(G8:G{end_r})"
        ws["G7"].number_format = '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-'
        ws["H7"].value = currency
        amount = total_sub_amt
    else:
        # Phiếu đơn thông thường: dọn sạch F8:G11 và điền thẳng số tiền vào G7
        for r_idx in range(8, 12):
            ws[f"F{r_idx}"].value = None
            ws[f"G{r_idx}"].value = None
        ws["G7"].value = amount
        ws["G7"].number_format = '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-'
        ws["H7"].value = currency

    # B8: Công thức số tiền bằng chữ tiếng Trung qua DBNum2
    ws["B8"].value = "=D12"
    ws["B8"].number_format = "[DBNum2][$-404]General"

    # D12: Số tiền tham chiếu từ G7
    ws["D12"].value = "=G7"
    ws["D12"].number_format = '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-'
    ws["E12"].value = currency

    # D13: Quy đổi USD
    ws["D13"].value = f"=+D12/{int(exchange_rate)}"
    ws["D13"].number_format = '_-* #,##0_-;\\-* #,##0_-;_-* "-"??_-;_-@_-'
    ws["E13"].value = "USD"

    # G14: Chữ ký người lập phiếu
    ws["G14"].value = f"制单\nPrepared by\n\n\n\n{prepared_by}"
    _attach_signature(ws, prepared_by)

    if supervisor:
        ws["F14"].value = f"单位主管\nSupervisor\n\n\n\n{supervisor}"
    if checker:
        ws["D14"].value = f"审核\nChecker\n\n\n\n{checker}"
    if accountant:
        ws["B14"].value = f"会计\nAccountant\n\n\n\n{accountant}"
    if director:
        ws["A14"].value = f"经理\nDirector\n\n\n\n{director}"

    if attachment_note:
        ws["B12"].value = attachment_note

    # 4. Tự động căn chỉnh chiều cao hàng 6 chống cắt chữ
    ws.row_dimensions[6].height = _calculate_row_height(full_reason)

    # 5. Cấu hình Page Layout & Chế độ xem Page Break Preview xung quanh bảng dữ liệu
    ws.sheet_view.view = "pageBreakPreview"
    ws.sheet_view.showGridLines = None  # Giữ xám ngoài trang, không loang lưới trắng
    ws.sheet_view.zoomScale = 100
    ws.sheet_view.zoomScaleNormal = 100
    ws.sheet_view.zoomScaleSheetLayoutView = 100

    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.print_area = f"'{ws.title}'!$A$1:$I$14"

    # 6. Lưu file an toàn
    clean_code = _sanitize_filename(report_code.replace("报单号：", "").replace("报单号", "").replace("报单", ""))
    clean_ben = _sanitize_filename(beneficiary_name)
    base_file_name = f"Don_Xin_Thanh_Toan_{clean_code}_{clean_ben}.xlsx"
    target_path = OUTPUT_DIR / base_file_name

    saved_path = None
    for attempt in range(1, 10):
        try:
            wb.save(str(target_path))
            saved_path = target_path
            break
        except PermissionError:
            target_path = OUTPUT_DIR / f"Don_Xin_Thanh_Toan_{clean_code}_{clean_ben}_v{attempt + 1}.xlsx"
        except Exception as exc:
            logger.error("Error saving payment voucher excel: %s", exc)
            raise exc

    if not saved_path:
        raise IOError("Không thể lưu file Excel do file đang bị khóa bởi tiến trình khác.")

    # 6. Ghi nhận lượt sử dụng vào danh bạ tài khoản thụ hưởng
    try:
        record_beneficiary_usage(beneficiary_name, account_number, bank_name)
    except Exception as exc:
        logger.warning("Could not record beneficiary usage: %s", exc)

    # 7. Lưu phiếu vào lịch sử database
    words_vi = number_to_vietnamese_words(amount)
    words_zh = number_to_chinese_words(amount)
    amount_usd = round(amount / exchange_rate, 2) if amount > 0 else 0.0

    record_id = _save_voucher_to_db(
        report_code=report_code,
        request_date=req_date_obj.strftime("%Y-%m-%d"),
        beneficiary_name=beneficiary_name,
        account_number=account_number,
        bank_name=bank_name,
        reason_vi=reason_vi,
        reason_zh=reason_zh,
        full_reason=full_reason,
        amount=amount,
        currency=currency,
        amount_usd=amount_usd,
        exchange_rate=exchange_rate,
        amount_in_words_vi=words_vi,
        amount_in_words_zh=words_zh,
        prepared_by=prepared_by,
        supervisor=supervisor,
        checker=checker,
        accountant=accountant,
        director=director,
        attachment_note=attachment_note,
        file_path=str(saved_path),
        file_name=saved_path.name
    )

    return {
        "status": "success",
        "voucher_id": record_id,
        "file_name": saved_path.name,
        "file_path": str(saved_path),
        "download_url": f"/api/v1/payment-requests/download/{saved_path.name}",
        "report_code": report_code,
        "beneficiary_name": beneficiary_name,
        "account_number": account_number,
        "bank_name": bank_name,
        "amount": amount,
        "amount_formatted": format_amount_display(amount),
        "amount_in_words_vi": words_vi,
        "amount_in_words_zh": words_zh,
        "amount_usd": amount_usd,
        "exchange_rate": exchange_rate,
        "currency": currency,
        "request_date": req_date_obj.strftime("%Y-%m-%d"),
        "full_reason": full_reason,
        "prepared_by": prepared_by,
        "next_report_code": get_next_report_code(employee_code=employee_code, target_date=req_date_obj)["full_code"]
    }


def _save_voucher_to_db(**kwargs) -> int:
    """Lưu thông tin phiếu đơn xin thanh toán vào cơ sở dữ liệu SQLite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO payment_voucher_requests 
            (report_code, request_date, beneficiary_name, account_number, bank_name, 
             reason_vi, reason_zh, full_reason, amount, currency, amount_usd, exchange_rate, 
             amount_in_words_vi, amount_in_words_zh, prepared_by, supervisor, checker, accountant, 
             director, attachment_note, file_path, file_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kwargs.get("report_code", ""),
                kwargs.get("request_date", ""),
                kwargs.get("beneficiary_name", ""),
                kwargs.get("account_number", ""),
                kwargs.get("bank_name", ""),
                kwargs.get("reason_vi", ""),
                kwargs.get("reason_zh", ""),
                kwargs.get("full_reason", ""),
                kwargs.get("amount", 0),
                kwargs.get("currency", "VND"),
                kwargs.get("amount_usd", 0.0),
                kwargs.get("exchange_rate", 26000),
                kwargs.get("amount_in_words_vi", ""),
                kwargs.get("amount_in_words_zh", ""),
                kwargs.get("prepared_by", "NGUYỄN SỸ KIM BẰNG"),
                kwargs.get("supervisor", ""),
                kwargs.get("checker", ""),
                kwargs.get("accountant", ""),
                kwargs.get("director", ""),
                kwargs.get("attachment_note", ""),
                kwargs.get("file_path", ""),
                kwargs.get("file_name", "")
            )
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as exc:
        logger.error("Error saving voucher to database: %s", exc)
        return 0
    finally:
        conn.close()


def list_voucher_history(search: Optional[str] = None, limit: int = 100) -> list:
    """Lấy danh sách các đơn xin thanh toán đã tạo, hỗ trợ tìm kiếm tra cứu theo mã báo đơn, đơn vị thụ hưởng, lý do..."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if search and search.strip():
            kw = f"%{search.strip().lower()}%"
            cursor.execute(
                """
                SELECT * FROM payment_voucher_requests
                WHERE LOWER(report_code) LIKE ?
                   OR LOWER(beneficiary_name) LIKE ?
                   OR LOWER(account_number) LIKE ?
                   OR LOWER(bank_name) LIKE ?
                   OR LOWER(full_reason) LIKE ?
                   OR LOWER(request_date) LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (kw, kw, kw, kw, kw, kw, limit)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM payment_voucher_requests
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            amt = int(round(float(r.get("amount") or 0)))
            r["amount_formatted"] = format_amount_display(amt)
            if r.get("file_name"):
                r["download_url"] = f"/api/v1/payment-requests/download/{r['file_name']}"
        return rows
    except Exception as exc:
        logger.error("Error listing voucher history: %s", exc)
        return []
    finally:
        conn.close()


def delete_voucher_history(voucher_id: int) -> bool:
    """Xóa một bản ghi đơn xin thanh toán khỏi lịch sử và xóa luôn file Excel vật lý tương ứng trên ổ đĩa."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 1. Lấy thông tin đường dẫn file vật lý trước khi xóa
        cursor.execute("SELECT file_path, file_name FROM payment_voucher_requests WHERE id = ?", (voucher_id,))
        row = cursor.fetchone()

        # 2. Xóa bản ghi trong cơ sở dữ liệu
        cursor.execute("DELETE FROM payment_voucher_requests WHERE id = ?", (voucher_id,))
        conn.commit()
        deleted = cursor.rowcount > 0

        # 3. Xóa file Excel vật lý trên ổ đĩa nếu có
        if deleted and row:
            f_path = row["file_path"] if isinstance(row, dict) else row[0]
            f_name = row["file_name"] if isinstance(row, dict) else row[1]
            candidates = set()
            if f_path:
                candidates.add(Path(f_path))
            if f_name:
                candidates.add(OUTPUT_DIR / f_name)

            for target in candidates:
                try:
                    if target and target.exists() and target.is_file():
                        target.unlink()
                        logger.info("Đã xóa file Excel vật lý tương ứng: %s", target)
                except Exception as file_err:
                    logger.warning("Không thể xóa file vật lý %s: %s", target, file_err)

        return deleted
    except Exception as exc:
        logger.error("Error deleting voucher %s: %s", voucher_id, exc)
        return False
    finally:
        conn.close()
