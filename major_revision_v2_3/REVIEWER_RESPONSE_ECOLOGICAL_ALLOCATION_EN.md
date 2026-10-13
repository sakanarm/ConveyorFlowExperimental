# Response to the ecological validity and decision locus concerns

This is a response draft for coauthor review, not a claim that a journal reviewer has accepted the revision. It is based on the audited six-block main analysis, including the disclosed technical replacement of interrupted Block 05.

## Concern 1: microtasks do not establish executable ML or repository repair

We agree. The original 60-case real-model tier used independent tabular calculations and behavioral repair surrogates. We now report a separate paired execution study with six mixed-workload blocks. Each block contained an Adult ML pipeline, a Beijing ML pipeline, and one BugsInPy repository repair. The ML pipelines required four verified stages: ingest, preprocess, train, and package. Repository patches ran in isolated containers and had to pass the visible bug test, public regressions, and fresh replay. The three allocation arms used the same cases, three-agent roster, verifier, and fixed 3,600-second observation horizon within each block. The arms were CF-Fit, a centralized implementation of the same fit rule, and fixed Static Owners.

The audited ledgers contain 155 provider attempts. CF-Fit verified 11/18 jobs, Central-Fit 10/18, and Static Owners 12/18. The corresponding ML pipeline counts were 11/12, 10/12, and 11/12. Only one of the 18 arm-level repository jobs passed all repair gates: Matplotlib case 28 under Static Owners. No CF-Fit or Central-Fit repository repair passed in this main study. We therefore claim executable ML allocation in this setting and one verified repository repair under a baseline. We do **not** claim that CF-Fit has demonstrated successful repository repair, general automated bug fixing, or production ML quality.

The six blocks reuse two ML corpora and include two repair cases from each of three repositories. Cases within a corpus or repository are not independent population replicates. Output-format and token-limit failures in the strict patch interface are part of the observed operational outcome, not evidence that a model could never repair the same bug under another contract.

## Concern 2: CF-Fit versus Central-Fit conflates decision location with other rules

We agree that the original global Central-Fit matcher does not isolate the location of the assignment decision. We added two narrower controls. In a frozen matched simulation, CF-Fit and Central-Matched used identical local proposals, fit and stand-down rules, claim order, and potential outcomes; 360/360 zero-overhead pairs had matching substantive event streams and metrics. Coordinator-only outages were imposed as scenarios, not estimated from production failures. In the executable real-model main, CF-Fit and CENTRAL_RULE_MATCHED shared the fit rule, roster, READY frontier, verifier, retry bounds, and atomic claim store. The pure choice function ran in agent processes in CF-Fit and in one coordinator process in the matched arm.

Across six live blocks, mean verified throughput was 1.833 jobs/hour for CF-Fit and 1.667 for the matched central arm. Their mean successful-job completion times were 322.20 and 273.59 seconds, and their mean provider-reported costs per verified job were 0.02991 and 0.03060 units. The mean paired throughput difference was +0.167 jobs/hour; its descriptive six-block bootstrap interval was [−0.333, +0.667]. On the five original complete blocks alone, the mean throughput difference was 0.000. These observations do not establish equivalence or a population-level advantage. Live assignments and provider latencies can differ after the choice function runs, so the comparison narrows but does not completely isolate a causal decision-locus effect.

CF-Fit removes the global *allocation decision maker*. It does not remove the shared READY belt, atomic claim store, verifier, event ledger, or provider gateway. We have not demonstrated system-wide fault tolerance or measured a production coordinator-failure rate.

## Protocol deviation and accounting

The original Block 05 was interrupted at the user's request before all three arms finished. Its partial ledger is preserved and excluded from research analysis; one started request has an unknown provider and billing outcome. Under a separately hashed technical replacement lock, Block 05_R1 reran all three arms with the same cases, arm order, seed, models, rules, and limits. The six analyzed blocks are 01–04, 05_R1, and 06. We report the five-original-complete-block sensitivity alongside the six-block result. Provider cost values retain the provider's unconfirmed units and are not labelled US dollars or total invoiced cost.

## Appropriate manuscript claim

The evidence supports a bounded claim: ConveyorFlow implements local capability-aware self-selection for dependency-ready tasks on a shared belt, and the tested settings yield different throughput, completion-time, utilization, cost, and task-outcome trade-offs from fixed ownership and matched centralized choice. The controlled simulation evaluates capability heterogeneity and component ablations. The real-model main demonstrates allocation over executable ML DAGs and records actual repository repair attempts. It does not identify a universally best policy, prove equivalence to centralized choice, or establish reliable repository repair by CF-Fit.

## What remains if the journal requires a stronger closure

1. Run the separately frozen repository feasibility follow-up with a more reliable, pretested patch artifact contract on unused cases. Its unit of comparison is model by case, not allocation arm; retain every failed and unresolved attempt. It cannot by itself show CF-Fit repository-repair success. If that claim is needed, preregister a subsequent paired allocation study using the new contract in all three arms. Keep both new studies separate from the existing main; do not pool results after seeing them.
2. Increase independent workload clusters and paired blocks. Report uncertainty at the corpus or repository cluster level rather than treating task variants as independent datasets. Predefine a smallest effect worth detecting if making an equivalence or non-inferiority claim.
3. If attributing an effect specifically to decision location, add a controlled replay or fault-injection experiment that fixes proposals and service times while changing only the decision locus. Treat real provider timing as an external-validity check, not a pure causal isolation.
4. Obtain independent human difficulty judgments before claiming human-valid task-difficulty labels. Until then, describe the current task-level rubric as an operational proxy.

Primary audit trail: `ecological_v1/main_analysis_with_replacement_v1.json` (SHA-256 `4808c4b22923c25c30b7fd686c33edf266755fcb5aaa4eb6b0ef7cd0dd3e44e7`), six block audit capsules, original lock `2206d6dde060cf467b920745ef3912d3da4269b8ceda4d3a9c45f3f82386efe2`, replacement lock `5161275f5a7b1b91c6758601cebbc04eeed0457ad6e1e9b0d3ca9b5aaccb2ee2`.
