# -*- coding: utf-8 -*-
"""Service quản lý Danh bạ tài khoản thụ hưởng (Beneficiaries Directory)."""

import logging
import re
import sqlite3
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database import get_db_connection

logger = logging.getLogger(__name__)


def list_beneficiaries(search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lấy danh sách các tài khoản thụ hưởng, hỗ trợ tìm kiếm và sắp xếp theo tần suất sử dụng."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if search and search.strip():
            kw = f"%{search.strip().lower()}%"
            cursor.execute(
                """
                SELECT id, unit_name, account_number, bank_name, short_name, 
                       default_reason, swift_code, currency, usage_count, last_used_at, created_at
                FROM beneficiaries
                WHERE LOWER(unit_name) LIKE ? 
                   OR LOWER(account_number) LIKE ? 
                   OR LOWER(bank_name) LIKE ? 
                   OR LOWER(COALESCE(short_name, '')) LIKE ?
                ORDER BY usage_count DESC, unit_name ASC
                LIMIT ?
                """,
                (kw, kw, kw, kw, limit)
            )
        else:
            cursor.execute(
                """
                SELECT id, unit_name, account_number, bank_name, short_name, 
                       default_reason, swift_code, currency, usage_count, last_used_at, created_at
                FROM beneficiaries
                ORDER BY usage_count DESC, unit_name ASC
                LIMIT ?
                """,
                (limit,)
            )
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except Exception as exc:
        logger.error("Error listing beneficiaries: %s", exc)
        return []
    finally:
        conn.close()


def get_beneficiary_by_id(beneficiary_id: int) -> Optional[Dict[str, Any]]:
    """Lấy thông tin 1 đơn vị thụ hưởng theo ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM beneficiaries WHERE id = ?", (beneficiary_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("Error fetching beneficiary %s: %s", beneficiary_id, exc)
        return None
    finally:
        conn.close()


def get_beneficiary_by_name(unit_name: str) -> Optional[Dict[str, Any]]:
    """Tìm chính xác theo tên đơn vị thụ hưởng."""
    if not unit_name or not unit_name.strip():
        return None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM beneficiaries WHERE LOWER(unit_name) = ? OR LOWER(short_name) = ?",
            (unit_name.strip().lower(), unit_name.strip().lower())
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("Error finding beneficiary by name %s: %s", unit_name, exc)
        return None
    finally:
        conn.close()


def _normalize_business_text(s: str) -> str:
    """Chuẩn hóa tên doanh nghiệp: loại bỏ dấu tiếng Việt, đưa về chữ thường và chuẩn hóa khoảng trắng."""
    if not s:
        return ""
    import unicodedata
    s = s.replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _get_business_core_tokens(norm_text: str) -> set:
    """Trích xuất tập các từ khóa cốt lõi, loại bỏ các từ tiền tố/hậu tố pháp nhân thông thường."""
    common_business_words = {
        "cong", "ty", "cty", "tnhh", "mtv", "co", "phan", "cp", "tm", "dv", 
        "sx", "xnk", "thuong", "mai", "dich", "vu", "san", "xuat", "viet", 
        "nam", "vn", "ltd", "corp", "corporation", "inc"
    }
    tokens = [w for w in norm_text.split() if len(w) >= 2]
    core_tokens = [w for w in tokens if w not in common_business_words]
    return set(core_tokens) if core_tokens else set(tokens)


def find_matching_beneficiary(text: str) -> Optional[Dict[str, Any]]:
    """
    Tìm kiếm thông minh đa cấp độ (Multi-tier Smart Matching):
    Không cần khớp đúng 100% tên, tự động nhận diện cả khi viết tắt, không dấu, hoặc thiếu tiền tố.
    
    Cấp 1: Khớp chính xác (Exact match) tên hoặc tên viết tắt (short_name).
    Cấp 2: Khớp không dấu (Normalized match) cả 2 chiều.
    Cấp 3: Khớp tên gợi nhớ / viết tắt (ví dụ: 'OMG', 'CX', 'THÁI SƠN', 'GLOBAL LINK').
    Cấp 4: Khớp bao hàm 2 chiều (Bi-directional Substring Matching) phần tên lõi.
    Cấp 5: Khớp tập từ khóa đặc trưng (Token Overlap Match).
    """
    if not text or not text.strip():
        return None

    raw_text = text.strip()
    norm_input = _normalize_business_text(raw_text)
    input_tokens = _get_business_core_tokens(norm_input)
    all_bens = list_beneficiaries(limit=200)

    # 1. Khớp chính xác hoặc khớp không dấu trực tiếp
    for b in all_bens:
        uname = b["unit_name"].strip()
        sname = (b.get("short_name") or "").strip()
        norm_u = _normalize_business_text(uname)
        norm_s = _normalize_business_text(sname)

        if raw_text.lower() == uname.lower() or (sname and raw_text.lower() == sname.lower()):
            return b
        if norm_input == norm_u or (norm_s and norm_input == norm_s):
            return b

    # 2. Khớp theo tên gợi nhớ / viết tắt (short_name) có ranh giới từ
    for b in all_bens:
        sname = (b.get("short_name") or "").strip()
        if sname and len(sname) >= 2:
            norm_s = _normalize_business_text(sname)
            # Kiểm tra xem từ viết tắt có nằm trong chuỗi đầu vào hay không
            pattern = rf"\b{re.escape(norm_s)}\b"
            if re.search(pattern, norm_input):
                return b

    # 3. Khớp bao hàm 2 chiều phần tên lõi (Sub-string match)
    for b in all_bens:
        norm_u = _normalize_business_text(b["unit_name"])
        # Cắt bỏ các tiền tố doanh nghiệp phổ biến
        core_u = norm_u
        for prefix in [
            "cong ty tnhh mtv", "cong ty tnhh tm dv sx", "cong ty tnhh tm dv",
            "cong ty tnhh", "cty tnhh tm", "cty tnhh", "cong ty co phan",
            "cty co phan", "cong ty cp", "cty cp", "cong ty", "cty"
        ]:
            if core_u.startswith(prefix):
                core_u = core_u[len(prefix):].strip()
                break

        core_in = norm_input
        for prefix in [
            "cong ty tnhh mtv", "cong ty tnhh tm dv sx", "cong ty tnhh tm dv",
            "cong ty tnhh", "cty tnhh tm", "cty tnhh", "cong ty co phan",
            "cty co phan", "cong ty cp", "cty cp", "cong ty", "cty"
        ]:
            if core_in.startswith(prefix):
                core_in = core_in[len(prefix):].strip()
                break

        # Nếu phần tên cốt lõi của bên này nằm trong bên kia và độ dài đủ an toàn (>= 4 ký tự)
        if len(core_u) >= 4 and (core_u in core_in or core_u in norm_input):
            return b
        if len(core_in) >= 4 and (core_in in core_u or core_in in norm_u):
            return b

    # 4. Khớp tập từ khóa đặc trưng (Token Overlap)
    if input_tokens:
        best_candidate = None
        best_score = 0.0

        for b in all_bens:
            norm_u = _normalize_business_text(b["unit_name"])
            db_tokens = _get_business_core_tokens(norm_u)

            if not db_tokens:
                continue

            intersection = input_tokens.intersection(db_tokens)
            if not intersection:
                continue

            # Điểm trùng khớp: tỉ lệ từ khóa cốt lõi trùng nhau
            overlap_score = len(intersection) / min(len(input_tokens), len(db_tokens))

            # Nếu tất cả từ cốt lõi của 1 bên đều xuất hiện ở bên kia (ví dụ 'thai son' nằm trọn trong 'phat trien cong nghe thai son')
            if input_tokens.issubset(db_tokens) or db_tokens.issubset(input_tokens):
                return b

            # Nếu có từ khóa thương hiệu đặc trưng trùng nhau (ví dụ: 'omg', 'finepro', 'avantech')
            distinctive_tokens = {w for w in intersection if len(w) >= 3 and w not in {"cong", "nghe", "phat", "trien", "dich", "thuong", "quoc"}}
            if distinctive_tokens and overlap_score >= 0.5:
                return b

            if overlap_score > best_score and overlap_score >= 0.6:
                best_score = overlap_score
                best_candidate = b

        if best_candidate:
            return best_candidate

    return None


def upsert_beneficiary(
    unit_name: str,
    account_number: str,
    bank_name: str,
    short_name: Optional[str] = None,
    default_reason: Optional[str] = None,
    swift_code: Optional[str] = None,
    currency: str = "VND"
) -> Dict[str, Any]:
    """Tạo mới hoặc cập nhật tài khoản thụ hưởng."""
    if not unit_name or not unit_name.strip():
        raise ValueError("Tên đơn vị thụ hưởng không được để trống.")
    if not account_number or not account_number.strip():
        raise ValueError("Số tài khoản không được để trống.")
    if not bank_name or not bank_name.strip():
        raise ValueError("Tên ngân hàng không được để trống.")

    unit_name = unit_name.strip()
    account_number = account_number.strip()
    bank_name = bank_name.strip()
    short_name = short_name.strip() if short_name else None
    default_reason = default_reason.strip() if default_reason else None
    swift_code = swift_code.strip() if swift_code else None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO beneficiaries (unit_name, account_number, bank_name, short_name, default_reason, swift_code, currency, usage_count, last_used_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(unit_name) DO UPDATE SET
                account_number = excluded.account_number,
                bank_name = excluded.bank_name,
                short_name = COALESCE(excluded.short_name, beneficiaries.short_name),
                default_reason = COALESCE(excluded.default_reason, beneficiaries.default_reason),
                swift_code = COALESCE(excluded.swift_code, beneficiaries.swift_code),
                currency = excluded.currency,
                updated_at = CURRENT_TIMESTAMP
            """,
            (unit_name, account_number, bank_name, short_name, default_reason, swift_code, currency)
        )
        conn.commit()
        return get_beneficiary_by_name(unit_name) or {}
    finally:
        conn.close()


def record_beneficiary_usage(
    unit_name: str,
    account_number: Optional[str] = None,
    bank_name: Optional[str] = None
):
    """Ghi nhận lượt sử dụng, tăng usage_count và tự động lưu nếu là đơn vị mới."""
    if not unit_name or not unit_name.strip():
        return
    unit_name = unit_name.strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        existing = cursor.execute("SELECT id FROM beneficiaries WHERE unit_name = ?", (unit_name,)).fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE beneficiaries 
                SET usage_count = usage_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (existing[0],)
            )
        elif account_number and bank_name:
            cursor.execute(
                """
                INSERT OR IGNORE INTO beneficiaries (unit_name, account_number, bank_name, usage_count, last_used_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                """,
                (unit_name, account_number.strip(), bank_name.strip())
            )
        conn.commit()
    except Exception as exc:
        logger.warning("Could not record beneficiary usage for %s: %s", unit_name, exc)
    finally:
        conn.close()


def delete_beneficiary(beneficiary_id: int) -> bool:
    """Xóa 1 tài khoản thụ hưởng khỏi danh bạ."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM beneficiaries WHERE id = ?", (beneficiary_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
