"""Contract service orchestrating DOCX filling and contract preview generation."""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.config import BASE_DIR, OUTPUTS_DIR, TEMPLATE_DOCX, WORKING_DIR
from app.services.preview_service import generate_contract_preview_html
from app.services.payment_schedule_service import (
    normalize_payment_schedule,
    resolve_payment_schedule,
)
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_chinese_words,
    number_to_vietnamese_words,
    parse_positive_integer,
)
from app.utils.file_helper import generate_contract_filename

# Ensure import path to dien_hop_dong_tu_dong
hop_dong_dir = str(WORKING_DIR / "scripts" / "hop_dong_generator")
if hop_dong_dir not in sys.path:
    sys.path.insert(0, hop_dong_dir)

try:
    from dien_hop_dong_tu_dong import fill_contract
except ImportError as exc:
    raise ImportError(f"Cannot import fill_contract from {hop_dong_dir}: {exc}")


def prepare_contract_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize, calculate totals, and ensure all required fields are present."""
    data = dict(raw_data)
    now = datetime.now()

    # Fallback date if not provided
    if not data.get("ngay_ky"):
        data["ngay_ky"] = str(now.day)
    if not data.get("thang_ky"):
        data["thang_ky"] = str(now.month)
    if not data.get("nam_ky"):
        data["nam_ky"] = str(now.year)
    if not data.get("so_hop_dong"):
        data["so_hop_dong"] = f"HD-{now.strftime('%Y%m%d')}-001"

    # Bên B default
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

    # Ensure Bên A structure
    ben_a = data.get("ben_a", {})
    raw_role = str(ben_a.get("chuc_vu", "")).strip()
    if not raw_role:
        ben_a["chuc_vu"] = "TỔNG GIÁM ĐỐC"
    else:
        role_cleaned = re.sub(r"\s*/\s*[\u4e00-\u9fff\s]+.*$", "", raw_role)
        role_cleaned = re.sub(r"[\u4e00-\u9fff]+", "", role_cleaned).strip()
        ben_a["chuc_vu"] = role_cleaned.upper() if role_cleaned else "TỔNG GIÁM ĐỐC"
    if not ben_a.get("chuc_vu_trung"):
        ben_a["chuc_vu_trung"] = "總經理"
    data["ben_a"] = ben_a

    # Ensure Dự Án
    du_an = data.get("du_an", {})
    if not du_an.get("ten_du_an_viet"):
        du_an["ten_du_an_viet"] = "Triển khai phần mềm và thiết bị IoT"
    data["du_an"] = du_an

    # Calculate item list totals and verify
    hang_muc = data.get("hang_muc", [])
    total_amount = 0
    total_qty = 0
    for idx, item in enumerate(hang_muc, start=1):
        item["stt"] = idx
        u_price = parse_positive_integer(item.get("don_gia", 0))
        qty = parse_positive_integer(item.get("so_luong", 0))
        line_total = parse_positive_integer(item.get("tong_gia", 0))

        if line_total == 0 and u_price and qty:
            line_total = u_price * qty
            item["tong_gia"] = format_currency_vnd(line_total)

        total_amount += line_total
        total_qty += qty

    if not data.get("tong_so_luong") and total_qty > 0:
        data["tong_so_luong"] = f"{total_qty} SET"

    # Synchronize stated total & respect discount if specified
    discounted_val = parse_positive_integer(data.get("tong_tien_sau_giam", 0))
    stated_val = parse_positive_integer(data.get("tong_tien_hop_dong_so", 0))

    final_contract_total = stated_val or discounted_val or total_amount
    data["tong_tien_truoc_giam"] = format_currency_vnd(total_amount)
    data["tong_tien_hop_dong_so"] = f"{final_contract_total:,}".replace(",", ".")

    if final_contract_total < total_amount and total_amount > 0:
        data["has_discount"] = True
        data["tong_tien_sau_giam"] = format_currency_vnd(final_contract_total)
    else:
        data["has_discount"] = False
        data["tong_tien_sau_giam"] = ""

    # Word conversions
    data["tong_tien_chu_viet"] = number_to_vietnamese_words(final_contract_total)
    data["tong_tien_chu_trung"] = number_to_chinese_words(final_contract_total)

    # Preserve an explicitly edited schedule. If none was supplied, select the
    # closest pattern from the approved 備註 sheets (712TR is the general fallback).
    if data.get("phan_bo_thanh_toan"):
        data["phan_bo_thanh_toan"] = normalize_payment_schedule(
            data["phan_bo_thanh_toan"], data
        )
    else:
        data["phan_bo_thanh_toan"] = resolve_payment_schedule("", data)

    for installment in data["phan_bo_thanh_toan"]:
        percentage = float(installment.get("phan_tram", 0))
        installment["so_tien"] = format_currency_vnd(
            round(final_contract_total * percentage / 100)
        )

    return data


def generate_contract_docx(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Word (.docx) file preserving 100% template layout, with support for custom output directory."""
    import shutil
    import logging
    svc_logger = logging.getLogger(__name__)

    sanitized_data = prepare_contract_data(data)
    
    if not os.path.exists(TEMPLATE_DOCX):
        raise FileNotFoundError(f"Không tìm thấy mẫu hợp đồng: {TEMPLATE_DOCX}")

    company_name = sanitized_data["ben_a"].get("ten_cong_ty", "KHACH_HANG")
    contract_no = sanitized_data.get("so_hop_dong", "")
    filename = generate_contract_filename(company_name, contract_no)
    default_output_path = OUTPUTS_DIR / filename

    # Check for custom output folder (default: E:\Working\Ho So Du An\Hop Dong)
    default_project_dir = WORKING_DIR / "Ho So Du An" / "Hop Dong"
    custom_dir = (data.get("custom_output_dir") or data.get("output_dir") or "").strip()
    if not custom_dir:
        custom_dir = str(default_project_dir)

    target_custom_path = None
    if custom_dir:
        try:
            custom_folder = Path(custom_dir)
            custom_folder.mkdir(parents=True, exist_ok=True)
            target_custom_path = custom_folder / filename
        except Exception as err:
            svc_logger.warning("Could not prepare custom output folder %s: %s", custom_dir, err)

    output_path = target_custom_path if target_custom_path else default_output_path

    # Execute core Zero-Layout-Distortion fill engine
    fill_result = fill_contract(
        template_path=str(TEMPLATE_DOCX),
        output_path=str(output_path),
        data=sanitized_data
    )

    actual_file = Path(fill_result.get("output_path", output_path))

    # Keep a copy in standard OUTPUTS_DIR so web downloads always work seamlessly
    if target_custom_path and actual_file.exists() and actual_file != default_output_path:
        try:
            OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(actual_file, default_output_path)
        except Exception as copy_err:
            svc_logger.warning("Could not sync to default outputs dir: %s", copy_err)

    preview_html = generate_contract_preview_html(sanitized_data)

    # Index document in SQLite documents table so link and path are persisted
    try:
        from app.database import index_single_document
        index_single_document(
            contract_code=contract_no or "DRAFT",
            doc_type="HOP_DONG",
            doc_name=f"Hợp đồng mua bán {contract_no or company_name}",
            file_name=actual_file.name,
            file_path=str(actual_file),
            file_size=actual_file.stat().st_size if actual_file.exists() else 0,
            file_format="docx",
            description=f"Hợp đồng mua bán song ngữ Việt - Trung ({company_name})"
        )
    except Exception as idx_err:
        svc_logger.warning("Could not auto-index document into SQLite: %s", idx_err)

    return {
        "status": "success",
        "file_name": actual_file.name,
        "file_path": str(actual_file),
        "folder_path": str(actual_file.parent),
        "download_url": f"/api/v1/contracts/download/{actual_file.name}",
        "total_amount": sanitized_data.get("tong_tien_sau_giam", ""),
        "company_name": company_name,
        "preview_html": preview_html,
        "contract_data": sanitized_data
    }


def save_contract_to_database(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Word (.docx) file, save contract and milestones into SQLite dossier, and index file."""
    import shutil
    import logging
    from app.database import get_db_connection
    from app.services.payment_request_excel_service import generate_payment_request_excel
    
    svc_logger = logging.getLogger(__name__)

    # 1. Generate official Word DOCX
    docx_result = generate_contract_docx(raw_data)
    sanitized = docx_result["contract_data"]
    file_path = Path(docx_result["file_path"])

    # 2. Copy DOCX to official project folder: "Ho So Du An/Hop Dong/"
    hop_dong_dir = WORKING_DIR / "Ho So Du An" / "Hop Dong"
    os.makedirs(hop_dong_dir, exist_ok=True)
    target_docx = hop_dong_dir / file_path.name
    try:
        shutil.copy2(file_path, target_docx)
        saved_docx_path = target_docx
    except Exception as err:
        svc_logger.warning("Could not copy docx to Ho So Du An: %s", err)
        saved_docx_path = file_path

    # 3. Extract contract details
    contract_code = sanitized.get("so_hop_dong", "").strip()
    if not contract_code:
        now = datetime.now()
        contract_code = f"HMV{now.strftime('%d%m%Y')}0001"

    ben_a = sanitized.get("ben_a", {})
    cust_vi = ben_a.get("ten_cong_ty", "").strip() or "Khách hàng"
    cust_zh = ben_a.get("ten_tieng_trung", "").strip()
    du_an = sanitized.get("du_an", {})
    proj_vi = du_an.get("ten_du_an_viet", "").strip() or "Dự án Hợp đồng mua bán"
    proj_zh = du_an.get("ten_du_an_trung", "").strip()

    day = sanitized.get("ngay_ky", "")
    month = sanitized.get("thang_ky", "")
    year = sanitized.get("nam_ky", "")
    signed_date = f"{str(day).zfill(2)}/{str(month).zfill(2)}/{year}" if (day and month and year) else datetime.now().strftime("%d/%m/%Y")

    total_amount = parse_positive_integer(sanitized.get("tong_tien_hop_dong_so", 0))
    if total_amount == 0:
        total_amount = parse_positive_integer(sanitized.get("tong_tien_sau_giam", 0))

    contact_email = "nguyensykimbang321@gmail.com"
    contact_cc = "pm02@hongming-global.com, sales@hongming-global.com"
    lead_eng = "Jenson Chang (張永吉)"
    status = "Mới ký kết - Chờ thu đợt 1"

    conn = get_db_connection()
    cursor = conn.cursor()

    # 4. Insert or Update into contracts table
    cursor.execute("SELECT id FROM contracts WHERE contract_code = ?", (contract_code,))
    existing = cursor.fetchone()

    if existing:
        contract_id = existing["id"]
        cursor.execute("""
            UPDATE contracts SET
                customer_name_vi = ?, customer_name_zh = ?,
                project_name_vi = ?, project_name_zh = ?,
                lead_engineer = ?, signed_date = ?,
                total_amount = ?, status = ?,
                contact_email = ?, contact_cc = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            cust_vi, cust_zh, proj_vi, proj_zh,
            lead_eng, signed_date, total_amount, status,
            contact_email, contact_cc, contract_id
        ))
    else:
        cursor.execute("""
            INSERT INTO contracts (
                contract_code, customer_name_vi, customer_name_zh,
                project_name_vi, project_name_zh, lead_engineer,
                signed_date, total_amount, paid_amount, status,
                contact_email, contact_cc, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        """, (
            contract_code, cust_vi, cust_zh,
            proj_vi, proj_zh, lead_eng,
            signed_date, total_amount, status,
            contact_email, contact_cc, f"Tạo từ hệ thống web ngày {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ))
        contract_id = cursor.lastrowid

    # 5. Create or refresh the exact number of payment milestones entered by the user.
    cursor.execute("DELETE FROM payment_milestones WHERE contract_id = ? OR contract_code = ?", (contract_id, contract_code))

    installments = sanitized["phan_bo_thanh_toan"]

    now = datetime.now()
    for idx, inst in enumerate(installments, start=1):
        dot_num = inst.get("dot", idx)
        pct = float(inst.get("phan_tram", 0))
        ms_amt = round(total_amount * pct / 100)
        ms_name = f"Đợt {dot_num}"
        cond = inst.get("dieu_kien_viet") or f"Thanh toán Đợt {dot_num} ({pct}%)"

        deadline_days = int(inst.get("thoi_han_tt_ngay") or 0)
        ms_status = "PENDING_TRIGGER"
        ms_label = "Chờ đánh dấu điều kiện"
        ms_action = f"Đánh dấu hoàn thành điều kiện Đợt {dot_num} để bắt đầu tính T/T {deadline_days} ngày"
        due_str = None

        cursor.execute("""
            INSERT INTO payment_milestones (
                contract_id, contract_code, milestone_name, percentage, amount,
                trigger_condition, trigger_date, payment_term_days, triggered,
                due_date, invoice_no, status, status_label,
                action_required, paid_date
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, 0, ?, 'Chưa xuất', ?, ?, ?, NULL)
        """, (
            contract_id, contract_code, ms_name, pct, ms_amt,
            cond, deadline_days, due_str, ms_status, ms_label, ms_action
        ))

    # 6. Index Word DOCX into documents table
    file_size = saved_docx_path.stat().st_size if saved_docx_path.exists() else 0
    cursor.execute("DELETE FROM documents WHERE contract_id = ? AND file_name = ?", (contract_id, saved_docx_path.name))
    cursor.execute("""
        INSERT INTO documents (
            contract_id, contract_code, doc_type, doc_name, file_name,
            file_path, file_size, file_format, description
        ) VALUES (?, ?, 'HOP_DONG', ?, ?, ?, ?, 'docx', ?)
    """, (
        contract_id, contract_code, f"Hợp đồng mua bán {contract_code}",
        saved_docx_path.name, str(saved_docx_path), file_size,
        f"Hợp đồng mua bán song ngữ Việt - Trung ({cust_vi})"
    ))

    conn.commit()
    conn.close()

    # 7. Automatically generate the initial 1:1 Excel Payment Request using
    # the actual first milestone instead of a fixed percentage.
    try:
        first_installment = installments[0]
        first_percentage = float(first_installment["phan_tram"])
        generate_payment_request_excel(
            contract_code=contract_code,
            milestone_name="Đợt 1",
            customer_name_vi=cust_vi,
            customer_name_zh=cust_zh,
            amount=round(total_amount * first_percentage / 100),
            due_date=""
        )
    except Exception as err:
        svc_logger.warning("Could not pre-generate initial Excel sheet: %s", err)

    return {
        "status": "success",
        "message": f"Đã lưu thành công Hợp đồng {contract_code} vào hệ thống!",
        "contract_code": contract_code,
        "contract_id": contract_id,
        "file_name": saved_docx_path.name,
        "file_path": str(saved_docx_path),
        "folder_path": str(saved_docx_path.parent),
        "download_url": docx_result["download_url"],
        "total_amount": total_amount,
        "customer_name": cust_vi,
        "reminders_url": "/reminders"
    }


def get_all_contracts_list() -> List[Dict[str, Any]]:
    """Retrieve full list of created contracts combining SQLite database and exported DOCX files."""
    from app.database import get_db_connection

    results = []
    seen_file_names = set()
    seen_contract_codes = set()

    # 1. Fetch contracts saved in SQLite
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.*, 
                   d.file_name, d.file_path, d.file_size, d.file_format, d.created_at as doc_created_at
            FROM contracts c
            LEFT JOIN documents d ON (d.contract_id = c.id OR d.contract_code = c.contract_code) AND d.doc_type = 'HOP_DONG'
            ORDER BY c.id DESC
        """)
        rows = cursor.fetchall()

        for r in rows:
            row_dict = dict(r)
            c_code = row_dict.get("contract_code") or ""
            f_name = row_dict.get("file_name") or ""
            f_path_str = row_dict.get("file_path") or ""

            # Check file on disk if available
            actual_path = None
            if f_path_str and os.path.exists(f_path_str):
                actual_path = Path(f_path_str)
            elif f_name:
                for candidate in [
                    WORKING_DIR / "Ho So Du An" / "Hop Dong" / f_name,
                    OUTPUTS_DIR / f_name,
                ]:
                    if candidate.exists():
                        actual_path = candidate
                        break

            file_size_bytes = actual_path.stat().st_size if actual_path and actual_path.exists() else (row_dict.get("file_size") or 0)
            file_mtime = datetime.fromtimestamp(actual_path.stat().st_mtime).strftime("%d/%m/%Y %H:%M") if actual_path and actual_path.exists() else ""

            if f_name:
                seen_file_names.add(f_name.lower())
            if c_code:
                seen_contract_codes.add(c_code.lower())

            results.append({
                "id": row_dict.get("id"),
                "contract_code": c_code,
                "customer_name_vi": row_dict.get("customer_name_vi") or "",
                "customer_name_zh": row_dict.get("customer_name_zh") or "",
                "project_name_vi": row_dict.get("project_name_vi") or "",
                "project_name_zh": row_dict.get("project_name_zh") or "",
                "lead_engineer": row_dict.get("lead_engineer") or "",
                "signed_date": row_dict.get("signed_date") or "",
                "total_amount": row_dict.get("total_amount") or 0,
                "paid_amount": row_dict.get("paid_amount") or 0,
                "currency": row_dict.get("currency") or "VND",
                "status": row_dict.get("status") or "Đang thực hiện",
                "notes": row_dict.get("notes") or "",
                "created_at": row_dict.get("created_at") or "",
                "file_name": f_name or (actual_path.name if actual_path else ""),
                "file_path": str(actual_path) if actual_path else f_path_str,
                "file_size": file_size_bytes,
                "file_mtime": file_mtime,
                "download_url": f"/api/v1/contracts/download/{f_name or (actual_path.name if actual_path else '')}" if (f_name or actual_path) else "",
                "source": "database"
            })

        conn.close()
    except Exception as exc:
        logging.getLogger(__name__).warning("Error querying contracts table: %s", exc)

    # 2. Scan physical folders for exported DOCX files not yet in the DB list
    scan_dirs = [
        WORKING_DIR / "Ho So Du An" / "Hop Dong",
        OUTPUTS_DIR
    ]

    for s_dir in scan_dirs:
        if not s_dir.exists():
            continue

        for p in s_dir.glob("*.docx"):
            if p.name.startswith("~$") or p.name.lower().startswith("test_") or "bien_ban" in p.name.lower():
                continue

            clean_lower = p.name.lower()
            if clean_lower in seen_file_names:
                continue

            seen_file_names.add(clean_lower)

            # Heuristic parse: Hop_Dong_{CUSTOMER}_{CONTRACT_CODE}_{TIMESTAMP}.docx
            extracted_code = ""
            extracted_customer = ""
            match = re.search(r"Hop_Dong_(.+?)_((?:HD|HMV)[\w\-]+)_(\d{8}_\d{6})", p.name, re.IGNORECASE)
            if match:
                raw_cust = match.group(1).replace("_", " ")
                extracted_customer = raw_cust
                extracted_code = match.group(2)
            else:
                match2 = re.search(r"Hop_Dong_(.+?)_(\d{8}_\d{6})", p.name, re.IGNORECASE)
                if match2:
                    extracted_customer = match2.group(1).replace("_", " ")
                else:
                    extracted_customer = p.stem.replace("Hop_Dong_", "").replace("_", " ")

            mtime_dt = datetime.fromtimestamp(p.stat().st_mtime)
            mtime_str = mtime_dt.strftime("%d/%m/%Y %H:%M")

            results.append({
                "id": None,
                "contract_code": extracted_code or "HỢP ĐỒNG WORD",
                "customer_name_vi": extracted_customer,
                "customer_name_zh": "",
                "project_name_vi": "Hợp đồng mua bán thiết bị & dịch vụ",
                "project_name_zh": "",
                "lead_engineer": "Hong Ming Global",
                "signed_date": mtime_dt.strftime("%d/%m/%Y"),
                "total_amount": 0,
                "paid_amount": 0,
                "currency": "VND",
                "status": "Đã xuất file Word",
                "notes": f"Tệp tạo ngày {mtime_str}",
                "created_at": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": p.name,
                "file_path": str(p),
                "file_size": p.stat().st_size,
                "file_mtime": mtime_str,
                "download_url": f"/api/v1/contracts/download/{p.name}",
                "source": "file_scan"
            })

    # Sort descending: newest created_at / file_mtime first
    def get_sort_key(item):
        return item.get("created_at") or item.get("file_mtime") or ""

    results.sort(key=get_sort_key, reverse=True)
    return results


def get_contract_detail_by_id_or_code(identifier: str) -> Dict[str, Any]:
    """Retrieve full contract details formatted for populating into ContractEditor form."""
    from app.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    row = None
    if str(identifier).isdigit():
        cursor.execute("SELECT * FROM contracts WHERE id = ?", (int(identifier),))
        row = cursor.fetchone()

    if not row:
        cursor.execute("SELECT * FROM contracts WHERE contract_code = ?", (str(identifier).strip(),))
        row = cursor.fetchone()

    if not row:
        # Check by file_name if identifier is a docx file
        cursor.execute("""
            SELECT c.* FROM contracts c
            JOIN documents d ON d.contract_id = c.id OR d.contract_code = c.contract_code
            WHERE d.file_name = ?
            LIMIT 1
        """, (str(identifier).strip(),))
        row = cursor.fetchone()

    if not row:
        conn.close()
        raise ValueError(f"Không tìm thấy hợp đồng với mã hoặc ID '{identifier}'")

    c = dict(row)
    c_id = c["id"]
    c_code = c["contract_code"]

    # Fetch milestones
    cursor.execute("""
        SELECT * FROM payment_milestones 
        WHERE contract_id = ? OR contract_code = ? 
        ORDER BY id ASC
    """, (c_id, c_code))
    milestones = [dict(m) for m in cursor.fetchall()]

    # Fetch document
    cursor.execute("""
        SELECT * FROM documents 
        WHERE (contract_id = ? OR contract_code = ?) AND doc_type = 'HOP_DONG'
        ORDER BY id DESC LIMIT 1
    """, (c_id, c_code))
    doc_row = cursor.fetchone()
    doc_dict = dict(doc_row) if doc_row else {}

    conn.close()

    # Parse signed date DD/MM/YYYY
    day, month, year = "", "", ""
    signed_date = c.get("signed_date") or ""
    if "/" in signed_date:
        parts = signed_date.split("/")
        if len(parts) >= 3:
            day, month, year = parts[0], parts[1], parts[2]

    # Convert milestones to phan_bo_thanh_toan
    phan_bo = []
    for idx, m in enumerate(milestones, start=1):
        m_name = m.get("milestone_name") or f"Đợt {idx}"
        pct = m.get("percentage") or 0
        cond = m.get("trigger_condition") or ""
        days = m.get("payment_term_days") or 0
        phan_bo.append({
            "dot": idx,
            "phan_tram": pct,
            "thoi_han_tt_ngay": days,
            "tieu_de": f"{m_name} ({pct}%)",
            "tieu_de_trung": f"第{idx}期款" if idx < len(milestones) else "尾款",
            "dieu_kien_viet": cond,
            "dieu_kien_trung": cond,
            "so_tien": f"{int(m.get('amount') or 0):,}".replace(",", ".")
        })

    tot_amt = int(c.get("total_amount") or 0)
    formatted_total = f"{tot_amt:,}".replace(",", ".") if tot_amt > 0 else ""

    return {
        "id": c.get("id"),
        "so_hop_dong": c_code,
        "ngay_ky": day,
        "thang_ky": month,
        "nam_ky": year,
        "ben_a": {
            "ten_cong_ty": c.get("customer_name_vi") or "",
            "ten_tieng_trung": c.get("customer_name_zh") or "",
            "dia_chi": "",
            "dia_chi_trung": "",
            "mst": "",
            "nguoi_dai_dien": "",
            "chuc_vu": "TỔNG GIÁM ĐỐC",
            "chuc_vu_trung": "總經理"
        },
        "ben_b": {
            "ten_cong_ty": "CÔNG TY TNHH TOÀN CẦU HONG MING",
            "ten_tieng_trung": "宏明環球有限公司",
            "dia_chi": "Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam",
            "dia_chi_trung": "越南胡志明市西貢坊阮惠路68號2樓",
            "mst": "0318280158",
            "nguoi_dai_dien": "TANG WEI LI",
            "chuc_vu": "TỔNG GIÁM ĐỐC",
            "chuc_vu_trung": "總經理"
        },
        "du_an": {
            "ten_du_an_viet": c.get("project_name_vi") or "",
            "ten_du_an_trung": c.get("project_name_zh") or ""
        },
        "tong_tien_hop_dong_so": formatted_total,
        "tong_tien_truoc_giam": f"{formatted_total} VND" if formatted_total else "",
        "tong_tien_sau_giam": f"{formatted_total} VND" if formatted_total else "",
        "thoi_gian_giao_hang_ngay": 80,
        "thoi_gian_bao_hanh_thang": 12,
        "phan_bo_thanh_toan": phan_bo,
        "hang_muc": [],
        "file_name": doc_dict.get("file_name", ""),
        "file_path": doc_dict.get("file_path", ""),
        "download_url": f"/api/v1/contracts/download/{doc_dict.get('file_name', '')}" if doc_dict.get("file_name") else "",
        "status": c.get("status") or "Đang thực hiện"
    }


def delete_contract_service(identifier: str) -> Dict[str, Any]:
    """Delete a contract and its associated milestones and document references."""
    from app.database import get_db_connection

    conn = get_db_connection()
    cursor = conn.cursor()

    row = None
    if str(identifier).isdigit():
        cursor.execute("SELECT id, contract_code FROM contracts WHERE id = ?", (int(identifier),))
        row = cursor.fetchone()

    if not row:
        cursor.execute("SELECT id, contract_code FROM contracts WHERE contract_code = ?", (str(identifier).strip(),))
        row = cursor.fetchone()

    if row:
        c_id = row["id"]
        c_code = row["contract_code"]
        cursor.execute("DELETE FROM payment_milestones WHERE contract_id = ? OR contract_code = ?", (c_id, c_code))
        cursor.execute("DELETE FROM documents WHERE contract_id = ? OR contract_code = ?", (c_id, c_code))
        cursor.execute("DELETE FROM contracts WHERE id = ?", (c_id,))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"Đã xóa thành công hợp đồng {c_code} khỏi hệ thống."
        }

    # If only a document or code exists
    cursor.execute("DELETE FROM documents WHERE file_name = ? OR contract_code = ?", (str(identifier), str(identifier)))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Đã xóa thông tin hợp đồng '{identifier}' khỏi danh sách."
    }

