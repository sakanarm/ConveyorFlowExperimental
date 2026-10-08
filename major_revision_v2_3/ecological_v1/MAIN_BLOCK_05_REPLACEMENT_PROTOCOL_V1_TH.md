# Protocol amendment: full-block replacement after user-directed pause

บล็อก `MAIN_BLOCK_05` หยุดระหว่าง CF-Fit ตามคำขอผู้ใช้เมื่อ 2026-10-07 23:52 น. (Asia/Bangkok) ก่อนมีผลครบสามแขน จึง audit แบบ paired ไม่ได้ บันทึกเหตุและ hash อยู่ใน `MAIN_BLOCK_05_INTERRUPTION_20261007_TH.md` ไฟล์ดิบเดิมไม่ถูกลบหรือเขียนทับ และมีหนึ่ง request ของ `pandas_82` ที่เริ่มแล้วแต่ไม่มี response; billable outcome ไม่ทราบ

ก่อนจ่าย API สำหรับ replacement ให้ freeze `main_block05_replacement_lock_v1.json` ซึ่งเพิ่มเพียง run ID `MAIN_BLOCK_05_R1` และสำเนา specification ของบล็อก 5 ที่เปลี่ยนเฉพาะ `block_id`/`run_id` เท่านั้น Case IDs, order ของสามแขน, seed, task arrival/DAG, owner map, agent/model deployment, capability profiles, generation bounds, image/verifier lock, scan/horizon และ metric definitions ต้องเท่าเดิมทั้งหมด ตัวตรวจ lock ต้องเปรียบเทียบ delta นี้แบบ exact และตรวจ hash หลักฐานที่ถูกพัก

รัน replacement ใหม่ **ทั้งสามแขน** ใน workspace ใหม่ ห้ามยืม Central-Fit ที่จบจากบล็อกเดิม ห้ามเติมต่อ CF-Fit ที่ค้าง และห้าม retry request เดิมภายใต้ run ID เดิม ทุก task ที่เริ่มใน replacement นับหนึ่ง provider attempt; ไม่ retry อัตโนมัติ ผลดิบต้องผ่าน auditor อิสระที่ใช้กฎเดียวกับ main และรับ amended lock ก่อนเป็น research result

Analysis แสดงเวกเตอร์ throughput, completion time, busy utilization และ provider-reported cost per verified job รวมทั้ง success/failure แยก metric ไม่สร้าง scalar winner ไม่ทดสอบ equivalence/fault tolerance ใช้ paired contrast สองชุด: (ก) ห้าบล็อกดั้งเดิมที่ audit ครบ และ (ข) ห้าบล็อกนั้นกับ `MAIN_BLOCK_05_R1` เป็น technical replacement แบบเปิดเผย ช่วง bootstrap เป็น descriptive เพราะใช้ข้อมูล Adult/Beijing ซ้ำและเคสจาก repository เพียงสามแห่ง

ใน manuscript ต้องระบุการหยุดและการทำ replacement ชัดเจน ผลบล็อกเดิมที่ไม่ครบไม่ใช่ negative outcome หรือศูนย์ค่าใช้จ่าย และไม่ถูกผสมกับ result ชุดใหม่ การรันต่างวันอาจมี provider-state/time-of-day confounding จึงห้ามอ้างว่าความต่าง CF-Fit กับ Central-Fit เกิดจาก decentralization เพียงสาเหตุเดียว หรือระบบหมด single point of failure
