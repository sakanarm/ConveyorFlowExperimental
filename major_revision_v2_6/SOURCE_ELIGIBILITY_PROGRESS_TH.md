# v2.6 — สถานะแหล่งข้อมูลก่อน Real-LLM main experiment

สถานะ ณ 12 ตุลาคม 2026: **ยังไม่ freeze main cohort และยังไม่เรียก LLM สำหรับ v2.6**. งานในไฟล์นี้คือ source eligibility เท่านั้น ไม่ใช่ผล RQ1/RQ2 หรือหลักฐานว่า CF-Fit ชนะ baseline.

## 1. ป้องกันการใช้เคสเดิมเป็นเคสใหม่

`build_prior_exposure_ledger_v1.py` ตรวจ `request_started.json` ในรากหลักฐาน v2.3–v2.5 ทั้ง workspace และ `D:\ConveyorFlowRuntime`. พบ 1,108 markers, ครอบคลุม 43 repository cases และ 4 ML corpora; marker นับเป็น prior exposure แม้การเรียก provider จะไม่สำเร็จ. ไม่มีรากที่กำหนดหายหรือ marker ที่จับคู่ case/corpus ไม่ได้. แหล่งข้อมูลคือ `prior_exposure_ledger_v1.json` ซึ่งเก็บเพียง relative path และ SHA-256 ของ marker ไม่เก็บ prompt, response หรือ API key. **จำนวน markers/API calls ไม่ใช่จำนวนตัวอย่างอิสระ**.

`build_unexposed_candidate_queue_v1.py` ตรึงลำดับ hash ของทุก project/case จาก BugsInPy manifest โดยข้าม 43 เคสที่เคยเรียก LLM. ทั้ง 17 project มีอย่างน้อย 2 *metadata candidates* ที่ยังไม่ exposed; คำว่า metadata candidate ไม่ได้หมายความว่ารัน test ใน container ได้. ดู `unexposed_candidate_queue_v1.json`.

## 2. Container preflight ตามคิวที่ตรึงไว้

| Project | คิวที่ตรวจ | buggy-fail/fixed-pass | สถานะ project สำหรับเกณฑ์ 2 เคส |
|---|---|---|---|
| PySnooper | `PySnooper_2`, `PySnooper_1` | ไม่มี | ไม่ผ่านภายใต้ verifier ที่ freeze ไว้; เคส 2 import fixture `mini_toolbox` ไม่ได้ใน buggy state, เคส 1 ผ่านทั้ง buggy/fixed |
| sanic | `sanic_5`, `sanic_3` หลัง amendment v1c | ทั้งสองเคส | ผ่าน **public-test contrast gate** เท่านั้น; gold-free candidate, regression และ independent audit ยังไม่เสร็จ |

รายละเอียด Sanic ที่ต้องไม่ลบออกจาก audit trail:

1. v1 ตรวจครบ 5 เคสตามคิว: `sanic_5` ผ่าน, อีก 4 เคสไม่ผ่านเพราะ import failure ทั้ง buggy/fixed (`httpx` 3 เคส, `requests_async` 1 เคส). เก็บ lock/ledger และ raw evidence ไว้.
2. v1b เพิ่ม `httpx==0.9.3` และ `requests-async==0.5.0` จาก public requirements ให้ทุกเคส แต่หยุดหลัง build แรกเพราะ package index ไม่มี `requests-async==0.5.0`. ไม่อ้างว่าเป็นผลทดสอบเคสที่เหลือและไม่ทิ้งหลักฐานนี้.
3. v1c เพิ่มเฉพาะ `httpx==0.9.3` ซึ่งมีให้ติดตั้ง และเริ่มคิวเดิมใหม่ทั้งหมด; `sanic_5` และ `sanic_3` ผ่าน buggy-fail/fixed-pass จึงหยุดตามกฎ “2 เคสแรกที่ผ่าน”. `sanic_1` ระบุ `httpx==0.11.1` ใน metadata จึงยังมี environment deviation; `requests-async==0.5.0` ไม่ถูกแทนด้วยเวอร์ชันอื่นเงียบ ๆ. ไม่มีการใช้ผล LLM ใน amendment เหล่านี้.

Preflight ใช้ image Python 3.8.20 และ dependency ที่ตรึงไว้ ไม่ใช่การจำลอง historical environment ที่ตรงทุกแพ็กเกจ. Raw Podman evidence อยู่ใต้ `D:\ConveyorFlowRuntime\v2_6`; ไฟล์ Git มี script, config, queue, lock, ledger และ `source_preflight_capsules_v1.json` ที่บันทึก hash/ผลโดยไม่เก็บ credential. Capsule ไม่แทน raw evidence สำหรับ independent audit. PySnooper v1 มีปัญหาการแสดง `/mnt/d` path ข้าม Windows/WSL ก่อนเริ่ม container จึงเก็บ lock เดิมและเปิด v1b ใหม่; `preflight_pysnooper_v1.py --audit` สำหรับ v1b ต้องรันใน WSL เพราะ raw path เป็น Linux path.

## 3. ผลต่อแผนวิจัย

- 17 project ใน manifest ไม่เท่ากับ 17 project ที่ใช้ main ได้. ขณะนี้ตรวจจริง 2 project: PySnooper ไม่ผ่าน; Sanic ผ่านเฉพาะ public-test contrast. ยังมี 15 project ที่ยังไม่ผ่าน preflight v2.6 และต้องคัดตามลำดับเดิม.
- เป้าหมาย 12 distinct qualified projects ยัง **ไม่รับประกัน**. หากไม่ถึง ให้หยุดที่ eligibility outcome และจำกัดข้ออ้างเป็น bounded multi-source feasibility ตาม protocol; ห้ามเพิ่มเคสเพราะทิศทางผล CF-Fit ไม่ถูกใจ.
- ก่อนยิง MFEC main ต้องทำ gold-free repair candidate/public regression, ML corpora เพิ่มและ full-DAG smoke, ability/difficulty/analysis lock, model-version/cost gate, matched decision-locus test และ freeze paired cohort. จากนั้นจึงรัน CF-Fit เทียบ Central-Rule-Matched กับ Static-Owners บน READY belt เดียวกัน และรายงาน throughput/time/utilization/cost เป็น trade-off.

การตรวจซ้ำแบบไม่เรียก LLM: `python major_revision_v2_6/build_prior_exposure_ledger_v1.py --write`, `python major_revision_v2_6/build_unexposed_candidate_queue_v1.py --write`, `python major_revision_v2_6/preflight_sanic_v1c.py --audit`; ส่วน PySnooper audit ให้เรียก script เดียวกันใน WSL/Podman environment. ทุก script ปฏิเสธการเขียนทับ lock/ledger ที่เปลี่ยนไป.

## 4. ต่อเนื่อง 12 ตุลาคม 2026: Sanic case 3 candidate gate

ยังไม่มีการเรียก LLM (`provider_calls = 0`). `sanic_3` เป็นเคสที่สองซึ่งผ่าน buggy-fail/fixed-pass ใน v1c. ตรึง `build_sanic3_candidate_v1.py` ก่อนรัน: candidate image เก็บเฉพาะ buggy `sanic` package และอนุญาต patch `sanic/app.py`; verifier image ถือ public buggy tests โดยไม่มี fixed source. รอบ v1 ไม่ผ่านเพราะ `tests/test_url_for.py` มีเพียง visible test เดียว จึงไม่มี non-visible regression node ตามเกณฑ์ 3 รายการ (`too_few_public_regressions`, selected 0). ไม่ลบผลนี้.

Amendment `build_sanic3_regression_v1b.py` ตรึงก่อนดู outcome โดยขยาย *inventory* ไปที่ public files ที่เกี่ยวกับ route/URL (`test_named_routes.py`, `test_routes.py`, `test_url_building.py`) และ hash-sort เลือก 5 node แรก ไม่เปลี่ยน source image, allowed patch, visible verifier หรือ LLM. ผลคือ visible buggy fail 1/1; 5/5 selected public regressions ผ่านทั้ง buggy และ fixed; candidate image audit ไม่พบ protected/fixed/test history. `audit_sanic3_regression_v1b.py` ตรวจ raw hashes, เลือก node ซ้ำจาก collection, JUnit และผล image audit แบบแยกจาก runner แล้วผ่าน (`summary_sha256 = b65b4d878c63f6d061f079b50c13e2d446a256f7824c5c25cf60c8424b56c90c`). Raw อยู่ `D:\ConveyorFlowRuntime\v2_6\sanic3_candidate_v1` และ `D:\ConveyorFlowRuntime\v2_6\sanic3_regression_v1b`.

**สถานะ:** `sanic_3` ผ่าน candidate/public-regression gate แบบ public tests (ไม่ใช่ novel hidden tests) และยังไม่ใช่ main-ready project เพราะเกณฑ์ 2 qualified cases/project ยังต้องตรวจ `sanic_5` ใน v2.6 environment/แผน regression ที่ตรึงเอง. Source frame โดยรวมยังไม่ freeze; ไม่มีผล RQ1/RQ2 ใหม่.

## 5. ต่อเนื่อง 12 ตุลาคม 2026: Sanic project ยังไม่เข้า main

`build_sanic5_candidate_v1.py` ตรึงกฎก่อนรันและเปิดเผยว่า v2.5 เคย timeout แบบ batch; รอบ v2.6 ใช้ source image ใหม่, candidate gold-free, patch scope `sanic/log.py`, hash-sort public logging nodes 3 ตัว และรันแยก node ภายใต้เพดาน 120 วินาที พร้อม stop-on-first-failed-pair. Independent audit ผ่านโดยยืนยัน **ผลไม่ผ่าน** (`summary_sha256 = 0ba601511777944fa8fb451310f904a9c4567becf0212be5cdbb6192549a0ece`): visible buggy fail 1/1, node แรกผ่านทั้ง buggy/fixed, node ที่สอง timeout ทั้ง buggy/fixed, node ที่สามจึงไม่ถูกรันตาม stop rule. ไม่เลือก node ทดแทนหลังเห็น timeout และไม่มี LLM call.

`preflight_sanic_recovery_v1d.py` ตรึงคิวเดิมที่เหลือ `sanic_2 → sanic_1 → sanic_4` หลัง case 5 ถูกตัดที่ candidate gate. ตรวจครบทุกเคสแล้ว: case 2 ผ่านทั้ง buggy/fixed จึงไม่มี bug contrast; cases 1 และ 4 เกิด test error ทั้ง buggy/fixed. Ledger SHA-256 `37286173bcd999f9ed626971047ed1a73765910dbae11f5e12d66380029a591f`, raw อยู่ `D:\ConveyorFlowRuntime\v2_6\sanic_preflight_v1d`, `provider_calls=0`.

**ผล source selection:** Sanic มีเพียง `sanic_3` ที่ผ่าน candidate gate จากคิวที่เหลือทั้งหมด จึง **ไม่ผ่านเกณฑ์ 2 cases/project** สำหรับ v2.6 main และไม่ควรยิง MFEC กับ Sanic ใน cohort หลัก. PySnooper และ Sanic เป็นสอง project แรกที่ตรวจครบแล้วและยังไม่เข้า main; project ถัดไปตาม frozen order คือ Cookiecutter. จำนวน qualified projects จาก 17 ยังเป็นศูนย์ ไม่ใช่สอง.

## 6. ต่อเนื่อง 12 ตุลาคม 2026: Cookiecutter public contrast และ storage stop

Cookiecutter มีคิว frozen `cookiecutter_3 → cookiecutter_1 → cookiecutter_4 → cookiecutter_2`. `preflight_cookiecutter_v1.py` ตรึง Python 3.6.15 image และแปลงคำสั่ง `tox <node>` แบบหนึ่งบรรทัดเป็น direct pytest node โดยเปิดเผยว่าไม่ใช่ historical Python 3.6.9/tox environment ที่ตรงทุกอย่าง. การ build `cookiecutter_3` รอบ v1 ล้มก่อนทดสอบ เพราะ Debian Buster mirror เดิมตอบ 404. เก็บ Dockerfile/build report/ledger ไว้; ไม่มี LLM call.

Amendment v1b เปลี่ยนเฉพาะ apt mirror เป็น Debian archive ก่อนรัน แต่ pytest หยุดเพราะ `setup.cfg` ระบุ `--cov=cookiecutter` โดยไม่มี pytest-cov. Amendment v1c ปิดเฉพาะ coverage addopts; ทั้ง buggy/fixed ยังเกิด test setup error เพราะขาด `mocker` fixture. จากนั้นตรวจ public `tox.ini` และ `test_requirements.txt` ซึ่งระบุ pytest-cov, pytest-mock, pytest-catchlog และ freezegun. Amendment v1d ตรึงเวอร์ชันของ test dependencies เหล่านี้ก่อนรันใหม่ และเก็บ v1–v1c เป็น excluded environment attempts แยกกัน ไม่ตีความเป็นผลบั๊ก.

ผล v1d ของ `cookiecutter_3`: public node `tests/test_read_user_choice.py::test_click_invocation` มี 4 parameterized tests; buggy fail 4/4, fixed pass 4/4, ไม่มี test error/skipped (`preflight_record_sha256 = a65895b1d55ea124c7747a85de2f687c617395929614ddf7044a8f4a91852efe`). `preflight_cookiecutter_v1d.py --audit` ยืนยัน ledger/record และรายงาน `provider_calls=0`. นี่เป็นเพียง **public buggy/fixed contrast**; ยังต้องทำ gold-free candidate, non-visible public regressions, independent audit และหาเคสที่สองก่อนเรียก project นี้ว่า eligible. Image/record ระบุ Python patch-level และ harness deviations ไว้แล้ว.

ก่อนเริ่ม `cookiecutter_1` ตรวจ C: เหลือ **14.68 GB** และ D: เหลือ **205.08 GB**. C: ต่ำกว่าเกณฑ์ 20 GB ใน protocol จึง **หยุด container preflight และ paid calls**. ลบเฉพาะ 9 image cache ที่ตรวจ tag/ID แล้วของ Sanic v2.6 ซึ่ง project ถูกตัดออกจาก main และไม่มี container ใช้งาน; สร้างใหม่ได้จาก script/lock และ raw evidence บน D: ไม่ถูกลบ. หลังลบและ `fstrim` C: ยังเหลือ **14.65 GB** เพราะ `ext4.vhdx` ของ Ubuntu WSL ไม่หดขณะใช้งาน. ไม่ prune images ของงานอื่นและยังไม่เปลี่ยนเกณฑ์หลังเห็นผล. ต้องจัด storage แบบตรวจ exact target และตรวจ gate ใหม่ก่อนรันต่อ. ปัจจุบันยังมี **0 project ที่ผ่านครบ 2 candidate cases** สำหรับ v2.6 main.
