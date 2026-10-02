# ConveyorFlow Real LLM Pilot

This folder contains a reproducible, vendor-neutral pilot scaffold. It does not
contain Real-LLM performance results. The current simulation evidence must not be
described as a benchmark of any named model or provider.

## What is ready

1. `PROTOCOL_TH.md` fixes the scientific objective, model-selection rule,
   capability gate, outcomes, and analysis boundary.
2. `build_cases.py` selects a deterministic 60-case manifest from the frozen
   public-data-derived task specifications.
3. `run_pilot.py --dry-run` validates the team configuration and case manifest,
   then writes every unresolved research blocker to `dry_run_manifest.json`.
4. `adapter_contract.py` defines the response fields that a provider adapter must
   return so latency, tokens, price, model version, and raw-output hashes are
   auditable.
5. `CALIBRATION_PROTOCOL.md` predeclares the held-out Ability Rank gate, and
   `build_calibration_probes.py` creates 30 deterministic ML Build/Fix Bug
   probes that remain separate from the allocation-policy cases.
6. `config.mfec_candidate.json` and `run_mfec_calibration.py` provide the MFEC
   three-model candidate calibration. API keys are read from
   `MFEC_LITELLM_API_KEY` and are never written to the output ledger.
7. `allocation_engine.py` implements the frozen pre-execution policy decision for
   CF-Fit, static round robin, and Central-Fit. It records an append-only event
   ledger and only permits the atomic claim winner to be executed. The engine
   test suite covers fit selection, temporary stand-down, aging, collisions,
   retries, deterministic dead-letter handling, and exact event hashes.
8. The integrated execution path invokes only the atomic claim winner,
   validates output in an isolated copy of the task bundle, rejects provider
   model-version drift, and writes per-run event and call ledgers. Provider
   calls run concurrently up to the team size without a round barrier: an
   agent that finishes can return to the belt while teammates remain busy.
9. All 60 public-data case bundles are materialized, audited, and frozen. Adult
   and Beijing use deterministic public-row microtasks. Bugs2Fix cases are
   explicitly bounded executable behavioral surrogates, not repository-level
   Java repair claims.
10. The runner reports measured wall-clock throughput, task completion and
    terminal-flow P95, cost per verified task, per-agent busy time, productive
    utilization, and peak concurrent executions. Mock concurrency tests are
    infrastructure evidence only and have `research_results=false`.

## What remains before execution

- Replace every `FILL_BEFORE_EXECUTION` field in `config.template.json`.
- Pin the exact API model versions and account-specific prices. The MFEC adapter
  is implemented and tested, but execution remains blocked until its returned
  version identity can be matched to immutable provider metadata.
- Freeze the completed configuration, case bundles, validators, and prices before
  observing policy comparisons.
- Keep the frozen allocation-engine SHA-256 unchanged. Any engine change
  requires a new lock, complete tests, and pre-experiment review.

## Commands

```powershell
python v2/real_llm_pilot/build_cases.py
python v2/real_llm_pilot/run_pilot.py --dry-run
python v2/real_llm_pilot/build_calibration_probes.py
python -m pytest v2/tests/test_real_llm_allocation_engine.py -q
python v2/real_llm_pilot/audit_allocation_engine.py
python v2/real_llm_pilot/audit_case_bundles.py
python v2/real_llm_pilot/audit_concurrent_runner.py
python v2/real_llm_pilot/probe_mfec_metadata.py
```

On Windows, run `run_mfec_calibration.ps1` to enter the API key through a
hidden-input prompt and execute the 90-call calibration. The generated rank is
provisional until MFEC supplies the immutable alias mapping and effective
pricing metadata.

## Current MFEC team decision

Ability calibration and the predeclared candidate stopping rule selected:

- `tencent-hy3`: ML Build L3 / Fix Bug L1
- `gpt-5-mini`: ML Build L2 / Fix Bug L3
- `glm-5.3-flash`: ML Build L3 / Fix Bug L3

See `ABILITY_CALIBRATION_RESULTS_TH.md`, `FINAL_TEAM_DECISION.md`, and
`final_team_evidence.json`. The model team is frozen, but the Main Real-LLM
policy experiment remains blocked only on immutable alias mapping and account-
specific token prices. The allocation-engine and bundle audits use mock/oracle
checks and are not Real-LLM performance evidence.
Calibration and candidate screening must not be reported as ConveyorFlow
policy outcomes.

The dry run writes `dry_run_manifest.json` with `research_results=false`, a
`blocked_not_executed` or `ready_not_executed` status, and a structured blocker
list. A dry run is an infrastructure check, not empirical evidence. Real
execution remains unavailable until every preflight blocker is resolved; when
enabled, the runner uses the frozen allocation engine rather than the invalid
all-models-by-all-cases loop.
