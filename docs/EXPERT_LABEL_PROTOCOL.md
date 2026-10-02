# Role-Conditioned LLM Difficulty Annotation Protocol

## Purpose

# Evidence status and claim

สร้าง **LLM-derived operational difficulty labels** สำหรับ Main Simulation โดยไม่ใช้ราคา ชื่อรุ่น
allocation outcome หรือ simulation pass/fail เป็นตัวช่วยตัดสิน

ห้ามเรียก labels ชุดนี้ว่า human-expert ground truth หรือ independent expert ratings ในบทความ
เพราะทั้งสามรอบมาจาก underlying model เดียวกัน แม้จะแยก context และบทบาทก็ตาม

## Items

ใช้ task-template variants ครบ 304 รายการ:

- Adult ML: 16 variants × 7 stages = 112
- Beijing ML: 16 variants × 7 stages = 112
- Bugs2Fix: 16 variants × 5 stages = 80

แต่ละ LLM evaluation pass เห็น workload context, variant context, stage, skill, dependencies และ task description
และ corpus-level characteristics แต่ไม่เห็น provisional difficulty, Agent level,
policy result หรือ label ของอีกคน

## Role-conditioned passes

- Pass 1: ML Methodologist เน้น data/modeling assumptions และ reasoning burden
- Pass 2: Software Reliability Reviewer เน้น dependency, failure modes และ verification burden
- Pass 3: Workflow/Resource Reviewer เน้น scope, coordination และ operational execution burden
- ทั้งสาม pass ใช้ underlying model เดียวกัน แต่ใช้ isolated context, shuffled order และห้ามอ่าน label ของ pass อื่น
- ให้ Difficulty 1/2/3, failure impact 1/2/3 และ confidence 1-5
- บันทึกเหตุผลสั้น ๆ สำหรับ D1/D3 และกรณี confidence <=2

## Difficulty anchors

- D1: ขั้นตอนตรงไปตรงมา ความไม่แน่นอนต่ำ ตรวจผลได้ชัด และ failure impact จำกัด
- D2: ต้องวิเคราะห์/เลือกวิธี มี ambiguity หรือ integration ปานกลาง
- D3: reasoning หลายขั้น, ambiguity สูง, debugging/model-risk สูง หรือ failure กระทบ downstream มาก

Difficulty และ failure impact ต้องกรอกแยกกัน ห้ามให้ผลกระทบสูงบังคับเป็น D3 โดยอัตโนมัติ

## Agreement gate

- รายงาน pairwise exact agreement, adjacent agreement และ quadratic-weighted Cohen's kappa
- acceptance target: minimum pairwise weighted kappa >= 0.70 และทุก difficulty class มีอย่างน้อย 10%
- disagreement ระยะ 2 ระดับต้อง adjudicate ทุก item
- หาก kappa < 0.60 ให้หยุด แก้ rubric และใช้ holdout items รอบใหม่
- ช่วง 0.60-0.69 ให้ adjudicate พร้อมบันทึกเหตุผลและส่งที่ปรึกษาตัดสินก่อน Main

## Freeze rule

หลัง adjudication ให้ export `llm_difficulty_labels_frozen.csv`, บันทึก SHA-256 และวันที่
แล้วห้ามแก้ระหว่าง Main หากต้องแก้ให้สร้าง version ใหม่และ rerun Main ทั้งชุด

## Manuscript claim

"Task difficulty was operationalized using a reproducible, role-conditioned LLM
annotation panel. Three blinded evaluation passes were elicited from the same
underlying model under distinct reviewer roles, followed by rule-based consensus
and a separate adjudication pass. These annotations are design inputs rather than
human-validated external ground truth."

Limitations ต้องระบุ correlated-error, prompt sensitivity และไม่มี human validation
พร้อมทำ sensitivity analysis ต่อ alternate difficulty mappings
