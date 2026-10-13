# v2.3 Supplemental repository-repair feasibility: execution protocol V2

สถานะ ณ 9 ตุลาคม 2026: เขียน **ก่อนเรียก LLM สำหรับ holdout ทั้งหกเคส** เป็น protocol amendment ต่อ `REPOSITORY_REPAIR_FOLLOWUP_PLAN_V1_TH.md`; ไม่ใช่การแก้ผล main six-block ย้อนหลัง และไม่ใช่ allocation-policy comparison

## เหตุผลและ estimand

main six-block ใช้ strict unified-diff contract และ CF-Fit/Central-Fit ซ่อม repository ไม่ผ่านเลย จึงทดสอบเฉพาะความเป็นไปได้ของการสร้าง patch ภายใต้ artifact interface ที่ผ่านการตรวจบน calibration แล้ว: อัตรา `VERIFIED / attempted model–case pairs` ของสาม MFEC deployment บนหก BugsInPy holdout ที่เลือกก่อนเห็นผล holdout model; รายงานแยกตาม repository และ model. ผลนี้ตอบได้ว่า patch interface ใหม่ช่วยให้เกิดการซ่อมจริงบ้างหรือไม่ แต่ไม่ตอบว่า CF-Fit จ่ายงานซ่อมได้ดีกว่า baseline.

## เคสและ preflight

ลำดับเคสคงที่จาก design เดิม: `luigi_11`, `matplotlib_6`, `pandas_127`, `luigi_16`, `matplotlib_26`, `pandas_74`. สอง Matplotlib เคสมี buggy-fail/fixed-pass ภายใต้ warning-filter amendment ที่ audit ไว้ก่อนแล้ว. สี่ Luigi/Pandas เคสเคยถูกข้ามเพราะ original main เต็ม quota จึงทำ container-only environment preflight ใหม่ด้วย config เดิมและต้องได้ buggy-fail/fixed-pass ก่อนเรียก LLM. หากเคสใดไม่ผ่าน ให้นับเป็น `environment_excluded` ใน case flow และไม่เรียก model สำหรับเคสนั้น; ห้ามเลือกเคสแทนหลังเห็นผล.

preflight wrapper V1 หยุดก่อน image build เพราะ metadata-only manifest ขาด field `status`; เก็บ tree และ lock ไว้ ไม่เรียก provider. V2 ใช้ output root แยกและ manifest schema ที่ engine ต้องการ; ห้ามลบหรือแก้ V1. Preflight recovery ล่าสุดต้อง audit ครบก่อน freeze paid instrument.

บันทึก platform recovery ก่อน model call: การเรียก V2 เคส `luigi_11` ด้วย WSL user แบบ rootless หยุดที่ Podman build (`sd-bus Permission denied`, return code 125) เพราะไม่ใช่ image store/rootful runtime ที่ main เดิมใช้; ไม่ใช่ผลของ model และไม่ตีความว่าเคสซ่อมไม่ได้. เก็บ V2 build report/summary ไว้. `preflight_repository_followup_rootful_v3.py` ล็อกหลักฐาน V1/V2 และทำ environment preflight สี่เคสใน output root ใหม่ผ่าน rootful Podman เดิม ซึ่งผ่าน disposable networkless verifier smoke test. ห้ามเปลี่ยนผล V1/V2 หรือเลือกเคสจากผล model.

## Interface และการป้องกัน leakage

ใช้ exact-edits adapter `repository_exact_edits_v3.py` ที่ทดสอบบน calibration เดิม: JSON object `{"edits":[{"path":"...","before":"...","after":"..."}]}` (1–8 edits). `before` ต้องเป็น substring ที่ตรงเพียงแห่งเดียวใน buggy source เดิม; path ต้องอยู่ใน allowed production files; ห้าม overlap, no-op, test/config/report edit และ adapter ต้องสร้าง canonical unified diff อย่าง deterministic โดยไม่แก้ semantic เอง. ชื่อ `before/after` คือ implementation ของ `search/replace` ในแผน V1; ความหมายเหมือนกันแต่ตรึง schema จริงนี้ก่อน holdout. Prompt มีเฉพาะ buggy source excerpt, visible public test/trace และ allowed paths; ห้ามส่ง fixed source/reference patch หรือ withheld regression ให้ model. Patch และ tests รันเฉพาะใน Podman container ที่ปิด network; ไม่รัน candidate บน Windows.

## การตรึงและการรัน

ก่อน request แรก ต้อง hash code, config, model aliases/exact versions, prompt ของทุกเคส, context, candidate/verifier image IDs, regression node list, token cap, timeout, case order, output root และ verifier. ใช้ `temperature=0`, `max_output_tokens=32768`, provider timeout 720 s, one call ต่อ model–case, SDK retries ปิด. ทุก model ใช้ instrument เดียวกัน สูงสุด 18 calls. บันทึก request-start marker ก่อนส่ง; หลัง timeout/error ไม่ retry pair นั้น และเก็บ unknown billing status.

หลังสร้าง patch ให้ผ่าน visible bug test, selected public regression ที่ไม่อยู่ใน prompt, แล้ว fresh replay ของทั้งสองชุดใน container ใหม่. `VERIFIED` ต้องผ่านทั้งสี่ gate. Format/provider/visible/regression/replay failures และ unresolved ที่เริ่มเรียกแล้วคงอยู่ใน operational denominator; case exclusions ก่อน request แยกต่างหาก. เก็บ append-only ledger, provider metadata/token/cost units (ไม่ตีความเป็น USD), source/response/patch/report hashes และ audit capsule. รายงาน Wilson interval แบบ descriptive เท่านั้น; หกเคสในสาม repository ไม่ใช่หกตัวอย่างอิสระสำหรับ population claim.

## ขอบเขตคำกล่าว

ห้าม pool กับ main strict-diff หรือ calibration; หากมี verified repair ก็อ้างเพียง feasibility ของ interface ใหม่บน holdout นี้ ไม่อ้าง CF-Fit repository-repair success หรือ decision-locus advantage. หากต้องการข้ออ้างเช่นนั้น ต้อง freeze **paired allocation experiment ใหม่** ที่ใช้ contract ใหม่เหมือนกันทุก arm และใช้เคสใหม่ ไม่ย้อนใช้ holdout นี้หลังเห็นผล.
