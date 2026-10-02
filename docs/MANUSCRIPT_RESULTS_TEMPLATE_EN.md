# Results Template — Confirmatory Main Study

This file contains reporting structure only. It must not contain confirmatory claims
until Main E1–E4 is authorized, executed, verified, and analyzed.

## Data and run integrity

- Planned/completed runs: [TBD]
- Seeds and paired-cell completeness: [TBD]
- Artifact/hash verification: [TBD]
- Zero-success, dead-letter, and unsettled counts: [TBD]
- Protocol deviations or reruns: [TBD]

## LLM annotation evidence

- Three-pass difficulty distribution: [TBD]
- Pairwise exact/adjacent agreement and weighted kappa: [TBD]
- Items adjudicated and reasons: [TBD]
- Frozen annotation SHA-256: [TBD]
- Alternate-mapping sensitivity: [TBD]

Agreement must be described as same-model procedural stability, not human validation.

## RQ1 — Allocation mechanism trade-offs

Report CF-Fit versus S1, S2, S3, and Central-Fit by workload, load, and resource
regime. Include cost per verified task, verified throughput, P95 terminal flow time,
completion, dead-letter, unsettled, utilization, paired effect, confidence interval,
adjusted p-value, and non-inferiority decision. Do not declare a universal winner.

## RQ2 — Capability heterogeneity

Report H0/H1/H2 trends under CF-Fit at equal mean ability. Separate R0 and R1 and
state whether capability variance changes fit benefits, cost, tail time, or failure
outcomes.

## RQ3 — Mechanism ablations

Report Full-minus-A1/A2/A3/A4 paired effects. A small or null A3 result must be
reported directly: stand-down is then a bounded refinement rather than a necessary
source of the overall CF-Fit effect. Do not remove the ablation or redefine the
mechanism after observing Main results.

## E4 — No-volunteer fallback

Compare F0–F3 under mixed and D3-heavy workloads. Report that F3 uses centralized
forced rescue and is a hybrid reference. Interpret terminal time together with
dead-letter and unsettled fractions to avoid survivorship/competing-risk errors.

## Robustness and limitations

Report reversed/permuted resource mappings, alternate difficulty mappings, and any
workload-specific reversals. Limit conclusions to the simulated architecture and
state the lack of human validation for LLM-derived difficulty annotations.
