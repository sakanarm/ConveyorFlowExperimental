# Continuation 3 หลังพักตามคำขอผู้ใช้

ประชากรทดลองเดิม 24 specifications × 4 ML stages × 3 deployment aliases = 288 คู่ ใช้ prompt, generation setting, image, validator, resource limits และ first-attempt rule เดิม รอบก่อนหยุดตามคำขอผู้ใช้หลังเสร็จ 91 คู่ อีก 2 คู่มี request marker แต่ไม่มี summary และ 195 คู่ยังไม่เคยเริ่ม

Continuation 3 เลือกได้เฉพาะ 195 คู่ที่ไม่มี request marker ก่อนตรึง lock. เก็บ hash ของ 91 summaries และ request markers, หลักฐานของสองคู่ขัดจังหวะ, ledger prefix, previous controller/lock และ trusted backend health. คู่ที่ขัดจังหวะไม่ถูกเรียก provider ซ้ำ และยังไม่ถูกนับเป็น model failure หรือ VERIFIED. งานที่ใช้ provider response แล้วแต่ fresh replay ถูกหยุดไม่ใช่ complete first-attempt observation

ก่อน API ใหม่ ต้องผ่าน trusted offline Podman health probe ใน output ใหม่. หลัง cleaned bounded timeout คงผล unresolved และตรวจ health อีกครั้งตาม continuation 2. Mapping drift, authentication error, unclean timeout, container launch failure และ evidence hash drift หยุดการเริ่มคู่ใหม่. Provider unresolved ติดต่อกันสามครั้งเปิด circuit เฉพาะ alias นั้น. ไม่มีการแก้กรณีที่ล้มเหลวหรือเลือก case ตามผล

เพิ่ม pause request ที่เขียนแบบ create-once. Controller ตรวจ request ก่อนเริ่มแต่ละคู่ และรอคำขอที่เริ่มไปแล้วจบตาม timeout ที่ตรึงไว้ ก่อนบันทึก paused checkpoint. การส่งคำขอพักยังไม่ใช่คำยืนยันว่าหยุดแล้ว; ต้องรอ `continuation_3_finished.json` และตรวจโปรเซส/container. ถ้าจำเป็นต้องบังคับหยุดกลางคำขอ ต้องรักษา request marker และจัดเป็น interrupted ตามหลักฐาน ไม่ใช่ retry อัตโนมัติ

การสรุปสุดท้ายต้องนับ 288 คู่และเปิดเผยสอง user-interrupted cells แยกใน unresolved denominator พร้อม billing unknown. ห้ามใช้ finalizer v1 ที่กำหนดว่าทั้ง 288 ต้องมี summary. Rates เป็น conditional stage operational results บนสอง corpora และ specification variants ไม่ใช่ full model-built ML pipelines, independent datasets, ability rank assignment หรือ allocation main
