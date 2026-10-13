# สถานะต้นฉบับและแผนภาพ 13 ตุลาคม 2026

ไฟล์ที่เลือกอ่าน/แก้ต่ออยู่ใน `v2/CURRENT_MANUSCRIPTS/`:

- `ConveyorFlow_IEEE_Manuscript_v2_6_1_Current.docx`
- `ConveyorFlow_AJSTR_Blinded_v2_6_1_Current.docx`
- `ConveyorFlow_AJSTR_Unblinded_v2_6_1_Current.docx`

ทั้งสามเริ่มจาก latest v2.3 `Main_Rev8/Rev6`, ไม่ใช่ร่าง bounded v2.6 ที่อิง source เก่ากว่า. เพิ่ม cohort 11 blocks และ matched fault control โดยแยกจาก six-block cohort; exposed FastAPI output-budget pilot ระบุเป็น instrument check ไม่ใช่ผล main. `audit_current_manuscripts_v2_6_1.py` ตรวจว่าตัวเลขและคำจำกัด claim ที่สำคัญอยู่ครบ, ภาพ embedded ไม่เปลี่ยน, 13 native equations ยังอยู่, ตารางเพิ่มสองรายการ, abstract AJSTR 222 คำ และไฟล์ blind ไม่มีข้อมูลระบุตัวผู้เขียนในแพ็กเกจ OOXML

ผลตรวจ layout **ยังไม่ผ่าน**: Microsoft Word automation ค้างก่อนเปิดเอกสารและถูกหยุดโดยไม่มีการแก้ไฟล์ต้นฉบับ; ตามคำขอของผู้ใช้ไม่ได้ใช้ LibreOffice. ฉะนั้น v2.6.1 เป็น **draft for coauthor/adviser review, not submission-ready** จนกว่าจะเปิดใน Microsoft Word ตรวจทุกหน้า, header/footer, ตาราง, captions, cross-references และ PDF export ด้วย Word. ชุดไฟล์ Word ใน `CURRENT_MANUSCRIPTS` ถูก ignore ใน Git; ไฟล์ code/protocol/audit ใน `major_revision_v2_6` ถูกเก็บเพื่อทำซ้ำ

ทุก version ของ manuscript ที่อยู่นอกโฟลเดอร์นี้ถูก **คัดลอกพร้อมตรวจ SHA-256** มาเป็น bounded v2.6 ระดับบนหรือ `ARCHIVE_FROM_OTHER_LOCATIONS/`; ไม่ย้ายต้นฉบับจริงเพราะ build scripts ยังอ้าง path เดิม. แผนภาพแก้ไขได้อยู่ใน `CURRENT_MANUSCRIPTS/DIAGRAMS/ConveyorFlow_diagrams_en_working.drawio` และ subfolders v2.0–v2.2; export Fig. 1–5 ฉบับ corrected อยู่ใน `DIAGRAMS/v2_2/corrected_exports/`. รายละเอียดไฟล์เลือกอ่านใน `CURRENT_MANUSCRIPTS/README_CURRENT_TH.md`

การทดลอง: exposed FastAPI output-budget pilot ผ่าน test 4 ชุดภายใต้ max output 32,768 แต่ไม่ใช่ main cohort. Scrapy source preflight v1b ผ่าน `scrapy_39` และ `scrapy_34` โดยมี provider calls = 0; ยังไม่ใช่ Real-LLM outcome หรือหลักฐานปิด Major Revision. รายละเอียดอยู่ใน `REPAIR_OUTPUT_BUDGET_PILOT_RESULT_TH.md` และ `SCRAPY_PUBLIC_PREFLIGHT_RESULT_TH.md`
