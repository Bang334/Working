# -*- coding: utf-8 -*-
"""CLI tạo Phiếu yêu cầu thanh toán Excel (sheet 712TR) và Word song ngữ."""

import argparse
import json
import sys
from pathlib import Path


WORKING_DIR = Path(__file__).resolve().parents[4]
PM_PORTAL_DIR = WORKING_DIR / "pm_portal"
if str(PM_PORTAL_DIR) not in sys.path:
    sys.path.insert(0, str(PM_PORTAL_DIR))

from app.database import init_db  # noqa: E402
from app.services.payment_request_excel_service import generate_payment_request_excel  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tạo đồng thời Phiếu yêu cầu thanh toán .xlsx theo sheet 712TR và .docx."
    )
    parser.add_argument("--contract-code", default="HMV22092026SY0001")
    parser.add_argument("--milestone", default="Đợt 1")
    parser.add_argument("--customer-name-vi")
    parser.add_argument("--customer-name-zh")
    parser.add_argument("--project-name-vi")
    parser.add_argument("--project-name-zh")
    parser.add_argument("--amount", type=float)
    parser.add_argument("--total-contract-amount", type=float)
    parser.add_argument("--percentage", type=float)
    parser.add_argument("--due-date")
    parser.add_argument("--invoice-no")
    parser.add_argument("--application-date")
    parser.add_argument(
        "--template-source",
        choices=("excel", "word"),
        default="excel",
        help="Nguồn mẫu chính: Excel sheet 712TR hoặc file Word trong Bieu Mau.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    init_db()
    result = generate_payment_request_excel(
        contract_code=args.contract_code,
        milestone_name=args.milestone,
        customer_name_vi=args.customer_name_vi,
        customer_name_zh=args.customer_name_zh,
        project_name_vi=args.project_name_vi,
        project_name_zh=args.project_name_zh,
        amount=args.amount,
        total_contract_amount=args.total_contract_amount,
        percentage=args.percentage,
        due_date=args.due_date,
        invoice_no=args.invoice_no,
        application_date=args.application_date,
        template_source=args.template_source,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "excel": result["file_path"],
                "word": result["word_file_path"],
                "template_sheet": "712TR",
                "template_source": result["template_source"],
                "template_file": result["template_file_name"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
