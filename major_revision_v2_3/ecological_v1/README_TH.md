# Ecological v1 ภายใน ConveyorFlow v2.3

## Live execution เริ่มแล้ว — 6 ตุลาคม 2026

ผู้ใช้อนุญาตให้ใช้ API เท่าที่จำเป็นโดยไม่จำกัดงบแล้ว เวลา 14:05 น. เริ่ม ML calibration ตาม execution lock แยกจาก preparation lock: 24 specifications × 4 stages × 3 deployments = 288 first-attempt calls. หลัง 10 คู่ ตัวรันเดิมหยุดจาก GLM RemoteDisconnected; เก็บ VERIFIED 7, contract failures 2 และ provider-unresolved 1 ไว้ทั้งหมด เวลา 14:22 น. เริ่ม continuation ที่ตรึง 278 **never-started pairs** ไม่ใช่ retry คู่ที่มี request แล้ว ดู `ML_CONTINUATION_AMENDMENT_TH.md` และ `BUDGET_AND_EXECUTION_AMENDMENT_TH.md`

คำสั่งตรวจสดแบบไม่ใช้ API:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalMLCalibrationAudit
```

`EcologicalMLCalibrationExecute` และ `EcologicalMLContinuationExecute` ต้องระบุ `-ConfirmPaidRun`; controller ปฏิเสธการเริ่มซ้ำที่มีหลักฐานแล้ว อย่าใช้คำสั่ง Execute เป็นคำสั่งดูสถานะ Candidate Python/joblib อยู่ใน isolated offline container เท่านั้น ไม่รันบน Windows. Repository preflight กำลังทำและยังไม่ส่งงานใหม่ให้ provider. ยังไม่มี allocation main/profile calibration ที่จบแล้ว

ส่วนที่เหลือด้านล่างเป็น **preparation snapshot ก่อนเริ่ม paid execution**. คำว่า `live_ready=false` ของ preparation audit หมายถึงยังไม่พร้อม allocation main ไม่ได้แปลว่า ML calibration ยังไม่เริ่ม งบที่กล่าวว่ายังไม่อนุมัติใน snapshot ถูก supersede ด้วย amendment ข้างต้น

อัปเดต 6 ตุลาคม 2026: **เตรียมและตรวจแบบ offline แล้ว แต่ยังไม่พร้อมรัน main experiment จริง**. งานรอบนี้ไม่เรียก API และไม่รันโค้ดที่โมเดลสร้างบนเครื่อง Windows. ผลจาก fixtures และ trusted numeric references ไม่ใช่ผล real-LLM รอบใหม่.

## สิ่งที่มีแล้ว

- `prepared_design/`: แยก ML specifications สำหรับ calibration 24 รายการและ main 12 รายการ พร้อม repository preflight candidates 24 รายการ. เลือกก่อนเห็นผลโมเดลและตัด pools เดิมออกทั้งหมด. Design SHA256: `bcda309b38d1fb6681e63319c4bdb467594460a6ecb3566ad6249ff8eb809c0b`.
- `ml_preparation/CAL_ADULT_01` และ `CAL_BEIJING_01`: เตรียม CSV และ trusted numeric reference gates แล้ว. มี training rows 26,049 และ 288,369 ตามลำดับ. Public test features ไม่มี target; labels และ reference predictions แยกจาก public tree. **ยังต้องผ่าน container preflight**.
- `dry_checks_20261006/`: ผ่าน 20 logical fixture runs ครอบคลุม success, upstream failure, provider-unresolved และ no-volunteer. CF/central ให้ claim ตรงกันใน 4 scenarios และ replay ledgers ได้ผลเดิม.
- `decision_process_check_20261006.json`: 4 Agent processes คำนวณข้อเสนอเอง เทียบกับ 1 coordinator process ที่ใช้ฟังก์ชันเดียวกัน. ได้ข้อเสนอตรงกันบน common snapshot.
- `shared_claim_check_20261006/`: หลาย trusted child processes แย่ง SQLite CAS. หนึ่ง task มีผู้ชนะหนึ่งราย และ Agent เดียวไม่ถือสอง tasks พร้อมกัน. เป็น correctness check ไม่ใช่ latency หรือ fault-tolerance result; SQLite ยังเป็น shared failure dependency.
- `audit_preparation.py`: ตรวจ hashes, schema, การแยก labels, fixture replay และ claim ledgers แบบ read-only. Entry point `Check` ล่าสุดผ่าน 154 unit tests พร้อม provenance audits และ exit 0.

ไฟล์ `PROTOCOL_TH.md` และ `prepare_design.py` ถูกตรึงใน preparation identity แล้ว ห้ามแก้แล้วใช้ lock เดิม. README นี้บันทึกความคืบหน้าของ implementation ไม่เปลี่ยน frozen protocol. จากเดิมที่มีเฉพาะ dry-run ใน process เดียว ขณะนี้มี separate-process probes เพิ่มแล้ว แต่ยังเป็น checks แยกส่วน ไม่ใช่ end-to-end live backend.

## สองช่องว่างที่กำลังปิด

1. **Ecological execution/calibration**: ใช้ ML stages และ buggy repositories จริง. ใน calibration ทุกโมเดลได้ trusted predecessors เดียวกัน เพื่อไม่ให้ failure ในขั้นต้นปิดบังความสามารถขั้นถัดไป. ส่วน main ต้องต่อ artifacts ที่ทีมสร้างจริงและนับ full-job outcomes; ห้ามนับ isolated stages เป็น full pipelines.
2. **Decision-locus control**: `CENTRAL_RULE_MATCHED` ใหม่ย้ายการคำนวณ choice function เดียวกันไป coordinator ไม่ใช่เพียง relay bids แบบ Central-Matched เดิม. Eligibility, fit, soft stand-down, aging, jitter, one proposal per Agent และ claim/execution budgets ต้องเท่ากัน. Control นี้ไม่ได้แทน centralized optimizer ทุกแบบ. Static owners กำหนดก่อนรันและไม่ self-select.

Scientific story ยังคงตามที่ปรึกษา: งานไหลขึ้น READY belt → Agent ที่ว่างประเมินและเลือกตาม capability–task fit → soft stand-down ลด priority เมื่องานง่ายเกินระดับ → atomic claim ป้องกันเจ้าของซ้ำ → execution/verifier → DONE หรือ bounded retry. RQ1 วัด trade-offs ไม่บังคับให้ชนะทุก metric; RQ2 คง homogeneous/heterogeneous teams และ Fit/Stand-down ablations. No-Fit ใหม่เอาเฉพาะ fit distance ออก ต้องแยกจาก No-Fit ของ simulation เดิมที่ปิดหลาย terms ร่วมกัน.

## ข้อจำกัดการเตรียมและProbability

ML เป็น feature subsets ใหม่บนสอง corpora และ row splits เดิม จึงเป็น **task-specification holdout** ไม่ใช่ raw-data holdout หรือ 24 independent datasets. Repository pool จำกัดที่ Python 3.8 และ single-pytest commands; ยังไม่ได้ preflight pool ใหม่นี้. การเลือกเฉพาะ environments ที่ทำซ้ำได้, localization และ public tests จำกัดขอบเขตข้อสรุป.

`Agent.ranks` และ required ranks ใน fixtures เป็นค่าทดสอบ ไม่ใช่ calibrated Ability Ranks. ห้ามเรียง Rank ตามราคา, brand หรือความใหม่ และห้ามบังคับให้สาม aliases ได้ Rank 1/2/3 คนละระดับ. ต้องวัด first-attempt outcomes บน calibration แยก workload/stage รายงาน uncertainty, unresolved และ billing แล้ว freeze profiles ก่อน main. Probability ของ 22,500 simulation runs เดิมยังเป็น scenario assumptions; ไม่เปลี่ยนย้อนหลังเป็น empirical เพียงเพราะมี stage feasibility 28/36.

Preparation นี้ไม่มี human-expert difficulty labels. หากใช้ LLM role-based rubric ต้องเปิดเผยว่าเป็น LLM-derived labels ไม่เรียกเป็น human expert validation. ผู้ใช้จะจัดการส่วนผู้เชี่ยวชาญเอง; เว้นไว้ก่อน ไม่เติมคำรับรองแทน.

Full preparation envelope 306 generation calls ยังไม่ใช่งบที่อนุมัติ และไม่ใช่ required minimum ที่รับรองว่าจะปิด Major Revision หรือได้ Q2. จำนวนที่จะ execute, precision และ scope ต้องตรึงก่อน calls ตามงบ; การเพิ่ม variants ไม่ได้เพิ่ม source clusters. ยังไม่มี main sample lock หรือ paid launch route สำหรับชุดนี้.

## คำสั่งoffline

รันจาก workspace root. ทุก stage ด้านล่างไม่เรียก MFEC:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage Check
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalAudit
```

ตัวอย่าง preparation ของ **เคสที่ยังไม่มี output** (trusted numeric reference เท่านั้น):

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalMLPrepare -CaseId CAL_ADULT_02
```

ห้ามเรียก CAL_ADULT_01/CAL_BEIJING_01 เพื่อทับผลที่มีแล้ว. สำหรับ rerun fixtures ให้เลือก NEW output path ภายใน ecological_v1; relative paths ต่อไปนี้ resolve จาก v2 โดย entry point:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalDryRun -OutputPath 'major_revision_v2_3/ecological_v1/dry_recheck_01'
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalDecisionCheck -OutputPath 'major_revision_v2_3/ecological_v1/decision_recheck_01.json'
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalClaimCheck -OutputPath 'major_revision_v2_3/ecological_v1/claim_recheck_01'
```

Existing outputs ถูกปฏิเสธ ไม่ลบหรือทับ run เดิม. Additional fixture outputs ไม่ใช่ extra research observations. Audit ตรวจ prepared ML ที่มีทั้งหมดและ canonical checks ลงวันที่ 20261006; ไม่ได้ audit ทุก manual rerun โดยอัตโนมัติ.

## ก่อนรันจริงยังขาดอะไร

1. ผู้ใช้กำหนดเพดาน API calls/งบ; ตรึง sample, precision และ provider identity/currency. ห้ามเริ่ม 306 calls จาก implicit approval.
2. คืนความพร้อมของ protected approvals ก่อน WSL/container/paid launch/Word. Automatic approval review เคยหยุดเพราะ usage quota; ไม่ใช้เส้นทางอื่นข้ามการปฏิเสธ.
3. ตรวจ trusted container stages สำหรับ ML specifications ใหม่ และ repository buggy-fail/fixed-pass, candidate gold-free, regression และ source identity ทุกเคสตามลำดับที่ตรึงไว้. เก็บ environment exclusions ทั้งหมด.
4. สร้าง ecological calibration ledger จริง แล้ว profiles พร้อม uncertainty/difficulty-label provenance. แยก conditional stage ability, observed operational completion และ unknown outcomes. ไม่ fit D1–D3 coefficients โดยไม่มี labels/variation.
5. เชื่อม decision components กับ live assessor/executor/verifier, common clock, shared CAS และ artifact store; ตรวจ end-to-end ก่อน paid main. ClaimStore ยังไม่มี verifier authentication หรือ candidate capability boundary; ห้าม mount DB ใน candidate container.
6. Freeze paired streams, teams ≤4, token cap, retry, timeout, arm-order randomization และ main analysis lock. ทดสอบ CF-Fit/Central-RuleMatched/Static พร้อม RQ2/ablations ตามขอบเขตที่งบรองรับ. รายงาน failures และ cost/time/throughput/utilization ทั้งหมด.
7. วิเคราะห์ผลแล้วอัปเดต Word v2.3 ทั้ง blind/unblind ด้วย Microsoft Word พร้อม render/page QA และ PowerPoint. ไม่แตะ v2.2; ยังไม่กล่าวว่า Word รับผลชุดใหม่แล้ว.

`live_ready=false` เป็นสถานะจริง ไม่ใช่ error ของโมเดล. Code/preparation ผ่านบาง gates แล้ว แต่ยังไม่ได้ปิด Major Revision ทั้งหมดและไม่รับรองผลการพิจารณาของ journal.
