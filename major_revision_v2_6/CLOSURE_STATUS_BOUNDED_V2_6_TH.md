# สถานะ Major Revision แบบไม่กล่าวอ้างเกินผล

วันที่ 11 ตุลาคม 2026

## ปิดได้ในขอบเขตใด

1. **ข้อกังวลว่างาน LLM จริงเป็นเพียง microtask/surrogate:** ปิดในระดับ *พิสูจน์ว่า implementation ทำงานกับงาน executable ที่เลือกมาได้* เพราะ v2.4 มี 11 paired blocks แต่ละ block มี ML pipeline เต็ม 1 งานและ repository repair ที่ตรวจใน container 1 งาน เปรียบเทียบสาม arm บนงานเดียวกัน: CF-Fit 17/22, Central-Rule-Matched 14/22, Static-Owners 18/22 งานที่ verified ผลไม่ใช่การชนะทุก baseline และไม่ใช้ 159 API calls เป็น n=159
2. **ข้อกังวลว่ายังแยกผลของการกระจายการตัดสินใจไม่ได้:** ปิดในระดับ *decision-layer dependency ภายใต้ fault ที่ควบคุม* เพราะการทดลอง 160 trials (20 tie seeds × 4 fault scenarios × 2 arms) คงกติกา fit/stand-down, READY belt, atomic claim, verifier และ service outcome เดิม เปลี่ยนตำแหน่ง process ตัดสินใจเท่านั้น เมื่อ coordinator ล้ม CF-Fit จบ 3/3 เทียบกับ Central 0/3; เมื่อ shared belt/claim store ล้ม ทั้งคู่ 0/3

## ยังห้ามอ้างอะไร

- ยังห้ามอ้างว่า CF-Fit “ดีกว่าทุก metric” เพราะ Static-Owners ได้ 18/22 มากกว่า CF-Fit 17/22 ใน cohort นี้ และผลด้านเวลาเป็น conditional-on-success คนละ subset
- ยังห้ามอ้าง population superiority/equivalence หรือความทั่วไปหลาย repository: มี 4 source repositories และ 2 ML corpora ซ้ำใน 11 blocks; 20 fault seeds เป็น task stream เดิม
- ยังห้ามอ้าง cost per verified job ของ executable cohort: ทุก arm มี unknown-cost attempts (1/1/3) และหน่วยเงิน provider ยังไม่ตรวจยืนยัน
- ยังห้ามอ้าง “ไม่มี single point of failure ทั้งระบบ”: shared belt, claim store, verifier และ gateway ยังเป็น failure domains ร่วม
- ยังห้ามอ้างว่า v2.6 source-diversity main experiment รันแล้ว: ขณะนี้เป็นเพียง exposure ledger/source preflight; Sanic ผ่านเบื้องต้น 2 case แต่ยังไม่ผ่าน gold-free/main audit; PySnooper ไม่ผ่าน preflight ปัจจุบัน

## ไฟล์ที่ทำในรอบนี้

- `manuscripts_bounded_v2_6/ConveyorFlow_IEEE_Manuscript_Bounded_v2_6.docx`
- `manuscripts_bounded_v2_6/ConveyorFlow_AJSTR_Blinded_Bounded_v2_6.docx`
- `manuscripts_bounded_v2_6/ConveyorFlow_AJSTR_Unblinded_Bounded_v2_6.docx`
- `REVIEWER_RESPONSE_BOUNDED_V2_6_EN.md`
- `build_bounded_manuscripts_v1.py` สร้างสำเนาใหม่จากต้นฉบับ ไม่ทับไฟล์เดิม รูปเดิม 15 ภาพยังอยู่ทุกฉบับ

ภาพ Fig. 1–5 ในสำเนาใหม่เปลี่ยนเป็น export ที่แก้ความหมายแล้วจาก `AJSTR Journal/figures_v2_2/legacy_style_corrected/` และมี source draw.io สองไฟล์ในโฟลเดอร์เดียวกัน ภาพ Fig. 1 ระบุชัดว่า simulation กับ real-LLM เป็นคนละ executable engine; Fig. 4 ระบุว่า static owner ถูกกำหนดก่อนเริ่ม ไม่ใช่ผู้จ่ายงานขณะรัน ภาพ Fig. 1 แสดง cohort microtask เดิม จึงเพิ่ม caption ระบุว่า executable v2.4 เป็น cohort แยกต่างหาก ไม่แอบอ้างว่ารูปครอบคลุมการทดลองใหม่ทั้งหมด

QA แบบโครงสร้างผ่าน: DOCX ทั้งสามไม่เสีย, มี 15 ภาพและ 10 ตารางต่อฉบับ, AJSTR blind ไม่พบชื่อ/อีเมล/ORCID/GitHub handle ใน XML แต่ยัง **ไม่ได้ตรวจหน้ากระดาษด้วย Microsoft Word** เพราะเครื่องมือควบคุม Word ไม่ปรากฏใน session นี้ และผู้ใช้ไม่อนุญาต LibreOffice จึงไม่เรียกไฟล์นี้ว่า camera-ready

**ข้อสรุป:** ถ้าปรับ claim ตามเอกสารใหม่ เราตอบ major concerns สองข้อนี้ด้วยหลักฐานที่มีได้อย่างซื่อสัตย์ แต่ไม่สามารถรับประกันว่า reviewer จะยกสถานะ Major Revision โดยอัตโนมัติ การอ้างทั่วไป/ต้นทุนรวม/ความทนทานทั้งระบบยังต้องผลเพิ่มหรือคงเป็น limitation ที่ชัดเจน
