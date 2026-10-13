# Reproducing ConveyorFlow v2.3

This extension studies decentralized self-selection, capability heterogeneity, and capability–task fit with soft stand-down. Tasks remain on a dependency-ready conveyor belt. Policies are experimental controls, not the primary contribution. The research questions concern trade-offs, not superiority on every metric.

## Code and contract checks

Use Python 3.10+ and install the dependencies declared in this repository. From the checkout root:

```powershell
python -m pytest tests -q
./REPRODUCE_V2_3.ps1 -Stage CodeCheck
```

On 6 October 2026, the explicitly scoped local suite passed 217 pytest tests (185 unittest cases plus 32 pytest-style tests). A clean public Git-index export passed 213 tests and explicitly skipped four integration checks that require public-data/reference preparation or the separately fetched BugsInPy reference patch. The integrated-backend and ML-finalizer guards passed in both runs. Skipped checks are not reported as passed. Fixture guard checks remain active without the gold patch. Tests do not constitute live-LLM results. `pytest.ini` limits default collection to trusted `tests/`; never collect candidate or benchmark source trees on the host. `Check` additionally audits *locally available* historical result capsules and may require investigator artifacts that are deliberately not committed. Do not infer that missing historical raw ledgers were regenerated.

Fixtures can be rerun into **new** destinations. Never overwrite a frozen run:

```powershell
./REPRODUCE_V2_3.ps1 -Stage EcologicalDryRun -OutputPath major_revision_v2_3/ecological_v1/reviewer_dry_01
./REPRODUCE_V2_3.ps1 -Stage EcologicalDecisionCheck -OutputPath major_revision_v2_3/ecological_v1/reviewer_decision_01.json
./REPRODUCE_V2_3.ps1 -Stage EcologicalClaimCheck -OutputPath major_revision_v2_3/ecological_v1/reviewer_claim_01
./REPRODUCE_V2_3.ps1 -Stage EcologicalIntegrationCheck -OutputPath major_revision_v2_3/ecological_v1/reviewer_integration_01
```

The separate-process decision check and SQLite claim check use trusted code. They test parity and ownership invariants, not LLM throughput, distributed fault tolerance, or network latency.

The integrated fixture check connects actual agent/coordinator choice processes, shared CAS, concurrent trusted fixture executors, predecessor artifact digests and verifier completion. CF computes its proposal in its claimant process; the rule-matched coordinator computes the same pure function centrally. Static ownership is fixed before execution. Hash-chain ledgers retain failures and unknown outcomes. There is no paid launch route in this fixture backend: its ranks, 100 ms clock and 20 ms backoff unit are diagnostic settings, not calibrated main-experiment parameters. Active work exceeding the fixture horizon leaves incomplete evidence rather than being promoted to a passed run. Live assessor/executor/container-verifier adapters and late-return billing rules remain integration gates.

## Live execution and security

The evaluator executes generated Python, patches, and serialized models only inside Linux containers. Network is disabled for candidate execution; hidden labels, quality gates, reference predictions, fixed repository trees/history, API credentials, and the claim database must not be mounted into candidate containers. Never execute candidate Python or deserialize candidate joblib on the host.

The investigator used WSL Ubuntu with Podman; `Dockerfile.ml_eval` and the image-lock/build utilities record the ML runtime. Repository builds use explicit BugsInPy commits, Python/package/build profiles and buggy-fail/fixed-pass qualification. A rebuild creates a new image identity: retain it in a new execution capsule rather than changing a historical lock. Fetch external benchmarks and public source datasets using the existing preparation/download utilities. Source availability does not imply identical future provider responses.

`MFEC_LITELLM_API_KEY` is a **process environment variable**. Supply your own credential; no key is committed. Provider deployment aliases and returned exact versions are checked against the frozen configuration. The WSL bridge reads the key from stdin, not arguments or a file, and does not pass it to candidate containers. Execution stages require `-ConfirmPaidRun`.

```powershell
./REPRODUCE_V2_3.ps1 -Stage EcologicalMLCalibrationAudit
./REPRODUCE_V2_3.ps1 -Stage EcologicalRepositoryCalibrationAudit
```

The above is read-only and makes no API calls. `EcologicalMLCalibrationFreeze` and `EcologicalMLCalibrationExecute` refer to the investigator's immutable first-attempt batch. Existing output evidence causes a restart to be rejected. `EcologicalMLContinuationFreeze/Execute` are a separately recorded recovery of **never-started pairs only**, not general retry commands. A reviewer should use a fresh checkout/output capsule and record a new date, image/model identities and locks, not pretend to recreate historical hashes.

`EcologicalMLContinuation2Freeze/Execute` preserves all previously started pairs and requires the recorded trusted backend-health gate. A cleaned workload timeout stays unresolved; another trusted health probe precedes further never-started calls. Launch/auth/mapping/hash failures still stop execution. `EcologicalRepositoryCalibrationFreeze/Execute` uses six different environment-qualified cases, one call per deployment, guarded exact edits, ten case-specific public regression identities, and fresh replay. Existing paid evidence is not overwritten. These commands address the dated investigator capsule; a clean reviewer checkout without that capsule cannot audit historical raw outcomes merely because a lock file is present.

Before repository model calls, two instrument amendments were recorded: pinned pandas/pytz activated two previously skipped Matplotlib regressions without replacing test identities, and public formatter-method excerpts completed one missing context. Original failed/incomplete instrument evidence is retained. Neither amendment is a model observation or a reference repair.

After all 18 repository pairs and their ledger appends finish, seal an aggregate report into a **new** directory:

```powershell
./REPRODUCE_V2_3.ps1 -Stage EcologicalRepositoryCalibrationFinalize -OutputPath major_revision_v2_3/results/ecological_repository_calibration_v1_final
```

This command rejects incomplete batches and existing destinations. It checks the final controller marker and evidence identity, retains unresolved outcomes, and records analysis/evidence hashes. It makes no API calls, executes no candidate code, and assigns no Ability Ranks. Per-repository cells contain only two cases per deployment; nominal Wilson intervals do not account for repository dependence and are not population-wide confidence statements.

`EcologicalMLCalibrationFinalize` likewise requires all 288 ML pairs, no active/pending pairs, final ledger agreement and a complete continuation controller. It reports deployment × corpus × stage operational rates, failures, unknown-outcome bounds and nominal Wilson references, not full pipelines, general-population intervals, Ability Ranks or D1–D3 coefficients. `ecological_v1/watch_ml_completion_v1.py` can wait for the existing controller and invoke this read-only finalizer. The watcher never issues/retries provider calls or changes Office/Git files; a stopped controller produces no final capsule. Its source/analysis/lock hashes are checked while waiting.

## Evidence boundaries

- The completed isolated-stage pilot has 36 case–stage–deployment pairs: 28 verified, 6 contract/execution failures, and 2 unresolved provider outcomes. All pairs use trusted predecessors. This is not 36 full pipelines or held-out ability calibration.
- The completed localized-repair pilot has 18 case–deployment pairs from six cases in three repositories: 7 verified. Public regression tests are withheld from candidates, not novel hidden tests. Environment exclusions, explicit localization, failures and unresolved billing remain disclosed.
- New ecological calibration started on 6 October 2026. The frozen ML population has 24 task specifications, four stages, and three deployments: 288 first-attempt requests. It reuses two source corpora and row splits; it is a task-specification holdout, not 24 independent datasets or a raw-data holdout. ML calibration is still running. Repository calibration used a separate outcome-blind environment pool and completed all 18 pairs: 8 verified, 8 model failures and 2 unresolved provider outcomes. The aggregate capsule is in `public_results/v2_3/ecological_repository_calibration_v1/`; raw candidate/provider artifacts remain investigator-held. Do not pool it with the earlier 18-pair repair pilot.
- Main live allocation comparison is not complete. `CENTRAL_RULE_MATCHED` moves the same choice computation to one coordinator; the older Central-Matched experiment only relayed bids. Do not merge these estimands. The shared belt/claim store remains a failure dependency.
- Original simulation probabilities are scenario assumptions. These pilot observations do not retroactively turn them into empirical estimates or provide a difficulty-specific probability curve. Ability ranks must come from calibration with uncertainty, not vendor, price or release date.

Detailed protocols, deviations and results are in `major_revision_v2_3/*.md` and `major_revision_v2_3/ecological_v1/*.md`. `STATUS_TH.md` is a dated progress record. API keys, provider response text, heavy data/model/candidate trees and Office drafts are intentionally excluded from Git. Diagram sources remain editable in `ConveyorFlow_diagrams_en_working.drawio`.
