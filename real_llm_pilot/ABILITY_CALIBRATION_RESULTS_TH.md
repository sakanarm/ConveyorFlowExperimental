# ผล Ability Calibration และการเลือกทีม MFEC

## สรุปผลลัพธ์

เลือกทีม heterogeneous สำหรับขั้น Real-LLM ก่อน Main Experiment จำนวน 3 agents:

| Agent | ML Build | Fix Bug | บทบาทเชิงปฏิบัติการ |
|---|---:|---:|---|
| `tencent-hy3` | L3 | L1 | เก่ง ML แต่รับ Fix Bug ได้มั่นคงเฉพาะ D1 ภายใต้ token budget |
| `gpt-5-mini` | L2 | L3 | ระดับกลางใน ML และระดับสูงใน Fix Bug |
| `glm-5.3-flash` | L3 | L3 | Advanced generalist |

ดังนั้นทีมมี workload-specific capability heterogeneity จริงทั้งสอง workload:

- ML Build มี rank vector `[L3, L2, L3]`
- Fix Bug มี rank vector `[L1, L3, L3]`

การแบ่งนี้ไม่ได้อนุมานจากชื่อรุ่น ราคา latency หรือจำนวน token แต่ได้จาก
held-out probes และ Wilson lower 95% confidence-bound gate ที่กำหนดก่อน
Main Experiment

## ความหมายต่อ ConveyorFlow

องค์ประกอบของทีมทำให้ทดสอบ Capability Fit และ Stand-down ได้โดยตรง:

1. สำหรับ Fix Bug D1, GPT และ GLM ทำได้แต่ควร stand down เพื่อเปิดให้ Tencent
   รับงานง่าย และเก็บ agent ระดับสูงไว้สำหรับ D2-D3
2. สำหรับ ML D1-D2, Tencent และ GLM สามารถ stand down ให้ GPT รับงานที่อยู่ใน
   capability envelope ของ GPT
3. สำหรับ ML D3 ให้ Tencent หรือ GLM volunteer; สำหรับ Fix Bug D2-D3 ให้ GPT
   หรือ GLM volunteer
4. ถ้าไม่มี agent volunteer งานต้องกลับเข้า queue ตาม aging/retry rule ไม่ให้
   งานหายออกจากระบบ

นี่คือรูปแบบ heterogeneity แบบ capability profile ไม่ได้บังคับว่าทุก workload
ต้องมี L1, L2 และ L3 ครบอย่างละหนึ่งตัว

## Calibration ที่ดำเนินการ

- Gemini 3/3.5/3.8 Flash: ทั้งหมดได้ L3/L3 จึงเก็บเป็น homogeneous evidence
  ไม่ใช้เป็น heterogeneous team
- Cross-family screen: GLM L3/L3, GPT-5 mini L2/L3 และ Claude Sonnet 5 L2/L3
- Minimax M2: L3/L3 จึงไม่ใช่ L1 candidate
- Tencent HY3: L3/L1 ภายใต้ common 4,096 completion-token limit
- หยุดค้นหาโมเดลตาม stopping rule หลัง Tencent เพื่อป้องกันการเลือกโมเดล
  แบบไล่หาผลที่ต้องการ

## Protocol deviations ที่เปิดเผย

1. CodeXGLUE exact textual repair ไม่เหมาะเป็น primary oracle เพราะอาจปฏิเสธ
   patch ที่ทำงานเทียบเท่ากัน จึงเปลี่ยน Fix Bug calibration เป็น executable
   hidden unit tests และเก็บ exact-match รอบแรกเป็น instrument pilot เท่านั้น
2. Adapter รุ่นแรกมี unintended 1,024-token cap ทั้งที่ config กำหนด 4,096
   จึง rerun เฉพาะ call ที่จบด้วย `finish_reason=length` และเก็บ ledger ทั้งสอง
   ชุดไว้ audit
3. Safety parser เคยปฏิเสธ Python code fence, `_` loop variable,
   `dict.fromkeys`, `type/isinstance` และ safe `try/except TypeError` จึงแก้เฉพาะ
   false-rejection rules แล้ว revalidate offline โดยไม่เรียก API ซ้ำ

รายละเอียดอยู่ใน `CALIBRATION_DEVIATION_LOG.md`

## Resource observations ที่ไม่ใช้จัด Rank

ค่าจาก screening 30 probes ต่อ model:

| Model | Mean latency/call | Input tokens | Output tokens |
|---|---:|---:|---:|
| Tencent HY3 | 11.061 s | 3,591 | 34,914 |
| GPT-5 mini | 2.012 s | 3,495 | 1,157 |
| GLM 5.3 Flash | 8.988 s | 3,588 | 9,742 |

Tencent มี output-token consumption สูงและมี 5 responses ที่ชน 4,096-token
limit ปัจจัยนี้เป็น operational behavior ภายใต้ resource budget และต้องรายงาน
แยกจาก Ability Rank

## Homogeneous controls สำหรับ RQ2

- `H_L3_GENERALIST`: GLM 5.3 Flash จำนวน 3 agent instances
- `H_L2_ML`: GPT-5 mini จำนวน 3 agent instances

เปรียบเทียบกับ heterogeneous team เดียวกันภายใต้ task stream, timeout, retry,
validator และ policy เดียวกัน

## สิ่งที่เขียนเป็น Claim ได้ในขณะนี้

เขียนได้ว่า calibration แสดง workload-specific capability profiles แตกต่างกัน
ภายใต้ probes และ resource budget ที่กำหนด และทีมที่เลือกเหมาะสำหรับทดสอบ
Capability Fit/Stand-down ต่อไป

ยังเขียนไม่ได้ว่า ConveyorFlow ชนะ baseline บน LLM จริง เพราะยังไม่มี
allocation-policy execution และห้ามเรียก calibration/screening ว่า Main
Experiment

## เงื่อนไขก่อน Main Real-LLM

1. ขอ immutable alias-to-underlying-model mapping และ effective date จาก MFEC
2. บันทึกราคา input/output tokens ของแต่ละ alias
3. materialize 60 task bundles พร้อม deterministic validators
4. freeze prompt, generation, retry, timeout, seed และ policy configuration
5. ประมาณจำนวน calls/tokens/cost ก่อนเริ่ม เพื่อไม่ให้ทดลองเกินงบ

Figure หลักของขั้นนี้คือ `figures/fig_ability_profile_radar.png` โดยพื้นที่ใน
radar ใช้เพื่อ descriptive visualization เท่านั้น ไม่ใช่ composite score
