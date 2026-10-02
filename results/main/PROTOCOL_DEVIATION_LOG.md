# ConveyorFlow Main — Protocol and Execution Deviation Log

## 2026-09-23: infrastructure interruption and checkpoint resume

- The original Main process stopped after 9,654 of 22,500 unique runs when the
  execution session was no longer available.
- The partial JSONL ledger and per-run compressed event files remained readable.
- Execution resumed with `python v2/scripts/run_main.py --workers 8`.
- The runner loaded the existing run IDs and skipped all completed runs. It used
  the same frozen configuration, seeds, source code, label files, and run IDs.
- No outcome-based exclusion, seed replacement, policy change, or parameter change
  was made.

Interpretation: this is an infrastructure interruption handled by the preregistered
checkpoint/rerun rule, not a substantive protocol change.

## 2026-09-23: confirmatory-analysis implementation correction

- Before Main execution completed and before comparative effects were computed,
  review of `analyze_main.py` found that the initial implementation pooled R0 and
  R1 for RQ1–RQ3/E4 effects even though the frozen preregistration required the
  resource regimes to be reported separately.
- The implementation was corrected to estimate R0 and R1 effects separately.
- Prespecified policy-by-load, policy-by-workload, and policy-by-resource
  difference-in-differences were added to the executable analysis because the
  frozen plan explicitly required these interactions.
- Holm adjustment remains within research-question and metric families. The
  experimental unit remains the paired seed/run; tasks are not treated as
  independent observations.
- Unit coverage was added for matched difference-in-differences. No simulation
  engine, design, seed, data, annotation, margin, or outcome definition changed.

Interpretation: this is a code correction that restores conformity with the frozen
analysis plan. It was made without inspecting confirmatory policy comparisons.

## 2026-09-23: secondary annotation-policy sensitivity summary

- After the 532 confirmatory metric-level effects were produced and inspected, a
  derived robustness table was added to compare CF-Fit with S2 and Central-Fit
  separately inside the lower, adjudicated, and upper difficulty mappings.
- All underlying runs, strategies, mappings, outcomes, and paired seeds were
  prespecified and already executed. No new simulation or outcome transformation
  was introduced.
- This table is labeled secondary/exploratory. It does not replace, reweight, or
  change the primary confirmatory results or their Holm families.

Interpretation: this analysis clarifies whether policy ordering is stable across
the prespecified annotation bounds; it must not be presented as an additional
confirmatory hypothesis.

## 2026-09-23: secondary Pareto and competing-risk visualizations

- After confirmatory results had been produced and inspected, descriptive
  two-objective Pareto frontiers were added for the RQ1 aggregate medians.
- Run-level Aalen-Johansen curves were added for VERIFIED and DEAD_LETTER as
  competing events, with UNSETTLED tasks right-censored at the run horizon.
- All 4,500 RQ1 ledgers were reconciled against offered, verified, dead-letter,
  and unsettled counts in `metrics.csv` before aggregation.
- Curves were calculated within each run and summarized across 450 runs per
  policy-resource cell. The 2.5th-97.5th percentile envelopes describe run
  heterogeneity and are not confidence intervals.
- No confirmatory contrast, endpoint, non-inferiority margin, test, multiplicity
  family, simulation run, or exclusion rule changed.

Interpretation: both additions are secondary/exploratory aids for explaining
multi-objective trade-offs and censoring. They must not be presented as
preregistered confirmatory hypotheses or as a new composite ranking.
