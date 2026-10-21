"""Unit & integration tests for Repair Contract functionality."""

import asyncio
import unittest
import httpx

from app.main import app
from app.services.repair_contract_service import (
    prepare_repair_contract_data,
    save_repair_contract_to_db,
    get_all_repair_contracts_list,
    get_repair_contract_detail,
    delete_repair_contract,
)
from app.services.repair_contract_word_service import generate_repair_contract_docx


class ASGITestClient:
    """Small sync facade for installed httpx/Starlette version combination."""

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


class TestRepairContract(unittest.TestCase):
    def setUp(self):
        self.client = ASGITestClient()
        self.sample_data = {
            "so_hop_dong": "HDSC-TEST-20261019",
            "ngay_ky": "19",
            "thang_ky": "10",
            "nam_ky": "2026",
            "ben_a": {
                "ten_cong_ty": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
                "ten_tieng_trung": "越南CX科技股份有限公司",
                "dia_chi": "Lô K1, KCX Tân Thuận, Q. 7, TP. HCM",
                "dia_chi_trung": "胡志明市第七郡新順加工出口區K1地塊",
                "mst": "0301789999",
                "nguoi_dai_dien": "CHEN CHEN-YEN",
                "chuc_vu": "TỔNG GIÁM ĐỐC",
                "chuc_vu_trung": "總經理"
            },
            "ten_goi_sua_chua_viet": "Dịch vụ kiểm tra, sửa chữa máy tính công nghiệp IPC",
            "ten_goi_sua_chua_trung": "工控機設備檢修及維修服務",
            "dia_diem_sua_chua": "Tại xưởng sản xuất Bên A",
            "thoi_gian_hoan_thanh_ngay": 10,
            "thoi_gian_bao_hanh_thang": 6,
            "hang_muc": [
                {
                    "stt": 1,
                    "ten_thiet_bi": "Máy tính công nghiệp IPC Advantech / 研華工控機",
                    "model_serial": "IPC-610H / SN: CX202401",
                    "noi_dung_sua_chua": "Thay nguồn ATX 400W & vệ sinh tản nhiệt",
                    "don_vi_tinh": "Bộ",
                    "don_gia": "6.800.000 VND",
                    "so_luong": "2",
                    "tong_gia": "13.600.000 VND"
                }
            ],
            "phan_bo_thanh_toan": [
                {
                    "dot": 1,
                    "phan_tram": 50,
                    "so_tien": "6.800.000 VND",
                    "tieu_de": "Tạm ứng ký hợp đồng",
                    "tieu_de_trung": "簽約預付款",
                    "dieu_kien_viet": "Thanh toán tạm ứng 50% ngay sau khi ký HĐ",
                    "dieu_kien_trung": "雙方簽約後即期支付 50%",
                    "thoi_han_tt_ngay": 0
                },
                {
                    "dot": 2,
                    "phan_tram": 50,
                    "so_tien": "6.800.000 VND",
                    "tieu_de": "Nghiệm thu hoàn tất",
                    "tieu_de_trung": "驗收交付款",
                    "dieu_kien_viet": "Thanh toán 50% còn lại sau khi nghiệm thu đạt",
                    "dieu_kien_trung": "設備維修完成並簽署驗收文件後支付 50%",
                    "thoi_han_tt_ngay": 30
                }
            ]
        }

    def tearDown(self):
        try:
            delete_repair_contract("HDSC-TEST-20261019")
        except Exception:
            pass

    def test_repair_contracts_page_view(self):
        """Test GET /repair-contracts renders HTML successfully."""
        response = self.client.get("/repair-contracts")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hợp Đồng Sửa Chữa", response.text)
        self.assertIn("維修清單", response.text)
        self.assertIn("aiRepairPromptInput", response.text)

    def test_prepare_repair_contract_data(self):
        """Test data preparation and currency calculation."""
        prepared = prepare_repair_contract_data(self.sample_data)
        self.assertEqual(prepared["tong_tien_hop_dong_so"], "13.600.000")
        self.assertIn("Mười ba triệu sáu trăm nghìn đồng", prepared["tong_tien_chu_viet"])
        self.assertIn("壹仟參佰陸拾萬", prepared["tong_tien_chu_trung"])

    def test_generate_repair_docx(self):
        """Test DOCX file generation."""
        prepared = prepare_repair_contract_data(self.sample_data)
        result = generate_repair_contract_docx(prepared)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["file_name"].endswith(".docx"))
        self.assertIn("HDSC-TEST-20261019", result["file_name"])

    def test_save_and_list_repair_contract(self):
        """Test saving repair contract to DB and retrieving in list."""
        save_res = save_repair_contract_to_db(self.sample_data)
        self.assertEqual(save_res["status"], "success")

        contracts = get_all_repair_contracts_list()
        found = any(c["contract_code"] == "HDSC-TEST-20261019" for c in contracts)
        self.assertTrue(found)

        detail = get_repair_contract_detail("HDSC-TEST-20261019")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["so_hop_dong"], "HDSC-TEST-20261019")
        self.assertEqual(len(detail["phan_bo_thanh_toan"]), 2)

    def test_api_endpoints(self):
        """Test API endpoints for repair contract."""
        res_list = self.client.get("/api/v1/repair-contracts/list")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(res_list.json()["status"], "success")

        res_gen = self.client.post("/api/v1/repair-contracts/generate", json=self.sample_data)
        self.assertEqual(res_gen.status_code, 200)
        self.assertEqual(res_gen.json()["status"], "success")

        res_save = self.client.post("/api/v1/repair-contracts/save", json=self.sample_data)
        self.assertEqual(res_save.status_code, 200)
        self.assertEqual(res_save.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
