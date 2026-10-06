# ConveyorFlow v2.3 สถานะปิด Major Revision

## Main artifact-chain contract 6 ตุลาคม 2026 เวลา 23:25 น.

เพิ่ม `ecological_v1/main_artifact_chain_v1.py` และ tests เพื่อตรวจ lineage ของ ML main ทุก stage ว่า predecessor มาจาก run/arm/case เดียวกัน, verifier ผ่าน และ source/response/artifact hashes ไม่ถูกเปลี่ยน. Trusted calibration predecessor ที่ไม่มี main origin ถูกปฏิเสธ. เป็น offline contract ที่ยังต้องเชื่อม live adapter/Podman/provider ledger จึงไม่ใช่ผล allocation main. Full local suite ผ่าน 238 tests. รอบ ML calibration ยังรันแยกอยู่

## Main allocation design/readiness 6 ตุลาคม 2026 เวลา 23:17 น.

เพิ่ม `ecological_v1/MAIN_ALLOCATION_DESIGN_V1_TH.md` เพื่อระบุ RQ1 แบบ trade-off, matched decision-locus control, static baseline, Fit/stand-down ablations, RQ2 teams ≤4, full artifact chain, metrics/uncertainty และ gates ก่อน paid main. ระบุชัดว่าแผนนี้เขียนหลังเห็น calibration บางส่วนแต่ก่อน main ไม่ใช่ preregistration ก่อน calibration. เพิ่ม `-Stage EcologicalMainReadiness` แบบ read-only/no-provider: ณ audit 113/288 ML pairs, repository capsule ครบ แต่ main-case preparation, profile, live sentinel และ execution lock ยังขาด จึง `ready_to_execute=false`. ตัวตรวจเป็น inventory เท่านั้น; file presence ไม่ใช่ quality certification. Full local suite ผ่าน 233 tests. Main ยังไม่เริ่มและ Major Revision ยังไม่ปิด

## แผนพื้นที่เก็บข้อมูล 6 ตุลาคม 2026 เวลา 22:53 น.

ผู้ใช้เห็นด้วยกับการใช้ D: พร้อม junction ที่พาธเดิมหลังรอบที่กำลังเขียนหยุดหรือจบ. ทดลอง junction ชั่วคราวในโฟลเดอร์ที่ตั้งชื่อเฉพาะแล้ว Windows แสดง `Junction` และ WSL มองผ่านพาธเดิมได้; ลบเฉพาะ probe ว่างแล้ว ไม่ย้ายผลจริงระหว่าง live run. C: ว่างประมาณ 12.7 GiB, D: ว่าง 242.9 GiB. `candidate_workspaces` 3.6 GiB โดย old isolated stage pilot v2 1.2 GiB และ live ecological ML calibration ประมาณ 0.8 GiB. Git objects ประมาณ 40 MiB จึงไม่ใช้ Git เป็นที่เก็บ raw artifacts. `watch_ml_disk_v3.py` ร้องขอ pause เมื่อ volume เหลือต่ำกว่า 4 GiB; ต้องรอ controller acknowledgement. ก่อนย้ายจริงต้องตรึงรายการ source/destination, ตรวจ hashes ก่อนและหลัง, ทดสอบ Windows/WSL/Podman กับพาธจริง และเก็บหลักฐานการย้ายไว้

## Event-driven integration fixture 6 ตุลาคม 2026 เวลา 22:47 น.

ตัวตรวจ `integration_backend_v2.py` dispatch trusted fixture execution ทันทีเมื่อ agent แต่ละตัวชนะ SQLite claim; targeted test ยืนยันว่า agent ที่เร็วเริ่ม execution ก่อน agent ช้าตอบกลับ. ห้า arms และ upstream failure/unknown ผ่านที่ `ecological_v1/integration_event_checks_20261006_v1/`; `python -m pytest tests -q` ผ่าน 226 tests. ยังไม่มี paid main หรือ full ML pipelines จากทีม. การ push commit ล่าสุดไป GitHub ยังรอการเชื่อมบัญชี GitHub ใน session นี้; commit อยู่ใน local main และไม่สูญหาย

## กลับมารัน 6 ตุลาคม 2026 เวลา 22:36 น.

ML continuation 3 เริ่มแล้วหลัง trusted offline backend health ผ่าน และ freeze คู่ที่ยังไม่เคยเริ่ม 195 คู่ด้วย lock SHA256 `86526557d7090bb1074f407d08a34d55a0d027be7687bf046a055b3713fd3622`. Frozen prompts, generation settings, image, validators และทรัพยากรเดิมคงเดิม. Snapshot 22:36 น.: 92/288 เสร็จ, 72 VERIFIED, มีสองคู่ที่ถูกขัดจังหวะตามจุดพักเดิม และหนึ่งคู่ใหม่กำลังทำ. ตัวรันใหม่มี pause request; read-only watcher เฝ้า completion และจะสร้าง final capsule เฉพาะเมื่อ 195 คู่ใหม่ settle ครบภายใต้ protocol. Analysis ฉบับใหม่รายงานสอง interrupted cells เป็น unresolved แยก ไม่ retry หรือเติมผล. Trusted tests 221 ผ่าน; repository calibration 18/18 ยังคงเดิม. นี่ยังเป็น conditional ML stage calibration ไม่ใช่ main allocation, Ability Rank ที่ยืนยันแล้ว หรือผลพร้อมส่งวารสาร

## พักตามคำขอผู้ใช้ 6 ตุลาคม 2026 เวลา 17:36 น.

หยุด ML controller และ completion watcher แล้ว ผลเสร็จ 91/288 (VERIFIED 71) มีสองคู่ขัดจังหวะและ 195 คู่ยังไม่เคยเริ่ม รายละเอียดใน `ecological_v1/USER_PAUSE_20261006_1736_TH.md`. Live updates ด้านล่างเป็นประวัติก่อนพัก

## Live update 6 ตุลาคม 2026 เวลา 16:35 น.

**ML continuation2กำลังรัน MFEC จริง; repositoryรอบใหม่จบ18/18แล้ว**. งบไม่ใช่blockerและไม่ต้องขอAPIceilingเพิ่ม. MLsnapshot16:35:05น.:completed67/288,VERIFIED53,STAGE_CONTRACT_FAILED5,GENERATION_CONTRACT_FAILED1,PROVIDER_UNRESOLVED7,REPLAY_UNRESOLVED1;active2และnever-started219. ActiveคือGLM/Beijing03/preprocessและTencent/Beijing03/train. Provider/model/token/source/gatesยังใช้locksเดิม ไม่retryคู่ที่เริ่มแล้ว

- เพิ่มintegratedprocessbackendfixtureแยกจากfrozenpaidcontrollers. เชื่อมREADY/dependencies → actualagentหรือcoordinatorchoiceprocess → sharedSQLiteCAS → concurrenttrustedfixtureexecution → verifier/artifact/terminalaccounting. ทั้ง5armsและupstreamfailure/unknownผ่านที่`ecological_v1/integration_checks_20261006_v2/`. ใหม่แก้Windowslong-pathimportในreviewercheckoutและตรึงdefaultpytestcollectionไว้trustedtests. ไม่อ้างว่าfixtureเป็นpaidmainหรือproductionconcurrencyครบ;liveadapters/late-returnsettlement/claim-roundbarrierยังเป็นgates
- Local217testsผ่าน;cleanpublicGit-indexexport213ผ่าน/4integrationchecksที่ต้องpublicdata/externalbenchmarkถูกskipอย่างชัดเจน ไม่ใช่passed. พร้อมpublicaggregate4filesของrepository18pairsที่byte-identicalกับfinalcapsule ไม่มีcredential/rawresponses/candidateartifactsในstaging
- เพิ่มMLfinalizerพร้อม4guards. การเรียกบนpartialbatchถูกปฏิเสธจริงและไม่มีfinaldirectoryสร้าง. ตัวเฝ้าcompletionแบบread-onlyเริ่มแล้วที่`watch_ml_completion_v1.py`:ไม่ใช้key/ไม่เรียกAPI/ไม่restartcontroller เมื่อครบ288และfinalmarkersตรงจึงseal`results/ecological_ml_calibration_v1_final/`;หากcontrollerหยุดจะไม่สร้างรายงานผลจบ. ห้ามเปลี่ยนwatcher/analysis/lockระหว่างเฝ้าโดยใช้identityเดิม
- IEEEProgressRev6ยังเป็นร่างล่าสุดที่สร้างสำเร็จ (21หน้า,15figures,13nativeeq,11tablesพร้อมrepositoryfinalcounts). Rev7caption-repairสองrouteหยุดเฉพาะhiddenWordhelpersในtempcopiesเพราะCOMไม่เดินต่อ;ไม่มีRev7outputและไม่กระทบLLMworkersหรือsource/v2.2. Fig9caption/whitespaceยังต้องแก้ก่อนdelivery. AJSTR/PowerPoint/QEยังไม่รับfinalaggregateรอบใหม่

**ยังไม่ปิดMajor Revision**:หลังcalibrationครบต้องfreezeprofiles/uncertainty/difficultyprovenance,เชื่อมlivecontaineradaptersและรันpairedCF-Fit/CENTRAL_RULE_MATCHED/Staticพร้อมRQ2/ablations. Storyตามที่ปรึกษาคงเดิม;วัดtrade-offs ไม่must-win. Snapshotsด้านล่างเป็นประวัติ

## Live update 6 ตุลาคม 2026 เวลา 16:06 น.

**ชุด repository ecological calibration จบครบ18/18แล้ว; ชุด ML ยังรัน MFEC จริงอยู่**. งบได้รับอนุญาตแล้ว ไม่รอคำตอบเรื่องเพดาน API และไม่เรียกคู่ที่เริ่มแล้วซ้ำเพื่อคัดผลดี

- Repository รอบใหม่: VERIFIED8, VISIBLE_TEST_FAILED5, UNFINISHED_OR_EMPTY_OUTPUT3, PROVIDER_UNRESOLVED2. Tencent4/6, GPT2/6, GLM2/6 VERIFIED. Auditor ตรวจ markers, summaries, append-only ledger และ replay gates ครบ ไม่มีคู่ซ้ำหรือคู่ค้าง ไม่ pool กับ supporting batch เก่าที่ VERIFIED7/18
- Final capsule: `results/ecological_repository_calibration_v1_final/`; summary SHA256 `6c03c7cc56a924683d2f18e2f660b7d31b19a6d3064cf33a7e7d3981d02eb51d`. มี16 returned responses,164113 input tokens,183522 output tokens และ0.159635836 provider-reported cost units. สกุลเงินยังไม่ยืนยัน; อีก2 requestsมีbillingที่ไม่ทราบ ไม่เรียกยอดนี้ว่าtotal billed cost
- Public aggregate copies ที่ `../public_results/v2_3/ecological_repository_calibration_v1/` มีเพียง audit/summary/manifest/RESULTS; ไม่มี credentials, responses หรือ candidate code. Local tests207ผ่าน; clean public code export203ผ่าน/4integration skips. Code pushล่าสุด`78a6f0f`; aggregate copyกำลังบันทึกในcommitถัดไป
- ML snapshot16:05:35น.: completed47/288, VERIFIED36, STAGE_CONTRACT_FAILED4, PROVIDER_UNRESOLVED6, REPLAY_UNRESOLVED1; active1, never-started240. ตัวเลขนี้ไม่ใช่final rate. Continuation2ยังทำงานด้วยlockเดิม
- หนึ่งBeijing trainชนfrozen256MiB file-size capซึ่งไม่ได้ระบุชัดในprompt; คงfailureไว้และเปิดเผยใน`ecological_v1/OBSERVED_RESOURCE_LIMITATION_TH.md`. ห้ามเปลี่ยนcapหรือrepair/rerunคู่เดิมเพื่อpromoteคะแนน; future mainต้องระบุresource limitsทั้งหมดก่อนoutcomes
- IEEE v2.3 ProgressRev6สร้างด้วยMicrosoft Wordแล้ว:21หน้า,15figures,13nativeequations,11tables รวมrepositoryรอบใหม่และข้อจำกัด. Renderedครบ21หน้าและตรวจทุกหน้าแล้ว พบFig9captionแยกcolumnและช่องว่างจากsection breaksที่ยังต้องแก้ จึงยังไม่ตั้งเป็นsubmission-ready. AJSTR/PowerPoint/QEยังไม่ได้รับfinal aggregateชุดนี้

**G5 paired live allocation main และ Major Revision ยังไม่ปิด**. ขั้นถัดไปคือfreeze profilesหลังcalibrationครบและเชื่อมseparate-process decision/claim/assessor/executor/verifierก่อนmainตามRQ1/RQ2. Controlใหม่CENTRAL_RULE_MATCHEDใช้choice functionเดียวกันแต่คำนวณที่coordinator; controlเก่าCentral-Matchedเป็นrelay-onlyและใช้แทนกันไม่ได้. ส่วนด้านล่างเป็นdated history ไม่ใช่สถานะปัจจุบัน

## Live update 6 ตุลาคม 2026 เวลา 15:26 น.

**กำลังเรียก real LLM ใหม่ทั้ง ML และ repository ตามงบที่ผู้ใช้อนุญาตแล้ว** ไม่รอเพดาน calls เพิ่ม และยังไม่สรุปว่า Major Revision ปิดแล้ว

- ML ecological calibration snapshot: completed 33/288 คู่, VERIFIED 26, STAGE_CONTRACT_FAILED 3, PROVIDER_UNRESOLVED 3, REPLAY_UNRESOLVED 1; active GLM / CAL_ADULT_02 / preprocess. เป็นสถานะระหว่างรัน ไม่ใช่ final success rate
- Continuation 1 หยุดที่ 22 คู่จาก fresh replay เกิน 360 วินาที เก็บ unresolved เดิมไว้ ตรวจ trusted backend ใน Podman image ที่ถูกต้องผ่าน แล้วเริ่ม continuation 2 เฉพาะ 266 คู่ที่ยังไม่เริ่ม เวลา 15:11 น. lock SHA256 `11eae1a8e6e36f180b826744832e1a2238cea8e1a38368e592814f6877cb020a` กติกาใหม่แยก cleaned workload timeout จาก backend failure และตรวจ health ก่อนเดินต่อ ไม่เปลี่ยน prompts/source/gates/timeout ไม่ retry คู่เดิม
- Offline health probe v1 เคยใช้ default Docker image lock ผิดและจบ exit125; เก็บไว้ แก้เฉพาะ diagnostic launch เป็น v2 ซึ่งผ่าน ไม่เปลี่ยน research outcome
- Repository calibration ใหม่เริ่ม API จริงเวลา 15:19 น.: 6 cases × 3 deployments = 18 คู่; snapshot completed5, VERIFIED3 และ VISIBLE_TEST_FAILED2, active GLM / pandas_37. lock SHA256 `24c9e82cc93f3f177e2e8cff6f580e5212be52c99ceb7ba407f98cefef438d1a`
- Repository baseline/source/no-op/import-sentinel ครบ6 cases และ60 case-specific regression identities ผ่านก่อน calls. Matplotlib10 เพิ่ม pinned pandas/pytz เพื่อรัน2 testsที่เดิม skipped; ใช้ test IDsเดิมทั้ง10 และรักษา original evidence. Context amendment เพิ่ม public formatter excerpts ก่อน LLM ไม่อ่าน gold diff ไม่ใช่ model success
- Local code suite ผ่าน **201 pytest tests** (169 unittest cases รวม6 controller guardsใหม่และ32 pytest-style checks). Git public code ชุดก่อนหน้าถูก push แล้วที่ `b886159`; ชุดใหม่กำลังตรวจและบันทึก ไม่รวม credential/raw responses/candidate artifacts/Office drafts
- สร้าง IEEE v2.3 Progress Rev3 ใหม่ด้วย Microsoft Word: 15รูป,13 native equations,10ตาราง,20หน้า รวม completed supporting ML36 และ repository18 ชุดเดิม แยก ongoing calibration จาก allocation main; กำลังตรวจ rendered pages ไม่ใช้ LibreOffice และไม่ทับ v2.2

ตรวจสถานะสดด้วย `EcologicalMLCalibrationAudit` และ `EcologicalRepositoryCalibrationAudit` ที่ `REPRODUCE_V2_3.ps1` สองชุดนี้ยังเป็น calibration ไม่ใช่ paired live allocation main. ยังต้อง freeze profiles จากผลครบ เชื่อม belt/claim/assessor/executor/verifier และรัน CF-Fit กับ CENTRAL_RULE_MATCHED/Static ตาม RQ1/RQ2 พร้อม ablations. ส่วน snapshot ด้านล่างเป็นประวัติของเวลาที่ระบุ ไม่ใช่สถานะปัจจุบัน

## Live update 6 ตุลาคม 2026 เวลา 14:22 น. — ใช้ส่วนนี้แทน snapshot ถัดไป

**เริ่ม real-LLM ecological calibration แล้ว ไม่ได้รอเพดานงบอีกต่อไป**. ผู้ใช้อนุญาตให้ใช้เท่าที่จำเป็นโดยไม่จำกัดงบ แผน ML ถูกตรึงที่ 24 task specifications × 4 stages × 3 deployments = 288 first-attempt requests; ไม่มี retry เพื่อคัดผลให้ผ่าน เริ่มเรียกจริงเวลา 14:05 น. (07:05 UTC)

- ก่อนตัวรันเดิมหยุดจาก GLM `RemoteDisconnected` ได้ 10 คู่: VERIFIED 7, STAGE_CONTRACT_FAILED 2, PROVIDER_UNRESOLVED 1. ผลทั้งหมดเก็บไว้; คู่ unresolved ไม่ถูกเรียกซ้ำและอาจมีค่าบริการแล้ว
- เดินหน้าด้วย continuation ที่ตรึงแยก **เฉพาะ 278 คู่ที่ยังไม่เริ่ม** เมื่อ 14:22 น. ตัวรันเริ่ม GLM train ของ CAL_ADULT_01 แล้ว ไม่เปลี่ยน prompts/gates/token cap/model mapping และไม่ทับหลักฐานเดิม
- ML execution lock SHA256 `2b9815b3e741783c8e62841380db625e757c72b7031f80fd8cad0e927e58737c`; continuation lock SHA256 `c9b456af9a13c5bea658f7b53b63a09e3f1dcab996830a90ec38a1126b7274c1`. ตรวจสถานะล่าสุดด้วย `REPRODUCE_V2_3.ps1 -Stage EcologicalMLCalibrationAudit` ไม่ใช้ตัวเลข snapshot นี้แทนผลจบ
- Trusted container reference ของ CAL_ADULT_01 ผ่านทั้ง 4 stages ก่อนเรียกโมเดล; labels/gates/reference predictions ไม่อยู่ใน candidate mounts; โค้ดที่โมเดลสร้างรันเฉพาะ locked offline Podman container
- Repository calibration pool ใหม่กำลัง preflight ก่อน provider calls: luigi_4, pandas_37, luigi_18 reproducible; matplotlib_23 environment-excluded; matplotlib_30 กำลังตรวจ ณ snapshot นี้ การเลือกอาศัย environment gates ตามลำดับที่ตรึง ไม่อาศัยคะแนน LLM
- เพิ่ม tests ของ private-score stripping/gates และ continuation: targeted continuation 4/4 ผ่าน; full suite ก่อนเพิ่ม continuation ผ่าน 158 tests ส่วน full `Check` 154 ใน snapshot เก่าเป็นผลก่อนเพิ่ม tests เหล่านี้

นี่คือ **calibration ที่กำลังรัน ไม่ใช่ allocation main หรือปิด Major Revision แล้ว**. หลักฐาน 36/36 ML isolated-stage เดิมและ 18/18 repository เดิมยังแยกจากชุดใหม่ ยังต้อง freeze profiles, เชื่อม live belt/CAS/assessor/executor/verifier และทำ paired main ตาม RQ1/RQ2 ก่อนสรุปผลทางสถาปัตยกรรม ทุนวิจัยผู้วิจัยหลักออกเอง; DPU สนับสนุน APC เท่านั้น

Snapshot ที่บอกว่ายังรอ budget หรือไม่มี calls ใหม่ด้านล่างเป็น **ประวัติก่อน 14:05 น.** ไม่ใช่สถานะปัจจุบัน Word/Git จะรายงานว่าเสร็จเมื่อสร้าง ตรวจ และบันทึกจริงเท่านั้น

## สถานะล่าสุด 6 ตุลาคม 2026 — ใช้ส่วนนี้แทน snapshot ด้านล่าง

**ยังไม่ปิด Major Revision และยังไม่พร้อมส่งจริง**. กรอบหลักคือ decentralized self-selection, capability heterogeneity และ capability–task fit/stand-down โดยงานไหลบนสายพาน ไม่ใช่จำนวน policies หรือวิธี AutoML/bug repair ใหม่. รายละเอียดการตรวจตามที่ปรึกษาอยู่ใน `ADVISOR_ALIGNMENT_V2_3_TH.md`.

- **Repository first-attempt ใหม่ครบ 18/18 คู่ และ provenance audit ผ่าน**: Tencent VERIFIED 4/6, GPT 1/6, GLM 2/6. GLM มี provider-unresolved 1 คู่ และ unfinished/empty 3 คู่; ไม่ลบ failures หรือแก้ patch ให้ผ่าน. หลักฐานฉบับจบคือ `results/repository_first_attempt_v1_audit_20261005.json` ซึ่งสร้างจริง 6 ต.ค. 02:40:12 UTC; SHA256 `06cdd1608af38a7f36470f3af8eac8394ff3bcd9bfda9f5beb17fced9fbf5eba`. หกเคสจากสาม repositories เป็น localized-repair feasibility ไม่ใช่ allocation comparison หรือ difficulty-specific probability calibration.
- **ML isolated-stage v2 จบครบ36/36 คู่**: Tencent VERIFIED11/12, GPT10/12, GLM7/12 รวม28 VERIFIED, 6 failures และ2 provider-unresolved. คู่สุดท้ายจบ6ต.ค.04:07:31UTC และ final capsule สร้าง04:07:53UTC ที่ `results/ml_isolated_stage_pilot_v2_final/`; audit SHA256 `22e37c2b84b4720f970a0bc86b0bd664728f03d85f29906591e49db9b3dba984`. ไม่มี worker/finalizer ของ batch นี้ค้างอยู่. ทั้งสาม specifications เคยถูกใช้แล้วและ predecessors เป็น trusted artifacts เดียวกัน จึงไม่ใช่36 full pipelines, held-out calibration หรือหลักฐานว่ากลยุทธ์จัดสรรงานใดชนะ. รายงานภาษาไทยอยู่ใน `ML_ISOLATED_STAGE_RESULTS_TH.md`.
- **Entry-point Check ล่าสุดผ่าน154 unit tests และจบ exit0** พร้อม frozen matched/proxy/ML/repository provenance audits และ ecological preparation audit. ไม่ใช้API ไม่execute generated candidate code และไม่ใช่main experiment. ปัญหา SQLite connection ไม่ปิดบน Windows ถูกแก้ก่อน rerun; unit tests ตรวจ one-owner/one-task, dependencies, retries, stale completions และ append-only interface.
- **เตรียม ecological v1 แล้ว แต่ยัง live_ready=false**: แยก calibration24ML specifications/main12ML specifications และ repository preflight candidates24รายการ โดยเลือกก่อน outcomes และตัด earlier poolsออก. Identity lock SHAของdesign `bcda309b38d1fb6681e63319c4bdb467594460a6ecb3566ad6249ff8eb809c0b`. ML variantsใช้สองcorpora/row splitsเดิม ไม่ใช่24independent datasetsหรือraw-dataholdout.
- **Offline inputs/reference เตรียมจริง2เคส** `CAL_ADULT_01` (26,049 train rows) และ `CAL_BEIJING_01` (288,369 train rows). Public test inputsไม่มีtarget; labels/reference predictionsแยกเป็น investigator/verifier-only. Numeric trusted referenceรันได้ แต่ยังไม่ได้ผ่าน container-stage preflight สำหรับเคสใหม่และยังไม่มี ecological LLM observations.
- **Correctness probes ใหม่ผ่าน**: 20logical fixture runs/4matched parity scenarios; actual separate-process choice4Agentsเทียบ1coordinatorให้ข้อเสนอตรงกัน; cross-process SQLite CASได้หนึ่งผู้ชนะต่อtaskและไม่ให้Agentเดียวถือสองtasks. เป็น trusted single-host fixture checks ไม่ใช่throughput/latency/fault-tolerance results. Shared claim storeยังเป็นcommon failure domain และยังไม่ได้เชื่อม live assessor/executor/verifierครบวงจร.
- Calibration envelope306generation callsเป็นเพียงขอบเขตการออกแบบ **ไม่ใช่งบที่อนุมัติหรือจำนวนที่จำเป็นต้องรันทุกครั้ง**. ยังรอเพดานcalls/งบ, sample/precision freeze, provider currency/version checks, case gates และ approval quota. รอบทำงานนี้ไม่มี API callsใหม่. คู่มือและคำสั่งofflineอยู่ใน `ecological_v1/README_TH.md`.
- **Word Progress_Rev4 สร้างแล้วทั้ง blind/unblind**: 32 หน้า, 16 รูป, 13 native equations, 10 ตาราง รวม completed repository table และข้อความ Funding: ผู้วิจัยหลักออกทุนวิจัยเอง; DPU สนับสนุน APC. ยังไม่ตั้งเป็นฉบับปัจจุบันที่ตรวจเสร็จ: heading polish จบเฉพาะ blind ก่อนสคริปต์หยุด; rendering เดิมไม่ตรงกับ blind ที่แก้แล้ว และยังตรวจภาพไม่ครบทุกหน้าของทั้งสองไฟล์. การเรียก Word เพื่อทำต่อถูกหยุดโดย automatic approval review เนื่องจาก usage quota. ไม่ใช้เส้นทางอื่นเพื่อข้าม approval.
- **Rev3 ยังเป็นฉบับล่าสุดที่ผ่าน layout QA** แต่ยังเป็น progress manuscript ไม่ใช่ submission-ready. v2.2 และ Rev3 ไม่ถูกทับ. ร่างข้อความภาษาอังกฤษเพื่อคงกรอบที่ปรึกษาอยู่ใน `../AJSTR Journal/v2_3_word_work/ADVISOR_ALIGNED_INSERT_PENDING_EN.md`; ยังไม่อ้างว่าแทรกลง Word แล้ว.

### สิ่งที่ต้องทำต่อโดยไม่เปลี่ยนเรื่องวิจัย

1. เก็บ completed36/36 final capsuleและ repository18/18ไว้; ไม่สั่ง feasibility pairsเดิมใหม่เพียงเพราะ modelไม่ผ่าน.
2. รายงาน isolated stages เป็น supporting execution evidence แยกจาก full-DAG feasibility และ repository results. การใช้ trusted predecessors ทำให้ทุกโมเดลถูกทดสอบทุก stage แต่ไม่ได้พิสูจน์การต่อ pipeline ของ model เองครบทุกขั้น.
3. ปรับคำอธิบาย **soft stand-down** ให้ตรงโค้ด: ลด priority เมื่อเก่งเกินงานและผ่อน penalty ตามอายุงาน ไม่ใช่ high-capability agent ต้องถอนตัวเสมอ.
4. เรียก Central-Matched **เดิม** ว่า matched coordinator-path/dependency control: ใช้ bids/arbitrationเดิมแล้วเพิ่ม relay ไม่ได้ย้ายผู้คำนวณทุกdecision. Controlใหม่ `CENTRAL_RULE_MATCHED` ใช้ pure choice ruleเดียวกัน แต่AgentคำนวณเองในCF-Fit/coordinatorคำนวณในcontrol; correctness probesผ่านแล้ว ยังไม่ใช่live experiment. ไม่แก้ frozen code/resultsเดิม. Shared READY/claim storeยังเป็นcommon dependency.
5. ตรึง budget/sample/precision จากนั้น preflightเคสใหม่และทำ ecological calibrationก่อนสร้างprofiles. Paired live CF-Fit/Central-RuleMatched/Static streams ยังไม่ครบ. RQ1ต้องรายงาน trade-offs throughput/time/utilization/costพร้อมfailures; RQ2คงhomogeneous/heterogeneous contrastและablations. ห้ามใช้stage probesแทนmain allocationหรือfit simulation probabilities และห้ามบังคับให้สามbrandsมีRank1/2/3หากcalibrationไม่สนับสนุน.
6. เมื่อ approval ใช้งานได้ จึง finish Word ทั้งสองฉบับ, scrub blind metadata, render และตรวจทุกหน้า ก่อนเปลี่ยน README_CURRENT หรือส่งไฟล์ว่าเป็นฉบับตรวจเสร็จ.

## ประวัติ snapshot 5 ตุลาคม 2026

ส่วนต่อไปเป็นประวัติเดิมเพื่อ audit ไม่ใช่ live status. ข้อความ 17/18 และยังไม่เริ่ม ML calls ถูก supersede ด้วยสถานะล่าสุดด้านบน.

อัปเดต 5 ตุลาคม 2026. **ยังไม่ใช่ submission-ready และยังไม่ปิด Major Revision ทั้งหมด**. ไม่รวม simulation, microtask และ executable DAG pilot เป็นผลชุดเดียว

## หลักฐานที่ตรวจสอบแล้ว

| ส่วน | ผลที่มี | ขอบเขตที่อ้างได้ |
|---|---|---|
| Matched architecture simulation | 2,160 runs / 1,080 pairs; E0 parity 360/360 และ shared-belt parity 360/360 | เปลี่ยนเฉพาะ coordinator relay ใน simulator; outage เป็น scenario สมมติ ไม่ใช่ outage rate ของ MFEC |
| Message-path prototype | 1,000 serial pairs; local/central median 0.10570/0.20875 ms; load sensitivity 24 sessions / 18,000 requests | Single-host IPC ไม่ใช่ latency ของ LLM/provider/network |
| Evaluator backend ใหม่ | Podman 3.4.4; trusted reference ผ่าน 8/8 variants รวม 32 stages | Harness checks ไม่มี LLM calls; packages เดิมแต่ image ID ใหม่ |
| Ingest environment recovery | Saved Tencent source จาก ADULT_P3/BEIJING_P3 replay ผ่านทั้งสองเคส | แยก Docker launch failure ออกจาก model failure; ไม่มี API calls ใหม่ ไม่ใช่ full jobs |
| Executable ML จริง | Tencent ADULT_P0 ผ่านครบ 4 stages; ROC-AUC 0.927089 บน hidden test 16,281 แถว | ผ่าน frozen feasibility contract ของหนึ่งเคส ไม่ใช่ policy comparison หรือ probability calibration |
| Clean replay | Tencent Adult รันใหม่ครบ 4 isolated stages ได้ predictions/model hashes เดิม | ทำซ้ำ source เดิมได้; ไม่มี API calls ใหม่ ไม่ใช่ independent extra job |
| BugsInPy environment preflight | 6 เคสจาก 3 repos: pandas #88/#76/#128/#27, matplotlib #15 และ luigi #19; buggy relevant test fail / fixed pass ครบ | Recovery เพิ่ม nose ให้ luigi และ build matplotlib แบบ serial; ไม่เปลี่ยน production source/gold patch; thefuck #32 เป็น environment exclusion ใน prefix 7 รายการ |
| Gold-free candidate/verifier preflight | 6 candidate images ไม่มี fixed tree/history/gold/tests; verifier แยกกัน; 60 frozen regression items มี 58 active passes และ 2 historical expected failures บนทั้ง buggy/fixed | Withheld public tests ไม่ใช่ novel hidden tests; expected failures ไม่นับเป็น passes; ดู `results/repository_baseline_gate_v2/audit.json` |
| Repository MFEC pilot v1 | ครบ 18 jobs / 36 attempts; 0 verified, 18 DEAD_LETTER | 12 GPT outputs ไม่ผ่าน strict diff format; 24 Tencent/GLM outputs จบด้วย length และ content ว่าง; ยังไม่ใช่การวัดว่าซ่อมบั๊กไม่ได้เมื่อ patch format ใช้งานได้ |
| Offline decoder diagnostic | ครบ 36 recorded attempts; 24 unrecoverable, 10 visible-test failures, 2 verified attempts เป็น GPT pandas #76 เคสเดียว | เปลี่ยน metadata เท่านั้น ไม่มี API calls เพิ่ม; หนึ่ง unique recovered job ไม่ใช่สอง successes อิสระ และไม่เปลี่ยน 0/18 ของ v1 |
| Revised output-contract sentinel | ครบ 3 calls บน pandas #88 ที่เคยใช้แล้ว: GLM VERIFIED, GPT VISIBLE_TEST_FAILED, Tencent UNFINISHED_OR_EMPTY_OUTPUT | Exact edits → canonical diff → guard เดิม; cap 32,768 เท่ากัน; เคสซ้ำ ไม่ใช่ calibration/main |
| Offline checks | Suite ผ่าน 116 tests เมื่อ 5 ต.ค. 10:38 UTC; timeout-cleanup unit test ที่เพิ่มภายหลังผ่านใน targeted suite 4/4 | ตรวจ contracts/provenance ไม่แทน ecological main; จำนวนล่าสุดดู `Check` |

## Pilot ใหม่และ failures

`ml_dag_pilot_v3_lock.json` freeze ก่อน calls: 2 reused P0 corpus cases × 3 models = 6 jobs, token cap 16,384 เท่ากันทุกโมเดล, ไม่เกิน 2 attempts/stage หรือ 48 calls รวม. ไม่แก้ source ให้โมเดล ไม่เปลี่ยน quality gate และไม่ rerun จนเลือกเจอผลบวก

ครบ 6 jobs แล้ว: Tencent Adult VERIFIED; GPT Adult DEAD_LETTER ที่ preprocess; GLM Adult PROVIDER_UNRESOLVED; GPT Beijing DEAD_LETTER ที่ train; Tencent Beijing train เกิน 360 วินาทีจึง ENVIRONMENT_UNRESOLVED; GLM Beijing DEAD_LETTER เพราะ output truncated ทั้งสอง preprocessing attempts. รวม 20 provider attempts, 1 verified job, 3 dead letters และ 2 unresolved jobs. Audit snapshot: `results/ml_dag_pilot_v3_audit_20261005.json`. นี่ไม่ใช่ independent dataset success probability

Cost ใช้ provider-reported units ไม่ตีเป็น USD; provider timeout อาจมี billable outcome ไม่ทราบ จึงห้ามเรียกผลรวมที่มีว่า total billed cost. Mapping hashes ไม่ยืนยัน immutable vendor snapshots. ไม่ส่ง API key เข้า candidate containerหรือบันทึกลงไฟล์

## งานที่กำลังทำ

1. v3 batch ทั้ง 6 jobs จบและผ่าน provenance audit แล้ว; clean replay ของ Tencent Adult ผ่านโดยไม่มี API calls เพิ่ม
2. Environment recovery, gold-free baseline และ no-op identity smoke ผ่านครบ 6 เคส/3 repos; MFEC repair pilot v1 จบครบแล้วและ provenance audit ผ่าน ดู `results/repository_repair_pilot_v1_audit_20261005.json`. รวม 627,649 input tokens, 397,841 output tokens, cost 0.369205896 provider-reported units (ยังไม่ยืนยันสกุลเงิน)
3. **Post-hoc decoder diagnostic จบและ audit ผ่าน**. จับ old context ที่ตรงทุก byte และมีตำแหน่งเดียว ไม่มี gold source และไม่แก้ addition/deletion ของโมเดล; ผล v1 ไม่ถูกเขียนทับ. เก็บ Windows lock ที่หยุดก่อน tests และ Linux recovery capsule แยกไว้ครบ. หลักฐาน `results/repository_decoder_replay_v2_audit_20261005.json`
4. **Revised-contract sentinel จบและ audit ผ่าน**. Exact replacements ไม่ต้องให้ LLM คำนวณ hunk counts; GLM pandas #88 ผ่าน visible + regression + fresh replay. ชุด regression ของเคสนี้มี 8 active passes และ 2 historical xfails ไม่ใช่ 10 passes. GPT รูปแบบผ่านแต่บั๊กไม่ผ่าน; Tencent length/content ว่าง. รวม 25,793 input / 37,601 output tokens และ 0.029603642 provider units. หลักฐาน `results/repository_contract_smoke_v3_audit_20261005.json`
5. **New-case preflight/candidate/identity gates ผ่านครบแล้ว**: 12 frozen pool records ได้ Luigi #31/#17, Matplotlib #18/#9, Pandas #166/#147 รวม 6 reproducible cases; Matplotlib #3 เป็น environment exclusion และ 5 quota skips. ไม่ซ้ำ exposed prefix. ก่อน calls มี transport recovery และ pre-outcome cardinality amendments แยก: Luigi #17 ใช้ทั้งหก regressions/ต้องหก active passes; Matplotlib #9 ใช้ทั้งเจ็ด numerical/API regressions/ต้องเจ็ด active passes. อีกสี่เคสใช้สิบรายการเดิม. รวม 53 selected regression identities เป็น active passes บน buggy/fixed baselines. ไม่ทิ้ง failing test ไม่ดูผล LLM. `results/repository_calibration_candidates_final_v4/` carry ห้า passed summaries แบบ byte-identical; ไม่ถือ copies เป็น extra observations. No-op และ trusted mutation import checks ผ่านครบหกเคส. Preparation lock `c39ad67d1a2f394c5c84769421bfea2f40c3649d3eaff7bf2c332d8283244cf7`; model protocol lock `0ee455b30ea4db37878d0b7e235c2e128a265dcd406db56d70e7e0ae3bc9d144` freeze ก่อน calls
6. **MFEC first-attempt ใหม่เริ่มจริงแล้ว** เมื่อ 5 ต.ค. 10:08 UTC: 6 cases × 3 aliases = 18 planned pairs, one call/pair, 32,768 output tokens และ 720 s/provider limit เท่ากัน. สาม alias workers รันตาม frozen case order; ledger อยู่ `candidate_workspaces/repository_first_attempt_v1/ledger_agent_*.jsonl`. สถานะ ณ audit 10:42:30 UTC: completed 17/18; Tencent ครบ6/verified4, GPT ครบ6/verified1, GLM completed5/verified2 มีหนึ่ง provider-unresolved และสอง unfinished/empty; GLM Matplotlib #9 ยังรัน. ตรวจล่าสุดด้วย `RepositoryFirstAttemptAudit` ไม่ใช้ snapshot นี้แทน live status. เป็น descriptive localized-repair first attempts ไม่ใช่ main allocation, difficulty-specific calibration หรือ simulator parameter fit
7. Word v2.3 **Progress_Rev3** ทั้ง blind/unblind สร้างด้วย Microsoft Wordแล้ว: 30 หน้า, 16 รูป, 13 native equations, 9 ตาราง; รวมผล original repository pilot, offline decoder และ sentinel แยกกัน พร้อมอ้างอิง primary BugsInPy. ตรวจ PNG ทุกหน้าแล้วทั้งสองฉบับและ structural/render provenance ผ่าน; ไม่ทับ v2.2/Rev1/Rev2. Word PDF export ค้างจึงใช้ native Word EMF→GDI สำหรับ layout QA; final PDF/journal packaging ยังต้องตรวจอีกครั้ง. Rev4 builder พร้อมรับเฉพาะ completed18/audit-passed snapshot ไม่แทรก partial table
8. **ML isolated-stage preparation ผ่านครบ12/12** เวลา 10:37:31 UTC, ไม่มี provider calls. การตรวจ exposure เพิ่มพบ legacy provider artifacts บน ADULT_P1/BEIJING_P1/ADULT_P2 แม้ไม่มี request-started file. จึงเก็บ v1 lock/preparation ที่ยังไม่มีpaidcallsไว้ และ freeze **v2 corrected reused-specification protocol** ก่อน calls: `43b8b53f45e0aa05297454583737d564fdac6758fe988b00f5e15cb755647ffa`. ชุดถัดไป3specs ×4stages ×3aliases =36first attemptsภายใต้v2 ไม่ใช่ first-ever attempts. Carry trusted referencesด้วยprovenance ไม่ใช่12observationsใหม่. ทั้งสามaliasesได้input/predecessorsเดียวกัน; semanticordinal mappings, fresh-processmodel/predictionquality และ replay. เป็นinterface-controlledfeasibilityบนสองcorpora ไม่ใช่held-out/difficultycalibrationหรือmain. ยังไม่เริ่ม paid calls ณ10:49UTC; รอrepositorybatchจบเพื่อไม่เพิ่มproviderloadกลางbatch. ดู `ML_ISOLATED_STAGE_PILOT_V2_PROTOCOL_TH.md`; exposureinventoryอยู่ `results/ml_isolated_stage_v2_exposure_inventory_20261005.json`

## Gap ก่อนส่งจริง

- Repository repair: output contract revision ใหม่มี localized repair ที่ผ่าน แต่ยังเป็น reused feasibility case. ชุดใหม่ต้องผ่าน candidate isolation/regression/identity smoke ก่อน model calls และต้องเก็บ failures ทั้งหมด. Public withheld tests ไม่ใช่ independent novel hidden tests
- Ecological calibration: held-out executable stages/jobs และ frozen rank/probability gates; ไม่เอา small conditional pilot ไป fit simulation probabilities
- Main allocation: paired CF-Fit/Central-Matched/Static DAG streams, ทีม/validators/budgets/backendเดียวกัน, สุ่ม arm order และเก็บ failed/unresolved jobs ทุกงาน
- Overhead/fault domains: local IPC proxy ไม่ใช่ E1 provider distribution หรือ production outage proof; shared READY/claim storeยังเป็น common dependency
- Harness: timeout ต้องหยุด container จริงด้วย per-attempt name/cidfile; Tencent timeout ถูกหยุดแบบเจาะจงและเก็บ original report ไม่แก้ frozen runnerกลาง batch
- Manuscript: ตาราง/CI ตรง audit; assumptions แยก empirical estimates; ไม่อ้างว่าการไม่มี global matcher ทำให้ไม่มี single point of failure ทั้งระบบ

Entry point `../REPRODUCE_V2_3.ps1`: `Check`, `PodmanVerify`, `PilotV3Audit`, `RepositoryPilotAudit`, `BugsPreflightStatus`; `PilotV3Execute`/`RepositoryPilotExecute` ต้องใช้ `-ConfirmPaidRun` และปฏิเสธงานที่มีอยู่แล้ว; `RepositoryDecoderReplay` ไม่มี API calls. ประวัติเดิมอยู่ใน `STATUS_HISTORY_20261004_TH.md`; backend details อยู่ใน `PODMAN_RUNTIME_RECOVERY_TH.md`

Stages ใหม่: `RepositoryContractAudit`, `BugsCalibrationPreflightStatus` เป็น read-only. `BugsCalibrationPreflightExecute` ใช้สำหรับ workspace สดหลัง freeze เท่านั้น; จะปฏิเสธการ launch ซ้ำเมื่อมี ledger แล้ว. Worker ที่เริ่มบนเครื่องนี้ยังรันอยู่ ให้ดูผลตามสถานะจริง ไม่ใช้คำว่า ready แทน completed
