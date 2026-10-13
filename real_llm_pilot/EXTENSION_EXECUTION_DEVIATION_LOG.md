# Real LLM Extension Execution Deviation Log

## 28 September 2026 Windows validator path failure

The first attempt of `HET_NO_STANDDOWN`, seed 3000, completed one provider call and wrote the candidate for `RLLM008`, but Windows refused to start the deterministic validator because the validator working directory exceeded the process working-directory path limit. The runner stopped before producing a policy summary. The attempt is marked `invalid_infrastructure_failure` and is excluded from all research outcomes.

The candidate itself failed when the same frozen validator was invoked manually through a short temporary drive path. That manual diagnostic result is not entered into the event ledger because the interrupted policy run did not complete its auditable execution path.

### Corrective action

The PowerShell wrapper now maps `v2/real_llm_pilot` to an unused temporary drive letter with `subst` for the duration of execution. The Python runner, allocation engine, cases, prompts, deterministic validators, model deployment hashes, ability profiles, seeds, policy parameters, generation settings, retry rules, metrics, contrasts, and statistical analysis remain unchanged. The mapping is removed in `finally`, and credentials are still cleared from the process environment.

This is an execution-path correction, not an outcome-driven design change. Seed 3000 may be rerun under the preregistered infrastructure-failure rule. The invalid original attempt and candidate are retained for audit.

- Pre-failure wrapper SHA-256: `aa72e5295417982ee939c456cd83e8ec909944f72bc6b5111953fae1f18cad79`
- Corrected wrapper SHA-256 after adding a visible resume-window title: `eb3d3b40e8f4c07c537a1f1bbd07c0571ad355de829290d95b03d51fac6e945d`
- Post-correction short-path preflight: `ready_not_executed`, blockers = 0
