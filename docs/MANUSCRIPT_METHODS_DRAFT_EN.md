# Methods Draft — ConveyorFlow Simulation Study

## Study design and claim boundary

We conducted a preregistered discrete-event simulation study of ConveyorFlow, a
decentralized volunteer-based task-allocation architecture. The study estimates
trade-offs rather than presuming that one policy dominates all outcomes. The primary
outcome is cost per verified task subject to prespecified completion-quality
constraints; verified throughput and P95 terminal flow time are key secondary
outcomes. The evidence is simulation-conditional and is not presented as observed
performance of named commercial LLMs.

## Public workload sources

Workloads were derived from UCI Adult (48,842 records), UCI Beijing Multi-Site Air
Quality (420,768 records), and the CodeXGLUE Bugs2Fix small training corpus (46,680
before/after function pairs). Raw files, source URLs, licenses, byte sizes, and SHA-256
checksums are recorded in `data/manifest.json`. Bugs2Fix supplies distributional
characteristics only; its normalized pairs are not treated as executable repository
tests.

Each job is a finite dependency graph. Adult and Beijing jobs contain seven stages:
load validation, exploratory analysis, cleaning/feature construction, baseline
modeling, advanced modeling, evaluation, and reporting. Bugs2Fix jobs contain five
stages: reproduction, localization, repair, regression testing, and reporting.

## Operational task difficulty

Task difficulty was operationalized using a reproducible, role-conditioned LLM
annotation panel. Three blinded evaluation passes were elicited from the same
underlying model under the roles of ML Methodologist, Software Reliability Reviewer,
and Workflow/Resource Reviewer. Each pass scored five rubric dimensions from 0 to 2:
specification ambiguity, scope/context span, dependency depth, reasoning depth, and
verification complexity. Totals 0–3, 4–6, and 7–10 mapped to D1, D2, and D3.
Failure impact was recorded separately.

The 304 items were stage-by-stratum specifications, not duplicated dataset records.
Forty-eight deterministic variants were derived from public-corpus characteristics:
16 Adult age-by-hours strata, 16 Beijing station/season strata, and 16 Bugs2Fix
source-length-by-patch-delta strata. Evaluation order was shuffled independently for
each pass. Pairwise exact agreement, adjacent agreement, and quadratic-weighted
Cohen's kappa were reported; non-unanimous items received a separate adjudication
pass. The final file and prompt artifacts were frozen by SHA-256 before Main runs.

Because the passes used the same underlying LLM, they are not independent expert
ratings. Their agreement measures procedural stability rather than human-validated
external validity. Alternate difficulty mappings and D3-heavy workloads are included
as robustness analyses. The primary adjudicated mapping is bounded by lower and upper
mappings formed from the minimum and maximum of the three role votes; these bounds
are evaluated in a prespecified subset and cannot replace the primary mapping after
results are observed.

## Agent ability and resource profiles

Agents have workload-specific Ability Levels L1, L2, and L3, defined by calibrated
pass-probability curves rather than model names or prices. Teams contain at most four
agents. H0=(2,2,2,2), H1=(1,2,2,3), and H2=(1,1,3,3) have equal mean ability and
increasing capability variance. Resource regime R0 holds speed, token factor, and
price equal; R1 associates higher capability with higher resources/cost. Reversed and
permuted R1 mappings test confounding sensitivity. Resource regimes are analyzed
separately.

## Allocation policies

CF-Fit exposes the ordered READY frontier to idle agents. Each agent makes a noisy
local assessment of difficulty, success probability, and effort, then chooses at most
one eligible task. A deterministic keyed jitter and capability-fit backoff govern
decentralized claim attempts; no component compares all agents' scores. An
overqualified agent initially hesitates, and this stand-down penalty decays with task
age. F2, the default no-volunteer mechanism, uses bounded threshold relaxation,
stand-down relaxation, re-offering, and a terminal dead-letter rule.

Static controls are fixed skill ownership (S1), frozen LLM-difficulty routing (S2),
and precomputed round robin (S3). Central-Fit uses comparable assessment/fit inputs
but a centralized matcher. Ablations remove assessment (A1), fit (A2), stand-down
(A3), or aging (A4). F0–F3 isolate fallback behavior; F3 is reported as a hybrid
central-rescue reference rather than ConveyorFlow.

## Outcomes and event accounting

All metrics are computed from an immutable event ledger. Outcomes include verified
throughput, terminal and verified completion time, cost per verified task, utilization,
completion fraction, dead-letter fraction, unsettled fraction, rework, collision rate,
assessment burden, stand-down rate, requeue rate, and forced-rescue rate. Every
billable assessment, execution, verification, retry, and forced rescue is accounted.

## Experimental structure and statistics

The experimental unit is a complete run/seed within a workload-load-team-resource
cell. Policies in a matched cell receive common arrivals, task attributes, and keyed
potential outcomes. Tasks within a run are not treated as independent replicates.
Main analyses use 50 paired seeds (proposed range 1000–1049), paired effect estimates,
95% confidence intervals, and Holm correction within each prespecified research
question and metric family. Zero-success runs remain infeasible rather than being
replaced by zero; dead-letter and unsettled outcomes are never discarded. No
post-hoc composite winner score is constructed.

## Reproducibility and separation of phases

Calibration, Validation Pilot, Pre-Main Extensions, and Main artifacts use disjoint
seed ranges and separate directories. Pilot observations cannot be pooled into
confirmatory estimates. Code, configuration, input manifest, event logs, annotation
files, and source snapshots are hashed. Main execution remains prohibited until the
annotation file, non-inferiority margins, sample size, seed range, analysis plan, and
advisor authorization are frozen.
