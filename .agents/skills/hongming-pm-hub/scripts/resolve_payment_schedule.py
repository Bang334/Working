# -*- coding: utf-8 -*-
"""CLI tái sử dụng để đọc lịch thanh toán từ 備註 và mô tả người dùng."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Locate the project independently of the drive letter on this computer.
_WORKSPACE_ROOT = next((p for p in __import__('pathlib').Path(__file__).resolve().parents if (p / 'pm_portal' / 'app').is_dir()), __import__('pathlib').Path.cwd())
def _workspace_path(relative):
    return str(_WORKSPACE_ROOT / relative.replace(chr(92), '/'))

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Phân tích lịch thanh toán 1-4 đợt theo mẫu Hong Ming."
    )
    parser.add_argument("text", nargs="?", default="", help="Mô tả tỷ lệ, thời hạn và mục đích từng đợt")
    parser.add_argument("--input-file", type=Path, help="Tệp UTF-8 chứa mô tả đầu vào")
    parser.add_argument("--workspace", type=Path, default=Path(_workspace_path('')))
    parser.add_argument("--company", default="")
    parser.add_argument("--project", default="")
    args = parser.parse_args()

    portal_dir = args.workspace / "pm_portal"
    if str(portal_dir) not in sys.path:
        sys.path.insert(0, str(portal_dir))

    from app.services.payment_schedule_service import resolve_payment_schedule

    source_text = args.text
    if args.input_file:
        source_text = args.input_file.read_text(encoding="utf-8")
    contract_data = {
        "ben_a": {"ten_cong_ty": args.company},
        "du_an": {"ten_du_an_viet": args.project},
    }
    schedule = resolve_payment_schedule(source_text, contract_data)
    print(json.dumps(schedule, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
