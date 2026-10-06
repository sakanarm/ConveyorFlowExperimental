# v2.3 matched architecture simulation preregistration

สถานะ: ลงแผนก่อนเปิดผล v2.3; ข้อมูลนี้ไม่แก้การทดลองหลักเดิม 22,500 runs

## วัตถุประสงค์

แยก `decision locus` จาก `candidate set/global matching` ในการเทียบ CF-Fit กับ Central-Matched. CF-Fit ใช้ local volunteer หนึ่ง bid ต่อ agent; Central-Matched รับและ relay bid **ชุดเดียวกัน** พร้อม arbitration เดียวกัน ไม่ประเมินงานเพิ่มเติมและไม่เปลี่ยน fit/stand-down/fallback. `CENTRAL_FIT` เดิมยังเป็น operational baseline อื่น ไม่ใช่ control ของ authority effect

## Design ที่ล็อก

ใช้ `config_matched_v1.json`: seeds 1000–1019, workloads Adult/Beijing/Bugs2Fix, load low/medium/high, R0/R1, H1 four-agent team, 200 jobs/run, K=8, frozen LLM difficulty labels. 1,080 paired cells × 2 policies = 2,160 runs. ทุกคู่ใช้ seed, task stream, potential outcomes และ resource parameters เดียวกัน

- `E0`: no overhead/no outage. **Gate:** หลังตัด `run_start` metadata แล้ว event streams และ substantive metrics ต้องตรงกันทั้งหมด 360 คู่; หากไม่ผ่าน หยุดวิเคราะห์
- `E2_COORD`: coordinator-only outage ตั้งแต่ 40% ถึง 50% ของ fixed run horizon. ใน central arm agent ยัง assess/bid และจ่าย assessment cost แต่ claim ไปถึงงานไม่ได้; CF arm ไม่มี coordinator ตัวนั้น. นี่เป็น **synthetic stress test** ไม่ใช่ค่า failure rate จริงของ MFEC
- `E2_BELT`: shared belt unavailable ช่วงเวลาเดียวกัน กระทบสอง arm เหมือนกัน. เป็น negative control ต่อข้ออ้างว่า CF ไม่มี shared failure point; event streams และ substantive metrics ต้องตรงกัน 360 คู่

ไม่มี `E1` latency ในชุดนี้ เพราะยังไม่ได้วัด latency จาก prototype จริง; ห้ามสมมติค่า delay แล้วใช้เป็นผลหลัก. การทดลอง E1 ต้อง freeze empirical distribution แยกก่อนรัน

## Outcomes และวิเคราะห์

Primary: verified throughput, cost per completed job, job completion rate. Guardrails: dead-letter, unsettled, terminal-flow P95, productive utilization. รายงานความต่าง `CF − Central-Matched` ภายใน paired cell; E0/E2_BELT เป็น parity checks ไม่มี p-value. E2_COORD รายงาน effect size และ 95% percentile paired-bootstrap CI ตามแต่ละ workload × load × resource regime; ปรับ multiplicity หากทดสอบนัยสำคัญหลาย scenario. ไม่รวม metrics เป็นคะแนนเดียวและไม่อ้าง fault tolerance ทั่วระบบ

หน่วยทำซ้ำคือ seed stream 20 ค่าในแต่ละ scenario; task ภายใน run ไม่ใช่ independent replicates. ค่า cost per completed job ที่ไม่มี completed job จะรายงานเป็น undefined/infinite พร้อมจำนวน zero-success แทนการละทิ้ง run

## Audit และขอบเขตคำอ้าง

บันทึก config/source SHA-256, event hash ต่อ run, parity check, metrics CSV, paired analysis และซอฟต์แวร์เวอร์ชัน. การทดสอบนี้ยังเป็น simulation ที่ใช้ assumed success/cost functions. แม้ E2_COORD ทำให้ CF ทน outage ของ allocation coordinator ได้ดีกว่า ก็สรุปได้เฉพาะ failure boundary ที่จำลองนั้น. Shared belt outage อาจหยุดทั้งสอง arm

ผลนี้ **ไม่ทดแทน** end-to-end Real-LLM pipeline/bugfix workstream และห้ามเพิ่มลง manuscript ก่อนการรันและตรวจผลจริง
