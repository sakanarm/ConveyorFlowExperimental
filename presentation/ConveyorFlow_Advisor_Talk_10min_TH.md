# บทพูดนำเสนอ ConveyorFlow ภายใน 10 นาที — สำหรับสไลด์ v5

> หลักการพูด: เล่าเป็นงานวิจัยเรื่อง trade-off ไม่ใช่การประกาศว่า CF-Fit ชนะทุกวิธี และแยกผล Simulation ออกจากผล Real-LLM ให้ชัดเจน

## Slide 1 — เปิดเรื่อง (0:00–0:25)

สวัสดีครับ วันนี้ผมขอนำเสนอ ConveyorFlow ซึ่งเป็นสถาปัตยกรรมจัดสรรงานสำหรับทีม LLM Agent ที่ให้งานไหลอยู่บนสายพาน และให้ Agent อาสาเลือกงานด้วยตนเองตามความสามารถ งานนี้ไม่ได้ตั้งสมมติฐานว่า ConveyorFlow ต้องชนะทุกตัวชี้วัด แต่ศึกษาว่าการกระจายอำนาจตัดสินใจเปลี่ยน trade-off ระหว่างความสำเร็จ ความเร็ว การใช้ทรัพยากร และต้นทุนอย่างไรครับ

## Slide 2 — สิ่งที่ปรับตามข้อเสนอแนะ (0:25–1:00)

จากข้อเสนอแนะครั้งก่อน ผมปรับ RQ1 จากคำถามว่า “ดีกว่าหรือไม่” เป็นการวัดผลต่อ throughput, completion time, utilization และ cost โดยตรง เพิ่ม RQ2 เพื่อเปรียบเทียบ homogeneous กับ heterogeneous team ภายใต้ CF-Fit และย้าย 13 policies ไปเป็น experimental design กับ ablation ไม่ใช่ contribution หลัก นอกจากนี้ ConveyorFlow และ baseline ใช้ workload และสายพานเดียวกัน ต่างกันที่ผู้ตัดสินใจจัดสรรงานครับ

## Slide 3 — Scientific contribution (1:00–1:40)

Scientific story มีห้าขั้นครับ หนึ่ง Agent มี Ability Rank และต้นทุนต่างกัน สอง Agent ประเมินงานจากข้อมูลที่ตนเห็น สามเลือกงานตาม capability–task fit สี่ Agent ที่เก่งเกินความจำเป็นสามารถ stand down ชั่วคราวเพื่อสงวนกำลังไว้ และห้า aging ป้องกันงานค้างโดยค่อย ๆ ผ่อนเงื่อนไข ดังนั้น contribution คือกลไก decentralized self-selection ที่เชื่อม heterogeneity, fit, stand-down และ aging เข้าด้วยกัน ไม่ใช่จำนวน policies ครับ

## Slide 4 — Tasks ride the belt: ConveyorFlow (1:40–2:15)

ภาพนี้แสดงแนวคิด tasks ride the belt งานจะขึ้นเป็น READY เมื่อ dependency เสร็จ Agent ที่ว่างจึงมอง ประเมิน และเสนอรับงาน โดย Ability Rank 1, 2 และ 3 หมายถึงระดับความสามารถที่วัดเชิงพฤติกรรม หากหลาย Agent เลือกงานเดียวกัน จะใช้ backoff และ atomic compare-and-swap ให้มีผู้ชนะเพียงรายเดียว ไม่มี global arbiter ที่จับคู่งานให้ทุกคนครับ

## Slide 5 — Baseline บนสายพานเดียวกัน (2:15–2:45)

Baseline ยังใช้ DAG, READY belt, dependency rule และข้อจำกัดหนึ่งงานต่อ Agent เหมือนกัน แต่ใช้ static routing table กำหนดเจ้าของ skill ล่วงหน้า หากเจ้าของไม่ว่าง งานต้องรอแม้ Agent อื่นจะทำได้ การออกแบบแบบนี้ช่วยให้เปรียบเทียบเฉพาะกลไกตัดสินใจจัดสรรงาน โดยไม่เปลี่ยนสถาปัตยกรรม workload ครับ

## Slide 6 — หนึ่ง tick ของระบบ (2:45–3:20)

ในหนึ่ง tick ระบบอัปเดตสถานะ Agent ตรวจผลที่จบ รับงานใหม่ refresh dependency แล้วจึงเปิดช่วง reach ให้ Agent ประเมินและเสนอรับงาน Claims ถูกตัดสินแบบ atomic ผู้ชนะเริ่มทำงาน และทุก event ถูกบันทึก หากไม่มีผู้สมัคร งานจะ age และ requeue ไม่ถูกบังคับมอบหมายโดยศูนย์กลาง และจะเป็น DEAD_LETTER เมื่อเกินขอบเขตที่ freeze ไว้ครับ

## Slide 7 — Experimental design (3:20–4:00)

Simulation ใช้ 50 paired seeds และ common random numbers รวม 22,500 runs หน่วยวิเคราะห์คือ run ต่อ seed ไม่ใช่ task ภายใน run แบ่งเป็น RQ1 เปรียบเทียบ CF-Fit กับ static controls และ Central-Fit, RQ2 เปลี่ยน team composition โดยตรึง team size และ mean ability, RQ3 ทำ component ablation และ E4 ทดสอบกรณีไม่มี Agent อาสา Workloads มาจาก UCI Adult, Beijing Air Quality และ CodeXGLUE Bugs2Fix ซึ่งเป็นข้อมูลสาธารณะขนาดเกิน 20,000 รายการครับ

## Slide 8 — RQ1 จาก Simulation (4:00–4:45)

ผล RQ1 ต้องอ่านเป็นเวกเตอร์ของผลลัพธ์ เทียบ static controls CF-Fit เพิ่ม verified throughput ประมาณ 9.4 ถึง 45.3 เปอร์เซ็นต์ และลด P95 terminal flow time ประมาณ 67.9 ถึง 83.1 เปอร์เซ็นต์ แต่ cost per verified task เพิ่มประมาณ 4.7 ถึง 52.4 เปอร์เซ็นต์ Completion ผ่าน non-inferiority ทั้งแปด contrasts ส่วนเทียบ Central-Fit ค่าต้นทุนและเวลาใกล้กัน แต่ throughput ของ CF-Fit ต่ำกว่าเล็กน้อย จึงไม่มีเหตุผลให้กล่าวว่า CF-Fit ชนะทุกด้านครับ

## Slide 9 — Radar แสดง trade-off (4:45–5:15)

Radar chart ใช้เพื่อสื่อรูปทรงของ trade-off เท่านั้น แต่ละแกนทำ min–max normalization ภายใน resource regime และไม่ใช่ composite inferential score ภาพแสดงว่าไม่มี policy เดียวครองทุกแกน CF-Fit ใกล้ Central-Fit ในหลาย outcome ส่วน static บางตัวเด่นเฉพาะต้นทุนหรือ outcome บางด้าน การสรุปจึงอิงผลทดสอบราย metric ไม่อิงพื้นที่ของรูปหลายเหลี่ยมครับ

## Slide 10 — RQ2: Capability heterogeneity (5:15–5:55)

RQ2 ใช้ H0 เท่ากับ 2-2-2-2, H1 เท่ากับ 1-2-2-3 และ H2 เท่ากับ 1-1-3-3 ทุกทีมมีสมาชิกสี่รายและ mean ability เท่ากับสอง จึงเป็น boundary compositions ที่ทดสอบผลของความกระจายโดยไม่เพิ่มกำลังเฉลี่ยของทีม ใน regime ที่ ability แยกจากต้นทุน heterogeneity ลดต้นทุนประมาณ 5 เปอร์เซ็นต์แต่ throughput ลดเล็กน้อย ส่วนเมื่อ ability ผูกกับราคาและความเร็ว ต้นทุนเพิ่มประมาณ 40 ถึง 82 เปอร์เซ็นต์เพื่อแลก throughput เพิ่ม 2 ถึง 5 เปอร์เซ็นต์ จึงได้ประโยชน์แบบมีเงื่อนไขครับ

## Slide 11 — RQ3: Ablation (5:55–6:35)

Ablation ชี้ว่า Fit และ Aging เป็นองค์ประกอบที่มีผลชัดกว่า Stand-down โดย Fit ลดต้นทุนประมาณ 3.5 ถึง 3.7 เปอร์เซ็นต์และลด P95 ประมาณ 12 เปอร์เซ็นต์ ส่วน Aging เพิ่ม completion ราว 10.4 ถึง 10.8 จุดและลด dead letter แต่ทำให้ P95 ยาวขึ้น Stand-down เปลี่ยน cost และ throughput เพียงเล็กน้อย จึงควรเขียนว่าเป็น bounded refinement ไม่ใช่แกนผลลัพธ์หลักครับ

## Slide 12 — E4: เมื่อไม่มี Agent อาสา (6:35–7:15)

F2 เป็น decentralized fallback: งานถูกเสนอใหม่ ย้ายไปท้ายคิว และผ่อน eligibility กับ stand-down ตามอายุ ก่อนจบเป็น DEAD_LETTER เมื่อเกินขอบเขต เทียบ F0 และ F1 กลไกนี้ลด cost และ dead letter พร้อมเพิ่ม throughput แต่ใช้เวลาจนถึง terminal outcome นานขึ้น ส่วน F3 เป็น central rescue ที่เร็วกว่า แต่เปลี่ยนผู้ตัดสินใจกลับเป็นศูนย์กลาง จึงรายงานเป็น hybrid reference ไม่ใช่ ConveyorFlow หลักครับ

## Slide 13 — Real-LLM Main (7:15–8:10)

จากนั้นผมรัน LLM จริง 10 paired seeds เมล็ดละ 60 tasks เปรียบเทียบ CF-Fit, Static S3 และ Central-Fit เทียบ S3 นั้น CF-Fit มี completion ต่ำกว่า 24.7 เปอร์เซ็นต์และ cost per verified task สูงกว่า 62.1 เปอร์เซ็นต์ แต่ wall time ต่ำกว่า 62.1 เปอร์เซ็นต์ throughput สูงกว่า 99.5 เปอร์เซ็นต์ และ utilization สูงกว่า 63.6 เปอร์เซ็นต์ ทุก contrast นี้มี Holm p เท่ากับ .005859 ส่วนเทียบ Central-Fit ยังไม่พบ metric ใดแตกต่างที่ Holm p ต่ำกว่า .05 แต่ “ไม่ significant” ไม่ได้แปลว่าเทียบเท่ากันครับ

## Slide 14 — Real-LLM Extension (8:10–9:05)

Extension ใช้ 10 paired seeds ต่อเงื่อนไขเพื่อตรวจ stand-down และ boundary conditions เมื่อเอา stand-down ออก completion ไม่เปลี่ยนและ cost per verified task เพิ่มประมาณ 1.3 เปอร์เซ็นต์ โดยไม่ significant ในสอง primary metrics สอดคล้องกับการเป็น refinement สำหรับ homogeneous GLM completion สูงขึ้น 110.5 เปอร์เซ็นต์และ cost per verified task ลด 82.6 เปอร์เซ็นต์ ขณะที่ homogeneous GPT ให้ผลตรงข้าม อย่างไรก็ตามนี่เป็น model-specific boundary evidence ไม่ใช่ causal proof ว่า homogeneous หรือ heterogeneous ดีกว่า เพราะ identity ของโมเดลและ mean capability ไม่ได้ matched กัน ส่วน time, throughput และ utilization ข้าม execution windows รายงานเป็น exploratory เท่านั้นครับ

## Slide 15 — สรุปและขอคำแนะนำ (9:05–10:00)

สรุปคือ Simulation แสดงว่า CF-Fit เปลี่ยน trade-off ระหว่างต้นทุน ความเร็ว completion และ utilization อย่างมีระบบ โดย Fit และ Aging มี contribution ที่วัดได้ ส่วน Real-LLM ยืนยันว่าความเร็วและ utilization ที่ดีขึ้นสามารถแลกมากับ completion และต้นทุน และ Extension แสดงว่า model composition เป็น boundary condition สำคัญ Claim ที่เขียนได้คือผลเชิง trade-off ภายใต้เงื่อนไขที่ทดสอบ Claim ที่ยังห้ามเขียนคือ CF-Fit ชนะทุก baseline, ผลไม่ significant แปลว่าเทียบเท่า หรือ homogeneous results พิสูจน์ causal effect ของ heterogeneity ขั้นต่อไปที่ขอคำแนะนำคือ contribution framing, target journal และแผน human-expert validation ก่อน submission ครับ

## ประโยคปิด 15 วินาที

ConveyorFlow ไม่ได้เสนอผู้ชนะทุก metric แต่เสนอและทดสอบราคากับประโยชน์ของการให้ Agent ที่ต่างกันเลือกงานเองบนสายพานเดียวกัน โดยใช้ capability fit, stand-down และ aging เป็นกลไกที่ตรวจสอบแยกองค์ประกอบได้ครับ

## ตัวเลขที่ควรจำก่อนนำเสนอ

- Simulation: 22,500 runs, 50 paired seeds
- Real-LLM Main: 10 paired seeds × 60 tasks × 3 policies
- CF-Fit เทียบ S3: completion −24.7%, cost/verified +62.1%, wall time −62.1%, throughput +99.5%, utilization +63.6%
- Main CF-Fit เทียบ S3: Holm p=.005859 ทุก metric-level contrast ที่รายงาน
- CF-Fit เทียบ Central-Fit: ไม่พบ Holm p<.05 ในหก metrics แต่ไม่ใช่หลักฐาน equivalence
- Extension primary outcomes: 10 paired seeds ต่อเงื่อนไข; timing-valid n=10/10/8/9 และ timing ข้าม window เป็น exploratory
