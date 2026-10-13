# ผล repository repair ชุดใหม่: first-attempt feasibility

อัปเดต 6 ตุลาคม 2026. ชุดนี้จบแล้ว แต่ไม่ใช่ main allocation experiment และไม่ได้ปิด Major Revision ทั้งหมด.

## ทำไมจึงทำ และทำไมเลือกแบบนี้

Microtasks และ repair surrogates ไม่พิสูจน์ว่า patch ใช้กับ repository จริงได้. ชุดนี้จึงให้ MFEC models สร้าง exact edits สำหรับ BugsInPy checkout จริง แล้วใช้ isolated verifier ตรวจ visible failing test, regression tests และ fresh replay ของ patch เดิม. ไม่รัน candidate บน Windows และไม่แก้ patch ให้โมเดล.

ก่อนเรียกโมเดล เลือกสองเคสต่อ repository จาก frozen hash order และตรวจ environment แบบ buggy-fail/fixed-pass. ได้ Luigi #31/#17, Matplotlib #18/#9 และ Pandas #166/#147: หกเคส/สาม repositories. เคสเหล่านี้ไม่ซ้ำ exposed prefix ของการทดลอง repository ก่อนหน้า แต่ไม่ได้อ้างว่าไม่เคยอยู่ใน training data ของ vendor. การเลือกเฉพาะ environments ที่ทำซ้ำได้และการให้ investigator localization ทำให้ผลเป็น **conditional localized-repair feasibility** ไม่ใช่ full-repository autonomous repair.

ทุกโมเดลได้โจทย์ งบ token และ test contract เดียวกัน: one provider call ต่อ model–case pair, output cap32,768, temperature0, provider limit720s. ผลไม่ผ่านหรือ output ว่างยังอยู่ใน planned denominator. แบบ first-attempt ช่วยป้องกันการลองซ้ำจนได้ผลดี และแยก revision ของ output contract ออกจาก pilot เก่า.

## ผลที่ตรวจสอบแล้ว

| Model alias | จบ/วางแผน | VERIFIED | ผลอื่น | Wilson95% แบบ descriptive |
|---|---:|---:|---|---|
| tencent-hy3 | 6/6 | 4/6 (66.7%) | visible-test failure2 | 30.0–90.3% |
| gpt-5-mini | 6/6 | 1/6 (16.7%) | visible-test failure4; exact-edits contract failure1 | 3.0–56.4% |
| glm-5.3-flash | 6/6 | 2/6 (33.3%) | provider-unresolved1; unfinished/empty3 | 9.7–70.0% |

VERIFIED หมายถึง unchanged model patch ผ่านทั้ง initial gates และ fresh replay. Replay ไม่ใช่ extra successful observation. Final baseline bundle มี53 selected regression identities: สี่เคสใช้สิบรายการ, Luigi #17ใช้หก, Matplotlib #9ใช้เจ็ด. Cardinality amendments เกิดก่อน model calls/outcomes ไม่ใช่ลบ tests หลังเห็นผล.

GLM provider-unresolved ยังไม่ทราบผลที่ provider อาจทำเสร็จ และไม่ทราบ billable outcome. อัตรา verified ภายใน observation window คือ2/6; หากกล่าวถึง outcome ที่อาจไม่ถูกสังเกต ช่วงขอบเขตเชิงตรรกะคือ2/6ถึง3/6 ไม่ใช่ confidence interval. ห้ามเรียก unresolved ว่า model patch ถูกตรวจแล้วและล้มเหลว.

## Token และต้นทุน

มี returned responses17รายการ: input223,970tokens, output223,724tokens และ provider-reported costรวม0.199841350units. ยังไม่ยืนยันสกุลเงิน และยังมีหนึ่ง call ที่ billable outcome ไม่ทราบ จึงไม่ใช่ total billed cost และไม่ควรใส่เครื่องหมาย USD. Provider alias/version mapping ที่บันทึกไว้ไม่ได้รับรองว่า vendor snapshot จะคงเดิมตลอดไป.

## ข้อสรุปที่ใช้ใน paper ได้

ชุดนี้แสดงว่า output contract และ isolated verification รองรับ **บาง localized repairs บน repository จริง** ได้ โดยคงผลลบครบ. จึงลดช่องว่างที่หลักฐานเดิมเป็น repair surrogate เท่านั้น.

แต่หกเคสมีเพียงสาม repository clusters และเคสใน repository เดียวกันสัมพันธ์กัน. Wilson intervals ในตารางเป็น descriptive binomial reference ไม่ใช่ independence-adjusted population intervals. ไม่ใช้ผลนี้จัด Ability Rank สากล ไม่ประมาณ D1–D3 coefficients ไม่ fit Equation7 และไม่ตีความว่า Tencent/CF-Fit ชนะทั่วไป.

ที่สำคัญ ชุดนี้ไม่ได้เปรียบเทียบการจัดสรร CF-Fit กับ Central-Matched/Static. Contribution ของ paper ยังคง decentralized self-selection + capability heterogeneity + fit/stand-down; repository repair เป็นเครื่องมือทดสอบ execution/verification. การยืนยัน trade-offs ของกลไกบน real-LLM ต้องมี paired allocation streams ที่ควบคุม workload/team/budget/validator เท่ากันแยกต่างหาก.

## หลักฐานและการทำซ้ำ

- Frozen model protocol: `repository_first_attempt_v1_lock.json`, SHA256 `0ee455b30ea4db37878d0b7e235c2e128a265dcd406db56d70e7e0ae3bc9d144`.
- Final audit: `results/repository_first_attempt_v1_audit_20261005.json`; สร้างจริง6ต.ค.02:40:12UTC. SHA256 `06cdd1608af38a7f36470f3af8eac8394ff3bcd9bfda9f5beb17fced9fbf5eba`.
- Append-only ledgers และ per-pair artifacts: `candidate_workspaces/repository_first_attempt_v1/`.
- ตรวจซ้ำแบบ read-only จาก workspace root: `& 'v2/REPRODUCE_V2_3.ps1' -Stage RepositoryFirstAttemptAudit`.
- การ execute คู่ที่มีผลแล้วต้องถูกปฏิเสธ. ไม่ใช้คำสั่ง restart เพื่อแทนที่ failed outputs และไม่ pool ผลกับ original pilot, offline decoder หรือ reused sentinel.
