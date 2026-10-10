# v2.4 paid main instrument incident: V24_BLOCK_01

สถานะ 10 ตุลาคม 2026: บล็อกแรกภายใต้ execution lock SHA-256 `2718200d171765133b03b68f27c6c51d39c9e538ce54cbf7feb12d7ecaaa77f3` เริ่มจริงและส่งคำขอ MFEC 2 ครั้ง มี `request_started.json`, `provider.json` และ `response.txt` อย่างละ 2 ไฟล์ ไม่ใช่ dry run

- `CF_FIT / luigi_8 / agent_2` ได้ raw verifier status `VERIFIED` แต่ยังไม่ใช่ผลวิจัยที่ผ่าน parent-block independent audit
- `CF_FIT / MAIN_ADULT_01 / ingest` ได้ provider response และ generated source แล้ว แต่ `stage_gate.py` เรียก `run_ml_container.inside_workspace()` ซึ่งยังตรวจเฉพาะ `major_revision_v2_3/candidate_workspaces` ขณะที่ v2.4 ตรึง ML runtime บน `/mnt/d/ConveyorFlowRuntime/v2_4/ml_main_exact_edits_v1` จึงเกิด `ValueError` ก่อน container verification
- Parent block บันทึก `instrument_unresolved.json`; ไม่มี `raw_complete.json`, ไม่ได้รันครบสาม allocation arms, ไม่สามารถนำเข้า paired analysis หรือสรุป CF-Fit ชนะ/แพ้

สาเหตุเป็น integration/path guard ของเครื่องมือ ไม่ใช่ model failure. v2.3 `run_ecological_main_v1.py` ตั้ง `run_ml_container.WORKSPACES` ให้ตรง D runtime ก่อนรัน; v2.4 runner ลืมขั้นตอนนี้ ต้องทำ recovery ที่เพิ่ม fail-fast pre-provider workspace test, hash source ใหม่, และใช้ execution root/lock ใหม่โดยไม่แก้หรือลบหลักฐานบล็อกนี้ ห้ามเรียก `V24_BLOCK_01` ซ้ำภายใต้ lock เดิมหรือเติมข้อมูลในบล็อกค้าง ต้องเปิดเผย partial paid exposure นี้ใน audit trail และ manuscript หากนำชุด recovery ไปใช้

Raw evidence อยู่ที่ `D:\ConveyorFlowRuntime\v2_4` และยังไม่ใช่ publication results.
