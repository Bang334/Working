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
    assert "BẢNG THEO DÕI CÔNG NỢ DỰ ÁN" in str(ws["A1"].value)
    assert "STT" in str(ws["A3"].value)
    assert "Dự án" in str(ws["B3"].value)
    assert "Khách hàng" in str(ws["C3"].value)


def test_update_status_and_notes():
    """Verify updating collection status and notes on a receivable item."""
    items = list_receivables()
    if not items:
        pytest.skip("No receivables in database to test update.")

    test_item = items[0]
    item_id = test_item["id"]

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
