# ConveyorFlow CF Fit Algorithm Specification

## Public state

READY belt เปิดเผย task id, stage, required skill, specification, age และ dependency status ไม่เปิดเผย `difficulty_gt` หรือ future outcome

## Local observation

แต่ละ idle Agent อ่าน READY tasks ตามลำดับสายพานไม่เกิน `K_scan=8` งานต่อรอบ และประเมิน `d_hat`, `p_hat`, effort และ confidence ด้วยตนเอง

## Eligibility

Task เป็น candidate เมื่อ skill compatible, Agent ว่าง, retry-diversity ผ่าน และ `p_hat >= tau(age)` โดย `tau` ลดจาก 0.60 เป็น 0.50 และ 0.35 ตามช่วงอายุ

## Fit and stand down

ใช้ workload-specific latent ability `theta` และ estimated difficulty:

`fit_gap = abs(level - d_hat)`

`overqualification = max(0, level - d_hat)`

`urgency = min(age / W3, 1)`

`backoff = beta_f*fit_gap + beta_o*overqualification*(1-urgency) - beta_a*urgency + jitter`

Agent เลือก candidate ที่ backoff ต่ำสุดและ schedule claim ที่ local time บวก backoff ค่า jitter ถูกสร้างจาก seed, task, agent และ attempt ผู้ที่ claim หลัง task ถูกล็อกแล้วแพ้ CAS และกลับไปดู belt รอบถัดไป

## No-volunteer controls

- **F0 Immediate re-offer:** threshold 0.60 และ stand-down คงเดิม งานอยู่บน belt
  จนถึง W3 แล้วเข้า DEAD_LETTER เพื่อไม่ให้ livelock
- **F1 Tail requeue:** threshold/stand-down คงเดิม ย้ายงานไปท้าย belt ทุกช่วง W1
  แบบ bounded จนถึง W3 หรือ requeue limit
- **F2 Aging + bounded relaxation:** decentralized default; ลด threshold และ
  stand-down penalty ตามอายุ
- **F3 Forced best-available:** ที่ W2 ตัวกลางเลือก Agent ว่างด้วย estimated
  success probability แล้วบันทึก `forced_rescue` และ coordination cost เป็น hybrid
  reference ไม่ใช่ ConveyorFlow

## No volunteer F2

- `age < W1`: re-offer ปกติ
- `W1 <= age < W2`: เพิ่ม urgency และ tail requeue
- `W2 <= age < W3`: ลด threshold และปิด overqualification penalty
- `age >= W3` หรือ requeue เกิน limit: DEAD_LETTER พร้อม cascade ไปยัง downstream tasks

Stand-down เป็น bounded hesitation ไม่ใช่ refusal

## Difficulty stress profile

`mixed` ใช้ distribution จาก corpus profile ส่วน `D3_HEAVY` ใช้ core difficulty
weights D1/D2/D3 = 0.10/0.20/0.70 โดยไม่เปลี่ยน arrival schedule หรือ task DAG

## Resource-mapping sensitivity

- `R1`: ability สูงสัมพันธ์กับ speed/token/price ที่สูงขึ้น
- `R1_REVERSED`: สลับ profile ของ L1 และ L3
- `R1_PERMUTED`: หมุน profile L1->กลาง, L2->สูง, L3->ต่ำ

Ability curve ไม่เปลี่ยนเมื่อ permute resource mapping

## Central Fit control

Central-Fit ใช้ observation window, assessment budget, cost และ latencyเดียวกับ CF-Fit แต่ central matcher เลือก assignment จึงไม่เรียกว่า ConveyorFlow
