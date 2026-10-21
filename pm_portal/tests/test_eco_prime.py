"""Automated test suite for ECO PRIME Quotation and AI Schematic feature."""

import io
import openpyxl
import pytest
import httpx

from app.main import app
from app.models.eco_prime_models import EcoPrimeItem, EcoPrimeQuotationData
from app.services.eco_prime.eco_prime_excel_service import generate_eco_prime_excel


@pytest.fixture
def anyio_backend():
    return 'asyncio'



@pytest.mark.anyio
async def test_eco_prime_sample_data_endpoint():
    """Kiểm tra endpoint sample-data trả về đúng 7 hạng mục (PW gộp vào CC2051) và dữ liệu Pou Hui."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/eco-prime/sample-data")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        quote = data["data"]
        assert quote["customer_name"] == "CÔNG TY TNHH VIỆT NAM PHỔ HUỆ Y TẾ CÔNG NGHỆ (POU HUI)"
        assert len(quote["items"]) == 7

        # Kiểm tra Gateway CC2051 gộp chung bộ nguồn PW có số lượng là 1 bộ
        gw = [it for it in quote["items"] if "CC2051" in it["name"]][0]
        assert gw["qty"] == 1
        assert "電源" in gw["name"] or "nguồn" in gw["name"]


def test_eco_prime_excel_generation():
    """Kiểm tra service tạo file Excel chuẩn 1:1 từ phôi mẫu gốc."""
    items = [
        EcoPrimeItem(stt=1, name="Đồng hồ PM210-4-V\nPM210-4-V", category="Đồng hồ\n電表", desc="Desc 1", qty=4, unit="BỘ", tax_rate=0.0),
        EcoPrimeItem(stt=2, name="Biến dòng CT-1000RV\nCT-1000RV", category="Biến dòng\n比流器", desc="Desc 2", qty=3, unit="BỘ", tax_rate=0.20),
        EcoPrimeItem(stt=3, name="Gateway CC2051\nCC2051", category="Gateway\n網關", desc="Desc 3", qty=1, unit="BỘ", tax_rate=0.08),
        EcoPrimeItem(stt=4, name="Vật tư phụ\n輔材", category="Vật tư\n輔材", desc="Desc 4", qty=1, unit="SET", tax_rate=0.08),
        EcoPrimeItem(stt=5, name="Chi phí thi công\n施工費", category="Thi công\n施工費", desc="Desc 5", qty=1, unit="SET", tax_rate=0.08),
    ]

    quote_data = EcoPrimeQuotationData(
        customer_name="TEST COMPANY",
        quote_title="Báo giá kiểm thử Test",
        exchange_rate=26130.0,
        items=items
    )

    result = generate_eco_prime_excel(quote_data, save_to_disk=False)
    assert result["bytes_io"] is not None
    assert result["item_count"] == 5

    # Đọc lại bằng openpyxl để kiểm tra thuộc tính
    wb = openpyxl.load_workbook(result["bytes_io"], data_only=False)
    ws = wb.active
    assert ws.freeze_panes is None
    assert ws.page_setup.scale == 38
    assert ws.sheet_view.zoomScale == 60


@pytest.mark.anyio
async def test_eco_prime_web_page_rendering():
    """Kiểm tra trang web /eco-prime-quotations render thành công HTTP 200."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/eco-prime-quotations")
        assert resp.status_code == 200
        assert "Báo Giá ECO PRIME" in resp.text
        assert "eco_prime_quotation.js" in resp.text
        assert "eco_prime_quotation.css" in resp.text
