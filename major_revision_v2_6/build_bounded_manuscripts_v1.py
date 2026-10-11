"""Make versioned manuscript copies with audited executable and fault evidence.

This script never edits the source manuscripts. It deliberately keeps the earlier
simulation and microtask cohorts separate from the v2.4 executable cohort.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "manuscripts_bounded_v2_6"

ABSTRACT = (
    "Heterogeneous large language model (LLM) agents differ in capability, speed, "
    "and resource use. ConveyorFlow lets idle agents inspect dependency-ready tasks "
    "on a shared belt, assess capability–task fit locally, volunteer, and temporarily "
    "stand down when overqualified. We evaluate throughput, completion time, "
    "utilization, and cost as separate, potentially conflicting outcomes. A frozen "
    "22,500-run simulation provides controlled comparisons with static and centralized "
    "allocation and tests team composition and mechanism ablations. A separate, "
    "independently audited real-LLM cohort comprises 11 paired blocks, each with an "
    "executable four-stage ML pipeline and a container-verified repository repair. "
    "CF-Fit verified 17/22 jobs, rule-matched central allocation 14/22, and static "
    "ownership 18/22; observed verified throughput was 1.545, 1.273, and 1.636 "
    "jobs/hour, respectively. In a separate matched decision-layer fault experiment, "
    "both mechanisms verified 3/3 tasks without faults; during a coordinator-only "
    "outage, CF-Fit verified 3/3 and the centralized arm 0/3, whereas a shared "
    "belt/claim-store outage stopped both. These results support a bounded claim: "
    "self-selection can run executable jobs without a central allocation decision "
    "process, but it is not universally superior, system-wide fault tolerant, or "
    "generalized across repositories. Complete monetary cost per verified job could "
    "not be established for the executable cohort because billing was missing for "
    "some attempts."
)

METHOD = [
    "Executable-workload validation was kept distinct from the earlier 60-case "
    "microtask and repair-surrogate study. Eleven independently audited paired "
    "blocks used the same two jobs in each arm: one complete four-stage ML DAG "
    "and one repository repair. The latter was accepted only by containerized, "
    "task-specific verification. The arms were CF-Fit, Central-Rule-Matched, and "
    "Static-Owners, each with a 3,600-second observation horizon. The paired block, "
    "not the LLM request, is the comparison unit. The cohort reused four repository "
    "projects and two ML corpora; its 159 provider attempts are not independent "
    "replicates. One interrupted planned block had unresolved provider outcomes and "
    "was excluded without replay or imputation. The separately frozen v2.5 "
    "two-block recovery extension was not pooled with this cohort.",
    "To isolate the location of the allocation decision, we additionally used a "
    "matched, no-LLM process-fault experiment. Both arms had the same three-task "
    "READY belt, Rank 1/2/3 team, fit and stand-down rules, SQLite atomic claim, "
    "verification fixtures, and service outcomes. Only the decision process was "
    "agent-local in CF-Fit and coordinator-local in Central-Rule-Matched. Twenty "
    "tie-breaking seeds were crossed with four fault scenarios and two arms "
    "(160 audited trials). The seeds perturb the same task stream and are not 20 "
    "independent workload samples. This experiment measures decision-layer "
    "dependence, not LLM quality, provider latency, production failure rates, or "
    "end-to-end reliability.",
]

RESULT = [
    "The executable cohort verifies that the mechanism was exercised beyond "
    "microtasks: CF-Fit completed 9/11 full ML pipelines and 8/11 repository "
    "repairs; the central arm completed 8/11 and 6/11; static ownership completed "
    "9/11 and 9/11. CF-Fit minus central allocation had a paired mean verified "
    "throughput difference of +0.273 jobs/hour; CF-Fit minus static ownership "
    "was −0.091 jobs/hour. Conditional completion-time differences were +4.10 s "
    "and −141.09 s, respectively, but the sets of verified jobs differ by arm, "
    "so these are not all-job speed effects. Busy-utilization differences were "
    "+0.00488 and −0.01490. Busy time includes provider waiting and verification "
    "and is not synonymous with productive work. Excluding the partially exposed "
    "first block leaves 15/20, 12/20, and 16/20 verified jobs in the same arm order.",
    "Known provider-reported cost units were 0.316764190, 0.299882132, and "
    "0.283972888, respectively; one, one, and three attempts had unknown cost. "
    "The provider unit was not independently verified as a currency. Therefore "
    "total monetary cost and cost per verified job for this executable cohort "
    "are missing, not zero, and no cost-efficiency winner is claimed.",
    "In the matched fault experiment, no-fault verification was 3/3 for each arm. "
    "A coordinator-only outage yielded 3/3 verified tasks for CF-Fit and 0/3 "
    "for the central arm during the fault window. A shared belt/claim-store outage "
    "yielded 0/3 for both; an agent-A2 outage yielded 2/3 for both. Every "
    "scenario returned to 3/3 after recovery. The pattern recurred under the 20 "
    "tie seeds, with audited proposal/claim parity in the no-fault setting. "
    "This supports a narrower architectural claim—removal of the central "
    "allocation-decision process from CF-Fit's critical path—not removal of "
    "all shared failure domains."
]

LIMIT = (
    "The executable study contains 11 paired blocks but only four source "
    "repositories and two ML corpora. Reused projects, datasets, stages, and API "
    "calls cannot be treated as independent samples; descriptive cluster "
    "intervals are not population-level confidence, superiority, or equivalence "
    "tests. Provider delay and dynamic task choices also mean that the live "
    "CF-Fit–central contrast does not identify a pure causal effect of decision "
    "location. The controlled fault experiment isolates that location for one "
    "small task stream, but does not establish production reliability. The shared "
    "READY belt, claim store, verifier, and provider gateway remain potential "
    "common failure domains. The v2.5 recovery blocks are exploratory and are "
    "reported separately. No complete monetary cost comparison is possible for "
    "the executable cohort while unknown-cost attempts remain."
)

CONCLUSION_ADD = (
    "The independently audited executable cohort demonstrates feasibility on "
    "full ML DAGs and container-verified repository repairs, not only microtasks. "
    "Its observed allocation outcomes form a trade-off rather than a universal "
    "ranking: CF-Fit verified more jobs than rule-matched central allocation, "
    "but static ownership verified the most. A matched fault experiment supports "
    "the limited claim that CF-Fit can continue allocation during an outage of "
    "the central decision process; failure of the shared belt/claim store stops "
    "both arms. These findings do not establish general superiority, equivalence, "
    "complete cost efficiency, or system-wide fault tolerance."
)


def insert_before(anchor, text: str, style: str = "Normal"):
    p = anchor.insert_paragraph_before(text)
    p.style = style
    return p


def find(doc: Document, exact: str):
    hits = [p for p in doc.paragraphs if p.text.strip() == exact]
    if len(hits) != 1:
        raise ValueError(f"Expected one anchor {exact!r}; found {len(hits)}")
    return hits[0]


def table_before(anchor, rows: list[tuple[str, ...]], doc: Document):
    table = doc.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    for row in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, row):
            cell.text = value
    anchor._p.addprevious(table._tbl)


def add_evidence(doc: Document, *, ajstr: bool):
    abstract = next(p for p in doc.paragraphs if p.text.startswith("Abstract"))
    abstract.text = ("Abstract: " if ajstr else "Abstract—") + ABSTRACT

    method_anchor = find(doc, "3. Results and Discussion" if ajstr else "VI. RESULTS")
    insert_before(
        method_anchor,
        "2.2.8. Executable paired validation and matched decision faults"
        if ajstr else "H. Executable Paired Validation and Matched Decision Faults",
        "Heading 3" if ajstr else "Heading 2",
    )
    for paragraph in METHOD:
        insert_before(method_anchor, paragraph)

    result_anchor = find(doc, "3.10. Interpretation" if ajstr else "VII. DISCUSSION")
    insert_before(
        result_anchor,
        "3.10. Executable workloads and decision-layer fault control"
        if ajstr else "J. Executable Workloads and Decision-Layer Fault Control",
        "Heading 2",
    )
    insert_before(
        result_anchor,
        "Table 9. Independently audited executable cohort; 11 paired blocks"
        if ajstr else "TABLE IX. INDEPENDENTLY AUDITED EXECUTABLE COHORT; 11 PAIRED BLOCKS",
    )
    table_before(
        result_anchor,
        [
            ("Arm", "Verified", "Full ML", "Repo repair", "Jobs/hour", "Unknown-cost calls"),
            ("CF-Fit", "17/22", "9/11", "8/11", "1.545", "1"),
            ("Central-Rule-Matched", "14/22", "8/11", "6/11", "1.273", "1"),
            ("Static-Owners", "18/22", "9/11", "9/11", "1.636", "3"),
        ],
        doc,
    )
    for paragraph in RESULT[:2]:
        insert_before(result_anchor, paragraph)
    insert_before(
        result_anchor,
        "Table 10. Matched decision-layer fault experiment; verified tasks during the fault window"
        if ajstr else "TABLE X. MATCHED DECISION-LAYER FAULT EXPERIMENT; VERIFIED TASKS DURING FAULT",
    )
    table_before(
        result_anchor,
        [
            ("Fault scenario", "CF-Fit", "Central-Rule-Matched"),
            ("No fault", "3/3", "3/3"),
            ("Coordinator-only outage", "3/3", "0/3"),
            ("Shared belt/claim-store outage", "0/3", "0/3"),
            ("Agent A2 outage", "2/3", "2/3"),
        ],
        doc,
    )
    insert_before(result_anchor, RESULT[2])

    if ajstr:
        find(doc, "3.10. Interpretation").text = "3.11. Interpretation"
        find(doc, "3.11. Limitations").text = "3.12. Limitations"
        limit_anchor = find(doc, "4. Conclusions")
        conclusion_anchor = find(doc, "Data and code availability")
        old_fault = "and failure injection was outside the experiment"
    else:
        limit_anchor = find(doc, "IX. CONCLUSION")
        conclusion_anchor = find(doc, "DATA AND CODE AVAILABILITY")
        old_fault = "and failure injection was outside the experiment"
    insert_before(limit_anchor, LIMIT)
    insert_before(conclusion_anchor, CONCLUSION_ADD)

    # Replace the now-obsolete statement without changing earlier cohort results.
    for p in doc.paragraphs:
        if "no component-failure injection was performed" in p.text:
            p.text = p.text.replace(
                "and no component-failure injection was performed.",
                "The separate matched v2.4 decision-layer fault experiment is reported below.",
            )
        if old_fault in p.text:
            p.text = p.text.replace(
                old_fault,
                "a separate matched decision-layer fault test, rather than the live LLM cohort, supplies the limited outage evidence",
            )

    availability = next(p for p in doc.paragraphs if p.text.startswith("The v2 research package") or p.text.startswith("Code, frozen configurations"))
    if ajstr:
        availability.text += (
            " The anonymized executable-cohort protocol, lock, audited summaries, "
            "and fault-test code can be supplied for blinded review; the public "
            "author-identified repository link is withheld from this copy."
        )
    else:
        availability.text += (
            " Audited v2.4 executable and decision-fault summaries and v2.6 source "
            "eligibility records are available at "
            "https://github.com/sakanarm/ConveyorFlowExperimental."
        )


def set_properties(doc: Document, *, blind: bool):
    props = doc.core_properties
    props.title = "ConveyorFlow decentralized task allocation manuscript"
    props.subject = "Executable workload and decision layer evidence"
    props.author = "" if blind else "Sakan Punyanon"
    props.last_modified_by = "" if blind else "Sakan Punyanon"
    props.comments = ""


def build_ieee():
    doc = Document(ROOT / "ConveyorFlow_IEEE_Manuscript.docx")
    add_evidence(doc, ajstr=False)
    set_properties(doc, blind=False)
    out = OUT / "ConveyorFlow_IEEE_Manuscript_Bounded_v2_6.docx"
    doc.save(out)
    return out


def build_ajstr():
    doc = Document(ROOT / "AJSTR Journal" / "ConveyorFlow_AJSTR_Blinded_Manuscript.docx")
    add_evidence(doc, ajstr=True)
    set_properties(doc, blind=True)
    blind = OUT / "ConveyorFlow_AJSTR_Blinded_Bounded_v2_6.docx"
    doc.save(blind)

    # The non-blind copy differs only in author-identifying front matter and link.
    unblind = Document(blind)
    lines = [
        "Sakan Punyanon 1, Chaiyaporn Khemapatapan 2, Aomduan Jeamaon 3",
        "1 College of Innovative Technology and Engineering, Dhurakij Pundit University, Thailand; 68140010@dpu.ac.th; ORCID 0009-0004-5309-8926",
        "2 College of Innovative Technology and Engineering, Dhurakij Pundit University, Thailand; chaiyaporn@dpu.ac.th; ORCID 0009-0008-8393-7478",
        "3 College of Innovative Technology and Engineering, Dhurakij Pundit University, Thailand; aomduan.jea@dpu.ac.th; ORCID 0009-0009-0435-5769",
        "Correspondence: Sakan Punyanon, 68140010@dpu.ac.th",
    ]
    anchor = unblind.paragraphs[1]
    for line in lines:
        insert_before(anchor, line)
    availability = next(p for p in unblind.paragraphs if "The anonymized executable-cohort protocol" in p.text)
    availability.text = availability.text.replace(
        "The anonymized executable-cohort protocol, lock, audited summaries, "
        "and fault-test code can be supplied for blinded review; the public "
        "author-identified repository link is withheld from this copy.",
        "Audited executable-cohort and fault-test summaries and code are available at "
        "https://github.com/sakanarm/ConveyorFlowExperimental.",
    )
    for heading, statement in [
        (
            "Author Contributions",
            "Sakan Punyanon: conceptualization, software, investigation, data curation, formal analysis, and original draft. Chaiyaporn Khemapatapan: conceptualization, methodology, supervision, and review and editing. Aomduan Jeamaon: conceptualization, experimental design, supervision, and review and editing. All authors reviewed and approved the manuscript.",
        ),
        (
            "Funding",
            "This research received no external research grant and was supported by the authors. Dhurakij Pundit University supports the article processing charge. No grant number applies.",
        ),
        (
            "Conflicts of Interest",
            "The authors declare no conflicts of interest.",
        ),
    ]:
        ref = find(unblind, "References")
        insert_before(ref, heading, "Heading 1")
        insert_before(ref, statement)
    set_properties(unblind, blind=False)
    identified = OUT / "ConveyorFlow_AJSTR_Unblinded_Bounded_v2_6.docx"
    unblind.save(identified)
    return blind, identified


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = [build_ieee(), *build_ajstr()]
    for file in files:
        doc = Document(file)
        print(f"{file}: {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables, {len(doc.inline_shapes)} inline figures")


if __name__ == "__main__":
    main()
