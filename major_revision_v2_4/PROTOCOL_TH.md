# v2.4: prospectively controlled experiments for the remaining Major Revision concerns

สถานะ 10 ตุลาคม 2026: เขียน **หลังเห็นผล v2.3** แต่ก่อน preflight หรือเรียก LLM สำหรับเคส v2.4. จึงเป็น prospective protocol เฉพาะ v2.4 ไม่ใช่ preregistration ของ v2.3. ไฟล์และผล v2.3 คงเดิมทั้งหมด. การทดลองไม่ตั้งเงื่อนไขว่า CF-Fit ต้องชนะ; ผลลบและงานที่ไม่จบอยู่ใน denominator.

## Scientific question and estimands

RQ1 ถามผลของ local self-selection บน READY belt ต่อ verified throughput, terminal completion time, busy/productive utilization, provider-reported cost per verified job, verification, dead-letter และ unresolved work เทียบกับ `CENTRAL_RULE_MATCHED` และ `STATIC_OWNERS`. ไม่มี composite score หรือ must-win. RQ2 และ fit/stand-down ablations ยังเป็นคนละ analysis; ไม่ยกจำนวน policy เป็น contribution.

การทดลอง A วัด paired allocation outcomes ของ **mixed workload stream** ภายใต้ artifact contract เดียวกันทุก arm. การทดลอง B วัดผลของ **decision locus** เมื่อข้อเสนอ, งาน, execution outcome และ service times ถูกตรึงเหมือนกัน. B ไม่ใช้ provider calls และไม่ใช่ตัวแทนของ live LLM latency.

## A. New real-LLM paired allocation, exact-edits contract

เลือกเคส BugsInPy จาก public metadata snapshot ด้วย `select_repair_cases_v1.py` โดยตัดทุกเคสใน prior exposure inventory และ v2.3 prepared pool ออกก่อน. Primary target คือ Luigi, Matplotlib, pandas และ FastAPI อย่างละ 3 เคส: แต่ละ repository มี **candidate queue 5 เคส** ที่ hash-sort ไว้ก่อน preflight; รับ 3 เคสแรกที่ผ่าน buggy-fail/fixed-pass, public regression baseline, gold-free candidate image, source-import และ context identity gates. หาก repository ใดได้ไม่ครบ 3 ภายใน queue ที่ตรึงไว้ ให้หยุดก่อน provider call, รายงาน exclusions แล้วทำ amendment ใหม่; ห้ามเลือกจาก model success. FastAPI ยังไม่มี environment profile ใน v2.3 และถือเป็น blocker จนตรวจ profile/container ผ่าน. ไม่ใช้ 6 holdouts ของ v2.3 ซ้ำ.

หนึ่ง paired block มี repository repair หนึ่ง job และ ML DAG ที่สร้างจาก public Adult/Beijing ตาม frozen arrival stream; agent ไม่เกิน 3 คน. ทุก arm ใช้ same case bundle, agent roster, ability/resource profile, prompt/output cap, exact `before`/`after` JSON adapter, allowed production paths, validator, retry bound, observation horizon และ provider version. CF-Fit ให้ idle agents volunteer เอง, Central-Matched ย้าย **pure choice rule เดียวกัน** ไป coordinator process, Static Owners กำหนด owner ก่อนงานมาถึง. Atomic claim, belt readiness, executor/verifier และ failure accounting คงเดิม. Balance arm order ก่อน calls; อย่าเปลี่ยน arm/case/model หลังเห็น output. ทุก request ต้องมี append-only start marker; started unknown/empty/error อยู่ใน operational denominator และไม่ auto-retry.

Verified repository repair ต้องผ่าน visible bug test, frozen public regressions และ fresh-container replay ของทั้งสองชุด. Public withheld regressions ไม่ใช่ independent hidden tests. Candidate source รันใน networkless disposable Linux container เท่านั้น. Verified ML job ต้องผ่าน ingest, preprocess, train และ package จาก predecessor artifact ของ arm เดียวกันจริง. ห้าม pool v2.4 กับ v2.3 strict-diff main หรือ 7/15 feasibility follow-up. Source repository/project คือ cluster; task/stage ภายใน DAG ไม่ใช่ independent replicate. Primary comparisons เป็น paired `CF_FIT - CENTRAL_RULE_MATCHED` และ `CF_FIT - STATIC_OWNERS` ต่อ metric; uncertainty ต้องคำนึงถึง block และ repository cluster. Sample target 12 blocks เป็น bounded four-repository study, **ไม่ใช่ power calculation หรือข้ออ้าง population equivalence**. ถ้าจะอ้าง equivalence ต้องตรึง smallest effect of interest และจำนวน blocks แยกก่อนรัน.

## B. Decision-locus controlled replay and fault-domain test

ใช้ same frozen task streams, local proposal set, deterministic claim ordering, per-agent service times และ verification outcomes ในทั้งสอง architecture. No-fault gate: agent-local กับ coordinator rule ต้องเลือกงานและได้ substantive event/outcome stream ตรงกัน; ถ้าไม่ตรง หยุดแก้ instrument ก่อนวิเคราะห์. รันใน process boundary จริง ไม่ใช้เพียง policy-name switch ใน simulator. แยก coordinator-only process outage, shared READY belt/claim-store outage (negative control) และหนึ่ง agent process outage โดยตรึง onset/duration/seed ก่อนดูผล. บันทึก loss of decision availability, recovered claims, verified throughput, terminal outcomes, time และ resource use พร้อม process-death and recovery evidence. Conditional result ภายใต้ fault injection ไม่ใช่อัตรา outage production หรือคำอ้างว่าทั้งระบบไม่มี single point of failure.

## Freeze / stop / publication gates

1. ก่อน paid call: cohort/preflight/allowed-files/context/validator/profile/model mapping/arm order/call cap/analysis code hashes ต้องเป็น execution lock ใหม่. ห้ามแก้ lock ที่ใช้เริ่มแล้ว. Provider version drift, unsupported FastAPI environment, source leakage หรือ incomplete regression baseline หยุด paid launch; retained failed preflight ไม่ใช่ model failure.
2. หลังรัน: auditor อิสระตรวจ ledger hashes, planned vs started/completed/unknown counts, model IDs, four test gates, same-arm ML artifact lineage และ paired block integrity. ไม่มี manual patch repair หรือ outcome-based case substitution.
3. Manuscript IEEE และ AJSTR ต้องแยก v2.3 main, v2.3 7/15 feasibility, v2.4 A และ v2.4 B. RQ1 รายงาน trade-offs ไม่ใช่ universal superiority; B อ้างได้เฉพาะ allocation-decision failure boundary. Difficulty labels เป็น operational proxy จนมี independent human review. ก่อนส่งต้อง visual QA ใน Microsoft Word และผู้เขียนร่วมตรวจ.

**การปิด concern หมายถึง design/implementation/audit ครบและคำอ้างไม่เกินหลักฐาน ไม่ใช่ CF-Fit ต้องซ่อมผ่านหรือชนะทุก metric.** Reviewer acceptance ไม่สามารถรับประกันล่วงหน้า.
