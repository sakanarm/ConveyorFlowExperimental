# ConveyorFlow Main Results — Confirmatory Simulation

## Secondary Pareto and competing-risk views

Two-objective Pareto frontiers support the trade-off framing but do not create a
new overall rank. In cost-throughput space, CF-Fit is slightly dominated by the
matched Central-Fit controller in both R0 and R1. Different static policies remain
nondominated because lower cost is accompanied by lower throughput. In
P95-completion space, Central-Fit is the only nondominated policy in R0; CF-Fit
joins it in R1 by exchanging slightly lower P95 time for slightly lower completion.

Run-level Aalen-Johansen curves were computed from all 4,500 RQ1 event ledgers.
At 1,000 ticks, median verified cumulative incidence for CF-Fit versus Central-Fit
was 0.590 versus 0.602 in R0 and 0.615 versus 0.621 in R1. Median dead-letter
incidence was 0.410 versus 0.396 and 0.382 versus 0.378, respectively. These
secondary curves show that CF-Fit closely follows Central-Fit and that terminal
latency must be interpreted together with verification, dead-letter, and
right-censoring. The percentile bands summarize run-to-run heterogeneity and are
not confidence intervals.

## Integrity

- Completed runs: 22,500/22,500
- Unique run IDs: 22,500; duplicates: 0
- Zero-success runs: 0
- Artifact verification: PASS; event hashes checked: 22,500
- Source hash match: True

All confirmatory statements below are conditional on the frozen discrete-event simulation. They are not measurements of named commercial LLMs.

## RQ1 — CF-Fit versus static and centralized allocation

Percentages are paired median differences relative to the comparator median. Asterisks mark Holm-adjusted p<0.05. Negative cost and P95 time are favorable; positive throughput is favorable.

| Resource | Comparator | Cost | Throughput | P95 time | Completion NI | Dead-letter NI | Unsettled NI |
|---|---|---:|---:|---:|:---:|:---:|:---:|
| R0 | S1 | +5.8%* | +42.0%* | -77.9%* | True | False | True |
| R0 | S2 | +52.3%* | +25.8%* | -83.1%* | True | False | True |
| R0 | S3 | +4.7%* | +9.4%* | -67.9%* | True | False | True |
| R0 | CENTRAL_FIT | +0.1% | -1.1%* | -0.6% | True | True | True |
| R1 | S1 | +52.4%* | +45.3%* | -77.3%* | True | False | True |
| R1 | S2 | +4.9%* | +22.8%* | -82.5%* | True | False | True |
| R1 | S3 | +8.8%* | +14.7%* | -74.2%* | True | False | True |
| R1 | CENTRAL_FIT | +0.5%* | -1.5%* | +0.0% | True | True | True |

## RQ2 — Capability heterogeneity under CF-Fit

H0=(2,2,2,2), H1=(1,2,2,3), and H2=(1,1,3,3) hold team size and mean ability constant while increasing ability variance.

| Resource | Contrast | Cost | Throughput | P95 time | Completion Δ |
|---|---|---:|---:|---:|---:|
| R0 | H1_minus_H0 | -5.1%* | -0.5% | -63.0%* | -0.003 |
| R0 | H2_minus_H0 | -5.2%* | -1.4%* | -64.3%* | -0.007* |
| R0 | H2_minus_H1 | -0.2% | -1.5%* | -3.2%* | -0.009* |
| R1 | H1_minus_H0 | +39.6%* | +2.3%* | -61.6%* | 0.011* |
| R1 | H2_minus_H0 | +81.8%* | +4.7%* | -63.1%* | 0.021* |
| R1 | H2_minus_H1 | +29.0%* | +1.4%* | -3.9%* | 0.007* |

## RQ3 — Component ablations

The direction is Full minus ablation. A small A3 effect means stand-down is a bounded refinement rather than the sole explanation for CF-Fit.

| Resource | Removed component | Cost | Throughput | P95 time | Completion Δ |
|---|---|---:|---:|---:|---:|
| R0 | Assessment | +6.7%* | +4.0%* | -65.9%* | 0.015* |
| R0 | Fit | -3.7%* | +2.2%* | -11.9%* | 0.009* |
| R0 | Stand-down | +0.1% | +0.2% | +1.2%* | 0.001 |
| R0 | Aging | -8.1%* | +37.3%* | +77.1%* | 0.108* |
| R1 | Assessment | +4.6%* | +4.1%* | -64.4%* | 0.017* |
| R1 | Fit | -3.5%* | +2.3%* | -11.8%* | 0.010* |
| R1 | Stand-down | +0.3% | -0.2% | +0.8%* | -0.001 |
| R1 | Aging | -15.0%* | +33.0%* | +85.5%* | 0.104* |

## E4 — No-volunteer fallback

F2 is the decentralized aging-and-relaxation default. F3 is a hybrid reference because a central component forces rescue.

| Resource | Contrast | Cost | Throughput | P95 time | Dead-letter Δ | Unsettled Δ |
|---|---|---:|---:|---:|---:|---:|
| R0 | F2−F0 | -23.9%* | +61.6%* | +73.5%* | -0.113* | 0.000 |
| R0 | F2−F1 | -23.6%* | +61.7%* | +74.0%* | -0.113* | 0.000 |
| R0 | F2−F3 | -0.0% | -5.7%* | +9.6%* | 0.017* | 0.000 |
| R1 | F2−F0 | -34.5%* | +56.0%* | +79.5%* | -0.111* | 0.000 |
| R1 | F2−F1 | -34.5%* | +56.5%* | +81.0%* | -0.112* | 0.000 |
| R1 | F2−F3 | +1.6%* | -3.7%* | +12.2%* | 0.011* | 0.000 |

## Interpretation boundary

The manuscript must describe a multi-objective trade-off, not a universal winner. Non-inferiority decisions use frozen absolute margins of 0.03 for completion, dead-letter, and unsettled fractions. LLM-derived difficulty labels are design inputs with same-model procedural-stability evidence, not human expert ground truth.

