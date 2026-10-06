# ผล repository repair pilot และ decoder diagnostic

อัปเดต 5 ตุลาคม 2026. รอบ MFEC v1 จบครบ 18 jobs แล้ว แต่ไม่มี original-protocol success. การวิเคราะห์เครื่องมืออ่าน patch ภายหลังพบหนึ่ง unique job ที่ซ่อมบั๊กได้เมื่อแปลง metadata อย่างเคร่งครัด ผลสองส่วนนี้ห้ามรวมเป็น success rate ใหม่หรือใช้ fit probability

## เหตุผลที่ทำ

Microtasks และ Bugs2Fix repair surrogates เดิมไม่ได้แก้ source repository จริง. จึงใช้ BugsInPy ซึ่งมี buggy/fixed commits และ executable public tests. เลือกตาม frozen hash-order prefix โดยไม่ดูผลของโมเดล ได้ pandas #88/#76/#128/#27, matplotlib #15 และ luigi #19 รวม 6 bugs จาก 3 repositories. thefuck #32 ถูกเก็บเป็น environment exclusion ไม่ใช่โมเดลล้มเหลว

Gold-containing images ใช้เฉพาะ trusted preflight. Final candidate image ไม่มี fixed code, gold patch, tests หรือ .git/history. Verifier แยกมี buggy source และ protected public tests. No-op smoke ผ่านก่อนเรียกโมเดลทั้งหกกรณี. Regression เลือก 10 items ต่อ case ก่อนรู้ผล; มี 58 active passes กับ 2 historical expected failures ซึ่งไม่ถูกนับเป็น passes. Public withheld tests ยังอาจอยู่ใน pretraining และไม่ใช่ novel independent hidden tests

## MFEC v1

| Model alias | Jobs | Calls | Original verified jobs | สาเหตุที่ไม่ถึง test gate |
|---|---:|---:|---:|---|
| tencent-hy3 | 6 | 12 | 0 | ทุก response เป็น length ที่ cap 16,384 และ content ว่าง |
| gpt-5-mini | 6 | 12 | 0 | ส่ง alternate patch markers หรือ line counts ไม่ตรง strict diff contract |
| glm-5.3-flash | 6 | 12 | 0 | ทุก response เป็น length ที่ cap 16,384 และ content ว่าง |

รวม 627,649 input tokens, 397,841 output tokens, cost 0.369205896 provider-reported units. ทั้ง 36 calls มี request ID, mapping identity, response/token/cost metadata; ยังไม่ยืนยันสกุลเงิน. Token counts อาจครอบคลุม output ที่ไม่ปรากฏใน content จึงไม่ตีความว่าเป็น code tokens ทั้งหมด และไม่สรุปสาเหตุภายในของ provider จาก log นี้

Strict guard ปฏิเสธรูปแบบก่อนนำ source ไป execute. ผลนี้วัดความสำเร็จภายใต้ output contract รุ่นนั้น ไม่ได้แยกความสามารถการซ่อมบั๊กออกจากปัญหา output protocol. ผลลบและต้นฉบับคำตอบทุก attempt ถูกเก็บไว้

## Offline decoder diagnostic

ตรึง decoder/config/runner และ hashes ของคำตอบเดิมก่อน test replay. Decoder เปลี่ยนเฉพาะ header, hunk counts และ offsets; additions/deletions/context ของโมเดลไม่ถูกแก้ และต้องตรงกับ buggy source ทุก byte ที่ตำแหน่งเดียว. ไม่อ่าน fixed source/gold/test outcomes เพื่อเลือกการแก้. ใช้ guard เดิม, images เดิม และ gates เดิม. Output ว่าง/non-stop ถูกระบุว่า unrecoverable

รอบแรกหยุดก่อน test เพราะ lock ที่สร้างบน Windows มี backslash keys ไม่ตรง WSL. เก็บ lock เดิมและบันทึก wrapper/manifest Linux แยก ไม่เปลี่ยนอัลกอริทึมหรือ test แล้วค่อย execute

ผลครบ 36 original attempts: 24 unrecoverable, 10 decoded attempts fail visible tests, 2 decoded attempts ผ่าน visible/regression/clean replay. สอง attempts ที่ผ่านเป็น GPT-5 mini ของ **pandas #76 เคสเดียว** และใช้ source edits เดิม จึงมี **หนึ่ง unique recovered job** ไม่ใช่สองผลสำเร็จอิสระ. ไม่เรียก API ใหม่ ไม่เปลี่ยนค่า 0/18 ของ original v1

## สิ่งที่ยังต้องทำ

ก่อน main เพิ่ม exact-edits sentinel แยก 3 calls บน **pandas #88 ที่เคยใช้แล้ว**. Truncate cap เพิ่มเท่ากันทุก alias เป็น 32,768; โมเดลส่ง JSON exact replacements แล้ว deterministic converter สร้าง strict diff. มีหนึ่ง GLM repair ผ่าน visible, 8 active regression passes + 2 unchanged historical xfails และ fresh replay. GPT รูปแบบใช้ได้แต่ visible bug test fail; Tencent finish_reason length/content ว่าง. ไม่ให้ investigators แก้ source, ไม่ใช้ gold และไม่มี automatic retry. รวม 25,793 input / 37,601 output tokens, 0.029603642 provider-reported units (currency unconfirmed). **ห้ามรวม 1/3 sentinel เข้ากับ 0/18 v1 หรือ decoder เพื่ออ้าง success probability**

กำลังเตรียม new-case calibration preflight ที่แยกจาก exposed prefix: 2 eligible cases ต่อ Luigi/Matplotlib/Pandas โดยเรียง hash ภายใน repository; budget ไม่เกิน 4 preflights ต่อ repo. ทุก exclusion และ quota skip อยู่ใน ledger. นี่เป็นการตรึงและตรวจ environment ก่อน calibration ไม่ใช่ผล model repair แล้ว. ตรึง population scope เป็น Python 3.8 และ single-pytest cases ในสาม repos ที่มี profile รองรับ; ไม่อ้างว่าเป็นตัวแทน BugsInPy ทั้งหมด

ก่อน main ต้องตรึง output contract ที่โมเดลส่งได้จริง, ทดสอบบน held-out pilot cases และเก็บ metadata ให้แยก unfinished output/format/apply/test failures. ต้องมี isolated stage calibration เพื่อไม่ให้ predecessor failure ทำให้ stage-level probability มี selection bias และต้องรัน paired allocation arms ด้วย input/validator/budget เดียวกัน. ผลที่มีตอนนี้ยืนยันหนึ่ง localized repair กับหนึ่ง ML DAG feasibility case; ยังไม่ปิด gap ของ policy comparison หรือ probability provenance

ตรวจซ้ำแบบ read-only จาก workspace root:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryPilotAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryDecoderAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryContractAudit
& 'v2/REPRODUCE_V2_3.ps1' -Stage BugsCalibrationPreflightStatus
```

หลักฐาน: `results/repository_repair_pilot_v1_audit_20261005.json`, `results/repository_decoder_replay_v2_audit_20261005.json`, `candidate_workspaces/repository_repair_pilot_v1/`, `candidate_workspaces/repository_decoder_replay_v2/`. ไม่ใส่ API key ใน repository หรือเอกสารเผยแพร่
