# Pilot Preregistration

## Status

เอกสารนี้ freeze Pilot เท่านั้น Main preregistration จะสร้างหลัง power analysis

## Fixed choices

- primary endpoint cost per verified task
- fixed team size 4
- H0 L2,L2,L2,L2
- H1 L1,L2,L2,L3
- H2 L1,L1,L3,L3
- `K_scan=8`, retry limit 3, F2 default
- calibration round 1 ใช้ paired seeds 0-19; independent validation round ใช้ 20-39
- R0 equal resource; R1 normalized heterogeneous resource
- no policy reads ground-truth difficulty ยกเว้น S2
- Pilot results must not be used as confirmatory evidence

## Pilot acceptance checks

- deterministic replay for same config and seed
- different seed changes workload
- no double claim and one task per Agent
- monotonic pass rates by ability and difficulty
- pooled pass rate ทุก Ability-Difficulty cell อยู่ในช่วง 0.05-0.95
- non-empty D1, D2, D3 strata
- no strategy terminates by an accidental global-loop failure
- cost ledger equals billable event sum
- no zero-success or UNSETTLED run is dropped
