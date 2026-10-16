"""Tests for Quotation module (Word .docx and Excel .xlsx export, download, and listing)."""

import asyncio
import sys
import unittest
from pathlib import Path

# Add app to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import httpx
from app.main import app
from app.config import WORKING_DIR


class ASGITestClient:
    """Small sync facade for the installed httpx/Starlette version combination."""

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


client = ASGITestClient()

SAMPLE_QUOTATION_PAYLOAD = {
    "customer_name_vi": "CÔNG TY TNHH CX TECHNOLOGY (VIỆT NAM)",
    "customer_name_zh": "台灣精星科技(越南)有限公司",
    "tax_code": "0301445789",
    "quotation_no": "HM-QT-TEST-001",
    "quotation_date": "16/10/2026",
    "project_name": "Dự án Nâng cấp Hệ Thống Giám Sát Năng Lượng EMS",
    "contact_person": "Phòng Kỹ Thuật",
    "validity": "30 ngày",
    "lead_time": "60 ngày",
    "warranty": "12 tháng",
    "payment_terms": "Tạm ứng 50%, Giao hàng 40%, Nghiệm thu 10%",
    "notes": "Báo giá chưa bao gồm thuế phí lắp đặt hạ tầng mạng ngoài xưởng.",
    "items": [
        {
            "name": "Đồng Hồ Đo Điện Đa Mạch Tử Ngoại PM2100-3-B",
            "unit": "Bộ",
            "qty": 4,
            "price": 18500000
        },
        {
            "name": "Biến Dòng Cảm Ứng Đo Dòng CT Split-core 200A/5A",
            "unit": "Cái",
            "qty": 12,
            "price": 1200000
        },
        {
            "name": "Tủ Lá Chắn Điện Xanh EMS Thông Minh",
            "unit": "Hệ",
            "qty": 1,
            "price": 35000000
        }
    ]
}


class TestQuotationModule(unittest.TestCase):
    """Test suite for Quotation Module (Word .docx and Excel .xlsx)."""

    def test_01_quotation_page_renders(self):
        """Verify quotation page loads successfully."""
        response = client.get("/quotation")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Báo Giá" in response.text or "Báo giá" in response.text)

    def test_02_generate_quotation_word(self):
        """Test generating bilingual Word (.docx) quotation."""
        response = client.post("/api/v1/quotation/generate-word", json=SAMPLE_QUOTATION_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["file_name"].endswith(".docx"))
        self.assertTrue(data["download_url"].startswith("/api/v1/quotation/download/"))
        self.assertGreater(data["total_amount"], 0)

        # Verify physical file exists
        file_path = Path(data["file_path"])
        self.assertTrue(file_path.exists())
        self.assertGreater(file_path.stat().st_size, 0)

    def test_03_generate_quotation_excel(self):
        """Test generating bilingual Excel (.xlsx) quotation."""
        response = client.post("/api/v1/quotation/generate-excel", json=SAMPLE_QUOTATION_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["file_name"].endswith(".xlsx"))
        self.assertTrue(data["download_url"].startswith("/api/v1/quotation/download/"))
        self.assertGreater(data["total_amount"], 0)

        # Verify physical file exists
        file_path = Path(data["file_path"])
        self.assertTrue(file_path.exists())
        self.assertGreater(file_path.stat().st_size, 0)

    def test_04_download_quotation_file(self):
        """Test downloading the generated Word file."""
        # First generate Word
        gen_res = client.post("/api/v1/quotation/generate-word", json=SAMPLE_QUOTATION_PAYLOAD)
        file_name = gen_res.json()["file_name"]

        # Download it
        dl_res = client.get(f"/api/v1/quotation/download/{file_name}")
        self.assertEqual(dl_res.status_code, 200)
        self.assertGreater(len(dl_res.content), 0)
        self.assertIn("wordprocessingml", dl_res.headers.get("content-type", ""))

    def test_05_list_quotation_files(self):
        """Test listing generated quotation files."""
        response = client.get("/api/v1/quotation/files")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("files", data)
        self.assertGreaterEqual(len(data["files"]), 2)
        formats = {f["file_format"] for f in data["files"]}
        self.assertIn("docx", formats)
        self.assertIn("xlsx", formats)

    def test_06_ai_parse_quotation(self):
        """Test Gemini AI parse endpoint for quotation inquiry."""
        req_data = {
            "raw_text": "Báo giá cho Công ty Vonmax thiết bị: 6 bộ Edge Gateway IoT-200 giá 16.800.000, 4 cuộn cáp RS485 giá 3.200.000.",
            "model_name": "gemini-2.5-flash"
        }
        response = client.post("/api/v1/quotation/ai-parse", json=req_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("data", data)
        self.assertIn("items", data["data"])
        self.assertGreaterEqual(len(data["data"]["items"]), 1)

    def test_07_save_quotation_with_versioning_and_backup(self):
        """Test saving a new quotation replaces old active version while preserving backup."""
        import time
        unique_no = f"HM-QT-UNITTEST-{int(time.time() * 1000)}"
        payload_v1 = dict(SAMPLE_QUOTATION_PAYLOAD)
        payload_v1["quotation_no"] = unique_no
        payload_v1["project_name"] = "Dự án Ban Đầu (v1)"

        # Save Version 1
        res1 = client.post("/api/v1/quotation/save", json=payload_v1)
        self.assertEqual(res1.status_code, 200)
        d1 = res1.json()
        self.assertEqual(d1["status"], "success")
        self.assertEqual(d1["version"], 1)

        # Save Version 2 (Same quotation_no, updated data)
        payload_v2 = dict(payload_v1)
        payload_v2["project_name"] = "Dự án Nâng Cấp Mới (v2)"
        payload_v2["items"] = payload_v1["items"] + [
            {"name": "Cáp Quang ODF Đơn Mốt 24 Core", "unit": "Cuộn", "qty": 2, "price": 4500000}
        ]

        res2 = client.post("/api/v1/quotation/save", json=payload_v2)
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertEqual(d2["status"], "success")
        self.assertEqual(d2["version"], 2)
        self.assertTrue(d2["previous_backed_up"])

        # Check version history endpoint
        hist_res = client.get(f"/api/v1/quotation/history/{unique_no}")
        self.assertEqual(hist_res.status_code, 200)
        hd = hist_res.json()
        self.assertEqual(hd["status"], "success")
        self.assertEqual(hd["total_versions"], 2)
        self.assertEqual(hd["history"][0]["version"], 2)
        self.assertTrue(hd["history"][0]["is_current"])
        self.assertEqual(hd["history"][1]["version"], 1)
        self.assertFalse(hd["history"][1]["is_current"])

        # Check backup folder contains archived file
        history_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia" / "Lich_Su"
        self.assertTrue(history_dir.exists())
        backups = list(history_dir.glob(f"*{unique_no}*"))
        self.assertGreaterEqual(len(backups), 1)

    @classmethod
    def tearDownClass(cls):
        """Clean up all temporary files and test database records created during testing."""
        from app.database import get_db_connection
        bao_gia_dir = WORKING_DIR / "Ho So Du An" / "Bao Gia"
        history_dir = bao_gia_dir / "Lich_Su"

        # Remove test files matching test patterns
        for folder in (bao_gia_dir, history_dir):
            if folder.exists():
                for pat in ("*TEST*", "*UNITTEST*"):
                    for f in folder.glob(pat):
                        if f.is_file():
                            try:
                                f.unlink()
                            except Exception:
                                pass

        # Clean test records from database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quotations WHERE quotation_no LIKE '%TEST%' OR quotation_no LIKE '%UNITTEST%'")
            cursor.execute("DELETE FROM documents WHERE file_name LIKE '%TEST%' OR file_name LIKE '%UNITTEST%'")
            conn.commit()
            conn.close()
        except Exception:
            pass


