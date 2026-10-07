# แผน follow-up สำหรับงานซ่อม repository จริง (v2.3)

สถานะ: **protocol amendment / supplemental feasibility** เขียนหลังเห็นผลดิบและ audit ของ MAIN_BLOCK_01–04 แต่ก่อนเริ่มการทดสอบ follow-up นี้ ไม่ใช่ส่วนของ frozen six-block main experiment และห้ามนำผลไปแทนหรือแก้ผลหลักย้อนหลัง

## เหตุผลและคำถาม

งาน mixed-workload หลักใช้ LLM สร้าง JSON ที่บรรจุ git unified diff แบบ strict หลายคำตอบไม่ผ่านรูปแบบ patch แม้มีเนื้อหา code จึงยังไม่แสดงหลักฐานเพียงพอว่า agent ซ่อม repository จริงได้ การทดลองเสริมนี้ถามอย่างจำกัดว่า **เมื่อมี artifact interface ที่ตรวจได้และใช้เหมือนกันกับทุก model จะมีการซ่อม bug ใน repository จริงที่ผ่าน visible test, public regression และ fresh replay หรือไม่** ไม่ใช้เพื่อตัดสินว่า CF-Fit ชนะ Central-Fit หรือ Static และไม่ใช่การทดสอบความทนต่อความล้มเหลวของโครงสร้างพื้นฐาน

## การแยกข้อมูลและการปรับ interface

1. ใช้เฉพาะเคส `calibration` จาก split เดิมในการพัฒนา prompt, parser, test harness และกำหนดเพดาน output; ห้ามอ่าน fixed commit/reference patch ให้ LLM หรือ adapter และห้ามปรับด้วยผลเคส holdout
2. เคส `main` ที่ยังไม่ได้ใช้ทั้งหกเคสถูกกำหนดตาม split เดิม ไม่เลือกตามผลโมเดล: `luigi_11`, `matplotlib_6`, `pandas_127`, `luigi_16`, `matplotlib_26`, `pandas_74` ต้องตรวจ preflight ที่เคยกำหนดไว้ก่อน และเปิดเผยการตัดออกตามกติกาคงที่ก่อนเรียก LLM หากเคสใดใช้ไม่ได้
3. เปลี่ยนเฉพาะ artifact interface จาก “LLM เขียน unified diff เอง” เป็น JSON รายการ edit ที่มี `path`, `search`, `replace` แล้ว adapter สร้าง diff แบบ deterministic ภายใน workspace ของ candidate ห้าม adapter แก้ semantic ของ code เอง, เติมคำตอบ, ลอง patch หลายแบบ, เปิดเครือข่าย, หรืออ่านข้อมูล verifier ที่ไม่อยู่ใน prompt
4. `search` ต้องตรงข้อความในไฟล์ที่อนุญาตเพียงตำแหน่งเดียว; reject ถ้าไม่ตรง/ตรงหลายตำแหน่ง, path traversal, ไฟล์ test/config/report, binary, edit ซ้อนหรือขัดกัน, encoding ผิด, หรือเกินขนาดที่ freeze ไว้ ไม่ใช้ fuzzy matching เพื่อหลีกเลี่ยงการซ่อมแทน LLM
5. Prompt, context, model mapping, token cap, อัตราเรียก และ verifier ต้อง freeze พร้อม SHA-256 **ก่อน** เรียก holdout ครั้งแรก ทุก model ใช้ interface และการตรวจเดียวกัน หนึ่ง model–case มีหนึ่ง provider call; ไม่ retry หลัง error หรือ timeout

## ขั้นรันและ endpoint

- ทดสอบ parser/adapter แบบ synthetic และบน calibration เท่านั้น; ตรวจว่าคำตอบผิดรูปแบบถูกปฏิเสธ และ diff ที่สร้างไม่แตะนอก allowed source files
- หลัง freeze รันทุกเคส holdout ที่ผ่าน preflight กับ model ทั้งสาม (สูงสุด 18 calls) ตามลำดับคงที่และบันทึก append-only request/response hash, exact model version, tokens, provider-reported cost, patch hash และ verifier logs แยกจาก main blocks
- ผลสำเร็จ `VERIFIED` ต้องผ่าน visible bug test, public regression ที่ไม่อยู่ใน prompt, และ fresh replay ของทั้งสองชุดใน isolated container; นับ provider/format/visible/regression/replay failures ใน denominator เดิม โดยแยก `environment_unresolved` ออกให้ตรวจสอบ
- รายงานจำนวน `VERIFIED / attempted` แยกตาม model และ repository พร้อมช่วงความไม่แน่นอนแบบ descriptive เท่านั้น เพราะหกเคสจากสาม repository ไม่เป็นตัวอย่างอิสระหรือฐานพิสูจน์ superiority
- ถ้าทั้งหมดไม่ผ่าน ให้รายงานว่า real-repository feasibility gap **ยังไม่ปิด** ห้ามย้ายข้อสรุปจาก ML pipeline หรือ microtask surrogate มาเป็นหลักฐานการซ่อม repository

## ขอบเขตข้ออ้างใน paper

ผล main six-block เป็นหลักฐานเรื่องการทำงาน ML pipeline จริงและการเปรียบเทียบกฎจัดสรรภายใต้ workload เดียวกัน; follow-up นี้เป็นหลักฐานเสริมเรื่องความเป็นไปได้ของ repository repair **ภายใต้ interface ใหม่** เท่านั้น ต้องระบุว่าเป็น protocol amendment หลังเห็น format failures และไม่รวมผลสอง interface เข้าด้วยกันเป็นอัตราความสำเร็จเดียว เรื่อง causal decision-locus ต้องอาศัย CF-Fit เทียบ Central-Fit ที่กฎ fit และทรัพยากรตรงกัน และยังไม่ใช่ fault-tolerance proof
