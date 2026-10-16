"""Unit and integration tests for custom personal reminders, dedicated folders, and multi-file attachments."""

import os
import sys
import io
import json
import asyncio
from datetime import date, timedelta
from pathlib import Path
import pytest
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.main import app
from app.services.custom_reminder_service import (
    create_custom_reminder,
    delete_custom_reminder,
    get_custom_reminders_list,
    get_sidebar_due_stats,
    toggle_custom_reminder_status,
    update_custom_reminder,
)


class ASGITestClient:
    """Facade for test client using httpx.ASGITransport."""

    @staticmethod
    async def _request(method, url, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as async_client:
            return await async_client.request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return asyncio.run(self._request("GET", url, **kwargs))

    def post(self, url, **kwargs):
        return asyncio.run(self._request("POST", url, **kwargs))

    def patch(self, url, **kwargs):
        return asyncio.run(self._request("PATCH", url, **kwargs))

    def delete(self, url, **kwargs):
        return asyncio.run(self._request("DELETE", url, **kwargs))


client = ASGITestClient()


def test_custom_reminder_dedicated_folder_and_multi_files():
    """Test creating reminder with dedicated folder, multiple files, images, and deletion options."""
    today_str = date.today().strftime("%Y-%m-%d")

    # 1. Create reminder with multiple uploaded files (including an image)
    uploaded = [
        ("bang_gia_dich_vu.xlsx", b"Excel content for pricing"),
        ("so_do_lap_dat.png", b"\x89PNG\r\n\x1a\nMock PNG Data"),
    ]
    created = create_custom_reminder(
        title="Gửi báo giá và sơ đồ lắp đặt cho CX Tech",
        due_date=today_str,
        description="Gửi anh Trương bản báo giá kèm sơ đồ nhà xưởng",
        due_time="10:00",
        priority="HIGH",
        category="CUSTOMER_FILE",
        uploaded_files=uploaded,
    )
    assert created["status"] == "success"
    rem_id = created["reminder_id"]
    folder_path = Path(created["folder_path"])

    # Dedicated folder must exist on disk!
    assert folder_path.exists() and folder_path.is_dir()
    assert (folder_path / "bang_gia_dich_vu.xlsx").is_file()
    assert (folder_path / "so_do_lap_dat.png").is_file()

    # 2. Check query list
    res = get_custom_reminders_list()
    assert res["status"] == "success"
    found = next((r for r in res["reminders"] if r["id"] == rem_id), None)
    assert found is not None
    assert found["attachments_count"] == 2
    assert len(found["attachments_list"]) == 2
    # One of them is image
    img_item = next((a for a in found["attachments_list"] if a["ext"] == "png"), None)
    assert img_item is not None
    assert img_item["is_image"] is True

    # 3. Test due count for sidebar
    sidebar_stats = get_sidebar_due_stats()
    assert sidebar_stats["status"] == "success"
    assert sidebar_stats["today_count"] >= 1
    assert sidebar_stats["has_due"] is True

    # 4. Delete with delete_files=False (keep files on disk)
    deleted_keep = delete_custom_reminder(rem_id, delete_files=False)
    assert deleted_keep is True
    # Folder and files should still exist on disk!
    assert folder_path.exists()
    assert (folder_path / "bang_gia_dich_vu.xlsx").is_file()

    # Now clean up folder on disk manually for test hygiene
    import shutil
    shutil.rmtree(folder_path, ignore_errors=True)
    assert not folder_path.exists()


def test_custom_reminder_api_endpoints_and_delete_with_files():
    """Test HTTP API endpoints including multi-file, preview, download, and delete_files=True."""
    today_str = date.today().strftime("%Y-%m-%d")

    # POST create via API
    png_bytes = b"\x89PNG\r\n\x1a\nMock PNG Test Image"
    files = [
        ("files", ("anh_chup_thiet_bi.png", io.BytesIO(png_bytes), "image/png")),
        ("files", ("huong_dan.txt", io.BytesIO(b"Test text file"), "text/plain")),
    ]
    data = {
        "title": "Thứ 2 gửi ảnh chụp thiết bị và hướng dẫn sử dụng",
        "due_date": today_str,
        "due_time": "14:00",
        "description": "Nhớ gửi ảnh trước 15h",
        "priority": "URGENT",
        "category": "CUSTOMER_FILE",
    }
    resp = client.post("/api/v1/custom-reminders", data=data, files=files)
    assert resp.status_code == 200, resp.text
    resp_data = resp.json()
    rem_id = resp_data["reminder_id"]
    folder_path = Path(resp_data["folder_path"])
    assert folder_path.exists()

    try:
        # GET sidebar due-count
        due_resp = client.get("/api/v1/custom-reminders/due-count")
        assert due_resp.status_code == 200
        due_data = due_resp.json()
        assert due_data["today_count"] >= 1

        # GET download attachment 0 (png)
        dl_resp = client.get(f"/api/v1/custom-reminders/{rem_id}/attachments/0/download")
        assert dl_resp.status_code == 200
        assert dl_resp.content == png_bytes

        # GET preview attachment 0 (inline png)
        prev_resp = client.get(f"/api/v1/custom-reminders/{rem_id}/attachments/0/preview")
        assert prev_resp.status_code == 200
        assert "image/png" in prev_resp.headers.get("content-type", "")

        # PATCH toggle
        toggle_resp = client.patch(f"/api/v1/custom-reminders/{rem_id}/toggle")
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["new_status"] == "COMPLETED"

    finally:
        # DELETE with delete_files=true (deletes folder and files automatically)
        del_resp = client.delete(f"/api/v1/custom-reminders/{rem_id}?delete_files=true")
        assert del_resp.status_code == 200
        # Dedicated folder must be deleted!
        assert not folder_path.exists()


def test_vietnam_timezone_enforcement():
    """Verify strict adherence to Vietnam Standard Time (ICT / GMT+7 / UTC+7 / Asia/Ho_Chi_Minh)."""
    from datetime import datetime, timezone, timedelta
    from app.services.time_utils import (
        VIETNAM_TZ,
        get_vietnam_now,
        get_vietnam_today,
        get_vietnam_today_str,
        get_vietnam_time_str,
        get_day_of_week_vi,
        format_due_string_vn,
    )

    # 1. Check exact offset (+07:00 = 25200 seconds)
    offset = VIETNAM_TZ.utcoffset(None)
    assert offset == timedelta(hours=7)
    assert offset.total_seconds() == 7 * 3600

    # 2. Check get_vietnam_now() matches UTC + 7 hours
    utc_now = datetime.now(timezone.utc)
    vn_now = get_vietnam_now()
    # The absolute timestamp (seconds since epoch) must match within 1 second
    assert abs(vn_now.timestamp() - utc_now.timestamp()) < 2.0
    # The hour in Vietnam should be (utc_hour + 7) % 24
    expected_hour = (utc_now.hour + 7) % 24
    assert vn_now.hour == expected_hour

    # 3. Check get_vietnam_today() returns correct date
    vn_today = get_vietnam_today()
    assert get_vietnam_today_str() == vn_today.strftime("%Y-%m-%d")

    # 4. Check weekday name in Vietnamese
    sample_monday = date(2026, 10, 19) # 2026-10-19 is a Monday
    assert get_day_of_week_vi(sample_monday) == "Thứ Hai"
    sample_sunday = date(2026, 10, 18)
    assert get_day_of_week_vi(sample_sunday) == "Chủ Nhật"

    # 5. Check format_due_string_vn calculations
    today_str = get_vietnam_today_str()
    # Future appointment today (at 23:59)
    res_today = format_due_string_vn(today_str, "23:59")
    assert res_today[3] is True  # is_today
    assert res_today[4] is False # is_overdue (time has not passed)

    # Yesterday appointment
    yesterday_str = (vn_today - timedelta(days=1)).strftime("%Y-%m-%d")
    res_yest = format_due_string_vn(yesterday_str, "09:00")
    assert res_yest[2] == -1    # days_diff = -1
    assert res_yest[4] is True  # is_overdue
    assert "Quá hạn 1 ngày" in res_yest[1]


def test_sidebar_customizer_markup():
    """Verify that sidebar customizer markup, CSS, JS, and data-nav-id attributes are present."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "sidebar_customizer.css" in html
    assert "sidebar_customizer.js" in html
    assert 'data-nav-id="quotations"' in html
    assert 'data-nav-id="contracts"' in html
    assert 'data-nav-id="dashboard"' in html
    assert 'data-section-id="project_flow"' in html
    assert "scModalOverlay" in html
    assert "btnOpenSidebarCustomizer" in html


