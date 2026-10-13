# บันทึกการพัก MAIN_BLOCK_05 ระหว่างรัน

สถานะ ณ 2026-10-07 16:52 UTC (2026-10-07 23:52 น. กรุงเทพฯ): ผู้ใช้ขอพักการรัน จึงหยุดเฉพาะ Python runner ของ `MAIN_BLOCK_05` ด้วย SIGTERM หลัง SIGINT ไม่ทำให้หยุด กระบวนการหลักยุติแล้ว ไม่ได้หยุด Docker/Podman หรือ container งานอื่น และไม่ได้ลบ/แก้ไฟล์ดิบ

- Frozen main lock SHA-256: `2206d6dde060cf467b920745ef3912d3da4269b8ceda4d3a9c45f3f82386efe2`
- `started.json` มีอยู่ SHA-256 `07c3249b0a3188d64b83ea24e6281470e5c30a5f4b3e290e8b1d961cc1323240`; `raw_complete.json` และ `instrument_unresolved.json` ไม่มี ณ เวลาตรวจ
- `CENTRAL_RULE_MATCHED` มี allocation summary SHA-256 `659bd78725e349fadc4121833d4dc151bf85793e16c41e3bac626329258d06b2` และ ledger SHA-256 `3bb194d6e4430d91f902200a98c9935eecdd043e898496fb0ce96da8ad67d57a` แต่เป็นเพียงแขนเดียวของบล็อกจับคู่ จึง **ไม่** นำเข้าผลหลักลำพัง
- `CF_FIT` มี ledger บางส่วน SHA-256 `20f1834685e06e3e479fe9ebae224aeb06d6ac3a1b6d4d058b98b8db26b3d6a5` และไม่มี allocation summary ปิดแขน ขณะหยุดมี `pandas_82` request marker SHA-256 `077d3a34514eec98dff5f8faaa7a0023fe94d0d88790cd2ec33919d92cf71e79` แต่ไม่มี response/summary; ถือว่า provider/billing outcome **ไม่ทราบ** ห้ามยิงซ้ำโดยอ้างว่าไม่เคยเรียก
- `STATIC_OWNERS` ยังไม่เริ่ม

หลักฐานดิบคงอยู่ใต้ `D:\ConveyorFlowRuntime\v2_3\candidate_workspaces\ecological_main_v1\MAIN_BLOCK_05` และ workspace ML/repository ที่มีชื่อบล็อกเดียวกัน ห้ามลบหรือเขียนทับ บล็อกนี้ไม่มีสถานะ audited/research result และ auditor เดิมต้องปฏิเสธตามที่ออกแบบไว้

แผนต่อ: รัน `MAIN_BLOCK_06` ซึ่งไม่เคยเริ่มและเป็นอิสระจากบล็อก 5 ตาม frozen lock เดิม จากนั้นทำ technical replacement **ทั้งสามแขนของบล็อก 5** ใน run ID ใหม่และ lock amendment ที่ freeze ก่อนจ่ายเงิน โดยใช้ case/order/resource/rule เดิมทุกอย่างและไม่ใช้ raw ที่หยุดเป็นส่วนหนึ่งของผล replacement; ระบุใน paper ว่ามี interruption กับ full-block replacement ไม่อ้างว่าเป็น exact resume หรือการทดลองหลักที่ไม่เคยถูกแก้ไข ห้ามแก้ frozen source/lock เดิมและห้ามผนวกแขน Central ที่จบเมื่อคืนเข้ากับแขนที่รันวันใหม่
