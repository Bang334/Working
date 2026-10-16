"""Windows fallback renderer for local QA: Word COM -> PDF -> PNG."""

import argparse
import shutil
from pathlib import Path

import fitz
import win32com.client


def render(input_path: Path, output_dir: Path, emit_pdf: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{input_path.stem}.pdf"
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    document = None
    try:
        document = word.Documents.Open(str(input_path.resolve()), ReadOnly=True)
        document.ExportAsFixedFormat(str(pdf_path.resolve()), 17)
    finally:
        if document is not None:
            document.Close(False)
        word.Quit()

    pdf = fitz.open(pdf_path)
    try:
        for page_number, page in enumerate(pdf, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            pixmap.save(output_dir / f"page-{page_number}.png")
    finally:
        pdf.close()

    if not emit_pdf:
        pdf_path.unlink()
    print(f"Pages rendered to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--emit_pdf", action="store_true")
    args = parser.parse_args()
    render(Path(args.input_path), Path(args.output_dir), args.emit_pdf)


if __name__ == "__main__":
    main()
