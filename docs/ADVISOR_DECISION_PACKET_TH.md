# ชุดตัดสินใจก่อน Main Experiment

## สถานะหลักฐาน

- Validation Pilot: 2,160/2,160 runs; artifact hashes ผ่านทั้งหมด
- Pre-Main Extensions: 6,480/6,480 runs; artifact hashes ผ่านทั้งหมด
- Preliminary power recommendation: 50 paired seeds
- Main experiment: ยังไม่อนุญาตจนกว่ารายการด้านล่างจะถูก freeze

## Scientific story ที่เสนอ

ConveyorFlow ศึกษาการจัดสรรงานแบบ decentralized self-selection ภายใต้ทีมที่มี
capability heterogeneity โดย Agent ประเมินงานและเลือกตาม capability-task fit พร้อม
aging/fallback ป้องกันงานค้าง ผล Pilot ชี้ว่า stand-down มีผลเพิ่มจาก Fit ค่อนข้างเล็ก
จึงควรนำเสนอเป็น bounded refinement ไม่ใช่ contribution ที่รับประกันผลเด่นทุก metric

## Difficulty evidence decision

ใช้ role-conditioned LLM annotation สามรอบจาก underlying model เดียวกัน แยกบทบาทและ
ลำดับ item พร้อม adjudication อีกหนึ่งรอบ เรียกว่า `LLM-derived operational difficulty`
เท่านั้น ไม่เรียกว่า human expert ground truth รายละเอียด Claim อยู่ใน
`LLM_ANNOTATION_CLAIM.md`

## Margin decision

เสนอให้ใช้ absolute non-inferiority margin 0.03 (3 percentage points) สำหรับ completion,
dead-letter และ unsettled เพราะตีความตรงและเข้มกว่าตัวเลือก 0.05 แต่ไม่แคบเท่า 0.02
ซึ่งอาจต้องใช้ N สูงโดยไม่ได้เพิ่ม practical meaning ข้อเสนอนี้เป็น normative decision
และไม่ได้เลือกจากผล Main

- [x] เจ้าของโครงการอนุมัติ margin 0.03 ทั้งสาม outcome เมื่อ 2026-09-22
- [ ] เปลี่ยนเป็น: ____________________ พร้อมเหตุผล: ____________________

## Confirmatory lock ที่เสนอ

- paired seeds: 50
- seed range: 1000–1049
- primary: cost per verified task ภายใต้ quality/completion constraints
- key secondary: verified throughput และ P95 terminal flow time
- แยก R0/R1; ห้าม pool resource regimes
- Holm correction ภายในแต่ละ RQ/metric family
- zero-success, dead-letter และ unsettled ต้องเก็บและรายงาน

## Sign-off

- [ ] LLM annotation protocol/claim boundary ยอมรับได้
- [x] Margin ได้รับอนุมัติโดยเจ้าของโครงการ
- [x] N=50 และ seeds 1000–1049 ได้รับอนุมัติโดยเจ้าของโครงการ
- [x] Main analysis plan freeze แล้ว
- [x] เจ้าของโครงการอนุญาตให้เริ่ม Main E1–E4
- [ ] ที่ปรึกษารับรองก่อน manuscript submission

ผู้อนุมัติ: ____________________ วันที่: ____________________
