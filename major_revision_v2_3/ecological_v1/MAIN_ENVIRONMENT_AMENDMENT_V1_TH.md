# v2.3 main environment amendment (7 October 2026)

This is an instrument/eligibility amendment **after** the original repository
preflight and **before** any repository-repair main-model call. It is not a
retrospective model-performance adjustment. The original preflight ledger and
its four Matplotlib exclusions remain unchanged and auditable.

## Repository environment

The frozen 12-case pool required two reproducible cases from each of Luigi,
Pandas, and Matplotlib. The original preflight qualified Luigi 2/2 and Pandas
2/2, but all four Matplotlib candidates stopped during pytest collection in
both buggy and fixed revisions. The common observed error was a Python 3.8
`DeprecationWarning` for an invalid escape sequence in legacy Matplotlib
source, promoted to a collection error. This did not measure the relevant bug.

Before amending the protocol, an offline diagnostic on the first frozen
Matplotlib case (`matplotlib_1`) showed that the narrowly scoped pytest option
`-W ignore::DeprecationWarning` allowed the relevant test to run: buggy failed
and fixed passed. The diagnostic case and outcome were therefore known before
the amendment and must be disclosed. We then froze one amendment for **all
four** original Matplotlib candidates in the original order, with the same
existing validator images, test selectors, resource limits, network isolation,
and no LLM calls. The sole change was the warning filter. All four were run,
even after the first two qualified. All four met the buggy-fail/fixed-pass
criterion. The predeclared first-two rule selects `matplotlib_1` and
`matplotlib_28`; `matplotlib_6` and `matplotlib_26` remain in the ledger, not
silently discarded.

The combined repository qualification is Luigi 2, Pandas 2, Matplotlib 2.
This is **environment eligibility only**. It says nothing about LLM repair
success and is not a paired allocation result. Commands:

```text
python ecological_v1/amend_matplotlib_preflight_v1.py --freeze
CONVEYORFLOW_CONTAINER_COMMAND=podman python3 ecological_v1/amend_matplotlib_preflight_v1.py --execute
python ecological_v1/amend_matplotlib_preflight_v1.py --audit
python ecological_v1/audit_main_repository_qualification_v1.py
```

The original ledger SHA-256 is
`16446c0e0e835bb18b886d32b4f12605fefc1b4ef91c03d616d002de9e53cd87`;
the amendment ledger SHA-256 is
`5d7867eca906bfa9b7ff975fa4138e0d88c5d2950f9d7fe845eb754868c802f6`.
These are distinct capsules. The amendment is not a preregistration made
before inspecting any Matplotlib environment outcome.

## Real-LLM adapter instrument

Technical sentinel v1 used the exposed calibration case `CAL_ADULT_01` and
one `tencent-hy3` call, not any main case. Its generated ingest source passed
the first locked container gate, but a fresh replay of the same source failed
to open `/submission/ingest_validate.py` with `[Errno 5] Input/output error`.
The same source hashes on both copies. A read-only Podman diagnostic reproduced
the I/O error from the long C-path bind mount; a short D-path copy with the
same SHA-256 was readable, and an offline container execution on D completed.
This is recorded as an instrument failure, not as evidence that the LLM could
not implement ingest. V1 remains stopped with one provider call and no retry.

Technical sentinel v2 is a separately frozen run on short D-backed candidate
workspaces. It uses the same public calibration case, model mapping, generation
bounds, locked offline evaluator, fresh replay, and same-arm provenance.
`run_main_adapter_sentinel_v2.py` explicitly restricts the unchanged verifier
module's workspace guard to the frozen D root **only in that process**; it does
not modify the old verifier source or v1 evidence. V2 is technical only: even
if all four stages verify, it is not a paper allocation observation. A separate
paired main execution lock and audited live allocator are still required.

V2 then verified generated ingest and preprocess, and made a third provider
call for train. The train source and artifact passed the first-stage verifier,
but the calibration compatibility helper tried to create the same
`compatibility_main_first_attempt` directory already used by preprocess.
The run stopped with `FileExistsError` before writing a train gate summary.
This is another instrument defect, not a failed model result. The v2 summary
and three request records remain intact. On a separate diagnostic clone, a
stage-scoped verifier checked that existing train artifact successfully:
ROC AUC 0.90857 versus the frozen 0.69383 floor. This diagnostic is not a
new model observation or an allocation result.

V3 freezes a distinct technical run with the sole additional verifier change
`compatibility_<label>_<stage>`, applied to both preprocess and train. The
calibration helper source is not rewritten; the stage-scoped function is
injected only in the v3 technical process and its hash is included in the
v3 lock. V1/v2 failures are retained. Repeating this exposed calibration case
is exclusively for instrument validation; it must not be used to improve an
estimated ability rank or select a favorable main outcome. A legitimate v3
candidate quality failure, if observed, must be reported and not retried
until it passes.

V3 completed all four generated stages on `CAL_ADULT_01` with one provider
call per stage. Ingest, preprocess, train, and package each passed both the
first locked verifier and a fresh replay; same-run/same-arm predecessor
origin checks passed. `audit_main_adapter_sentinel_v3.py` independently
verified the source/response/gate/artifact hashes, stage-scoped compatibility
reports, and predecessor chain. Its summary SHA-256 is
`4dd21844739dbc3b64080d25b2088c192c1d4a1434bf6cf8b0259e3748d49e74`.
Across v1/v2/v3 there were 1+3+4=8 technical provider calls; none belongs to
the ecological allocation-main denominator. A passing sentinel validates this
one integration route, not all agents, cases, policy arms, provider reliability,
or the proposed RQ1/RQ2 claims.

All 12 frozen main ML inputs were also audited case by case for source hashes,
public/hidden separation, schemas, row counts, and preparation-script identity.
The repository environment gate now has six selected cases (two per project).
Before paid paired main, the remaining work is: gold-free repository contexts
and verifier audit, a real paired live allocator with decision-locus/claim/
failure/late-return accounting, then a frozen arrival/arm-order/limits/analysis
lock. Merely creating a lock file is not sufficient.

## Later technical allocator and repository-preparation record (7 October 2026)

The preceding paragraph describes the state **before** this later work. It
must not be read as the current readiness result. The live allocator
`live_allocator_core_v1.py` first failed an offline fixture because the
observation clock started before SQLite initialization on the D-backed mount.
The failed fixture directory was retained. The clock was then anchored after
store creation; a separate fixture completed all five policy arms, upstream
model failure, unresolved provider outcome, and bounded no-volunteer handling.
These are trusted fixtures, not throughput or cost measurements.

A separately frozen technical paired sentinel then used two **exposed
calibration** ingest cases in each of `CF_FIT`, `CENTRAL_RULE_MATCHED`, and
`STATIC_OWNERS`. The public-only six-bundle lock was audited before any paid
call. Its first launch checked the rootless Podman store, found no evaluator
image, and stopped before a provider call. The exact locked image ID
`d1dd86e9ef7bb249f3468e90214f3ceb3a9e8ff1ed84b0b7e1926458f423a37e`
was verified in the rootful store used by the previous successful sentinel;
the same frozen evaluator and inputs were then run there. The technical run
made exactly six provider requests, with no automatic retry. All six generated
ingest stages passed the locked first verifier and fresh replay. The read-only
`audit_main_allocator_sentinel_v1.py` checked request/model identity, local
versus coordinator decision process, SQLite claim wins, generated source,
artifact provenance, replay, tokens, and provider cost units. The technical
lock SHA-256 is `c375053ee16389628ea29bdb0903693149ee41863a9390d4d0700efe3a8a058a`;
the raw summary SHA-256 is
`c064cab4691ec5e77209e74af119966ff0ae7c5c2d7aeb4960c7e2af765054c5`.
This is **not** a main paired effect estimate: it has only two familiar
calibration jobs, one stage, and a fixed arm order.

For repository main, six selected cases were localized from buggy public
tracebacks and API names, without reading a gold diff. The first image-build
attempt used the Docker default in WSL and stopped with `docker` not found;
no image or LLM observation was made. A first frozen recovery stopped before
building because its output-root override also redirected a lock lookup.
Both failures remain. The second separate recovery required explicit rootful
Podman and a minimum of 8 GiB free on C before each case. It built isolated
candidate/verifier images for Luigi 2, Pandas 2, and Matplotlib 2; candidate
source hashes match the buggy trees and the final candidate images have no
fixed/source/protected/gold roots. The original candidate gate passed five
cases. `matplotlib_28` failed the original all-active rule only because one
of ten selected public regressions was skipped for the same FreeType
environment reason on buggy and fixed; the other nine passed on both. This
failed status remains unchanged.

Before **any repository-repair main LLM call**, a disclosed post-outcome
environment amendment applied one rule to all six preselected cases: visible
buggy failure; identical candidate/fixed regression dispositions; no
regression failures/errors; and at least `min(8, selected_count)` active
passes on both. No test was replaced or rerun. The amended candidate gate
qualifies six cases for context preparation, but `matplotlib_1` has only two
eligible public regressions and `matplotlib_28` has nine active plus one
common skip. This limited coverage and the post-preflight timing of the
amendment must be disclosed in the manuscript, not portrayed as an original
preregistration. The amendment lock SHA-256 is
`531c715ec81a023e05872c421a453407a19ac550bcd3d43b4ca602edf2cb29e2`.

The first main-context extraction stopped on `luigi_3` because the old
extractor assumed the visible method name was unique across all test classes.
The original failure remains. A separate class-qualified selector and bounded
container file transport then prepared all six cases. For each, a no-op patch
reproduced the visible bug and frozen public regression dispositions, while a
trusted import-sentinel mutation caused its unique failure marker, proving
that patched source is actually loaded. The read-only six-case context audit
checks the buggy-source hashes, prompt paths/excerpts, and identity evidence.
Its recovery lock SHA-256 is
`1cc1ef5c3512536c66882c7a25e8a1fcefb635e6bae0fa2e0062c0ec4cafcae9`.
No repository-repair main model call has yet occurred.

The current `check_main_readiness_v1.py` still returns
`ready_to_execute: false`. The outstanding conditions are a frozen paired
main execution lock, an audited full-workload live adapter (the technical
sentinel covers ingest only), and a frozen paired arm order/arrival/limits/
analysis protocol. The six-call technical sentinel and the six repository
contexts must never be copied into the paper's main-results denominator.
