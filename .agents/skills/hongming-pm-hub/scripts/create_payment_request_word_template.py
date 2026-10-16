# -*- coding: utf-8 -*-
"""Create a working copy of the approved supplier payment request template.

This compatibility entry point intentionally does not rebuild or overwrite the
golden template. Use ``fill_supplier_payment_request_docx.py`` when data must be
changed.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


TEMPLATE = Path(r"E:\Working\Bieu Mau\đơn yêu cầu NCC thanh toán-Gốc.docx")
DEFAULT_OUTPUT = Path(r"E:\Working\Bieu Mau\đơn yêu cầu NCC thanh toán-Bản mới.docx")


def next_fallback(path: Path) -> Path:
    candidate = path.with_name(f"{path.stem}_v2{path.suffix}")
    counter = 3
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_v{counter}{path.suffix}")
        counter += 1
    return candidate


def create_copy(output: Path) -> Path:
    template = TEMPLATE.resolve()
    target = output.resolve()
    if not template.exists():
        raise FileNotFoundError(f"Không tìm thấy mẫu chuẩn: {template}")
    if template == target:
        raise ValueError("Không được ghi đè file mẫu gốc.")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(template, target)
        return target
    except PermissionError:
        fallback = next_fallback(target)
        shutil.copy2(template, fallback)
        return fallback


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tạo bản sao 1:1 từ mẫu Phiếu yêu cầu NCC thanh toán đã duyệt."
    )
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = create_copy(args.output)
    print(os.fspath(result))


if __name__ == "__main__":
    main()
