# Pilot Calibration Decision

## Round 1 finding

Calibration Pilot รอบแรกใช้ paired seeds 0-19 ครบ 2,160 runs และผ่าน
monotonicity ทุกช่อง แต่ pooled empirical pass rate ของ L3-D1 เท่ากับ 0.9815
ซึ่งสูงกว่า ceiling diagnostic 0.95 ผลรอบแรกจึงถูกเก็บแยกใน
`results/pilot_round1_precalibration/` และห้ามใช้เป็น confirmatory evidence

## Locked revision for independent validation pilot

แก้เฉพาะ generative ability curve จาก
`1.2 + workload_adjustment + 1.2*theta - 1.5*(difficulty-2)` เป็น
`alpha_w + 0.85*theta - 1.2*(difficulty-2)` โดย alpha เท่ากับ
0.88/0.86/0.86 สำหรับ Adult/Beijing/Bugs2Fix ตามลำดับ

เหตุผลคือให้ theoretical probabilities ทุก Ability-Difficulty cell อยู่ในช่วง
ประมาณ 0.23-0.95 พร้อมรักษา ordering และ behavioral anchors ของ L1/L2/L3
การปรับนี้พิจารณาเฉพาะ calibration diagnostic ไม่ได้เลือกจาก policy winner

เพื่อไม่ validate บน random draws ชุดเดิม รอบ validation ใช้ paired seeds 20-39
ส่วน Main confirmatory ต้องใช้ seed ชุดใหม่หลัง protocol ถูก freeze

## Decision rule

Validation Pilot ต้องผ่าน:

- pass rate เพิ่มตาม Ability และลดตาม Difficulty
- pooled cell rate ทุกช่องอยู่ระหว่าง 0.05 และ 0.95
- queue regime ของแต่ละ workload เป็น low < medium < high
- run integrity และ reproducibility checks ผ่าน
