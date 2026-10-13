# Task Difficulty Rubric

LLM evaluator ให้คะแนนโดยห้ามเห็น strategy, Agent ที่จะรับงาน หรือผล simulation

แต่ละมิติให้ 0 ถึง 2 คะแนน:

1. specification ambiguity
2. scope and context span
3. dependency depth
4. reasoning depth
5. verification complexity

คะแนนรวม provisional mapping สำหรับ Pilot:

- 0-3 เป็น D1
- 4-6 เป็น D2
- 7-10 เป็น D3

Failure impact เก็บเป็น criticalityแยก ไม่รวมใน difficulty ใช้ role-conditioned LLM passes สามรอบและรายงาน pairwise agreement ก่อน Main

Pilot ใช้ deterministic provisional mapping จาก task template และ corpus characteristics เพื่อทดสอบ engineเท่านั้น ไม่ถือว่าแทน LLM-derived labels ที่ freeze สำหรับ Main
