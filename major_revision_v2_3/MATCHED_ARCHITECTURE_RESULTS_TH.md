# v2.3 matched architecture contrast — ผล simulation รอบแรก

สถานะ: รันครบ 3 ตุลาคม 2026; **เป็น simulation เท่านั้น** ไม่ใช่ผล Real-LLM และไม่ใช่การวัด outage จริงของ MFEC

## Design และ audit

ใช้ design ที่ล็อกใน `config_matched_v1.json`: 20 seeds × 3 workloads × 3 loads × 2 resource regimes × 3 environments × 2 policies = **2,160 runs หรือ 1,080 paired cells**. ทั้งสอง policy เห็น task stream, frontier K=8, agent team, assessment, fit/stand-down, retry-diversity, aging, fallback, cost functions และ keyed potential outcomes เดียวกัน `CENTRAL_MATCHED` รับเพียง local bid หนึ่งรายการต่อ agent ไม่ใช้ global matching แบบ `CENTRAL_FIT` เดิม

ไฟล์ `results/matched_v1/main/manifest.json` บันทึก source/config/label/result hashes; `pair_audit.csv` บันทึก event hashes และ parity; `metrics.csv` เป็น run-level outcomes; `summary.csv` เป็น paired estimates และ bootstrap CIs. `analyze_matched_v1.py` ตรวจ hashes ก่อนสรุปผล

## ผลหลักที่ตอบ reviewer

- **E0, ไม่มี overhead/outage:** event stream หลังตัด `run_start` และ substantive metrics ตรงกัน **360/360 คู่**. ผลนี้ยืนยันว่า control เปลี่ยนเฉพาะเส้นทางตัดสินใจ ไม่ได้แอบเพิ่ม candidate edges หรือเปลี่ยนต้นทุน เมื่อไม่คิด communication/failure จะไม่มีเหตุให้คุณภาพ/ต้นทุนต่างกัน
- **E2_BELT, shared belt outage:** ตรงกัน **360/360 คู่**. ConveyorFlow ยังพึ่ง shared belt/atomic store จึงไม่ควรอ้างว่าไม่มี single point of failure ทั้งระบบ
- **E2_COORD, synthetic coordinator outage ช่วง 40–50% ของ horizon:** 360 คู่; CF − Central-Matched ในภาพรวมเป็น verified **tasks** throughput `+0.03898 tasks/tick`, job-completion rate `+0.04722`, simulated cost per completed job `−1.8215 cost units`, task dead-letter rate `−0.02739`, unsettled rate `−0.01443`, terminal-flow P95 `−102.39 ticks`, utilization `+0.07797`. ทุก 18 strata มีทิศทางเดียวกันใน throughput, job completion และ cost-per-completed-job; ตารางแยก stratum/95% paired-bootstrap CI อยู่ใน `summary.csv`

ตัวอย่าง high load, R0: Adult throughput `+0.06588 tasks/tick` (95% paired-bootstrap CI `+0.05963` ถึง `+0.07176`); Beijing `+0.03365` (`+0.02926` ถึง `+0.03796`); Bugs2Fix simulated workload `+0.02972` (`+0.02343` ถึง `+0.03633`). ค่า CI เป็น descriptive ไม่ปรับ multiplicity และไม่ได้ใช้ประกาศความเหนือกว่าทั่วไป

## การตีความที่อนุญาต

ผล E0 แสดงว่า **decision locus เพียงอย่างเดียว** ไม่ทำให้ผลต่างใน simulator นี้เมื่อไม่มี overhead/failure. ผล E2_COORD แสดงผลของการเอา coordinator ออกจาก failure path **ภายใต้ outage ที่ผู้วิจัยกำหนดในแบบจำลอง** เท่านั้น; ไม่ใช่หลักฐานว่า MFEC หรือระบบ production มี outage 10% และไม่ใช่การทดสอบความทนทานของ queue/broker ทั้งระบบ. `CENTRAL_FIT` เดิมยังเป็น operational policy comparator ไม่ใช่ matched authority control

ตัวชี้วัด `verified_throughput` ใน simulation คือ verified **tasks** ต่อ tick; job-completion rate เป็นสัดส่วน **jobs** ที่เสร็จครบ. Simulated cost units ไม่ใช่ USD ของผู้ให้บริการ. การทดลองนี้ยังไม่ปิด ecological gap ของ ML pipeline/repository bug fix; ห้าม pool กับ microtask Real-LLM เดิมหรือเขียนเป็นผล real-model

## สิ่งที่ยังต้องทำ

1. วัด route latency จาก prototype แล้ว freeze ก่อน `E1`; หากไม่ได้วัด ห้ามใส่ค่า delay สมมติเป็นผลหลัก
2. ทำ end-to-end MFEC ML pipeline และ BugsInPy repair หลัง sandbox/container และ API credential พร้อม โดยใช้ hidden validators ที่เตรียมแยกไว้
3. ทำ sensitivity agent outage และ/หรือ failover ตาม protocol ก่อนอ้าง availability ที่กว้างกว่าชั้น coordinator
