# v2.4 context amendment v1b (ก่อนเรียก LLM)

การเตรียม prompt ชุด v1 หยุดที่ `pandas_121` โดยไม่มีการเรียก provider: กฎ AST ดึง class `DataFrame` ทั้งก้อนจาก `pandas/core/frame.py` ทำให้ข้อความ excerpt เกินเพดาน 160,000 ตัวอักษร หลักฐานและ lock v1 เก็บไว้ตามเดิม ไม่ลบหรือแก้ผลที่ค้างอยู่

ชุด v1b ตัดเฉพาะชื่อ `DataFrame` ออกจาก *รายการ AST excerpt* ของ `pandas_121` คง `replace`, `_replace_single`, `replace_list` ไว้ ไม่เปลี่ยน production files ที่อนุญาตให้แก้, visible test, public regressions, ภาพ candidate/verifier หรือวิธีตัดสินผล ตัวโมเดลยังได้รับ source excerpt ของทั้งสามไฟล์ตามกฎเดิม และ patch ที่เสนอจะถูกใช้กับไฟล์ buggy ทั้งฉบับ การเปลี่ยนนี้อาศัยขนาด context ก่อน provider เท่านั้น ไม่อาศัย fixed source หรือผล LLM

ต้องเตรียม identity gate ใหม่ครบ 12 เคสภายใต้ root `results/repair_contexts_v1b` และล็อก hash ของ amendment ก่อนจ่าย API ค่า context cap 160,000 ตัวอักษรไม่เปลี่ยน การผ่าน gate นี้ยังไม่ใช่ผลการซ่อม repository โดย LLM
