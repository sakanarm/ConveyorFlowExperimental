# v2.3 repository-repair follow-up: pre-provider cohort amendment V3

บันทึกก่อนเรียก MFEC LLM สำหรับ holdout follow-up ชุดนี้ ไม่แก้ผล main six-block และไม่ใช้เป็นการเทียบ allocation policy

แผนเดิมระบุ BugsInPy holdout 6 เคสตามลำดับ `luigi_11`, `matplotlib_6`, `pandas_127`, `luigi_16`, `matplotlib_26`, `pandas_74` และกำหนดชัดว่าเคสที่ไม่ผ่าน candidate/public-regression gate ก่อนเรียก model ต้องถูกคัดออก ไม่เลือกเคสหรือ regression ใหม่จากผลที่เห็น ขณะทำ gate ไม่มี provider call

ผล gate ก่อน provider: 5 เคสผ่าน candidate baseline และ context/source-import identity ทั้งหมด ได้แก่ `luigi_11`, `matplotlib_6`, `pandas_127`, `luigi_16`, `pandas_74`. `matplotlib_26` ผ่าน visible buggy-fail และ fixed-pass แต่ regression ที่เลือกแบบ hash ล่วงหน้าหนึ่งรายการคือ `test_pandas_bar_align_center` เป็น `skip` เหมือนกันทั้ง buggy/fixed ทำให้ active pass เท่ากับ 9 ต่ำกว่าเกณฑ์ 10 ใน frozen builder. เก็บ `candidate_preflight_failed` เป็น pre-provider exclusion; ห้ามแทนที่ node หรือเรียก model สำหรับเคสนี้

ดังนั้น paid cohort คือ 5 เคส × 3 frozen MFEC deployments = สูงสุด 15 first-attempt model–case pairs; ลำดับเคสเดิมหลังตัด exclusion; หนึ่ง call ต่อ pair, ไม่มี retry หลัง request-start marker. Operational denominator คือคู่ที่เริ่ม request จริง และต้องรายงาน pending/stop แยกต่างหาก หากครบ 15 ให้ batch status `complete`. โปรแกรม paid runner ฉบับร่างก่อน freeze มีการ hard-code ว่าต้องครบ 6/18 และจะรายงาน batch ที่ครบ 15 เป็น incomplete จึงแก้ก่อนสร้าง paid lock/request แรก โดยไม่เปลี่ยน prompt contract, eligible case list, public regression selection, verifier, model aliases, หรือ main-study results

ผล follow-up นี้ทดสอบความเป็นไปได้ของ exact-edits repository repair บนเคสที่ผ่าน pre-provider gate เท่านั้น ไม่ใช้กล่าวว่า CF-Fit ซ่อม repository ได้ดีกว่า Central-Fit และไม่ pool กับ strict-diff main result. รายงาน 1/6 pre-provider exclusion ควบคู่ 5-case analysis เพื่อไม่ซ่อนข้อจำกัดด้าน ecological coverage
