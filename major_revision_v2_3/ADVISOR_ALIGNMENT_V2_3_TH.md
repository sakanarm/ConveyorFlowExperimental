# กรอบวิจัย ConveyorFlow v2.3 ตามข้อเสนอแนะที่ปรึกษา

ตรวจเมื่อ 6 ตุลาคม 2026 โดยเทียบ manuscript Progress Rev4 กับวิธีทดลอง โค้ด `matched_architecture.py` และ protocols ที่ตรึงไว้ เอกสารนี้กำหนดขอบเขตข้อสรุปและรายการแก้ถ้อยคำ ไม่เปลี่ยนอัลกอริทึม configs หรือผลที่ freeze แล้ว

## เรื่องหลักของ paper

งานเข้าระบบเป็น job และ tasks จะขึ้นสายพาน READY เมื่อ dependencies ผ่านการตรวจแล้ว Agent ที่ว่างประเมินงานที่มองเห็นและเลือกเองตาม capability–task fit จากนั้น volunteer หรือให้โอกาส Agent ที่เหมาะกว่า Atomic claim ใช้แก้การชนกัน ไม่ใช่ตัวกลางที่เลือกคู่ Agent–Task

งานที่ผ่านจะปลดล็อกงานถัดไป ส่วนงานที่ล้มเหลวหรือไม่มีผู้รับจะกลับ READY ได้ตามขอบเขต aging/retry/requeue ที่กำหนด งานที่ยังไม่จบเมื่อถึง horizon ต้องนับเป็น UNSETTLED ไม่หายไปจากผล

Scientific contribution ยังคงเป็น **Decentralized Self-Selection + Capability Heterogeneity + Fit/Stand-down** จำนวน policies, output contracts, ML stage harness และ repository patching เป็นเครื่องมือหรือหลักฐานที่ใช้ทดสอบเรื่องนี้ ไม่ใช่ contributions หลักคนละเรื่อง การเพิ่ม executable workloads ตรวจว่ารันและตรวจงานจริงได้ แต่ไม่ได้เปลี่ยน paper ให้เป็นข้อเสนอวิธี bug repair หรือ AutoML ใหม่

## คำถามและหลักฐานที่ต้องเชื่อมกัน

| กรอบที่ปรึกษา | การออกแบบ/สิ่งที่รายงาน | ข้อจำกัดที่ต้องคงไว้ |
|---|---|---|
| RQ1: self-selection ส่งผลอย่างไร | Throughput, Task Completion Time, Utilization และ Cost พร้อม verified/dead-letter/unsettled; เทียบ CF-Fit กับ Static และ Central-Fit | ระบุ metric/เงื่อนไข ไม่เปลี่ยน objective หลังเห็นผล และรายงาน cost objective ที่ไม่ผ่าน |
| RQ2: diversity ภายใต้ CF-Fit | H0=(2,2,2,2), H1=(1,2,2,3), H2=(1,1,3,3): ทีมละ4 Agents และ mean rank2; แยก R0/R1 | Live contrasts ต่าง model identity และช่วงเวลารันด้วย จึงไม่อ้าง pure causal effect |
| Fit และ Stand-down มีส่วนอย่างไร | Ablations แยก assessment, fit, stand-down และ aging ตามกติกาที่ freeze | รายงานผลไม่ชัดด้วย ไม่บังคับให้ทุก ablation ต้องด้อยกว่า full CF-Fit |
| Tasks อยู่บนสายพาน | Fig.1–5 พร้อม editable draw.io; READY, dependency gate, local bids, claim และ retry | Static กำหนดเจ้าของล่วงหน้า ไม่ใช่ AI แจกงานขณะรัน; shared store ยังเป็น dependency |
| รันงานจริงได้หรือไม่ | แยก full-DAG feasibility, หก repository cases ต่อโมเดล และ isolated stages | ไม่รวมกับ22,500 simulation runs/60 microtasks และไม่เรียก stages ว่า full pipelines |

## สามจุดที่ต้องเล่าให้ตรงกับโค้ด

**RQ2 controls:** `_agents` ใน `../Code/conveyorflow_v2/simulator.py` ตรึง speed/token_factor/price เท่ากันทุก rank ใน R0 จึงใช้ดูความต่างของ capability composition ภายใต้ resource profiles ที่ควบคุม ส่วน R1 เปลี่ยนทั้ง capability และทรัพยากรตาม rank จึงไม่ใช่ผลของ capability variance ล้วน Mean rank เท่ากันไม่ได้แปลว่า mean success probability หรือต้นทุนรวมเท่ากัน ต้องแยกข้อสรุป R0/R1

**Stand-down:** แนวคิดคือ Agent ที่เก่งเกินงานเปิดโอกาสให้ Agent ที่พอเหมาะรับงานง่าย ใน main simulator เป็น **soft stand-down**: เพิ่ม overqualification penalty ให้ local bid และผ่อน penalty เมื่องานรอนาน Agent ที่เก่งยัง eligible และอาจได้งานเมื่อไม่มีคู่แข่งที่เหมาะกว่า ส่วน real microtask allocator ใช้ temporary refusal แยกต่างหาก จึงห้ามกล่าวว่าสอง implementations เหมือนกันทุกขั้น หรือ High Agent ถอนตัวจากงานง่ายเสมอ หากทดลอง strict stand-down ต้อง freeze revision/ablation ใหม่ก่อนรัน ไม่แก้ผลเดิม

**Central controls:** Central-Fit เดิมเป็น global matcher จึงเทียบ complete policies ที่ต่างทั้ง candidate pairs, matching และ decision authority ส่วน Central-Matched คง one-bid-per-agent, fit, stand-down และ arbitration เดิม แล้วเพิ่ม coordinator relay มันควบคุม **additional coordinator path/dependency** ไม่ได้พิสูจน์ผลของ centralized optimizer ทุกชนิด หรือว่าไม่มี single point of failure ทั้งระบบ E0 parity เป็นผลที่คาดหวังของ control ส่วน E2_COORD เป็น synthetic interruption ไม่ใช่สถิติ outage ของ MFEC

## ผลที่เล่าได้โดยไม่หลุดกรอบ

Simulation เดิมมี trade-offs: CF-Fit กับ Central-Fit ใกล้กันหลาย metrics แต่ไม่เท่ากันทุกด้าน และ cost/verified task ของ CF-Fit สูงกว่า Static ใน prespecified contrasts จึงไม่กล่าวว่า lower-cost objective บรรลุแล้วเพียงเพราะ throughput สูงกว่า Verified-only latency มี selection bias ส่วน terminal P95 รวม dead-letter/horizon accounting ไม่ใช่เวลาของงานที่สำเร็จล้วน

Repository first-attempt ใหม่ครบ18คู่และ audit ผ่าน: Tencent4/6, GPT1/6, GLM2/6 VERIFIED โดย GLM มี provider-unresolved1 และ unfinished/empty3 แยกจาก visible-test failures หกเคส/สาม clusters และ public tests ทำให้ Wilson intervals เป็น descriptive ไม่ใช่ population bounds ที่ปรับความสัมพันธ์แล้ว ผลนี้แสดง bounded localized repairs ไม่ใช่ allocation advantage ไม่ใช้จัด Ability Rank หรือ fit Equation7 ดูเหตุผลและผลละเอียดใน `REPOSITORY_FIRST_ATTEMPT_RESULTS_TH.md`

ML isolated-stage v2 ใช้ reused specifications และ trusted predecessors เดียวกัน เพื่อไม่ตัดโอกาสทดสอบ train/package เมื่อ stage ก่อนล้ม Exposure inventory เปิดเผย legacy responses ที่ request-only scan พลาด; v1 ไม่มี paid calls และเก็บไว้ ผลใหม่ใช้ planned denominator36 ไม่รวม replay เป็น observations เพิ่ม ด้วยสอง corpora ที่สัมพันธ์กันและตัวอย่างเล็ก จึงยังไม่ปิด held-out calibration/main gap

## การแก้ถ้อยคำรอบถัดไปใน Word

1. คง RQ1 เป็น “how/what trade-offs” และ RQ2 เป็นผลของ diversity ไม่เปลี่ยนเป็น superiority hypotheses ย้อนหลัง
2. อธิบาย soft stand-down และ R0/R1 ให้ชัดใน methodology/discussion พร้อมคงผลที่ไม่ชัด
3. ใช้ “matched coordinator-path/dependency control” เมื่อสรุป Central-Matched ไม่อ้างว่าแยก centralized optimization ทุกส่วนได้แล้ว
4. ใส่ผล ML stages เมื่อครบและ audit ผ่านใน supporting feasibility section ไม่ยกเป็น contribution หลัก
5. ระบุ paired live allocation และ held-out calibration ว่ายังไม่เสร็จ ไม่อ้างว่าปิด Major Revision หรือพร้อมส่ง Q2 แล้ว

## สถานะไฟล์ Word

Rev4 มี32หน้า/16รูป/13 native equations/10ตาราง รวม completed repository table แต่ยังไม่ผ่าน final QA: heading polish จบเฉพาะ blind ก่อนสคริปต์หยุด การทำต่อด้วย Word ติด usage quota ของ automatic approval review ภาพ render ก่อน polish ไม่ตรงกับไฟล์ปัจจุบัน ต้องทำทั้งสองฉบับให้เสร็จ ล้าง blind metadata และตรวจทุกหน้าใหม่ก่อนส่งมอบ Rev3 และ v2.2 เดิมไม่เปลี่ยน
