# ConveyorFlow Main Simulation Preregistration — FROZEN

## Status

**FROZEN 2026-09-22 / AUTHORIZED FOR EXECUTION BY PROJECT OWNER.** Advisor sign-off
ยังต้องมีแยกต่างหากก่อนส่ง manuscript แต่ไม่ใช้แก้ protocol หลังเห็น Main outcomes

## Scientific claim boundary

งานไม่ตั้งสมมติฐานว่า CF-Fit ต้องชนะทุก metric แต่ประเมิน trade-off vector ของ
cost per verified task, verified throughput, P95 terminal flow time, completion,
dead-letter/unsettled และ utilization เทียบกับ static/central controls

## Confirmatory questions

- RQ1: decentralized self-selection เปลี่ยน trade-off vector เมื่อเทียบ S1/S2/S3
  และ Central-Fit อย่างไร
- RQ2: capability variance ที่ mean latent ability เท่ากันเปลี่ยนผล CF-Fitอย่างไร
- RQ3: self-assessment, Fit, Stand-down และ Aging แต่ละส่วน contribute อย่างไร
- E4: fallback mechanisms รับมือ no-volunteer/D3-heavy stress อย่างไร โดย F3 เป็น
  hybrid reference ไม่ใช่ ConveyorFlow

## Experimental unit and pairing

หน่วยวิเคราะห์คือ run/seed ภายใน workload-load-team-resource cell ทุก policy ใน
paired cell ใช้ arrivals, tasks และ keyed potential outcomes เดียวกัน Task ภายใน
run ไม่ถือเป็น independent replicates

## Planned matrices

- E1/RQ1: CF-Fit, S1, S2, S3, Central-Fit; H1 primary; 3 workloads × 3 loads;
  R0/R1 แยกรายงาน
- E2/RQ2: CF-Fit; H0/H1/H2; 3 workloads × 3 loads; R0 primary, R1 robustness
- E3/RQ3: Full/A1/A2/A3/A4; H1/H2; 3 workloads; medium/high; R0/R1
- E4: F0/F1/F2/F3; L1X4/H1; 3 workloads; mixed/D3-heavy; medium/high;
  R0/R1; F3 แยกเป็น hybrid
- Resource sensitivity: R1 positive/reversed/permuted mappings
- Annotation sensitivity: lower/adjudicated/upper role-vote mappings สำหรับ CF-Fit,
  S2 และ Central-Fit บน H1, medium/high, R0; primary inference ใช้ adjudicated เท่านั้น

## Outcomes

Primary outcome สำหรับ RQ1 คือ cost per verified task ภายใต้ quality/completion
constraints ส่วน verified throughput และ P95 terminal flow timeเป็น key secondary
outcomes RQ2 ใช้ trend ตาม latent variance 0/0.5/1.0 และ RQ3 ใช้ paired change
Full-minus-ablation

## Margins to freeze

| Constraint/contrast | Margin | Status |
|---|---:|---|
| completion non-inferiority | 0.03 absolute | frozen |
| dead-letter non-inferiority | 0.03 absolute | frozen |
| unsettled/backlog non-inferiority | 0.03 absolute | frozen |
| cost smallest effect | 10% | pilot rule; confirm before freeze |
| throughput smallest effect | 10% | pilot rule; confirm before freeze |
| P95 time smallest effect | 10% | pilot rule; confirm before freeze |

## Sample size

`N_main = max(50, N_RQ1, N_RQ2, N_RQ3, N_E4)` paired seeds ใช้ power 0.80
และ family-wise alpha 0.05 หลัง Holm correction

- RQ1/RQ2 pilot estimate: 50
- RQ3/E4/resource-sensitivity pilot estimate: 50
- preliminary overall N under current smallest-effect rules: 50
- final N: 50 paired seeds
- confirmatory seed range: 1000–1049
- frozen draft matrix เมื่อใช้ N=50: 22,500 unique runs รวม 1,800 annotation-sensitivity runs

## Statistical analysis

1. คำนวณ outcome ต่อ run โดยไม่ใช้ task เป็น replicate
2. สร้าง paired differences ภายในทุก matched cell
3. รายงาน effect estimate, 95% CI และ standardized effect โดยแยก R0/R1
4. ใช้ paired seed-cluster bootstrap 10,000 resamples, analysis seed 20260922
   สำหรับ 95% CI และ Wilcoxon signed-rank เป็น hypothesis test
5. ปรับ multiple comparisons ด้วย Holm ภายในแต่ละ RQ family
6. รายงาน interaction policy×load, policy×workload และ policy×resource เฉพาะที่
   preregister; interaction อื่นเป็น exploratory
7. RQ2 ใช้ ordered trend test ตาม latent variance และรายงาน pairwise H0/H1/H2
8. Zero-success เป็น infeasible/infinity ไม่แทนด้วยศูนย์; UNSETTLED และ
   dead-letter ไม่ถูก drop
9. รายงาน Pareto/trade-off และห้ามสร้าง post-hoc composite score เพื่อเลือก winner

## Exclusion and rerun rule

ไม่มี outcome-based exclusion Run ถูก rerunด้วย seed/config เดิมได้เฉพาะ artifact
เสียหาย, invariant failure หรือ infrastructure interruption พร้อมบันทึกเหตุผล
และเก็บ failed artifact หากอ่านได้

## Freeze checklist

- [x] role-conditioned LLM annotations ผ่าน agreement gate, adjudication และมี frozen SHA-256
- [x] บทความระบุชัดว่า labels ไม่ใช่ human-expert ground truth
- [x] quality/non-inferiority margins ได้รับอนุมัติ
- [x] Pilot Extension ผ่านและคำนวณ RQ3/E4 power แล้ว
- [x] final N และ seed range ถูก lock
- [ ] code/config/data snapshot มี SHA-256
- [x] analysis plan ถูก freeze ก่อนเห็น Main outcomes
- [x] เจ้าของโครงการอนุมัติ Main E1-E4 เป็นลายลักษณ์อักษรใน session
- [ ] ที่ปรึกษาอนุมัติ manuscript ก่อน submission
