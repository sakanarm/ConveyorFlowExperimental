# ข้อจำกัดที่สังเกตระหว่าง ecological ML calibration

วันที่ 6 ตุลาคม 2026 คู่ CAL_BEIJING_02 / train / tencent-hy3 จบเป็น STAGE_CONTRACT_FAILED. Container return code 1 และ traceback จบด้วย `OSError: [Errno 27] File too large` ขณะ joblib เขียน estimator. เป็น execution/artifact-budget failure ภายใต้ instrument นี้ ไม่ใช่หลักฐานว่าโมเดลไม่สามารถเรียนรู้ regression หรือเลือก algorithm ผิดเสมอไป. เก็บ source, partial artifact, execution report และผลเดิม ไม่แก้ code หรือเพิ่มเพดานเพื่อเลื่อนผลเป็น VERIFIED.

ตัวรัน ML ใช้ file-size limit 268,435,456 bytes, 2 CPUs, RAM 4 GiB และเวลา 360 วินาทีต่อ execution. Limits และ implementation hashes ถูกตรึงก่อน calls. Public prompt ระบุ CPU, RAM, เวลาและ no-network แต่ไม่ได้ระบุ file-size limit อย่างชัดเจน. ความไม่ครบของข้อความข้อจำกัดนี้ต้องเปิดเผยเมื่ออธิบาย first-attempt rates; ห้ามตีความ operational verification เป็น intrinsic model ability ที่ไม่ขึ้นกับ output contract หรือ resource budget.

ยังไม่เปลี่ยน prompt/cap หรือรันเฉพาะคู่ที่ไม่ผ่านใน batch ที่กำลังทำ. Main หรือ protocol revision ถัดไปต้องประกาศ artifact-size limit พร้อม execution constraints ใน public prompt ก่อน outcomes และตรึงใหม่แยกจาก calibration รุ่นนี้. หากทำ sensitivity ต้องกำหนด population/selection และ denominator ล่วงหน้า ไม่เลือกเฉพาะกรณีที่มีโอกาสเปลี่ยนเป็นผ่าน. ไม่ fit simulation probability หรือ Ability Rank โดยละเลย limitation นี้.
