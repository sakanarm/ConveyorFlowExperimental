"""Remove the spurious BUSY-to-BIDDING arrow from current Fig. 5 sheet.

The historical source page is left untouched. The correct BIDDING-to-BUSY
"won" edge and BUSY-to-IDLE "done" edge remain in the editable draw.io page.
"""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


SOURCE = Path(__file__).resolve().parent.parent / "ConveyorFlow_diagrams_en_working.drawio"
PAGE = "AJSTR v2.2 | Fig 5 - simulation tick"
BAD_EDGE = "t_csKau-SENMY2UGk-Rz-2"


def main():
    source_text = SOURCE.read_text(encoding="utf-8")
    marker = '<diagram name="' + PAGE + '"'
    if source_text.count(marker) != 1:
        raise ValueError("Expected one current Fig. 5 sheet")
    before, current_and_after = source_text.split(marker, 1)
    current, after = current_and_after.split("</diagram>", 1)
    lines = current.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if f'id="{BAD_EDGE}"' in line), None)
    if start is None or start + 2 >= len(lines):
        raise ValueError("Expected one spurious edge")
    block = "".join(lines[start:start + 3])
    if (block.count(f'id="{BAD_EDGE}"') != 1 or
            'source="n42"' not in block or 'target="n41"' not in block or
            'id="n44"' not in current or 'source="n41"' not in current or
            'target="n42"' not in current):
        raise ValueError("Fig. 5 transition preconditions changed")
    del lines[start:start + 3]
    SOURCE.write_text(before + marker + "".join(lines) + "</diagram>" + after,
                      encoding="utf-8", newline="")
    check = ET.parse(SOURCE).getroot()
    fixed = next(page for page in check.findall("diagram") if page.get("name") == PAGE)
    assert all(cell.get("id") != BAD_EDGE for cell in fixed.findall(".//mxCell"))
    print(f"Corrected {PAGE}; original historical page preserved")


if __name__ == "__main__":
    main()
