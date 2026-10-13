# การเชื่อมสายพานกับ decision processes และ execution interface

## Event-driven fixture check 6 ตุลาคม 2026 เวลา 22:45 น.

เพิ่ม `integration_backend_v2.py` ให้ parent event loop รับผล claim ของแต่ละ agent แล้วเริ่ม trusted execution ทันที โดยไม่รอ claim responses ของทั้งทีมก่อน dispatch. CF-Fit ยังให้ agent process คำนวณข้อเสนอเอง; `CENTRAL_RULE_MATCHED` ยังให้ coordinator process คำนวณด้วย pure choice rule เดียวกันแล้วส่ง nomination; Static owner ตรึงก่อนรัน. ใช้ SQLite CAS, READY belt, dependencies, verified artifacts, bounded failure และ hash-chain ledger เดิม. `check_integration_backend_v2.py` ผ่านห้า arms และ upstream failure/unknown ใน NEW output `integration_event_checks_20261006_v1/`; targeted test พิสูจน์ว่า execution_started ของ agent เร็วเกิดก่อน agent ช้าส่งคำตอบ. ทุกรายการเป็น trusted fixture, ไม่มี MFEC calls, ไม่มี candidate code, ไม่มีตัวเลข performance ที่ใช้เป็นผลตีพิมพ์

ยังต้องเชื่อม paid assessor/executor/verifier, calibrated profiles, full pipeline artifacts, late-return settlement, common paired streams และการตรวจ provider/resource accounting ก่อนทดลอง allocation main. Shared SQLite ยังเป็น failure dependency. Snapshot/claim semantics เปลี่ยนตาม event time จริง จึงต้องบันทึก snapshot hashes และ paired block order ก่อน paid main; fixture parity ไม่ใช่การพิสูจน์ผล real LLM

อัปเดต 6 ตุลาคม 2026. สร้าง backend fixture แยกจาก frozen calibration controllers เพื่อเตรียม paired real-LLM main ระหว่างที่ ML calibration ยังรันอยู่ ไม่มี API calls จาก integration checks และไม่มีการรันโค้ดที่ LLM สร้างใน host

`integration_worker_v1.py` ทำ CF choice และ SQLite claim ใน process ของ agent เดียวกัน ฝั่ง CENTRAL_RULE_MATCHED ให้ coordinator process ใช้ pure choice functionเดียวกันแล้วส่ง nomination ให้ agent claim โดยไม่เลือกใหม่ ผู้เชื่อมระบบไม่ sort proposals แล้วเลือกผู้ชนะ แต่ compare-and-swap ใช้ arrival order จริง Static owner mappingกำหนดก่อนรัน ทุกเส้นทางใช้ store/execution seamเดียวกัน ไม่มี model keyในdecision subprocess environment

`integration_backend_v1.py` ต่อ dependency-ready frontier → decision processes → shared atomic claim → concurrent trusted fixture executor → verifier completion → predecessor artifact digest → terminal job accounting มีappend-only SQLiteeventsและhash-chain JSONL แยกจากoutputsของcalibration. No-Fitเอาเฉพาะfit distanceออก; No-StandDownเอาเฉพาะoverqualification penaltyออก

Targeted6unit testsผ่านในรุ่นแรก: actual decision locus, dependency artifacts, concurrent static execution, bounded upstream failure, provider-unknown propagation, no-volunteer และledger mutation/overwriteguards. Integration probeแรกอยู่`integration_checks_20261006_v1/`และผ่าน5successful-DAG arms + upstream failure/unknown. ต่อมาปรับเฉพาะfixture no-volunteer counterให้count once/tickและนับเฉพาะเมื่อไม่มีeligible agent ไม่รวมcapacity contention; ต้องใช้NEWprobe directoryสำหรับรุ่นปัจจุบัน Sourcehashในcapsuleเดิมคงเดิมและไม่ใช่ผลLLM

ยังไม่ใช่G5mainหรือproofของproductiondistributedsystem: profilesเป็นfixture values,clock100ms/backoff20msเป็นdiagnostic-only settings, executors/verifiersเป็นtrusted fixturesในthreads ไม่ใช่live adapters. ไม่มีpaidlaunchrouteในbackendนี้ ไม่รายงานเวลาของfixtureเป็นthroughput/time/costของLLMจริงหรือผลfault-tolerance. SharedSQLite/storeยังเป็นcommon failure domain และverify seamยังไม่ใช่authenticated production verifier

Fixtureนี้ยังรวบรวมclaimresponsesต่อcommon snapshotก่อนdispatchไปexecutionthreads. ก่อนpaidmainต้องเปลี่ยนเป็นevent-drivenworker/completionเพื่อไม่ให้claim-roundbarrierหรือstragglerสร้างglobalproviderbarrier. Passingfixtureไม่ใช่การยืนยันว่าproductionlatency/concurrencyครบแล้ว

ก่อนmainยังต้องทำดังนี้:

1. ปิดcalibrationพร้อมfullplannedaccountingและfreezeempiricalprofiles/uncertainty. ไม่ใช้partialratesเลือกwinnerหรือบังคับสามmodelsให้ได้Rank1/2/3ต่างกัน
2. ต่อMFECassessor/executorและcontainerverifierที่แยกcandidate artifactsจากDB/key/labels/tests. MLmainต้องใช้artifactsจากทีมจริงไม่ใช่trustedpredecessorsของcalibration
3. Freezecommonwallclock/arrivalstreams/teams≤4/token/resources/attemptdiversity/observationdeadline/armorderและanalysisก่อนcalls. ระบุ256MiBartifactcapและlimitsอื่นทั้งหมดในprompt
4. ตรวจend-to-enddrysentinel,providerdrift,latecallbacks,deadlinebilling,immutablepredecessorsและfull-jobaccounting. Fixtureนี้ปฏิเสธactiveworkที่เลยhorizonโดยpreserveincompleteevidence;ยังไม่มีpaidlate-returnsettlementrule
5. รันpairedCF-Fit/CENTRAL_RULE_MATCHED/StaticและRQ2/fit/stand-downablationsหลังgatesผ่าน แยกcontrolนี้จากrelay-onlyCentral-Matchedเดิม. ผลใกล้กันไม่ใช่equivalenceและไม่ใช่system-widefailuretolerance

คำสั่งตรวจintegrationรุ่นปัจจุบันแบบofflineโดยเลือกNEWoutputpathภายในecological_v1:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage EcologicalIntegrationCheck -OutputPath 'major_revision_v2_3/ecological_v1/integration_recheck_01'
```
