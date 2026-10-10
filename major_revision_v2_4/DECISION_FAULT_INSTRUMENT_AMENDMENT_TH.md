# v2.4 decision-fault instrument amendment (before any trial)

Initial `results/decision_fault_v1/lock.json` was created with zero trials and zero provider calls. The first `--execute` invocation stopped in `freeze()` before creating a trial: Python compared frozen JSON dependency lists with in-memory tuples and reported lock drift. This was a serialization-equivalence bug, not a research outcome.

The initial lock is retained. `decision_fault_replay_v1.py` now serializes task dependencies as lists in the stable object and uses a new `results/decision_fault_v1b` lock/output root. No fault or allocation outcome was observed before this amendment. The task stream, arms, scenarios, seed range, worker implementation, CAS rule, fixture outcomes and metrics remain unchanged. The v1b lock must be frozen before its first trial and must not be edited after execution starts.
