# -*- coding: utf-8 -*-
"""Test suite for Procurement & Supplier PO Tracker module."""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from pathlib import Path

# Setup paths
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import openpyxl
from app.database import init_db, get_db_connection
from app.services.procurement_service import (
    bulk_import_procurement_orders,
    create_procurement_order,
    delete_all_procurement_orders,
    delete_procurement_order,
    get_procurement_order,
    get_procurement_stats,
    list_procurement_orders,
    update_procurement_order,
    update_procurement_order_notes,
    update_procurement_order_status,
)
from app.services.procurement_excel_service import (
    export_procurement_excel,
    parse_procurement_excel,
)


def test_procurement_flow():
    print(">>> 1. Khởi tạo Database...")
    init_db()

    print(">>> 2. Xóa sạch dữ liệu test...")
    delete_all_procurement_orders()

    print(">>> 3. Tạo một đơn mua hàng mới...")
    new_id = create_procurement_order({
        "order_no": 1,
        "project_name": "Seiyo / 正揚",
        "category": "Hệ thống",
        "item_name": "3 PCS ADAM",
        "quantity": 3,
        "customer_company": "SEIYO / 正揚",
        "supplier_name": "Advantech",
        "order_date": "2026-07-31",
        "eta_date": "2026-08-10",
        "actual_delivery_date": "2026-08-12",
        "supplier_payment_status": "Đã thanh toán",
        "shipping_notes": "Đã giao",
    })
    assert new_id > 0, "Không thể tạo đơn hàng"

    fetched = get_procurement_order(new_id)
    assert fetched is not None, "Không tìm thấy đơn vừa tạo"
    assert fetched["item_name"] == "3 PCS ADAM"
    assert fetched["delivery_status"] == "DELIVERED"
    print(f"    [OK] Đã tạo đơn #{new_id}: {fetched['item_name']} - Trạng thái: {fetched['delivery_status_label']}")

    print(">>> 4. Cập nhật đơn mua hàng...")
    update_success = update_procurement_order(new_id, {
        "shipping_notes": "Đã giao hàng và bàn giao cho kỹ thuật"
    })
    assert update_success, "Lỗi cập nhật đơn hàng"
    updated = get_procurement_order(new_id)
    assert "bàn giao" in updated["shipping_notes"]
    print("    [OK] Cập nhật ghi chú thành công")

    print(">>> 4.1. Test inline update_procurement_order_notes...")
    notes_ok = update_procurement_order_notes(new_id, "Ghi chú rủi ro test inline")
    assert notes_ok
    assert get_procurement_order(new_id)["shipping_notes"] == "Ghi chú rủi ro test inline"
    print("    [OK] update_procurement_order_notes thành công")

    print(">>> 4.2. Test inline update_procurement_order_status...")
    status_ok = update_procurement_order_status(new_id, "DELAYED")
    assert status_ok
    delayed_order = get_procurement_order(new_id)
    assert delayed_order["delivery_status"] == "DELAYED"
    assert "Trễ" in delayed_order["delivery_status_label"]
    print(f"    [OK] update_procurement_order_status sang DELAYED: {delayed_order['delivery_status_label']}")

    status_deliv = update_procurement_order_status(new_id, "DELIVERED")
    assert status_deliv
    deliv_order = get_procurement_order(new_id)
    assert deliv_order["delivery_status"] == "DELIVERED"
    print(f"    [OK] update_procurement_order_status sang DELIVERED: {deliv_order['delivery_status_label']}")

    print(">>> 5. Test parse file Excel thực tế 'QLDA_TRANG_PM_2026 (1).xlsx'...")
    excel_path = Path(r"C:\Users\BANG\Downloads\QLDA_TRANG_PM_2026 (1).xlsx")
    if excel_path.exists():
        parsed_orders, meta = parse_procurement_excel(str(excel_path))
        print(f"    [OK] Đã đọc Sheet '{meta['sheet_name']}': {len(parsed_orders)} dòng hợp lệ.")
        assert len(parsed_orders) >= 15, f"Kỳ vọng >= 15 dòng, thực tế {len(parsed_orders)}"

        print(">>> 6. Test import toàn bộ vào database...")
        imported_count = bulk_import_procurement_orders(parsed_orders, overwrite=True)
        print(f"    [OK] Đã import thành công {imported_count} đơn hàng vào SQLite.")

        stats = get_procurement_stats()
        print(f"    [OK] Thống kê: Tổng {stats['total_orders']} | Đã giao {stats['delivered_count']} | Đang giao {stats['in_transit_count']} | Chờ TT {stats['pending_payment_count']}")
        print(f"    [OK] Danh sách NCC: {stats['suppliers']}")

        print(">>> 7. Test xuất file Excel...")
        all_orders = list_procurement_orders()
        excel_buf = export_procurement_excel(all_orders)
        excel_bytes = excel_buf.getvalue()
        assert len(excel_bytes) > 5000, "File Excel xuất ra quá nhỏ"
        print(f"    [OK] Đã xuất file Excel theo dõi ({len(excel_bytes):,} bytes).")
    else:
        print(f"    [SKIP] File Excel không tồn tại tại {excel_path}")

    # Giữ nguyên dữ liệu không xóa sạch sau test để người dùng sử dụng tiếp
    stats = get_procurement_stats()
    assert stats["total_orders"] > 0
    print(f"    [OK] Đã kiểm tra cơ sở dữ liệu: {stats['total_orders']} đơn hàng sẵn sàng!")

    print("\n==========================================")
    print("   TẤT CẢ CÁC BÀI TEST ĐÃ VƯỢT QUA 100%!")
    print("==========================================")


def test_procurement_chart():
    from app.services.procurement_chart_service import get_procurement_chart_data

    chart_data = get_procurement_chart_data()
    assert chart_data["status"] == "success"
    assert "kpi" in chart_data
    assert "projects_readiness" in chart_data
    assert "timeline_analysis" in chart_data
    assert len(chart_data["projects_readiness"]) > 0

    p0 = chart_data["projects_readiness"][0]
    assert "project_name_vi" in p0
    assert "readiness_pct" in p0
    assert "segments" in p0
    assert len(p0["segments"]) > 0

    s0 = p0["segments"][0]
    assert "item_name" in s0
    assert "color_class" in s0
    assert "supplier_name" in s0
    print(f"    [OK] test_procurement_chart: {len(chart_data['projects_readiness'])} dự án, KPI: {chart_data['kpi']['overall_readiness_pct']}%")


if __name__ == "__main__":
    test_procurement_flow()
    test_procurement_chart()

