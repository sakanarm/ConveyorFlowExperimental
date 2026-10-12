# ส่งต่องาน v2.7 (13 ตุลาคม 2026)

## สถานะที่ยืนยันแล้ว

Real-LLM Scrapy extension จบ 6/6 arms; ไม่มี provider call ค้าง. Candidate lock และ live lock freeze ก่อน calls; independent audit seal ตรวจ request identities, append-only ledgers, actor/claim evidence และ replay patch ที่ผ่านใน Podman. รายงานตัวเลขใน `RESULTS_V27_TH.md`; คำสั่งตรวจซ้ำใน `REPRODUCE_V27.ps1`. ผลคือ CF-Fit 1/2, Central-Rule-Matched 1/2, Static-Owners 1/2. ทั้งสองบั๊กมาจาก repository เดียว; ไม่ใช่ main mixed ML/repair cohort และไม่ให้ใช้ p-value/CI ระดับ population. ค่า gateway response cost เป็น estimate unit ที่ยังไม่ยืนยันสกุลเงิน/ใบแจ้งหนี้.

## ที่เก็บ

- `C:` ภายใน workspace `v2/major_revision_v2_7`: source, frozen locks, audit capsule, analysis, protocol, results, future-work plan, reproducibility scripts และ Word structural/QA scripts. อย่าลบ capsule/locks หลังตีพิมพ์.
- `C:` ภายใน `v2/CURRENT_MANUSCRIPTS`: Word draft ล่าสุดคือ IEEE และ AJSTR blind/unblind ชื่อ `*v2_7_Exploratory_Draft_Rev3.docx`. Folder นี้ถูก `.gitignore` โดยตั้งใจ; Rev1/Rev2 และ v2.6.1 ยังอยู่ ไม่ได้ทับ. `README_CURRENT_TH.md` ระบุว่าฉบับไหนล่าสุด.
- `D:\ConveyorFlowRuntime\v2_7\scrapy_live_pair_v1`: raw responses, patches, request markers, verifier reports, allocation ledgers. เป็นหลักฐานหนัก/อาจมีเนื้อหา provider จึงไม่ขึ้น public Git. ห้ามย้ายโดยไม่แก้ path/hashes ใน audit หรือถ่ายสำเนาแบบรักษา integrity.
- `D:\ConveyorFlowRuntime\v2_7\word_qa`: สำเนาพาธสั้นสำหรับ Microsoft Word, PDF/PNG QA. ใช้พาธสั้นเพราะ Word COM ค้างกับ workspace path ยาว; LibreOffice ไม่ได้ใช้. รายงาน QA ขนาดเล็กอยู่ `v2/major_revision_v2_7/word_qa/qa_report_v1.json`.

## ตรวจซ้ำโดยไม่เรียก API

จาก PowerShell ที่ `v2`:

```powershell
.\major_revision_v2_7\REPRODUCE_V27.ps1 -Mode AuditSource
.\major_revision_v2_7\REPRODUCE_V27.ps1 -Mode AuditCandidate
.\major_revision_v2_7\REPRODUCE_V27.ps1 -Mode AuditLive
.\major_revision_v2_7\REPRODUCE_V27.ps1 -Mode VerifyAnalysis
python major_revision_v2_7/audit_manuscript_v27_drafts.py
```

`SealLive` ทำได้เฉพาะก่อนมี `audit_capsule_v1.json` (สคริปต์ปฏิเสธการเขียนทับ). `RunNext`/`RunRemaining` เป็นคำสั่งเสียค่า API และปัจจุบันครบแล้ว ไม่ควรยิงซ้ำ. ห้ามลบ request marker เพื่อ rerun กรณี provider outcome ไม่ถูกใจ.

## Word และความพร้อมส่ง

Rev3 ทั้งสามฉบับ render ด้วย Microsoft Word ได้ (IEEE 24 หน้า, AJSTR 35 หน้าแต่ละฉบับ), ตรวจ table ใหม่/Future Work ที่เกี่ยวข้องด้วยภาพ และ machine scan ทุกหน้าพบไม่มีหน้าเปล่าหรือ text box หลุดขอบ. รูป/สมการเดิมครบและ blind identity scan ผ่าน. **ยังไม่ได้ตรวจภาพทุกหน้าที่ 100% หรือให้ผู้เขียน/อาจารย์อนุมัติเนื้อหา จึงยังเป็น draft ไม่ใช่ไฟล์ submit-ready**. ผล v2.7 ไม่ปิด Major Revision ทั้งหมด: project diversity, complete mixed cohort/ML replication, human labels, billed cost และ generalizable decision-locus effect ยังเปิดอยู่. แผนใน `FUTURE_WORK_PLAN_TH.md` ยังยึด scientific story ของที่ปรึกษา ไม่ขยายเป็นการเสนอ 13 policies.
