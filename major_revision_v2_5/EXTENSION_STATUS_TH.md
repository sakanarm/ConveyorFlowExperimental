# v2.5: สถานะการปิด gap เรื่อง generalization, cost และ fault tolerance

สถานะ ณ 11 ตุลาคม 2026: **ยังไม่ปิด Major Revision gap** เอกสารนี้บันทึกผลที่ทำเพิ่มจริงและขอบเขตของผล โดยไม่เอาจำนวน API calls มานับเป็นตัวอย่างอิสระ และไม่แก้ผล v2.4 ย้อนหลัง

## 1. จำนวนแหล่งงานอิสระและความแม่นยำ

รอบ v2.4 มี 11 paired blocks ที่ audit ครบ แต่ยังใช้เพียง 4 source repositories และ 2 ML corpora ซ้ำกัน จำนวน 159 provider attempts เป็นหน่วยบัญชีการเรียก ไม่ใช่ 159 independent experimental units. สคริปต์ [`precision_scenarios_v1.py`](precision_scenarios_v1.py) อ่านผลที่ audit แล้วและคำนวณความกว้างครึ่งหนึ่งของช่วงประมาณค่าแบบ Student-t ในกรณีสมมติ *ระหว่าง repository*. ค่า SD จาก 4 repositories เดิมเท่ากับ 0.167 verified jobs/hour แต่ไม่ควรใช้ค่านี้ลำพังเพื่อรับรอง N เพราะประมาณจาก cluster น้อยมาก. หาก SD จริงเป็น 0.5, การมี 20 repositories ให้ half-width ประมาณ 0.234 jobs/hour; หาก SD เป็น 1.0, ต้องถึง 64 repositories จึงได้ประมาณ 0.250. เป้าหมาย ±0.25 นี้เป็น **scenario สำหรับหารือ ไม่ใช่เกณฑ์ที่ที่ปรึกษารับรองหรือ power calculation ที่เสร็จแล้ว**. ML corpus clustering ยังต้องออกแบบแยก ไม่ใช่นับรวมกับ repository โดยตรง. ดูผลที่ [`precision_scenarios_v1.json`](results/precision_scenarios_v1.json).

เริ่มคัด repo ใหม่แบบ outcome-blind และ container-only แล้ว:

| แหล่งใหม่ | buggy/fixed preflight | gold-free candidate + public regression | สถานะสำหรับ paid extension |
|---|---|---|---|
| Sanic bug 5 | buggy fail 1/1, fixed pass 1/1 | public regressions ฝั่ง buggy และ fixed timeout ภายใต้ `--network none` | **ตัดออก** ตาม frozen gate; ไม่ใช้เป็นผล LLM |
| PySnooper bug 3 | buggy fail 1/1, fixed pass 1/1 | candidate ไม่มี fixed source/test; visible bug ยัง fail, public non-visible tests 4/4 ผ่านทั้ง buggy และ fixed; audit อิสระผ่าน | **พร้อมเป็น candidate** สำหรับรอบที่ freeze cohort และ analysis ใหม่; ยังไม่มี paid LLM result |
| Black (queue 8 cases) | case 21 buggy/fixed ผ่านทั้งคู่จึงไม่ใช่ contrast; case 3 import ไม่ผ่านทั้งคู่ (`typing_extensions` ใน v1, `_black_version` ใน v1b หลังเติม dependency และ replay queue) | ยังไม่ถึง candidate gate | **ยังไม่ผ่าน**; คง exclusions ทั้งสอง ledger; ต้องมี package-build profile ที่ผ่านทั้ง buggy/fixed ก่อนคัดต่อ |

PySnooper มีบันทึก instrument amendments ทุกฉบับ: v1 tag ตัวพิมพ์ใหญ่ผิดรูปแบบ OCI, v1b/v1c พบ dependencies ที่ repository ประกาศแต่ minimal image ยังไม่ติดตั้ง, v1d ผ่าน preflight, candidate v1 verifier เจอ Podman cache error, v1b build แบบ no-cache สำเร็จ, และ public-regression v1c แก้เกณฑ์ขั้นต่ำ 5 test ที่เป็นไปไม่ได้เพราะไฟล์นี้มี non-visible test เพียง 4. ทุก amendment เกิด **ก่อน LLM call**, เก็บผลเดิมไว้, replay queue/selection เดิม และ public-regression v1c ใช้ครบทั้ง 4 โดยไม่คัดตามผล. Audit script คือ [`audit_new_repo_gates_v1.py`](audit_new_repo_gates_v1.py); รายงานคือ [`new_repo_gates_audit_v1.json`](results/new_repo_gates_audit_v1.json). Image เป็น local artifacts; Git เก็บ code, locks, bounded audit และวิธีสร้างซ้ำ ไม่เก็บ source images/log ขนาดใหญ่.

**ขั้นถัดไป:** qualify อย่างน้อย 3 repositories เพิ่มจาก 4 เดิมและ PySnooper เพื่อให้ถึง design floor 8 repositories พร้อม public ML corpora ใหม่อย่างน้อย 2 ชุดขนาด ≥20,000 rows (ผู้สมัคร: UCI Bank Marketing 45,211 rows และ Covertype 581,012 rows). ต้อง freeze source hash, split, DAG, leakage rule, container verifier, failure/exclusion log และ balanced paired arms ก่อน paid calls. Floor 8/4 เป็นความหลากหลายขั้นต่ำเชิงออกแบบ **ไม่ใช่หลักฐานว่า precision พอ**; หาก scenario/CI บอกว่าไม่พอ ต้องจำกัด claim ไม่เพิ่ม N จนผลถูกใจ.

## 2. Cost efficiency

ผล v2.4 มี cost ไม่ทราบ 5 attempts: CF-Fit 1, Central-Rule-Matched 1, Static-Owners 3. ค่า `known_provider_cost_units` เป็นเพียง subtotal; cost/verified job ทั้ง arm จึงยังเป็น `null`. ไม่เติมศูนย์ ไม่แทนด้วยค่าเฉลี่ย และไม่ตีความ subtotal เป็น cost advantage. การตรวจ read-only MFEC LiteLLM spend endpoints ได้ HTTP 403 จึงต้องมี **read-only billing/spend export จาก MFEC** สำหรับช่วงเวลาทดลองเดิม หรือรอบใหม่ที่มีการยืนยันว่า account-level usage/charge ถูกส่งกลับครบทุก attempt. ถ้าไม่ครบ ให้รายงาน token/attempt efficiency เป็น outcome แยก และไม่ claim monetary cost efficiency จาก real-LLM tier. Simulation cost เป็น calibrated assumption ไม่ใช่ใบแจ้งหนี้ MFEC.

## 3. Fault tolerance

ไม่จำเป็นต้องรัน fault test เดิมซ้ำเพื่อสร้างตัวเลขเพิ่ม: [`DECISION_FAULT_RESULT_TH.md`](../major_revision_v2_4/DECISION_FAULT_RESULT_TH.md) มี 160 audited no-LLM trials = 20 paired seeds × 4 scenarios × 2 architectures. ใน coordinator-only outage, CF-Fit ยัง verified 3/3 เทียบ Central-Rule-Matched 0/3; เมื่อ shared belt/claim store ล้ม ทั้งคู่ 0/3. จึงเขียนได้เพียงว่า **ไม่มี central allocation-decision process เป็นจุดพึ่งพาใน fault window ที่ทดสอบ** ไม่ใช่ระบบทั้งหมดไม่มี single point of failure หรือพิสูจน์ production reliability. Seeds 20 ค่าเป็น repeated jitter บน workload เดียว ไม่ใช่ 20 งานอิสระ.

## 4. Gate ก่อน real-LLM extension

1. Qualified cohort ต้องมี repo/dataset diversity ตาม protocol และไม่มี case ที่เลือกจากผล LLM; ทุก exclusion ต้องคงใน ledger.
2. ตกลง estimand และ precision target/SESOI กับผู้วิจัยและที่ปรึกษา แล้ว freeze sample-size/analysis plan ตาม hierarchy `source → case → paired arm → repeat`. คง RQ1 แบบ trade-off vector ไม่บังคับ CF-Fit ชนะทุก metric; RQ2 heterogeneity และ stand-down ablation แยกชัด.
3. ใช้ belt, team ≤4 models, ability profile, prompts, model versions, horizon, executor/verifier และ accounting เดียวกันใน matched arms; ความต่าง CF-Fit vs Central-Rule-Matched อยู่ที่ตำแหน่งผู้ตัดสินใจเลือกงาน. Static-Owners เป็น control ที่กำหนดเจ้าของล่วงหน้า.
4. ต้องมี provider billing export หรือประกาศ cost missingness เป็นข้อจำกัดก่อนเริ่ม, พร้อม stopping rule ที่ไม่เพิ่ม calls ตามทิศทางผล.

จากนั้นจึงยิง real LLM เพิ่มและปรับ manuscript IEEE/AJSTR ตามผลที่ audit จริง. **ยังไม่ควรเปลี่ยนข้อความใน paper เป็น “ปิด Major Revision gap แล้ว”** จาก feasibility รอบนี้.

## 5. Real-LLM exploratory feasibility (11 ตุลาคม 2026)

หลังจากพบว่า MFEC gateway ตอบจริง (`mfec_gateway_probe_v1.json`; ไม่นับเป็นข้อมูลวิจัย) ได้ freeze prompt จาก buggy source และ visible test ของ PySnooper bug 3 ซึ่งผ่าน pre-provider gate แล้ว ก่อนเรียก LLM จริง 3 deployment ด้วยกติกา exact-edits เดียวกัน โมเดลเห็นเพียง buggy source และ visible public test; fixed source อยู่ใน validator เท่านั้น ไม่อยู่ใน prompt หรือ candidate image. งานแต่ละ model–case pair เรียกหนึ่งครั้ง ไม่มี retry และ patch ทดสอบใน Podman แบบ `--network none` กับ visible test, public regressions 4 ตัว และ clean replay ทั้งสองชุด

Audit อิสระจาก response, canonical patch, JUnit XML และ frozen hashes ผ่าน: `tencent-hy3`, `gpt-5-mini`, `glm-5.3-flash` ได้ **VERIFIED 3/3 model–case pairs** บน **repository อิสระเพียง 1 แห่ง** ใช้ input/output tokens ตามลำดับ 968/14,157; 957/125; 952/99. Gateway ส่ง response-cost header ครบทั้งสาม (0.007602672, 0.00128025, 0.0001923 ในหน่วยที่ gateway รายงาน) แต่ **ยังไม่ยืนยันสกุลเงินหรือเทียบเป็นเงินที่เรียกเก็บจริง**. ดูเครื่องมือ [`run_pysnooper_llm_feasibility_v1.py`](run_pysnooper_llm_feasibility_v1.py), [`audit_pysnooper_llm_feasibility_v1.py`](audit_pysnooper_llm_feasibility_v1.py) และ [`audit JSON`](results/pysnooper_llm_feasibility_audit_v1.json). Raw prompts/responses/patches และ JUnit อยู่ใน `results/v25_pysnooper_llm_feasibility_v1/` บนเครื่องและไม่ขึ้น Git เพราะอาจใหญ่/ขึ้นกับ local image; Git เก็บตัวรัน, frozen lock และ audit summary.

นี่พิสูจน์ได้เพียงว่า **interface และ verifier ใช้งานกับ repository ใหม่ได้จริง** ไม่ใช่ 3 repositories, ไม่ใช่ผล CF-Fit เทียบ Central-Fit, ไม่ใช่หลักฐานสถิติของความทั่วไป และยัง **ไม่ปิด Major Revision**. Gate ข้อ 1–4 ด้านบนยังใช้กับ *paired allocation main extension*; รอบ exploratory นี้ถูกระบุแยกไว้ตั้งแต่ก่อน calls และห้ามนำไป pool กับ v2.4 main.
