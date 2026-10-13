# v2.4 main recovery v2

รอบ main v1 เริ่มจริง 2 provider calls ใน V24_BLOCK_01 แล้วหยุดเพราะ runner ไม่ตั้ง ML workspace guard ให้ตรงไดรฟ์ D เก็บ execution lock, source, provider responses และ partial ledger ของ v1 ไว้ทั้งหมด การหยุดเกิดจากข้อผิดพลาดของเครื่องมือและตรวจพบก่อน ML container verification จึงไม่มี paired block ที่ใช้วิเคราะห์ได้

รอบ recovery v2 ตั้ง workspace เป็น ML runtime เฉพาะที่ตรึงไว้ ตรวจทั้ง path ที่ต้องยอมรับและ path ที่ต้องปฏิเสธก่อน provider call และรัน trusted ML DAG 4 stages พร้อม fresh-container replay บน Adult และ Beijing ก่อนเปิด paid queue การตรวจนี้มี provider calls = 0 และเป็นเครื่องมือตรวจระบบเท่านั้น

คง cohort, 12 paired blocks, 3 allocation arms, counterbalanced order, task arrivals, profiles, prompts, token limits, verification, retry และ horizon เหมือน v1 ใช้ execution root และ lock ใหม่ เพิ่ม hash ของไฟล์ verifier ที่เกี่ยวข้องและหลักฐาน smoke. ห้ามแก้ code/lock เมื่อเริ่ม paid run แล้ว ห้ามทับ root ที่เริ่มแล้ว และไม่มี automatic provider retries. แก้เครื่องมือโดยไม่ป้อน provider output เดิมเข้า prompt ใหม่

V24_BLOCK_01 มี prior partial paid exposure ซึ่งเปิดเผยแยกต่างหาก รายงาน recovery 12 paired blocks และ sensitivity analysis ตัด V24_BLOCK_01 เหลือ 11 blocks เพื่อให้เห็นว่าข้อสรุปขึ้นกับบล็อกนี้หรือไม่ เก็บทั้งผลบวก ผลลบ งานไม่สำเร็จและ provider errors ตาม denominator. จำนวนคำขอ/token/cost ของ incident v1 แสดงเป็น operational overhead แยกจาก paired recovery estimand และไม่รวมเป็น sample ซ้ำ ห้ามอ้างว่าทั้ง 12 recovery blocks เป็นเคสที่ไม่เคยเรียกมาก่อน

เงื่อนไขคำอ้าง: ผล ML ต้องผ่านครบ ingest/preprocess/train/package ด้วย artifacts ของ arm เดียวกัน; repair ต้องผ่าน visible test, frozen public regressions และ fresh-container replay. การซ่อมมี investigator localization และ public tests จึงไม่ใช่ open-ended autonomous repository repair. CF-Fit เทียบ Central-Rule-Matched ใช้ choice rule เดียวกันแต่ต่าง process ที่ตัดสินใจ; no-fault/recovery/fault-domain evidence ของชุด B ประกอบคำอ้างเฉพาะชั้น allocation decision. วิเคราะห์ trade-offs ต่อ metric ตาม RQ1 และรักษา RQ2/heterogeneity/fit/stand-down เป็น contribution เดิม

การปิด Major concerns ขึ้นกับความครบและขอบเขตหลักฐาน ไม่มีเงื่อนไขว่าผลต้องเข้าข้าง CF-Fit และไม่รับประกันคำตัดสินของ reviewer
