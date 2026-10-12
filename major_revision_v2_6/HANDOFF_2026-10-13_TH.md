# ConveyorFlow v2.6 handoff — 13 ตุลาคม 2026

เอกสารนี้เป็น checkpoint สำหรับคนรับช่วงงาน **ไม่ใช่ผลวิจัยที่ตรวจสอบเสร็จแล้ว**. ห้ามอ่านจำนวน API calls เป็นจำนวนตัวอย่างอิสระ และห้ามประกาศว่า Major Revision ปิดแล้วจากรอบ exploratory.

## พื้นที่จัดเก็บ

- **C: โค้ด/แผน/lock/เอกสาร Git**: `C:\Users\Sakan P\Desktop\Personal\ปเอก\2_Other Projects\9_ConveyorFlow A Decentralized Volunteer-Based Task Allocation Framework for Heterogeneous LLM Agents_กำลังทำ\v2` เป็น Git worktree. โฟลเดอร์หลักของรอบนี้คือ `major_revision_v2_6`. Worktree มีไฟล์อื่นที่ผู้ใช้แก้ไว้จำนวนมาก; **อย่า reset/clean/delete ทั้ง repo**.
- **D: raw execution evidence**: `D:\ConveyorFlowRuntime\v2_6`. FastAPI diagnostic เดิมอยู่ใน `fastapi_llm_feasibility_v1` และ `fastapi_llm_prompt_amendment_v1`. รอบ paired ใหม่อยู่ใน `fastapi_paired_exploratory_v1`; ข้างในมี prompt ที่ hash ตรึงและ directory แยก arm.
- **D: Ubuntu WSL/Podman image store**: `D:\WSLDistros\Ubuntu\ext4.vhdx`. Backup ก่อนย้ายอยู่ `D:\WSLBackups\ConveyorFlow_20261012\Ubuntu_pre_move_20261012.vhdx`. ไม่ลบ backup หรือ image store โดยไม่ตรวจ.
- `MFEC_LITELLM_API_KEY` **ไม่อยู่ในเอกสาร/lock/Git**; ส่งผ่าน environment ของ process เท่านั้น. หากเครื่องไม่มี credential ต้องให้เจ้าของเครื่องตั้งเองโดยไม่พิมพ์ค่าใน log/chat.

## หลักฐานก่อนหน้าที่ใช้ได้/ไม่ได้

- Protocol ของ prospective main: `major_revision_v2_6/MAJOR_REVISION_CLOSURE_PROTOCOL_TH.md`. ยังไม่ freeze cohort 12 repositories × 2 bugs และ 6 ML corpora. รอบนี้ **ไม่ใช่ main E2**.
- Source eligibility: FastAPI สองเคสผ่าน public buggy/fixed และ regression gate; capsule `fastapi_two_candidate_gates_capsule_v1.json`. Scrapy ยังเป็น metadata-only queue.
- FastAPI Real-LLM diagnostic ที่ audit แล้ว: 6 first attempts ได้ 0 verified; prompt amendment แยก 2 adaptive attempts ได้ 0 verified. `fastapi_11` มี post-outcome instrument scope miss; **อย่าใช้เป็น clean model-failure claim**. ดู `FASTAPI_REAL_LLM_DIAGNOSTIC_TH.md`.
- v2.5 paired recovery บน D: (`D:\ConveyorFlowRuntime\v2_5\paired_recovery_v1`) เคยรันครบแล้ว. โฟลเดอร์ C: ชื่อ `V25_PAIR_02` ที่เหมือนยังไม่เริ่มเป็น long-path predecessor ของ recovery **ไม่ใช่ independent new block**; ห้ามยิงซ้ำเพื่อเพิ่ม N.

## รอบ paired ใหม่ที่เริ่ม 13 ตุลาคม

- Runner: `major_revision_v2_6/run_fastapi_paired_exploratory_v1.py`.
- Lock: `major_revision_v2_6/fastapi_paired_exploratory_v1/lock.json`, SHA-256 `d369f5c5e8fe03023c01a3374f913f23ab33c9f9290a256e90739220bf349a7e` ตอน freeze ก่อน provider call.
- งาน: `fastapi_8:repair` เคสเดียวบน READY belt; 3 agents จาก profile เดิม; difficulty rank 2; arm order `CENTRAL_RULE_MATCHED` แล้ว `CF_FIT`; `temperature=0`, output cap 4096, timeout 600 s, max 1 provider call/arm, no retry. Prompt เป็น public-test amendment เดิมและ hash เดียวกันทั้ง arms. Candidate/verifier Podman images ถูก pin.
- **ข้อจำกัดล่วงหน้า**: เคส FastAPI เคยใช้ใน diagnostic แล้ว; มี repository อิสระเพียง 1 แห่ง; repair-only ไม่มี ML DAG; จึงเป็น adaptive exploratory paired comparison เท่านั้น ไม่สามารถแทน prospective mixed E2 หรือปิด generalizability gap.
- **สถานะล่าสุด:** ทั้ง `CENTRAL_RULE_MATCHED` และ `CF_FIT` ยิง MFEC จริงและจบแล้ว (1 provider request/arm). Independent audit ผ่าน; capsule อยู่ `fastapi_paired_exploratory_v1/audit_capsule_v1.json`. ทั้งคู่เลือก A1/agent_1, ได้ response ว่างโดย `finish_reason=length` ที่ output cap 4096, จบ `DEAD_LETTER`, verified 0/1 ต่อ arm. **อย่ารัน `--run-next` เพื่อเพิ่ม N**; runner จะข้าม arm ที่จบแล้ว. ดูผล/ข้อจำกัดใน `FASTAPI_PAIRED_EXPLORATORY_RESULT_TH.md`.

## วิธีรับช่วงอย่างปลอดภัย

1. ตรวจ `D:\ConveyorFlowRuntime\v2_6\fastapi_paired_exploratory_v1\CENTRAL_RULE_MATCHED` และ `CF_FIT` ว่าแต่ละ arm มี `allocation/summary.json`, `events.jsonl`, `agent_*/request_started.json`, `provider.json`, `summary.json` หรือไม่. อย่าแก้/ลบ raw evidence.
2. รอบนี้จบแล้ว; คำสั่ง `--run-next` **ไม่ควรถูกใช้เพื่อยิงซ้ำ**. หากมีเหตุให้ตรวจทวนแบบ read-only ใช้ `wsl -d Ubuntu -u root --cd "$PWD" -- python3 major_revision_v2_6/audit_fastapi_paired_exploratory_v1.py` จาก repo `v2`; ไม่ต้องส่ง API key. หาก audit capsule มีอยู่แล้ว ไม่ใส่ `--seal` ซ้ำ.
3. Independent audit ตรวจ lock/code/prompt hashes, provider IDs, request markers, ledger chain, decision locus, CAS uniqueness, task state และ token/cost accounting แล้ว. `response_cost` จาก gateway ยังไม่ยืนยันสกุลเงินหรือ billing. Raw output และ evidence บน D: ต้องเก็บไว้ ไม่ควรนำขึ้น public GitHub โดยไม่ตรวจขนาด/สิทธิ์/ข้อมูลใน prompt.
4. หากจะปิด Major Revision ตาม protocol ยังต้อง source-diverse mixed ML+repository cohort และ E1 matched decision-locus/fault experiment บน traces ใหม่. ห้าม pool รอบ exploratory นี้กับ v2.6 main หรืออ้าง CF‑Fit ชนะทุก metric.

## Runtime note

ช่วงเริ่มรอบนี้พบ `podman image prune -f` ที่ orphan และค้างถือ image-store lock หลัง WSL บูต. ตรวจ PID/parent แล้วส่ง TERM เฉพาะ process นั้น; หลังจากนั้น `podman images` ตอบและ pinned FastAPI images ยังอยู่. ไม่มี provider call ก่อน freeze. ถ้า Podman ค้างอีก ให้ตรวจ process/lock และงานอื่นก่อนส่งสัญญาณ ไม่ prune image cache ใหม่แบบกว้าง.
