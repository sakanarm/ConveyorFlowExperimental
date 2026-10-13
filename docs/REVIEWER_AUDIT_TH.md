# ผลตรวจ Manuscript ในมุม Reviewer (Scopus Q2–Q3)

วันที่ตรวจ: 2 ตุลาคม 2026
คำแนะนำโดยรวม: **Major Revision ก่อนส่งวารสาร** แต่พร้อมสำหรับให้อาจารย์ที่ปรึกษาตรวจรอบถัดไป

## จุดแข็ง

1. Scientific story ชัดขึ้น: decentralized self-selection → capability heterogeneity → fit/stand-down → aging/fallback.
2. ไม่บังคับให้ CF-Fit ชนะทุก metric และรายงานผลเป็น trade-off ระหว่าง completion, cost, time, throughput และ utilization.
3. Simulation ใช้ paired seeds, common random numbers, multiplicity correction, event-ledger audit และ frozen design.
4. แยก simulation, Real-LLM main และ extension/boundary evidence อย่างระมัดระวัง.
5. ระบุข้อจำกัดของ role-conditioned LLM labels และไม่เรียกว่า independent human experts.

## Major comments ที่ต้องปิดก่อน submit

1. เพิ่มถ้อยคำ RQ1–RQ3 แบบเป็นทางการใน Introduction ให้ตรงกับหัวข้อ Results และระบุ estimand/metric ต่อ RQ.
2. เปลี่ยนหลักฐาน “pre-specified/frozen” ให้ตรวจสอบภายนอกได้ด้วย public commit/tag และ DOI-backed archive; hash ภายในอย่างเดียวไม่พอ.
3. อธิบายเหตุผล/ที่มาของพารามิเตอร์ simulation เช่น ability coefficients, arrival/load, churn, speed/token/cost mappings และเพิ่ม sensitivity หรือ calibration linkage.
4. ทำ human-expert validation ของ difficulty labels หรือคง framing ว่าเป็น machine-generated operational labels เท่านั้น.
5. Real-LLM มี 10 paired seeds และผู้ให้บริการเดียว จึงควรวางเป็น supplementary validation; ระบุวันเวลา, alias/metadata hash, price source และ confidence intervals ให้ครบ.
6. อธิบาย fairness ของ Central-Fit และ static controls ให้ชัด: information budget, visibility, scan window, computational overhead และสิทธิ์เข้าถึงข้อมูลต้องเทียบกันได้.
7. ทำ cost accounting ให้ตรวจสอบได้ว่ารวม retries, failed calls, assessor/verifier calls และ token source แบบใด.
8. Public reproducibility package ต้องมี README, environment lock, test commands, exact frozen configs, aggregate results, hashes และวิธีขอ/สร้างข้อมูลใหม่.

## Minor comments

- ใช้คำ Ability Rank 1/2/3 และ AR1–AR3 ให้สม่ำเสมอในข้อความ รูป และตาราง.
- แยก percentage points จาก relative percent โดยเฉพาะ completion ของ Real-LLM.
- ใช้ `prespecified` หรือ `pre-specified` แบบเดียวตลอดเล่ม.
- ลดประโยคยาวและรูปแบบ “not X but Y” ที่ซ้ำบ่อย; ปรับน้ำเสียงให้เป็นวิชาการธรรมชาติ.
- ระบุหน่วยและ denominator ของ task, case, job, run และ seed ในทุกตารางผล.
- ย้ายชื่อไฟล์ Draw.io จาก caption ไปส่วน Data/Code Availability หาก template ของวารสารไม่ต้องการรายละเอียด repository ใน caption.
- เติม affiliation/e-mail และตรวจ reference/DOI ทุกตัวก่อนส่งจริง.

## AI check

ไม่ควรใช้ AI detector เป็นหลักฐานว่า manuscript “เขียนโดย AI” เพราะผลตรวจไม่มีความน่าเชื่อถือเพียงพอสำหรับการตัดสินผู้เขียน งานนี้ควรผ่านการตรวจแบบ provenance-based ได้แก่:

- เปิดเผย AI-assisted labels และบทบาทของ AI ในการ drafting/coding/visual preparation ตาม policy ของวารสาร.
- ไม่เรียก role-conditioned passes ว่า human experts หรือ independent raters.
- เก็บ prompts, outputs, adjudication, hashes และ claim-to-evidence mapping.
- ตรวจ citation, ตัวเลข, terminology และ prose ด้วยมนุษย์รอบสุดท้าย.

## Verdict

Manuscript มี contribution และหลักฐานมากพอสำหรับพัฒนาเป็น paper ได้ แต่ยังไม่ควร submit จนกว่าจะปิดประเด็น public preregistration/archive, simulation calibration rationale, baseline fairness/cost accounting และ human-expert validation หรือจำกัด claim ให้ตรงกับหลักฐานปัจจุบัน.
