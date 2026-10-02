from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "main"
FIGURES = RESULTS / "figures"
ABILITY_FIGURES = ROOT / "real_llm_pilot" / "figures"
DRAWIO_FIGURES = ROOT / "manuscript_assets" / "drawio"
REAL_LLM = ROOT / "real_llm_pilot"
REAL_LLM_MAIN = REAL_LLM / "main_mfec_aggregated"
REAL_LLM_EXTENSION = REAL_LLM / "extension_mfec_aggregated"
MANUSCRIPT = ROOT / "ConveyorFlow_IEEE_Manuscript.docx"
ADVISOR = ROOT / "ConveyorFlow_Advisor_Explanation_TH.docx"

METRICS = (
    "cost_per_verified_task",
    "verified_throughput",
    "p95_terminal_flow_time",
    "task_completion_rate",
    "dead_letter_rate",
    "unsettled_rate",
    "productive_utilization",
)


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_inputs() -> dict:
    required = [
        RESULTS / "metrics.csv",
        RESULTS / "confirmatory_effects.csv",
        RESULTS / "descriptive_summary.csv",
        RESULTS / "annotation_policy_sensitivity.csv",
        RESULTS / "pareto_frontier_summary.csv",
        RESULTS / "competing_risk_summary.csv",
        RESULTS / "secondary_analysis_integrity.json",
        RESULTS / "execution_summary.json",
        RESULTS / "analysis_integrity.json",
        RESULTS / "artifact_verification.json",
        ROOT / "expert_labels" / "expert_label_agreement.json",
        ROOT / "expert_labels" / "llm_annotation_validation.json",
        ROOT / "data" / "manifest.json",
        ROOT / "real_llm_pilot" / "pilot_output" / "dry_run_manifest.json",
        ROOT / "real_llm_pilot" / "final_team_evidence.json",
        ROOT / "real_llm_pilot" / "concurrent_runner_audit.json",
        ABILITY_FIGURES / "fig_ability_profile_radar.png",
        DRAWIO_FIGURES / "architecture_system.png",
        DRAWIO_FIGURES / "architecture_process.png",
        DRAWIO_FIGURES / "cf_fit_belt.png",
        DRAWIO_FIGURES / "baseline_static.png",
        DRAWIO_FIGURES / "one_tick.png",
        REAL_LLM_MAIN / "validated_runs.json",
        REAL_LLM_MAIN / "real_llm_descriptive.csv",
        REAL_LLM_MAIN / "real_llm_pairwise.csv",
        REAL_LLM_EXTENSION / "validated_extension_runs.json",
        REAL_LLM_EXTENSION / "extension_descriptive.csv",
        REAL_LLM_EXTENSION / "extension_pairwise.csv",
        REAL_LLM / "figures" / "fig_real_llm_main_radar.png",
        REAL_LLM / "figures" / "fig_real_llm_extension_radar.png",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing required report inputs: {missing}")
    execution = json.loads((RESULTS / "execution_summary.json").read_text(encoding="utf-8"))
    integrity = json.loads((RESULTS / "analysis_integrity.json").read_text(encoding="utf-8"))
    verification = json.loads((RESULTS / "artifact_verification.json").read_text(encoding="utf-8"))
    secondary_integrity = json.loads((RESULTS / "secondary_analysis_integrity.json").read_text(encoding="utf-8"))
    real_main = json.loads((REAL_LLM_MAIN / "validated_runs.json").read_text(encoding="utf-8"))
    real_extension = json.loads((REAL_LLM_EXTENSION / "validated_extension_runs.json").read_text(encoding="utf-8"))
    if execution.get("status") != "complete" or not integrity.get("pass") or verification.get("status") != "pass" or secondary_integrity.get("status") != "complete":
        raise SystemExit("refusing manuscript generation: execution/integrity/verification is incomplete")
    if real_main.get("status") != "validated_complete_main" or real_main.get("validated_runs") != 30:
        raise SystemExit("refusing manuscript generation: Main Real-LLM results are incomplete")
    if real_extension.get("status") != "validated_complete_extension" or real_extension.get("validated_extension_runs") != 30:
        raise SystemExit("refusing manuscript generation: Real-LLM extension results are incomplete")
    return {
        "metrics": load_csv(RESULTS / "metrics.csv"),
        "effects": load_csv(RESULTS / "confirmatory_effects.csv"),
        "descriptive": load_csv(RESULTS / "descriptive_summary.csv"),
        "annotation_policy": load_csv(RESULTS / "annotation_policy_sensitivity.csv"),
        "pareto": load_csv(RESULTS / "pareto_frontier_summary.csv"),
        "competing": load_csv(RESULTS / "competing_risk_summary.csv"),
        "secondary_integrity": secondary_integrity,
        "execution": execution,
        "integrity": integrity,
        "verification": verification,
        "agreement": json.loads((ROOT / "expert_labels" / "expert_label_agreement.json").read_text(encoding="utf-8")),
        "annotation": json.loads((ROOT / "expert_labels" / "llm_annotation_validation.json").read_text(encoding="utf-8")),
        "manifest": json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8")),
        "real_llm_dry_run": json.loads((ROOT / "real_llm_pilot" / "pilot_output" / "dry_run_manifest.json").read_text(encoding="utf-8")),
        "ability_evidence": json.loads((ROOT / "real_llm_pilot" / "final_team_evidence.json").read_text(encoding="utf-8")),
        "concurrency_audit": json.loads((ROOT / "real_llm_pilot" / "concurrent_runner_audit.json").read_text(encoding="utf-8")),
        "real_main_validation": real_main,
        "real_main_descriptive": load_csv(REAL_LLM_MAIN / "real_llm_descriptive.csv"),
        "real_main_pairwise": load_csv(REAL_LLM_MAIN / "real_llm_pairwise.csv"),
        "real_extension_validation": real_extension,
        "real_extension_descriptive": load_csv(REAL_LLM_EXTENSION / "extension_descriptive.csv"),
        "real_extension_pairwise": load_csv(REAL_LLM_EXTENSION / "extension_pairwise.csv"),
    }


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=55, start=55, bottom=55, end=55) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_columns(section, count: int, space_twips: int = 300) -> None:
    sect_pr = section._sectPr
    cols = sect_pr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sect_pr.append(cols)
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), str(space_twips))


def add_page_number(section, font: str = "Times New Roman", size: float = 8) -> None:
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.font.name = font
    run.font.size = Pt(size)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr, fld_char2])


def set_run_font(run, name: str, size: float | None = None, bold: bool | None = None, color: str | None = None) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_text(
    paragraph,
    text: str,
    *,
    font: str,
    size: float,
    bold: bool = False,
    italic: bool = False,
    color: str | None = None,
) -> None:
    # Word's Times New Roman/TH Sarabun fallback is inconsistent for several
    # mathematical Unicode glyphs in automated PDF export.  Keep the source
    # prose readable while emitting portable ASCII equivalents in the DOCX.
    portable_text = text.translate(str.maketrans({
        "·": "*",
        "×": "x",
        "Δ": "delta",
        "α": "alpha",
        "θ": "theta",
        "κ": "kappa",
        "ρ": "rho",
        "τ": "tau",
        "→": "->",
        "−": "-",
    }))
    run = paragraph.add_run(portable_text)
    set_run_font(run, font, size, bold, color)
    run.italic = italic


def format_table(table, *, font: str, size: float, header_fill: str = "D9EAF7") -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    if table.rows:
        set_repeat_table_header(table.rows[0])
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if row_index == 0:
                shade_cell(cell, header_fill)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.space_before = Pt(0)
                if row_index == 0:
                    # Prevent a repeated header from being stranded as the
                    # final line on a page without at least one data row.
                    paragraph.paragraph_format.keep_with_next = True
                for run in paragraph.runs:
                    run.text = run.text.translate(str.maketrans({
                        "·": "*", "×": "x", "Δ": "delta", "α": "alpha",
                        "θ": "theta", "κ": "kappa", "ρ": "rho", "τ": "tau",
                        "→": "->", "−": "-",
                    }))
                    set_run_font(run, font, size, row_index == 0)


def add_caption(doc: Document, text: str, *, font: str, size: float = 8):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(5)
    add_text(paragraph, text, font=font, size=size)
    return paragraph


def add_bullet(doc: Document, text: str, *, font: str, size: float, level: int = 0) -> None:
    paragraph = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    paragraph.paragraph_format.space_after = Pt(2)
    add_text(paragraph, text, font=font, size=size)


def effect_index(effects: list[dict]) -> dict[tuple[str, str, str, str], dict]:
    return {(row["family"], row["stratum"], row["contrast"], row["metric"]): row for row in effects}


def f(row: dict, key: str) -> float:
    return float(row[key])


def pct(row: dict) -> str:
    reference = f(row, "right_seed_median")
    difference = f(row, "paired_seed_median_difference")
    if reference == 0 or not math.isfinite(reference):
        return f"{difference:+.3f}"
    return f"{100 * difference / abs(reference):+.1f}%"


def delta(row: dict, digits: int = 3) -> str:
    return f"{f(row, 'paired_seed_median_difference'):+.{digits}f}"


def ci(row: dict, digits: int = 3) -> str:
    return f"[{f(row, 'bootstrap_ci_low'):.{digits}f}, {f(row, 'bootstrap_ci_high'):.{digits}f}]"


def star(row: dict) -> str:
    return "*" if f(row, "p_holm") < 0.05 else ""


def yn(value: str) -> str:
    return "Yes" if value.lower() == "true" else "No"


def abstract_text(data: dict) -> str:
    idx = effect_index(data["effects"])
    rq1 = [idx[("RQ1", resource, f"CF_FIT_minus_{comp}", metric)]
           for resource in ("R0", "R1")
           for comp in ("S1", "S2", "S3", "CENTRAL_FIT")
           for metric in ("cost_per_verified_task",)]
    cost_favorable = sum(f(row, "paired_seed_median_difference") < 0 for row in rq1)
    cost_sig = sum(f(row, "paired_seed_median_difference") < 0 and f(row, "p_holm") < 0.05 for row in rq1)
    completion_ni = sum(
        idx[("RQ1", resource, f"CF_FIT_minus_{comp}", "task_completion_rate")]["noninferiority_pass"].lower() == "true"
        for resource in ("R0", "R1") for comp in ("S1", "S2", "S3", "CENTRAL_FIT")
    )
    return (
        "Heterogeneous large-language-model agents differ in capability, latency, token demand, and cost, "
        "yet task assignment is commonly fixed or centrally controlled. This paper presents ConveyorFlow, "
        "a decentralized assignment mechanism in which idle agents inspect dependency-ready tasks on a shared "
        "belt, assess capability-task fit locally, volunteer, and temporarily stand down when overqualified. "
        "A pre-specified discrete-event simulation, frozen before execution, evaluated public-data-derived ML-build and bug-fix workloads "
        "across 22,500 unique runs and 50 paired seeds. Against static controls, CF-Fit increased verified "
        "throughput by 9.4-45.3% and reduced P95 terminal flow time by 67.9-83.1%, but increased cost by "
        "4.7-52.4% and explicit dead letters as it converted horizon backlog into terminal outcomes. Against a "
        "matched centralized fit controller, cost and time were near parity, throughput was 1.1-1.5% lower, and "
        f"completion non-inferiority passed in {completion_ni}/8 prespecified contrasts. Controlled team "
        "compositions show that capability heterogeneity is beneficial only conditional on resource mapping. "
        "Ablations identify fit, assessment, and aging as consequential components, while stand-down is a bounded "
        "refinement. In a supplementary ten-seed Real-LLM study, CF-Fit delivered 99.5% higher throughput and "
        "62.1% lower wall time than static round robin, but 24.7% lower completion and 62.1% higher cost per "
        "verified task; it detected no metric-level difference from a "
        "centralized fit matcher at the prespecified threshold; a separately frozen extension probes stand-down "
        "and homogeneous-team boundary conditions. ConveyorFlow is therefore supported as an interpretable "
        "trade-off mechanism rather than a universally dominant allocator."
    )


def family_counts(data: dict, family: str) -> dict:
    rows = [row for row in data["effects"] if row["family"] == family and row["direction"] == "left-minus-right"]
    by_metric = {metric: [row for row in rows if row["metric"] == metric] for metric in METRICS}
    return {
        "contrasts": len(by_metric["cost_per_verified_task"]),
        "cost_lower": sum(f(row, "paired_seed_median_difference") < 0 for row in by_metric["cost_per_verified_task"]),
        "cost_lower_sig": sum(f(row, "paired_seed_median_difference") < 0 and f(row, "p_holm") < 0.05 for row in by_metric["cost_per_verified_task"]),
        "throughput_higher": sum(f(row, "paired_seed_median_difference") > 0 for row in by_metric["verified_throughput"]),
        "throughput_higher_sig": sum(f(row, "paired_seed_median_difference") > 0 and f(row, "p_holm") < 0.05 for row in by_metric["verified_throughput"]),
        "p95_lower": sum(f(row, "paired_seed_median_difference") < 0 for row in by_metric["p95_terminal_flow_time"]),
        "p95_lower_sig": sum(f(row, "paired_seed_median_difference") < 0 and f(row, "p_holm") < 0.05 for row in by_metric["p95_terminal_flow_time"]),
        "all_sig": sum(f(row, "p_holm") < 0.05 for row in rows),
        "all_rows": len(rows),
    }


def rq1_ni_counts(data: dict) -> dict[str, int]:
    rows = [row for row in data["effects"] if row["family"] == "RQ1"]
    return {
        metric: sum(
            row["noninferiority_pass"].lower() == "true"
            for row in rows if row["metric"] == metric
        )
        for metric in ("task_completion_rate", "dead_letter_rate", "unsettled_rate")
    }


def english_family_summary(data: dict, family: str) -> str:
    counts = family_counts(data, family)
    n = counts["contrasts"]
    return (
        f"Across {n} prespecified resource-stratified contrasts, the left-hand mechanism had lower cost in "
        f"{counts['cost_lower']}/{n} cases ({counts['cost_lower_sig']} Holm-significant), higher throughput in "
        f"{counts['throughput_higher']}/{n} ({counts['throughput_higher_sig']} significant), and lower P95 "
        f"terminal time in {counts['p95_lower']}/{n} ({counts['p95_lower_sig']} significant)."
    )


def thai_family_summary(data: dict, family: str) -> str:
    counts = family_counts(data, family)
    n = counts["contrasts"]
    return (
        f"สรุป {n} contrasts: ด้านซ้ายมีต้นทุนต่ำกว่า {counts['cost_lower']}/{n} "
        f"({counts['cost_lower_sig']} กรณี significant หลัง Holm), throughput สูงกว่า "
        f"{counts['throughput_higher']}/{n} ({counts['throughput_higher_sig']} significant) และ P95 ต่ำกว่า "
        f"{counts['p95_lower']}/{n} ({counts['p95_lower_sig']} significant)"
    )
    return (
        "Heterogeneous large-language-model agent teams create an allocation problem in which capability, "
        "latency, and cost can conflict. This paper presents ConveyorFlow, a decentralized decision mechanism "
        "in which idle agents inspect an ordered ready-task belt, estimate their own probability of success and "
        "effort, volunteer according to capability–task fit, and temporarily stand down when overqualified. "
        "A preregistered discrete-event simulation compared CF-Fit with three static allocations and a "
        "centralized fit matcher across machine-learning-build and bug-fix workloads derived from three public "
        f"corpora. The confirmatory design comprised {int(data['integrity']['observed_runs']):,} unique runs over "
        "50 paired seeds, two resource regimes, three loads, controlled team compositions, mechanism ablations, "
        "and fallback stress tests. Paired seed-cluster bootstrap intervals, Wilcoxon signed-rank tests, and Holm "
        f"correction were used. CF-Fit had a lower median cost per verified task in {cost_favorable}/8 "
        f"resource-stratified RQ1 contrasts ({cost_sig}/8 Holm-significant), while the prespecified completion "
        f"non-inferiority condition held in {completion_ni}/8 contrasts. Heterogeneity, component ablation, and "
        "no-volunteer analyses showed context-dependent effects rather than universal dominance. The evidence "
        "supports ConveyorFlow as a transparent trade-off mechanism and isolates self-assessment, fit, aging, "
        "and stand-down as testable components. Conclusions are simulation-conditional; role-conditioned LLM "
        "difficulty annotations are reproducible design inputs, not human-validated ground truth."
    )


def setup_ieee_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.62)
    section.bottom_margin = Inches(0.62)
    section.left_margin = Inches(0.64)
    section.right_margin = Inches(0.64)
    set_columns(section, 1)
    add_page_number(section)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(9.5)
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.0
    for style_name, size in (("Title", 20), ("Heading 1", 10), ("Heading 2", 9.5), ("Heading 3", 9)):
        style = styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
    styles["Heading 1"].font.all_caps = True
    return doc


def ieee_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(3)
    add_text(paragraph, text, font="Times New Roman", size=10 if level == 1 else 9.5, bold=True)


def ieee_paragraph(doc: Document, text: str, *, first_line: bool = True) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Inches(0.14) if first_line else None
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.0
    add_text(paragraph, text, font="Times New Roman", size=9.5)


def add_full_width_section(doc: Document) -> None:
    section = doc.add_section(WD_SECTION.CONTINUOUS)
    section.top_margin = Inches(0.62)
    section.bottom_margin = Inches(0.62)
    section.left_margin = Inches(0.64)
    section.right_margin = Inches(0.64)
    set_columns(section, 1)


def add_two_column_section(doc: Document) -> None:
    section = doc.add_section(WD_SECTION.CONTINUOUS)
    section.top_margin = Inches(0.62)
    section.bottom_margin = Inches(0.62)
    section.left_margin = Inches(0.64)
    section.right_margin = Inches(0.64)
    set_columns(section, 2, 300)


def add_ieee_result_table(doc: Document, data: dict, family: str) -> None:
    idx = effect_index(data["effects"])
    add_full_width_section(doc)
    if family == "RQ1":
        headers = ["Regime", "Comparator", "Cost", "Throughput", "P95 time", "Completion NI", "Dead NI", "Unsettled NI"]
        rows = []
        for resource in ("R0", "R1"):
            for comp in ("S1", "S2", "S3", "CENTRAL_FIT"):
                contrast = f"CF_FIT_minus_{comp}"
                cost = idx[("RQ1", resource, contrast, "cost_per_verified_task")]
                thr = idx[("RQ1", resource, contrast, "verified_throughput")]
                p95 = idx[("RQ1", resource, contrast, "p95_terminal_flow_time")]
                completion = idx[("RQ1", resource, contrast, "task_completion_rate")]
                dead = idx[("RQ1", resource, contrast, "dead_letter_rate")]
                unsettled = idx[("RQ1", resource, contrast, "unsettled_rate")]
                rows.append([resource, comp, pct(cost)+star(cost), pct(thr)+star(thr), pct(p95)+star(p95), yn(completion["noninferiority_pass"]), yn(dead["noninferiority_pass"]), yn(unsettled["noninferiority_pass"])])
        caption = "TABLE II. CF-FIT MINUS COMPARATOR: PAIRED MEDIAN EFFECTS AND NON-INFERIORITY"
    elif family == "RQ2":
        headers = ["Regime", "Contrast", "Cost", "Throughput", "P95 time", "Completion Δ", "95% CI (completion)"]
        rows = []
        for resource in ("R0", "R1"):
            for contrast in ("H1_minus_H0", "H2_minus_H0", "H2_minus_H1"):
                cost = idx[("RQ2", resource, contrast, "cost_per_verified_task")]
                thr = idx[("RQ2", resource, contrast, "verified_throughput")]
                p95 = idx[("RQ2", resource, contrast, "p95_terminal_flow_time")]
                completion = idx[("RQ2", resource, contrast, "task_completion_rate")]
                rows.append([resource, contrast.replace("_minus_", "−"), pct(cost)+star(cost), pct(thr)+star(thr), pct(p95)+star(p95), delta(completion)+star(completion), ci(completion)])
        caption = "TABLE III. CAPABILITY-HETEROGENEITY EFFECTS UNDER CF-FIT"
    elif family == "RQ3":
        headers = ["Regime", "Full−ablation", "Cost", "Throughput", "P95 time", "Completion Δ", "Cost 95% CI"]
        labels = {"A1": "A1 assessment", "A2": "A2 fit", "A3": "A3 stand-down", "A4": "A4 aging"}
        rows = []
        for resource in ("R0", "R1"):
            for name in ("A1", "A2", "A3", "A4"):
                contrast = f"FULL_minus_{name}"
                cost = idx[("RQ3", resource, contrast, "cost_per_verified_task")]
                thr = idx[("RQ3", resource, contrast, "verified_throughput")]
                p95 = idx[("RQ3", resource, contrast, "p95_terminal_flow_time")]
                completion = idx[("RQ3", resource, contrast, "task_completion_rate")]
                rows.append([resource, labels[name], pct(cost)+star(cost), pct(thr)+star(thr), pct(p95)+star(p95), delta(completion)+star(completion), ci(cost)])
        caption = "TABLE IV. MECHANISM ABLATIONS; DIRECTION IS FULL MINUS ABLATION"
    else:
        headers = ["Regime", "Contrast", "Cost", "Throughput", "P95 time", "Dead-letter Δ", "Unsettled Δ"]
        rows = []
        for resource in ("R0", "R1"):
            for name in ("F0", "F1", "F3"):
                contrast = f"F2_minus_{name}"
                cost = idx[("E4", resource, contrast, "cost_per_verified_task")]
                thr = idx[("E4", resource, contrast, "verified_throughput")]
                p95 = idx[("E4", resource, contrast, "p95_terminal_flow_time")]
                dead = idx[("E4", resource, contrast, "dead_letter_rate")]
                unsettled = idx[("E4", resource, contrast, "unsettled_rate")]
                rows.append([resource, f"F2−{name}", pct(cost)+star(cost), pct(thr)+star(thr), pct(p95)+star(p95), delta(dead)+star(dead), delta(unsettled)+star(unsettled)])
        caption = "TABLE V. DEFAULT F2 FALLBACK MINUS ALTERNATIVES"
    caption_paragraph = add_caption(doc, caption, font="Times New Roman", size=8)
    caption_paragraph.paragraph_format.keep_with_next = True
    table = doc.add_table(rows=1, cols=len(headers))
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = str(value)
    format_table(table, font="Times New Roman", size=7.4, header_fill="D9EAF7")
    note = doc.add_paragraph()
    note.paragraph_format.space_before = Pt(2)
    add_text(note, "* Holm-adjusted p<0.05. Percent entries are paired median differences relative to the comparator median.", font="Times New Roman", size=7.5, italic=True)
    add_two_column_section(doc)


def real_desc_index(rows: list[dict], key: str) -> dict[tuple[str, str], dict]:
    return {(row[key], row["metric"]): row for row in rows}


def real_pair_index(rows: list[dict], left_key: str, right_key: str) -> dict[tuple[str, str, str], dict]:
    return {(row[left_key], row[right_key], row["metric"]): row for row in rows}


def add_real_llm_table(
    doc: Document,
    *,
    rows: list[dict],
    key: str,
    order: list[str],
    labels: dict[str, str],
    caption: str,
) -> None:
    index = real_desc_index(rows, key)
    add_full_width_section(doc)
    add_caption(doc, caption, font="Times New Roman", size=8)
    table = doc.add_table(rows=1, cols=7)
    headers = ["Condition", "N (primary/timing)", "Completion", "Cost / verified", "Wall time (s)", "Throughput / s", "Utilization"]
    for column, value in enumerate(headers):
        table.rows[0].cells[column].text = value
    for name in order:
        cells = table.add_row().cells
        values = [
            labels[name],
            f"{int(f(index[(name, 'completion_rate')], 'n'))}/{int(f(index[(name, 'run_wall_time_seconds')], 'n'))}",
            f"{100 * f(index[(name, 'completion_rate')], 'mean'):.2f}%",
            f"${f(index[(name, 'cost_per_verified_task')], 'mean'):.6f}",
            f"{f(index[(name, 'run_wall_time_seconds')], 'mean'):.2f}",
            f"{f(index[(name, 'verified_throughput_per_second')], 'mean'):.5f}",
            f"{100 * f(index[(name, 'resource_utilization')], 'mean'):.2f}%",
        ]
        for column, value in enumerate(values):
            cells[column].text = value
    format_table(table, font="Times New Roman", size=7.1, header_fill="D9EAF7")
    add_two_column_section(doc)


def extension_contrast_sentence(data: dict, left: str, role: str) -> str:
    index = real_pair_index(
        data["real_extension_pairwise"], "left_condition", "right_condition"
    )
    completion = index[(left, "HET_FULL", "completion_rate")]
    cost = index[(left, "HET_FULL", "cost_per_verified_task")]
    wall = index[(left, "HET_FULL", "run_wall_time_seconds")]
    throughput = index[(left, "HET_FULL", "verified_throughput_per_second")]
    utilization = index[(left, "HET_FULL", "resource_utilization")]
    significant = [
        label
        for label, row in (
            ("completion", completion),
            ("cost per verified task", cost),
            ("wall time", wall),
            ("throughput", throughput),
            ("utilization", utilization),
        )
        if f(row, "p_holm") < 0.05
    ]
    significant_text = ", ".join(significant) if significant else "none of the reported outcomes"
    return (
        f"{role} changed completion by {100 * f(completion, 'mean_difference_left_minus_right'):+.2f} percentage points "
        f"and cost per verified task by {f(cost, 'relative_mean_change_percent'):+.2f}%. "
        f"The cross-window wall time, throughput, and utilization changes were "
        f"{f(wall, 'relative_mean_change_percent'):+.2f}%, "
        f"{f(throughput, 'relative_mean_change_percent'):+.2f}%, and "
        f"{f(utilization, 'relative_mean_change_percent'):+.2f}%, respectively. "
        f"After Holm correction, significant outcomes were: {significant_text}."
    )


def build_ieee(data: dict) -> None:
    doc = setup_ieee_document()
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(8)
    add_text(title, "ConveyorFlow: Decentralized Capability-Aware Self-Selection for Heterogeneous LLM Agent Teams", font="Times New Roman", size=20, bold=True)
    author = doc.add_paragraph()
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(author, "Sakan Punyanon", font="Times New Roman", size=11)
    affiliation = doc.add_paragraph()
    affiliation.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(affiliation, "Affiliation and corresponding-author e-mail to be confirmed before submission", font="Times New Roman", size=8, italic=True)

    abstract = doc.add_paragraph()
    abstract.paragraph_format.left_indent = Inches(0.25)
    abstract.paragraph_format.right_indent = Inches(0.25)
    abstract.paragraph_format.space_before = Pt(8)
    add_text(abstract, "Abstract—", font="Times New Roman", size=9, bold=True, italic=True)
    add_text(abstract, abstract_text(data), font="Times New Roman", size=9)
    keywords = doc.add_paragraph()
    keywords.paragraph_format.left_indent = Inches(0.25)
    keywords.paragraph_format.right_indent = Inches(0.25)
    add_text(keywords, "Index Terms—", font="Times New Roman", size=9, bold=True, italic=True)
    add_text(keywords, "decentralized task allocation, heterogeneous agents, large language models, self-selection, discrete-event simulation", font="Times New Roman", size=9)

    add_two_column_section(doc)
    ieee_heading(doc, "I. INTRODUCTION")
    ieee_paragraph(doc, "Teams of large-language-model (LLM) agents increasingly divide complex work into specialized roles. Existing frameworks demonstrate the value of structured conversations and role-based workflows [1]–[3], yet assignment is often fixed in advance or delegated to a central orchestrator. That assumption becomes consequential when agent capability, service time, token demand, and price differ: sending every task to the most capable agent can be accurate but expensive, while routing every task to a cheap agent can increase retries and tail latency.")
    ieee_paragraph(doc, "ConveyorFlow treats allocation as a stream of dependency-ready tasks on a shared belt. Idle agents inspect a bounded window, assess the visible task locally, and volunteer. The assignment decision is decentralized—there is no component that globally ranks all agents for CF-Fit—although the ready belt, atomic claim operation, and event ledger remain shared coordination infrastructure. This distinction avoids the stronger and unsupported claim that the entire system is fully distributed.")
    ieee_paragraph(doc, "The scientific contribution is therefore not a catalog of policies. It is a connected mechanism: capability heterogeneity creates a reason for local selection; capability–task fit shapes volunteering; an overqualified agent can stand down temporarily; and task aging relaxes hesitation so that low-fit work does not wait indefinitely. The study asks how this mechanism changes a vector of cost, throughput, completion time, utilization, and failure outcomes, rather than requiring a universal winner.")
    ieee_paragraph(doc, "The contributions are threefold: (1) a reproducible decentralized self-selection mechanism with explicit fit, stand-down, aging, and bounded no-volunteer behavior; (2) a controlled design that changes capability variance while holding team size and mean latent ability constant; and (3) a pre-specified event-ledger simulation, frozen before execution, with public-data-derived workloads, static and centralized controls, component ablations, fallback stress tests, and annotation/resource robustness analyses.")

    ieee_heading(doc, "II. RELATED WORK")
    ieee_paragraph(doc, "Classical distributed task allocation includes negotiation protocols such as Contract Net [7], formal task-allocation taxonomies [8], [9], and consensus-based decentralized auctions [10]. These approaches establish that local or market-based decisions can reduce dependence on a central controller, but their communication, bidding, and objective assumptions differ from a shared ready-belt architecture for LLM-agent work.")
    ieee_paragraph(doc, "LLM multi-agent systems such as AutoGen, MetaGPT, ChatDev, CAMEL, and AgentVerse coordinate specialized agents through conversation, role play, or standardized workflows [1]–[5]. A recent survey organizes this broader design space by environment interface, profiling, communication, and capability acquisition [6]. ConveyorFlow is complementary: it isolates who chooses a ready task and why, using capability fit and bounded stand-down rather than prescribing a full conversational software-development process. The controlled simulation provides the primary causal comparisons, while the completed Real-LLM study supplies narrower implementation-level evidence under dated provider aliases and deterministic validators.")
    ieee_paragraph(doc, "The task-difficulty protocol is informed by work on LLM-based evaluation [11], while studies of prompting choices and judge bias motivate a strict validity boundary [12], [13]. Three role-conditioned passes from the same underlying model measure procedural stability, not inter-expert human agreement or external ground truth. This limitation is carried into the robustness design and the claims.")

    ieee_heading(doc, "III. SYSTEM MODEL AND OBJECTIVE")
    ieee_paragraph(doc, "A job is a finite directed acyclic graph (DAG). A task enters the ordered READY frontier only after all dependencies are verified. The system contains at most four agents. An agent has workload-specific latent ability θ, a speed factor, a token factor, and a price factor; ability is deliberately separated from resource cost.")
    ieee_paragraph(doc, "The primary objective is to reduce cost per verified task subject to prespecified completion-quality constraints. Completion non-inferiority requires the lower confidence limit of CF-Fit minus comparator to be at least −0.03. Dead-letter and unsettled non-inferiority require the upper confidence limit to be at most +0.03. Verified throughput and P95 terminal flow time are key secondary outcomes; utilization is explanatory and is not assumed to be better merely because it is higher.")
    ieee_paragraph(doc, "No post-hoc weighted score collapses these outcomes. A policy can be cheaper but slower, faster but less complete, or operationally attractive only under one resource regime. The estimand is thus a trade-off vector conditional on workload, load, team composition, and resource mapping.")

    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(DRAWIO_FIGURES / "architecture_system.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 1. ConveyorFlow system architecture. Frozen workloads, allocation rules, and ability/resource profiles feed one state-machine core. The assessor, executor, and verifier interfaces are implemented by both the 22,500-run simulation tier and the 60-case Real-LLM tier; both tiers write append-only ledgers that drive the same metric and analysis pipeline.", font="Times New Roman", size=8)
    add_two_column_section(doc)

    ieee_heading(doc, "IV. CONVEYORFLOW MECHANISM")
    ieee_heading(doc, "A. Local Observation and Eligibility", level=2)
    ieee_paragraph(doc, "Each idle agent scans at most K_scan=8 visible READY tasks. For each task it estimates difficulty d-hat, pass probability p-hat, effort, and confidence. A task is eligible only when skill constraints and retry-diversity rules hold and p-hat exceeds an age-dependent threshold τ(age). The default threshold decreases from 0.60 to 0.50 and then 0.35 as waiting increases.")
    ieee_heading(doc, "B. Capability Fit and Stand-Down", level=2)
    ieee_paragraph(doc, "For an eligible task, the local claim delay combines capability mismatch, overqualification, urgency, and deterministic keyed jitter: backoff = |level−d-hat| + 0.8·max(0, level−d-hat)·(1−urgency) − 0.5·urgency + jitter. An overqualified agent therefore hesitates early, preserving advanced capacity for difficult work. This is bounded hesitation, not permanent refusal: the penalty decays with age and is removed at the second aging threshold.")
    ieee_heading(doc, "C. Atomic Claim and No-Volunteer Handling", level=2)
    ieee_paragraph(doc, "Each agent selects at most one candidate. Claims are ordered by local claim time and resolved by an atomic compare-and-swap abstraction; losing agents return to the next decision round. Under the default F2 mechanism, tasks are re-offered, moved to the tail at W1=8 and W2=20, and evaluated with relaxed thresholds and stand-down. At W3=50 or after eight requeues, the task becomes DEAD_LETTER and dependent work is terminally accounted. F3 instead forces a centrally selected rescue and is reported only as a hybrid reference.")

    ieee_heading(doc, "D. End-to-End Process Architecture", level=2)
    ieee_paragraph(doc, "Figure 2 traces one task from belt admission through self-assessment, volunteering or stand-down, atomic claiming, execution, deterministic verification, artifact publication, retry, and terminal accounting. The decision boundary is explicit: the belt broadcasts only READY work; each idle agent independently evaluates can-do status, estimated difficulty, and confidence; and the claim primitive resolves races without selecting a preferred agent. A failed attempt returns to the belt while retries remain, whereas the frozen retry bound produces ABANDONED/DEAD_LETTER accounting. A job is complete only when every constituent task is verified DONE.")
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(DRAWIO_FIGURES / "architecture_process.png"), width=Inches(4.9))
    add_caption(doc, "Fig. 2. ConveyorFlow process architecture. Heterogeneous Ability Rank 1/2/3 agents observe the same READY belt, self-assess, volunteer or stand down, and contend through an atomic claim. Execution and verification feed the blackboard and either complete the job or re-enter bounded retry handling. Editable source: page 'ConveyorFlow - Process Architecture' in ConveyorFlow_diagrams_en_working.drawio.", font="Times New Roman", size=8)
    add_two_column_section(doc)

    ieee_heading(doc, "E. Controlled Belt Comparison and Tick Semantics", level=2)
    ieee_paragraph(doc, "Figures 3 and 4 make the experimental control explicit. Both CF-Fit and the static baseline receive the same dependency-released tasks, place them on the same ordered READY belt, use the same execution and verification semantics, and apply the same retry and terminal-accounting rules. What changes is allocation authority. Under CF-Fit, every idle agent observes a bounded belt window, evaluates capability-task fit locally, and may volunteer or stand down. The shared atomic claim operation only resolves simultaneous claims; it does not globally rank agent-task pairs.")
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(DRAWIO_FIGURES / "cf_fit_belt.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 3. CF-Fit task flow. Dependency-ready tasks ride the shared belt; idle heterogeneous agents independently assess visible tasks, volunteer when eligible, and use an atomic claim only to resolve collisions. The editable source is the page 'Belt - CF-Fit (P3)' in ConveyorFlow_diagrams_en_working.drawio.", font="Times New Roman", size=8)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(DRAWIO_FIGURES / "baseline_static.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 4. Static-allocation control on the same belt. A task-to-agent rule is fixed before execution, so agents do not self-select at run time; arrivals, readiness, execution, verification, and failure accounting remain controlled. The editable source is the page 'Baseline - Static assignment (P0_FIXED)' in ConveyorFlow_diagrams_en_working.drawio.", font="Times New Roman", size=8)
    add_two_column_section(doc)
    ieee_paragraph(doc, "In the static control, a frozen ownership or routing table assigns each task class before the run; an idle agent merely executes work already mapped to it. Therefore, observed differences cannot be attributed to a different queue, workload, dependency rule, or verifier. They estimate the effect of changing from predetermined allocation to decentralized self-selection under otherwise matched simulation conditions. Central-Fit is a separate active centralized comparator: it uses comparable assessment and fit inputs but a global matcher selects the assignment.")
    ieee_paragraph(doc, "Figure 5 defines one simulation tick and prevents ambiguity about causality. The engine first applies scheduled churn, collects arrivals, admits tasks whose dependencies are verified, and refreshes belt order and age. Idle agents then scan, assess, and emit at most one claim. Atomic resolution starts non-conflicting winners; execution, verification, cost, tokens, busy time, retries, and terminal states are then recorded in the immutable event ledger. A failed task is re-offered while attempts remain. If no agent volunteers, F2 keeps the task on the belt, ages and requeues it with relaxed thresholds, and eventually sends it to DEAD_LETTER after the prespecified wait/requeue bounds. The run terminates only when the belt is empty, no agent is busy, and no future arrival or dependency release remains.")
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(DRAWIO_FIGURES / "one_tick.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 5. One deterministic simulation tick, in execution order. The same tick skeleton is used by all policies; only the allocation-decision block changes. Editable source: page 'One tick of the conveyor, in order' in ConveyorFlow_diagrams_en_working.drawio.", font="Times New Roman", size=8)
    add_two_column_section(doc)

    ieee_heading(doc, "V. METHODOLOGY")
    ieee_heading(doc, "A. Public Workload Sources", level=2)
    ieee_paragraph(doc, "Workload distributions were derived from UCI Adult (48,842 records) [14], UCI Beijing Multi-Site Air Quality (420,768 records) [15], and the CodeXGLUE Bugs2Fix small training corpus (46,680 buggy/fixed function pairs) [16]. Adult and Beijing instantiate seven-stage ML-build DAGs; Bugs2Fix instantiates five-stage reproduce–localize–repair–regression-test–report DAGs. Bugs2Fix pairs provide distributional characteristics only and are not represented as executable repository tests. Source URLs, licenses, byte counts, and SHA-256 hashes were frozen in the data manifest.")
    ieee_heading(doc, "B. Operational Task Difficulty", level=2)
    agreement = data["agreement"]["pairwise_agreement"]
    kappas = [value["quadratic_weighted_kappa"] for value in agreement.values()]
    exacts = [value["exact_agreement"] for value in agreement.values()]
    distribution = data["annotation"]["adjudicated_distribution"]
    ieee_paragraph(doc, f"Difficulty was operationalized over 304 stage-by-stratum specifications from 48 deterministic public-data-derived variants. Three blinded passes used the same underlying LLM under ML Methodologist, Software Reliability Reviewer, and Workflow/Resource Reviewer roles. Five rubric dimensions were scored 0–2; totals 0–3, 4–6, and 7–10 mapped to D1, D2, and D3. Pairwise exact agreement ranged from {min(exacts):.3f} to {max(exacts):.3f}; quadratic-weighted κ [20] ranged from {min(kappas):.3f} to {max(kappas):.3f}; adjacent agreement was 1.000. Ninety-four non-unanimous items were separately adjudicated, yielding D1={distribution['1']}, D2={distribution['2']}, and D3={distribution['3']}. Seventeen decisions differed from mechanical consensus. The frozen label SHA-256 is 56207cd87a28ab221911c2bf07ee0cf6f8ec6547bab7880fc5ef268ad24b2add.")
    ieee_paragraph(doc, "The passes are not independent human experts. Their agreement is evidence of same-model procedural stability only. The minimum subgroup κ was 0.628 for one Beijing rater pair; lower and upper vote mappings, each changing 47 labels, were therefore retained as sensitivity bounds.")
    ieee_heading(doc, "C. Ability and Team Compositions", level=2)
    ieee_paragraph(doc, "Ability is represented by three behavioral ranks rather than model names. Ability Rank 1, 2, and 3 (AR1–AR3) use θ=−1, 0, and +1 in logit[P(pass)] = α_w + 0.85θ − 1.2(d−2), with α_Adult=0.88 and α_Beijing=α_Bugs2Fix=0.86. H0=(2,2,2,2), H1=(1,2,2,3), and H2=(1,1,3,3) all have four agents and mean rank 2, but variances 0, 0.5, and 1. These boundary compositions isolate capability variance. AR1×4 is used only as a fallback stress team.")
    ieee_heading(doc, "D. Controls, Ablations, and Resource Regimes", level=2)
    ieee_paragraph(doc, "Static controls are fixed skill ownership (S1), precomputed difficulty-level routing (S2), and precomputed round robin (S3). Central-Fit uses comparable assessment and fit inputs but globally matches free agents and tasks. Ablations remove assessment (A1), fit (A2), stand-down (A3), or aging (A4). R0 equalizes speed, token, and price factors. R1 associates AR1/AR2/AR3 with speed 0.90/1.00/1.15, token factor 0.80/1.00/1.30, and price factor 0.50/1.00/3.00. Reversed and permuted mappings test resource confounding.")

    add_full_width_section(doc)
    add_caption(doc, "TABLE I. CONFIRMATORY EXPERIMENT DESIGN", font="Times New Roman", size=8)
    table = doc.add_table(rows=1, cols=6)
    headers = ["Block", "Policies / factors", "Team", "Load", "Resource", "Memberships"]
    for i, value in enumerate(headers): table.rows[0].cells[i].text = value
    design_rows = [
        ["RQ1", "CF-Fit, S1–S3, Central-Fit", "H1", "low/med/high", "R0/R1", "4,500"],
        ["RQ2", "CF-Fit; H0/H1/H2", "controlled mean", "low/med/high", "R0/R1", "2,700"],
        ["RQ3", "Full, A1–A4", "H1/H2", "med/high", "R0/R1", "6,000"],
        ["E4", "F0–F3; mixed/D3-heavy", "AR1×4/H1", "med/high", "R0/R1", "9,600"],
        ["Sensitivity", "resource + label mappings", "H1", "med/high", "specified", "2,400"],
    ]
    for values in design_rows:
        cells = table.add_row().cells
        for i, value in enumerate(values): cells[i].text = value
    format_table(table, font="Times New Roman", size=7.5)
    note = doc.add_paragraph()
    add_text(note, "Membership totals overlap where one run satisfies multiple scopes; the frozen design contains 22,500 unique runs.", font="Times New Roman", size=7.5, italic=True)
    add_two_column_section(doc)

    ieee_heading(doc, "E. Experimental Unit and Statistics", level=2)
    ieee_paragraph(doc, "The experimental unit is a complete run/seed within a matched workload–load–team–resource cell. Tasks within a run are not independent replicates. All policies in a matched cell share arrivals, task attributes, and keyed potential outcomes. Main inference uses 50 paired seeds (1000–1049), seed-cluster median effects, 10,000 paired bootstrap resamples with analysis seed 20260922, Wilcoxon signed-rank tests, and Holm correction within each question and metric family [17]–[19]. Zero-success runs remain infeasible rather than being replaced by zero; dead-letter and unsettled tasks are never dropped.")
    ieee_paragraph(doc, f"The execution completed {int(data['integrity']['observed_runs']):,} unique runs with {int(data['integrity']['duplicate_run_ids']):,} duplicate IDs and {int(data['integrity']['zero_success_runs']):,} zero-success runs. All {int(data['verification']['event_hashes_checked']):,} compressed event ledgers matched their recorded hashes, and the execution source hash matched the current simulation source. The pre-execution source archive SHA-256 was 91e2cec400769fce8cea53682ebfe0b67c93bdc2756b365ad0bf56a1c8995c25.")
    ieee_paragraph(doc, "An infrastructure interruption after 9,654 runs was resumed from the exact checkpoint without changing seeds or configuration. Before execution completed and before comparative effects were computed, the analysis implementation was corrected to separate R0/R1 and add the interactions already required by the frozen plan. Engine, data, outcomes, margins, and exclusions were unchanged; both events are recorded in the protocol-deviation log.")
    ieee_paragraph(doc, "After the confirmatory results were locked, two secondary descriptive analyses were added. Two-objective Pareto frontiers use the RQ1 descriptive medians without forming a weighted score. Competing-risk curves use task creation as time zero, VERIFIED and DEAD_LETTER as competing events, and UNSETTLED work as right-censored at the run horizon. Aalen-Johansen curves are estimated separately for each run and summarized across 450 runs per policy-resource cell; the percentile envelopes describe run heterogeneity and are not confidence intervals. These additions do not change the pre-specified estimands, tests, or multiplicity families.")

    ieee_heading(doc, "F. Simulation Execution and Outcome Construction", level=2)
    ieee_paragraph(doc, "Every paired policy run uses the same fixed observation horizon H, arrival schedule, task attributes, churn schedule, and keyed potential outcomes. A task is offered once its job is admitted and its dependencies permit release. At each tick the engine executes the ordered sequence shown in Fig. 5, then appends state transitions and resource accounts to a compressed event ledger. The simulation never reads a reported metric from mutable live state: outcomes are reconstructed after the run from the ledger. Runs stop at the common horizon; verified work, DEAD_LETTER work, and nonterminal UNSETTLED work are all retained. This prevents one policy from receiving extra drain time and prevents unresolved work from silently disappearing.")
    ieee_paragraph(doc, "Task completion rate is the number of verified tasks divided by all offered tasks; dead-letter and unsettled rates use the same denominator. Verified throughput is verified tasks divided by H. Productive utilization is productive busy ticks divided by H times the number of available agents. Terminal flow time is measured from task creation to either verified completion or terminal failure, and the reported tail statistic is its run-level 95th percentile. Total cost includes all recorded assessment, execution, verification, and retry charges. Cost per verified task divides that total by the verified count; a zero-success run is retained as infeasible rather than assigned a zero cost. These definitions make cost interpretable only together with completion and terminal disposition.")

    ieee_heading(doc, "G. Real-LLM Execution and Validation Protocol", level=2)
    ieee_paragraph(doc, "The Real-LLM tier freezes 60 executable cases: 20 Adult-derived ML cases, 20 Beijing-derived ML cases, and 20 Bugs2Fix-derived repair cases. The selected three-agent team is evaluated under CF-Fit, Static S3, and Central-Fit with ten paired seeds and the same case bundles, eligibility rules, retry limits, and deterministic validators. Each agent holds at most one task, but different agents issue provider calls concurrently without a global round barrier. A successful API response counts as verified only when its task-specific validator passes; pass=false is therefore a functional validation failure, not automatically a provider failure. Provider failures that exhaust the frozen retry rule invalidate the policy run instead of being relabeled as task-quality failures.")
    ieee_paragraph(doc, "For each valid run, completion is verified cases divided by 60, cost is computed from recorded input/output tokens and the frozen observed price metadata, cost per verified task divides total cost by verified cases, throughput divides verified cases by monotonic wall-clock duration, and utilization divides summed agent busy seconds by wall time times three agents. Main comparisons are seed-paired and Holm-adjusted across the prespecified metric family. The extension retains all ten runs per condition for completion and cost. Timing uses the frozen provider-gap rule: timing-valid sample sizes are 10/10/8/9 for HET_FULL, HET_NO_STANDDOWN, HOM_GLM_GENERALIST, and HOM_GPT_PROFILE, respectively; cross-window timing contrasts are exploratory because provider load was not randomized across windows.")

    ieee_heading(doc, "VI. RESULTS")
    ieee_heading(doc, "A. RQ1: Allocation Trade-Offs", level=2)
    ieee_paragraph(doc, "Table II reports CF-Fit minus each control separately for R0 and R1. Percent effects are relative to the comparator median; an asterisk marks Holm-adjusted p<0.05. The non-inferiority columns must be read jointly with cost and speed: a cheaper outcome is not treated as preferable when its completion or terminal-failure constraint is violated.")
    add_ieee_result_table(doc, data, "RQ1")
    ni = rq1_ni_counts(data)
    ieee_paragraph(doc, english_family_summary(data, "RQ1") + f" Completion, dead-letter, and unsettled non-inferiority passed in {ni['task_completion_rate']}/8, {ni['dead_letter_rate']}/8, and {ni['unsettled_rate']}/8 contrasts, respectively.")
    ieee_paragraph(doc, "Against the static controls, CF-Fit increased completion by 4.49–16.39 percentage points and reduced unsettled work by 26.15–57.39 points, but increased explicit dead letters by 17.50–35.84 points. The failed dead-letter margins therefore describe a disposition trade-off: static routing left substantial work unresolved at the horizon, whereas CF-Fit terminalized it. Against Central-Fit, completion was lower by only 0.50 points in R0 and 0.89 points in R1, dead letters were higher by 0.57 and 0.69 points, and all three non-inferiority constraints passed.")
    doc.add_picture(str(FIGURES / "fig2_rq1_cost.png"), width=Inches(3.2))
    add_caption(doc, "Fig. 6. RQ1 paired median cost differences with 95% seed-cluster bootstrap intervals. Negative values favor CF-Fit.", font="Times New Roman", size=8)

    add_full_width_section(doc)
    radar_paragraph = doc.add_paragraph()
    radar_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    radar_paragraph.add_run().add_picture(str(FIGURES / "fig6_rq1_tradeoff_radar.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 7. RQ1 descriptive trade-off profiles. Each axis is min-max normalized within one resource regime so that higher is preferable; the chart is not a composite inferential score.", font="Times New Roman", size=8)
    add_two_column_section(doc)
    ieee_paragraph(doc, "The radar chart is a visualization aid only. It shows why a single winner is inappropriate: CF-Fit and Central-Fit are similar on throughput, terminal time, completion, and unsettled work, whereas different static controls occupy the favorable cost or dead-letter extremes. All formal claims remain based on the prespecified metric-level contrasts and non-inferiority tests.")

    ieee_heading(doc, "B. RQ2: Capability Heterogeneity", level=2)
    ieee_paragraph(doc, "Table III changes capability variance without changing team size or mean level. H2−H0 is the prespecified linear boundary contrast; H1 comparisons reveal whether an effect emerges gradually or only at the extreme composition. R0 isolates capability variance, while R1 evaluates the same composition change when ability is correlated with speed, token use, and price.")
    add_ieee_result_table(doc, data, "RQ2")
    ieee_paragraph(doc, english_family_summary(data, "RQ2") + " Because the direction is the more heterogeneous team minus the less heterogeneous team, signs must be interpreted by metric rather than as an overall heterogeneity benefit.")
    ieee_paragraph(doc, "The large P95 reduction also has a competing-risk explanation: H0 retained a median unsettled fraction of 0.342, while H1 and H2 reached zero unsettled work and had higher explicit dead-letter fractions. Under R0, heterogeneity reduced cost by about 5% but slightly reduced throughput; under R1 it increased cost by 40–82% while improving throughput by 2–5%. Thus, the economic conclusion depends strongly on whether high capability is coupled to high price.")
    doc.add_picture(str(FIGURES / "fig3_rq2_throughput.png"), width=Inches(3.2))
    add_caption(doc, "Fig. 8. RQ2 verified-throughput effects under controlled capability heterogeneity.", font="Times New Roman", size=8)

    ieee_heading(doc, "C. RQ3: Mechanism Contribution", level=2)
    ieee_paragraph(doc, "Full-minus-ablation effects identify which component changes observed outcomes. A null or small A3 effect is retained and interpreted as evidence that stand-down is a bounded refinement rather than the sole source of ConveyorFlow behavior. Assessment, fit, and aging are evaluated independently rather than bundled into a single policy count.")
    add_ieee_result_table(doc, data, "RQ3")
    ieee_paragraph(doc, english_family_summary(data, "RQ3") + " Here, a favorable Full-minus-ablation sign is evidence that the removed component improves that metric; an unfavorable or null sign limits that component claim.")
    ieee_paragraph(doc, "Assessment increased cost by 4.6–6.7% but increased throughput and completion while converting approximately 35–37 points of horizon backlog into terminal outcomes. Fit reduced cost by 3.5–3.7%, raised throughput by about 2.2%, and reduced P95 time by about 12%, although it also shifted some unsettled work to dead letters. Aging produced the clearest completion effect (+10.4–10.8 points) and reduced dead letters by about 12.4 points, at the cost of 77–86% longer P95 terminal time. Stand-down changed cost, throughput, and completion only trivially and slightly worsened P95 time; it is therefore supported only as a bounded refinement, not as the primary mechanism.")
    doc.add_picture(str(FIGURES / "fig4_rq3_cost.png"), width=Inches(3.2))
    add_caption(doc, "Fig. 9. RQ3 cost effects. Direction is full CF-Fit minus each ablation.", font="Times New Roman", size=8)

    ieee_heading(doc, "D. E4: No-Volunteer Fallback", level=2)
    ieee_paragraph(doc, "The fallback analysis combines mixed and D3-heavy task profiles and includes both H1 and the AR1×4 stress team. Terminal time is interpreted together with dead-letter and unsettled fractions to avoid survivorship bias. F3 uses a central rescue decision and therefore cannot be used as evidence for a purely decentralized ConveyorFlow mechanism.")
    add_ieee_result_table(doc, data, "E4")
    ieee_paragraph(doc, english_family_summary(data, "E4") + " The direction is default F2 minus the alternative; therefore the F3 comparison quantifies a decentralization trade-off rather than a like-for-like ConveyorFlow policy change.")
    ieee_paragraph(doc, "Relative to F0/F1, F2 spent longer on terminal disposition but substantially lowered cost and dead-letter fractions while increasing verified throughput. Relative to the hybrid F3 rescue, F2 had similar cost but 3.7–5.7% lower throughput, 9.6–12.2% longer P95 time, and 1.1–1.7 points more dead letters. This is the measured price of retaining decentralized no-volunteer handling in the tested stress conditions.")
    doc.add_picture(str(FIGURES / "fig5_e4_deadletter.png"), width=Inches(3.2))
    add_caption(doc, "Fig. 10. F2-minus-alternative dead-letter effects under no-volunteer stress.", font="Times New Roman", size=8)

    ieee_heading(doc, "E. Robustness", level=2)
    resource_counts = family_counts(data, "RESOURCE")
    annotation_counts = family_counts(data, "ANNOTATION")
    interaction_rows = [row for row in data["effects"] if row["family"] == "RQ1_INTERACTION"]
    interaction_sig = sum(f(row, "p_holm") < 0.05 for row in interaction_rows)
    secondary = data["annotation_policy"]
    cf_s2 = [row for row in secondary if row["contrast"] == "CF_FIT_minus_S2"]
    cf_central = [row for row in secondary if row["contrast"] == "CF_FIT_minus_CENTRAL_FIT"]
    stable_s2 = all(
        f(next(row for row in cf_s2 if row["stratum"] == source and row["metric"] == metric), "paired_seed_median_difference") * sign > 0
        for source in ("frozen_llm", "frozen_llm_lower", "frozen_llm_upper")
        for metric, sign in (("cost_per_verified_task", 1), ("verified_throughput", 1), ("p95_terminal_flow_time", -1))
    )
    central_cost_sig = sum(
        f(row, "p_holm") < 0.05 for row in cf_central if row["metric"] == "cost_per_verified_task"
    )
    ieee_paragraph(doc, f"Resource-mapping effects were recomputed under reversed and permuted R1 assignments; {resource_counts['all_sig']}/{resource_counts['all_rows']} metric-level effects were Holm-significant. Annotation sensitivity reran CF-Fit, S2, and Central-Fit with lower and upper role-vote mappings on medium/high R0 cells; {annotation_counts['all_sig']}/{annotation_counts['all_rows']} absolute-performance effects were Holm-significant. In a transparently labeled secondary derived summary, the CF-Fit-versus-S2 direction for cost (higher), throughput (higher), and P95 time (lower) was stable across all three mappings={stable_s2}; CF-Fit-versus-Central-Fit cost was significant in {central_cost_sig}/3 mappings. The pre-specified policy-by-load, policy-by-workload, and policy-by-resource analysis identified {interaction_sig}/{len(interaction_rows)} Holm-significant difference-in-differences. These analyses test dependence on assumed resource coupling, difficulty boundaries, and context; they do not replace the adjudicated mapping in primary inference.")

    ieee_heading(doc, "F. Secondary Pareto and Competing-Risk Views", level=2)
    ieee_paragraph(doc, "The cost-throughput Pareto frontier contains Central-Fit, Static AR1-only, and Static round-robin in R0, and Central-Fit, Static AR3-only, and Static round-robin in R1. CF-Fit is not economically nondominated because Central-Fit has slightly lower cost and higher throughput in both regimes. In the time-completion space, Central-Fit alone is nondominated in R0, while CF-Fit joins Central-Fit in R1 by trading a 1.5-tick lower median P95 for a 0.86-point lower completion rate. This is descriptive support for the trade-off framing, not a new hypothesis test.")
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(FIGURES / "fig7_rq1_pareto_frontiers.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 11. RQ1 descriptive two-objective Pareto frontiers. Filled markers are nondominated within the displayed metric pair; no cross-metric weighting is applied.", font="Times New Roman", size=8)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(FIGURES / "fig8_rq1_competing_risks.png"), width=Inches(7.0))
    add_caption(doc, "Fig. 12. Run-level Aalen-Johansen cumulative incidence for verified and dead-letter outcomes. Lines are medians across 450 runs; shading is the 2.5th-97.5th percentile run envelope, not a confidence interval.", font="Times New Roman", size=8)
    add_two_column_section(doc)
    ieee_paragraph(doc, "At 1,000 ticks, median verified cumulative incidence for CF-Fit versus Central-Fit was 0.590 versus 0.602 in R0 and 0.615 versus 0.621 in R1; dead-letter incidence was 0.410 versus 0.396 and 0.382 versus 0.378, respectively. Static policies accumulated verified outcomes more slowly and retained more right-censored work. The curves therefore reinforce the primary result: CF-Fit closely tracks the matched centralized controller, while terminal-time summaries alone can favor policies that leave work unresolved.")

    ieee_heading(doc, "G. Pre-Main Real-LLM Ability Calibration", level=2)
    ieee_paragraph(doc, "A separate pre-Main calibration called MFEC deployment aliases on 30 held-out probes per screened model. It did not execute or compare allocation policies. Ability was assigned separately by workload using predeclared Wilson lower-95% gates under a common 4,096 completion-token budget; model name, price, latency, and token use were excluded from rank assignment. A stopping rule selected a three-agent profile-heterogeneous team before any Real-LLM policy run: Tencent HY3 (ML Rank 3/Fix Rank 1), GPT-5 mini (ML Rank 2/Fix Rank 3), and GLM 5.3 Flash (ML Rank 3/Fix Rank 3). These are operational ranks of dated MFEC aliases, not universal model-family rankings.")
    table = doc.add_table(rows=1, cols=4)
    for index, value in enumerate(("MFEC alias", "ML Build", "Fix Bug", "Operational role")):
        table.rows[0].cells[index].text = value
    for values in (
        ("tencent-hy3", "Rank 3", "Rank 1", "ML specialist / basic repair"),
        ("gpt-5-mini", "Rank 2", "Rank 3", "Intermediate ML / advanced repair"),
        ("glm-5.3-flash", "Rank 3", "Rank 3", "Advanced generalist"),
    ):
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = value
    format_table(table, font="Times New Roman", size=8, header_fill="D9EAF7")
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(ABILITY_FIGURES / "fig_ability_profile_radar.png"), width=Inches(6.6))
    add_caption(doc, "Fig. 13. Descriptive pass-rate profiles used for pre-Main team selection. Radar area is not an inferential composite score; ordinal ranks use the prespecified confidence-bound gates.", font="Times New Roman", size=8)
    add_two_column_section(doc)
    ieee_paragraph(doc, "Calibration instrument corrections are fully logged: non-executable exact-match repair was replaced by hidden executable tests; an unintended 1,024-token adapter cap was corrected by rerunning only length-terminated cells at the frozen 4,096-token setting; and safe-parser false rejections were revalidated offline. Original and corrected ledgers were retained. The 60 executable bundles, deployment hashes, provider-reported cost accounting, and reviewed allocation engine were frozen before policy execution.")

    ieee_heading(doc, "H. Supplementary Real-LLM Allocation Validation", level=2)
    ieee_paragraph(doc, "The Real-LLM study used the selected three-agent team, 60 executable cases, deterministic validators, and ten paired seeds. Each atomic-claim winner was executed once at a time per agent, while independent agents ran concurrently without a round barrier. Provider failures after the frozen retry limit invalidated a policy run rather than being counted as task-quality failures. This study is a supplementary validation with ten paired seeds; the 22,500-run simulation remains the confirmatory causal analysis.")
    add_real_llm_table(
        doc,
        rows=data["real_main_descriptive"],
        key="policy",
        order=["CF_FIT", "S3", "CENTRAL_FIT"],
        labels={"CF_FIT": "CF-Fit", "S3": "Static round robin", "CENTRAL_FIT": "Central-Fit"},
        caption="TABLE VI. REAL-LLM DESCRIPTIVE OUTCOMES ACROSS TEN PAIRED SEEDS",
    )
    main_desc = {
        (row["policy"], row["metric"]): f(row, "mean")
        for row in data["real_main_descriptive"]
    }
    ieee_paragraph(
        doc,
        "Across ten paired seeds, CF-Fit completed "
        f"{100 * main_desc[('CF_FIT', 'completion_rate')]:.2f}% of cases with mean wall time "
        f"{main_desc[('CF_FIT', 'run_wall_time_seconds')]:.2f} s, verified throughput "
        f"{main_desc[('CF_FIT', 'verified_throughput_per_second')]:.5f} tasks/s, utilization "
        f"{100 * main_desc[('CF_FIT', 'resource_utilization')]:.2f}%, and cost per verified task "
        f"${main_desc[('CF_FIT', 'cost_per_verified_task')]:.6f}. Static S3 completed "
        f"{100 * main_desc[('S3', 'completion_rate')]:.2f}% at "
        f"{main_desc[('S3', 'verified_throughput_per_second')]:.5f} tasks/s and "
        f"${main_desc[('S3', 'cost_per_verified_task')]:.6f} per verified task. Central-Fit completed "
        f"{100 * main_desc[('CENTRAL_FIT', 'completion_rate')]:.2f}% at "
        f"{main_desc[('CENTRAL_FIT', 'verified_throughput_per_second')]:.5f} tasks/s and "
        f"${main_desc[('CENTRAL_FIT', 'cost_per_verified_task')]:.6f} per verified task. These descriptive levels establish the operational scale before paired inference.",
    )
    main_pairs = real_pair_index(data["real_main_pairwise"], "left_policy", "right_policy")
    cf_s3_completion = main_pairs[("CF_FIT", "S3", "completion_rate")]
    cf_s3_cost = main_pairs[("CF_FIT", "S3", "cost_per_verified_task")]
    cf_s3_wall = main_pairs[("CF_FIT", "S3", "run_wall_time_seconds")]
    cf_s3_throughput = main_pairs[("CF_FIT", "S3", "verified_throughput_per_second")]
    cf_s3_utilization = main_pairs[("CF_FIT", "S3", "resource_utilization")]
    ieee_paragraph(
        doc,
        f"Relative to static round robin, CF-Fit changed completion by "
        f"{100 * f(cf_s3_completion, 'mean_difference_left_minus_right'):+.2f} percentage points and cost per "
        f"verified task by {f(cf_s3_cost, 'relative_mean_change_percent'):+.2f}%, while wall time changed by "
        f"{f(cf_s3_wall, 'relative_mean_change_percent'):+.2f}%, throughput by "
        f"{f(cf_s3_throughput, 'relative_mean_change_percent'):+.2f}%, and utilization by "
        f"{f(cf_s3_utilization, 'relative_mean_change_percent'):+.2f}%. All six prespecified metric-level "
        f"comparisons were Holm-significant (adjusted p={f(cf_s3_completion, 'p_holm'):.6f}). This is a "
        "speed-utilization versus completion-cost trade-off, not Pareto superiority.",
    )
    cf_central = [
        main_pairs[("CF_FIT", "CENTRAL_FIT", metric)]
        for metric in (
            "completion_rate", "total_cost", "cost_per_verified_task",
            "run_wall_time_seconds", "verified_throughput_per_second", "resource_utilization",
        )
    ]
    ieee_paragraph(
        doc,
        "CF-Fit and Central-Fit were descriptively close under the selected team, and none of the six "
        f"paired comparisons reached Holm-adjusted p<0.05 (minimum adjusted p="
        f"{min(f(row, 'p_holm') for row in cf_central):.6f}). This result does not establish equivalence; it "
        "states only that the ten-seed supplementary study detected no difference at the prespecified threshold.",
    )
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(REAL_LLM / "figures" / "fig_real_llm_main_radar.png"), width=Inches(6.7))
    add_caption(doc, "Fig. 14. Descriptive Real-LLM policy profiles. Each axis is min-max normalized within the three policies so that higher is preferable; the radar is not an inferential composite score.", font="Times New Roman", size=8)
    add_two_column_section(doc)

    ieee_heading(doc, "I. Real-LLM Stand-Down and Team-Composition Extension", level=2)
    ieee_paragraph(doc, "A separately frozen extension added one single-component ablation and two homogeneous boundary conditions. HET_NO_STANDDOWN retained decentralized self-selection, eligibility, fit scoring, aging, retry, and requeue while removing only stand-down. HOM_GLM_GENERALIST replicated the calibrated GLM Rank-3/Rank-3 deployment across three slots; HOM_GPT_PROFILE replicated the GPT ML-Rank-2/Fix-Rank-3 deployment. These homogeneous teams are ecological boundary conditions, not mean-ability-matched causal controls. Controlled mean-ability evidence for RQ2 therefore remains in the simulation.")
    add_real_llm_table(
        doc,
        rows=data["real_extension_descriptive"],
        key="condition_id",
        order=["HET_FULL", "HET_NO_STANDDOWN", "HOM_GLM_GENERALIST", "HOM_GPT_PROFILE"],
        labels={
            "HET_FULL": "Heterogeneous full CF-Fit",
            "HET_NO_STANDDOWN": "Heterogeneous without stand-down",
            "HOM_GLM_GENERALIST": "Homogeneous GLM",
            "HOM_GPT_PROFILE": "Homogeneous GPT",
        },
        caption="TABLE VII. REAL-LLM ABLATION AND HOMOGENEOUS BOUNDARY OUTCOMES",
    )
    extension_desc = {
        (row["condition_id"], row["metric"]): f(row, "mean")
        for row in data["real_extension_descriptive"]
    }
    ieee_paragraph(
        doc,
        "For the primary extension outcomes, HET_FULL and HET_NO_STANDDOWN both completed "
        f"{100 * extension_desc[('HET_FULL', 'completion_rate')]:.2f}% of cases; their mean costs per verified task were "
        f"${extension_desc[('HET_FULL', 'cost_per_verified_task')]:.6f} and "
        f"${extension_desc[('HET_NO_STANDDOWN', 'cost_per_verified_task')]:.6f}, respectively. "
        f"HOM_GLM_GENERALIST completed {100 * extension_desc[('HOM_GLM_GENERALIST', 'completion_rate')]:.2f}% "
        f"at ${extension_desc[('HOM_GLM_GENERALIST', 'cost_per_verified_task')]:.6f} per verified task, whereas "
        f"HOM_GPT_PROFILE completed {100 * extension_desc[('HOM_GPT_PROFILE', 'completion_rate')]:.2f}% "
        f"at ${extension_desc[('HOM_GPT_PROFILE', 'cost_per_verified_task')]:.6f}. The opposite homogeneous outcomes demonstrate model-specific boundary behavior; they do not identify a causal effect of team homogeneity.",
    )
    ieee_paragraph(doc, extension_contrast_sentence(data, "HET_NO_STANDDOWN", "Removing stand-down"))
    ieee_paragraph(doc, extension_contrast_sentence(data, "HOM_GLM_GENERALIST", "The homogeneous GLM boundary"))
    ieee_paragraph(doc, extension_contrast_sentence(data, "HOM_GPT_PROFILE", "The homogeneous GPT boundary"))
    ieee_paragraph(doc, "The extension ran after HET_FULL. Provider load and network conditions were therefore not randomized across execution windows. Completion, cost, and allocation-event contrasts are the main supplementary evidence and retain all ten paired seeds per condition. Wall time, throughput, and utilization comparisons are explicitly exploratory: timing-valid sample sizes were 10 for HET_FULL and HET_NO_STANDDOWN, 8 for HOM_GLM_GENERALIST, and 9 for HOM_GPT_PROFILE after applying the frozen provider-gap rule. The three timing exclusions remain included for completion and cost. A Windows path-length failure interrupted the first seed before a policy summary existed; the attempt was retained as infrastructure-invalid and rerun through a short temporary drive without changing any research parameter. A later user-requested pause interrupted GLM seed 3004 before summary creation; its partial ledger was retained and the seed was rerun from the beginning under a new timestamp with the same frozen parameters.")
    add_full_width_section(doc)
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(REAL_LLM / "figures" / "fig_real_llm_extension_radar.png"), width=Inches(6.7))
    add_caption(doc, "Fig. 15. Descriptive Real-LLM sensitivity profiles for the stand-down ablation and homogeneous boundary teams. Per-axis normalization is visual only; cross-window timing axes are exploratory.", font="Times New Roman", size=8)
    add_two_column_section(doc)

    ieee_heading(doc, "VII. DISCUSSION")
    ieee_paragraph(doc, "The results should be read as a Pareto-style trade-off map. ConveyorFlow is supported when local self-selection produces an operationally useful cost–throughput–time combination while respecting completion and terminal-failure margins; it need not dominate every centralized or static control on every axis. Resource-stratified reporting is essential because a mechanism that protects high-ability agents can have different economic consequences when capability is or is not expensive.")
    ieee_paragraph(doc, "The heterogeneity experiment distinguishes diversity from average team strength. H0, H1, and H2 share the same mean latent ability; differences therefore arise from composition and task matching rather than simply adding a stronger team. The ablations further separate the contribution of noisy local assessment, fit ranking, temporary overqualification stand-down, and task aging.")
    ieee_paragraph(doc, "Operationally, stand-down should not be presented as refusal. It is a decaying backoff term that reserves scarce capability early and disappears as waiting becomes urgent. Aging and bounded dead-letter behavior are therefore part of the mechanism’s safety story: they prevent an easy task from being postponed forever when the preferred lower-level agent is unavailable.")
    ieee_paragraph(doc, "The live MFEC execution provides a complementary implementation check rather than replacing the controlled simulation. Relative to Static S3, CF-Fit completed fewer tasks and spent more per verified task, but finished the observed workload window faster with substantially higher verified throughput and utilization. Relative to Central-Fit, the ten paired seeds produced descriptively close results and no Holm-significant metric-level contrast; this is absence of detected difference, not evidence of equivalence. The extension tests whether the live pattern is sensitive to removing stand-down and to two ecologically plausible homogeneous deployments. Because homogeneous models change both capability profile and provider behavior, those conditions bound deployment behavior but do not isolate heterogeneity as cleanly as the mean-matched simulation compositions.")
    ieee_paragraph(doc, "The secondary Pareto and competing-risk views sharpen, but do not broaden, that conclusion. They show why a single rank is unstable across objective pairs and why terminal latency must be interpreted with the probability of verification, dead letter, and censoring. Because these views were added after confirmatory inspection, they are evidence for interpretation and future preregistration rather than additional confirmatory claims.")

    ieee_heading(doc, "VIII. THREATS TO VALIDITY")
    ieee_paragraph(doc, "Construct validity is limited by simulated success, time, token, assessment, and cost functions. Ability ranks represent calibrated behavioral envelopes, not specific model versions. Public corpora shape workload distributions, but a simulation task is not equivalent to executing a real ML project or repository repair. CodeXGLUE pairs are non-executable in this study.")
    ieee_paragraph(doc, "Difficulty labels were produced by three role-conditioned passes of one underlying LLM and one adjudication pass. This improves reproducibility but does not establish human-expert validity or rater independence. The Beijing subgroup κ=0.628 signals a local reliability limitation; alternate mappings bound, but do not eliminate, this concern.")
    ieee_paragraph(doc, "Internal validity is strengthened by frozen seeds, common random numbers, keyed potential outcomes, an immutable event ledger, source and artifact hashes, and no outcome-based exclusions. Nevertheless, the chosen logistic ability curve, load process, scan window, aging thresholds, retry limit, and four-agent cap can interact. External validity is limited to the tested architecture and ranges. The supplementary Real-LLM evidence uses 10 paired seeds, 60 task bundles, a single MFEC-compatible endpoint, and dated provider aliases rather than independently verified immutable model versions. Provider latency and load can drift, and the main and extension windows were not randomized together; cross-window timing contrasts are therefore exploratory. Homogeneous boundary teams also conflate capability composition with model-specific behavior. Human difficulty validation, additional providers and team sizes, and communication-failure sensitivity remain future work.")
    ieee_paragraph(doc, "The live validators establish task-specific functional success for the selected ML-build and bug-fix bundles, but they do not cover every semantic, security, maintainability, or production-quality property. Ten seeds provide useful paired sensitivity evidence rather than definitive population estimates. One pre-summary extension attempt failed because of Windows path length, was retained as infrastructure-invalid, and was rerun after a path-only wrapper correction; no scientific parameter, seed, model, task, validator, or analysis rule was changed.")
    ieee_paragraph(doc, "The competing-risk envelopes summarize between-run dispersion rather than sampling uncertainty, and right-censoring at the fixed simulation horizon assumes that unresolved work is not reclassified after observation ends. The Pareto frontiers depend on the two displayed objectives and would change under a different objective set. Both analyses are explicitly secondary.")

    ieee_heading(doc, "IX. CONCLUSION")
    ieee_paragraph(doc, "ConveyorFlow reframes heterogeneous LLM-agent allocation as decentralized capability-aware self-selection over a ready-task belt. Its scientific story joins local decision authority, capability heterogeneity, fit, temporary stand-down, and aging. A pre-specified simulation frozen before execution across 22,500 unique runs evaluates the resulting trade-offs against realistic static and centralized controls rather than claiming universal dominance. A completed, safety-locked Real-LLM study adds implementation-level evidence: it exposes a statistically clear speed-utilization versus completion-cost trade-off against static assignment, while the selected decentralized and centralized fit mechanisms were not distinguishable with ten paired seeds. The separately frozen stand-down and homogeneous-team extension supplies sensitivity and deployment-boundary evidence, not a replacement for the simulation’s controlled causal comparisons. Human validation of task difficulty remains separate and pending.")

    ieee_heading(doc, "DATA AND CODE AVAILABILITY")
    ieee_paragraph(doc, "The v2 research package contains source code, frozen configurations, public-data manifests, annotation packets and prompts, event-ledger hashes, analysis scripts, secondary-analysis outputs, the pre-execution source snapshot, and the vendor-neutral Real-LLM protocol and harness. The editable ConveyorFlow_diagrams_en_working.drawio source contains the system architecture, process architecture, CF-Fit belt, static baseline, and one-tick pages reproduced in Figures 1–5. Dated MFEC calibration and execution ledgers, team-selection evidence, immutable configuration and case hashes, validated main and extension run manifests, statistical summaries, figures, and the documented path-only extension deviation are included. Provider aliases and prices are recorded as observed configuration metadata and should not be interpreted as independently verified model lineage. Raw CodeXGLUE files remain subject to their upstream license. A public archival DOI should be added after advisor approval and repository release.")

    ieee_heading(doc, "REFERENCES")
    references = [
        "[1] Q. Wu et al., “AutoGen: Enabling next-gen LLM applications via multi-agent conversation,” in Proc. COLM, 2024.",
        "[2] S. Hong et al., “MetaGPT: Meta programming for a multi-agent collaborative framework,” in Proc. ICLR, 2024.",
        "[3] C. Qian et al., “ChatDev: Communicative agents for software development,” in Proc. ACL, pp. 15174–15186, 2024, doi: 10.18653/v1/2024.acl-long.810.",
        "[4] G. Li, H. Hammoud, H. Itani, D. Khizbullin, and B. Ghanem, “CAMEL: Communicative agents for ‘mind’ exploration of large language model society,” in Adv. Neural Inf. Process. Syst., vol. 36, 2023, doi: 10.52202/075280-2264.",
        "[5] W. Chen et al., “AgentVerse: Facilitating multi-agent collaboration and exploring emergent behaviors,” in Proc. ICLR, 2024.",
        "[6] T. Guo et al., “Large language model based multi-agents: A survey of progress and challenges,” in Proc. IJCAI, pp. 8048–8057, 2024, doi: 10.24963/ijcai.2024/890.",
        "[7] R. G. Smith, “The contract net protocol: High-level communication and control in a distributed problem solver,” IEEE Trans. Comput., vol. C-29, no. 12, pp. 1104–1113, 1980, doi: 10.1109/TC.1980.1675516.",
        "[8] B. P. Gerkey and M. J. Matarić, “A formal analysis and taxonomy of task allocation in multi-robot systems,” Int. J. Robot. Res., vol. 23, no. 9, pp. 939–954, 2004, doi: 10.1177/0278364904045564.",
        "[9] G. A. Korsah, A. Stentz, and M. B. Dias, “A comprehensive taxonomy for multi-robot task allocation,” Int. J. Robot. Res., vol. 32, no. 12, pp. 1495–1512, 2013, doi: 10.1177/0278364913496484.",
        "[10] H.-L. Choi, L. Brunet, and J. P. How, “Consensus-based decentralized auctions for robust task allocation,” IEEE Trans. Robot., vol. 25, no. 4, pp. 912–926, 2009, doi: 10.1109/TRO.2009.2022423.",
        "[11] Y. Liu et al., “G-Eval: NLG evaluation using GPT-4 with better human alignment,” in Proc. EMNLP, pp. 2511–2522, 2023, doi: 10.18653/v1/2023.emnlp-main.153.",
        "[12] C.-H. Chiang and H.-Y. Lee, “A closer look into using large language models for automatic evaluation,” in Findings EMNLP, pp. 8928–8942, 2023, doi: 10.18653/v1/2023.findings-emnlp.599.",
        "[13] G. H. Chen, S. Chen, Z. Liu, F. Jiang, and B. Wang, “Humans or LLMs as the judge? A study on judgement bias,” in Proc. EMNLP, pp. 8301–8327, 2024, doi: 10.18653/v1/2024.emnlp-main.474.",
        "[14] B. Becker and R. Kohavi, Adult [Dataset], UCI Machine Learning Repository, 1996, doi: 10.24432/C5XW20.",
        "[15] S. Chen, Beijing Multi-Site Air Quality [Dataset], UCI Machine Learning Repository, 2017, doi: 10.24432/C5RK5G.",
        "[16] S. Lu et al., “CodeXGLUE: A machine learning benchmark dataset for code understanding and generation,” arXiv:2102.04664, 2021.",
        "[17] F. Wilcoxon, “Individual comparisons by ranking methods,” Biometrics Bull., vol. 1, no. 6, pp. 80–83, 1945.",
        "[18] B. Efron, “Bootstrap methods: Another look at the jackknife,” Ann. Stat., vol. 7, no. 1, pp. 1–26, 1979.",
        "[19] S. Holm, “A simple sequentially rejective multiple test procedure,” Scand. J. Stat., vol. 6, no. 2, pp. 65–70, 1979.",
        "[20] J. Cohen, “Weighted kappa: Nominal scale agreement with provision for scaled disagreement or partial credit,” Psychol. Bull., vol. 70, no. 4, pp. 213–220, 1968.",
    ]
    for reference in references:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.16)
        paragraph.paragraph_format.first_line_indent = Inches(-0.16)
        paragraph.paragraph_format.space_after = Pt(0)
        add_text(paragraph, reference, font="Times New Roman", size=7.5)

    # A terminal continuous section makes Word balance the final reference
    # page across both columns instead of leaving the right column empty.
    add_full_width_section(doc)

    doc.core_properties.title = "ConveyorFlow: Decentralized Capability-Aware Self-Selection for Heterogeneous LLM Agent Teams"
    doc.core_properties.author = "Sakan Punyanon"
    doc.core_properties.subject = "IEEE-style pre-submission research manuscript"
    doc.save(MANUSCRIPT)


def setup_thai_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    add_page_number(section, font="TH Sarabun New", size=12)
    normal = doc.styles["Normal"]
    normal.font.name = "TH Sarabun New"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "TH Sarabun New")
    normal.font.size = Pt(15)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.05
    for name, size in (("Title", 24), ("Heading 1", 19), ("Heading 2", 17), ("Heading 3", 16)):
        style = doc.styles[name]
        style.font.name = "TH Sarabun New"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "TH Sarabun New")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
    return doc


def th_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    paragraph.paragraph_format.space_before = Pt(8)
    paragraph.paragraph_format.space_after = Pt(4)
    add_text(paragraph, text, font="TH Sarabun New", size={1: 19, 2: 17, 3: 16}[level], bold=True)


def th_paragraph(doc: Document, text: str, *, bold_lead: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Cm(0.7)
    if bold_lead and text.startswith(bold_lead):
        add_text(paragraph, bold_lead, font="TH Sarabun New", size=15, bold=True)
        add_text(paragraph, text[len(bold_lead):], font="TH Sarabun New", size=15)
    else:
        add_text(paragraph, text, font="TH Sarabun New", size=15)


def add_th_result_table(doc: Document, data: dict, family: str) -> None:
    idx = effect_index(data["effects"])
    if family == "RQ1":
        headers = ["Regime", "เทียบกับ", "ต้นทุน", "Throughput", "P95", "Comp. NI", "Dead NI", "Unsettled NI"]
        rows = []
        for resource in ("R0", "R1"):
            for comp in ("S1", "S2", "S3", "CENTRAL_FIT"):
                contrast = f"CF_FIT_minus_{comp}"
                cost = idx[("RQ1", resource, contrast, "cost_per_verified_task")]
                thr = idx[("RQ1", resource, contrast, "verified_throughput")]
                p95 = idx[("RQ1", resource, contrast, "p95_terminal_flow_time")]
                rows.append([resource, comp, pct(cost)+star(cost), pct(thr)+star(thr), pct(p95)+star(p95), yn(idx[("RQ1", resource, contrast, "task_completion_rate")]["noninferiority_pass"]), yn(idx[("RQ1", resource, contrast, "dead_letter_rate")]["noninferiority_pass"]), yn(idx[("RQ1", resource, contrast, "unsettled_rate")]["noninferiority_pass"])])
    elif family == "RQ2":
        headers = ["Regime", "Contrast", "ต้นทุน", "Throughput", "P95", "Completion Δ"]
        rows = []
        for resource in ("R0", "R1"):
            for contrast in ("H1_minus_H0", "H2_minus_H0", "H2_minus_H1"):
                rows.append([resource, contrast.replace("_minus_", "−"), pct(idx[("RQ2", resource, contrast, "cost_per_verified_task")]), pct(idx[("RQ2", resource, contrast, "verified_throughput")]), pct(idx[("RQ2", resource, contrast, "p95_terminal_flow_time")]), delta(idx[("RQ2", resource, contrast, "task_completion_rate")])])
    elif family == "RQ3":
        headers = ["Regime", "Full−ส่วนที่ตัด", "ต้นทุน", "Throughput", "P95", "Completion Δ"]
        rows = []
        for resource in ("R0", "R1"):
            for name in ("A1", "A2", "A3", "A4"):
                contrast = f"FULL_minus_{name}"
                rows.append([resource, name, pct(idx[("RQ3", resource, contrast, "cost_per_verified_task")]), pct(idx[("RQ3", resource, contrast, "verified_throughput")]), pct(idx[("RQ3", resource, contrast, "p95_terminal_flow_time")]), delta(idx[("RQ3", resource, contrast, "task_completion_rate")])])
    else:
        headers = ["Regime", "Contrast", "ต้นทุน", "Throughput", "P95", "Dead Δ", "Unsettled Δ"]
        rows = []
        for resource in ("R0", "R1"):
            for name in ("F0", "F1", "F3"):
                contrast = f"F2_minus_{name}"
                rows.append([resource, f"F2−{name}", pct(idx[("E4", resource, contrast, "cost_per_verified_task")]), pct(idx[("E4", resource, contrast, "verified_throughput")]), pct(idx[("E4", resource, contrast, "p95_terminal_flow_time")]), delta(idx[("E4", resource, contrast, "dead_letter_rate")]), delta(idx[("E4", resource, contrast, "unsettled_rate")])])
    table = doc.add_table(rows=1, cols=len(headers))
    for i, value in enumerate(headers): table.rows[0].cells[i].text = value
    for values in rows:
        cells = table.add_row().cells
        for i, value in enumerate(values): cells[i].text = str(value)
    format_table(table, font="TH Sarabun New", size=11.5, header_fill="D9EAF7")


def build_advisor(data: dict) -> None:
    doc = setup_thai_document()
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Cm(4.5)
    add_text(title, "ConveyorFlow v2", font="TH Sarabun New", size=28, bold=True)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(subtitle, "เอกสารอธิบายงานวิจัยและผลการทดลองสำหรับนำเสนออาจารย์ที่ปรึกษา", font="TH Sarabun New", size=21, bold=True)
    desc = doc.add_paragraph()
    desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(desc, "Decentralized Capability-Aware Self-Selection for Heterogeneous LLM Agent Teams", font="TH Sarabun New", size=16, italic=True)
    author = doc.add_paragraph()
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    author.paragraph_format.space_before = Cm(2.0)
    add_text(author, "ผู้วิจัย: Sakan Punyanon", font="TH Sarabun New", size=17)
    status = doc.add_paragraph()
    status.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(status, "สถานะ: Simulation Main และ secondary analysis เสร็จสมบูรณ์; Real-LLM ทำ Ability Calibration และเลือกทีมแล้ว แต่ยังไม่มีผลเปรียบเทียบ allocation policy", font="TH Sarabun New", size=15, color="9C0006")
    doc.add_page_break()

    th_heading(doc, "สรุปสำหรับอธิบายอาจารย์")
    th_paragraph(doc, "งานนี้ไม่ได้เสนอว่า ConveyorFlow ต้องชนะทุกตัวชี้วัด แต่เสนอและทดสอบกลไกการตัดสินใจเลือกงานแบบกระจายศูนย์สำหรับทีม AI Agent ที่ความสามารถและต้นทุนต่างกัน โดย Agent ว่างจะดูงานที่พร้อมบนสายพาน ประเมินความเหมาะสมด้วยตนเอง อาสารับงาน และอาจชะลอการรับงานที่ง่ายเกินความสามารถชั่วคราว เพื่อสำรอง Agent ระดับสูงไว้ให้งานยาก เมื่อรอนานระบบจะผ่อนเงื่อนไขเพื่อไม่ให้งานค้างตลอดไป")
    th_paragraph(doc, f"Main experiment ใช้ discrete-event simulation จำนวน {int(data['integrity']['observed_runs']):,} unique runs, 50 paired seeds และตรวจ hash ของ event ledger ครบ {int(data['verification']['event_hashes_checked']):,} ไฟล์ ผลที่อธิบายได้จึงเป็นหลักฐานภายใต้แบบจำลอง ไม่ใช่ผลการเรียก Claude หรือ OpenAI รุ่นจริง")
    add_bullet(doc, "Scientific contribution: decentralized self-selection + capability heterogeneity + capability–task fit + bounded stand-down + aging", font="TH Sarabun New", size=15)
    add_bullet(doc, "Experimental policies เป็นเครื่องมือพิสูจน์กลไก ไม่ใช่ contribution หลัก", font="TH Sarabun New", size=15)
    add_bullet(doc, "ผลต้องอ่านเป็น trade-off ของต้นทุน ความเร็ว throughput completion และความล้มเหลว", font="TH Sarabun New", size=15)

    th_heading(doc, "สิ่งที่เปลี่ยนจากแผน/งานเดิม")
    changes = [
        ["เดิม", "ปรับใน v2", "เหตุผลเชิงวิจัย"],
        ["เล่า 13 policies เป็น contribution", "เล่า mechanism story; policies เป็น experimental evidence", "ทำให้ novelty อยู่ที่องค์ความรู้ ไม่ใช่จำนวนวิธีทดลอง"],
        ["RQ1 ถามว่า ‘ดีกว่า’ หรือไม่", "ถามผลต่อ trade-off vector", "ไม่บังคับให้ชนะทุก metric ที่ conflict กัน"],
        ["Strong/Mid/Weak", "Ability L1/L2/L3 จาก behavioral curve", "ไม่ผูกความสามารถกับชื่อรุ่น ราคา หรือความใหม่"],
        ["Oracle/HEFT", "ตัดออก; ใช้ S1/S2/S3 และ matched Central-Fit", "ข้อมูลและสมมติฐานเทียบได้กับ online case มากกว่า"],
        ["ผสม model/vendor ตั้งแต่ต้น", "Simulation generic ability ก่อน", "isolate mechanism; real-model phase เป็น validation ถัดไป"],
        ["ไม่มีคนรับงานยังไม่ชัด", "F0–F3; F2 aging+relaxation เป็น default", "วัด dead-letter/unsettled และป้องกัน livelock"],
        ["Difficulty label ไม่ชัด", "rubric + 3 role passes + adjudication + sensitivity", "ทำซ้ำและตรวจ stability ได้โดยไม่อ้าง human ground truth"],
    ]
    table = doc.add_table(rows=1, cols=3)
    for i, value in enumerate(changes[0]): table.rows[0].cells[i].text = value
    for row_values in changes[1:]:
        cells = table.add_row().cells
        for i, value in enumerate(row_values): cells[i].text = value
    format_table(table, font="TH Sarabun New", size=12.5, header_fill="FFF2CC")

    th_heading(doc, "1. ปัญหาวิจัยและวัตถุประสงค์")
    th_paragraph(doc, "ปัญหาคือทีม LLM Agent แบบ heterogeneous มีทั้งความสามารถ เวลาใช้ Token และราคาแตกต่างกัน หากใช้ตัวกลางเลือกงานทั้งหมดอาจเกิด bottleneck และ single point of decision แต่ถ้าให้ Agent รับงานเองโดยไม่มีเกณฑ์ งานง่ายอาจถูก Agent แพงรับไป งานยากอาจถูก Agent อ่อนรับจนต้อง retry หรือไม่มีใครอาสา")
    th_paragraph(doc, "Objective หลักคือ ลด cost per verified task ภายใต้ข้อจำกัดคุณภาพที่กำหนดล่วงหน้า โดย completion ของ CF-Fit ต้องไม่ด้อยกว่า baseline เกิน 0.03 และ dead-letter/unsettled ต้องไม่สูงกว่า baseline เกิน 0.03 พร้อมรายงาน throughput และ P95 terminal flow time เป็นผลรองสำคัญ ไม่มีการรวมทุก metric เป็นคะแนนชนะตัวเดียวภายหลังเห็นผล")
    for text in (
        "RQ1: decentralized self-selection ของ CF-Fit เปลี่ยน cost, throughput, P95 time, completion, failure และ utilization เทียบ static/central controls อย่างไร",
        "RQ2: เมื่อคุมจำนวน Agent และค่าเฉลี่ย ability เท่ากัน ความหลากหลายของ ability มีผลต่อ CF-Fit อย่างไร",
        "RQ3: self-assessment, fit, stand-down และ aging แต่ละส่วนมี contribution เท่าใด",
        "E4: เมื่อไม่มี Agent อาสา กลไก F0–F3 โดยเฉพาะ F2 รับมือ mixed และ D3-heavy workload อย่างไร",
    ):
        add_bullet(doc, text, font="TH Sarabun New", size=15)

    th_heading(doc, "2. Input, Process และ Output")
    th_heading(doc, "2.1 Input", level=2)
    add_bullet(doc, "Job DAG จากสองประเภทงาน: ML Build และ Fix Bug", font="TH Sarabun New", size=15)
    add_bullet(doc, "READY task ที่ dependency ผ่านแล้ว พร้อม skill, specification, age และ retry history", font="TH Sarabun New", size=15)
    add_bullet(doc, "Agent profile: Ability L1/L2/L3, speed factor, token factor และ price factor", font="TH Sarabun New", size=15)
    add_bullet(doc, "ค่าทดลอง: workload, load ρ=0.4/0.7/0.9, team composition, resource regime, policy, fallback และ seed", font="TH Sarabun New", size=15)
    th_heading(doc, "2.2 Process", level=2)
    steps = [
        "ปล่อย Job ตาม arrival process และเปิด task แรกที่ dependency ครบเข้าสายพาน READY",
        "Agent ว่างสแกนงานตามลำดับไม่เกิน K_scan=8 งาน",
        "Agent ประเมิน difficulty, pass probability, effort และ confidence จากข้อมูลที่มองเห็น โดยไม่เห็น ground-truth difficulty หรือผลลัพธ์อนาคต",
        "กรอง eligibility ด้วย skill, retry diversity และ threshold τ(age)",
        "คำนวณ fit gap, overqualification, urgency และ keyed jitter เป็น backoff",
        "Agent เลือก candidate เดียวและพยายาม atomic claim; ผู้แพ้ collision กลับไปดูรอบถัดไป",
        "execute → verify; ถ้าไม่ผ่านให้ retry ภายใต้ max attempts=3",
        "ถ้าไม่มี volunteer ใช้ fallback; F2 re-offer/requeue/relax และจบที่ DEAD_LETTER แบบ bounded",
        "ทุก assessment, claim, execution, verification, retry, requeue และ rescue ถูกบันทึกใน immutable event ledger",
    ]
    for i, text in enumerate(steps, 1):
        paragraph = doc.add_paragraph()
        add_text(paragraph, f"{i}. {text}", font="TH Sarabun New", size=15)
    doc.add_picture(str(FIGURES / "fig1_architecture.png"), width=Cm(16.0))
    add_caption(doc, "ภาพรวม ConveyorFlow: READY belt → local assessment/volunteer → atomic claim → execute/verify", font="TH Sarabun New", size=12)
    th_heading(doc, "2.3 Output", level=2)
    th_paragraph(doc, "Output ต่อ run ประกอบด้วย cost per verified task, verified throughput, median/P95 flow time, completion, dead-letter, unsettled, utilization, rework, collision, assessment burden, stand-down, requeue และ forced rescue พร้อม event hash และ config hash")

    th_heading(doc, "3. ข้อมูลสาธารณะที่ใช้")
    table = doc.add_table(rows=1, cols=5)
    for i, value in enumerate(["ชุดข้อมูล", "ประเภท", "จำนวน", "ใช้สร้าง", "ข้อจำกัด"]): table.rows[0].cells[i].text = value
    values = [
        ["UCI Adult", "Classification", "48,842 records", "ML-build 7 stages", "Public CC BY 4.0"],
        ["UCI Beijing", "Time-series regression", "420,768 records", "ML-build 7 stages", "12 stations; missing data"],
        ["CodeXGLUE Bugs2Fix", "Buggy/fixed Java", "46,680 pairs", "Fix-bug 5 stages", "Distribution only; ไม่ใช่ executable tests"],
    ]
    for row_values in values:
        cells = table.add_row().cells
        for i, value in enumerate(row_values): cells[i].text = value
    format_table(table, font="TH Sarabun New", size=13)
    th_paragraph(doc, "จำนวนข้อมูลทุกชุดมากกว่า 20,000 ตามข้อกำหนด แหล่งที่มา license byte size และ SHA-256 อยู่ใน data/manifest.json เพื่อให้ดาวน์โหลดและตรวจซ้ำได้")

    th_heading(doc, "4. การกำหนด Task Difficulty")
    th_paragraph(doc, "สร้าง 304 stage-by-stratum specifications จาก 48 deterministic variants แล้วให้ LLM ตัวเดียวทำงานภายใต้ 3 บทบาทที่แยก prompt และลำดับ packet: ML Methodologist, Software Reliability Reviewer และ Workflow/Resource Reviewer แต่ละบทบาทให้คะแนน 5 มิติ 0–2 ได้แก่ ambiguity, context span, dependency depth, reasoning depth และ verification complexity รวม 0–3=D1, 4–6=D2, 7–10=D3")
    agreement = data["agreement"]["pairwise_agreement"]
    kappas = [value["quadratic_weighted_kappa"] for value in agreement.values()]
    exacts = [value["exact_agreement"] for value in agreement.values()]
    dist = data["annotation"]["adjudicated_distribution"]
    th_paragraph(doc, f"ผล agreement: exact {min(exacts):.1%}–{max(exacts):.1%}, quadratic-weighted kappa {min(kappas):.3f}–{max(kappas):.3f}, adjacent agreement 100% มี 94 รายการไม่เป็นเอกฉันท์และ adjudicate ครบ โดย 17 รายการต่างจาก mechanical consensus ผลสุดท้าย D1={dist['1']}, D2={dist['2']}, D3={dist['3']}")
    th_paragraph(doc, "Claim ที่ใช้ได้: เป็น role-conditioned LLM annotation panel ที่ทำซ้ำได้และมี separate adjudication แต่ไม่ใช่ผู้เชี่ยวชาญมนุษย์หลายคน ไม่ใช่ independent raters และไม่ใช่ external ground truth จุดอ่อนเฉพาะกลุ่มคือ Beijing rater2–rater3 kappa=0.628 จึงมี lower/upper mapping sensitivity ซึ่งเปลี่ยน 47 labels ต่อขอบ")

    th_heading(doc, "5. Ability Rank วัดอย่างไร")
    th_paragraph(doc, "Ability วัดจากพฤติกรรมที่คาดว่าจะผ่านงานแต่ละระดับ ไม่วัดจากชื่อยี่ห้อ ความใหม่ ราคา ความเร็ว หรือจำนวนพารามิเตอร์โดยตรง ใน Simulation ใช้ latent theta และ logistic success curve: logit[P(pass)] = alpha_workload + 0.85 theta − 1.2(difficulty−2)")
    table = doc.add_table(rows=1, cols=4)
    for i, value in enumerate(["Rank", "theta", "นิยามเชิงพฤติกรรม", "สิ่งที่ไม่ใช้เป็นนิยาม"]): table.rows[0].cells[i].text = value
    for row_values in (["L1 Basic", "−1", "น่าเชื่อถือหลักใน D1", "ราคา/รุ่น"], ["L2 Intermediate", "0", "น่าเชื่อถือใน D1–D2", "Token/Speed"], ["L3 Advanced", "+1", "ยังมีโอกาสสำเร็จที่ใช้การได้ใน D3", "ความใหม่ของโมเดล"]):
        cells = table.add_row().cells
        for i, value in enumerate(row_values): cells[i].text = value
    format_table(table, font="TH Sarabun New", size=13)
    th_paragraph(doc, "ตัวอย่าง P(pass) เมื่อ alpha=0.86: L1 เท่ากับประมาณ 0.77/0.50/0.23 สำหรับ D1/D2/D3; L2 เท่ากับ 0.89/0.70/0.42; L3 เท่ากับ 0.95/0.85/0.62 จึงเป็นเส้นโค้ง monotonic ทั้งตาม ability และ difficulty ไม่ใช่การตั้งชื่อ rank เฉย ๆ")
    th_paragraph(doc, "ถ้าทดลอง Real LLM ในอนาคต ต้องสร้าง held-out capability probe แยกตาม workload แล้วจัด Rank จาก lower bound ของ 95% confidence interval; โมเดลที่ไม่ถึงเกณฑ์ L1 ต้องเป็น L0/Unqualified ไม่ควรใช้ราคาหรือชื่อรุ่นเป็นตัวแทน ability")

    th_heading(doc, "6. Boundary Compositions คืออะไร")
    th_paragraph(doc, "Boundary compositions คือการเลือกทีมที่อยู่ปลายขอบของระดับความหลากหลาย เพื่อดู effect ของ heterogeneity ให้ชัด โดยคุม team size=4 และ mean ability=2 เท่ากัน")
    table = doc.add_table(rows=1, cols=4)
    for i, value in enumerate(["ทีม", "องค์ประกอบ", "Mean", "Variance/ความหมาย"]): table.rows[0].cells[i].text = value
    for row_values in (["H0", "(2,2,2,2)", "2.0", "0.0 homogeneous"], ["H1", "(1,2,2,3)", "2.0", "0.5 heterogeneous ระดับกลาง"], ["H2", "(1,1,3,3)", "2.0", "1.0 boundary/extreme heterogeneity"], ["L1×4", "(1,1,1,1)", "1.0", "stress team เฉพาะ E4"]):
        cells = table.add_row().cells
        for i, value in enumerate(row_values): cells[i].text = value
    format_table(table, font="TH Sarabun New", size=13)
    th_paragraph(doc, "ดังนั้น H2 ไม่ได้เก่งกว่า H0 โดยค่าเฉลี่ย แต่กระจายเป็น Agent อ่อนสองตัวและเก่งสองตัว ถ้า H2 ต่างจาก H0 เราจึงตีความได้ว่าเกิดจาก composition/fit ไม่ใช่เพิ่มกำลังเฉลี่ยของทีม")

    th_heading(doc, "7. Baseline, Ablation และ Fallback")
    for text in (
        "S1 Fixed skill ownership: กำหนดเจ้าของตาม skill ล่วงหน้า",
        "S2 Fixed difficulty-level routing: ใช้ difficulty mapping ที่ freeze แล้วกำหนดเจ้าของล่วงหน้า",
        "S3 Precomputed round robin: หมุน Agent ตามลำดับโดยไม่ปรับระหว่าง run",
        "Central-Fit: ใช้ assessment/fit ใกล้เคียงกันแต่ตัวกลางจับคู่ Agent–task",
        "A1/A2/A3/A4: ตัด assessment/fit/stand-down/aging เพื่อดู contribution แยกส่วน",
        "F0 immediate re-offer, F1 bounded tail requeue, F2 aging+relaxation แบบ decentralized, F3 central forced rescue แบบ hybrid",
    ):
        add_bullet(doc, text, font="TH Sarabun New", size=15)
    th_paragraph(doc, "ตัด Oracle และ HEFT ออกจาก baseline เพราะใช้ข้อมูล/สมมติฐานไม่เทียบเท่ากับ online local-observation setting และไม่ใช่ baseline ที่อิงการใช้งานของ case นี้โดยตรง")

    th_heading(doc, "8. Experimental Design และการวิเคราะห์")
    th_paragraph(doc, "Main design มี 22,500 unique runs จาก 50 seeds 1000–1049 แต่ละ run มี 200 jobs ใช้ common arrivals, task attributes และ keyed potential outcomes สำหรับ policies ที่จับคู่กัน หน่วยวิเคราะห์คือ run/seed ไม่ใช่ task ภายใน run")
    for text in (
        "RQ1 memberships 4,500; RQ2 2,700; RQ3 6,000; E4 9,600; resource sensitivity 600; annotation sensitivity 1,800",
        "95% CI ใช้ paired seed-cluster bootstrap 10,000 resamples, analysis seed 20260922",
        "Hypothesis test ใช้ Wilcoxon signed-rank และ Holm correction แยกภายใน RQ/metric family",
        "รายงาน R0/R1 แยกกัน และคำนวณ policy×load, policy×workload, policy×resource interactions ที่ preregistered",
        "zero-success เป็น infinity/infeasible; dead-letter และ unsettled ห้ามตัดทิ้ง",
        "Pareto และ competing-risk เป็น secondary descriptive analysis ที่เพิ่มหลัง confirmatory results; ไม่เปลี่ยน hypothesis หรือ Holm family",
    ):
        add_bullet(doc, text, font="TH Sarabun New", size=15)

    th_heading(doc, "9. ผลการทดลอง Main")
    th_paragraph(doc, "วิธีอ่านตาราง: ค่าเปอร์เซ็นต์เป็น paired median difference ของด้านซ้ายเทียบด้านขวา ค่าต้นทุนและ P95 ติดลบถือว่าดีกว่า ส่วน throughput ติดบวกถือว่าดีกว่า เครื่องหมาย * คือ Holm-adjusted p<0.05 แต่ต้องอ่าน non-inferiority และ failure outcomes ร่วมกัน")
    th_heading(doc, "9.1 RQ1 — CF-Fit เทียบ Baseline", level=2)
    add_th_result_table(doc, data, "RQ1")
    ni = rq1_ni_counts(data)
    th_paragraph(doc, thai_family_summary(data, "RQ1") + f" ส่วน completion/dead-letter/unsettled non-inferiority ผ่าน {ni['task_completion_rate']}/8, {ni['dead_letter_rate']}/8 และ {ni['unsettled_rate']}/8 ตามลำดับ")
    th_paragraph(doc, "เทียบ static controls, CF-Fit เพิ่ม completion 4.49–16.39 จุดเปอร์เซ็นต์และลด unsettled 26.15–57.39 จุด แต่เพิ่ม dead-letter 17.50–35.84 จุด จึงห้ามอ่าน dead-letter แยกเดี่ยว: static ดูเหมือนทิ้งงานน้อยเพราะยังค้างที่ horizon มาก ขณะที่ CF-Fit ทำให้งานมี terminal disposition ชัดขึ้น เทียบ Central-Fit ต่างกันเล็กน้อยและ non-inferiority ผ่านทุก quality constraint")
    doc.add_picture(str(FIGURES / "fig2_rq1_cost.png"), width=Cm(15.5))
    add_caption(doc, "รูปที่ 1 RQ1 cost per verified task: CF-Fit minus comparator พร้อม 95% CI", font="TH Sarabun New", size=12)
    doc.add_picture(str(FIGURES / "fig6_rq1_tradeoff_radar.png"), width=Cm(16.5))
    add_caption(doc, "รูปที่ 2 Radar chart ของ RQ1: ทุกแกน normalize ภายใน R0 หรือ R1 ให้ค่าสูงหมายถึงดีกว่า ใช้เพื่อมอง trade-off เท่านั้น ไม่ใช่คะแนนรวมเชิงอนุมาน", font="TH Sarabun New", size=12)
    th_paragraph(doc, "Radar chart ทำให้เห็นว่า CF-Fit และ Central-Fit มีรูปทรงใกล้กันด้าน throughput, P95, completion และ unsettled ขณะที่ static บางแบบเด่นเฉพาะต้นทุนหรือ dead-letter จึงสนับสนุนการเล่าแบบ trade-off vector ไม่ใช่การประกาศผู้ชนะจากพื้นที่รูปหลายเหลี่ยม")
    doc.add_picture(str(FIGURES / "fig7_rq1_pareto_frontiers.png"), width=Cm(16.5))
    add_caption(doc, "รูปที่ 3 Pareto frontiers สอง objective: จุดทึบคือ nondominated เฉพาะคู่ metric ที่แสดง ไม่ใช่คะแนนรวมและไม่ใช่ hypothesis test ใหม่", font="TH Sarabun New", size=12)
    th_paragraph(doc, "ด้าน cost-throughput ไม่มี policy เดียวครองทุกจุด: R0 มี Central-Fit, Static L1-only และ Static round-robin บน frontier; R1 มี Central-Fit, Static L3-only และ Static round-robin ส่วน CF-Fit ถูก Central-Fit dominate เล็กน้อยในคู่นี้ ด้าน P95-completion นั้น Central-Fit อยู่บน frontier เพียงตัวเดียวใน R0 ขณะที่ R1 มีทั้ง Central-Fit และ CF-Fit เพราะ CF-Fit เร็วกว่าเล็กน้อยแต่ completion ต่ำกว่าเล็กน้อย")
    doc.add_picture(str(FIGURES / "fig8_rq1_competing_risks.png"), width=Cm(16.5))
    add_caption(doc, "รูปที่ 4 Cumulative incidence แบบ competing risks: เส้นคือ median ของ 450 run-level Aalen-Johansen curves ต่อ policy/regime และเงาคือช่วง percentile ของ runs ไม่ใช่ confidence interval", font="TH Sarabun New", size=12)
    th_paragraph(doc, "ที่ 1,000 ticks verified incidence ของ CF-Fit เทียบ Central-Fit เท่ากับ 0.590 กับ 0.602 ใน R0 และ 0.615 กับ 0.621 ใน R1 ส่วน dead-letter เท่ากับ 0.410 กับ 0.396 และ 0.382 กับ 0.378 ตามลำดับ จึงสรุปได้ว่า CF-Fit ติดตาม matched centralized controller ค่อนข้างใกล้ แต่ terminal-time อย่างเดียวอาจทำให้ policy ที่ปล่อยงานค้างดูดีกว่าความเป็นจริง")
    th_heading(doc, "9.2 RQ2 — Capability Heterogeneity", level=2)
    add_th_result_table(doc, data, "RQ2")
    th_paragraph(doc, thai_family_summary(data, "RQ2"))
    th_paragraph(doc, "H2−H0 เป็น boundary contrast ของ variance 1.0 กับ 0.0; H1 ช่วยดูว่าผลเปลี่ยนต่อเนื่องหรือเกิดเฉพาะ composition สุดขอบ ต้องอธิบาย R0 เป็น capability-only และ R1 เป็น ability-resource coupled robustness")
    th_paragraph(doc, "P95 ที่ลดมากไม่ได้แปลว่า heterogeneity เร็วกว่าอย่างเดียว เพราะ H0 มี median unsettled 0.342 ขณะที่ H1/H2 เป็นศูนย์และมี explicit dead-letter สูงกว่า ใน R0 heterogeneity ลด cost ราว 5% แต่ throughput ลดเล็กน้อย ส่วน R1 cost เพิ่ม 40–82% แลกกับ throughput เพิ่ม 2–5% จึงยืนยันว่า resource mapping เป็น moderator สำคัญ")
    th_heading(doc, "9.3 RQ3 — Component Ablation", level=2)
    add_th_result_table(doc, data, "RQ3")
    th_paragraph(doc, thai_family_summary(data, "RQ3"))
    th_paragraph(doc, "หาก A3 stand-down มี effect เล็กหรือไม่ significant ห้ามลบผลหรือเปลี่ยนสมมติฐาน ให้สรุปว่า stand-down เป็น bounded refinement ขณะที่ effect หลักอาจมาจาก assessment, fit หรือ aging")
    th_paragraph(doc, "ผลจริงสนับสนุน Fit ค่อนข้างชัด: ลด cost 3.5–3.7%, เพิ่ม throughput ราว 2.2% และลด P95 ราว 12% ส่วน Aging เพิ่ม completion 10.4–10.8 จุดและลด dead-letter ราว 12.4 จุด แต่ P95 ยาวขึ้น 77–86% Assessment ช่วย throughput/completion แต่มี cost overhead และเปลี่ยน backlog เป็น terminal outcomes ขณะที่ Stand-down แทบไม่เปลี่ยน cost/throughput/completion และทำให้ P95 แย่ลงเล็กน้อย")
    th_heading(doc, "9.4 E4 — No-Volunteer Fallback", level=2)
    add_th_result_table(doc, data, "E4")
    th_paragraph(doc, thai_family_summary(data, "E4"))
    th_paragraph(doc, "F3 อาจดูดีบาง metric เพราะมีตัวกลาง forced rescue แต่ต้องเรียกว่า hybrid reference ไม่ใช่ ConveyorFlow และต้องอ่าน P95 พร้อม dead-letter/unsettled เพื่อไม่ให้ระบบที่ทิ้งงานเร็วดูเหมือนเร็วโดยผิดความหมาย")
    th_paragraph(doc, "F2 เทียบ F0/F1 ลด cost และ dead-letter พร้อมเพิ่ม throughput มาก แต่ใช้เวลาจน terminal นานกว่า ส่วนเทียบ F3 นั้น F2 มี cost ใกล้กัน แต่ throughput ต่ำกว่า 3.7–5.7%, P95 สูงกว่า 9.6–12.2% และ dead-letter สูงกว่า 1.1–1.7 จุด ซึ่งเป็นต้นทุนของการคง fallback แบบ decentralized ใน stress test นี้")
    th_heading(doc, "9.5 Robustness", level=2)
    th_paragraph(doc, "Absolute outcomes ไวต่อ resource mapping และ lower/upper difficulty mapping จึงห้ามอ้างว่าตัวเลขจะคงเดิมเมื่อเปลี่ยนสมมติฐาน อย่างไรก็ตาม secondary derived analysis พบว่า CF-Fit เทียบ S2 มีทิศทางเหมือนกันทั้ง lower/adjudicated/upper: ต้นทุนสูงกว่า, throughput สูงกว่า และ P95 ต่ำกว่า ส่วนเทียบ Central-Fit ต้นทุนและ P95 ใกล้กัน แต่ throughput/completion ของ CF-Fit ต่ำกว่าเล็กน้อย โดย quality non-inferiority ยังผ่านทุก mapping การสรุป secondary นี้บันทึกหลังเห็น confirmatory results และไม่ใช้เปลี่ยน primary claim")

    th_heading(doc, "9.6 Real-LLM Ability Calibration ก่อน Main Experiment", level=2)
    th_paragraph(doc, "Calibration เรียก MFEC deployment aliases จริง แต่ยังไม่รันหรือเปรียบเทียบ ConveyorFlow policies ใช้ held-out probes แยก ML Build และ Fix Bug พร้อม Wilson lower 95% gate ภายใต้ completion-token budget 4,096 เท่ากัน และหยุดค้นหา candidate ตาม stopping rule ก่อนเห็น policy outcome")
    table = doc.add_table(rows=1, cols=4)
    for index, value in enumerate(("MFEC alias", "ML Build", "Fix Bug", "บทบาท")):
        table.rows[0].cells[index].text = value
    for values in (
        ("tencent-hy3", "L3", "L1", "เก่ง ML / Fix Bug ขั้นพื้นฐาน"),
        ("gpt-5-mini", "L2", "L3", "ML ระดับกลาง / Fix Bug ขั้นสูง"),
        ("glm-5.3-flash", "L3", "L3", "Advanced generalist"),
    ):
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = value
    format_table(table, font="TH Sarabun New", size=13, header_fill="D9EAF7")
    doc.add_picture(str(ABILITY_FIGURES / "fig_ability_profile_radar.png"), width=Cm(16.5))
    add_caption(doc, "รูปที่ 9 Ability pass-rate profile สำหรับเลือกทีมก่อน Main Real-LLM; พื้นที่ radar เป็น descriptive เท่านั้น Rank ใช้ confidence-bound gate ที่กำหนดล่วงหน้า", font="TH Sarabun New", size=12)
    th_paragraph(doc, "ทีมสุดท้ายมี rank vector ML=[L3,L2,L3] และ Fix Bug=[L1,L3,L3] จึงทดสอบ Capability Fit และ Stand-down ได้โดยตรง แต่ยังห้ามอ้างว่า ConveyorFlow ชนะ baseline บนโมเดลจริง เพราะยังไม่มี allocation-policy execution")
    th_paragraph(doc, "ขณะนี้ 60 case bundles, deterministic validators และ allocation engine ถูก audit และ freeze แล้ว ตัวรันจะเลือก atomic-claim winner ก่อน execute และเรียกหลาย agent พร้อมกันจริงแบบไม่มี round barrier พร้อมวัด wall-clock throughput, completion/terminal time, busy time, utilization, token และ cost การทดสอบ sleeping-oracle เห็น peak concurrency=3 และผ่านครบ แต่ติดป้าย research_results=false จึงไม่ใช่ผล Real-LLM")
    th_paragraph(doc, "Preflight ล่าสุดเหลือ blocker ภายนอกเพียง immutable alias-to-version mapping และราคา input/output token ของ MFEC ทั้ง 3 รุ่น จากนั้นจึง freeze config และรัน Main Real-LLM ได้ ส่วน human-expert validation ข้ามไว้ตามแผนและผู้วิจัยจะดำเนินการแยกต่างหาก")

    th_heading(doc, "10. Claim ที่เขียนได้และ Claim ที่ห้ามเขียน")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "เขียนได้"
    table.rows[0].cells[1].text = "ห้ามเขียน/ต้องหลีกเลี่ยง"
    claim_rows = [
        ["CF-Fit เปลี่ยน trade-off vector ภายใต้ simulation ตามผลที่รายงาน", "CF-Fit ชนะทุก baseline ทุก metric"],
        ["Agent เลือกงานเองโดยไม่มี central assignment decision", "ระบบไม่มีส่วนกลางเลย—เพราะ belt/ledger/CAS เป็น shared infrastructure"],
        ["LLM annotations เป็น reproducible design inputs", "ผู้เชี่ยวชาญมนุษย์ 3 คนให้ ground truth"],
        ["Ability L1–L3 เป็น calibrated behavioral levels", "L3 คือโมเดลใหม่สุด/แพงสุดโดยนิยาม"],
        ["ผลเป็น discrete-event simulation evidence", "เป็นผล benchmark ของ Claude/OpenAI รุ่นจริง"],
        ["มีผล Real-LLM Ability Calibration และเลือกทีม heterogeneous ก่อน Main แล้ว", "Calibration เท่ากับผลเปรียบเทียบ ConveyorFlow policy หรือพิสูจน์ว่า provider ใดเหนือกว่า"],
        ["Concurrent runner ผ่าน offline infrastructure audit และ peak overlap=3", "ตัวเลข mock throughput/latency เป็นผลวิจัย Real-LLM"],
        ["Stand-down เป็น bounded hesitation ที่ decay ตาม age", "Agent เก่งปฏิเสธงานง่ายถาวร"],
    ]
    for row_values in claim_rows:
        cells = table.add_row().cells
        for i, value in enumerate(row_values): cells[i].text = value
    format_table(table, font="TH Sarabun New", size=13, header_fill="E2F0D9")

    th_heading(doc, "11. คำถามที่อาจารย์หรือ Reviewer น่าจะถาม")
    qa = [
        ("ทำไมไม่ใช้ Model จริง?", "ขณะนี้ใช้ MFEC models จริงในขั้น Ability Calibration แล้ว และเลือกทีม Tencent HY3, GPT-5 mini และ GLM 5.3 Flash ส่วน 60 executable cases, validator, engine และ concurrent runner พร้อมแล้ว; Main Real-LLM เหลือรอ immutable alias mapping และราคาจาก MFEC ก่อน freeze config"),
        ("Decentralized จริงหรือไม่?", "Decentralized เฉพาะ assignment decision: Agent ประเมินและเลือกเอง ไม่มี global matcher ใน CF-Fit แต่มี shared belt, ledger และ atomic claim infrastructure"),
        ("ทำไมใช้ LLM คนเดียวประเมิน difficulty หลายบทบาท?", "เพื่อสร้าง reproducible operational labels เมื่อยังไม่มี human panel พร้อมเปิดเผยว่าไม่ independent และทำ lower/upper sensitivity; ก่อนยืนยัน external validity ต้องมี human experts"),
        ("ทำไม baseline ไม่มี Oracle/HEFT?", "Oracle ใช้ข้อมูลอนาคตและ HEFT ต้องมี execution estimates/global scheduling assumptions ที่ไม่เท่ากับ online local observation จึงเทียบไม่เป็นธรรม; ใช้ static realistic controls และ Central-Fit ที่ matched inputs แทน"),
        ("ทำไมทีมไม่เกิน 4 Agent?", "เป็น scope ที่ freeze เพื่อควบคุม factorial size และตีความ composition ได้ตรง; scalability beyond four agents เป็น future work"),
        ("ถ้าไม่มีคนรับงานทำอย่างไร?", "F2 ค่อย ๆ ลด threshold และ stand-down, tail-requeue ที่ W1/W2 และ dead-letter ที่ W3/requeue limit; F3 เป็น central rescue reference"),
        ("Ability กับราคาปนกันไหม?", "ไม่ปนในนิยาม R0 แยก ability จาก resource; R1 แล้ว reversed/permuted sensitivity ใช้ตรวจ confounding"),
        ("ทำไมไม่ประกาศ winner?", "เพราะ cost, time, throughput และ completion conflict กัน จึงใช้ vector และ non-inferiority constraints ตาม comment ที่ปรึกษา"),
    ]
    for question, answer in qa:
        paragraph = doc.add_paragraph()
        add_text(paragraph, f"Q: {question}", font="TH Sarabun New", size=15, bold=True)
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(0.7)
        add_text(paragraph, f"A: {answer}", font="TH Sarabun New", size=15)

    th_heading(doc, "12. Limitations และขั้นถัดไปก่อนส่ง Journal")
    for text in (
        "ให้อาจารย์ตรวจ scientific claim, target journal และ contribution framing ก่อน submission",
        "เติม affiliation, corresponding e-mail, ORCID, funding/acknowledgment และ data/code DOI โดยไม่เดา",
        "ปรับ manuscript เข้ากับ template ของวารสารเป้าหมายโดยตรง; เอกสารนี้เป็น IEEE-style pre-submission draft",
        "ทำ human-expert validation ของ difficulty labels หรืออย่างน้อย blinded expert subsample โดยผู้วิจัยเป็นผู้ดำเนินการ",
        "ขอ immutable alias-to-version mapping และราคา input/output token ของ MFEC ทั้ง 3 รุ่น แล้ว freeze config ก่อน Main Real-LLM; 60 bundles, validators, allocation engine และ concurrent runner พร้อมและผ่าน offline audit แล้ว",
        "เพิ่ม communication-failure, larger-team และ live-token-price sensitivity เฉพาะเป็นงานถัดไป ไม่ปนกับ confirmatory Main นี้",
    ):
        add_bullet(doc, text, font="TH Sarabun New", size=15)

    doc.add_page_break()
    th_heading(doc, "13. Reproducibility Checklist")
    checks = [
        ("Main runs", f"{data['integrity']['observed_runs']}/{data['integrity']['expected_runs']} unique; duplicates={data['integrity']['duplicate_run_ids']}"),
        ("Event ledgers", f"verified={data['verification']['event_hashes_checked']}; mismatches={len(data['verification']['event_hash_mismatches'])}"),
        ("Simulation source", f"hash match={data['verification']['source_hash_matches']}"),
        ("Source snapshot", "SHA-256 91e2cec400769fce8cea53682ebfe0b67c93bdc2756b365ad0bf56a1c8995c25"),
        ("Difficulty labels", "SHA-256 56207cd87a28ab221911c2bf07ee0cf6f8ec6547bab7880fc5ef268ad24b2add"),
        ("Seeds", "1000–1049; analysis seed 20260922"),
        ("Secondary RQ1", f"Pareto 20 rows; competing-risk ledgers checked={data['secondary_integrity']['competing_risk']['runs_checked']}; class=secondary exploratory"),
        ("Real-LLM scaffold", f"preflight cases={data['real_llm_dry_run']['cases']}; bundles/validators/engine ready; remaining blocker codes={','.join(item['code'] for item in data['real_llm_dry_run']['blockers'])}; policy results=none"),
        ("Concurrent runner", f"offline audit={data['concurrency_audit']['status']}; peak active={data['concurrency_audit']['mock_peak_active']}; research_results={data['concurrency_audit']['research_results']}; provider calls={data['concurrency_audit']['provider_calls']}"),
        ("Real-LLM ability", "ML ranks=L3/L2/L3; Fix Bug ranks=L1/L3/L3; calibration only, not policy outcome"),
        ("Protocol deviations", "Session interruption resumed from checkpoint; analysis code corrected before effects to separate R0/R1 and add preregistered interactions; no engine/seed/config/outcome rule changed"),
        ("Advisor sign-off", "ยังไม่บันทึก—ต้องขออนุมัติก่อน submission"),
    ]
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "รายการ"
    table.rows[0].cells[1].text = "สถานะ/หลักฐาน"
    for row_values in checks:
        cells = table.add_row().cells
        for i, value in enumerate(row_values): cells[i].text = value
    format_table(table, font="TH Sarabun New", size=13)

    doc.core_properties.title = "ConveyorFlow v2 — เอกสารอธิบายงานวิจัยสำหรับอาจารย์ที่ปรึกษา"
    doc.core_properties.author = "Sakan Punyanon"
    doc.core_properties.subject = "Step-by-step research and experiment explanation"
    doc.save(ADVISOR)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ConveyorFlow manuscript artifacts from validated results.")
    parser.add_argument("--ieee-only", action="store_true", help="Build only the IEEE-style manuscript.")
    args = parser.parse_args()
    data = load_inputs()
    build_ieee(data)
    outputs = [str(MANUSCRIPT)]
    if not args.ieee_only:
        build_advisor(data)
        outputs.append(str(ADVISOR))
    print(json.dumps({"status": "complete", "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
