# -*- coding: utf-8 -*-
"""
Database module for Hong Ming PM Portal.
Uses SQLite to store contracts, payment milestones, and document index mapping,
eliminating the need to open raw Excel/Word files to check contract associations.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import openpyxl

from app.config import WORKING_DIR

DB_DIR = WORKING_DIR / "database"
DB_PATH = DB_DIR / "pm_portal.db"
SIMULATED_TODAY = datetime.now()

# Ensure database directory exists
os.makedirs(DB_DIR, exist_ok=True)


def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe connection with dictionary cursor support."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables and schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_code TEXT UNIQUE NOT NULL,
        customer_name_vi TEXT NOT NULL,
        customer_name_zh TEXT,
        project_name_vi TEXT,
        project_name_zh TEXT,
        lead_engineer TEXT,
        signed_date TEXT,
        total_amount REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'VND',
        status TEXT,
        contact_email TEXT,
        contact_cc TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payment_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
        contract_code TEXT NOT NULL,
        milestone_name TEXT NOT NULL,
        percentage REAL,
        amount REAL NOT NULL,
        trigger_condition TEXT,
        trigger_date TEXT,
        payment_term_days INTEGER,
        triggered INTEGER DEFAULT 0,
        due_date TEXT,
        invoice_no TEXT,
        status TEXT,
        status_label TEXT,
        action_required TEXT,
        paid_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL,
        contract_code TEXT,
        doc_type TEXT NOT NULL,
        doc_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        file_format TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS system_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    );

    CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_no TEXT NOT NULL,
        customer_name_vi TEXT NOT NULL,
        customer_name_zh TEXT,
        tax_code TEXT,
        project_name TEXT,
        contact_person TEXT,
        validity TEXT,
        lead_time TEXT,
        warranty TEXT,
        payment_terms TEXT,
        notes TEXT,
        subtotal REAL DEFAULT 0,
        vat_amount REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        version INTEGER DEFAULT 1,
        is_current INTEGER DEFAULT 1,
        docx_file_name TEXT,
        docx_file_path TEXT,
        xlsx_file_name TEXT,
        xlsx_file_path TEXT,
        items_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS custom_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT NOT NULL,
        due_time TEXT DEFAULT '09:00',
        priority TEXT DEFAULT 'NORMAL',
        category TEXT DEFAULT 'GENERAL',
        status TEXT DEFAULT 'PENDING',
        attachment_name TEXT,
        attachment_path TEXT,
        attachment_size INTEGER DEFAULT 0,
        folder_path TEXT,
        attachments TEXT DEFAULT '[]',
        completed_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS beneficiaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT UNIQUE NOT NULL,
        account_number TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        short_name TEXT,
        default_reason TEXT,
        swift_code TEXT,
        currency TEXT DEFAULT 'VND',
        usage_count INTEGER DEFAULT 0,
        last_used_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payment_voucher_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_code TEXT NOT NULL,
        request_date TEXT NOT NULL,
        beneficiary_name TEXT NOT NULL,
        account_number TEXT NOT NULL,
        bank_name TEXT NOT NULL,
        reason_vi TEXT,
        reason_zh TEXT,
        full_reason TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'VND',
        amount_usd REAL,
        exchange_rate REAL DEFAULT 26000,
        amount_in_words_vi TEXT,
        amount_in_words_zh TEXT,
        prepared_by TEXT DEFAULT 'NGUYỄN SỸ KIM BẰNG',
        supervisor TEXT DEFAULT '',
        checker TEXT DEFAULT '',
        accountant TEXT DEFAULT '',
        director TEXT DEFAULT '',
        attachment_note TEXT DEFAULT '',
        file_path TEXT,
        file_name TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS procurement_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no INTEGER,
        project_name TEXT NOT NULL,
        category TEXT,
        item_name TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit TEXT DEFAULT 'Bộ',
        customer_company TEXT,
        supplier_name TEXT NOT NULL,
        order_date TEXT,
        eta_date TEXT,
        actual_delivery_date TEXT,
        material_desc TEXT,
        supplier_payment_status TEXT,
        delivery_status TEXT DEFAULT 'PENDING',
        delivery_status_label TEXT,
        shipping_notes TEXT,
        unit_price REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'VND',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS project_receivables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no INTEGER,
        project_name TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        contract_code TEXT,
        total_contract_amount REAL DEFAULT 0,
        net_amount REAL DEFAULT 0,
        vat_rate REAL DEFAULT 0,
        vat_amount REAL DEFAULT 0,
        gross_amount REAL DEFAULT 0,
        received_amount REAL DEFAULT 0,
        remaining_debt REAL DEFAULT 0,
        customer_promised_date TEXT,
        due_date TEXT,
        paid_date TEXT,
        doc_status TEXT,
        collection_status TEXT DEFAULT 'PENDING',
        notes TEXT,
        linked_milestone_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS receivables_weekly_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date TEXT NOT NULL,
        week_number INTEGER,
        year INTEGER,
        receivable_id INTEGER NOT NULL REFERENCES project_receivables(id) ON DELETE CASCADE,
        project_name TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        contract_code TEXT,
        gross_amount REAL DEFAULT 0,
        received_amount REAL DEFAULT 0,
        remaining_debt REAL DEFAULT 0,
        customer_promised_date TEXT,
        due_date TEXT,
        paid_date TEXT,
        collection_status TEXT,
        notes TEXT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );


    CREATE INDEX IF NOT EXISTS idx_contracts_code ON contracts(contract_code);
    CREATE INDEX IF NOT EXISTS idx_milestones_contract ON payment_milestones(contract_code);
    CREATE INDEX IF NOT EXISTS idx_documents_contract ON documents(contract_code);
    CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type);
    CREATE INDEX IF NOT EXISTS idx_quotations_no ON quotations(quotation_no);
    CREATE INDEX IF NOT EXISTS idx_quotations_current ON quotations(is_current);
    CREATE INDEX IF NOT EXISTS idx_custom_reminders_status ON custom_reminders(status);
    CREATE INDEX IF NOT EXISTS idx_custom_reminders_due ON custom_reminders(due_date);
    CREATE INDEX IF NOT EXISTS idx_beneficiaries_name ON beneficiaries(unit_name);
    CREATE INDEX IF NOT EXISTS idx_beneficiaries_short ON beneficiaries(short_name);
    CREATE INDEX IF NOT EXISTS idx_voucher_report_code ON payment_voucher_requests(report_code);
    CREATE INDEX IF NOT EXISTS idx_voucher_beneficiary ON payment_voucher_requests(beneficiary_name);
    CREATE INDEX IF NOT EXISTS idx_procurement_project ON procurement_orders(project_name);
    CREATE INDEX IF NOT EXISTS idx_procurement_supplier ON procurement_orders(supplier_name);
    CREATE INDEX IF NOT EXISTS idx_procurement_delivery ON procurement_orders(delivery_status);
    CREATE INDEX IF NOT EXISTS idx_snapshots_date ON receivables_weekly_snapshots(snapshot_date);
    CREATE INDEX IF NOT EXISTS idx_snapshots_rec_id ON receivables_weekly_snapshots(receivable_id);

    """)

    # Backward-compatible migration for databases created before event-based
    # payment deadlines were introduced.
    existing_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(payment_milestones)").fetchall()
    }
    for column_name, definition in (
        ("trigger_date", "TEXT"),
        ("payment_term_days", "INTEGER"),
        ("triggered", "INTEGER DEFAULT 0"),
    ):
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE payment_milestones ADD COLUMN {column_name} {definition}"
            )

    # Backward-compatible migration for custom_reminders (folder_path & attachments)
    cr_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(custom_reminders)").fetchall()
    }
    for col_name, col_def in (
        ("folder_path", "TEXT"),
        ("attachments", "TEXT DEFAULT '[]'"),
    ):
        if col_name not in cr_columns:
            cursor.execute(
                f"ALTER TABLE custom_reminders ADD COLUMN {col_name} {col_def}"
            )

    # Seed default beneficiaries if table is empty
    seed_default_beneficiaries(cursor)

    conn.commit()
    conn.close()


def seed_default_beneficiaries(cursor: sqlite3.Cursor):
    """Nạp sẵn danh bạ tài khoản thụ hưởng từ thực tế hoạt động Hong Ming."""
    count = cursor.execute("SELECT COUNT(*) FROM beneficiaries").fetchone()[0]
    if count > 0:
        return

    default_beneficiaries = [
        (
            "CONG TY TNHH TO CHUC SU KIEN OMG",
            "0071000764939",
            "Vietcombank CN HCM",
            "TCSK OMG",
            "Thanh toán theo hợp đồng triển lãm VIMF",
            None,
            "VND",
            5
        ),
        (
            "CONG TY TNHH FINEPRO AUTOMATION",
            "700020535654",
            "Shinhanbank",
            "FINEPRO",
            "Thanh toán chi phí Thu Thập dữ liệu máy dập",
            None,
            "VND",
            4
        ),
        (
            "CÔNG TY TNHH ĐẦU TƯ PHÁT TRIỂN VÀ THƯƠNG MẠI THANH XUÂN",
            "0101100497008",
            "tại ngân hàng MB (Quân Đội)",
            "THANH XUÂN",
            "Thanh toán phí dịch vụ theo Hợp đồng và báo cáo NHNN",
            None,
            "VND",
            3
        ),
        (
            "CÔNG TY TNHH VIET NHAT SOLUTIONS",
            "5592201007166",
            "Agribank - CN Thành phố Thuận An Sóng Thần",
            "VIỆT NHẬT",
            "Thanh toán máy laptop, thiết bị IT",
            "VBAAVNVX6524",
            "VND",
            3
        ),
        (
            "CÔNG TY TNHH MTV CÔNG NGHỆ BÁCH DUY",
            "203485179",
            "Ngân Hàng TMCP Á Châu (ACB) - CN Bắc Sài Gòn",
            "BÁCH DUY",
            "THANH TOÁN MUA PIN MÁY QUÉT MÃ VẠCH RFR900",
            None,
            "VND",
            3
        ),
        (
            "CÔNG TY TNHH AVANTECH VIỆT NAM TECHNOLOGY",
            "0851000023335",
            "Ngân Hàng TMCP Ngoại Thương Việt Nam - CN Hà Thành",
            "Advanteck",
            "Thanh toán giá trị hợp đồng thiết bị Advantech",
            None,
            "VND",
            2
        ),
        (
            "CONG TY TNHH WIN TECH SOLUTION",
            "68968888",
            "tại ngân hàng TMCP Á Châu - CN Bảy Hiền, Tp HCM",
            "WIN TECH",
            "TT gia hạn HT mở hóa đơn",
            None,
            "VND",
            2
        ),
        (
            "CONG TY TNHH PHAT TRIEN CONG NGHE THAI SON",
            "0491001474862",
            "Ngân Hàng TMCP Ngoại Thương VN - CN Thăng Long HN",
            "THÁI SƠN",
            "TT CKS+EBH(bhxh) và Gia hạn CKS+PM Hải Quan",
            None,
            "VND",
            2
        ),
        (
            "CÔNG TY TNHH TÍN BẢO LAN",
            "1043233195",
            "Ngân Hàng TMCP Ngoại Thương Việt Nam - CN Kỳ Đồng, HCM",
            "TÍN BẢO LAN",
            "Thanh toán theo hợp đồng thiết bị Tín Bảo Lan",
            None,
            "VND",
            2
        ),
        (
            "CÔNG TY TNHH HẰNG ĐỈNH",
            "5813207",
            "Ngân Hàng TMCP Á Châu (ACB) – Chi Nhánh Bình Dương",
            "HẰNG ĐỈNH",
            "Thanh toán văn phòng phẩm (VPP)",
            None,
            "VND",
            2
        ),
        (
            "CÔNG TY TNHH TM DV SX GLOBAL LINK",
            "110003019737",
            "VIETINBANK",
            "GLOBAL LINK",
            "Thanh toán phí thủ tục hải quan và vận chuyển HAWB",
            None,
            "VND",
            3
        ),
        (
            "CÔNG TY TNHH YẾN SÀO SONG KIM / TRAN KIM CHI",
            "050131909079",
            "Sacombank - Chi nhánh Bình Dương",
            "SONG KIM",
            "Thanh toán tiền mua quà tặng sự kiện, đối tác",
            None,
            "VND",
            1
        ),
        (
            "CTY TNHH TM TOAN PHU GIAI",
            "1361168168",
            "ACB - PGD HUYNH TAN PHAT",
            "TOÀN PHÚ GIAI",
            "Thanh toán chi phí vé máy bay công tác",
            None,
            "VND",
            2
        ),
        (
            "CÔNG TY TNHH GIAO NHẬN HÀNG HẢI ĐỨC TRƯỜNG THỊNH",
            "53597968",
            "ACB – PGD Nguyễn Biểu",
            "DTT",
            "Thanh toán cước vận chuyển hàng không (Air Freight), phí lưu kho",
            None,
            "VND",
            2
        ),
        (
            "CONG TY TNHH TRẢI NGHIỆM HAHA EXE",
            "77774466",
            "ACB - CN HCM",
            "HAHA EXE",
            "Thanh toán tiền vé máy bay công tác theo hóa đơn",
            None,
            "VND",
            1
        ),
        (
            "CONG TY CO PHAN CONG NGHE OMI",
            "687979887979",
            "ACB - CN HCM",
            "OMI CALL",
            "Thanh toán tổng đài OMI CALL theo hợp đồng",
            None,
            "VND",
            2
        ),
        (
            "CONG TY TNHH A&B VIET NAM",
            "0201000700555",
            "Ngân hàng Vietcombank - CN Hà Tĩnh",
            "A&B",
            "Thanh toán chi phí thi công hệ thống cáp và lắp đặt IoT",
            None,
            "VND",
            3
        ),
        (
            "CÔNG TY TNHH THƯƠNG MẠI DỊCH VỤ CÔNG NGHỆ QUỐC TẾ HẰNG THANH",
            "1039508686",
            "Ngân hàng Vietcombank - Thị trấn Vôi - Lạng Giang – Bắc Giang",
            "HẰNG THANH",
            "Thanh toán theo hợp đồng và phụ lục phát sinh",
            None,
            "VND",
            2
        ),
        (
            "CONG TY TNHH THUONG MAI THINH DAI PHAT",
            "1272036868",
            "VCB - CN BD",
            "THỊNH ĐẠI PHÁT",
            "Thanh toán văn phòng phẩm theo hóa đơn",
            None,
            "VND",
            2
        ),
        (
            "BHXH CO SO TAN DINH",
            "0331009999999",
            "Vietcombank – Chi nhánh Sài Gòn",
            "BHXH TÂN ĐỊNH",
            "Thanh toán bảo hiểm xã hội (BHXH) cho cán bộ nhân viên",
            None,
            "VND",
            4
        )
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO beneficiaries 
        (unit_name, account_number, bank_name, short_name, default_reason, swift_code, currency, usage_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, default_beneficiaries)


def seed_database():
    """Index actual project documents without injecting any mock or dummy contract data."""
    conn = get_db_connection()
    scan_and_index_documents(conn)
    conn.close()


def scan_and_index_documents(conn: sqlite3.Connection):
    """Scans all folders under E:\\Working and indexes their documents with contracts."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents")  # Refresh index

    # Mapping contract codes to contract_id
    cursor.execute("SELECT id, contract_code FROM contracts")
    contract_id_map = {row["contract_code"]: row["id"] for row in cursor.fetchall()}

    scan_directories = [
        # Hồ sơ dự án - Nghiệm thu
        (WORKING_DIR / "Ho So Du An" / "Nghiem Thu", "NGHIEM_THU", "Biên bản nghiệm thu & bàn giao"),
        # Hồ sơ dự án - Yêu cầu thanh toán
        (WORKING_DIR / "Ho So Du An" / "Yeu Cau Thanh Toan", "YEU_CAU_THANH_TOAN", "Đơn yêu cầu thanh toán"),
        # Hồ sơ dự án - Xuất kho
        (WORKING_DIR / "Ho So Du An" / "Xuat Kho", "PHIEU_XUAT_KHO", "Phiếu xuất kho kiêm bàn giao thiết bị"),
        # Hồ sơ dự án - Báo giá
        (WORKING_DIR / "Ho So Du An" / "Bao Gia", "BAO_GIA", "Bảng báo giá thiết bị"),
        # Hồ sơ dự án - Hợp đồng
        (WORKING_DIR / "Ho So Du An" / "Hop Dong", "HOP_DONG", "Hợp đồng mua bán"),
    ]

    for folder_path, doc_type, default_desc in scan_directories:
        if not folder_path.exists():
            continue

        for p in folder_path.glob("*.*"):
            if p.is_dir() or p.name.startswith("~$") or p.suffix.lower() not in (".docx", ".xlsx", ".pdf", ".json", ".doc"):
                continue

            file_name = p.name
            file_path_str = str(p)
            file_size = p.stat().st_size
            file_format = p.suffix.lower().replace(".", "")

            # Heuristic detection of contract code
            matched_code = None
            for code in contract_id_map.keys():
                if code.lower() in file_name.lower():
                    matched_code = code
                    break
            
            # Detect by customer keywords if not matched by code
            if not matched_code:
                fn_lower = file_name.lower()
                if "cx" in fn_lower and "nghiem_thu" in fn_lower:
                    matched_code = "HMV151020250001"
                elif "cx" in fn_lower and "thanh toán" in fn_lower:
                    matched_code = "HMV151020250001"
                elif "phieu_xuat_kho" in fn_lower:
                    matched_code = "HMV021020260001"
                elif "hop_dong" in fn_lower and "bieu mau" not in str(p).lower():
                    matched_code = "HMV021020260001"

            contract_id = contract_id_map.get(matched_code) if matched_code else None

            # Generate friendly document name
            doc_name = file_name.replace("_", " ").rsplit(".", 1)[0]
            description = f"{default_desc} ({matched_code})" if matched_code else default_desc

            cursor.execute("""
                INSERT INTO documents (
                    contract_id, contract_code, doc_type, doc_name, file_name,
                    file_path, file_size, file_format, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contract_id, matched_code, doc_type, doc_name, file_name,
                file_path_str, file_size, file_format, description
            ))

    conn.commit()


# ==========================================================
# PUBLIC QUERY INTERFACES
# ==========================================================

def get_contracts_dossier() -> List[Dict[str, Any]]:
    """Return all contracts with their milestones and linked documents."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM contracts ORDER BY
        CASE 
            WHEN status LIKE '%Đang nghiệm thu%' OR status LIKE '%Chờ%' THEN 1
            WHEN status LIKE '%Đang%' THEN 2
            ELSE 3
        END, signed_date DESC
    """)
    contracts_rows = cursor.fetchall()
    contracts = []

    for c in contracts_rows:
        c_dict = dict(c)
        c_code = c_dict["contract_code"]

        # Fetch milestones
        cursor.execute("""
            SELECT * FROM payment_milestones 
            WHERE contract_code = ? 
            ORDER BY id ASC
        """, (c_code,))
        milestones = [dict(m) for m in cursor.fetchall()]

        # Compute the live deadline only after its own trigger event has been
        # checked off. Before that, the milestone is not late.
        has_urgent = False
        has_waiting = False
        for m in milestones:
            due_str = m.get("due_date")
            days_left = None
            if due_str:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        due_dt = datetime.strptime(due_str, fmt)
                        days_left = (due_dt.date() - SIMULATED_TODAY.date()).days
                        break
                    except ValueError:
                        continue
            m["days_left"] = days_left
            if m.get("status") != "PAID":
                if not m.get("triggered") or not due_str:
                    m["status"] = "PENDING_TRIGGER"
                    m["status_label"] = "Chờ đánh dấu điều kiện"
                elif days_left is not None and days_left < 0:
                    m["status"] = "OVERDUE"
                    m["status_label"] = f"Quá hạn {abs(days_left)} ngày"
                elif days_left is not None and days_left <= 10:
                    m["status"] = "URGENT"
                    m["status_label"] = f"Sắp đến hạn (còn {days_left} ngày)"
                else:
                    m["status"] = "WAITING"
                    m["status_label"] = "Đang chờ thanh toán"
            if m.get("status") in ("URGENT", "OVERDUE"):
                has_urgent = True
            if m.get("status") in ("URGENT", "WAITING"):
                has_waiting = True

        # Fetch linked documents (only documents whose physical files exist on disk)
        cursor.execute("""
            SELECT id, doc_type, doc_name, file_name, file_path, file_size, file_format, description 
            FROM documents 
            WHERE contract_code = ?
            ORDER BY doc_type ASC
        """, (c_code,))
        raw_documents = [dict(d) for d in cursor.fetchall()]
        documents = []
        for d in raw_documents:
            fp_str = d.get("file_path") or ""
            if fp_str and Path(fp_str).is_file():
                try:
                    d["file_size"] = Path(fp_str).stat().st_size
                except Exception:
                    pass
                documents.append(d)

        c_dict["milestones"] = milestones
        c_dict["documents"] = documents
        c_dict["has_urgent"] = has_urgent
        c_dict["has_waiting"] = has_waiting
        c_dict["con_lai"] = max(0, (c_dict["total_amount"] or 0) - (c_dict["paid_amount"] or 0))
        c_dict["ty_le_thu"] = (
            f"{int((c_dict['paid_amount'] / c_dict['total_amount']) * 100)}%"
            if c_dict["total_amount"] and c_dict["paid_amount"]
            else "0%"
        )
        contracts.append(c_dict)

    conn.close()
    return contracts


def get_contract_by_code(contract_code: str) -> Optional[Dict[str, Any]]:
    """Return single contract dossier by code."""
    dossiers = get_contracts_dossier()
    for c in dossiers:
        if c["contract_code"] == contract_code:
            return c
    return None


def activate_payment_milestone(
    milestone_id: int,
    trigger_date: str,
    custom_term_days: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Check off a milestone trigger and derive its due date from its own T/T term."""
    trigger_dt = None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            trigger_dt = datetime.strptime(str(trigger_date).strip(), fmt)
            break
        except ValueError:
            continue
    if trigger_dt is None:
        raise ValueError("Ngày kích hoạt phải có dạng DD/MM/YYYY hoặc YYYY-MM-DD.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    if custom_term_days is not None:
        try:
            term_days = int(custom_term_days)
        except (ValueError, TypeError):
            term_days = int(row["payment_term_days"] or 0)
    else:
        term_days = int(row["payment_term_days"] or 0)

    # Nghiệp vụ thực tế: Đợt 1 ký kết hợp đồng ghi là thanh toán ngay nhưng quy trình duyệt chi của kế toán thường mất khoảng 10 ngày
    if term_days == 0:
        name_lower = str(row["milestone_name"] or "").lower()
        cond_lower = str(row["trigger_condition"] or "").lower()
        if "đợt 1" in name_lower or "ký" in cond_lower or "kí" in cond_lower or "tạm ứng" in cond_lower or "cọc" in cond_lower:
            term_days = 10

    due_dt = trigger_dt + timedelta(days=term_days)
    days_left = (due_dt.date() - SIMULATED_TODAY.date()).days
    if days_left < 0:
        status, label = "OVERDUE", f"Quá hạn {abs(days_left)} ngày"
    elif days_left <= 10:
        status, label = "URGENT", f"Sắp đến hạn (còn {days_left} ngày)"
    else:
        status, label = "WAITING", "Đang chờ thanh toán"

    trigger_text = trigger_dt.strftime("%d/%m/%Y")
    due_text = due_dt.strftime("%d/%m/%Y")
    cursor.execute(
        """
        UPDATE payment_milestones
        SET trigger_date = ?, due_date = ?, payment_term_days = ?, triggered = 1,
            status = ?, status_label = ?
        WHERE id = ?
        """,
        (trigger_text, due_text, term_days, status, label, milestone_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    result = dict(cursor.fetchone())
    result["days_left"] = days_left
    conn.close()
    return result


def reset_payment_milestone(milestone_id: int) -> Optional[Dict[str, Any]]:
    """Reset a milestone back to un-triggered pending state."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    term_days = int(row["payment_term_days"] or 0)
    dot_name = row["milestone_name"]
    action_text = f"Đánh dấu hoàn thành điều kiện {dot_name} để bắt đầu tính T/T {term_days} ngày"

    cursor.execute(
        """
        UPDATE payment_milestones
        SET trigger_date = NULL, due_date = NULL, triggered = 0,
            status = 'PENDING_TRIGGER', status_label = 'Chờ đánh dấu điều kiện',
            action_required = ?
        WHERE id = ?
        """,
        (action_text, milestone_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    result = dict(cursor.fetchone())
    result["days_left"] = None
    conn.close()
    return result


def mark_milestone_paid(
    milestone_id: int,
    paid_date: Optional[str] = None,
    invoice_no: Optional[str] = None,
    actual_amount: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Mark a milestone as paid, update paid date & invoice, and recalculate contract paid total."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    contract_id = row["contract_id"]
    contract_code = row["contract_code"]
    milestone_amount = float(actual_amount if actual_amount is not None else row["amount"])

    if not paid_date:
        paid_date = datetime.now().strftime("%d/%m/%Y")

    inv_no = str(invoice_no).strip() if invoice_no else (row["invoice_no"] or "Chưa xuất")

    cursor.execute("""
        UPDATE payment_milestones
        SET status = 'PAID',
            status_label = 'Đã thu đủ',
            paid_date = ?,
            invoice_no = ?,
            amount = ?,
            action_required = 'Đã hoàn thành thu tiền'
        WHERE id = ?
    """, (paid_date, inv_no, milestone_amount, milestone_id))

    # Recalculate contract total paid amount
    cursor.execute("""
        SELECT SUM(amount) FROM payment_milestones
        WHERE contract_id = ? AND status = 'PAID'
    """, (contract_id,))
    new_paid = float(cursor.fetchone()[0] or 0.0)

    # Check contract total
    cursor.execute("SELECT total_amount, status FROM contracts WHERE id = ?", (contract_id,))
    c_row = cursor.fetchone()
    total_amt = float(c_row["total_amount"] or 0.0)
    current_status = c_row["status"] or ""

    if new_paid >= total_amt and total_amt > 0:
        new_status = "Đã hoàn tất / tất toán 100%"
    elif new_paid > 0 and "đang" not in current_status.lower() and "hoàn tất" not in current_status.lower():
        new_status = "Đang thực hiện (Đã nhận một phần thanh toán)"
    else:
        new_status = current_status

    cursor.execute("""
        UPDATE contracts
        SET paid_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_paid, new_status, contract_id))

    conn.commit()

    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    updated_ms = dict(cursor.fetchone())
    conn.close()
    return {
        "milestone": updated_ms,
        "contract_code": contract_code,
        "new_paid_amount": new_paid,
        "contract_status": new_status,
    }


def unmark_milestone_paid(milestone_id: int) -> Optional[Dict[str, Any]]:
    """Revert a paid milestone back to pending / waiting state and recalculate contract total."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    contract_id = row["contract_id"]
    contract_code = row["contract_code"]
    triggered = row["triggered"]
    due_date = row["due_date"]

    # Calculate days left
    days_left = None
    if due_date:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                due_dt = datetime.strptime(due_date, fmt)
                days_left = (due_dt.date() - SIMULATED_TODAY.date()).days
                break
            except ValueError:
                continue

    if not triggered or not due_date:
        status = "PENDING_TRIGGER"
        status_label = "Chờ đánh dấu điều kiện"
        action_required = f"Đánh dấu hoàn thành điều kiện {row['milestone_name']}"
    elif days_left is not None and days_left < 0:
        status = "OVERDUE"
        status_label = f"Quá hạn {abs(days_left)} ngày"
        action_required = "Đôn đốc thanh toán quá hạn"
    elif days_left is not None and days_left <= 10:
        status = "URGENT"
        status_label = f"Sắp đến hạn (còn {days_left} ngày)"
        action_required = "Gửi đề nghị thanh toán"
    else:
        status = "WAITING"
        status_label = "Đang chờ thanh toán"
        action_required = "Theo dõi hạn thanh toán"

    cursor.execute("""
        UPDATE payment_milestones
        SET status = ?,
            status_label = ?,
            paid_date = NULL,
            action_required = ?
        WHERE id = ?
    """, (status, status_label, action_required, milestone_id))

    # Recalculate contract total paid
    cursor.execute("""
        SELECT SUM(amount) FROM payment_milestones
        WHERE contract_id = ? AND status = 'PAID'
    """, (contract_id,))
    new_paid = float(cursor.fetchone()[0] or 0.0)

    cursor.execute("SELECT total_amount, status FROM contracts WHERE id = ?", (contract_id,))
    c_row = cursor.fetchone()
    current_status = c_row["status"] or ""

    if "hoàn tất" in current_status.lower() and new_paid < float(c_row["total_amount"] or 0):
        new_status = "Đang thực hiện (Chờ thu các đợt tiếp theo)"
    else:
        new_status = current_status

    cursor.execute("""
        UPDATE contracts
        SET paid_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_paid, new_status, contract_id))

    conn.commit()

    cursor.execute("SELECT * FROM payment_milestones WHERE id = ?", (milestone_id,))
    updated_ms = dict(cursor.fetchone())
    conn.close()
    return {
        "milestone": updated_ms,
        "contract_code": contract_code,
        "new_paid_amount": new_paid,
        "contract_status": new_status,
    }


def update_contract_status(
    contract_code: str,
    new_status: str,
    notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update contract operational status and optional notes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contracts WHERE contract_code = ?", (contract_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    if notes is not None:
        cursor.execute("""
            UPDATE contracts
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE contract_code = ?
        """, (new_status.strip(), notes.strip(), contract_code))
    else:
        cursor.execute("""
            UPDATE contracts
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE contract_code = ?
        """, (new_status.strip(), contract_code))

    conn.commit()
    cursor.execute("SELECT * FROM contracts WHERE contract_code = ?", (contract_code,))
    updated_c = dict(cursor.fetchone())
    conn.close()
    return updated_c



def get_all_documents_by_type(doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all indexed documents whose files exist on disk, optionally filtered by type."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if doc_type:
        cursor.execute("SELECT * FROM documents WHERE doc_type = ? ORDER BY id DESC", (doc_type,))
    else:
        cursor.execute("SELECT * FROM documents ORDER BY doc_type ASC, id DESC")
    raw_docs = [dict(d) for d in cursor.fetchall()]
    conn.close()
    docs = []
    for d in raw_docs:
        fp_str = d.get("file_path") or ""
        if fp_str and Path(fp_str).is_file():
            try:
                d["file_size"] = Path(fp_str).stat().st_size
            except Exception:
                pass
            docs.append(d)
    return docs


def index_single_document(
    contract_code: str,
    doc_type: str,
    doc_name: str,
    file_name: str,
    file_path: str,
    file_size: int = 0,
    file_format: str = "docx",
    description: str = "",
    contract_id: Optional[int] = None
) -> int:
    """Index or update a document in the documents table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if not contract_id and contract_code:
        cursor.execute("SELECT id FROM contracts WHERE contract_code = ?", (contract_code,))
        r = cursor.fetchone()
        if r:
            contract_id = r["id"]

    cursor.execute("DELETE FROM documents WHERE contract_code = ? AND file_name = ?", (contract_code, file_name))
    cursor.execute("""
        INSERT INTO documents (
            contract_id, contract_code, doc_type, doc_name, file_name,
            file_path, file_size, file_format, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        contract_id, contract_code, doc_type, doc_name, file_name,
        file_path, file_size, file_format, description
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def delete_document_record_and_file(doc_id: int) -> bool:
    """Delete a single document record from database AND physically delete the file on disk."""
    import logging
    logger = logging.getLogger(__name__)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    fp_str = row["file_path"]
    if fp_str:
        p = Path(fp_str)
        if p.exists() and p.is_file():
            try:
                p.unlink(missing_ok=True)
                logger.info("Deleted physical file on disk: %s", p)
            except Exception as e:
                logger.warning("Could not delete physical file %s: %s", p, e)
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    return True


def delete_contract_dossier(contract_code: str) -> bool:
    """Delete a contract, its milestones, associated document records, AND physical files on disk."""
    import logging
    logger = logging.getLogger(__name__)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM contracts WHERE contract_code = ?", (contract_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    contract_id = row["id"]

    # 1. Fetch physical files linked to this contract and delete them from disk
    cursor.execute("SELECT file_path FROM documents WHERE contract_id = ? OR contract_code = ?", (contract_id, contract_code))
    doc_rows = cursor.fetchall()
    for d in doc_rows:
        try:
            fp_str = d["file_path"]
            if fp_str:
                # SAFEGUARD: Never delete files inside Bieu Mau
                if "bieu mau" in fp_str.lower() or "bieu_mau" in fp_str.lower():
                    logger.warning("SAFEGUARD: Blocked attempt to delete master template: %s", fp_str)
                    continue
                p = Path(fp_str)
                if p.exists() and p.is_file():
                    p.unlink(missing_ok=True)
                    logger.info("Deleted physical file on disk for contract %s: %s", contract_code, p)
        except Exception as err:
            logger.warning("Error deleting file for contract %s: %s", contract_code, err)

    # 2. Delete database records
    cursor.execute("DELETE FROM payment_milestones WHERE contract_id = ? OR contract_code = ?", (contract_id, contract_code))
    cursor.execute("DELETE FROM documents WHERE contract_id = ? OR contract_code = ?", (contract_id, contract_code))
    cursor.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
    conn.commit()
    conn.close()
    return True


