"""Unit and integration tests for custom personal reminders and task scheduling."""

import os
import sys
import io
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


def test_custom_reminder_crud_service():
    """Test full CRUD lifecycle of a custom reminder in service layer."""
    today_str = date.today().strftime("%Y-%m-%d")

    # 1. Create reminder
    created = create_custom_reminder(
        title="Gửi file báo giá cập nhật cho khách CX",
        due_date=today_str,
        description="Gửi anh Trương xem trước 3 phương án",
        due_time="09:30",
        priority="HIGH",
        category="CUSTOMER_FILE",
        file_bytes=b"Mock Excel Content 12345",
        file_name="Bao_Gia_Test.xlsx",
    )
    assert created["status"] == "success"
    rem_id = created["reminder_id"]
    assert rem_id > 0
    assert created["attachment_name"] == "Bao_Gia_Test.xlsx"

    # 2. List reminders and check stats
    res = get_custom_reminders_list()
    assert res["status"] == "success"
    reminders = res["reminders"]
    found = next((r for r in reminders if r["id"] == rem_id), None)
    assert found is not None
    assert found["title"] == "Gửi file báo giá cập nhật cho khách CX"
    assert found["is_today"] is True
    assert found["due_date_formatted"] is not None
    assert "Thứ" in found["due_date_formatted"] or "Chủ Nhật" in found["due_date_formatted"]
    assert res["stats"]["today"] >= 1

    # 3. Toggle status to COMPLETED
    toggled = toggle_custom_reminder_status(rem_id)
    assert toggled["status"] == "success"
    assert toggled["new_status"] == "COMPLETED"

    # 4. Update reminder
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    updated = update_custom_reminder(
        reminder_id=rem_id,
        title="Gửi file báo giá (Đã dời sang ngày mai)",
        due_date=tomorrow_str,
        priority="URGENT",
    )
    assert updated["status"] == "success"

    # 5. Verify update
    res2 = get_custom_reminders_list()
    found2 = next((r for r in res2["reminders"] if r["id"] == rem_id), None)
    assert found2 is not None
    assert found2["title"] == "Gửi file báo giá (Đã dời sang ngày mai)"
    assert found2["priority"] == "URGENT"

    # 6. Delete reminder
    deleted = delete_custom_reminder(rem_id, delete_file=True)
    assert deleted is True

    # 7. Verify deletion
    res3 = get_custom_reminders_list()
    found3 = next((r for r in res3["reminders"] if r["id"] == rem_id), None)
    assert found3 is None


def test_custom_reminder_api_endpoints():
    """Test HTTP API endpoints for custom reminders."""
    next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    # POST create
    file_content = b"Dummy contract attachment text"
    files = {"file": ("Hop_Dong_Dinh_Kem.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {
        "title": "Thứ 2 gửi hợp đồng ký số cho công ty Vonmax",
        "due_date": next_week,
        "due_time": "14:00",
        "description": "Lưu ý kiểm tra lại điều khoản tạm ứng 35%",
        "priority": "NORMAL",
        "category": "CUSTOMER_FILE",
    }
    resp = client.post("/api/v1/custom-reminders", data=data, files=files)
    assert resp.status_code == 200, resp.text
    resp_data = resp.json()
    rem_id = resp_data["reminder_id"]
    assert rem_id > 0

    try:
        # GET list
        list_resp = client.get("/api/v1/custom-reminders")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["status"] == "success"
        assert any(r["id"] == rem_id for r in list_data["reminders"])

        # GET download attachment
        dl_resp = client.get(f"/api/v1/custom-reminders/{rem_id}/download")
        assert dl_resp.status_code == 200
        assert dl_resp.content == file_content

        # PATCH toggle
        toggle_resp = client.patch(f"/api/v1/custom-reminders/{rem_id}/toggle")
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["new_status"] == "COMPLETED"

        # GET project files
        proj_files_resp = client.get("/api/v1/custom-reminders/project-files")
        assert proj_files_resp.status_code == 200
        assert "files" in proj_files_resp.json()

    finally:
        # DELETE cleanup
        del_resp = client.delete(f"/api/v1/custom-reminders/{rem_id}?delete_file=true")
        assert del_resp.status_code == 200
