# v2.4 pre-provider amendment v1b — FastAPI reserve queue

วันที่ 10 ตุลาคม 2026. **ยังไม่มีการเรียก MFEC/LLM สำหรับการทดลอง A ใน v2.4**

ชุดคัดเลือก `cohort_v1.json` และผล preflight เดิมคงไว้ ไม่แก้ย้อนหลัง หลังตรวจครบทั้งห้าเคสของ FastAPI มีเพียง `fastapi_10` และ `fastapi_12` ที่เกิด contrast แบบ buggy-fail/fixed-pass ใน environment ที่ประกาศไว้ ส่วน `fastapi_13`, `fastapi_2`, `fastapi_1` เป็น `environment_excluded` (รวมถึง collection error และ fixed test ที่ไม่ผ่าน) จึงไม่สามารถนับเป็น model failure หรือใส่ในการทดลองแบบเสียค่า API ได้

ตาม stop rule ของ protocol เดิม จึงเปิด **คิวสำรอง v1b ก่อน provider call** จาก public BugsInPy metadata snapshot เดิม โดยใช้ exclusion, Python 3.8, รูปแบบ `run_test.sh`, hash validation และ hash-sort domain เดิมทุกข้อ แล้วพิจารณาเคสที่อยู่ **ถัดจากห้าตัวเดิมเท่านั้น** ตามลำดับที่ตรึงไว้ หยุดเมื่อมี FastAPI ผ่านรวมสามเคส หรือเมื่อคิวสำรองหมด ไม่มีการใช้ผล LLM ในการเลือกคิวหรือแก้ environment เป็นรายเคส หากคิวหมด ให้หยุดและทำ amendment ใหม่; ห้ามลดเกณฑ์ fixed-pass เพื่อให้ได้จำนวนที่ต้องการ

ผล preflight ของสาม repository อื่นและ FastAPI สองเคสที่ผ่านยังใช้ต่อได้โดยอ้าง lock/ledger/hash เดิม ส่วน v1b มี lock และ ledger แยกกัน ผู้ตรวจอิสระต้องรวมสอง ledger ตามลำดับเดิมก่อน candidate/context gate และก่อนตรึง execution lock ที่อนุญาต paid calls. เป้าหมายยังเป็นสี่ repository × สามเคส แต่ขอบเขตข้ออ้างต้องระบุว่าคัดเลือกจากเคสที่ reproducible ใน pinned environment ไม่ใช่ตัวแทนสุ่มของ bug ทั้งหมด
