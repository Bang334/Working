"""Integration and unit tests for Hong Ming PM Portal APIs."""

import sys
import unittest
from pathlib import Path

# Add app to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPMPortalAPI(unittest.TestCase):
    """Test suite for PM Portal Web Endpoints."""

    def test_01_contracts_page_render(self):
        """Verify the contracts UI page renders properly."""
        response = client.get("/contracts")
        self.assertEqual(response.status_code, 200)
        self.assertIn("HONG MING GLOBAL", response.text)
        self.assertIn("Bảng Danh Mục Sản Phẩm", response.text)

    def test_02_contract_preview_endpoint(self):
        """Verify preview generation with Minh Phat 10 items."""
        payload = {
            "so_hop_dong": "HD-20261013-001/HMG-MP",
            "ngay_ky": "13",
            "thang_ky": "10",
            "nam_ky": "2026",
            "ben_a": {
                "ten_cong_ty": "CÔNG TY TNHH GIẢI PHÁP CÔNG NGHỆ MINH PHÁT",
                "ten_tieng_trung": "越南明發科技解決方案有限公司",
                "dia_chi": "Số 28, Đường Công Nghệ, Phường Bình Dương, Thành phố Hồ Chí Minh, Việt Nam",
                "dia_chi_trung": "越南胡志明市平陽坊科技路28號",
                "mst": "0000000000",
                "nguoi_dai_dien": "NGUYỄN MINH KHẢI",
                "chuc_vu": "Tổng giám đốc",
                "chuc_vu_trung": "總經理"
            },
            "du_an": {
                "ten_du_an_viet": "Hệ thống Quản lý Kho WMS & MES Pro",
                "ten_du_an_trung": "WMS倉庫管理系統與MES Pro生產管理軟體建置案"
            },
            "hang_muc": [
                {
                    "stt": 1,
                    "ten_san_pham": "Hệ thống quản lý kho WMS Standard\nWMS Standard 倉庫管理系統",
                    "don_gia": "185.000.000 VND",
                    "so_luong": "1 SET",
                    "tong_gia": "185.000.000 VND"
                },
                {
                    "stt": 2,
                    "ten_san_pham": "Phần mềm quản lý sản xuất MES Pro (bản quyền 30 máy)\nMES Pro 生產管理軟體（30台設備授權版）",
                    "don_gia": "420.000.000 VND",
                    "so_luong": "1 SET",
                    "tong_gia": "420.000.000 VND"
                }
            ],
            "tong_so_luong": "2 SET",
            "tong_tien_hop_dong_so": "605.000.000"
        }

        response = client.post("/api/v1/contracts/preview", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("MINH PHÁT", data["preview_html"])
        self.assertIn("605.000.000 VND", data["preview_html"])

    def test_03_contract_docx_generation(self):
        """Verify Word (.docx) generation and download flow."""
        payload = {
            "so_hop_dong": "HD-20261013-TEST",
            "ngay_ky": "13",
            "thang_ky": "10",
            "nam_ky": "2026",
            "ben_a": {
                "ten_cong_ty": "CÔNG TY TNHH GIẢI PHÁP CÔNG NGHỆ MINH PHÁT",
                "ten_tieng_trung": "越南明發科技解決方案有限公司",
                "dia_chi": "Số 28, Đường Công Nghệ, Phường Bình Dương, Thành phố Hồ Chí Minh, Việt Nam",
                "dia_chi_trung": "越南胡志明市平陽坊科技路28號",
                "mst": "0000000000",
                "nguoi_dai_dien": "NGUYỄN MINH KHẢI",
                "chuc_vu": "Tổng giám đốc",
                "chuc_vu_trung": "總經理"
            },
            "du_an": {
                "ten_du_an_viet": "Hệ thống Quản lý Kho WMS",
                "ten_du_an_trung": "WMS倉庫管理系統"
            },
            "hang_muc": [
                {
                    "stt": 1,
                    "ten_san_pham": "Hệ thống quản lý kho WMS Standard\nWMS Standard 倉庫管理系統",
                    "don_gia": "185.000.000 VND",
                    "so_luong": "1 SET",
                    "tong_gia": "185.000.000 VND"
                }
            ],
            "tong_so_luong": "1 SET",
            "tong_tien_hop_dong_so": "185.000.000"
        }

        response = client.post("/api/v1/contracts/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["status"], "success")
        self.assertTrue(res_data["file_name"].endswith(".docx"))

        # Test download
        download_res = client.get(res_data["download_url"])
        self.assertEqual(download_res.status_code, 200)
        self.assertTrue(len(download_res.content) > 1000)


if __name__ == "__main__":
    unittest.main()
