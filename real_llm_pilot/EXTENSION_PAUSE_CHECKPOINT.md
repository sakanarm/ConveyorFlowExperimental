# Real-LLM Extension Pause Checkpoint

- Paused at: `2026-09-28T12:07:39+07:00`
- Reason: user-requested pause.
- Active provider processes after pause: `0`.
- Valid completed extension summaries: `14/30`.
- Historical infrastructure-invalid attempts: `1` (the documented Windows path-length attempt; not a research result).

## Completed conditions and seeds

- `HET_NO_STANDDOWN`: seeds `3000-3009` complete (`10/10`).
- `HOM_GLM_GENERALIST`: seeds `3000-3003` complete (`4/10`).
- `HOM_GPT_PROFILE`: no seeds started (`0/10`).

## Interrupted seed

`HOM_GLM_GENERALIST / CF_FIT__s3004` was interrupted before `summary.json` was created. Its partial attempts are retained for provenance but must not be counted as research results. On resume, seed `3004` must be rerun from the beginning under a new timestamped execution directory with the unchanged frozen config, cases, validators, model mapping, and analysis plan.

## Resume rule

Resume `HOM_GLM_GENERALIST` with `--seed-from 3004`, then run all ten frozen seeds for `HOM_GPT_PROFILE`. Aggregation must accept only directories containing a validated `summary.json`, require exactly ten completed summaries per extension condition, and continue to reject the interrupted partial directory.

No completed result was deleted or modified at pause time.
