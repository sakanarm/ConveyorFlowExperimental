# ผล Real-LLM ecological main v2.4 ที่ผ่าน independent audit

สถานะ ณ 11 ตุลาคม 2026: คิว v3 จบแล้วและสร้าง `results/main_resume_v3/analysis.json` (SHA-256 `5192a0fc3c67295161899f408b4c247fa1383c631cbf7ea9a8cc7b38a196810e`). Audit capsules ของ block 01, 02 และ 04–12 ครบ 11 block และทุกไฟล์มีสถานะ `v2_4_recovery_block_independently_audited`. จำนวน provider attempts ใน 11 block นี้เท่ากับ 159. Block 03 หยุดกลางทางหลังเริ่ม 9 คำขอ โดย 2 คำขอไม่ทราบ provider outcome; เก็บหลักฐานไว้ แต่ไม่เติมค่า ไม่ยิงซ้ำ และไม่ใช้ในการเปรียบเทียบแบบจับคู่. ดังนั้น **นี่ไม่ใช่การทดลอง 12 block ที่เสร็จครบ**.

## นิยามและผลที่อ่านได้ตรงจาก analysis

แต่ละ block ที่สมบูรณ์มี 2 jobs (ML pipeline 1 งานและ repository repair 1 งาน) และเปรียบเทียบ CF-Fit, Central-Rule-Matched และ Static-Owners บนงานเดียวกันภายใต้ observation window 3,600 วินาที. ตัวเลข throughput ด้านล่างคือจำนวน jobs ที่ verified ภายใน horizon หารด้วยเวลาสังเกตสะสม 11 ชั่วโมงต่อ arm; ไม่ใช่อัตราการให้บริการของประชากรงานทั่วไป. Provider cost เป็นหน่วยที่ provider รายงาน โดยสกุลเงินยังไม่ได้รับการยืนยัน.

| Arm | Verified / arrived | ML pipelines | Repository repairs | Verified jobs/hour | Provider attempts | Known cost units | Unknown-cost attempts |
|---|---:|---:|---:|---:|---:|---:|---:|
| CF-Fit | 17/22 | 9/11 | 8/11 | 1.545 | 52 | 0.316764190 | 1 |
| Central-Rule-Matched | 14/22 | 8/11 | 6/11 | 1.273 | 52 | 0.299882132 | 1 |
| Static-Owners | 18/22 | 9/11 | 9/11 | 1.636 | 55 | 0.283972888 | 3 |

CF-Fit ลบ Central-Rule-Matched มี paired mean difference ของ verified throughput +0.273 jobs/hour, completion time **เฉพาะงานที่ verified** +4.10 วินาที, busy utilization +0.00488 และ productive utilization +0.00562. CF-Fit ลบ Static-Owners มี throughput -0.091 jobs/hour, conditional completion time -141.09 วินาที, busy utilization -0.01490 และ productive utilization -0.00423. ค่าเวลาที่เปรียบเทียบคำนวณจาก subset ของงานสำเร็จซึ่งไม่เหมือนกันทุก arm จึงไม่แปลว่า CF-Fit ทำงานทุกประเภทเร็วขึ้น. Busy utilization รวมเวลารอ provider และ verification; ค่า busy สูงขึ้นไม่ใช่ประสิทธิภาพที่ดีขึ้นโดยอัตโนมัติ.

**ห้ามรายงาน cost per verified job ของทั้ง arm เป็นตัวเลขสมบูรณ์:** analysis ระบุค่าเป็น `null` เพราะมี unknown-cost attempts ในทุก arm. Complete-case paired cost contrasts มีเพียง 10/11 block สำหรับ CF-Fit เทียบ Central-Rule-Matched และ 7/11 สำหรับ CF-Fit เทียบ Static-Owners; ผลเหล่านี้อาจมี missingness bias และไม่ใช่คำตอบของต้นทุนรวม. ต้องรายงาน known provider cost และจำนวน unknown แยกกันตามตาราง ไม่แทน unknown ด้วยศูนย์หรือค่าเฉลี่ย.

Sensitivity ที่ตัด block 01 ซึ่งเคยมี partial v1 exposure เหลือ 10 complete blocks: CF-Fit verified 15/20, Central-Rule-Matched 12/20 และ Static-Owners 16/20. ทิศทางจำนวนงานสำเร็จยังเหมือนเดิม แต่ไม่ทำให้ผลเป็น population inference.

## ความหมายสำหรับ RQ และ claim

ผลชุดนี้เพิ่มหลักฐานเชิง ecological ว่ากลไก self-selection, capability-task fit และ stand-down สามารถใช้กับ ML DAG ที่รันจริงและการซ่อม repository ที่ผ่าน container verifier ได้. CF-Fit verified มากกว่า Central-Rule-Matched ใน cohort นี้ แต่ Static-Owners verified มากที่สุด. จึงเล่าเป็น **trade-off vector** ของ throughput, conditional completion time, utilization และ cost accounting ตาม RQ1 ไม่ใช้คำว่า CF-Fit เหนือกว่าทุกด้าน. การทดลองนี้ไม่ได้แยกผลของ stand-down เพียงองค์ประกอบเดียว และไม่ได้ตอบ RQ2 เรื่อง homogeneous เทียบ heterogeneous ด้วยตัวมันเอง; ต้องอ้างการทดลองเฉพาะของคำถามเหล่านั้นแยกต่างหาก.

Central-Rule-Matched ถือ fit rule, team, workload, verifier และ horizon ตามสัญญาการทดลองเดียวกัน แต่ real-time assignments และ provider latency อาจต่างกัน. ดังนั้น contrast นี้ลด confounding ของกติกา allocation ลง แต่ไม่พิสูจน์ผลเชิงเหตุของตำแหน่งผู้ตัดสินใจได้บริสุทธิ์ทั้งหมด. การไม่ใช้ global agent-task matcher ไม่เท่ากับระบบไร้จุดล้มเหลวรวม: READY belt, atomic claim store, verifier และ provider gateway ยังเป็น shared dependencies. ข้ออ้าง fault tolerance ต้องอาศัย failure-injection ที่จับคู่กติกาและจำกัด claim ที่ allocation-decision layer.

มีเพียง 4 source repositories และ 2 ML corpora ที่ใช้ซ้ำ; stages, retries, provider attempts และหลาย bugs ใน repo เดียวกัน **ไม่ใช่ตัวอย่างอิสระ**. Repository-cluster bootstrap intervals ใน `analysis.json` เป็น descriptive uncertainty จาก cluster ที่มีน้อย ไม่ใช่ population confidence intervals, equivalence test หรือ power guarantee. อย่านำค่า p หรือ CI ที่ไม่ครอบศูนย์ไปอ้างว่างานพร้อมตีพิมพ์โดยลำพัง. ถ้าต้องการข้อสรุปทั่วไปหรือ equivalence ต้องขยายด้วย source projects/datasets/cases ใหม่ภายใต้ lock และ sample-size/precision plan ใหม่ก่อนเรียก LLM.

## ข้อความ English ที่นำไปปรับใน Manuscript ได้

> In eleven independently audited paired blocks of executable ML-pipeline and repository-repair jobs, CF-Fit verified 17 of 22 jobs, the rule-matched centralized arm verified 14, and static ownership verified 18. Their observed verified throughputs were 1.545, 1.273, and 1.636 jobs per hour, respectively, under identical 3,600-second block horizons. Thus, local self-selection verified more jobs than the rule-matched centralized arm in this bounded cohort, while static ownership verified the most. Completion-time contrasts condition on different successful subsets. Provider cost per verified job could not be fully determined because one CF-Fit, one centralized, and three static attempts had unknown billing outcomes. One planned block was interrupted and excluded from paired analysis without retry or imputation. These findings describe an implementation-level trade-off, not population-level superiority, equivalence, or system-wide fault tolerance.

ก่อนแทรกใน IEEE/AJSTR ต้องรักษาผล v2.3 เป็น cohort ก่อนหน้า ไม่ pool กับ v2.4 โดยไม่มี protocol รองรับ; ปรับ Abstract, Method, Results, Discussion, Limitations, table/figure numbering และ reference-to-repository ให้สอดคล้องกัน. ฉบับ blind ต้องไม่มีชื่อผู้เขียน, อีเมล, ORCID หรือ GitHub handle ใน package metadata/links ที่เปิดเผยตัวตน. QA ใน Word ต้องตรวจรูป 5 ภาพ, สมการ 13 รายการ, header/footer, cross-references และทุกหน้าหลัง repagination. เอกสารนี้เป็น source-of-truth ของตัวเลข v2.4 แต่ไม่ได้แทน `analysis.json` หรือ audit capsules.
