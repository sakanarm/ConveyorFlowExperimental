# ผล CF‑Fit เทียบ Central‑Rule‑Matched: FastAPI exploratory pair

วันที่ 13 ตุลาคม 2026; **รอบนี้เสร็จและ independent audit ผ่าน** แต่เป็น adaptive, repair-only, single-repository pair ไม่ใช่ prospective v2.6 main E2.

## เหตุผลและวิธี

หลัง v2.6 FastAPI diagnostic พิสูจน์ว่าทั้ง provider และ container verifier เรียกได้จริง ผู้วิจัยต้องการทดสอบ **ตำแหน่งผู้ตัดสินใจเลือกงาน** โดยตรงก่อน. จึงตรึงงาน `fastapi_8:repair` บน READY belt เดียวกัน, 3 agent/profile เดิม, prompt public-test amendment เดิม, image/verifier เดิม, seed, fit/stand-down, CAS, horizon และ provider settings เหมือนกันทั้งสอง arm. Central‑Rule‑Matched ให้ coordinator process ใช้ rule เดียวกันก่อนเสนอ claim; CF‑Fit ให้ agent process ประเมินเอง. มีหนึ่ง task และหนึ่ง provider request ต่อ arm, ไม่ retry. Lock SHA-256 คือ `d369f5c5e8fe03023c01a3374f913f23ab33c9f9290a256e90739220bf349a7e`; lock ถูกสร้างก่อนสอง calls.

เคสนี้ **เคยใช้ใน diagnostic** แล้วและไม่ใช่ held-out case. เหตุผลที่เลือกคือ `fastapi_8` ผ่าน public eligibility และ audit พบว่า allowed edit scope ครอบคลุมตำแหน่ง public reference fix (ต่างจาก `fastapi_11` ที่ instrument scope miss). การเลือกหลังเห็น diagnostic ทำให้ต้องเรียกผลนี้ว่า exploratory อย่างชัดเจน.

| Arm | ผู้ตัดสินใจ | Agent/โมเดล slot | Verified jobs | ผล response | Input/output tokens | Execution time |
|---|---|---|---:|---|---:|---:|
| Central‑Rule‑Matched | coordinator process | A1/agent_1 | 0/1 | empty, finish=`length` | 9,595 / 4,096 | 34.03 s |
| CF‑Fit | A1 agent process | A1/agent_1 | 0/1 | empty, finish=`length` | 9,595 / 4,096 | 36.45 s |

ทั้งสอง arm ได้ unique provider request IDs, ตัดสินใจเลือก A1 เหมือนกัน, และงานสิ้นสุด `DEAD_LETTER`. Verified throughput = 0 ทั้งคู่; verified task-completion time และ cost per verified job **นิยามไม่ได้** เพราะไม่มีงานผ่าน. Gateway คืน response-cost units 0.003429228 (Central) และ 0.0024915 (CF) แต่ไม่ยืนยันสกุลเงินหรือ billing จึงห้ามเรียกว่า USD/เงินจริง หรือสรุปว่า CF ถูกกว่า. เวลาประมวลผลของสอง requests ต่างกันตาม gateway/LLM stochasticity; 1 pair ไม่ใช่หลักฐานว่า architecture ใดเร็วกว่า. เห็นเพียงว่า decision actor ต่างกันจริงโดย rule และตัวเลือกเดียวกัน.

Independent audit: `audit_fastapi_paired_exploratory_v1.py` ตรวจ frozen dependencies, prompt hash, distinct provider IDs, append-only event ledgers, coordinator/agent process actor, atomic-claim uniqueness, response และ terminal state; ผลอยู่ `fastapi_paired_exploratory_v1/audit_capsule_v1.json`. Raw request/response/provider/ledger อยู่ `D:\ConveyorFlowRuntime\v2_6\fastapi_paired_exploratory_v1`.

## ตอบ reviewer ได้แค่ไหน

รอบนี้แสดงว่า **ทั้งสอง allocation path ถูกเรียกใช้กับ Real‑LLM และ verifier จริง** โดยเปลี่ยนผู้คำนวณ rule จาก coordinator เป็น agent. แต่ผลลัพธ์ 0/1 ต่อ arm ไม่แสดงประโยชน์ด้าน success, throughput, time หรือ cost; ไม่มี ML pipeline, มีเพียงหนึ่ง repository ที่เคยเปิดผลแล้ว และไม่มีการ inject coordinator/shared-belt faults. จึง **ยังไม่ปิด Major Revision** เรื่อง mixed real work, generalizability หรือผลเชิงสาเหตุของ decentralization. ไม่ควรนำ 2 API calls ไปนับเป็น n=2 independent projects หรือ pool กับ v2.6 prospective main.

งานต่อที่อยู่ใน scope เดิม: source-qualify repositories อิสระและ ML corpora ตาม `MAJOR_REVISION_CLOSURE_PROTOCOL_TH.md`, ตรึง mixed blocks/ability ก่อนเห็นผล, แล้วรัน E2 ทั้ง CF‑Fit/Central‑Rule‑Matched/Static‑Owners; ทำ E1 matched fault-domain แยก เพื่อจำกัด claim เรื่องการลด dependency ของ coordinator เฉพาะ decision layer. ไม่แก้ผลล้มเหลวนี้ด้วยการผ่อนเกณฑ์ย้อนหลัง.
