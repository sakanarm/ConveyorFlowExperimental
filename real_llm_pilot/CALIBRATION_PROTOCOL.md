# Held-out Ability Calibration Protocol

## Purpose

This phase assigns provisional Ability Rank L0-L3 to the three MFEC deployment
aliases before any allocation-policy result is observed. Price, latency, model
name, and version number do not determine ability.

## Design

- 30 held-out probes: 15 ML Build and 15 Fix Bug.
- Each workload contains five D1, five D2, and five D3 probes.
- Every model receives every probe once: 90 API calls in total.
- Probe order is seeded and model order rotates across probes to reduce temporal
  order confounding.
- Generation temperature is zero and output is validated automatically.
- ML answers use deterministic JSON/numeric validation.
- Bugs2Fix answers use normalized exact repair against the paired public target.
- The calibration set is separate from the 60-case allocation-policy manifest.

## Predeclared rank rule

For each model, pool the two workload families within each difficulty (10 probes
per difficulty) and compute the Wilson lower 95% confidence bound.

- L1 gate: D1 lower bound >= 0.50.
- L2 gate: pass L1 and D2 lower bound >= 0.40.
- L3 gate: pass L1-L2 and D3 lower bound >= 0.25.
- L0: fails the L1 gate.

Ranks are contiguous: a model cannot receive L3 if it fails D1 or D2. Report
the per-workload rates alongside the pooled gate because 15 probes per workload
are too few for a strong workload-specific rank.

## Claim boundary

The result is a calibration of the recorded MFEC deployment aliases on these
probes and collection date. It is not a universal model-family ranking, not a
comparison of ConveyorFlow policies, and not evidence that one vendor is
superior. CodeXGLUE may have appeared in model pretraining, so the Fix Bug score
is an operational calibration measure rather than a contamination-free model
benchmark.

## Instrument correction after pilot

The initial CodeXGLUE normalized exact-repair oracle is retained only as an
instrument-pilot result. Primary Fix Bug calibration v2 uses executable hidden
unit tests plus AST safety screening and restricted subprocess execution. ML
Build and Fix Bug ranks are reported separately as `A[i,w]`; they are not pooled
into a single rank. See `CALIBRATION_DEVIATION_LOG.md` for the disclosure.
