# -*- coding: utf-8 -*-
"""Entry point workspace cho bộ sinh dữ liệu thử biên bản sửa chữa CX."""

from pathlib import Path
import runpy


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "hongming-pm-hub"
    / "scripts"
    / "generate_complex_repair_test_workbook.py"
)

runpy.run_path(str(SCRIPT), run_name="__main__")
