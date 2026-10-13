# ผล real-LLM mixed-workload v2.3 สำหรับตรวจต้นฉบับ

สถานะ: ผลจาก auditor อิสระ 6 paired blocks (`MAIN_BLOCK_01–04`, `MAIN_BLOCK_05_R1`, `MAIN_BLOCK_06`), 155 provider attempts ที่มีหลักฐานใน ledger; มิใช่การสุ่มจาก 6 datasets อิสระ ข้อมูล Adult และ Beijing ถูกใช้ซ้ำข้ามบล็อก, repository cases มาจากสามโครงการ, หนึ่งบล็อกมี 2 งาน ML แบบ 4-stage DAG และ 1 งานซ่อม bug จริง ทั้งสาม allocation arms ใช้ task/arrival, agent roster, resource/ability profile, verifier และ observation horizon เดียวกันภายในบล็อก

`MAIN_BLOCK_05` เดิมถูกพักโดยผู้ใช้ระหว่างรัน ไม่มีผลครบสามแขนและ **ไม่** นับเป็น research result มีคำขอหนึ่งรายการที่เริ่มแล้วแต่ provider/billing outcome ไม่ทราบ บล็อก `MAIN_BLOCK_05_R1` คือ technical replacement ที่รันใหม่ครบสามแขนภายใต้ amended lock; raw เดิมถูกเก็บไว้และไม่ถูกผสมกับ R1 รายละเอียดและ hash อยู่ใน `MAIN_BLOCK_05_INTERRUPTION_20261007_TH.md`, `MAIN_BLOCK_05_REPLACEMENT_PROTOCOL_V1_TH.md` และ audit capsule ของ R1

## ผลระดับงาน

| Arm | งานที่ verified ภายใน horizon / 18 | ML pipelines verified / 12 | Repository repairs verified / 6 |
| --- | ---: | ---: | ---: |
| CF-Fit | 11 | 11 | 0 |
| Central-Fit (same fit rule) | 10 | 10 | 0 |
| Static Owners (กำหนดเจ้าของก่อนรัน) | 12 | 11 | 1 |

Repository repair ที่ผ่านคือ `matplotlib_28` ใน Static ของบล็อก 6 โดย `tencent-hy3`: visible test, public regression, fresh replay ของ visible และ regression คืน exit code 0 ทั้งสี่ด่าน งานซ่อมอื่นไม่ผ่านเกณฑ์ครบ จึงห้ามกล่าวว่า CF-Fit ซ่อม repository สำเร็จใน main tier; งานซ่อมหลายครั้งติดรูปแบบ strict unified diff/token cap ต้องแยก limitation ของ artifact interface จาก allocation mechanism

## เวกเตอร์ RQ1 (ค่าเฉลี่ยของ 6 paired blocks)

| Arm | Throughput verified jobs/hour | Mean completion time ของงานที่สำเร็จ (s) | Busy utilization | Provider-reported cost units / verified job (mean of block ratios) |
| --- | ---: | ---: | ---: | ---: |
| CF-Fit | 1.833 | 322.20 | 0.0714 | 0.02991 |
| Central-Fit | 1.667 | 273.59 | 0.0510 | 0.03060 |
| Static Owners | 2.000 | 719.53 | 0.0914 | 0.02880 |

ค่าเฉลี่ย completion time เป็น **conditional on success**; ทั้งสาม arm สำเร็จคนละ subset ของงาน จึงอ่านว่าเป็น turnaround ของงานที่แต่ละ arm ส่งมอบได้ ไม่ใช่เวลาเฉลี่ยของ task ที่เหมือนกันทุกตัว Utilization สูงไม่ได้แปลว่าดีเสมอ อาจหมายถึง agent ถูกงาน/การรอ provider นานขึ้น หน่วยเงินของ `response_cost` ไม่ได้รับการยืนยันจาก provider จึงห้ามใส่สัญลักษณ์สกุลเงิน

## ผลจับคู่ (CF-Fit ลบ baseline)

| Contrast | Throughput (jobs/hour) | Completion time (s) | Busy utilization | Cost units/verified job |
| --- | ---: | ---: | ---: | ---: |
| CF-Fit − Central-Fit, 6 blocks | +0.167 | +48.61 | +0.0205 | −0.00069 |
| CF-Fit − Static, 6 blocks | −0.167 | −397.33 | −0.0200 | +0.00111 |
| CF-Fit − Central-Fit, 5 original complete blocks | 0.000 | +49.34 | +0.0181 | +0.00231 |
| CF-Fit − Static, 5 original complete blocks | −0.200 | −372.06 | −0.0144 | +0.00315 |

ผล CF-Fit กับ Central-Fit **ใกล้กันในบาง metric แต่ไม่เท่ากันทุกด้าน**: ในห้าบล็อกเดิม throughput เฉลี่ยต่าง 0; เมื่อรวม R1 ต่าง +0.167 ส่วน CF-Fit จบงานที่สำเร็จช้ากว่า Central เฉลี่ยประมาณ 49 วินาที แต่เร็วกกว่า Static ประมาณ 6.6 นาที โดย Static ได้จำนวนงานสำเร็จรวมมากกว่าเพราะซ่อม Matplotlib ได้หนึ่งเคส ช่วง bootstrap ของ main เป็น descriptive block-resampling ไม่ใช่ population confidence interval และไม่ใช่ equivalence test การเปรียบ CF/Central ควบคุมกฎ fit และ roster ให้ตรงกัน แต่ผล model assignment และ provider latency ในเวลาจริงยังแปรผัน จึงไม่อาจอ้าง causal effect ของ decentralization เพียงอย่างเดียว

## ขอบเขตการอ้างใน paper

- RQ1 ใช้คำว่า “ส่งผลอย่างไร” ต่อ throughput, completion time, utilization, cost efficiency; ไม่ใช้ “ดีกว่าทุก baseline” หรือ scalar winner
- Scientific contribution ที่ทดสอบคือ READY tasks บน belt, local self-assessment/volunteering, capability–task fit และ stand-down; จำนวน policy เป็น experimental controls ไม่ใช่ contribution หลัก
- RQ2 เรื่องทีม homogeneous/heterogeneous และ ablation ต้องอ้างผล simulation ชุดเดิมแยกจาก main real-LLM tier นี้; main tier นี้เป็น heterogeneous three-model roster เท่านั้น
- CF-Fit ไม่มี centralized *allocation decision maker* ใน trace แต่ยังพึ่ง shared belt/claim store, verifier และ provider gateway จึงห้ามอ้างว่าไม่มี single point of failure ทั้งระบบ หรือพิสูจน์ fault tolerance แล้ว
- ผลนี้แสดง end-to-end ML pipeline จริงและอย่างน้อยหนึ่ง successful repository repair จริงภายใต้ baseline; ไม่รองรับข้ออ้างว่า CF-Fit ทำ repository repair ได้สำเร็จในชุด main และไม่ควรใช้ microtask surrogate แทนผลนี้

แหล่งตัวเลข: `main_analysis_with_replacement_v1.json` ซึ่งผูก hash ของ audit capsule และ raw ledger แต่ละแขน; provider call count จากหก audit capsules ผลนี้ต้องนำไปแก้ manuscript/presentation แบบระบุ protocol replacement และ limitation ให้ครบ ก่อนตัดสินใจส่งวารสาร
