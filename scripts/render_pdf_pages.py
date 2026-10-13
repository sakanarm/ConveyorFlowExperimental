from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def main() -> int:
    parser = argparse.ArgumentParser(description="Render each PDF page to a PNG for document QA.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(args.pdf)
    matrix = fitz.Matrix(args.dpi / 72.0, args.dpi / 72.0)
    for page_number, page in enumerate(document, 1):
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        pixmap.save(args.output_dir / f"page-{page_number}.png")
    print(f"rendered {len(document)} pages to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
