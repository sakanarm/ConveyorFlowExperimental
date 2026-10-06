# Ecological v1: เตรียม calibration และ main allocation

เริ่ม 6 ตุลาคม 2026 ภายใน v2.3 เอกสารนี้ freeze เฉพาะหลักการเลือก task-specification pools และขอบเขต preparation ไม่ใช่การรับรองว่าพร้อมเรียก API หรืออนุมัติค่าใช้จ่าย Main sample size และ precision/budget ยังต้องตรึงก่อนเรียกโมเดล

## เรื่องวิจัยที่คงเดิม

Tasks ขึ้นสายพาน READY เมื่อถึงเวลาและ dependencies ผ่าน verifier Agent ที่ว่างประเมินและเลือกหนึ่งงานจากงานที่มองเห็นด้วย capability–task fit ใช้ soft stand-down ให้โอกาส Agent ที่พอเหมาะ ไม่รับรองว่า CF-Fit ต้องชนะทุก metric Policies, ML pipelines และ repository repairs เป็นเครื่องมือทดสอบ ไม่ใช่ contribution หลักใหม่

RQ1 วัด throughput, completion time, utilization และ cost พร้อม VERIFIED/DEAD_LETTER/UNSETTLED และ provider-unresolved RQ2 ดูความหลากหลายของความสามารถในทีม โดยทีมไม่เกิน4 Agents แยกข้อสรุปที่เปลี่ยน resource profiles ด้วย Ablations ต้องแยก Fit และ Stand-down ไม่ขยายจำนวน policies เพื่อเป็น contribution

## Case pools และสิ่งที่คำว่า held-out หมายถึง

- ML: ใช้ public Adult48,842แถว และ Beijing ที่มี288,369 training rows ตาม source manifest เดิม สร้าง feature-subset specifications ใหม่จากการตัด2หรือ3 features โดย deterministic hash order ไม่ซ้ำ8 pilot specifications เดิม แบ่ง calibration12และ main6 specifications ต่อ corpusก่อน outcomes
- **เป็น task-specification holdout เท่านั้น**: source corpora, row splits และ labels ยังเป็นชุดเดิม ไม่อ้าง raw-data holdout หรือ24 independent datasets Variants มีความสัมพันธ์กัน จึงรายงาน source clusters และ uncertainty ที่คำนึงถึงความสัมพันธ์นี้
- Repository: Python3.8 single-pytest population ใน Luigi/Matplotlib/Pandas ตัดทั้ง earlier pools และ exposed prefix ไม่ตัดเฉพาะ model failures สุ่มลำดับด้วย hash ที่ตรึงไว้ แยก calibration/main pools poolละ4 candidates/repository เลือก2เคสแรกที่ผ่าน buggy-fail/fixed-pass พร้อม candidate isolation/regression/source-identity gates บันทึก environment exclusions และ quota skips ทั้งหมด
- หาก poolไม่พอ ให้รายงาน gateไม่ผ่าน ไม่เพิ่มเคสหลังเห็น model outcomes Gold/fixed source อยู่เฉพาะ investigator/verifier ไม่อยู่ใน candidate prompts/images
- อย่าเรียกชื่อ stage หรือ proxy rubric ว่า human-expert difficulty labels ไม่มีการสร้างหลักฐานว่าได้รับ expert validation หากใช้ LLM labels ต้องเปิดเผยและตรึงก่อน outcomes

## Calibration และงบ

Full preparation envelope มี24MLspecifications×4stages×3models =288 generation calls และ6bugs×3models =18calls รวม306calls แต่ **ยังไม่อนุมัติ spend และยังไม่ตรึง sample size ที่จะ execute** เพดาน outputต่อcall32,768 รวม10,027,008tokensเฉพาะenvelopeนี้ ต้องเลือก budget/precision ก่อนสร้าง execution lock ห้ามเติม budget จาก implicit approval หรือเรียก306callsว่าผู้ใช้อนุมัติแล้ว

ทุกโมเดลทำทุก isolated stage จาก trusted predecessorsเดียวกัน เพื่อลด reachability bias ใช้ first attempt ไม่ rerun modelจนผ่าน แยก bounded full-job success จาก conditional stage rates ค่า p ที่ได้เป็น deployment×workload/stage×task-populationนี้ ไม่ใช่ universal ability และยังไม่มีเหตุผลให้ fit D1–D3 logistic coefficients หากไม่มี within-stage difficulty variation/valid labels

รายงาน observed verification ภายใน budget, failures, unresolved และ `[S/N,(S+U)/N]` outcome bounds แยกจาก confidence interval ไม่ปิดบัง unknown billing หรือเรียก provider unitsว่าUSD Fit/sensitivity simulationต้องเป็น configใหม่ ไม่แก้22,500runsเดิมย้อนหลัง

## Main control ที่ต้องเพิ่มให้ตรงข้อวิจารณ์

Central-Matched เดิมเป็น **relay-only control** ไม่แยกตำแหน่งคำนวณ task choice ทุกส่วน จึงเตรียม controlใหม่ชื่อ `CENTRAL_RULE_MATCHED` โดย:

1. ใช้ candidate snapshot, capability/assessment inputs, eligibility, fit, soft stand-down, aging, jitter และone-proposal-per-agentเหมือนCF-Fit
2. CF-Fitคำนวณข้อเสนอที่ฝั่ง Agent ส่วน Central-RuleMatchedคำนวณด้วยfunctionเดียวกันที่coordinator ไม่ใช้globaloptimizer ไม่เพิ่มagent–taskedges และไม่เปลี่ยนtie-breaking
3. ใช้ claim/execution/verification/arrival/retry budgets เดียวกัน และสุ่ม arm order ใน paired blocks Static owners กำหนดก่อนรันและไม่ self-select
4. ยืนยันzero-overhead decision parity และแยก actual decision-process/claim-path timing ก่อนใช้เป็น live evidence Current dry-runเป็นlogical placement test ไม่ใช่ distributed-deployment proof
5. Shared READY/claim storeและledgerยังเป็นdependencies ห้ามกล่าวว่าไม่มีsingle point of failureทั้งระบบ Fault injectionถ้าทำ ต้องเป็นpredeclared scenarioไม่ใช่MFECoutagefrequency

การปรับcontrolนี้แก้ช่องว่างที่relay-only comparisonยังไม่แยกผู้คำนวณคำตัดสิน ไม่แก้code/ผลCentral-Matchedเดิมและไม่อ้างว่าผลใหม่มีแล้ว

Prototypeขณะนี้แยก `Agent.propose` กับ `Coordinator.propose` เป็นสองdecisioncomponents แต่รันในPythonprocessเดียวกันในdry-run ยังไม่ใช่proofของphysicaldecentralization. No-Fitในcontractใหม่เอาเฉพาะfitdistanceออกและคงsoftstand-downpenalty เพื่อเป็นorthogonalablation ต่างจากNo-Fitของsimulatorเดิมที่ปิดprioritytermsร่วมกัน ต้องระบุrevisionนี้ ไม่poolablationทั้งสองengineว่าเป็นกติกาเดียวกัน

## เกณฑ์พร้อมรันจริง

ต้องมี budget/sample/precision lock, new reference/container gates, gold-free repository gates, ecological capability profilesพร้อมuncertainty, difficulty-label provenance, paid-assessment/executor/verifier integration, actual concurrency/clock/decision-path audit และ provider identity/cost accounting ก่อนmain execution หากขาดข้อใดให้ready=false

`run_dry.py` ใช้ trusted fixture outcomesเท่านั้น ไม่เรียกLLM ไม่execute candidate ไม่วัดreal throughput/time/cost ผลdry-runต้องติด `research_results=false` ไม่มี `--execute` ที่หลอกว่าmainพร้อมแล้ว Microsoft Wordและpaid/container executionรอบใหม่ยังติดapproval quota; ห้ามข้ามด้วยอีกเส้นทาง
