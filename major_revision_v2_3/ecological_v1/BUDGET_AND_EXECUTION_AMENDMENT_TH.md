# การอนุมัติงบและลำดับรัน ecological calibration

ผู้ใช้ยืนยัน 6 ตุลาคม 2026 ว่าไม่จำกัดงบหรือ API calls แต่ให้ใช้เท่าที่จำเป็น. การอนุมัตินี้แทนข้อ budget-pending ใน preparation snapshot ไม่แก้ identity lock หรือผลเก่าย้อนหลัง และไม่อนุมัติการรันซ้ำจนโมเดลผ่าน.

เริ่ม calibration ตาม pool ที่เตรียมก่อน outcomes: ML 12 specifications ต่อ corpus (Adult และ Beijing) × 4 stages × 3 deployments = 288 planned first-attempt calls. Repository เลือก 2 environments ที่ผ่านต่อ repository จาก pool ที่ตรึงไว้ (สูงสุด 4 preflights ต่อ stratum) × 3 deployments = 18 calls. ตัวเลขนี้ไม่ใช่ sample size ของ main allocation. กำหนด caps เป็นขอบเขตต่อ protocol แม้ผู้ใช้ไม่จำกัดงบ เพื่อป้องกันการเรียกซ้ำโดยไม่จำเป็น.

Primary estimand ของ ML คือ observed first-attempt verification แยก deployment × corpus × stage ภายใต้ specifications และ contract นี้ (n=12 ต่อ cell); รายงานข้ามสอง corpora เป็น descriptive aggregate ไม่ใช่ 24 independent datasets. Nominal Wilson interval ที่ n=12 และ p ใกล้0.5 มี half-width ประมาณ0.246; ที่ n=24 ประมาณ0.186. เป็น binomial reference ที่ไม่แก้ dependence ระหว่าง variants; ไม่ใช้เป็น population-wide CI หรือรับรอง precision ของ source-level generalization. จำนวน source clusters ยังมีสอง. ไม่ fit D1–D3 coefficient จากชื่อ stage.

ตรึงรายชื่อทั้งหมด, stage contract, token cap32,768, temperature0, provider timeout720s, one attempt/pair, verifier/image/implementation hashes และลำดับเคสก่อน first call. Reference preparation ทำตามลำดับเดียวกันทุกโมเดล โดยให้ทุก stage ได้ trusted predecessor เดียวกัน. Case-specific prompts และ input/artifact hashes ตรึงก่อน calls ของเคสนั้น; หาก reference ไม่ผ่านให้หยุดเพื่อแก้ instrument ใน revision ใหม่ ไม่เลือกทิ้งเคสเพราะผลโมเดล.

Operational primary denominator รวม planned pairs ที่เริ่มแล้วทั้ง verified, model failures และ provider-unresolved; rows ที่ยังไม่เริ่มต้องรายงาน pending ไม่ถือเป็น failures. เก็บ request marker ก่อนเรียก provider และไม่ส่งซ้ำเมื่อผล billing ไม่ทราบ. Replay source/patch เดิมเป็น verifier check ไม่ใช่ observation เพิ่ม. Alias/version mapping ที่เปลี่ยนให้หยุด batch และบันทึก drift. Currency ของ provider-reported cost ยังไม่ยืนยัน; รายงานเป็น units ไม่เขียนUSD.

Container check ใหม่เรียกได้สำเร็จแล้วหลังการอนุมัติครั้งนี้: Podman ps ได้ผล empty list. ไม่กล่าวว่า approvals สำหรับทุก action จะผ่านโดยอัตโนมัติ; protected actions ถัดไปต้องใช้ approval ตามปกติ. ไม่มีการ bypass quota หรือรัน candidate บน host.

หลัง calibration ต้องวิเคราะห์ profiles พร้อม uncertainty และความต่างจริงก่อนออกแบบ teams/RQ2. ไม่บังคับให้สามโมเดลมี Rank1/2/3 คนละกลุ่ม. Main ต้องมี execution lock แยก, paired stream, actual decision process/clock/CAS integration และ end-to-end gates; ห้ามเรียก isolated calibration ว่า allocation main.
