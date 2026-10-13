# v2.3: การวินิจฉัยความล้มเหลวของ repository verifier (บันทึกหลังบล็อก 1)

บันทึกนี้ทำหลังบล็อก `MAIN_BLOCK_01` ผ่าน independent audit แล้ว แต่ก่อนเริ่ม
บล็อก 2–6 ไม่ใช่ส่วนหนึ่งของล็อกการทดลองเดิม และห้ามอธิบายว่าเป็น
การจัดประเภทที่ preregister ไว้ก่อนเห็นบล็อก 1

ใน static arm ของ `luigi_3` โมเดลส่ง patch กลับมา แต่ trusted guard หยุดก่อน
pytest สร้าง XML: `ValueError: context mismatch; fuzzy matching is forbidden`
พร้อม return code 1 และไม่มี timeout นี่คือ patch ที่นำไปใช้กับ source
ที่ล็อกไว้ไม่ได้ ไม่ใช่ความล้มเหลวของ Docker หรือ provider โดยตรง
adapter เดิมจัดทุกกรณีที่ไม่มี XML เป็น `VERIFIER_ENVIRONMENT_UNRESOLVED`
อย่างหยาบเกินไป Raw ledger/summary และการนับ `UNSETTLED` ของผลหลัก
จะยังคงเดิม ห้ามแก้ย้อนหลัง

สคริปต์เสริม `adjudicate_repository_guard_failure_v1.py`
(SHA-256 `f9097acdae9544bee753996692efc02463f3c1f09a85347df74e3382b00b21e4`)
อ่านเฉพาะบล็อกที่ผ่าน independent audit แล้ว และติดป้ายวินิจฉัย
`MODEL_PATCH_CONTEXT_MISMATCH` ก็ต่อเมื่อมีหลักฐานครบทั้ง: visible gate,
ไม่มี XML, return code 1, ไม่ timeout, และ stderr มีข้อความ trusted guard
ดังกล่าวตรงตัว กติกานี้ใช้เหมือนกันกับบล็อก 1–6 ไม่เปลี่ยนจำนวน API calls,
ความสำเร็จของ job, throughput, completion time, utilization หรือ provider cost
ถ้าข้อความไม่ตรง จะคง unresolved ไว้

ในบล็อก 1 การวินิจฉัยเสริมพบเฉพาะ static arm หนึ่งรายการ ส่วน CF-Fit
และ Central-Rule-Matched เป็น `PATCH_FORMAT_FAILED` ตามผลดิบอยู่แล้ว
เมื่อเขียน paper ต้องแสดงทั้ง raw status และ sensitivity diagnosis
ไม่ใช้การวินิจฉัยเสริมนี้ทำให้ baseline ดูแย่ขึ้นหรือ CF-Fit ดูดีขึ้น
และต้องแยกว่าการแก้ repository จริง **ยังไม่สำเร็จ** ในบล็อก 1
