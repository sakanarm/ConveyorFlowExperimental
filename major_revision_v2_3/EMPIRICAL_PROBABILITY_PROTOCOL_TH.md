# v2.3: ที่มาของความน่าจะเป็นสำเร็จ (ก่อนใช้เป็น empirical parameter)

## Addendum 6 ตุลาคม 2026 — ไม่เปลี่ยน outcomes ของ completed protocols

Repository first-attempt18คู่จบแล้ว และ ML isolated-stage v2กำลังรันบนreusedspecifications. **ยังไม่ใช่ held-out ecological probability calibration**: หก bugs/สามrepositoryclustersและสองMLcorporaไม่พอแทน task population ของทุกdifficulty. การรันโค้ดจริงได้บางเคสไม่ทำให้ coefficients ของEquation7มี empirical provenance ย้อนหลัง. แหล่งข้อมูล public datasets ใช้สร้าง workloads; ไม่ได้เป็นแหล่งของ model success probability โดยตัวมันเอง. Parameterเดิมต้องคงป้าย scenario assumption และค่าทุกตัวต้องtraceถึง frozenconfig/source/สูตรที่ใช้.

ก่อน calibration รุ่นถัดไป ให้แยก estimands ชัดเจน:

1. **Operational verification within budget**: verified first attemptภายใน frozen observation/deadline ÷ planned eligible attempts. Provider-unresolvedไม่ใช่ observed verification จึงอยู่ในdenominator แต่บันทึกเป็นunresolvedแยก ไม่เรียก observed code failure. Report failures/unknownbillingควบคู่.
2. **Capability conditional on evaluable return**: verified ÷ evaluable returned outputs เป็น secondary descriptive quantity. การตัด unresolvedอาจทำให้selectionbias จึงห้ามแทน operational primary rate หรืออ้างว่าเป็นlatent universal ability.
3. **Unknown-result bounds**: หาก S verified, U outcome-unresolved, N planned eligible attempts ให้รายงานช่วงเชิงตรรกะ `[S/N,(S+U)/N]` พร้อม uncertainty intervalsที่เหมาะกับsamplingdesignแยกกัน. Boundsนี้ไม่ใช่95%CI. Environment/instrument failuresแยกตามfrozenruleและต้องแสดงfullplannedaccountingไม่หายไป.

ข้อความเดิมด้านล่างที่ว่าtimeout“นับเป็นfailure”หมายถึงไม่ได้verifiedภายใน operational budget ไม่ใช่หลักฐานว่าcandidateที่ไม่เคยได้รับถูกทดสอบแล้วและผิด. Completed pilot classifications/locks/resultsไม่เปลี่ยน. Future calibrationต้องfreezeนิยามนี้ก่อนcalls และแจ้งamendmentหากต่างจากprotocolเก่า.

ที่มาจากงานอื่นอาจสนับสนุนเหตุผลเชิงรูปแบบของ logistic response curve แต่ไม่สามารถยืนยันค่า0.85/1.20สำหรับMFEC deploymentsเหล่านี้. ถ้าต้องการเรียกค่าใหม่ว่าempirical ต้องมีcase manifest, pre-outcome labels, ledger, fitting method, cluster-aware uncertaintyและheld-out predictive checksจริง. Sensitivity analysisช่วยตรวจความทนทานของข้อสรุป แต่ไม่ใช่การสร้างสถิติที่มาของprobabilities.

สถานะ 4 ตุลาคม 2026: **แผนเก็บข้อมูล ยังไม่มี empirical probability สำหรับงาน end-to-end**. เอกสารนี้ไม่เปลี่ยนผล simulation 22,500 runs หรือ manuscript v2.2 ย้อนหลัง

## 1. ปัญหาที่อาจารย์ชี้

Adult, Beijing และ Bugs2Fix ให้ข้อมูล/โจทย์สาธารณะ แต่ไม่ได้ให้จำนวนครั้งที่ MFEC agent แต่ละตัวทำ task ระดับ D1–D3 สำเร็จ ค่า `logit(p) = alpha_w + 0.85 theta_a - 1.20(d-2)` ใน simulation เดิมจึงเป็น **scenario assumption**. Calibration pilot ที่ใช้ seed ของ simulator ตรวจเพียงว่า curve ไม่ชนเพดานและเรียงตาม Ability/Difficulty; ไม่ใช่การประมาณ `p` จาก LLM จริง. Ability probes เดิมมีห้าข้อต่อ workload × difficulty × model และเป็น microtasks; ห้ามใช้แทนผล ML DAG หรือ repository repair

## 2. Estimand และแหล่งข้อมูลที่ต้องสร้าง

แหล่งข้อมูลหลักต้องเป็น append-only ledger ของ **การพยายามทำงานที่ตรึงไว้ล่วงหน้า** โดยโมเดล MFEC ที่ระบุ deployment alias/version, วันเวลา, prompt/validator/container hash และผลตรวจอัตโนมัติ. หนึ่งแถวคือหนึ่ง model–case–stage attempt ตาม first-attempt protocol. กำหนด

`p(a,w,d) = Pr(verified on first attempt | frozen model a, workload w, difficulty d, frozen prompt/validator/token budget, sampled held-out task specification)`.

รายงานทั้ง `successes / eligible attempts` และ Wilson 95% interval; provider timeout/error หลังเริ่ม attempt นับเป็น failure ที่มีค่าใช้จ่าย, ส่วน environment failure ที่เกิดก่อน model output ต้องบันทึกแยกและตัดออกได้เฉพาะตามเกณฑ์ที่ตรึงไว้ก่อน. ไม่ใช้ stage ที่ไม่เคยถูกเรียกเพราะ predecessor ล้มเหลวเป็น failure ของ stage นั้น และไม่ทิ้ง job ที่ล้มเหลวจาก end-to-end denominator

## 3. กัน selection bias ของ DAG

ML DAG pilot ที่ปล่อย stage ต่อเมื่อ stage ก่อนผ่าน วัดได้เพียง `P(stage passes | reached)` และ `P(full job verified)`; ไม่ประมาณความสามารถที่แท้จริงของทุก model ในทุก stage เพราะ train/package ของ job ที่ตายก่อนหน้าไม่ได้ถูกทดสอบ. สำหรับการประมาณ stage-level `p`, ต้องมี **isolated held-out stage probes**: สร้าง input และ predecessor artifacts ด้วย trusted reference ที่ผ่าน verifier, ให้ทุก model ทำ stage เดียวกันจาก state เดียวกัน, แล้วรัน source ของ model ใน locked offline container. แยกผลชุดนี้จาก full-DAG pilot และจาก main allocation cases

Fix Bug ใช้ repository checkout ที่ผ่าน preflight buggy-fail/fixed-pass; ทุก model ได้ issue, allowed files และ test budget เดียวกันโดยไม่เห็น gold patch/hidden tests. หลัง model ตอบ ให้ทดสอบ patch ใน isolated container และเก็บผล visible/hidden/regression. Surrogate microtasks เดิมไม่เข้าตัวส่วนนี้

Difficulty D1–D3 ต้องมาจาก rubric/labels ที่ตรึงก่อนเห็น model outcomes; ปัจจุบัน ML pilot กำหนด rank ตามชื่อ stage (`ingest=1`, `preprocess=2`, `train=3`, `package=2`) จึง confound difficulty กับชนิด stage. ก่อนประมาณ coefficient ของ difficulty ต้องเพิ่ม task specifications หลายระดับภายใน stage หรือวิเคราะห์แยก stage และระบุข้อจำกัด. LLM-adjudicated labels ต้องเรียกเช่นนั้น ไม่เรียก human expert labels

## 4. แยกชุดข้อมูลและลำดับตรึง

1. **Harness feasibility**: 4 Adult, 4 Beijing และ 6 bugs ตาม protocol v2.3 ใช้หา environment/validator faults และวัด cost/runtime; ไม่ใช้เลือก policy winner หรือ estimate หลัก
2. **Held-out calibration**: เลือก task specifications แยกจาก policy main; ให้สาม frozen models ทำทุก probe ภายใต้ budget เดียวกัน. ตรึง case hashes, difficulty labels, exclusion rule, model mapping, prompt, validator, image และ provider-cost recording ก่อนเรียก API. เก็บ model-specific outcomes ต่อ cell พร้อม cluster ID ของ source corpus/repository
3. **Parameter fitting**: ระบุวิธีจากข้อมูลก่อนเปิดผล main. เริ่มจาก observed binomial rates + Wilson interval; ถ้า cell บาง ให้ใช้ hierarchical logistic model ที่มี workload/stage effects และรายงาน prior, fit diagnostics, uncertainty และ predictive checks. ห้ามเติม cell ที่ไม่มีข้อมูลด้วยค่าจำลองเดิมแล้วเรียกว่า empirical
4. **Sensitivity**: ส่งช่วงล่าง/กลาง/บนที่มาจาก interval หรือ posterior เข้า simulator; ทดสอบว่าข้อสรุปเชิง trade-off เปลี่ยนหรือไม่. Version/config ใหม่ต้องแยกจาก confirmatory run เดิมและใช้ seed ชุดใหม่ที่ตรึงก่อนดูผล
5. **Main ecological comparison**: หลัง G0–G4 ผ่าน จึงรัน CF-Fit, Central-Matched และ static บน paired streams; calibration cases ไม่ปะปนกับ main. รายงาน full-job verified rate, cost/time/utilization และ failure ทั้งหมด แม้ผลไม่เข้าทาง CF-Fit

จำนวนต่อ cell และ CI target **ยังไม่ตรึง** เพราะต้องวัด cost/variance จาก feasibility ก่อน. จำนวนห้าข้อต่อ cell ใน microtask calibration เดิมไม่พอให้ถือเป็น empirical probability ของ ecological task. ระบุ unit of inference เป็น model deployment × task population นี้ ไม่ใช่ความสามารถสากลของ vendor หรือ dataset อิสระหลายชุด; variant จาก corpus เดียวกันต้อง cluster ในการวิเคราะห์

เพื่อประเมินงบอย่างโปร่งใส: เมื่อ observed rate ใกล้ 0.5, Wilson 95% interval มีครึ่งความกว้างประมาณ 0.33 ที่ `n=5`, 0.17 ที่ `n=30`, และ 0.13 ที่ `n=50` ต่อ cell. ถ้าแยกสามโมเดล × สาม workload × สาม difficulty และต้องการ 50 independent probes ต่อ cell จะเป็น **1,350 model calls สำหรับ calibration เท่านั้น** ก่อน main policy experiment. ตัวเลขนี้เป็นตัวอย่าง precision/budget ไม่ใช่ sample size ที่อนุมัติแล้ว; repeated variants ของ corpus เดียวกันยังมีความสัมพันธ์กันและอาจให้ effective sample size ต่ำกว่า `n` ดิบ

## 5. เกณฑ์แก้ manuscript

- ก่อนมี calibration ข้อความหลัง Equation (7) ใน v2.2 ถูกต้องเมื่อเรียกว่า *assumed potential-outcome model*; ห้ามเขียนว่า empirically calibrated
- เมื่อมี ledger ตามข้อ 2–4 จึงเพิ่มตาราง `model × workload × difficulty/stage: n, verified, p-hat, 95% interval`, provenance hashes และ fitting/sensitivity results ใน v2.3 ฉบับใหม่
- หาก Docker, API budget หรือจำนวน cases ไม่พอ ให้เก็บ result เป็น feasibility/negative finding และคง claim แบบ simulation-only; อย่าอ้างว่าปิด empirical-parameter gap แล้ว

เอกสารที่เกี่ยวข้อง: `../AJSTR Journal/SIMULATION_PARAMETER_PROVENANCE_V2_2_TH.md`, `../real_llm_pilot/CALIBRATION_PROTOCOL.md`, `../AJSTR Journal/AJSTR_v2_3_MAJOR_REVISION_PROTOCOL_TH.md`, `STATUS_TH.md`.
