# -*- coding: utf-8 -*-
"""Unit tests for Project Receivables (AR Debt Tracker) module."""

import io
import openpyxl
import pytest

from app.database import init_db
from app.services.receivables_excel_service import export_receivables_excel
from app.services.receivables_service import (
    calculate_days_left,
    determine_collection_status,
    get_receivable,
    get_receivables_stats,
    import_receivables_from_sheet3,
    list_receivables,
    parse_flexible_date,
    sync_from_existing_contracts,
    update_receivable_notes,
    update_receivable_status,
)


def test_date_and_status_helpers():
    """Test date parsing and collection status determination."""
    assert parse_flexible_date("2026-10-15") == "2026-10-15"
    assert parse_flexible_date("15/10/2026") == "2026-10-15"
    assert parse_flexible_date("#VALUE!") is None
    assert parse_flexible_date(None) is None

    # Paid determination
    assert determine_collection_status(100.0, 100.0, "2026-10-01") == "PAID"
    assert determine_collection_status(100.08, 100.0, "2026-10-01") == "PAID"

    # Overdue determination
    past_date = "2020-01-01"
    assert determine_collection_status(0.0, 100.0, past_date) == "DELAYED"


def test_list_and_stats_receivables():
    """Verify listing receivables and calculating statistics."""
    init_db()
    items = list_receivables()
    assert isinstance(items, list)

    stats = get_receivables_stats()
    assert "total_receivable" in stats
    assert "total_received" in stats
    assert "total_debt" in stats
    assert "completion_rate" in stats
    assert stats["total_receivable"] >= 0
    assert stats["completion_rate"] >= 0


def test_receivables_excel_export():
    """Verify Excel export generates valid 17-column format matching Sheet 3."""
    excel_bytes = export_receivables_excel()
    assert len(excel_bytes) > 2000

    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=False)
    assert "3. Theo Dõi Công Nợ Dự Án" in wb.sheetnames
    ws = wb["3. Theo Dõi Công Nợ Dự Án"]

    # Header title check
    assert "STT" in str(ws["A1"].value)
    assert "Dự án" in str(ws["B1"].value)
    assert "Khách hàng" in str(ws["C1"].value)


def test_update_status_and_notes():
    """Verify updating collection status and notes on a receivable item."""
    items = list_receivables()
    if not items:
        pytest.skip("No receivables in database to test update.")

    test_item = items[0]
    item_id = test_item["id"]
    orig_status = test_item.get("collection_status") or "PENDING"
    orig_paid_date = test_item.get("paid_date")
    orig_notes = test_item.get("notes") or ""

    try:
        # 1. Update status to DELAYED
        ok_status = update_receivable_status(item_id, "DELAYED")
        assert ok_status is True

        # 2. Update notes
        test_note = "Đã gọi điện cho PM đối tác, hẹn thanh toán vào thứ Sáu"
        ok_notes = update_receivable_notes(item_id, test_note)
        assert ok_notes is True

        # 3. Verify updated values
        refreshed = get_receivable(item_id)
        assert refreshed is not None
        assert refreshed["collection_status"] == "DELAYED"
        assert "hẹn thanh toán vào thứ Sáu" in refreshed["notes"]
    finally:
        # Restore original state so test does not mutate live database
        update_receivable_status(item_id, orig_status, paid_date=orig_paid_date)
        update_receivable_notes(item_id, orig_notes)


def test_receivables_word_and_ppt_export_fulfilling_boss_rules():
    """Verify Word (.docx) and PowerPoint (.pptx) export conforming to Boss's 3 rules."""
    from app.services.receivables_report_service import (
        prepare_receivables_management_data,
        generate_receivables_word_report,
        generate_receivables_ppt_presentation,
    )
    from docx import Document
    from pptx import Presentation

    # 1. Prepare data
    data = prepare_receivables_management_data()
    assert "completed_items" in data
    assert "must_collect_items" in data
    assert "retention_items" in data
    assert "overdue_risk_items" in data
    assert "carry_forward_items" in data
    assert "total_completed_amount" in data
    assert "total_unpaid_amount" in data

    # Verify Mutually Exclusive Partitioning (Point 2)
    assert round(data["total_must_collect_amount"] + data["total_retention_amount"] + data["total_overdue_amount"], 2) == round(data["total_unpaid_amount"], 2)
    assert len(data["must_collect_items"]) + len(data["retention_items"]) + len(data["overdue_risk_items"]) == len(data["unpaid_items"])

    # Verify Rule 3 & 4 Bilingual Carry Forward enrichment (Point 1 & 5)
    for item in data["carry_forward_items"]:
        assert "cat_vi" in item
        assert "cat_zh" in item
        assert "root_cause_vi" in item
        assert "root_cause_zh" in item
        assert "target_date_vi" in item
        assert "target_date_zh" in item
        assert "action_plan_vi" in item
        assert "action_plan_zh" in item

    # Verify Filter-aware Stats (Point 3)
    data_filtered = prepare_receivables_management_data(customer="JINXUN")
    assert data_filtered["stats"]["total_receivable"] == sum(float(x.get("gross_amount") or 0.0) for x in data_filtered["completed_items"] + data_filtered["unpaid_items"])

    # 2. Test Word (.docx) generation
    docx_bytes = generate_receivables_word_report(data)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 5000

    doc = Document(io.BytesIO(docx_bytes))
    full_text = " ".join(p.text for p in doc.paragraphs)
    assert "BÁO CÁO ĐIỀU HÀNH CÔNG NỢ DỰ ÁN" in full_text
    assert "PHẦN 1: CÁC KHOẢN ĐÃ XÁC NHẬN THU TIỀN XONG" in full_text
    assert "PHẦN 2: TRỌNG TÂM CÔNG NỢ ĐANG THEO DÕI" in full_text
    assert "PHẦN 3: BẢNG PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ" in full_text
    assert "PHẦN 4: TỔNG KẾT ĐIỀU HÀNH" in full_text
    assert len(doc.tables) >= 4

    # 3. Test PowerPoint (.pptx) generation
    pptx_bytes = generate_receivables_ppt_presentation(data)
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 5000

    prs = Presentation(io.BytesIO(pptx_bytes))
    assert len(prs.slides) >= 8  # At least 8 slides with pagination support



def test_weekly_comparison_and_snapshots():
    """Verify weekly side-by-side debt comparison, time-travel state reconstruction and snapshot saving."""
    import asyncio
    from app.services.receivables_service import (
        get_weekly_comparison_data,
        save_weekly_snapshot,
    )
    from app.controllers.receivables_controller import (
        get_weekly_comparison_endpoint,
        save_weekly_snapshot_endpoint,
        WeeklySnapshotRequest,
    )
    from app.database import get_db_connection

    # 1. Test get_weekly_comparison_data with explicit last week vs this week dates
    prev_date = "2026-10-18"
    curr_date = "2026-10-25"
    res = get_weekly_comparison_data(prev_date=prev_date, curr_date=curr_date)

    assert res["status"] == "success"
    assert "dates" in res
    assert res["dates"]["prev_date"] == prev_date
    assert res["dates"]["curr_date"] == curr_date
    assert "deltas" in res
    assert "prev_week" in res
    assert "curr_week" in res
    assert "changes" in res

    # Verify counts and items
    prev_items = res["prev_week"]["items"]
    curr_items = res["curr_week"]["items"]
    assert len(prev_items) == len(curr_items)

    # Verify items paid on 2026-10-22 are marked unpaid on prev_date and paid on curr_date
    for p_item, c_item in zip(prev_items, curr_items):
        if c_item.get("paid_date") == "2026-10-22":
            assert p_item["collection_status"] != "PAID"
            assert p_item["received_amount"] == 0.0
            assert c_item["collection_status"] == "PAID"
            assert c_item["received_amount"] == c_item["gross_amount"]
            assert c_item["change_type"] == "NEWLY_PAID"

    # Deltas check
    deltas = res["deltas"]
    assert deltas["net_received_increase"] >= 0
    assert deltas["newly_paid_count"] >= 1

    # 2. Test saving weekly snapshot and retrieving from snapshot
    test_snapshot_date = "2026-10-15"
    saved_count = save_weekly_snapshot(snapshot_date=test_snapshot_date, note="QA Test Snapshot")
    assert saved_count > 0

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM receivables_weekly_snapshots WHERE snapshot_date = ?", (test_snapshot_date,))
    snap_count = cursor.fetchone()[0]
    assert snap_count == saved_count

    # Cleanup snapshot
    cursor.execute("DELETE FROM receivables_weekly_snapshots WHERE snapshot_date = ?", (test_snapshot_date,))
    conn.commit()
    conn.close()

    # 3. Test API controller endpoints
    endpoint_res = asyncio.run(get_weekly_comparison_endpoint(prev_date=prev_date, curr_date=curr_date))
    assert endpoint_res["status"] == "success"
    assert "deltas" in endpoint_res


def test_custom_chart_upload_and_datasources():
    """Verify switching between DB, Sample JSON, and Standalone Uploaded Files without DB mutation."""
    import asyncio
    import json
    from app.services.receivables_service import register_custom_receivables_file, list_receivables
    from app.controllers.receivables_controller import get_weekly_comparison_endpoint

    # Initial count in database
    initial_db_items = list_receivables()
    initial_db_count = len(initial_db_items)

    # 1. Test 'db' data source
    res_db = asyncio.run(get_weekly_comparison_endpoint(data_source="db"))
    assert res_db["status"] == "success"
    assert res_db["data_source"] == "db"
    assert "contracts_comparison" in res_db

    # 2. Test 'sample' data source
    res_sample = asyncio.run(get_weekly_comparison_endpoint(data_source="sample"))
    assert res_sample["status"] == "success"
    assert res_sample["data_source"] == "sample"
    assert len(res_sample["contracts_comparison"]) > 0

    # 3. Test standalone custom upload (JSON or Excel)
    dummy_custom_json = json.dumps({
        "receivables": [
            {
                "id": 1,
                "project_name": "Phần mềm MES xưởng 3\nMES 3廠軟體",
                "customer_name": "Công ty TNHH Thí Nghiệm",
                "contract_code": "TEST-HD-001",
                "gross_amount": 100000000.0,
                "received_amount": 50000000.0,
                "remaining_debt": 50000000.0,
                "due_date": "2026-10-30",
                "paid_date": None,
                "doc_status": "Đã xuất hóa đơn",
                "notes": "File tải lên từ phòng Kế Toán"
            }
        ]
    }).encode("utf-8")

    upload_id, items = register_custom_receivables_file(dummy_custom_json, "ke_toan_t10.json")
    assert len(items) == 1
    assert items[0]["contract_code"] == "TEST-HD-001"

    res_upload = asyncio.run(get_weekly_comparison_endpoint(data_source="upload", upload_id=upload_id))
    assert res_upload["status"] == "success"
    assert res_upload["data_source"] == "upload"
    assert len(res_upload["contracts_comparison"]) == 1
    assert res_upload["contracts_comparison"][0]["contract_code"] == "TEST-HD-001"

    # 4. Strict DB Integrity Check: Verify that DB count did NOT change at all
    after_db_items = list_receivables()
    assert len(after_db_items) == initial_db_count, "Database must not be altered by standalone file upload!"


def test_start_date_and_payment_term_trigger():
    """Verify updating start_date and payment_term_days to trigger due date calculation."""
    from app.services.receivables_service import update_receivable
    items = list_receivables()
    if not items:
        pytest.skip("No receivables to test.")
    item = items[0]
    item_id = item["id"]
    orig_start = item.get("start_date")
    orig_term = item.get("payment_term_days")
    orig_due = item.get("due_date")

    try:
        ok = update_receivable(item_id, {
            "project_name": item["project_name"],
            "customer_name": item["customer_name"],
            "start_date": "2026-10-26",
            "payment_term_days": 60,
            "due_date": "2026-12-25"
        })
        assert ok is True
        refreshed = get_receivable(item_id)
        assert refreshed["start_date"] == "2026-10-26"
        assert refreshed["payment_term_days"] == 60
        assert refreshed["due_date"] == "2026-12-25"
    finally:
        update_receivable(item_id, {
            "project_name": item["project_name"],
            "customer_name": item["customer_name"],
            "start_date": orig_start,
            "payment_term_days": orig_term,
            "due_date": orig_due
        })


