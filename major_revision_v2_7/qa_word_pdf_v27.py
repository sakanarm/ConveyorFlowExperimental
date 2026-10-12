"""Audit Microsoft Word PDF exports; does not replace full human page review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
PDF_DIR = Path("D:/ConveyorFlowRuntime/v2_7/word_qa")
REPORT = HERE / "word_qa/qa_report_v1.json"
NAMES = ("IEEE", "AJSTR_Blind", "AJSTR_Unblind")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(name):
    path = PDF_DIR / (name + "_v27_rev3.pdf")
    doc = fitz.open(path)
    blank, offpage, text_lengths = [], [], []
    for index, page in enumerate(doc):
        content = page.get_text()
        text_lengths.append(len(content))
        if len(content.strip()) < 100:
            blank.append(index + 1)
        for block in page.get_text("blocks"):
            x0, y0, x1, y1 = block[:4]
            if (x0 < -1 or y0 < -1 or x1 > page.rect.width + 1 or
                    y1 > page.rect.height + 1):
                offpage.append({"page": index + 1, "bbox": list(block[:4])})
    table_marker = ("TABLE XV. BOUNDED SCRAPY REPAIR EXTENSION" if name == "IEEE"
                    else "Table 14. Bounded Scrapy repair extension")
    table_pages = [i + 1 for i, page in enumerate(doc)
                   if table_marker in page.get_text()]
    if len(table_pages) != 1 or "Static-Owners" not in doc[table_pages[0] - 1].get_text():
        raise ValueError(f"{name}: result table split or missing")
    future_pages = [i + 1 for i, page in enumerate(doc)
                    if "Future work" in page.get_text()]
    if len(future_pages) != 1 or blank or offpage:
        raise ValueError(f"{name}: future/blank/offpage anomaly")
    return {"name": name, "pdf_sha256": sha(path), "pages": len(doc),
            "minimum_page_text_chars": min(text_lengths),
            "blank_pages": blank, "offpage_text_blocks": offpage,
            "complete_result_table_page": table_pages[0],
            "future_work_page": future_pages[0],
            "visual_review": "result_and_future_pages_inspected_not_every_page"}


if __name__ == "__main__":
    result = {"renderer": "Microsoft Word ExportAsFixedFormat",
              "libreoffice_used": False,
              "documents": [inspect(name) for name in NAMES]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result, indent=2))
