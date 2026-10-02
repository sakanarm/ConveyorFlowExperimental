# รายงาน Role-Conditioned LLM Difficulty Annotation

## สถานะ

**PASS สำหรับ operational annotation gate** และ adjudication เสร็จครบ แต่ไม่ถือเป็น
human-expert validation หรือ external ground truth

## วิธี

- 304 task-stage × data-stratum items
- 48 variants ที่ derive จาก public corpora จริง: Adult 16, Beijing 16, Bugs2Fix 16
- 3 blinded role-conditioned passes จาก underlying model เดียวกัน
- บทบาท: ML Methodologist, Software Reliability Reviewer และ Workflow/Resource Reviewer
- ให้คะแนน rubric 5 มิติ 0–2 แล้ว map total 0–3 เป็น D1, 4–6 เป็น D2, 7–10 เป็น D3
- แยก failure impact ออกจาก difficulty
- Senior Methods Adjudicator ตัดสินทุกข้อที่ไม่เป็นเอกฉันท์ โดยไม่เห็นผล Simulation

## Agreement

| Pair | Exact | Adjacent | Quadratic-weighted κ |
|---|---:|---:|---:|
| ML–Reliability | 0.829 | 1.000 | 0.823 |
| ML–Workflow | 0.783 | 1.000 | 0.799 |
| Reliability–Workflow | 0.770 | 1.000 | 0.793 |

Minimum overall pairwise κ=0.793 ผ่าน gate 0.70 มี 94/304 รายการที่ไม่เป็น
เอกฉันท์และ adjudicate ครบ 94 รายการ โดย 17 รายการตัดสินต่างจาก mechanical
majority/consensus

Subgroup diagnostic ที่ต้องรายงาน: Beijing ของคู่ Reliability–Workflow มี κ=0.628
จึงอยู่ระดับ review แม้ overall gate ผ่าน ประเด็นนี้จัดการด้วยการรายงานตรง ๆ และ
lower/upper mapping sensitivity ไม่ตีความว่า agreement รวมพิสูจน์ validity

## Frozen result

| Difficulty | Items | Share |
|---|---:|---:|
| D1 | 52 | 17.1% |
| D2 | 113 | 37.2% |
| D3 | 139 | 45.7% |

- primary frozen SHA-256: `56207cd87a28ab221911c2bf07ee0cf6f8ec6547bab7880fc5ef268ad24b2add`
- lower mapping: 47 labels ต่างจาก primary; SHA-256 `92a15a89f5779213d97dfd472e399572eadbd703ea36450b5d5ec409c6f04e27`
- upper mapping: 47 labels ต่างจาก primary; SHA-256 `7519b662625614a8a87de4e05a9c4f6f6442443f82d0e37d9b9af997aeb02a86`

## Claim ที่อนุญาต

> Task difficulty was operationalized using a reproducible, role-conditioned LLM
> annotation panel. Three blinded evaluation passes were elicited from the same
> underlying model under distinct reviewer roles, followed by rule-based consensus
> and a separate adjudication pass. These annotations are design inputs rather than
> human-validated external ground truth.

## Engine integration

Main ใช้ `difficulty_source=frozen_llm` และบันทึก label-file hash ใน config/run
artifacts ทุกครั้ง Lower/upper mappings ใช้เฉพาะ robustness subset
`ANNOTATION_SENSITIVITY` ห้ามแทน primary mapping หลังเห็นผล

## Literature basis and limitation

LLM-based structured evaluation มี precedent เช่น G-Eval แต่ LLM judges มี documented
bias และความไม่เสถียร จึงต้องใช้ claim แบบจำกัดขอบเขต:

- Liu et al. (2023), G-Eval: https://aclanthology.org/2023.emnlp-main.153/
- Chen et al. (2024), Humans or LLMs as the Judge?: https://aclanthology.org/2024.emnlp-main.474/

Role prompting ไม่ทำให้สาม pass กลายเป็น independent raters ข้อสรุปเกี่ยวกับ absolute
difficulty จึงเป็น simulation-conditional

