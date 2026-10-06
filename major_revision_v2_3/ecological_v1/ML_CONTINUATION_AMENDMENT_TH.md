# การเดินหน้าคู่ที่ยังไม่เริ่ม — 6 ตุลาคม 2026

ผู้ใช้อนุญาตให้ทำ real-LLM ต่อโดยไม่กำหนดเพดานงบ ตัวรันเดิมหยุดหลัง 10 คู่ เมื่อ GLM preprocess ของ CAL_ADULT_01 เกิด RemoteDisconnected หนึ่งครั้ง ผล 7 VERIFIED, 2 STAGE_CONTRACT_FAILED และ 1 PROVIDER_UNRESOLVED เก็บไว้ทั้งหมด ไม่มีคำตอบที่จะใช้ตัดสินคู่สุดท้ายและค่าใช้จ่ายอาจเกิดแล้ว

การเดินหน้ารอบนี้ **ไม่ใช่ retry**: เรียกเฉพาะ 278 คู่ในแผนเดิมที่ไม่มี request marker และไม่มี output directory เท่านั้น รวมทั้ง batch ยังมีได้ไม่เกิน 288 first-attempt requests ไม่เรียกคู่ที่เริ่มแล้วซ้ำ ไม่เพิ่มตัวอย่างตามคะแนน และไม่เปลี่ยน prompt, generation, quality gate, model mapping หรือ dependencies ของ execution lock เดิม

ก่อนเรียกครั้งแรก ตรึง continuation lock พร้อม hashes ของหลักฐานเดิม รายการคู่ที่ยังไม่เริ่ม และ implementation ของ continuation แยกจาก lock เดิม ใช้ batch-owner lock เดียวกันเพื่อกัน controller ซ้อนกัน ผลจะเข้าสู่ ledger เดิมและมี continuation events เพิ่มเติมเพื่อ audit

Provider-unresolved ถือเป็นผลที่ต้องรายงาน ไม่ใช่ model failure ที่ยืนยันได้ หลังหนึ่งครั้งสามารถส่ง **งานอื่น** ที่ยังไม่เริ่มให้ deployment เดิมได้ หากเกิด provider-unresolved สามครั้งติดต่อกันระหว่าง continuation ของ deployment นั้น ให้หยุด deployment นั้นและคงงานที่เหลือเป็น NOT_STARTED; HTTP 401/403 และ deployment mapping drift หยุดการส่งงานใหม่ทั้ง batch หลัง worker อื่นจบ request ที่กำลังทำ ไม่ส่ง paid request ทดแทน ไม่แก้ผลเก่า ENVIRONMENT_UNRESOLVED/REPLAY_UNRESOLVED หยุดเพื่อแก้เครื่องมือ ไม่เดินหน้าปะปนกับผลความสามารถ

ตัวเลขระหว่างรันเป็น progress เท่านั้น ยังไม่ใช่ผล allocation main, universal ability ranks หรือ probability ที่ปรับเข้ากับ simulation เดิมย้อนหลัง
