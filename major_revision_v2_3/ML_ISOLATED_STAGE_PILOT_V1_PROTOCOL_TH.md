# ML isolated-stage pilot v1

เริ่มเตรียม 5 ตุลาคม 2026 ก่อน provider calls ของชุดนี้. เป็น **interface-controlled feasibility** ไม่ใช่ main allocation หรือ probability fit. ไม่เปลี่ยน frozen ML DAG v3 หรือผล v2.2.

## เหตุผลและโจทย์

Full DAG เดิมหยุดเมื่อ predecessor ไม่ผ่าน จึงไม่ได้ให้ทุก deployment ทำ train/package จาก state เดียวกัน. ชุดนี้ให้ทั้งสาม MFEC aliases ทำทุก stage อย่างอิสระจาก trusted predecessor artifacts ที่เหมือนกัน. ผลตอบคำถามว่าโมเดลทำ stage ที่ executable และเชื่อมต่อได้หรือไม่ ภายใต้ interface ที่กำหนด ไม่ตอบว่าโมเดลสร้าง ML pipeline แบบอิสระได้ทุกแบบ.

ใช้ ADULT_P1, BEIJING_P1, ADULT_P2 ที่มี input/quality gates/reference checks อยู่แล้ว. Pre-exposure scan ก่อนสร้าง reference bundles พบว่า BEIJING_P2 มี ingest request ใน feasibility รุ่นก่อน จึงนำออกก่อน freeze/provider calls โดยไม่ดูผลตอบหรือ model outcomes. สาม specifications ที่เหลือต้องไม่มี model request evidence. มี 3 specifications × 4 stages × 3 deployment aliases = **36 first attempts สูงสุด 36 provider calls**, ไม่มี model retry. ข้อมูลมาจาก **สอง corpus เท่านั้น** และ feature-subset variants ใช้ train/test rows ร่วมกัน ไม่ใช่สาม datasets อิสระ. ยังคงใช้ public train มากกว่า 20,000 แถวและ hidden test labels แยกจาก candidate.

## Interface และการตรวจ

- Ingest: JSON columns/row counts ต้องตรง CSV จริง.
- Preprocess: joblib dictionary มี `columns,mappings` เท่านั้น. columns ตัด row_id/target/timestamp, categorical mappings เป็น sorted training categories โดย missing=`__MISSING__`, unknown=-1. Numeric conversion เป็น float/coerce to NaN. Trusted verifier ตรวจ mapping ตรง training rows และ transform train/validation/test ได้. เป็น ordinal-state contract ที่ตั้งใจจำกัด ไม่ใช่ข้ออ้างว่าปิด leakage ทุกชนิดได้.
- Train: รับ trusted preprocessing เดียวกัน; model dictionary มี `columns,mappings,model,classification` เท่านั้น. model เป็น importable sklearn estimator. Trusted prediction process ตรวจ interoperability, finite predictions/row identities และ frozen hidden quality floor/ceiling. ไม่โหลด joblib บน host.
- Package: รับ trusted fitted model เดียวกัน; predictions ต้องผ่าน structure และ frozen hidden quality gate.

Predecessors มาจาก trusted reference ไม่ใช่ผล predecessor ของ deployment นั้น. ส่งเฉพาะ prior source เพื่ออธิบาย artifact format ไม่ส่ง current/future reference solution, hidden labels หรือ reference test scores. ทุก verified observation ต้องทำซ้ำ source เดิมใน fresh container และผ่าน gate ทั้งสองครั้ง; replay ไม่ใช่อีก independent attempt.

## Resource และ accounting

เหมือนกันทุก alias: temperature 0, output cap 32,768, provider limit 720 s, แต่ละ execution/semantic gate 360 s, 2 CPUs/4 GiB/read-only root/no network/UID 65534. กำหนด OMP/OpenBLAS/MKL/NumExpr threads=2 ไว้ก่อน calls. Serialize candidate containers บนเครื่องนี้ด้วย process lock; provider workers อาจรอคำตอบพร้อมกันได้. บันทึก queue/execution/provider time แยก ไม่เรียกเวลาเครื่องนี้ว่า allocation throughput.

Container มีชื่อเฉพาะทุก attempt; timeout ต้อง stop/remove ชื่อนั้นและตรวจว่าไม่เหลืออยู่. ไม่ฆ่างาน container ที่ไม่เกี่ยวข้อง. Credentials ส่งทาง stdin ของ trusted bridge และตัดออกจาก container environment; ไม่มี key ใน output.

ทุก pair อยู่ใน planned operational denominator. แยก provider unresolved, generation/contract failure, candidate failure, quality failure และ environment unresolved. ไม่มี automatic paid retry เมื่อไม่ทราบ billable outcome. Cost เป็น provider-reported units จนกว่าจะยืนยัน currency; missing response cost ไม่ถือเป็นศูนย์. ห้าม rerun model failures จนพบ success.

รายงาน per deployment × stage และ corpus พร้อม counts/outcomes. แต่ละ Adult-stage cell มีเพียงสอง specifications ที่สัมพันธ์กัน และ Beijing-stage cell มีหนึ่ง specification จึงเป็น descriptive feasibility เท่านั้น ไม่เปรียบ corpus เป็น causal effect ไม่ fit difficulty coefficient ไม่ตั้ง Ability Rank จากผลนี้ ไม่แทนชุด held-out ecological calibration ที่ต้องกำหนด precision และไม่รวมกับผล full-DAG/pilot รุ่นเดิม. การปิด Major Revision ทั้งหมดยังต้อง paired real allocation streams บน cases แยกต่างหาก.
