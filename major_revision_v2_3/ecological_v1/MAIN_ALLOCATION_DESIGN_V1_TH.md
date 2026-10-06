# v2.3 ecological main: แผนการทดลองก่อนเปิดผล allocation

สถานะ 6 ตุลาคม 2026: **design specification, not an execution lock or a result**. เขียนขณะ ML calibration ยังรันและมีผลบางส่วนที่มองเห็นแล้ว แต่ก่อนสร้างหรือรัน ecological allocation main. จึงไม่อ้างว่าเป็น preregistration ก่อนเห็น calibration ทั้งหมด. การเปลี่ยนแผนหลังไฟล์นี้ต้องเป็น amendment ลงวันเวลาและเหตุผล; ห้ามแก้ย้อนหลังหรือเลือกเฉพาะเคส/โมเดลที่ผ่าน

## คำถามและสิ่งที่เป็น contribution

RQ1 ถามว่าการย้ายจุดตัดสินใจไปยัง agent ที่เห็นงานบน READY belt เปลี่ยน verified throughput, เวลาจบงาน, utilization และต้นทุนต่อ verified job อย่างไรเมื่อเทียบกับการตัดสินใจส่วนกลางที่ใช้กติกาเดียวกันและ static preassignment. ไม่ตั้งสมมติฐานว่า CF-Fit ต้องชนะทุกตัวชี้วัด. RQ2 ถามว่าทีมที่มี capability ต่างกันสัมพันธ์กับผลของ CF-Fit อย่างไร. Fit กับ soft stand-down เป็นองค์ประกอบกลไกที่ต้องแยกด้วย ablation; จำนวน policies ไม่ใช่ scientific contribution. Shared belt/claim store ยังเป็น failure dependency แม้ไม่มี allocation coordinator ใน CF-Fit

## ประชากรงานและหน่วยวิเคราะห์

- ML main คือ 12 task specifications ที่กำหนดไว้ก่อนผล main ใน `prepared_design/design.json`: `MAIN_ADULT_01`–`06` และ `MAIN_BEIJING_01`–`06`. สอง public corpora มี source rows มากกว่า 20,000 แต่ 12 specifications ไม่ใช่ 12 independent datasets; row splits ของแต่ละ corpus ใช้ร่วมกัน. ใน main ต้องให้ agent สร้าง artifact ของแต่ละ stage ต่อจาก **artifact ที่ทีมใน arm นั้นสร้างและ verifier รับรองจริง**. ห้ามใช้ trusted predecessor จาก calibration มาปิดช่อง stage ที่ทีมทำไม่สำเร็จ
- `main_artifact_chain_v1.py` เป็น contract offline สำหรับตรวจ run/arm/case เดียวกัน, verified report, provider-response/source/artifact hashes และ lineage ของ predecessor ทุกชั้น. Tests ปฏิเสธ trusted reference ที่ไม่มี main origin, ข้าม arm และไฟล์ที่ถูกแก้ภายหลัง. ยัง **ไม่ใช่** live adapter หรือหลักฐานว่า LLM ได้สร้าง pipeline แล้ว; ต้องต่อเข้ากับ container verifier และ append-only provider ledger ก่อน main
- Repository main ต้องใช้เคสใหม่จาก frozen eligible pool และ buggy-fail/fixed-pass, public regression, gold-free/source-identity gates เดิมให้ผ่านก่อน. เป้าหมายสองเคสต่อ Luigi, Matplotlib และ Pandas; ถ้า pool ที่ตรึงไว้ไม่พอ ให้รายงาน gate failure และลดขอบเขตโดย amendment ก่อน model calls ไม่เติมเฉพาะเคสหลังดูผล
- หน่วยงานคือ ML DAG หนึ่งรายการหรือ repository repair หนึ่งรายการ. หน่วยเปรียบเทียบเชิงการจัดสรรคือ **workload stream ทั้งสายพาน** ที่มีหลาย jobs อยู่ร่วมกัน ไม่ใช่ stage call เดี่ยว. การทำ stream เดิมซ้ำเป็น temporal/arrival sensitivity ไม่ใช่ independent dataset เพิ่ม. รายงาน Adult, Beijing และสาม repository clusters แยกก่อน pooled description

## Arms และทีม

ทีมเป้าหมายไม่เกิน 4 agents; primary heterogeneous team ใช้หนึ่ง deployment ต่อ alias ทั้งสาม (`tencent-hy3`, `gpt-5-mini`, `glm-5.3-flash`) เฉพาะเมื่อ version/availability gate ผ่าน. ห้ามเปลี่ยน alias หลังเห็น main results. Ability เป็น vector ตาม workload/stage ที่ได้จาก conditional calibration; ราคาเป็นมิติแยก. Rank 1/2/3 เป็นคำบรรยายระดับ ไม่บังคับให้สาม deployment อยู่คนละ Rank ถ้าหลักฐานไม่แยก. เกณฑ์ rank และ difficulty proxy ต้อง freeze พร้อม uncertainty ก่อน main; หากแยกไม่ได้ให้รายงานว่า rank ambiguous และทำ sensitivity แทนการตั้งชื่อใหม่ให้ดูต่าง

Primary RQ1 บนทีม heterogeneous เดียวกัน:

1. `CF_FIT`: idle agents เห็น READY tasks, assess เอง, volunteer หรือ soft stand-down, แล้วใช้ atomic claim แก้ชนกัน. ไม่มี central allocation chooser
2. `CENTRAL_RULE_MATCHED`: coordinator process คำนวณ **pure choice rule เดียวกัน** บน snapshot/eligibility/fit/stand-down/aging/jitter เดียวกัน แล้ว nominate; ไม่เพิ่ม global optimizer หรือ candidate edges. Claim/executor/verifier เหมือน CF-Fit. ความต่างหลักคือ decision locus และทางผ่านของคำตัดสิน
3. `STATIC_OWNERS`: กำหนดเจ้าของงาน/ทักษะก่อนเริ่ม stream; งานยังขึ้น READY belt แต่ไม่มีการ volunteer runtime และห้ามเปลี่ยนเจ้าของเมื่อเขายุ่ง เว้นแต่ preregistered failure handling ที่ใช้เท่ากันทุก arm

Mechanism checks บน heterogeneous team: `CF_NO_FIT` เอาเฉพาะ fit-distance ออก, `CF_NO_STAND_DOWN` เอาเฉพาะ overqualification penalty ออก. ไม่ใช้ผล ablation คนละ semantics จาก simulator เก่ามารวมโดยไม่มี revision label. RQ2 เป็น CF-Fit เพิ่มบน homogeneous teams สามชุด (สาม agent ที่เป็น deployment เดียวกันต่อชุด). ความต่าง mixed-vs-homogeneous ปนกับ total capability/price; จึงรายงาน model mix และ resource-adjusted description ไม่เรียกว่า pure causal effect ของ heterogeneity หากยัง match capacity/cost ไม่ได้

## Paired execution และ outcome contract

ก่อน paid main ต้องสร้าง execution lock ใหม่ซึ่งระบุ case IDs, manifests/hashes, model versions, prompt/validator/container versions, team members, static mapping, common arrival streams, temporal blocks, arm order, limits, timeout, token/resource caps, retry and no-volunteer bounds, deadline and late-return rule. ใช้ arrival/job pool เดียวกันในแต่ละ paired block; arm order ต้อง balance/randomize **ก่อน** calls เพื่อไม่ให้ provider drift เข้าข้าง arm หนึ่ง. Provider version drift หยุดทั้ง paired block และบันทึก ไม่แอบแทน deployment. แต่ละ LLM attempt มี request marker ก่อน call และ append-only ledger; provider timeout/unknown ไม่กดซ้ำเพื่อให้ผ่าน

Primary report เป็น vector ไม่รวมคะแนนเดียว: verified jobs ต่อ wall-clock observation window, terminal job completion time และ P95, productive/busy utilization โดยแยก idle/assessment/claim/execute/verify, provider-reported cost units ต่อ verified job. Guardrails: job success fraction, DEAD_LETTER, UNSETTLED, retries, no-volunteer, token use, unknown billing. Cost per verified job เมื่อ verified=0 ต้องรายงาน undefined พร้อมตัวนับ ไม่ลบ run. Currency ของ provider cost ยังไม่ยืนยัน จึงไม่เรียก USD. ทุก metric คำนวณจาก ledger ไม่ใช่ live UI state

รายงานความต่าง `CF_FIT − CENTRAL_RULE_MATCHED` และ `CF_FIT − STATIC_OWNERS` ภายใน paired block สำหรับแต่ละ metric พร้อมทิศทางที่ดีของ metric นั้น; ไม่สรุปว่าใกล้เคียงเท่ากับ statistically equivalent หากไม่มี equivalence margin/power ที่ตรึงไว้. Uncertainty ต้องคำนึงถึง case/source clustering; สอง ML corpora และสาม repository clusters ไม่พออ้าง population-wide inference. ไม่ใช้ task/stage ภายใน DAG เป็น independent replicate. รายงาน ablation และ RQ2 แยกจาก primary contrasts; ถ้าหลาย hypothesis ให้แก้ multiplicity หรือระบุว่า exploratory

## Gates ที่ต้องผ่านก่อนคำสั่ง Execute

1. ปิด 288 planned ML calibration identities ตาม bounded protocol (รวมสอง user-interrupted เป็น unresolved), audit/final capsule และ repository calibration capsuleผ่าน; วิเคราะห์ profile พร้อม outcome sensitivity ไม่เลือกเฉพาะ successful pairs. ไม่มีการย้อนหลังไปแก้ 22,500-run simulation probabilities ว่า empirical
2. เตรียมและตรวจ main ML/repository inputs **ทุกเคสที่ตรึงไว้**; reference และ fresh replay ใน container, hidden labels/gold แยกจาก candidate, no symlink/source leak, artifact size cap อยู่ใน prompt และ verifier contract. ถ้า reference ล้ม ให้หยุดแก้ instrument ใน revision ใหม่ ไม่เลือกตัด case หลังดู model output
3. Live assessor/executor/verifier ต้องผ่าน sentinel end-to-end ที่ใช้ generated artifact chain จริง, provider identity/cost accounting, late callback/deadline settlement, SQLite CAS cross-process, no-volunteer retry, outage provenance และ immutable ledgers. Fixture `integration_backend_v2.py` ที่ผ่านอยู่ **ไม่ใช่** paid main และ timing 100 ms/20 ms ของ fixture ใช้เป็นจริงไม่ได้
4. Freeze sample/precision/arm-order/arrival/limits และ analysis script ก่อน first main call. หากทรัพยากรหรือเวลาไม่รองรับ full matrix ให้ลดจำนวน block/arms ด้วย amendment **ก่อน** เห็น main results โดยรักษา RQ1 matched control และ static baseline เป็นแกนขั้นต่ำ; รายงาน exploratory RQ2/ablations ตามจริง

เมื่อ gate ใดไม่ผ่าน สถานะคือ `main_not_ready`; ห้ามคัดลอกเลข calibration หรือ trusted fixture ไปเป็นผล ecological allocation. แม้ทุก gate ผ่าน การยืนยันต้องอยู่ใน execution lock แยกและ reviewer-reproducible evidence capsule; Manuscript จะอัปเดตเฉพาะเมื่อผล main ตรวจ audit แล้ว
