# LLM Difficulty Annotation: Claim Boundary

## Claim allowed in the manuscript

> Task difficulty was operationalized using a reproducible, role-conditioned LLM
> annotation panel. Three blinded evaluation passes were elicited from the same
> underlying model under distinct reviewer roles, followed by rule-based consensus
> and a separate adjudication pass. These annotations are design inputs rather than
> human-validated external ground truth.

## สิ่งที่อ้างได้

- pipeline ทำซ้ำได้ เพราะเก็บ corpus hash, variant derivation, rubric, prompt/role,
  shuffled packet, raw rating, consensus, adjudication และ frozen-file hash
- agreement ระหว่าง role-conditioned passes วัดได้ด้วย pairwise weighted kappa
- labels ใช้ operationalize latent task difficulty สำหรับ Simulation และ S2 เท่านั้น
- robustness ตรวจด้วย lower/adjudicated/upper role-vote mappings และ D3-heavy stress

## สิ่งที่ห้ามอ้าง

- ห้ามใช้คำว่า human expert, independent expert หรือ external ground truth
- agreement สูงไม่เท่ากับ validity สูง เพราะ passes ใช้ underlying modelเดียวกัน
- ห้ามอ้างว่า role prompting กำจัด correlated error, prompt sensitivity หรือ model bias
- ห้ามอ้าง generalization ไปยังการทำงานของ LLM จริงจาก Simulation เพียงอย่างเดียว

## Required limitation sentence

> Because all annotation passes used the same underlying LLM, their errors may be
> correlated; role-conditioned agreement measures procedural stability rather than
> independent validation. No human calibration set was available, so conclusions
> involving absolute difficulty levels are interpreted as simulation-conditional.

## Recommended terminology

ใช้ `LLM-derived difficulty label`, `role-conditioned evaluation pass`,
`operational difficulty` และ `simulation-conditional evidence`
