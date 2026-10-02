# แผนที่ล็อกก่อนทดลอง: Real-LLM Supplementary Extension

สถานะ: **FROZEN BEFORE EXECUTION**  
วันที่ล็อก: 28 กันยายน 2026  
ขอบเขต: การทดลองเสริมด้วย LLM จริง ไม่ใช่การแทนที่ Main Simulation

## 1. เหตุผลที่ต้องทดลองเพิ่ม

ผล Real-LLM ชุดหลักเปรียบเทียบ CF-Fit, Static Round Robin (S3) และ Central-Fit ภายใต้ทีม heterogeneous เดียวกัน จึงตอบ RQ1 เรื่องผลของกลไกจัดสรรงานได้ แต่ยังไม่แยกหลักฐานของคำอธิบายทางวิทยาศาสตร์สองส่วนสำคัญ:

1. **Capability heterogeneity (RQ2):** ยังไม่มีทีม LLM จริงที่เอาความหลากหลายออกเพื่อดูว่า CF-Fit เปลี่ยนอย่างไร
2. **Stand-down contribution (RQ3):** ยังไม่ทราบว่าการให้ agent ที่เก่งเกินความจำเป็นหลีกทางสร้างผลเพิ่มจาก fit assessment หรือไม่

จึงเพิ่มเฉพาะเงื่อนไขที่ปิดช่องว่างดังกล่าว ไม่เพิ่มหลาย policy โดยไม่มีสมมติฐาน และไม่ใช้จำนวน policy เป็น contribution ของงาน

## 2. คำถามและเหตุผลของแต่ละเงื่อนไข

### E1 — HET_NO_STANDDOWN

- ทีม: heterogeneous ชุดเดิม
- Policy: CF-Fit ที่คง self-assessment, eligibility, fit scoring, aging, retry และ requeue แต่ปิด stand-down เท่านั้น
- เหตุผล: เป็น component ablation ที่เปลี่ยนเพียงองค์ประกอบเดียว จึงแยก incremental contribution ของ stand-down ได้ตรงที่สุด
- การตีความ: ถ้าผลไม่ต่าง ต้องรายงานว่าไม่พบ incremental effect ภายใต้ workload/ทีมนี้ ไม่สรุปว่ากลไกไม่มีประโยชน์ในทุกบริบท

### E2 — HOM_GLM_GENERALIST

- ทีม: 3 agent slots ที่เป็น `glm-5.3-flash` deployment เดียวกันและมี ability profile ML=3, Fix=3
- Policy: CF-Fit เต็มรูปแบบ
- เหตุผล: เป็น homogeneous high-capability boundary เพื่อดู behavior เมื่อความหลากหลายหายไปและทุก slot เป็น generalist ที่ผ่าน calibration ระดับสูง

### E3 — HOM_GPT_PROFILE

- ทีม: 3 agent slots ที่เป็น `gpt-5-mini` deployment เดียวกันและมี ability profile ML=2, Fix=3
- Policy: CF-Fit เต็มรูปแบบ
- เหตุผล: เป็น homogeneous profile อีกระดับหนึ่ง ช่วยไม่ให้ข้อสังเกตเรื่อง homogeneous ผูกกับ model family เดียว

สอง homogeneous conditions เป็น **boundary/ecological sensitivity evidence** ไม่ใช่ causal mean-matched test เพราะค่าเฉลี่ย ability และ model identity ไม่เท่ากับทีม heterogeneous เดิม การทดสอบ causal RQ2 แบบควบคุม mean ability ใช้ Main Simulation เป็นหลัก

## 3. Reference condition

ใช้ `HET_FULL` จาก Real-LLM main run ที่ผ่าน validation แล้ว 10 paired seeds เป็น reference:

- tencent-hy3: ML=3, Fix=1
- gpt-5-mini: ML=2, Fix=3
- glm-5.3-flash: ML=3, Fix=3
- Policy: CF-Fit เต็มรูปแบบ

## 4. สิ่งที่ควบคุมให้เหมือนเดิม

- 60 executable cases: Adult ML 20, Beijing ML 20, Bugs2Fix 20
- paired seeds 3000–3009
- deterministic validators และ frozen case bundles ชุดเดิม
- team size = 3 slots
- temperature = 0, max output tokens = 4096
- timeout = 180 วินาที, API retry สูงสุด 2 ครั้ง
- allocation parameters: k_scan=8, w1=2, w2=4, max no-volunteer rounds=6, max attempts=3
- atomic claim, asynchronous execution, requeue/retry และ cost จาก provider response header เหมือนเดิม

การคงองค์ประกอบเหล่านี้ช่วยลดคำอธิบายทางเลือก แต่ไม่ทำให้ homogeneous comparison กลายเป็น mean-matched causal test

## 5. Outcomes และ estimands ที่กำหนดล่วงหน้า

รายงานทุก metric โดยไม่เลือกเฉพาะ metric ที่สนับสนุน ConveyorFlow:

- completion rate
- total cost และ cost per verified task
- run wall time และ p95 completion/flow time
- verified throughput
- resource utilization
- input/output tokens, provider calls, retries และ dead letters
- allocation/event diagnostics เช่น stand-down count และงานต่อ agent

Contrasts ที่กำหนดก่อนเห็นผล:

1. `HET_NO_STANDDOWN − HET_FULL` สำหรับ RQ3
2. `HOM_GLM_GENERALIST − HET_FULL` สำหรับ RQ2 boundary
3. `HOM_GPT_PROFILE − HET_FULL` สำหรับ RQ2 boundary

ใช้ paired seed summaries, exact paired Wilcoxon signed-rank, Holm correction ภายใน metric family, paired bootstrap 95% CI และ rank-biserial effect size เช่นเดียวกับชุดหลัก

## 6. สมมติฐาน

- H3a: stand-down จะเปลี่ยนการกระจายงาน โดยลดการใช้ high-capability agent กับงานที่ agent ต่ำกว่ายังเพียงพอ
- H3b: ผลของ stand-down ต่อ completion/time/cost อาจมี trade-off; ไม่กำหนดว่าจะต้องชนะทุก metric
- H2a: เมื่อทีมเป็น homogeneous ประโยชน์จาก capability-task differentiation ควรลดลงหรือเปลี่ยนรูป
- H2b: ความต่างระหว่าง homogeneous กับ heterogeneous อาจสะท้อนทั้ง composition และ model identity จึงตีความเป็น boundary evidence เท่านั้น

## 7. Timing limitation

E1–E3 รันภายหลัง HET_FULL จึงไม่สามารถควบคุม provider load และ network condition ข้ามช่วงเวลาได้อย่างสมบูรณ์ ผลด้านคุณภาพ/ต้นทุนและ event allocation ใช้เป็น contrasts หลัก ส่วน wall-clock latency, throughput และ utilization ที่เทียบข้ามรอบติดป้าย **exploratory cross-window** และต้องไม่ใช้เป็นหลักฐาน causal เดี่ยว ๆ

## 8. กฎหยุด รันซ้ำ และ exclusion

- จำนวนที่ล็อก: 3 conditions × 10 seeds = 30 policy-runs
- provider failure ที่ยังไม่หายหลัง retry ทำให้ run นั้นเป็น `invalid_infrastructure_failure`; ห้ามนับเป็น task failure
- รันซ้ำได้เฉพาะ run ที่ invalid เพราะ infrastructure และต้องเก็บหลักฐาน run เดิมไว้
- validator failure เป็นผลการทดลองตามปกติและห้ามรันใหม่เพราะผลไม่ถูกใจ
- ห้ามเปลี่ยน model, ability rank, case, validator, seed, policy parameter หรือ metric หลังเริ่ม execution
- รายงาน null/negative results และ limitations ครบถ้วน

## 9. ขอบเขต claim ที่อนุญาต

- อนุญาต: “ภายใต้ deployment, workload และช่วงเวลาที่ทดสอบ...”
- อนุญาต: “ไม่พบความแตกต่างเชิงสถิติ” เมื่อผลไม่ significant
- ไม่อนุญาต: อ้าง equivalence จาก non-significance
- ไม่อนุญาต: อ้างว่า heterogeneity เป็นสาเหตุจาก homogeneous boundary controls เพียงอย่างเดียว
- ไม่อนุญาต: อ้างว่า CF-Fit หรือ stand-down เหนือกว่าทุก objective

## 10. เหตุผลเชิงงานตีพิมพ์

การออกแบบนี้เชื่อมกับ scientific story โดยตรง: agent มีความสามารถต่างกัน จึง self-select ตาม fit และ agent ที่เก่งเกินจำเป็นอาจ stand down เพื่อรักษาความสามารถไว้ให้งานยาก การทดลองหลักตอบว่า decentralized selection เปลี่ยน performance อย่างไร ส่วน extension นี้ตรวจว่า heterogeneity และ stand-down ซึ่งเป็นกลไกอธิบาย story มีหลักฐานสนับสนุนเพียงใด โดยแยก confirmatory Simulation ออกจาก supplementary Real-LLM validation อย่างโปร่งใส

