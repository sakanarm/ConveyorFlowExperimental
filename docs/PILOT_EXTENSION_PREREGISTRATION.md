# Pre-Main Pilot Extension Preregistration

## Status and boundary

Frozen before execution on 2026-09-22. ชุดนี้เป็น Pilot Extension เพื่อประมาณ
variance/power และตรวจ mechanism เท่านั้น ไม่ใช่ Main confirmatory evidence และ
ห้ามรวมกับ seeds 0-39

## Common controls

- paired seeds 40-59
- 200 jobs/run, fixed horizon = last arrival + 180 ticks
- `K_scan=8`, max attempts 3, W1/W2/W3 = 8/20/50
- workloads Adult ML, Beijing ML, Bugs2Fix
- loads medium 0.70 และ high 0.90
- task/arrival/potential-outcome draws keyed ด้วย seed และ entity identifiers
- zero-success, dead-letter และ UNSETTLED runs ต้องเก็บทั้งหมด

## RQ3 ablation matrix

- Full, A1 No self-assessment, A2 No fit, A3 No stand-down, A4 No aging
- teams H1/H2
- workloads 3, loads medium/high, regimes R0/R1
- fallback F2, mixed difficulty
- 2,400 runs ก่อน deduplication กับ E4

## Resource-mapping sensitivity

- Full CF-Fit, teams H1/H2, workloads 3, loads medium/high
- regimes R1_REVERSED และ R1_PERMUTED
- fallback F2, mixed difficulty
- 480 runs

## E4 fallback stress matrix

- F0/F1/F2/F3 โดย F3 เป็น hybrid reference แยกจาก ConveyorFlow
- teams L1X4/H1
- workloads 3, loads medium/high, regimes R0/R1
- profiles mixed/D3_HEAVY
- 3,840 runs ก่อน deduplication

หลังตัด Full/F2/H1/mixed cells ที่ซ้ำกัน design มี **6,480 unique runs**

## Acceptance checks

- design, metrics และ event files ครบ 6,480 unique run IDs
- A1 มี assessment count = 0; A3 มี stand-down count = 0
- F0 ไม่มี requeue/forced rescue; F1 มี tail requeue; F3 มี forced rescue
- D3_HEAVY มีสัดส่วน D3 สูงกว่า mixed ทุก workload
- same config/seed replay ได้ event hash เดิม
- cost ledger และ artifact hashes ผ่าน

## Power planning

ใช้ run/seed เป็นหน่วยวิเคราะห์ สร้าง paired seed-level contrasts สำหรับ RQ3 และ
E4 แยก family ใช้ power 0.80 และ Holm-family alpha 0.05 รายงาน Monte Carlo
normal approximation เป็น preliminary N เท่านั้น Overall Main N ต้องใช้
`max(50, N_RQ1, N_RQ2, N_RQ3, N_E4)` หลัง margins ถูก freeze

## No post-result tuning rule

หาก gate ไม่ผ่าน ห้ามแก้ค่าทับผลชุดนี้ ให้เก็บเป็น audit trail ระบุเหตุผลและใช้
seed range ใหม่สำหรับ validation รอบถัดไป
