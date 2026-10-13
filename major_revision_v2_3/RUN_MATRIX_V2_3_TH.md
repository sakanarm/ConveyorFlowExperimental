# v2.3: ต้องรันอะไรเพื่อปิด Major Revision และรีรันอย่างไร

## Live update 6 ตุลาคม 2026 เวลา 16:35 น.

MLกำลังรันMFECจริง:67completed/288 (53VERIFIED,6contract/generationfailures,7provider-unresolved,1replay-unresolved),2active,219never-started. Repositorycalibrationรอบใหม่ครบ18/18และfinalcapsule/publicaggregateพร้อมแล้ว. งบไม่ใช่blocker. เพิ่ม`EcologicalIntegrationCheck`ที่เชื่อมactualdecisionprocess/CAS/concurrenttrustedfixtures/verificationครบ แต่ยังไม่ใช่liveadaptermain. Local217testsผ่าน/publicexport213ผ่าน4integration skips

`EcologicalMLCalibrationFinalize`มีcomplete-controller/ledgerguardsและปฏิเสธpartialrunแล้ว. Read-onlycompletionwatcherกำลังเฝ้าเพื่อsealreportหลังครบเท่านั้น ไม่เรียกAPIหรือretrycontroller. WordRev7ไม่สำเร็จเพราะCOMค้าง;Rev6ยังเป็นร่างล่าสุดต้องแก้Fig9captionและตรวจlayoutใหม่. **G5/MajorRevisionยังไม่ปิด**;latestblockนี้แทนsnapshotsต่อไป

## Live update 6 ตุลาคม 2026 เวลา 16:06 น.

Repository ecological calibrationครบ18/18:8VERIFIED,8model failuresและ2provider-unresolved. Final capsuleอยู่`results/ecological_repository_calibration_v1_final/`; public aggregate copiesอยู่`../public_results/v2_3/ecological_repository_calibration_v1/`. ห้ามเรียกfinalizerทับdirectoryนี้. MLยังเรียกMFECจริง: snapshotcompleted47/288,36VERIFIED,4contract failures,6provider-unresolved,1replay-unresolved; active1,never-started240. งบอนุญาตแล้วและไม่มีbudget blocker. สองcalibration tiersยังไม่ใช่G5allocation main

Local tests207ผ่าน; public export203ผ่าน/4integration skips. IEEEProgressRev6สร้างด้วยWordและrenderครบ21หน้า แต่Fig9caption/section whitespaceยังต้องแก้ก่อนส่งเอกสาร. Gitล่าสุด`78a6f0f`; aggregate commitกำลังทำ. ตรวจสถานะสดด้วยauditsด้านล่าง ไม่ใช้Executeเป็นstatus check. **ยังไม่ปิดMajor Revision**; latestsnapshotนี้แทนประวัติต่อไป

## Live update 6 ตุลาคม 2026 เวลา 15:26 น.

งบอนุญาตแล้วและ **ML/repository calibration กำลังเรียก MFEC จริงทั้งสองชุด**. ML completed33/288 (26VERIFIED,3contract failure,3provider-unresolved,1replay-unresolved), repositoryใหม่ completed5/18 (3VERIFIED,2visible failure) ณเวลานี้ ไม่รวมกับ36/18 supporting pairsเก่า และไม่ใช่ final rates. ตรวจสดด้วยสองคำสั่ง audit ด้านล่าง; Execute จะสร้าง calls ไม่ใช่การดูสถานะ

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalMLCalibrationAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalRepositoryCalibrationAudit
```

ML continuation2 ตรวจ backend ผ่านและเดินเฉพาะ266 never-started pairsหลัง continuation1หยุดจากtimeout. ไม่เพิ่ม cap/เปลี่ยน codeเพื่อให้คะแนนผ่าน. Repositoryใหม่ผ่าน baseline/context/identityก่อนcalls ใช้60case-specific public regression identities; เติมdependencyและpublic excerptsในamendmentsที่เก็บแยกก่อนmodel outcomes. Code suiteล่าสุด201pytest testsผ่าน. IEEE ProgressRev3สร้างด้วยWordแล้วกำลังตรวจ20หน้า. **G5 paired live main และ Major Revisionยังไม่ปิด**. snapshotต่อไปเป็นประวัติเท่านั้น

## Live update 6 ตุลาคม 2026 เวลา 14:22 น.

งบได้รับอนุมัติแล้ว (ใช้เท่าที่จำเป็น ไม่จำกัดเพดาน) ML ecological calibration **เริ่มจริงเวลา 14:05 น.** ตาม execution lock 288 first-attempt calls. ตัวรันเดิมหยุดหลัง 10 คู่: 7 VERIFIED, 2 contract failures, 1 GLM provider-unresolved. เวลา 14:22 น. เริ่ม continuation ที่ตรึงเฉพาะ 278 never-started pairs ไม่เรียกคู่ที่เริ่มแล้วซ้ำ. Repository calibration preflight กำลังทำก่อน calls. ตรวจสดด้วย `EcologicalMLCalibrationAudit`; คำสั่ง `Execute` ไม่ใช่คำสั่งดูสถานะ. Full code suite ล่าสุดผ่าน 162 tests. Snapshot ที่บอกว่าไม่มี API calls ใหม่/รอเพดานงบด้านล่างเป็นประวัติก่อนรอบนี้; **G5 allocation main ยังไม่พร้อม และ Major Revision ยังไม่ปิด**

## Update 6 ตุลาคม 2026

Repository first-attemptครบ18/18และauditผ่าน: Tencent4/6, GPT1/6, GLM2/6VERIFIED; หนึ่งprovider-unresolvedแยกจากfailures. ML isolated-stage v2จบครบ36/36: Tencent11/12, GPT10/12, GLM7/12 รวม28VERIFIED/6failures/2unresolved. Final capsuleสร้าง6ต.ค.04:07:53UTCที่ `results/ml_isolated_stage_pilot_v2_final/`. ทั้งสองชุดเป็น **G1 execution evidence ไม่ใช่ G0 calibration หรือ G5 main**. Entry-point Checkล่าสุดผ่าน154testsพร้อมauditsและจบexit0.

กรอบ RQ1/RQ2, soft stand-down และ matched coordinator-path control ตรวจไว้ใน `ADVISOR_ALIGNMENT_V2_3_TH.md`. ไม่เปลี่ยน objective เป็น must-win และไม่ยกระดับจำนวน policies/patch harness เป็น contribution. WordRev4รวม repositorytableแล้วแต่ยังไม่ผ่าน final page QA; Word automationรอบถัดไปติด approval usage quota. สถานะละเอียดและเวลาของ snapshot ดู `STATUS_TH.md`.

ตารางด้านล่างคงเป็น run matrix; ตัวเลขระหว่างรัน17/18เป็นประวัติ5ต.ค. ไม่ใช่สถานะล่าสุด.

Finalizerสร้าง `results/ml_isolated_stage_pilot_v2_final/{audit.json,summary.json,RESULTS.md}` สำเร็จแล้ว; อย่าเรียกให้ทับcapsuleนี้. ตรวจซ้ำด้วย `MLIsolatedStageAudit` หรือ `Check`. FinalauditSHA256 `22e37c2b84b4720f970a0bc86b0bd664728f03d85f29906591e49db9b3dba984`. รายงานtoken/costที่สังเกตได้แยกunknownbillingและย้ำtrustedpredecessors/reusedspecifications ไม่เปลี่ยนpilotเป็นmain.

ไม่มี worker/finalizer ของ36-pair batchค้างอยู่. Ecologicalชุดถัดไปอยู่ใน `ecological_v1/`: prepared case pools, numeric referencesสองเคส, logicalbelt/decision-process/shared-CAScorrectnesschecksผ่านแล้ว แต่ **live_ready=false** และไม่มี APIcallsใหม่. ดู `ecological_v1/README_TH.md`; sampling/budget/precision/container/labels/profiles/liveintegrationยังเป็นgatesก่อนmain. Controlใหม่ `CENTRAL_RULE_MATCHED` ย้ายผู้คำนวณchoice ต่างจากrelay-onlyCentral-Matchedเดิม; อย่าpoolผลสองcontrolsเป็นแบบเดียวกัน.

อัปเดต 5 ตุลาคม 2026. `../REPRODUCE_V2_3.ps1` เป็น entry point แบบ v2 เดิม แต่ **ยังไม่มี main ecological experiment ที่พร้อมรัน**. `-Stage Check` ตรวจ unit tests และ provenance แบบ offline-only ไม่ใช้ MFEC และไม่รัน generated code. Suite snapshot ผ่าน **116 tests** เมื่อ10:38UTC และ targeted timeout-cleanup suite ผ่าน4/4หลังเพิ่มหนึ่ง test; จำนวนจริงล่าสุดดู `Check`

| Gate | สิ่งที่ต้องรัน | สถานะ/เกณฑ์ผ่าน |
|---|---|---|
| G0 | Freeze aliases/version, provider-cost evidence, budget, held-out ecological calibration cases และ precision rule; วัด first-attempt pass แยก model × workload × difficulty/stage แล้วสรุปด้วย `summarize_ecological_calibration.py` | ยังไม่ครบ; ดู `EMPIRICAL_PROBABILITY_PROTOCOL_TH.md`. Microtask rank เดิมใช้แทนไม่ได้ และยังไม่มี ecological calibration ledger |
| G1-ML | Trusted four-stage DAG และ bounded MFEC feasibility ก่อน calibration/main | Reference 8 variants/32 stages ผ่านบน Podman. Third prompt revision: 2 reused P0 corpus cases × 3 models = 6 jobs; 1 VERIFIED, 3 DEAD_LETTER, 2 unresolved; 20 calls. Tencent Adult clean replay ผ่าน. ยังไม่ใช่ 8 independent held-out cases ตามแผนเดิม |
| G1-Bug | Buggy-fail/fixed-pass ตาม frozen hash order; 6 bugs ≥3 repositories; gold-free candidate และ regression baseline; จากนั้น MFEC patch | ครบ 6 cases/3 repos และ no-op identity smoke. V1 ครบ 18 jobs/36 calls แต่ทุก attempt ถูก output-format gate ปฏิเสธ. Offline decoder replay กู้หนึ่ง unique GPT pandas #76 job ผ่าน visible + 10 public regressions + clean replay; 10 decoded attempts ยัง fail, 24 outputs ว่าง/unfinished. ไม่เปลี่ยนผล v1 |
| G1-Bug diagnostic v3 | Same-case exact-edits sentinel; common 32,768 cap; one call/alias, no retry | จบ 3 calls; GLM pandas #88 VERIFIED รวม fresh replay (8 active regression passes + 2 unchanged xfails), GPT valid edits แต่ visible test fail, Tencent length/empty. ไม่ใช่ independent held-out observations |
| G0 preparation ใหม่ | Stratified new-case preflight: 2 eligible bugs/repo ใน Luigi/Matplotlib/Pandas; ≤4 preflights/repo | Preflight/candidate/source-identity ผ่านครบ6cases/3repos; 53 regression identities เป็น active baseline passes. First-attempt MFEC batch รันจริง18planned pairs, ณ10:42UTC completed17; ดู read-only audit. ผลเป็น localized first attempts ไม่ใช่ D1–D3 probability fit |
| Isolated-stage feasibility ใหม่ | Trusted reference12probes แล้ว36 MFEC first attempts ทุกโมเดลทำทุกstageจากinput/predecessorsเดียวกัน | Reference passed12/12. V1 request-onlyexposurescanพลาดlegacyresponses จึงไม่executev1; correctedv2 freezeก่อนcallsพร้อมinventory. เป็นreused-specificationdiagnostic, ordinal-stateinterfaceจำกัด, two correlatedcorpora ไม่ใช่held-out ecologicalcalibration/main. `MLIsolatedStageAudit` / `MLIsolatedStageExecute` ใช้v2 |
| G2 | Matched-decision-locus simulation `run_matched_v1.py` แล้ว `analyze_matched_v1.py` และ read-only `verify_matched_v1.py` | ทำแล้ว 2,160 runs/1,080 pairs, 720/720 E0 และ belt-outage parity; เป็น simulation ไม่ใช่ latency จริง |
| G3 | วัด local claim กับ coordinator relay ที่ prototype จริง; freeze overhead distribution; แยก coordinator/belt/agent outage | มีผล **single-host serial IPC proxy 1,000 คู่** และ **load-sensitivity 24 sessions/18,000 requests** ที่ 1/2/4/8 concurrent clients; ตรวจซ้ำได้ (`OVERHEAD_PROXY_RESULTS_TH.md`). ยังขาด network/provider, การแยก queue/claim/relay และ fault-domain measurements. ยังไม่มี E1 ที่มีสิทธิเป็นผลหลัก |
| G4 | Feasibility audit: completion, failures, model drift, prompt revision, cost, isolation, leakage และ reproducibility | ML/repository/decoder audits ผ่านด้าน provenance แต่ feasibility ยังไม่เพียงพอสำหรับ main. ต้อง freeze output contract รุ่นถัดไปและตรวจ model eligibility บน held-out cases; ห้ามเลือกเฉพาะเคสที่ผ่านหรือเรียก repeated diagnostics ว่าตัวอย่างอิสระ |
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
& 'v2/REPRODUCE_V2_3.ps1' -Stage PilotV3Audit
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryPilotAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryDecoderAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryContractAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage BugsCalibrationPreflightStatus
```

ปัจจุบันใช้ Ubuntu WSL + rootful Podman สำหรับ isolated execution. `PodmanVerify` ตรวจ frozen ML image lock; Docker stages เดิม (`LivePreflight`, `PilotDryRun`, `PilotExecute`) เก็บไว้เพื่อประวัติ ไม่ใช่เส้นทางที่ใช้ใน v3 batch นี้

เมื่อมี frozen held-out calibration manifest และ JSONL ledger จริงแล้ว ใช้ `-Stage CalibrationSummary -CalibrationManifest <path> -CalibrationLedger <path>` เพื่อรายงาน per-cell `n`, successes, failures และ Wilson 95% interval. สคริปต์จะไม่ตีตราว่าค่าเหล่านี้ fit เป็น simulator parameter โดยอัตโนมัติ

การรัน MFEC เป็นคำสั่ง explicit และใช้คีย์จาก **process environment** ส่งผ่าน stdin เท่านั้น ไม่อยู่ใน argv, candidate image หรือผลที่เผยแพร่:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage PilotV3Execute -CaseId ADULT_P0 -ModelSlot agent_2 -ConfirmPaidRun
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryPilotExecute -CaseId pandas_76 -ModelSlot agent_2 -ConfirmPaidRun
```

**ตัวอย่าง execute ข้างต้นมีผลอยู่แล้วใน workspace นี้ จึงต้องถูกปฏิเสธ ไม่ใช่คำสั่งให้รันซ้ำตอนนี้**. PilotV3 จำกัดไม่เกินสอง attempts/stage; repository v1 ไม่เกินสอง attempts/job. `RepositoryDecoderReplay` เป็น offline diagnostic ไม่มี API calls แต่รัน source ที่กู้ metadata ใน Podman; เมื่อ output มีอยู่แล้วจะปฏิเสธการทับ. `MatchedRun`/`MatchedAnalyze` ก็ปฏิเสธการเขียนทับผลที่มีอยู่เช่นกัน

## Restart/rerun rule — “ให้ผ่าน” โดยไม่เลือกผลเข้าข้างเรา

1. **Infrastructure fail ก่อน provider call** (เช่น Docker preflight): ไม่ใช่ model attempt; แก้ environment แล้วเรียก case เดิมซ้ำได้หลังตรวจว่าไม่มี provider request/response ค้าง
2. **Provider call ถูกส่งแล้วหรือมี response artifact แต่ไม่มี summary**: หยุด ตรวจ request ID, cost, prompt/response hashes, stage report และอาจทำ recovery ledger; ห้ามกดรันซ้ำแบบ blind เพราะอาจนับซ้ำ/เสียค่าใช้จ่ายซ้ำ
3. **LLM output รันแล้วไม่ผ่าน validator**: นับเป็น model failure ตาม frozen attempt/retry cap. ห้ามแก้ patch/โค้ดของ model แล้วนับว่าผ่าน หรือรีรันจนได้ success; ถ้าปรับ prompt ให้เป็น revision ใหม่บนเคส pilot ใหม่และเปิดเผย deviation
4. **Harness/reference ล้ม**: เป็น environment/instrument failure แยกจาก model failure; แก้ code/validator/image version, rerun reference, freeze revision แล้วค่อยเริ่ม pilot/main ใหม่ โดยเก็บ ledger เดิมไว้
5. **Main แล้วเกิด outage/version drift**: หยุด cell/paired block, บันทึกเหตุและใช้ rule ที่ preregistered; ไม่ลบเฉพาะ arm ที่เสีย. Main ทั้งสาม arms ต้องมี paired stream และ accounting เท่าเทียมกัน

ผลลบของ LLM ยังเป็นผลวิจัยที่ใช้ได้ถ้า design/harness ผ่านและรายงานตรงไปตรงมา. “ปิด Major Revision” หมายถึงหลักฐานและการควบคุมครบ ไม่ใช่บังคับให้ทุก model/job สำเร็จหรือ CF-Fit ชนะทุก metric
# Update 5 ตุลาคม 2026 ชุดบั๊กใหม่

New-case preflight และ gold-free baselines ผ่านครบหกเคส/สาม repos. Final baseline bundle ใช้ 53 regression identities (4×10 + Luigi #17 ทั้ง6 + Matplotlib #9 ทั้ง7), all active passes บน buggy/fixed; cardinality amendments freeze ก่อน outcomes ของ short-file cases และก่อน model calls. No-op และ trusted source-mutation import checks ผ่านครบแล้ว. Candidate/preparation gates ไม่มี provider calls

เริ่ม MFEC first-attempt จริง 10:08 UTC: 18 planned pairs, หนึ่ง call/pair, common cap32,768/temp0/provider720s/test180s. อยู่ `candidate_workspaces/repository_first_attempt_v1/`; frozen lock `repository_first_attempt_v1_lock.json`. สาม alias workers ไม่มี model retry; audit via `../REPRODUCE_V2_3.ps1 -Stage RepositoryFirstAttemptAudit`. ไม่รวมกับ reused pilots/decoder/sentinel ไม่ใช้เป็น main policy evidenceหรือ D1–D3 rank fit. สถานะสุดท้ายต้องดู completed/missing/in_progress ไม่เรียก started ว่า finished
