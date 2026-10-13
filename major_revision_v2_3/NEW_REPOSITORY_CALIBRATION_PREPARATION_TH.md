# การเตรียมบั๊กใหม่เพื่อเก็บ first-attempt observations

ตรึง 5 ตุลาคม 2026 ก่อน preflight และก่อน model calls. Preflight จบแล้ว ได้ 6 bugs: Luigi #31/#17, Matplotlib #18/#9, Pandas #166/#147. จาก pool 12 records มี 6 reproducible, 1 environment exclusion (Matplotlib #3 import/collection error บนทั้ง buggy/fixed) และ 5 quota skips. ยังไม่ใช่ผล calibration หรือ main policy comparison

## เหตุผลและการเลือกตัวอย่าง

เคส feasibility เดิมถูกใช้ปรับ environment และ output contract แล้ว จึงไม่เหมาะเป็น held-out estimate. ใช้ metadata pool เดิมที่ freeze ไว้ แต่ตัด prefix 7 รายการที่เคย preflight ออกทั้งชุด. กำหนด scope จาก harness support ก่อนรู้ผลใหม่: Python 3.8, invocation เป็น `pytest` และ test target เดียว, ในสาม repos ที่มี profile รองรับ. เรียง `selection_hash` ภายในแต่ละ repo แล้วสลับ Luigi → Matplotlib → Pandas. รายชื่อสูงสุด 4 ต่อ repo รวม 12 รายการถูกบันทึกใน manifest ก่อน execute

เลือกสอง cases แรกที่ buggy relevant test fail และ fixed pass ในแต่ละ stratum. ไม่ดู model outcomes, gold patch content หรือความง่ายของการซ่อมเพื่อเลือกตัวอย่าง. Candidate ที่ไม่ผ่าน environment ต้องมี record พร้อม logs; เมื่อ stratum ได้สองเคสแล้ว รายการที่เหลือใช้สถานะ `not_requested_stratum_quota_met` ไม่เรียกเป็น failed test. หากครบ budget แล้วยังไม่พอ ให้หยุด ไม่สลับ repo หรือเลือกเคสตามใจภายหลัง

ใช้ Python 3.8.20 และ minimal dependency pins ที่เปิดเผยแล้ว; Luigi เพิ่ม nose 1.3.7, Matplotlib build แบบ serial ก่อนเริ่มชุดใหม่. จึงไม่ใช่ exact historical environment reproduction. Images ระยะนี้มี fixed source สำหรับ trusted validators เท่านั้น **ห้ามใช้เป็น candidate image**

## ขั้นต่อไปก่อนเรียก LLM

1. Audit frozen manifest/config/runner และ actual buggy/fixed XML ของทุก selected case
2. สร้าง final candidate images จาก buggy production source เท่านั้น; แยก verifier image และไม่ใส่ gold/history/tests ใน candidate. Declare source-localization basis โดยไม่ปกปิดว่าให้ข้อมูลตำแหน่งไฟล์อย่างไร
3. Freeze public regression identities ก่อนเห็น outcomes. ตรวจ same buggy/fixed dispositions, active passes, expected failures และห้ามเลือก test ใหม่เพราะอันเดิมไม่ผ่าน
4. No-op identity smoke เพื่อยืนยัน verifier อ่าน candidate source จริงและยังตรวจพบ original bug
5. Freeze first-attempt prompt, common generation budget, model mapping, request ceiling, exclusions และ ledger schema ก่อน calls. ไม่ reuse prior patches หรือ visible failure feedback จาก feasibility ใน prompt
6. ทุก frozen alias ทำทุก eligible case ครั้งเดียว. Format, truncation, apply, visible/regression failure และ provider uncertainty ต้องอยู่ใน denominator ตาม declared rule; ห้าม retry จนได้ success

## ขอบเขตสถิติ

ระยะแรกมีเพียง 6 cases/model. รายงาน observed verified rate และ Wilson 95% interval แบบ descriptive โดยระบุ repository clusters; ไม่เรียกเป็น precise estimate ของความสามารถทุก vendor หรือ fit difficulty coefficient D1-D3 จากหกเคสนี้. ไม่มี independent human labels ในระยะนี้ และไม่แทน stage-isolated ML calibration. ถ้าใช้เป็น probability source ให้จำกัด estimand เฉพาะ frozen localized-repair protocol และ supported task population พร้อม uncertainty; main cases ต้องแยกออกจาก calibration cases

หลักฐานอยู่ใน `results/bugsinpy_calibration_preflight_v1/`; แยก individual build artifacts ใน `results/calibration_preflight_v1_*/`. ตรวจสถานะด้วย `../REPRODUCE_V2_3.ps1 -Stage BugsCalibrationPreflightStatus`. การ preflight นี้ไม่มี API calls

## Candidate และเครื่องมืออ่าน context

Freeze `build_repository_calibration_candidates_v1.py` ก่อนสร้าง final images. Source allowlist มาจาก buggy traceback/public API; เป็น investigator-localized repair ไม่ใช่ autonomous navigation. Numerical/API regression scope ตัด functions/classes ที่มี image-comparison decorators/fixtures โดย AST ก่อน outcomes เพราะ minimal environment ใช้ system FreeType ต่างจาก historical image baselines. Hash sort identities ที่เหลือและใช้สิบรายการแรก; ไม่แทนรายการที่ fail. ต้องมีอย่างน้อยแปด active passes และ identical buggy/fixed dispositions; xfail ไม่ใช่ pass

รอบแรกหยุดที่ Matplotlib #18 เพราะ large JSON stdout ถูกบันทึกไม่ครบ. ไม่แก้ frozen builder และไม่ลบ artifacts. `build_repository_calibration_candidates_recovery_v2.py` เป็น instrument recovery แยก: AST filter เดิมทำงานใน trusted container แล้วส่งเฉพาะรายชื่อ functions; cases/source/tests/hash rule/baseline gates ไม่เปลี่ยน. ผลของ recovery ไม่ใช่ independent experiment. Context production source และ visible test excerpt ใช้ bind-report JSON file เพื่อหลีกเลี่ยง large stdout transport; full source ไม่ถูก execute บน host

`prepare_repository_first_attempt_v1.py` ต้องผ่าน identity checks ทั้งหกเคสก่อน calls. Source <=60,000 characters ส่งเต็ม; ไฟล์ยาวใช้ public-API AST excerpts ตาม symbols ที่ประกาศไว้และ cap 160,000 characters. Full buggy source เป็น canonical edit target. วิธี localization/excerpts ถูกเปิดเผย ไม่ใช้ fixed source, gold diff หรือผลโมเดลเลือก snippets

ก่อนเห็นผล Luigi #17 regressions พบว่าไฟล์ relevant มีเพียงหก tests อื่น จึง freeze `build_repository_calibration_candidates_amendment_v3.py` แยก. เคสนี้ใช้ทุกหกรายการและต้องมีหก active passes; อีกห้าเคสใช้สิบเหมือนเดิม. ไม่เปลี่ยน test เพราะ fail ไม่ใช้ผล LLM คัด case และไม่ลบสองรอบเดิม. Identity มีทั้ง no-op ที่คง original failures/regression dispositions และ trusted sentinel mutation ที่ต้องแสดงว่า source ที่ส่งถูก import จริง. Mutation ไม่ใช่ repair และไม่นับเป็น model result

หลัง collection ของ Matplotlib #9 (ยังไม่รัน regressions) พบ numerical/API items เจ็ดรายการ จึง freeze final cardinality amendment `build_repository_calibration_candidates_final_v4.py` ใช้ทุกเจ็ดและต้องเจ็ด active passes. Carry ห้า closed/passed baseline artifacts จาก v3 แบบ byte-for-byte พร้อม SHA256 และ original artifact directory; ไม่รันห้าเคสซ้ำ ไม่ถือ copies เป็น independent observations. อีกสี่ cases ที่มีพอใช้สิบรายการเหมือนเดิม. Final total จะเป็น 53 selected regression identities หากครบ gates; ต้องอ่าน actual counts ไม่สมมติว่าผ่านแล้ว. เคส Matplotlib #9 visible bug test เป็น public PNG image regression ที่ buggy/fixed contrast ผ่านใน declared environment; numerical-only filter ใช้สำหรับเพิ่มเติม withheld regressions ไม่ใช่เปลี่ยน visible target

## ชุด first-attempt ที่จะเรียกจริง

`run_repository_first_attempt_v1.py`: 6 new cases × 3 frozen aliases = 18 planned pairs, แต่ละ pair ครั้งเดียว; output cap 32,768 / temperature 0 / provider limit 720 s / test limit 180 s เท่ากัน. Exact-text JSON edits → canonical diff → unchanged guard → visible/regression → fresh visible/regression replay. ไม่มี source repair โดยผู้วิจัยและไม่มี automatic provider retries. ผล unresolved ยังอยู่ใน operational denominator พร้อม conservative bounds; missing ไม่ถูกตีเป็น failed/completed. ไม่รวมกับ 18-job feasibility, offline decoder หรือ reused sentinel. รายงาน cluster caveat และ Wilson intervals เป็น descriptive เท่านั้น ไม่ยกระดับ Ability Rank หรือ fit simulator curve จาก n=6

Audit/status entry point: `RepositoryFirstAttemptAudit`; single-pair paid execution: `RepositoryFirstAttemptExecute -CaseId <frozen_case> -ModelSlot <slot> -ConfirmPaidRun`. ไม่มี API key ใน configs/artifacts. ชุดนี้ต้อง freeze prompt/model/validators ทั้งหมดก่อนเริ่ม calls และต้องมี ledger ครบก่อนสรุป rate. ชุด main ต้องใช้ cases ที่แยกออกต่างหาก
