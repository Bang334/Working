"""Regression tests for workbook-driven, flexible payment schedules."""

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import database
from app.services.contract_service import prepare_contract_data
from app.services.payment_schedule_service import (
    load_payment_templates,
    normalize_payment_schedule,
    resolve_payment_schedule,
)


class PaymentScheduleTests(unittest.TestCase):
    def test_reads_approved_patterns_from_all_relevant_sheets(self):
        templates = {row["sheet_name"]: row for row in load_payment_templates()}

        self.assertEqual(templates["712TR"]["percentages"], [30, 60, 10])
        self.assertEqual(templates["712TR"]["deadlines"], [None, 15, 30])
        self.assertEqual(templates["chengfeng"]["percentages"], [30, 30, 30, 10])
        self.assertEqual(templates["HM27082026JI002"]["percentages"], [30, 55, 15])
        self.assertEqual(templates["CX"]["percentages"], [100])

    def test_four_phases_preserve_order_and_individual_deadlines(self):
        schedule = resolve_payment_schedule(
            "Thanh toán 10% 30 ngày, 30% 60 ngày, 30%, 30%", {}
        )

        self.assertEqual([row["phan_tram"] for row in schedule], [10, 30, 30, 30])
        self.assertEqual([row["thoi_han_tt_ngay"] for row in schedule], [30, 60, None, None])
        self.assertIn("hạ tầng", schedule[1]["dieu_kien_viet"])
        self.assertIn("FAC", schedule[3]["dieu_kien_viet"])

    def test_three_custom_phases_are_not_replaced_by_old_default(self):
        schedule = resolve_payment_schedule("Phương thức thanh toán: 40%, 30%, 30%", {})
        self.assertEqual([row["phan_tram"] for row in schedule], [40, 30, 30])

    def test_user_description_wins_and_gemini_supplies_its_chinese_rendering(self):
        ai_rows = [
            {
                "phan_tram": 10,
                "dieu_kien_viet": "Dùng cho chi phí bản quyền phần mềm",
                "dieu_kien_trung": "用於軟體授權費用",
            },
            {"phan_tram": 20},
            {"phan_tram": 70},
        ]
        schedule = resolve_payment_schedule(
            "Thanh toán: 10% dùng cho chi phí bản quyền, 30 ngày; 20%; 70%",
            {"phan_bo_thanh_toan": ai_rows},
        )

        self.assertEqual(schedule[0]["thoi_han_tt_ngay"], 30)
        self.assertEqual(schedule[0]["dieu_kien_viet"], "Dùng cho chi phí bản quyền phần mềm")
        self.assertEqual(schedule[0]["dieu_kien_trung"], "用於軟體授權費用")
        self.assertNotIn("mo_ta_nguoi_dung", schedule[1])

    def test_jinxun_mes_uses_matching_project_sheet_when_input_has_no_percentages(self):
        data = {
            "ben_a": {"ten_cong_ty": "CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM"},
            "du_an": {"ten_du_an_viet": "Triển khai hệ thống MES Lite"},
            "hang_muc": [{"ten_san_pham": "MES Lite - Giao diện Web và API"}],
        }
        schedule = resolve_payment_schedule("", data)

        self.assertEqual([row["phan_tram"] for row in schedule], [30, 55, 15])
        self.assertTrue(all(row["nguon_mau_sheet"] == "HM27082026JI002" for row in schedule))

    def test_prepare_contract_preserves_user_schedule(self):
        data = {
            "ben_a": {"ten_cong_ty": "Khách hàng", "chuc_vu": "Tổng giám đốc"},
            "du_an": {"ten_du_an_viet": "Dự án tùy chỉnh"},
            "hang_muc": [],
            "tong_tien_hop_dong_so": "100.000.000",
            "phan_bo_thanh_toan": [
                {"dot": 1, "phan_tram": 40, "thoi_han_tt_ngay": 30},
                {"dot": 2, "phan_tram": 30, "thoi_han_tt_ngay": 60},
                {"dot": 3, "phan_tram": 30},
            ],
        }
        prepared = prepare_contract_data(data)

        self.assertEqual([row["phan_tram"] for row in prepared["phan_bo_thanh_toan"]], [40, 30, 30])
        self.assertEqual(prepared["phan_bo_thanh_toan"][0]["so_tien"], "40.000.000 VND")

    def test_rejects_percentage_total_other_than_100(self):
        with self.assertRaisesRegex(ValueError, "100%"):
            normalize_payment_schedule(
                [{"phan_tram": 10}, {"phan_tram": 30}, {"phan_tram": 30}], {}
            )

    def test_deadline_starts_from_checked_trigger_date(self):
        with TemporaryDirectory() as temp_dir:
            temp_db = Path(temp_dir) / "payment-trigger.db"
            with patch.object(database, "DB_PATH", temp_db), patch.object(
                database, "SIMULATED_TODAY", datetime(2026, 10, 15)
            ):
                database.init_db()
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO contracts
                    (contract_code, customer_name_vi, total_amount)
                    VALUES ('HD-TEST', 'Khách hàng thử', 100000000)"""
                )
                contract_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO payment_milestones
                    (contract_id, contract_code, milestone_name, percentage, amount,
                     trigger_condition, payment_term_days, triggered, status)
                    VALUES (?, 'HD-TEST', 'Đợt 1', 10, 10000000,
                            'Sau khi ký hợp đồng', 30, 0, 'PENDING_TRIGGER')""",
                    (contract_id,),
                )
                milestone_id = cursor.lastrowid
                conn.commit()
                conn.close()

                activated = database.activate_payment_milestone(
                    milestone_id, "01/10/2026"
                )

                self.assertEqual(activated["trigger_date"], "01/10/2026")
                self.assertEqual(activated["due_date"], "31/10/2026")
                self.assertEqual(activated["days_left"], 16)
                self.assertEqual(activated["status"], "WAITING")


if __name__ == "__main__":
    unittest.main()
