# v2.6 FastAPI Real-LLM diagnostic — รายงานผลภายใน 12 ตุลาคม 2026

## ขอบเขตและเหตุผล

ผู้วิจัยมีเวลาจำกัด จึงเปิดรอบ **bounded repository-repair feasibility** แยกจาก prospective 12-repository main cohort. สองเคส `fastapi_11` และ `fastapi_8` ของ **repository เดียว** ผ่าน buggy-fail/fixed-pass, gold-free candidate, public regression และ independent source audit ก่อนเรียก MFEC. คำถามของรอบนี้แคบมาก: LLM ที่ให้ผ่าน MFEC สามารถสร้าง exact-edit patch ซึ่งผ่าน public visible tests และ non-visible public regression tests พร้อม replay ใน Podman ได้หรือไม่. รอบนี้ **ไม่ทดสอบการจัดสรรงาน CF-Fit/Central-Fit/Static**, ไม่มี ML Build DAG และไม่ใช้ตอบ RQ1/RQ2 โดยตรง.

## วิธีการที่ตรึงก่อนเรียก LLM

- Lock `fastapi_llm_feasibility_v1/lock.json` และโค้ด runner ถูก push ก่อนคำขอแรก. เคส 2 × โมเดล 3 = 6 คู่ตามลำดับคงที่, หนึ่งคำขอต่อคู่, ไม่มี automatic retry เมื่อมี `request_started.json`.
- Candidate prompt มีเฉพาะ buggy production source ที่เลือกจาก public failure และส่วนท้ายของ public failure; fixed source ไม่อยู่ใน candidate หรือ prompt. โมเดลคืน JSON exact edits สำหรับ production files ที่อนุญาตเท่านั้น.
- Patch ถูกใช้และตรวจใน verifier container ที่แยกจาก candidate. ต้องผ่าน visible nodes, 3 public regression nodes ที่ตรึงก่อน outcome, แล้ว replay ทั้งสองชุด จึงจะเป็น `VERIFIED`. ภาพและ raw JUnit อยู่บน `D:\ConveyorFlowRuntime\v2_6`.
- โมเดลเป็น 3 deployments ใน `config.mfec_main_frozen.json`; `temperature=0`, output cap 16,384 และ timeout 600 วินาที. Ability Rank เดิมไม่ได้ recalibrate จากสองเคสนี้.

## ผลที่ audit ได้

Independent audit `audit_fastapi_llm_feasibility_v1.py` ตรวจครบ **6/6 request markers**, ledger-summary hashes, provider request IDs, response/patch hashes และ JUnit evidence; ดู `fastapi_llm_feasibility_v1/audit_capsule_v1.json`. ผลคือ **verified repair 0/6**: `tencent-hy3` กับ `glm-5.3-flash` คืนเนื้อหาว่างทั้งสองเคสหลังใช้ output cap (รวม 4 attempts), ส่วน `gpt-5-mini` สร้าง patch ได้ทั้งสองเคสแต่ visible tests ยัง fail (2 attempts). นี่เป็น **6 provider attempts ภายใน 2 bugs ของ 1 repository** ไม่ใช่ N=6 repositories หรือหลักฐานสถิติเรื่องความทั่วไป. รวม provider-reported input 77,148 tokens และ output 66,255 tokens. มี response-cost units รวม 0.063248938 แต่ไม่ระบุสกุลเงิน/ไม่ reconcile billing; **ห้ามเรียกว่า USD หรือ monetary cost/job**.

หลังเห็นผลดังกล่าวจึงทำ prompt amendment **แยกเวอร์ชัน** `run_fastapi_llm_prompt_amendment_v1.py`: เพิ่ม full public visible-test source และลด output cap เหลือ 4,096 สำหรับ `gpt-5-mini` บนสองเคสเดิม. Lock ถูกตรึงก่อน 2 คำขอใหม่. `audit_fastapi_llm_prompt_amendment_v1.py` ตรวจสองคำขอแล้ว: **verified repair 0/2**, ทั้งสอง patch ไม่ผ่าน visible tests. เนื่องจากเป็นการปรับหลังเห็นผล ห้าม pool เป็น 0/8 “first attempts” หรือใช้ประมาณ first-attempt rate; ให้รายงานแยกเป็น adaptive diagnostic. ใช้ provider-reported input 27,784 และ output 468 tokens ในรอบนี้.

## ตีความและข้อจำกัดสำหรับ manuscript

หลักฐานนี้ยืนยันว่า MFEC ถูกเรียกจริง, request identities/usage ถูกบันทึก, LLM สร้าง patch ได้บางคำขอ และ verifier container ปฏิเสธ patch ที่ไม่ผ่าน test ได้. **ไม่ได้ยืนยันว่า LLM ซ่อม FastAPI สำเร็จ**, ไม่ได้เพิ่ม independent repository project มากกว่าหนึ่ง, ไม่ได้ทดสอบ ML pipeline ใหม่ และไม่ได้เปรียบเทียบกลไก decentralized decision locus. จึงยัง **ไม่ปิด Major Revision concern** เรื่อง real executable success, source diversity หรือ CF-Fit vs Central-Fit. ห้ามใส่ 0/6 เป็นผลหลักของ RQ1 หรือเลือกเฉพาะผล v2.3–v2.5 ที่ดีแล้วละผลลบนี้ถ้าจะกล่าวถึง v2.6.

ถ้าจำเป็นต้องส่งเอกสารภายในคืนนี้ ให้ใช้ผล v2.3–v2.5 ตามขอบเขตเดิมและใส่ v2.6 นี้เป็น *exploratory stress-test/limitation* หรือเก็บเป็น supplementary audit เท่านั้น. Abstract/conclusion ต้องไม่กล่าวว่า v2.6 main completed หรือ Major Revision closed. ขั้นต่อไปในงานวิจัยจริงคือปรับ instrument/โมเดลก่อนคัด repository และ ML corpus ใหม่ตาม protocol โดยประกาศ amendment ก่อนเรียก LLM; ต้องไม่ยิงซ้ำ ID เดิมหรือปรับเกณฑ์ผ่านหลังเห็น outcome.
