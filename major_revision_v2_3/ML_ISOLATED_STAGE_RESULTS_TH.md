# ผล ML isolated-stage v2 ที่จบแล้ว

ชุด36คู่จบ6ตุลาคม2026 เป็น supporting execution evidence ไม่ใช่ main allocation experiment หรือ held-out probability calibration. ไม่ทับผลv2.2หรือfeasibility revisionก่อนหน้า.

## ทำไมต้องแยก stages

ถ้าทดสอบเฉพาะfull DAG เมื่อingestไม่ผ่าน โมเดลจะไม่มีโอกาสทำpreprocess/train/package การนับขั้นที่ยังไม่ถูกเรียกว่าmodelfailureจึงผิด. ชุดนี้ให้ทั้งสามโมเดลได้public inputsและtrusted predecessorsเดียวกันในทุกstage เพื่อทดสอบstage execution/artifact interoperability โดยไม่ให้ผลต้นทางปิดบังขั้นถัดไป.

เลือกสามspecificationsที่เปิดเผยว่าเคยใช้แล้ว: AdultP1/AdultP2/BeijingP1 จากเพียงสองcorpora. รุ่นv1ยังไม่ได้เรียกAPIและเก็บไว้แยก; v2freezeก่อนcallsพร้อมlegacy-exposureinventory. ดังนั้นชุดนี้ไม่ได้พิสูจน์ว่าโมเดลสร้างpipelineของตนเองครบสี่ขั้น.

## ผลครบ36/36

| Alias | Ingest /3 | Preprocess /3 | Train /3 | Package /3 | VERIFIED /12 |
|---|---:|---:|---:|---:|---:|
| tencent-hy3 | 2 | 3 | 3 | 3 | 11 |
| gpt-5-mini | 3 | 2 | 2 | 3 | 10 |
| glm-5.3-flash | 2 | 1 | 1 | 3 | 7 |

รวม28VERIFIED, 3stage-contractfailures, 3generation-contractfailures และ2provider-unresolved. One callต่อplanned pair; outputcap32,768/temperature0/boundedverifierเหมือนกัน. Sourceที่ผ่านต้องผ่านfresh replayด้วย; replayไม่ใช่extraobservation. ไม่แก้candidateให้โมเดลและไม่retryเพียงเพื่อให้ได้success.

Provider-unresolvedไม่ใช่โค้ดที่ถูกตรวจแล้วและล้มเหลว. เก็บไว้ในplanneddenominatorของobserved operational completion แต่แยกผลที่ไม่ทราบ. VERIFIED28/36=77.8%; unknown-outcome boundsคือ28/36ถึง30/36=83.3% เป็นlogicalboundsไม่ใช่confidenceinterval. Variants/stagesสัมพันธ์กัน ไม่ใช่36independent fulljobs.

## ทรัพยากรที่บันทึกได้

Returned responses34, input77,899tokens, output372,642tokens, provider-reportedcost0.250668134units. ยังไม่ยืนยันcurrencyและสองcallsมีunknownbillableoutcome จึงไม่ใช่totalbilledcostและห้ามเขียนเป็นUSD. Sandboxqueue/serializationเป็นharnessoverhead ไม่ใช่หลักฐานthroughputของทีมที่ทำงานพร้อมกัน.

## ใช้เขียนpaperได้แค่ไหน

ใช้แสดงว่าbounded execution/verifierรองรับMLstagesจริงบางส่วนได้ และเปิดเผยfailure modesครบ. แยกจากfull-DAGpilotที่TencentAdultผ่านหนึ่งjob และจากrepositoryfirstattempt18pairs. ห้ามรวมdenominatorsหรือเรียกเป็นmainpolicycomparison.

ยังไม่ใช่ที่มาของuniversalAbilityRank, difficulty-specificprobabilities หรือsimulationEquation7. ยังไม่พิสูจน์CF-FitชนะCentral/Static. Contributionยังเป็นdecentralizedself-selection + capabilityheterogeneity + fit/softstand-down บนREADYbelt; MLexecutionเป็นเครื่องมือทดสอบ. RQ1เป็นtrade-offs; RQ2และablationsต้องทดสอบteam/mechanismcontrastsแยก.

ขั้นถัดไปคือตรึงbudget/sample/precision, preflightspecificationsใหม่, ทำcalibrationเพื่อได้profilesพร้อมuncertainty แล้วpairedliveallocationตามcontrolsที่แยกผู้คำนวณdecisionจริง. Preparedpoolเป็นtask-specificationholdoutเท่านั้น ไม่ใช่raw-dataholdout.

## ตรวจซ้ำ

จากworkspace root:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage MLIsolatedStageAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage Check
```

Final capsule: `results/ml_isolated_stage_pilot_v2_final/`; auditSHA256 `22e37c2b84b4720f970a0bc86b0bd664728f03d85f29906591e49db9b3dba984`. อ่าน `RESULTS.md` สำหรับภาษาอังกฤษและ `summary.json`/`audit.json` สำหรับmachine-readableevidence. ห้ามเรียกfinalizerทับcapsuleที่มีแล้ว. WordRev4ยังไม่อัปเดตผลนี้และยังไม่ผ่านfinalpageQA; งานWordต่อยังติดapprovalquota.
