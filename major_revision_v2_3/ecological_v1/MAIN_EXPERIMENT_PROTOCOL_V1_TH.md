# v2.3: เหตุผลและวิธีทดลองจริงเพื่อปิด Major Revision

สถานะเอกสาร: วิธีทดลองที่ล็อกไว้ก่อนอ่านผล ไม่ใช่บทสรุปผลวิจัย  
ล็อก canonical: `main_allocation_execution_lock_v1.json` (SHA-256
`2206d6dde060cf467b920745ef3912d3da4269b8ceda4d3a9c45f3f82386efe2`)

## ประเด็นที่ต้องพิสูจน์

งานเดิมใช้ simulation 22,500 runs และ real-LLM microtasks 60 cases ซึ่งใช้ตรวจ
กลไกและพฤติกรรมเบื้องต้น แต่ยังไม่แสดงการสร้าง ML pipeline แบบต่อเนื่องหรือ
การซ่อม repository จริง ขณะเดียวกันการเทียบ CF-Fit กับ Central-Fit เดิมยัง
แยกตำแหน่งผู้ตัดสินใจออกจากกติกาได้ไม่หมด การทดลองนี้จึงใช้กติกา fit เดียวกัน
แต่สลับเฉพาะผู้คำนวณการเลือกงาน: agent แต่ละตัวเลือกเองใน CF-Fit หรือ
coordinator process เลือกให้ใน Central-Rule-Matched ทั้งคู่ใช้ atomic claim
เดียวกันเพื่อป้องกันผู้รับงานซ้ำ ไม่มีการอ้างว่าระบบทั้งหมดไร้ส่วนกลาง
เพราะการประกาศ READY และการเก็บ event ยังอยู่ใน infrastructure ร่วมกัน

## งานและทีมที่ตรึงไว้

- หก mixed-workload blocks แต่ละบล็อกมี Adult ML หนึ่ง DAG, Beijing ML หนึ่ง
  DAG และ BugsInPy หนึ่ง repository repair; ทั้งสามงานเข้า belt ต่างเวลา
  (0, 20, 40 วินาที) เหมือนกันในทั้งสามแขน งาน ML มี ingest → preprocess →
  train → package และเริ่มขั้นถัดไปได้เมื่อ artifact ก่อนหน้าผ่าน verifier
  ในแขนเดียวกันเท่านั้น
- Adult และ Beijing เป็น public corpora ซึ่ง train rows มากกว่า 20,000;
  หกเคสต่อ corpus เป็น variants ของแหล่งเดิม ไม่ใช่ 12 dataset อิสระ
  Repository cases มาจาก Luigi, Pandas และ Matplotlib อย่างละสองเคส
  จึงต้องรายงานผลแยกโครงการด้วย
- ทีมใช้ MFEC LLM สามตัว (`tencent-hy3`, `gpt-5-mini`, `glm-5.3-flash`)
  พร้อม exact deployment fingerprints ที่ล็อกไว้ Rank 1/2/3 เป็นระดับการ
  routing เชิงปฏิบัติที่คำนวณจาก calibration ตาม workload/stage ไม่ใช่
  ความฉลาดแท้ของโมเดล ไม่ใช่ราคา และบาง cell มี unresolved ที่ทำให้ rank ไว
  ต่อสมมติฐาน จึงห้ามอ้างว่าเป็น ranking สากล
- ความยาก task ใช้ rubric ที่กำหนดโดยผู้วิจัย: ingest 1, preprocess 2,
  train 3, package 2, repository repair 2 เป็น proxy ตามชนิดขั้นตอน
  ไม่ใช่ expert-labeled difficulty และยัง confound กับ stage

## แขนทดลองและการควบคุม

หนึ่งบล็อกใช้ task/arrival/dependency/team/profile/generation/container/verifier
เหมือนกันทั้งสามแขน: `CF_FIT`, `CENTRAL_RULE_MATCHED`, `STATIC_OWNERS`
แขน static กำหนดเจ้าของแต่ละ task ก่อนรันจาก rank สูงสุด แล้วใช้ภาระงาน
ที่วางแผนไว้และ agent ID ตัดสินกรณีเสมอ; เจ้าของไม่เปลี่ยนขณะรัน
ลำดับแขนถูกสลับสมดุลครบหกรูปแบบระหว่างหกบล็อกเพื่อลดผลของช่วงเวลา API
งานที่ไม่มีผู้รับจะรอ/ผ่อนเกณฑ์ตามอายุ task จนถึงขอบที่ล็อก แล้วจึง
`DEAD_LETTER`; งานที่ provider outcome ไม่ทราบจะเป็น `UNSETTLED`
ไม่มี automatic retry ของ request ที่เริ่มแล้ว

## ตัวชี้วัดและขอบเขตการอนุมาน

RQ1 รายงานเป็นเวกเตอร์ ไม่รวมคะแนนเดียว: verified jobs ต่อชั่วโมงในหน้าต่าง
เวลา 3,600 วินาที, เวลาเสร็จของ job ที่ verified ภายในหน้าต่าง,
สัดส่วนเวลาที่ agent อยู่ใน executor และ provider-reported cost ต่อ job
ที่ verified ถ้า cost ของ attempt ใดไม่ทราบ จะไม่แทนค่าเป็นศูนย์ แต่ให้
cost metric ของแขนนั้นเป็น undefined รายงาน success, P95, tokens,
unknown-cost attempts, dead letters, unsettled และงานที่เสร็จหลัง horizon
แยกต่างหาก Busy utilization รวมเวลารอ provider/verification จึงไม่ใช่
CPU utilization ผลต่างเป็น paired block differences พร้อม descriptive
block bootstrap เท่านั้น หกบล็อกมีแหล่งข้อมูลซ้ำ ไม่ใช้ CI นี้เป็น
population inference และไม่ทดสอบ equivalence จากการที่ค่าคล้ายกัน

RQ2 เรื่องทีม homogeneous/heterogeneous และ ablation เรื่อง fit/stand-down
ยังใช้หลักฐานจาก simulation ที่ออกแบบไว้เดิม การทดลองจริงชุดนี้เน้นปิด
ecological-validity gap และทดสอบตำแหน่งการตัดสินใจแบบ matched rule
จึงไม่แอบอ้างว่า real-LLM สามแขนนี้พิสูจน์ RQ2 หรือ fault tolerance
ของ coordinator 13 policies เป็นเครื่องมือทดลอง ไม่ใช่ scientific contribution
หลัก เรื่องหลักยังเป็นงานที่ไหลบน READY belt, self-selection,
capability-task fit และ soft stand-down ของตัวที่เก่งเกินจำเป็น

## หลักฐานและเงื่อนไขก่อนนำเข้าบทความ

ทุก request มี marker ก่อนเรียก API, โมเดล/เวอร์ชัน, prompt hash, token/cost
ที่ provider ส่งกลับ และ verifier/container report งานซ่อมต้องคืน patch
ที่ผ่าน strict allowlist จากนั้นทดสอบ visible bug และ public regression
ใน image แยก พร้อม fresh replay งาน ML ต้องผ่าน stage gate และ fresh replay
ครบทุกขั้น ตัว allocator เขียน append-only hash-chain ledger และ SQLite
atomic-claim log ผลดิบยังไม่ใช่ research result จน
`audit_ecological_main_v1.py` ตรวจแต่ละบล็อกครบสามแขนและสร้าง audit capsule
แล้ว `analyze_ecological_main_v1.py` จึงคำนวณผล ผู้เขียนต้องเปิดเผย
Matplotlib common-environment skip amendment และข้อจำกัดของ
gold-free public regressions ตามหลักฐานที่ตรึงไว้ก่อน main call

ไฟล์ล็อกครั้งแรกที่ Windows serialize path ผิดถูกเก็บไว้ตาม
`MAIN_LOCK_PREEXECUTION_PLATFORM_AMENDMENT_V1_TH.md` และถูกปฏิเสธก่อน
มี main provider request ไม่ใช่การเลือกแก้ protocol หลังเห็นผล
