# Real-LLM Extension Timing-Validity Note

Date: 2026-09-29 (Asia/Bangkok)

## Scope

The Real-LLM extension contains 30 validated extension runs: 10 runs for
`HET_NO_STANDDOWN`, 10 for `HOM_GLM_GENERALIST`, and 10 for
`HOM_GPT_PROFILE`.  The 10 `HET_FULL` runs are the frozen main-experiment
reference condition.

All 30 extension runs remain in the primary completion and cost analyses.
The timing-validity rule is endpoint-specific and therefore does not remove a
run from completion rate, total cost, or cost per verified task.

## Timing exclusions

Three extension runs exceeded the preregistered non-provider-gap threshold and
are excluded only from wall-clock time, throughput, utilization, and other
timing-derived summaries:

| Condition | Seed | Run ID | Maximum non-provider gap | Timing status |
|---|---:|---|---:|---|
| `HOM_GLM_GENERALIST` | 3003 | `CF_FIT__s3003` | 180.826 s | excluded from timing endpoints |
| `HOM_GLM_GENERALIST` | 3007 | `CF_FIT__s3007` | 14,670.670 s | excluded from timing endpoints |
| `HOM_GPT_PROFILE` | 3007 | `CF_FIT__s3007` | 180.575 s | excluded from timing endpoints |

Consequently, the timing-valid sample sizes are 10/10/8/9 for `HET_FULL`,
`HET_NO_STANDDOWN`, `HOM_GLM_GENERALIST`, and `HOM_GPT_PROFILE`, respectively.
The extension timing contrasts are reported as exploratory cross-window
evidence and must not be described as confirmatory causal effects.

## Execution incidents not analyzed as research runs

- One path-length failure occurred before a valid research run was produced;
  it is an infrastructure-invalid attempt and is excluded from all analyses.
- A user-requested pause left one partial `HOM_GLM_GENERALIST` seed-3004
  directory without a completed summary.  The completed resumed run is the
  analyzed run; the partial directory is retained for auditability and is not
  counted as an additional replicate.

No completed run was rerun merely to improve an observed result.

## Post-execution visualization change

After data collection, `create_real_llm_figures.py` was changed only to select
a headless rendering backend and improve label/layout readability.  The input
tables, metric definitions, min-max normalization, inferential procedures, and
reported numerical results were unchanged.  The frozen pre-execution lock is
therefore retained as the historical protocol record rather than silently
rewritten.
