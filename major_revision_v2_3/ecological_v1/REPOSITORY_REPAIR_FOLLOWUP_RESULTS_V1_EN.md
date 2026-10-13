# Supplemental real-LLM repository-repair follow-up (v2.3)

Status: completed and independently audited on 9 October 2026. This is a post-main feasibility experiment, not a ConveyorFlow allocation-policy comparison. The raw pair records, four verification reports for each verified patch, frozen prompts, append-only ledgers, and batch markers are under `major_revision_v2_3/candidate_workspaces/ecological_repair_followup_live_v1/`. The frozen paid instrument is `ecological_v1/repository_repair_followup_execution_lock_v1.json` (SHA-256 `1f803b97209eb47525e4e33d55afc3c976f4a05457fc82f327652af9eb6a50e6`). The independent aggregate is `results/ecological_repair_followup_audit_v1/audit.json` (SHA-256 `492e57cafd08e490ea331f38f62e4dfa43d61ae452767a159f70bc48fcced04a`).

## Why this experiment was run

The original six-block real-LLM allocation experiment used a strict unified-diff output contract and produced no verified repository repairs for CF-Fit or Central-Fit. That result should not be reinterpreted as proof that the models cannot repair repositories. We therefore tested whether a separately calibrated, deterministic exact-edits interface could produce verified patches on *unused* BugsInPy holdouts. This tests repair feasibility under a new artifact interface; it does not re-estimate the effect of decentralized self-selection or replace the original allocation result.

## Frozen workflow and denominator

Six holdouts were prespecified in order: `luigi_11`, `matplotlib_6`, `pandas_127`, `luigi_16`, `matplotlib_26`, `pandas_74`. Container-only environment qualification passed for all six. Candidate/verifier images were built without gold patches; the visible bug test had to fail, the historical fixed version had to pass, and ten hash-selected public regression nodes had to be active and pass in both buggy and fixed environments. `matplotlib_26` had one selected node skipped in both environments, leaving nine active passes. It was excluded **before any model call** without replacing the test or case. Five cases passed source-import and context-identity gates.

Each of three frozen MFEC deployments received the same gold-free prompt for each eligible case, with localized buggy source and the visible public test. The model had to return one JSON object of exact `before`/`after` edits to allowed production files. The adapter converted valid edits to a guarded patch without semantic changes. There was one call per model–case pair (`temperature=0`, maximum 32,768 output tokens, 720-second provider timeout), no retry after a request-start marker, and a ceiling of 15 calls. Tests ran in disposable, network-disabled Linux Podman containers, not on Windows. `VERIFIED` required a passing visible bug test, all ten selected public regressions, and fresh-container replay of both sets. These are public withheld regressions, not novel hidden tests.

## Audited observations

The batch completed 15 of 15 started calls, with no mapping/instrument circuit stop. The independently checked status counts were seven `VERIFIED`, four `VISIBLE_TEST_FAILED`, and four `UNFINISHED_OR_EMPTY_OUTPUT`.

| MFEC deployment | Verified | Visible-test failed | Unfinished/empty | Total |
|---|---:|---:|---:|---:|
| `tencent-hy3` | 5 | 0 | 0 | 5 |
| `gpt-5-mini` | 1 | 4 | 0 | 5 |
| `glm-5.3-flash` | 1 | 0 | 4 | 5 |
| **All** | **7** | **4** | **4** | **15** |

By repository, verified patches were 3/6 Luigi pairs, 1/3 Matplotlib pairs, and 3/6 Pandas pairs. The four unfinished/empty responses all came from `glm-5.3-flash`; each provider record reports `finish_reason=length` and 32,768 output tokens, but the returned content was empty. We cannot infer the exact internal token allocation from this metadata. Gateway-reported input/output tokens total 166,363/246,358 across the 15 calls; these are not allocator cost estimates, and the gateway cost currency is unverified.

The audit checked every request marker against the paid lock, every response and patch hash, the exact model deployment identifier, all append-only ledger rows, and all four JUnit/verifier artifacts for each `VERIFIED` pair. Seven verified patches therefore establish *conditional repair feasibility* on these five qualified public holdouts. They do not establish general repository-repair reliability, success on the excluded sixth case, repair of unseen repositories, or a CF-Fit advantage over Central-Fit. A new paired allocation experiment with the same exact-edits contract in every arm would be required for the last claim.

## Interpretation for the manuscripts

Report the original strict-diff allocation result unchanged. Present this follow-up as a separately labelled feasibility/limitation analysis, including the 1/6 pre-provider exclusion and the full 15-pair denominator. Do not pool it with the main six-block CF-Fit/Central-Fit/Static result or use its model-specific outcomes as an ability-rank calibration after seeing holdout results. The decision-locus causal gap remains open: the current paired simulation and real-LLM arms do not fully isolate decentralization from all other allocation mechanics.
