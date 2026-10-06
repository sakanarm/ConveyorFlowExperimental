# ConveyorFlow v2.3 major-revision workstream

This folder is **not** a completed paper result. It separates (1) matched-decision-locus simulation, (2) ecological ML/repository harness preparation, and (3) bounded real-LLM feasibility. Read `STATUS_TH.md` for the current gate status and `../AJSTR Journal/AJSTR_v2_3_MAJOR_REVISION_PROTOCOL_TH.md` for the preregistered design.

`../AJSTR Journal/AJSTR_v2_3_EVIDENCE_INSERT_DRAFT_EN.md` retains the earlier working insert. Audited v2.3 Word content is staged under `../AJSTR Journal/v2_3_word_work`; new Word manuscripts are separate from v2.2 and are not submission-ready until the missing ecological main results pass review.

The v2-style PowerShell entry point is `../REPRODUCE_V2_3.ps1`. Its default `-Stage Check` runs offline tests and read-only evidence verification; it does not call MFEC. `RUN_MATRIX_V2_3_TH.md` maps every Major Revision gate to its required run, pass condition, and safe restart rule. Live main ecological experiments are not yet enabled.

## Reproduce checks without an API key

From `v2`'s parent workspace:

```powershell
python -m unittest discover -s v2/tests -p 'test_*.py'
python v2/major_revision_v2_3/audit_ml_dag_pilots.py
python v2/major_revision_v2_3/audit_ml_dag_pilot_v3.py
python v2/major_revision_v2_3/verify_podman_lock.py
```

These commands are offline integrity checks. They do not call MFEC or execute generated code. The audits explicitly mark pilot counts as **not probability calibration**.

## Bounded container-only feasibility

The earlier feasibility runner supports a locked Docker evaluator, or the separately certified Podman evaluator through explicit runtime and image-lock environment settings. The third-revision runner uses the frozen Podman protocol and stdin credential bridge. Both check the evaluator before a billable provider call, and generated Python executes only inside a networkless read-only container. Do not paste the API key into a command, file, issue, or repository.

The completed third-revision batch is inspected without paid reruns:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage PilotV3Audit
& 'v2/REPRODUCE_V2_3.ps1' -Stage BugsPreflightStatus
```

The initial `ADULT_P0` and `BEIJING_P0` calls are preserved in `candidate_workspaces`; both failed at preprocessing. The revised prompt is identified by `prompt_revision` and hashes. See `FEASIBILITY_DEVIATIONS_TH.md`. Do not combine prompt revisions as one confirmatory sample.

## Evidence boundary

- `MATCHED_ARCHITECTURE_RESULTS_TH.md` is simulation evidence under assumed parameters; it is not measured MFEC outage/latency.
- `OVERHEAD_PROXY_RESULTS_TH.md` reports 1,000 paired **single-host serial IPC** measurements of a direct claim versus one additional coordinator relay. The frozen CSV/manifest pass `verify_overhead_proxy_v1.py`. This is not MFEC/provider latency, a concurrent-load result, or real-outage evidence, and it is not yet an E1 main-experiment distribution.
- The separate `measure_overhead_load_v1.py` freezes 1/2/4/8-client sessions (24 sessions, 18,000 measured requests), with both routes sharing the same claim-store design and central adding one serial relay. `verify_overhead_load_v1.py` verifies its frozen artifacts. These are local load-sensitivity measurements, not provider/network evidence or proof of real-system throughput.
- `EMPIRICAL_PROBABILITY_PROTOCOL_TH.md` describes the held-out, isolated-stage and full-job data needed before a real-model probability can replace Equation (7)'s assumed curve.
- `results/ml_dag_feasibility_audit_v3_20261005.json` audits eight earlier pilots and distinguishes two Docker launch failures from model failures. `results/ml_dag_pilot_v3_audit_20261005.json` audits the separate six-job, 20-request third-revision batch: one complete pipeline, three candidate dead letters and two unresolved jobs. Do not pool revisions or estimate ecological ranks from these conditional samples.
- `ml_eval_image_lock_podman_v1.json` certifies the alternative Podman evaluator after all eight trusted four-stage references passed. `verify_podman_lock.py` verifies its stored reports, source and artifact hashes without a key or daemon. See `PODMAN_RUNTIME_RECOVERY_TH.md` for backend deviations.
- Tencent ADULT_P0 passed the four-stage frozen ML feasibility contract with hidden ROC-AUC 0.927089 on 16,281 test rows. `replay_verified_ml_pilot_v3.py` clean-replayed its unchanged source and reproduced the prediction/model hashes without new provider calls. This is one observed pipeline, not a policy comparison or an extra independent job.
- The auditable combined v6 prefix has seven evaluated candidates: six reproducible cases across pandas, matplotlib and luigi, and one preserved thefuck environment exclusion. The four pandas cases are carried by provenance reference, not re-counted as new executions. Luigi adds the historically pinned nose dependency; matplotlib's serial `-j 1` build reproduces the contrast where parallel builds failed. Original source/commits/tests remain unchanged and all prior failures are retained.
- `build_bugsinpy_candidate_v1.py` creates separate gold-free final candidate and verifier images through multi-stage builds. Ten hash-selected regression items per case are frozen before their outcomes. `audit_repository_baselines_v2.py` reports 58 active passes and two historical expected failures, corrects accounting without replacing tests and preserves the original v1 failed summary. Withheld public repository tests are not novel independent hidden tests.
- `run_repository_identity_smoke_v1.py` checks the patch evaluator with no-op diffs, not repairs. The bounded MFEC runner `run_repository_repair_pilot_v1.py` allows six bugs × three aliases, at most two attempts/job or 36 calls. Source is never manually repaired; provider errors stop unresolved without automatic paid retries. Preflight is not evidence of successful LLM repair.
- New v2.3 drafts may report completed extensions with their limitations. They must not claim that missing ecological calibration, multi-repository LLM repairs or paired live-policy main runs have passed. v2.2 results remain unchanged.
