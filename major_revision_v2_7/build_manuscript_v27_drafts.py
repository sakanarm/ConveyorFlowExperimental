"""Add the audited bounded Scrapy extension to copies of current manuscripts.

These files remain drafts until every page is reviewed in Microsoft Word.
Never pool the two Scrapy bugs with independent projects or the mixed cohorts.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document

V2 = Path(__file__).resolve().parent.parent
CURRENT = V2 / "CURRENT_MANUSCRIPTS"
ANALYSIS = Path(__file__).resolve().parent / "scrapy_live_pair_v1/analysis_v1.json"
SOURCES = (
    ("ConveyorFlow_IEEE_Manuscript_v2_6_1_Current.docx",
     "ConveyorFlow_IEEE_Manuscript_v2_7_Exploratory_Draft_Rev3.docx", False, False),
    ("ConveyorFlow_AJSTR_Blinded_v2_6_1_Current.docx",
     "ConveyorFlow_AJSTR_Blinded_v2_7_Exploratory_Draft_Rev3.docx", True, True),
    ("ConveyorFlow_AJSTR_Unblinded_v2_6_1_Current.docx",
     "ConveyorFlow_AJSTR_Unblinded_v2_7_Exploratory_Draft_Rev3.docx", True, False),
)


def windows_safe(path):
    value = str(Path(path).resolve())
    return "\\\\?\\" + value if len(value) >= 240 and not value.startswith("\\\\?\\") else value


def insert_before(anchor, text, style=None):
    paragraph = anchor.insert_paragraph_before(text, style=style)
    return paragraph


def find(doc, beginning):
    found = [paragraph for paragraph in doc.paragraphs
             if paragraph.text.startswith(beginning)]
    if len(found) != 1:
        raise ValueError("Expected exactly one anchor: " + beginning)
    return found[0]


def insert_table_before(doc, anchor, values):
    table = doc.add_table(rows=0, cols=len(values[0]))
    table.style = "Table Grid"
    for values_row in values:
        cells = table.add_row().cells
        for cell, value in zip(cells, values_row):
            cell.text = str(value)
    anchor._p.addprevious(table._tbl)
    return table


def build(doc, analysis, ajstr, blind):
    if ajstr:
        anchor = find(doc, "3.13. Interpretation")
        heading = "3.13. Bounded Scrapy repository extension"
        table_title = "Table 14. Bounded Scrapy repair extension"
        find(doc, "3.13. Interpretation").text = "3.14. Interpretation"
        find(doc, "3.14. Limitations").text = "3.15. Limitations"
    else:
        anchor = find(doc, "VII. DISCUSSION")
        heading = "P. Bounded Scrapy Repository Extension"
        table_title = "TABLE XV. BOUNDED SCRAPY REPAIR EXTENSION"
    insert_before(anchor, heading, "Heading 2")
    insert_before(anchor,
                  "We conducted a separate repair-only extension on the first two "
                  "previously unattempted Scrapy bugs in a pre-frozen public-source "
                  "queue. The buggy checkout failed its public test and the fixed "
                  "validator passed before any model call. The prompt contained only "
                  "the selected buggy production file and public failure trace. Five "
                  "non-visible public tests per case passed on both checkouts before "
                  "selection. Each case was presented on the same READY belt to "
                  "CF-Fit, Central-Rule-Matched, and Static-Owners, with one provider "
                  "request per arm, the same three-agent roster, the same prompt, "
                  "a 1,800-s horizon, and a 32,768-token output ceiling. Verification "
                  "required visible, regression, and fresh replay checks in Podman. "
                  "The task rank of 2 was a fixed exploratory allocation setting, "
                  "not an expert difficulty label.")
    by_case = {case_id: {row["arm"]: row for row in analysis["rows"]
                         if row["case_id"] == case_id}
               for case_id in ("scrapy_39", "scrapy_34")}
    case_sentence = " ".join(
        f"For {case_id}, CF-Fit, rule-matched central allocation, and static "
        f"ownership verified {by_case[case_id]['CF_FIT']['verified']}/1, "
        f"{by_case[case_id]['CENTRAL_RULE_MATCHED']['verified']}/1, and "
        f"{by_case[case_id]['STATIC_OWNERS']['verified']}/1 repairs, respectively."
        for case_id in ("scrapy_39", "scrapy_34"))
    insert_before(anchor, case_sentence)
    caption = insert_before(anchor, table_title)
    caption.paragraph_format.page_break_before = True
    caption.paragraph_format.keep_with_next = True
    arm_labels = (("CF_FIT", "CF-Fit"),
                  ("CENTRAL_RULE_MATCHED", "Central-Rule-Matched"),
                  ("STATIC_OWNERS", "Static-Owners"))
    values = [("Arm", "Verified", "Mean restricted time (s)",
               "Busy fraction (%)", "Output tokens")]
    for key, label in arm_labels:
        row = analysis["arms"][key]
        values.append((label, f"{row['verified_cases_of_two']}/2",
                       f"{row['mean_restricted_completion_seconds']:.1f}",
                       f"{100 * row['mean_busy_fraction_fixed_horizon']:.2f}",
                       str(row["total_output_tokens"])))
    insert_table_before(doc, anchor, values)
    reported = {key: sum(row["provider_cost_units_currency_unverified"]
                         for row in analysis["rows"] if row["arm"] == key)
                for key, _ in arm_labels}
    insert_before(anchor,
                  "Across both requests per arm, the gateway reported cost "
                  f"figures of {reported['CF_FIT']:.6f}, "
                  f"{reported['CENTRAL_RULE_MATCHED']:.6f}, and "
                  f"{reported['STATIC_OWNERS']:.6f} units for CF-Fit, "
                  "Central-Rule-Matched, and Static-Owners, respectively. "
                  "These are provisional gateway estimates; the MFEC tariff, "
                  "currency, and invoice have not been reconciled. Thus, they "
                  "are not verified billed costs or a monetary efficiency ranking.")
    insert_before(anchor,
                  "Restricted time assigns the 1,800-s horizon to a repair not "
                  "verified by the horizon; conditional completion time is not "
                  "imputed for failures. Busy fraction uses three agents times "
                  "the fixed horizon as its denominator. Provider-reported cost "
                  "units are not verified billed currency, so monetary cost per "
                  "verified job is unavailable. The two bugs belong to one "
                  "repository project and all arms used the selected A1 model; "
                  "provider calls are not independent project-level samples. "
                  "This extension does not add a full ML pipeline, establish "
                  "cross-project generalization, or isolate the effect of "
                  "stand-down. The earlier six- and eleven-block executable "
                  "cohorts remain separate and are not pooled with these cases.")
    future_anchor = find(doc, "Data and code availability" if ajstr
                         else "DATA AND CODE AVAILABILITY")
    insert_before(future_anchor, "Future work", "Heading 2")
    insert_before(future_anchor,
                  "A preregistered extension should sample independent public "
                  "repository projects and ML corpora, size the project-level "
                  "paired comparison for a stated precision target, and validate "
                  "task difficulty and Ability Ranks with independent human "
                  "raters before observing outcomes. It should compare matched "
                  "homogeneous and heterogeneous teams and isolate fit and "
                  "stand-down by ablation. Belt-order sensitivity needs two "
                  "separate manipulations: the order in which READY tasks are "
                  "exposed and the order in which agents reach or claim them. "
                  "With workloads and decision rules held fixed, future runs "
                  "should measure collisions, waiting, starvation, completion, "
                  "utilization, and cost under these orderings. Controlled "
                  "coordinator-only, shared claim-store, and provider outages "
                  "should delimit the failure-domain claim. Finally, the "
                  "gateway's dated tariff, usage records, and invoice must be "
                  "reconciled before reporting billed cost per verified job. "
                  "These are proposed tests, not results of the present study.")
    doc.core_properties.subject = "Audited bounded Scrapy extension, separate from main cohorts"
    if blind:
        doc.core_properties.author = ""
        doc.core_properties.last_modified_by = ""


def main():
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if (analysis["status"] != "BOUNDED_DESCRIPTIVE_ONE_REPOSITORY_NOT_MAIN" or
            analysis["cases"] != 2 or
            analysis["independent_repository_projects"] != 1):
        raise ValueError("Audited bounded analysis required")
    for source_name, target_name, ajstr, blind in SOURCES:
        target = CURRENT / target_name
        if target.exists():
            raise FileExistsError("Refuse to overwrite " + str(target))
        doc = Document(windows_safe(CURRENT / source_name))
        before = (len(doc.inline_shapes), len(doc.element.body.xpath('.//m:oMath')))
        build(doc, analysis, ajstr, blind)
        after = (len(doc.inline_shapes), len(doc.element.body.xpath('.//m:oMath')))
        if before != after:
            raise ValueError("Figure/native equation count changed")
        doc.save(windows_safe(target))
        print(target_name, "figures", after[0], "equations", after[1],
              "tables", len(doc.tables), flush=True)


if __name__ == "__main__":
    main()
