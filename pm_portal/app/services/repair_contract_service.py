"""Business service for Repair and Maintenance Contracts."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import OUTPUTS_DIR, WORKING_DIR
from app.database import get_db_connection
from app.services.repair_contract_word_service import generate_repair_contract_docx
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)


def prepare_repair_contract_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize, calculate totals, and ensure all required fields are present for repair contract."""
    data = dict(raw_data)
    now = datetime.now()

    if not data.get("ngay_ky"):
        data["ngay_ky"] = str(now.day)
    if not data.get("thang_ky"):
        data["thang_ky"] = str(now.month)
    if not data.get("nam_ky"):
        data["nam_ky"] = str(now.year)
    if not data.get("so_hop_dong"):
        data["so_hop_dong"] = f"HDSC-{now.strftime('%Y%m%d')}-001"

    if not data.get("ben_b"):
        data["ben_b"] = {
            "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
            "ten_tieng_trung": "宏明環球有限公司",
            "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
            "dia_chi_trung": "越南胡志明市西貢坊阮惠路68號2樓",
            "mst": "0318280158",
            "nguoi_dai_dien": "TANG WEI LI",
            "chuc_vu": "TỔNG GIÁM ĐỐC",
            "chuc_vu_trung": "總經理"
        }

    ben_a = data.get("ben_a", {})
    raw_role = str(ben_a.get("chuc_vu", "")).strip()
    if not raw_role:
        ben_a["chuc_vu"] = "TỔNG GIÁM ĐỐC"
    if not ben_a.get("chuc_vu_trung"):
        ben_a["chuc_vu_trung"] = "總經理"
    data["ben_a"] = ben_a

    if not data.get("ten_goi_sua_chua_viet"):
        data["ten_goi_sua_chua_viet"] = "Dịch vụ sửa chữa và bảo dưỡng thiết bị"
    if not data.get("ten_goi_sua_chua_trung"):
        data["ten_goi_sua_chua_trung"] = "設備維修與保養服務"

    if not data.get("dia_diem_sua_chua"):
        data["dia_diem_sua_chua"] = "Tại nhà xưởng sản xuất Bên A"

    # Calculate item totals
    hang_muc = data.get("hang_muc", [])
    total_amount = 0
    total_qty = 0

    for idx, item in enumerate(hang_muc, start=1):
        item["stt"] = idx
        raw_price = item.get("don_gia", "")
        raw_qty = item.get("so_luong", "1")

        price_int = parse_positive_integer(raw_price)
        qty_match = re.search(r"\d+", str(raw_qty))
        qty_int = int(qty_match.group(0)) if qty_match else 1
        total_qty += qty_int

        row_total = price_int * qty_int
        item["don_gia"] = format_currency_vnd(price_int)
        item["tong_gia"] = format_currency_vnd(row_total)
        total_amount += row_total

    data["hang_muc"] = hang_muc
    data["tong_so_luong"] = f"{total_qty} SET" if total_qty > 0 else "0 SET"

    if total_amount > 0:
        data["tong_tien_hop_dong_so"] = format_currency_vnd(total_amount).replace(" VND", "")
        data["tong_tien_truoc_giam"] = format_currency_vnd(total_amount)
        data["tong_tien_sau_giam"] = format_currency_vnd(total_amount)
        data["tong_tien_chu_viet"] = number_to_vietnamese_words(total_amount)
        data["tong_tien_chu_trung"] = number_to_chinese_words(total_amount)

        # Process Installments
        installments = data.get("phan_bo_thanh_toan", [])
        if not installments:
            data["phan_bo_thanh_toan"] = [
                {
                    "dot": 1,
                    "phan_tram": 50,
                    "so_tien": format_currency_vnd(round(total_amount * 0.5)),
                    "tieu_de": "Tạm ứng ký hợp đồng",
                    "tieu_de_trung": "簽約預付款",
                    "dieu_kien_viet": "Thanh toán tạm ứng 50% ngay sau khi ký kết hợp đồng sửa chữa",
                    "dieu_kien_trung": "雙方簽署維修合約後即期以電匯方式支付 50%",
                    "thoi_han_tt_ngay": 0
                },
                {
                    "dot": 2,
                    "phan_tram": 50,
                    "so_tien": format_currency_vnd(round(total_amount * 0.5)),
                    "tieu_de": "Nghiệm thu hoàn tất",
                    "tieu_de_trung": "驗收交付款",
                    "dieu_kien_viet": "Thanh toán 50% còn lại sau khi hoàn thành sửa chữa, chạy thử đạt và ký biên bản nghiệm thu",
                    "dieu_kien_trung": "設備維修完成、測試正常並簽署驗收確認書後支付剩餘 50%",
                    "thoi_han_tt_ngay": 30
                }
            ]
        else:
            for inst in installments:
                pct = float(inst.get("phan_tram", 0) or 0)
                if pct > 0:
                    inst_amount = round(total_amount * pct / 100)
                    inst["so_tien"] = format_currency_vnd(inst_amount)

    return data


def save_repair_contract_to_db(data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update repair contract and its payment installments into SQLite database."""
    prepared = prepare_repair_contract_data(data)
    so_hd = prepared["so_hop_dong"]
    ben_a = prepared["ben_a"]
    total_val = parse_positive_integer(prepared.get("tong_tien_hop_dong_so", 0))

    signed_date_str = f"{prepared.get('nam_ky')}-{prepared.get('thang_ky', '01').zfill(2)}-{prepared.get('ngay_ky', '01').zfill(2)}"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure contract_type column exists
    try:
        col_info = [r[1] for r in cursor.execute("PRAGMA table_info(contracts)").fetchall()]
        if "contract_type" not in col_info:
            cursor.execute("ALTER TABLE contracts ADD COLUMN contract_type TEXT DEFAULT 'SALE'")
    except Exception:
        pass

    # Check if contract already exists
    cursor.execute("SELECT id FROM contracts WHERE contract_code = ?", (so_hd,))
    row = cursor.fetchone()

    project_vi = prepared.get("ten_goi_sua_chua_viet", "Dịch vụ sửa chữa thiết bị")
    project_zh = prepared.get("ten_goi_sua_chua_trung", "設備維修保養服務")

    if row:
        contract_id = row["id"]
        cursor.execute("""
            UPDATE contracts SET
                customer_name_vi = ?,
                customer_name_zh = ?,
                project_name_vi = ?,
                project_name_zh = ?,
                signed_date = ?,
                total_amount = ?,
                contract_type = 'REPAIR',
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            ben_a.get("ten_cong_ty", ""),
            ben_a.get("ten_tieng_trung", ""),
            project_vi,
            project_zh,
            signed_date_str,
            total_val,
            f"Thời hạn sửa chữa: {prepared.get('thoi_gian_hoan_thanh_ngay', 15)} ngày; Bảo hành: {prepared.get('thoi_gian_bao_hanh_thang', 6)} tháng",
            contract_id
        ))
    else:
        cursor.execute("""
            INSERT INTO contracts (
                contract_code, customer_name_vi, customer_name_zh,
                project_name_vi, project_name_zh, signed_date,
                total_amount, paid_amount, status, contract_type, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'Đang thực hiện sửa chữa', 'REPAIR', ?)
        """, (
            so_hd,
            ben_a.get("ten_cong_ty", ""),
            ben_a.get("ten_tieng_trung", ""),
            project_vi,
            project_zh,
            signed_date_str,
            total_val,
            f"Thời hạn sửa chữa: {prepared.get('thoi_gian_hoan_thanh_ngay', 15)} ngày; Bảo hành: {prepared.get('thoi_gian_bao_hanh_thang', 6)} tháng"
        ))
        contract_id = cursor.lastrowid

    # Refresh payment milestones
    cursor.execute("DELETE FROM payment_milestones WHERE contract_id = ?", (contract_id,))

    installments = prepared.get("phan_bo_thanh_toan", [])
    for idx, inst in enumerate(installments, start=1):
        pct = float(inst.get("phan_tram", 0) or 0)
        amount_m = round(total_val * pct / 100) if total_val > 0 else 0
        term_days = inst.get("thoi_han_tt_ngay")
        if term_days is None:
            term_days = 0 if idx == 1 else 30

        trigger_cond = inst.get("dieu_kien_viet", f"Đợt {idx}")
        milestone_name = inst.get("tieu_de") or f"Đợt {idx} ({pct}%)"

        cursor.execute("""
            INSERT INTO payment_milestones (
                contract_id, contract_code, milestone_name, percentage,
                amount, trigger_condition, payment_term_days, triggered, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (
            contract_id,
            so_hd,
            milestone_name,
            pct,
            amount_m,
            trigger_cond,
            term_days,
            1 if idx == 1 else 0
        ))

    conn.commit()
    conn.close()

    # Automatically generate DOCX
    docx_res = generate_repair_contract_docx(prepared, prepared.get("custom_output_dir"))

    return {
        "status": "success",
        "message": f"Đã lưu hợp đồng sửa chữa {so_hd} vào cơ sở dữ liệu và xuất file Word!",
        "contract_id": contract_id,
        "contract_code": so_hd,
        "docx_info": docx_res
    }


def get_all_repair_contracts_list() -> List[Dict[str, Any]]:
    """Retrieve full list of created repair contracts from database and outputs directory."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, contract_code, customer_name_vi, customer_name_zh,
                   project_name_vi, project_name_zh, signed_date,
                   total_amount, paid_amount, status, created_at, updated_at
            FROM contracts
            WHERE contract_type = 'REPAIR' OR contract_code LIKE 'HDSC%'
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        contracts_list = []
        for r in rows:
            code = r["contract_code"]
            total_vnd = r["total_amount"] or 0
            contracts_list.append({
                "id": r["id"],
                "contract_code": code,
                "customer_name_vi": r["customer_name_vi"] or "",
                "customer_name_zh": r["customer_name_zh"] or "",
                "project_name_vi": r["project_name_vi"] or "Dịch vụ sửa chữa thiết bị",
                "project_name_zh": r["project_name_zh"] or "設備維修保養服務",
                "signed_date": r["signed_date"] or "",
                "total_amount": total_vnd,
                "total_amount_formatted": format_currency_vnd(total_vnd),
                "status": r["status"] or "Đang thực hiện sửa chữa",
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            })
        conn.close()
        return contracts_list
    except Exception as exc:
        conn.close()
        return []


def get_repair_contract_detail(contract_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve full repair contract details from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM contracts WHERE contract_code = ?
    """, (contract_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    contract_id = row["id"]
    cursor.execute("""
        SELECT * FROM payment_milestones WHERE contract_id = ? ORDER BY id ASC
    """, (contract_id,))
    milestone_rows = cursor.fetchall()
    conn.close()

    milestones = []
    for m in milestone_rows:
        milestones.append({
            "dot": len(milestones) + 1,
            "phan_tram": m["percentage"],
            "so_tien": format_currency_vnd(m["amount"]),
            "tieu_de": m["milestone_name"],
            "dieu_kien_viet": m["trigger_condition"],
            "thoi_han_tt_ngay": m["payment_term_days"]
        })

    return {
        "so_hop_dong": row["contract_code"],
        "ben_a": {
            "ten_cong_ty": row["customer_name_vi"],
            "ten_tieng_trung": row["customer_name_zh"] or "",
        },
        "ten_goi_sua_chua_viet": row["project_name_vi"] or "",
        "ten_goi_sua_chua_trung": row["project_name_zh"] or "",
        "tong_tien_hop_dong_so": str(int(row["total_amount"] or 0)),
        "phan_bo_thanh_toan": milestones,
        "status": row["status"]
    }


def delete_repair_contract(contract_code: str) -> bool:
    """Delete a repair contract from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contracts WHERE contract_code = ?", (contract_code,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted
