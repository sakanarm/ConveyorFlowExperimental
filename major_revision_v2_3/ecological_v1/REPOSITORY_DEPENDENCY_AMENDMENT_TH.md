# เติม dependency ของ regression โดยไม่เปลี่ยนข้อสอบ

วันที่ 6 ตุลาคม 2026 baseline ชุด ecological calibration พร้อม 5/6 cases ส่วน matplotlib_10 มี 10 regression identities ตาม hash-selection เดิม: 8 ผ่านจริงและ 2 skipped โดย JUnit ระบุ `No module named pandas` ทั้ง buggy และ fixed baseline การเก็บผลนี้เป็น passed หรือการเลือก test ใหม่จะทำให้ coverage ไม่ตรง protocol จึงไม่ทำ

ก่อนเรียก LLM case นี้ เพิ่มเพียง pandas==1.0.3 และ pytz==2020.1 ใน derived candidate, verifier และ trusted fixed evaluator images ที่แยกจากของเดิม โดยไม่เปลี่ยน Python 3.8.20, numpy==1.18.4, buggy/fixed source, test identities, selection order, timeout หรือ minimum-pass rule pandas 1.0.3 เป็น release ในช่วงเดียวกับ environment packages ที่ใช้และมี Python 3.8 wheel ตาม https://pypi.org/pypi/pandas/1.0.3/json ใช้ --no-deps เพื่อไม่เปลี่ยน package อื่น เงื่อนไขเวอร์ชันที่ติดตั้งและการ import ตรวจใน container

รัน visible test ของ buggy และ fixed รวมทั้ง regression ชุดเดิมทั้งสิบ บน environment ใหม่นี้ ตรวจว่า candidate ยังไม่มี tests, fixed tree, gold patch หรือ .git และ allowed source hashes ตรง buggy เดิม ก่อน freeze paid prompts กรณีอื่นใช้ baseline ที่ผ่านแล้ว ไม่มีการทดลองซ่อมจาก LLM หรือการแทน case ตามคะแนน

เป็น instrument amendment ก่อน model outcomes ไม่ใช่ความสำเร็จของ model และไม่ใช่การ reproduce historical dependencies แบบครบทุก package ต้องอธิบายข้อจำกัดนี้ใน paper ทุก model ที่ทำ matplotlib_10 ใช้ image identities ใหม่นี้เหมือนกัน หลักฐานเก่าไม่เขียนทับ
