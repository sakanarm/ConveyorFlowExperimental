# Protocol สำหรับ Real LLM Pilot ของ ConveyorFlow

## สถานะและขอบเขต

เอกสารนี้เป็น protocol สำหรับการทดลองระยะถัดไปและยังไม่มีผล Real-LLM การทดลอง
Simulation จำนวน 22,500 runs ยังคงเป็นหลักฐานหลักของ manuscript ปัจจุบัน ส่วน
Real-LLM pilot ใช้ตรวจ external validity ของกลไก ไม่ใช้ย้อนกลับไปปรับสมมติฐานหรือ
เลือกเฉพาะผลที่สอดคล้องกับ Simulation

## Objective

วัดว่า decentralized self-selection แบบ CF-Fit รักษา trade-off ระหว่างต้นทุนต่อ
งานที่ผ่านการตรวจสอบ throughput เวลาเสร็จงาน และคุณภาพปลายทางได้หรือไม่ เมื่อ agent
เป็น LLM API จริง โดยไม่มีตัวกลางตัดสินใจมอบหมายงานให้ agent ใน CF-Fit

Primary estimand คือ paired difference ของ CF-Fit เทียบกับ Static Round Robin และ
Central-Fit ภายใน task stream เดียวกัน ไม่กำหนดว่า CF-Fit ต้องชนะทุก metric

## Model team และ Ability Rank

- ใช้ไม่เกิน 4 models ต่อทีม
- การทดลองแรกควรใช้ models ภายในผู้ให้บริการเดียวกัน 3 versions ที่อยู่ใกล้กัน เพื่อลด
  cross-vendor confounding แล้วจึงทำ cross-vendor robustness เป็นการทดลองรอง
- ตรึง exact model version หรือ snapshot ห้ามใช้ชื่อ alias ที่เปลี่ยน implementation ได้
- Ability Rank ไม่ได้อนุมานจากราคา ความใหม่ จำนวนพารามิเตอร์ หรือชื่อรุ่น
- วัดจาก held-out executable probes แยก ML Build และ Fix Bug
- L1 ต้องผ่านเกณฑ์ D1, L2 ต้องผ่าน D1-D2 และ L3 ต้องรักษา lower 95 percent confidence
  bound เหนือเกณฑ์ใน D3 หากไม่ผ่าน L1 ให้เป็น L0 และไม่เข้า team
- ราคา latency input tokens และ output tokens เป็นตัวแปรทรัพยากรแยกจาก ability

## Input

1. ML Build จาก Adult และ Beijing public corpora
2. Fix Bug จาก Bugs2Fix public corpus
3. case manifest 60 cases แบ่ง 20 cases ต่อ workload และ stratify ตาม D1-D3
4. isolated task bundle ของแต่ละ case ซึ่งต้องมี input files คำสั่งรัน และ deterministic
   validator ก่อนเปลี่ยน `executable_ready` เป็น true
5. frozen team configuration generation parameters timeout retry rule และราคา ณ วันที่รัน

Manifest ที่สร้างจาก `build_cases.py` เป็น specification index เท่านั้น ไม่ใช่ executable
benchmark จนกว่าจะ materialize bundle และ validator ครบ

## Policies

ใช้ 3 policies ใน pilot เพื่อควบคุมงบและตอบคำถามหลักโดยตรง

1. CF-Fit decentralized self-selection พร้อม stand-down และ aging
2. Static Round Robin กำหนดล่วงหน้าโดยไม่ใช้ข้อมูลอนาคต
3. Central-Fit ใช้ข้อมูลที่ agent มองเห็นชุดเดียวกัน แต่มี global matcher

ทุก policy ใช้ task arrival stream, dependency graph, timeout, retry budget และ validator
เดียวกัน การสุ่มต้อง paired ด้วย seed เดียวกัน

## Procedure

1. รัน held-out ability probes และตรึง L1-L3 ก่อนเปิด policy results
2. Freeze config model snapshots task bundles validators prompts prices และ random seeds
3. รัน infrastructure smoke โดยไม่มี case ที่ใช้วิเคราะห์
4. รัน pilot อย่างน้อย 10 paired seeds เพื่อประมาณ variance และ feasibility
5. กำหนดจำนวน Main Real-LLM seeds จาก precision target และงบก่อนดู comparative result
6. เรียกผู้ชนะ claim พร้อมกันได้ไม่เกินจำนวน agent โดยไม่มี round barrier; agent ที่เสร็จก่อน
   ต้องกลับไปสแกนสายพานได้ทันที แม้ agent อื่นยังทำงานอยู่ การวัดเวลาใช้ monotonic wall clock
7. บันทึกทุก assessment volunteer stand-down claim collision execution verification retry
   token usage latency cost และ terminal outcome ใน append-only ledger
8. ตรวจ hash ของ config cases validators raw responses และ event ledger
9. วิเคราะห์ที่ระดับ paired run หรือ seed ห้ามถือ task ใน run เดียวกันเป็น independent replicate

## Outcomes

Primary outcomes คือ cost per verified task, verified throughput, P95 terminal completion
time, task completion rate, dead-letter rate และ unsettled rate Secondary outcomes คือ
productive utilization, tokens per verified task, claim collision, stand-down และ no-volunteer
events

นิยามเชิงปฏิบัติ: verified throughput คือจำนวน VERIFIED หารด้วย wall-clock run time;
completion time วัดจากงานเข้าสายพานครั้งแรกถึง VERIFIED; terminal flow time วัดจากงานเข้า
ครั้งแรกถึง VERIFIED/DEAD_LETTER/UNSETTLED; utilization คือผลรวมเวลาที่ agent ถูก claim
และทำ execution+validation หารด้วย (เวลารัน × จำนวน agent) โดยรายงาน busy time แยก agent
ควบคู่กัน ไม่ใช้ผลรวม latency จาก API แทน wall-clock throughput

เมื่อมี VERIFIED, DEAD_LETTER และ right-censored/unsettled พร้อมกัน ให้รายงาน cumulative
incidence เพิ่มเติม ไม่สรุปจากเวลาเฉพาะงานที่เสร็จเพียงอย่างเดียว

## Analysis boundary

- Simulation และ Real-LLM เป็น evidence คนละ phase ห้าม pool เป็น sample เดียวกัน
- Real-LLM pilot ใช้ประเมิน feasibility และ variance จนกว่าจะ freeze Main Real-LLM plan
- Pareto และ radar เป็น descriptive visualization ไม่ใช่ composite inferential score
- หาก model provider เปลี่ยน snapshot หรือ safety behavior ระหว่างรัน ให้หยุด cell นั้นและ
  บันทึก protocol deviation ห้ามแทนที่รุ่นโดยไม่แก้ version
- Human-expert validation ของ difficulty labels แยกจาก protocol นี้และผู้วิจัยจะดำเนินการเอง

## Claim ที่เขียนได้หลังมีผลจริง

เขียนได้เฉพาะผลของ exact model snapshots, task bundles, validators, prices และช่วงเวลาที่
ทดลอง ห้ามขยายเป็นข้อสรุปว่า provider หรือ LLM ทั่วไปมีพฤติกรรมเช่นเดียวกัน และห้ามนำ
dry-run หรือ mock adapter มาเขียนเป็นผลการทดลอง
