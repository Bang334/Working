# -*- coding: utf-8 -*-
"""Entry point đồng bộ cho script nghiệp vụ trong hongming-pm-hub."""

from pathlib import Path
import runpy


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "hongming-pm-hub"
    / "scripts"
    / "generate_repair_acceptance_from_source.py"
)

runpy.run_path(str(SCRIPT), run_name="__main__")
