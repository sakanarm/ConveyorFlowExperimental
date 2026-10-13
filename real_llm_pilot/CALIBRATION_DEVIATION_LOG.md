# Ability Calibration Deviation Log

## CD-001 — Fix Bug oracle replacement after instrument pilot

- Status: disclosed instrument correction before allocation-policy execution.
- Trigger: the first 90-call calibration completed with no API errors and a
  93.3% ML Build pass rate for every model, but normalized exact-match repair
  passed only 0/15, 1/15, and 1/15 Fix Bug cases.
- Diagnosis: the CodeXGLUE normalized-function pairs do not include executable
  repositories or tests. Exact textual agreement can reject a semantically
  correct alternative repair and therefore is not a valid primary ability
  oracle for this study.
- Correction: retain the first exact-match result as an instrument-pilot
  secondary observation. Replace the primary Fix Bug calibration with 15
  reproducible functions having hidden executable tests, AST safety checks,
  restricted builtins, isolated Python execution, and a three-second timeout.
- Ability aggregation correction: report `A[i,w]` separately for ML Build and
  Fix Bug. Do not pool the two workload families into one rank.
- Bias boundary: aggregate pilot results were observed before this correction,
  so calibration v2 is labeled an instrument-correction study. No ConveyorFlow
  allocation-policy result was observed or used to design the new probes.

## CD-002 — Unintended output-token cap in executable calibration

- Trigger: 21/45 executable-calibration responses ended with
  `finish_reason=length`; 17 of those produced syntactically truncated code.
- Cause: the shared adapter unintentionally capped `max_tokens` at 1,024 even
  though the frozen configuration specified 4,096. The models' hidden reasoning
  consumed much of the completion budget.
- Correction: remove the adapter cap and rerun only calls whose original
  `finish_reason` was `length`, using the originally frozen 4,096-token setting.
  Preserve both original and retry ledgers and select the retry only for the
  affected model-probe cell.
- Static-safety correction: permit `dict.fromkeys`, a deterministic operation
  over an in-memory dictionary. Revalidate non-truncated responses without an
  additional API call.
- Claim boundary: corrected results must cite both ledgers and this deviation;
  the original truncated outcomes must not be interpreted as model failures.

## CD-003 — Safe-parser false rejections

- Trigger: five complete responses were rejected because the parser did not
  recognize a `python` code fence, rejected an ordinary `_` loop variable, or
  disallowed safe one-argument `type`/`isinstance` checks.
- Correction: recognize Python fences; reject only double-underscore names and
  attributes; permit `type(x)` and `isinstance(x, ...)` under restricted
  builtins. Preserve bans on imports, file/network access, dynamic execution,
  unsafe attributes, and unbounded worker execution.
- Execution: revalidate saved responses offline. No API call is repeated for
  this parser correction.

## CD-004 — Safe in-memory exception handling

- Trigger: one complete GLM response used `try/except TypeError` while removing
  duplicates, but the sandbox initially rejected all `try` statements.
- Correction: allow exception handling while retaining bans on imports,
  file/network access, dynamic execution, unsafe attributes, and explicit
  raising. Expose only `TypeError` and `ValueError` in restricted builtins.
- Execution: revalidate saved responses offline; no API call is repeated.
