# ผลขยาย Real-LLM v2.5: paired recovery สอง block

สถานะ 11 ตุลาคม 2026: `V25_RECOV_01` และ `V25_RECOV_02` จบและผ่าน independent audit ทั้งคู่ ผลนี้เป็น **exploratory extension** หลังเห็นผล v2.4 ไม่ใช่ confirmatory sample ใหม่ และไม่รวม block `V25_PAIR_01` ที่เกิด long-path instrument failure หลังเริ่ม 2 provider calls. เก็บหลักฐานความผิดพลาดเดิมไว้และไม่เติมผลที่หาย.

## งานและตัวเทียบ

แต่ละ block มีงานสองชนิดบน READY belt เดียวกัน: ML pipeline 1 งานและ repository repair 1 งาน. ใช้ทีม 3 agents, verifier และ observation horizon 3,600 วินาทีเหมือนกัน. `CF_FIT` ให้ agents เลือก/stand down ใน process ของตน; `CENTRAL_RULE_MATCHED` ใช้กติกา fit เดียวกันแต่ตัดสินใจใน coordinator; `STATIC_OWNERS` กำหนดเจ้าของล่วงหน้า. หน่วยเปรียบเทียบคือ **source-paired mixed block** ไม่ใช่ stage, bug test หรือ API call.

| Block / sources | CF-Fit | Central-Rule-Matched | Static-Owners |
|---|---:|---:|---:|
| Bank Marketing + Black: verified jobs / 2 | 0 | 0 | 0 |
| Covertype + PySnooper: verified jobs / 2 | 1 | 1 | 1 |
| Total verified jobs / 4 | 1 | 1 | 1 |
| Full ML pipelines / 2 | 0 | 0 | 0 |
| Repository repairs / 2 | 1 | 1 | 1 |
| Provider calls in audited blocks | 7 | 7 | 8 |

Block แรกมี 12 calls. Bank ingest/preprocess ผ่านในแต่ละ arm แต่ train ไม่ผ่าน hidden quality/contract; Black repair ไม่ผ่าน visible test หรือ output ไม่สมบูรณ์. Block ที่สองมี 10 calls. PySnooper repair ผ่านทั้งสาม arm. Covertype ของ CF-Fit และ Central ผ่าน ingest แต่ preprocess ไม่ผ่าน stage contract; Static ผ่าน ingest/preprocess แต่ train ไม่ผ่าน stage contract. ดังนั้น v2.5 **ไม่ได้** เพิ่มตัวอย่าง full ML pipeline ที่ LLM ทำสำเร็จ; หลักฐาน full-pipeline ที่เคยมีมาจาก v2.4 คนละ cohort.

Throughput ของ block แรกเท่ากับ 0 jobs/hour ทุก arm; block ที่สองเท่ากับ 1 jobs/hour ทุก arm ภายใต้ horizon เดียวกัน. งาน verified ใน block ที่สองมี completion time 101.99 s (CF-Fit), 13.34 s (Central), และ 152.22 s (Static). เป็นงาน PySnooper เพียงงานเดียวต่อ arm และ agent/model ที่ได้รับงานต่างกัน จึงไม่ใช่หลักฐานทั่วไปว่า Central เร็วกว่า. Cost per verified job ของ block แรก **นิยามไม่ได้** เพราะ verified jobs เป็นศูนย์; block ที่สอง provider รายงาน 0.01749756, 0.01564275, 0.024757002 ตามลำดับ แต่ **ยังไม่ยืนยันหน่วยเงิน/ยอดเรียกเก็บจริง**. ห้ามใช้เป็นข้อสรุป monetary cost efficiency.

## ตัดสินความพร้อมเชิงวิชาการ

ผล v2.4 ซึ่งมี 11 audited paired blocks บน 4 repositories/2 ML corpora พบ CF-Fit 17/22, Central 14/22, Static 18/22 verified jobs; ควรรายงานเป็น cohort เดิม ไม่ pool กับ v2.5 โดยไม่มี protocol รองรับ. v2.5 เพิ่ม source ใหม่เป็น Black/PySnooper และ Bank/Covertype แต่ยังมีเพียง 2 blocks; 22 calls ไม่ใช่ 22 หน่วยอิสระ. ผล v2.5 มีประโยชน์ในการแสดงว่า framework ทำงานกับงานใหม่และเผย failure modes แต่ **ยังไม่ปิด population precision, equivalence, monetary cost หรือ system-wide fault-tolerance concern**. ความต่างที่เกิดจาก decision locus ก็ยังมี provider latency และ dynamic assignment เป็นส่วนของ pathway จึงไม่ควรใช้คำว่า isolated pure causal effect.

ขั้นต่อไปให้อยู่ใน scope: (1) เพิ่ม *source projects* และ ML corpora ที่ไม่ซ้ำภายใต้ outcome-blind preflight/lock และ gold-free verifier ก่อนเรียก LLM, (2) freeze วิธีวิเคราะห์ระดับ cluster/precision ก่อนรอบขยาย, (3) ถ้า billing export จาก MFEC ยังไม่ได้ ให้ตัด monetary real-LLM claim และแสดง tokens/provider-cost units แยก, (4) อัปเดต IEEE/AJSTR จากผล audit พร้อมผลลบและข้อจำกัด ไม่แก้ prompt/เกณฑ์ตามผลย้อนหลัง. การเพิ่มจำนวน calls บน source เดิมอย่างเดียวไม่แก้เรื่องความเป็นอิสระของข้อมูล.

หลักฐานที่ตรวจซ้ำได้: `paired_recovery_lock_v1.json`, `results/paired_recovery_audits_v1/V25_RECOV_01.json`, `results/paired_recovery_audits_v1/V25_RECOV_02.json`, `results/paired_recovery_analysis_v1.json`, และ `results/paired_long_path_failure_v1.json`. Raw execution อยู่ใน short-path D: runtime โดย audit caps ระบุ SHA-256 ของ allocation ledgers, summaries, prompts, responses และ verifier records.

## สถานะ source ถัดไป (ยังไม่ใช่ผล Real-LLM)

`youtube-dl` bug 27 เป็น repository project ใหม่ซึ่งเป็น **case แรกตาม hash-ordered queue** ที่ผ่าน public buggy-fail/fixed-pass. Candidate image มี buggy source แต่ไม่มี fixed tree, protected tests หรือ Git metadata; independent candidate audit ผ่าน. Visible test ล้มบน buggy และผ่านบน fixed, ขณะที่ public regressions ที่เลือกก่อนดู outcomes ผ่านตรงกัน 10/10 ทั้งสอง tree. ไม่มี LLM call สำหรับเคสนี้. Preflight v1 หยุดก่อนสร้าง container เพราะ Python metadata filter 3.8 ไม่ตรง case 3.7; v1b เป็น amendment แยกที่เปลี่ยนเพียง filter โดยคง queue/test/image. Interpreter จริงยังเป็น 3.8.20 แทน historical 3.7.4 และต้องรายงาน environment deviation นี้. ยัง **ไม่นับ youtube-dl เป็น paired Real-LLM replicate** จนกว่าจะ freeze protocol/ability profile และรันครบสาม arm แล้ว audit.
