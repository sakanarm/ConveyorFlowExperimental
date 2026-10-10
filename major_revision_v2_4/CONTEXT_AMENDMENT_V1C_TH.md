# v2.4 context amendment v1c (ก่อนเรียก LLM)

หลังจาก v1b ผ่านถึง `pandas_1` การเตรียม `pandas_80` หยุดก่อนเรียก provider: รายชื่อ API เดิม (`__invert__`, `SparseArray`, `_unary_method`) ไม่มี AST definition ใน `pandas/core/series.py` ซึ่งยาวกว่าเกณฑ์แสดงเต็ม จึงไม่สามารถสร้าง excerpt ของไฟล์นั้นได้ หลักฐาน v1b และ lock ทั้งสองรุ่นก่อนหน้านี้เก็บไว้ ไม่แก้ไขหรือลบ

ตรวจจาก *buggy source* พบ method `Series.__array_ufunc__` ซึ่งเกี่ยวข้องกับการประมวลผล unary operation จึงเพิ่มชื่อ `__array_ufunc__` ในรายการ excerpt ของ `pandas_80` เพียงเคสเดียว ไม่เปลี่ยน allowed production files, visible test `test_invert`, public regressions, candidate/verifier image, หรือเพดาน 160,000 ตัวอักษร ไม่ได้เปิด fixed source หรืออาศัยผล LLM

ต้องรัน source-import identity gate ใหม่ครบ 12 เคสใน `results/repair_contexts_v1c` และ seal independent audit ก่อนเปิด paid main experiment การผ่าน gate ไม่ใช่ผล LLM
