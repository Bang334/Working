# -*- coding: utf-8 -*-
"""Entrypoint tương thích cho bộ tạo Phiếu yêu cầu thanh toán Excel + Word."""

import runpy
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "hongming-pm-hub"
    / "scripts"
    / "generate_payment_request.py"
)

runpy.run_path(str(SCRIPT), run_name="__main__")
