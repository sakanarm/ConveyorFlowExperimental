# v2.3: ต้องรันอะไรเพื่อปิด Major Revision และรีรันอย่างไร

อัปเดต 4 ตุลาคม 2026. `../REPRODUCE_V2_3.ps1` เป็น entry point แบบ v2 เดิม แต่ **ยังไม่มี main ecological experiment ที่พร้อมรัน**. คำสั่งเริ่มต้น `-Stage Check` เป็น offline-only; ไม่ใช้ MFEC, ไม่รัน generated code และไม่เขียนทับผล. ผ่าน 70 unit tests, matched-result integrity, serial/load overhead-proxy integrity, BugsInPy selection status และ ML pilot ledger audit ใน workspace นี้

| Gate | สิ่งที่ต้องรัน | สถานะ/เกณฑ์ผ่าน |
|---|---|---|
| G0 | Freeze aliases/version, provider-cost evidence, budget, held-out ecological calibration cases และ precision rule; วัด first-attempt pass แยก model × workload × difficulty/stage แล้วสรุปด้วย `summarize_ecological_calibration.py` | ยังไม่ครบ; ดู `EMPIRICAL_PROBABILITY_PROTOCOL_TH.md`. Microtask rank เดิมใช้แทนไม่ได้ และยังไม่มี ecological calibration ledger |
| G1-ML | Trusted four-stage DAG smoke (`run_smoke_ml_dag.py`) แล้ว pilot MFEC **4 Adult + 4 Beijing** ที่แยกเคส/ledger | Reference Adult/Beijing ผ่านแล้ว; MFEC P0 อย่างละหนึ่งเคส ingest ผ่านแต่ preprocess ล้ม. P1 prompt revision ใหม่รอ Docker |
| G1-Bug | Candidate image/buggy-fail/fixed-pass/hidden-regression preflight ตาม frozen hash order; เลือก **6 bugs ≥3 repositories**; จากนั้นค่อยให้ MFEC สร้าง patch และตรวจใน container | มี tornado#8 smoke หนึ่งเคสเท่านั้น; `select_bugsinpy_pilot.py` ยังรายงาน 0 preflights. ต้องสร้าง multi-repo container/runner เพิ่ม |
| G2 | Matched-decision-locus simulation `run_matched_v1.py` แล้ว `analyze_matched_v1.py` และ read-only `verify_matched_v1.py` | ทำแล้ว 2,160 runs/1,080 pairs, 720/720 E0 และ belt-outage parity; เป็น simulation ไม่ใช่ latency จริง |
| G3 | วัด local claim กับ coordinator relay ที่ prototype จริง; freeze overhead distribution; แยก coordinator/belt/agent outage | มีผล **single-host serial IPC proxy 1,000 คู่** และ **load-sensitivity 24 sessions/18,000 requests** ที่ 1/2/4/8 concurrent clients; ตรวจซ้ำได้ (`OVERHEAD_PROXY_RESULTS_TH.md`). ยังขาด network/provider, การแยก queue/claim/relay และ fault-domain measurements. ยังไม่มี E1 ที่มีสิทธิเป็นผลหลัก |
| G4 | Feasibility audit: completion, failures, model drift, prompt revision, cost, container integrity, leakage, multi-repo reproducibility | ยังไม่ผ่าน; ผล P0 เป็น negative pilots และตรวจ hash ได้. ต้องครบ 4+4+6 ก่อน freeze main |
| G5 | Paired ecological main: CF-Fit, Central-Matched, Static; cases/streams/validator/team/token cap เท่ากัน, arm order randomized, event ledgers ครบ | **ยังไม่มี main runner ที่อนุญาตให้รัน**; สร้างหลัง G0–G4 ผ่านเท่านั้น ห้ามเรียก pilot ว่า main |
| G6 | วิเคราะห์ job-level outcomes, paired CI, cost/time/throughput/utilization, write manuscript v2.3 พร้อมข้อจำกัด | รอ G5; ห้ามแก้ตัวเลข v2.2 ย้อนหลัง |

## คำสั่งที่ใช้ได้ตอนนี้

จาก workspace root:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage Check
& 'v2/REPRODUCE_V2_3.ps1' -Stage MatchedVerify
& 'v2/REPRODUCE_V2_3.ps1' -Stage OverheadVerify
& 'v2/REPRODUCE_V2_3.ps1' -Stage OverheadLoadVerify
& 'v2/REPRODUCE_V2_3.ps1' -Stage BugsPreflightStatus
& 'v2/REPRODUCE_V2_3.ps1' -Stage PilotDryRun -CaseId ADULT_P1 -ModelSlot agent_2
```

`-Stage LivePreflight` ตรวจ Docker daemon และ immutable evaluator image แบบ read-only โดยไม่เรียก MFEC; ใช้เมื่อ Docker กลับมาพร้อมก่อน `PilotExecute`.

เมื่อมี frozen held-out calibration manifest และ JSONL ledger จริงแล้ว ใช้ `-Stage CalibrationSummary -CalibrationManifest <path> -CalibrationLedger <path>` เพื่อรายงาน per-cell `n`, successes, failures และ Wilson 95% interval. สคริปต์จะไม่ตีตราว่าค่าเหล่านี้ fit เป็น simulator parameter โดยอัตโนมัติ

เมื่อ Docker Linux engine และคีย์ใน **process environment** พร้อมแล้วเท่านั้น:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage PilotExecute -CaseId ADULT_P1 -ModelSlot agent_2 -ConfirmPaidRun
```

PilotExecute จำกัดสูงสุดหนึ่ง MFEC call ต่อ stage/สี่ calls ต่อ case; ตรวจ Docker daemon และ locked image ก่อน call แรก. Generated code รันเฉพาะ networkless Docker container. `MatchedRun`/`MatchedAnalyze` เป็นคำสั่งสร้างผลใหม่แบบ explicit และปฏิเสธการเขียนทับผลที่มีอยู่

## Restart/rerun rule — “ให้ผ่าน” โดยไม่เลือกผลเข้าข้างเรา

1. **Infrastructure fail ก่อน provider call** (เช่น Docker preflight): ไม่ใช่ model attempt; แก้ environment แล้วเรียก case เดิมซ้ำได้หลังตรวจว่าไม่มี provider request/response ค้าง
2. **Provider call ถูกส่งแล้วหรือมี response artifact แต่ไม่มี summary**: หยุด ตรวจ request ID, cost, prompt/response hashes, stage report และอาจทำ recovery ledger; ห้ามกดรันซ้ำแบบ blind เพราะอาจนับซ้ำ/เสียค่าใช้จ่ายซ้ำ
3. **LLM output รันแล้วไม่ผ่าน validator**: นับเป็น model failure ตาม frozen attempt/retry cap. ห้ามแก้ patch/โค้ดของ model แล้วนับว่าผ่าน หรือรีรันจนได้ success; ถ้าปรับ prompt ให้เป็น revision ใหม่บนเคส pilot ใหม่และเปิดเผย deviation
4. **Harness/reference ล้ม**: เป็น environment/instrument failure แยกจาก model failure; แก้ code/validator/image version, rerun reference, freeze revision แล้วค่อยเริ่ม pilot/main ใหม่ โดยเก็บ ledger เดิมไว้
5. **Main แล้วเกิด outage/version drift**: หยุด cell/paired block, บันทึกเหตุและใช้ rule ที่ preregistered; ไม่ลบเฉพาะ arm ที่เสีย. Main ทั้งสาม arms ต้องมี paired stream และ accounting เท่าเทียมกัน

ผลลบของ LLM ยังเป็นผลวิจัยที่ใช้ได้ถ้า design/harness ผ่านและรายงานตรงไปตรงมา. “ปิด Major Revision” หมายถึงหลักฐานและการควบคุมครบ ไม่ใช่บังคับให้ทุก model/job สำเร็จหรือ CF-Fit ชนะทุก metric
