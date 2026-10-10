# Luigi reserve gate before any v2.4 provider call

คิว Luigi ที่ตรึงไว้ใน `cohort_v1.json` คือ 8, 25, 14, 23, 13 ตามลำดับ. Preflight สิ่งแวดล้อมสามเคสแรกผ่าน แต่ candidate/regression gate เดิมของ 8 และ 25 ไม่ผ่าน (`candidate_preflight_failed`): เคส 8 มี public tests ในชุด regression ที่ fail อยู่แล้วใน buggy baseline; เคส 25 มี public regression nodes ไม่ถึงเกณฑ์ที่กำหนด. เหตุนี้ไม่ใช่ผลจาก LLM และไม่มีการเรียก provider ใน v2.4

ตาม protocol ที่เขียนไว้ล่วงหน้า ต้องตรวจเคสสำรอง 23 และ 13 ตามคิวเดิมผ่าน environment gate และ candidate/context gates เดิมก่อน หากยังได้ไม่ครบสามเคส Luigi ให้หยุดและออก amendment เพิ่ม ไม่ลดเกณฑ์ 5 baseline-passing regressions และไม่เอาเคสที่ gate ล้มเหลวไปนับเป็น model failure. Evidence root/lock ของคิวสำรองแยกจาก preflight เดิม ทุก exclusion และ failure เก็บไว้ตรวจย้อนหลังได้
