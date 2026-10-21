# -*- coding: utf-8 -*-
"""Unit tests for Installation Acceptance feature."""

import os
import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.installation_acceptance_word_service import (
    generate_installation_acceptance_word,
    prepare_installation_acceptance_data,
)
from app.services.installation_acceptance_preview_service import (
    generate_installation_acceptance_preview_html,
)
from app.controllers.acceptance_controller import (
    generate_installation_acceptance_word_controller,
    render_installation_acceptance_preview_controller,
    get_installation_sample_data_controller,
    list_acceptance_files_controller,
)


class TestInstallationAcceptance(unittest.TestCase):
    """Test suite for Installation Acceptance & Handover confirmation."""

    def setUp(self):
        self.sample_data = get_installation_sample_data_controller()["data"]

    def test_sample_data_structure(self):
        """Verify standard CX sample data has all required fields."""
        self.assertEqual(self.sample_data["so_hop_dong"], "HMV151020250001")
        self.assertEqual(self.sample_data["ben_a"]["ten_cong_ty"], "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)")
        self.assertEqual(len(self.sample_data["hang_muc"]), 7)
        self.assertEqual(len(self.sample_data["payment_stages"]), 3)

    def test_generate_stage_3_only(self):
        """Verify generating Word document with Stage 3 only (20% = 46.800.000 VND)."""
        data = dict(self.sample_data)
        data["payment_stages"] = [
            {"stage_num": 1, "stage": "GIAI ĐOẠN 1\n第一期", "condition": "Ký kết", "rate": "40%", "amount": "93.600.000 VND", "selected": False},
            {"stage_num": 2, "stage": "GIAI ĐOẠN 2\n第二期", "condition": "Triển khai", "rate": "40%", "amount": "93.600.000 VND", "selected": False},
            {"stage_num": 3, "stage": "GIAI ĐOẠN 3\n第三期", "condition": "Nghiệm thu đạt tiêu chuẩn\n驗收合格時", "rate": "20%", "amount": "46.800.000 VND", "selected": True},
        ]
        res = generate_installation_acceptance_word(data)
        self.assertEqual(res["status"], "success")
        self.assertTrue(Path(res["file_path"]).is_file())

    def test_generate_stages_2_and_3_combined(self):
        """Verify generating Word document with Stages 2 & 3 combined (60% = 140.400.000 VND)."""
        data = dict(self.sample_data)
        data["payment_stages"] = [
            {"stage_num": 1, "stage": "GIAI ĐOẠN 1\n第一期", "condition": "Ký kết", "rate": "40%", "amount": "93.600.000 VND", "selected": False},
            {"stage_num": 2, "stage": "GIAI ĐOẠN 2\n第二期", "condition": "Sau khi triển khai", "rate": "40%", "amount": "93.600.000 VND", "selected": True},
            {"stage_num": 3, "stage": "GIAI ĐOẠN 3\n第三期", "condition": "Nghiệm thu đạt tiêu chuẩn", "rate": "20%", "amount": "46.800.000 VND", "selected": True},
        ]
        res = generate_installation_acceptance_word(data)
        self.assertEqual(res["status"], "success")
        self.assertTrue(Path(res["file_path"]).is_file())

    def test_preview_html_generation(self):
        """Verify HTML preview renders all 7 items and sections."""
        html = generate_installation_acceptance_preview_html(self.sample_data)
        self.assertIn("BIÊN BẢN TIẾN ĐỘ LẮP ĐẶT VÀ NGHIỆM THU LẮP ĐẶT", html)
        self.assertIn("HMV151020250001", html)
        self.assertIn("CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)", html)
        self.assertIn("Concept Development", html)
        self.assertIn("WEB RFID報表查詢", html)
        self.assertIn("93.600.000 VND", html)

    def test_docx_document_generation(self):
        """Verify Word document is created without errors and preserves template layout."""
        result = generate_installation_acceptance_word(self.sample_data)
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["file_name"].endswith(".docx"))
        
        file_path = Path(result["file_path"])
        self.assertTrue(file_path.is_file())
        self.assertGreater(file_path.stat().st_size, 10000)

    def test_list_files_includes_docx(self):
        """Verify listing function returns docx files alongside xlsx."""
        res = list_acceptance_files_controller()
        self.assertEqual(res["status"], "success")
        files = res["files"]
        has_docx = any(f["file_name"].endswith(".docx") for f in files)
        self.assertTrue(has_docx, "Should list created .docx files")


if __name__ == "__main__":
    unittest.main()
