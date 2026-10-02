# Final MFEC Team Decision Before Main Experiment

## Selected heterogeneous team

| Agent | ML Build | Fix Bug | Operational role |
|---|---:|---:|---|
| `tencent-hy3` | L3 | L1 | ML-advanced / Fix-Bug-basic specialist |
| `gpt-5-mini` | L2 | L3 | ML-intermediate / Fix-Bug-advanced specialist |
| `glm-5.3-flash` | L3 | L3 | Advanced generalist |

This team is heterogeneous in both workload families. It also creates the
capability-fit pattern needed to exercise stand-down: on Fix Bug D1, higher
agents can stand down for Tencent; on ML D1-D2, L3 agents can stand down for
GPT-5 mini; and advanced agents remain available for tasks beyond those gates.

## Homogeneous controls for RQ2

- `H_L3_GENERALIST`: three independent GLM 5.3 Flash agent instances.
- `H_L2_ML`: three independent GPT-5 mini agent instances.

The study does not claim the team contains every ordinal rank on every
workload. It tests heterogeneity of workload-specific capability profiles.

## Why Tencent is L1 on Fix Bug

Tencent passed all D1 probes, four of five D2 probes, and one of five D3 probes
under the common 4,096 completion-token limit. Five responses terminated at the
fixed limit. The rank therefore describes operational ability under the frozen
resource budget, not an unlimited-budget intrinsic intelligence claim. Token
use and latency remain separate resource outcomes.

## Execution status

The model team, allocation engine, and 60 audited case bundles are frozen, but
Main Real-LLM policy execution is blocked until:

1. MFEC provides immutable alias-to-model mapping/effective dates.
2. Input and output token prices are recorded.
Resolved infrastructure item: the reviewed and hashed allocation engine makes
CF-Fit, static round robin, and Central-Fit select the claimant before
execution. The integrated runner calls only the atomic claim winner, validates
the output in an isolated bundle copy, and rejects model-version drift. It now
executes independent claim winners concurrently without a round barrier and
records wall-clock throughput, terminal time, per-agent busy time, utilization,
peak concurrency, token use, and cost. This path has passed offline mock tests;
those tests are not Real-LLM policy results.

Resolved case item: 60 isolated bundles have deterministic validators and a
frozen lock. Adult and Beijing are public-data microtasks. Bugs2Fix tasks are
explicitly labeled executable behavioral surrogates and do not support a
repository-level Java repair claim.

No ConveyorFlow policy result was used during model selection.
