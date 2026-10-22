"""Automated test suite for Centralized File Manager feature."""

import pytest
import httpx

from app.main import app
from app.services.file_manager_service import (
    CATEGORY_CONFIG,
    decode_file_id,
    delete_file,
    encode_file_id,
    list_all_files,
    rename_file,
)
from app.config import WORKING_DIR


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_list_all_files_service():
    """Kiểm tra service quét danh sách file tập trung."""
    result = list_all_files()
    assert result["status"] == "success"
    assert result["total_files"] > 0
    assert "files" in result
    assert "category_counts" in result
    assert "extension_counts" in result

    # Kiểm tra metadata của 1 file đầu tiên
    first_file = result["files"][0]
    assert "id" in first_file
    assert "file_name" in first_file
    assert "category" in first_file
    assert "file_size_human" in first_file
    assert "icon_type" in first_file
    assert "updated_at_formatted" in first_file


def test_list_files_filter_category():
    """Kiểm tra lọc theo danh mục hợp đồng và biểu mẫu."""
    res_hop_dong = list_all_files(category="hop_dong")
    for f in res_hop_dong["files"]:
        assert f["category"] == "hop_dong"

    res_bieu_mau = list_all_files(category="bieu_mau")
    for f in res_bieu_mau["files"]:
        assert f["category"] == "bieu_mau"


def test_list_files_filter_extension():
    """Kiểm tra lọc theo định dạng Word và Excel."""
    res_word = list_all_files(extension="word")
    for f in res_word["files"]:
        assert f["file_ext"] in ("docx", "doc")

    res_excel = list_all_files(extension="excel")
    for f in res_excel["files"]:
        assert f["file_ext"] in ("xlsx", "xls", "csv")


def test_list_files_search():
    """Kiểm tra tìm kiếm từ khóa."""
    result = list_all_files(search="CX")
    assert result["status"] == "success"
    for f in result["files"]:
        name_or_cat = (f["file_name"] + f["category_label"] + f["folder_name"]).lower()
        assert "cx" in name_or_cat


def test_file_id_encode_decode_safety():
    """Kiểm tra mã hóa và giải mã an toàn file_id, chống path traversal."""
    test_path = WORKING_DIR / "Ho So Du An" / "Hop Dong"
    if test_path.exists():
        files = list(test_path.glob("*.*"))
        if files:
            p = files[0]
            fid = encode_file_id(p)
            decoded = decode_file_id(fid)
            assert decoded.resolve() == p.resolve()

    # Kiểm tra giải mã chuỗi độc hại thoát khỏi thư mục
    with pytest.raises(Exception):
        decode_file_id("Li4vLi4vLi4vd2luZG93cy9zeXN0ZW0zMg==")


def test_protect_template_from_deletion():
    """Kiểm tra cơ chế bảo vệ: Không cho phép xóa hoặc đổi tên file Biểu Mẫu Gốc."""
    res_bieu_mau = list_all_files(category="bieu_mau")
    if res_bieu_mau["files"]:
        bm_file = res_bieu_mau["files"][0]
        with pytest.raises(PermissionError):
            delete_file(bm_file["id"])

        with pytest.raises(PermissionError):
            rename_file(bm_file["id"], "new_name.xlsx")


@pytest.mark.anyio
async def test_file_manager_view_page():
    """Kiểm tra trang web GET /files render thành công."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/files")
        assert resp.status_code == 200
        assert "Quản Lý Hồ Sơ & File" in resp.text
        assert "filemgr-workspace" in resp.text


@pytest.mark.anyio
async def test_file_manager_api_list():
    """Kiểm tra API GET /api/v1/files trả về danh sách đầy đủ."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["total_files"] > 0
        assert len(data["files"]) > 0


@pytest.mark.anyio
async def test_file_manager_api_download():
    """Kiểm tra API tải file hợp lệ."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        list_resp = await client.get("/api/v1/files?limit=1")
        data = list_resp.json()
        first_file = data["files"][0]
        fid = first_file["id"]

        dl_resp = await client.get(f"/api/v1/files/download/{fid}")
        assert dl_resp.status_code == 200
        assert "content-disposition" in dl_resp.headers


@pytest.mark.anyio
async def test_file_manager_api_open_endpoints_validation():
    """Kiểm tra validation khi gọi API mở file và mở explorer."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Thiếu file_id
        resp_file = await client.post("/api/v1/files/open-file", json={})
        assert resp_file.status_code == 400

        resp_exp = await client.post("/api/v1/files/open-explorer", json={})
        assert resp_exp.status_code == 400

