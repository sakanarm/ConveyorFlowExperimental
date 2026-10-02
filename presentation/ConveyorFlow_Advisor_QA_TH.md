# คำถาม–คำตอบสำหรับอาจารย์ — ConveyorFlow v5

## 1. Contribution ใหม่จริง ๆ คืออะไร

กลไกจัดสรรงานแบบ decentralized self-selection สำหรับทีม Agent ที่ความสามารถและต้นทุนต่างกัน โดย Agent ประเมินงานเอง เลือกตาม capability–task fit และใช้ stand-down กับ aging เพื่อสงวนความสามารถสูงและป้องกันงานค้าง 13 policies เป็นหลักฐานทดลอง ไม่ใช่ contribution หลัก

## 2. ทำไมเรียก Decentralized ทั้งที่ยังมีสายพานและ atomic claim

คำว่า decentralized หมายถึง allocation decision ไม่มี global matcher ที่คำนวณว่าใครต้องทำงานใด Agent ตัดสินใจจากข้อมูลที่มองเห็นเอง ส่วน READY belt, event ledger และ atomic claim เป็น shared coordination infrastructure เพื่อรักษาความถูกต้องของสถานะ งานไม่ได้อ้างว่าทั้งระบบ fully distributed

## 3. Objective หลักคืออะไร

วัด trade-off ของ cost per verified task, completion, throughput, terminal time และ utilization ภายใต้ข้อจำกัดเดียวกัน ไม่รวมทุก metric เป็นคะแนนผู้ชนะเดียว เพราะ objectives อาจขัดกัน

## 4. ทำไมไม่ตั้ง Objective เป็น cost ต่ำสุดอย่างเดียว

ระบบที่ถูกที่สุดอาจปล่อยงานค้างหรือมี completion ต่ำ จึงต้องอ่าน cost ร่วมกับ verified completion, dead letter และ unsettled fraction มิฉะนั้นระบบที่ไม่ทำงานอาจดูเหมือนประหยัดที่สุด

## 5. CF-Fit ดีกว่า Static หรือไม่

ดีกว่าในความเร็วและการใช้ทรัพยากรภายใต้หลายเงื่อนไข แต่แพงกว่าและ Real-LLM มี completion ต่ำกว่า S3 จึงตอบเป็น trade-off ไม่ใช่คำว่า “ดีกว่า” แบบทุกมิติ

## 6. ทำไม CF-Fit ไม่ชนะ Central-Fit

Central-Fit เป็น matched centralized benchmark ที่ใช้ข้อมูลใกล้เคียงกันแต่จับคู่แบบ global ผลใกล้กันช่วยวัดราคาของการกระจาย decision authority โดยตรง จุดมุ่งหมายไม่ใช่บิดการทดลองให้ decentralized ชนะ centralized

## 7. ผลไม่ significant ระหว่าง CF-Fit กับ Central-Fit แปลว่าเทียบเท่ากันหรือไม่

ไม่แปลครับ การไม่ปฏิเสธสมมติฐานศูนย์อาจเกิดจาก effect เล็กหรือ power ไม่พอ การอ้าง equivalence ต้องกำหนด equivalence margin และใช้การทดสอบเฉพาะ เช่น TOST ซึ่งงานนี้ยังไม่ได้ทำกับ Real-LLM Main

## 8. Stand-down มี novelty แต่ผลเล็ก จะยังเขียนได้หรือไม่

เขียนได้ในฐานะ bounded refinement และกลไกสงวน capacity เชิงเหตุผล แต่ห้ามอ้างว่าเป็นสาเหตุหลักของผลทั้งหมด ทั้ง Simulation ablation และ Real-LLM extension ชี้ว่า Fit และ Aging ให้ผลชัดกว่า stand-down ในเงื่อนไขปัจจุบัน

## 9. Real-LLM ยืนยันอะไรเกี่ยวกับ Stand-down

เมื่อเอา stand-down ออก completion แทบไม่เปลี่ยนและ cost per verified task เพิ่มประมาณ 1.3% โดยไม่มี primary metric ที่ผ่าน Holm significance จึงสนับสนุนการตีความว่า stand-down เป็น refinement มากกว่ากลไกหลัก

## 10. Boundary compositions คืออะไร

ใน Simulation คือทีมที่อยู่ปลายขอบของความหลากหลาย แต่ตรึง team size และ mean ability เท่ากัน ได้แก่ H0=(2,2,2,2), H1=(1,2,2,3), H2=(1,1,3,3) เพื่อเปลี่ยน variance/composition โดยไม่เพิ่มกำลังเฉลี่ยของทีม

## 11. Homogeneous GLM ดีมาก แปลว่า heterogeneity ไม่จำเป็นหรือไม่

ยังสรุปไม่ได้ เพราะ Real-LLM homogeneous conditions เปลี่ยน model identity และไม่ได้ตรึง mean capability ให้เท่ากับ heterogeneous team ผลนี้เป็น boundary/sensitivity evidence ว่า composition สำคัญ ไม่ใช่ causal estimate ของ heterogeneity

## 12. ทำไม Homogeneous GLM กับ Homogeneous GPT ให้ผลคนละทิศ

เพราะความสามารถจริง ความสอดคล้องกับ workload, output behavior, latency และราคาแตกต่างกัน ผลนี้แสดงว่า team label อย่าง homogeneous อย่างเดียวไม่พอ ต้องระบุโมเดลและ resource mapping ที่ใช้ด้วย

## 13. Ability Rank วัดอย่างไร

วัดจาก behavioral pass rate บน held-out executable probes แยก ML Build และ Fix Bug ใช้ Wilson lower 95% confidence bound เป็น gate ของ Rank 1–3 ไม่ใช้ราคา ความใหม่ หรือชื่อรุ่นกำหนด rank โดยตรง ราคาและความเร็วเป็น resource attributes แยกต่างหาก

## 14. ใครกำหนดความยากของ Task

ชุดปัจจุบันใช้ role-conditioned LLM raters หลายบทบาทและ adjudication พร้อมบันทึก agreement และ sensitivity variants เพื่อให้ทำซ้ำได้ แต่ไม่เรียกว่า human ground truth การยืนยันกับผู้เชี่ยวชาญจริงถูกเว้นไว้เป็นขั้นตอนก่อน submission

## 15. ใช้ตัวโมเดลเดียวเขียนหลาย Role ถือเป็นผู้เชี่ยวชาญหลายคนได้หรือไม่

ไม่ได้ ถือเป็นหลายมุมมองจาก LLM เดียวกัน ไม่ใช่ผู้ประเมินอิสระและไม่แทน expert labels จากคน จึงใช้สร้าง provisional labels และ sensitivity analysis ได้ แต่ต้องเปิดเผยข้อจำกัด

## 16. ทำไมไม่ใช้ Oracle หรือ HEFT

Oracle ใช้ข้อมูลอนาคต ส่วน HEFT ต้องมี execution estimates และ global scheduling assumptions ซึ่งไม่ตรงกับ online local-observation setting งานจึงเลือก realistic static controls และ matched Central-Fit เพื่อให้เปรียบเทียบภายใต้ข้อมูลและข้อจำกัดใกล้กัน

## 17. ถ้าไม่มี Agent รับงานเกิดอะไรขึ้น

F2 จะ re-offer, tail-requeue และผ่อน eligibility/stand-down ตามอายุ เมื่อเกิน frozen bound หรือ requeue limit จะเป็น DEAD_LETTER จึงไม่มีการวนไม่สิ้นสุด ส่วน F3 central forced rescue แยกรายงานเป็น hybrid reference

## 18. `pass=false` หมายถึงอะไร

หมายถึงคำตอบของโมเดลไม่ผ่าน validator ของ task นั้น เช่น output ไม่ตรง schema, code รันไม่ผ่าน หรือผลไม่ตรง expected behavior ไม่ได้แปลว่า API call ล้มเหลวเสมอไป API failure, timeout และ validation failure ต้องบันทึกแยกกัน

## 19. P95 ลดมาก แปลว่าเร็วขึ้นจริงหรือไม่

ต้องอ่านร่วมกับ competing outcomes เพราะ policy ที่ปล่อยงาน unresolved มากอาจทำให้ terminal-time distribution ดูดีหรือแย่ผิดความหมาย งานจึงรายงาน completion, dead letter, unsettled และ cumulative incidence ควบคู่ ไม่สรุปจาก P95 เพียงตัวเดียว

## 20. ข้อมูลสาธารณะใหญ่พอหรือไม่

ใช้ UCI Adult 48,842 records, Beijing Air Quality 420,768 records และ CodeXGLUE Bugs2Fix 46,680 pairs ทุกชุดเกิน 20,000 ตามเกณฑ์ แต่ต้องอธิบายว่า Simulation ใช้คุณลักษณะ workload ที่สกัดจากข้อมูลเหล่านี้ ส่วน Real-LLM ใช้ชุด 60 cases ที่ freeze ไว้

## 21. ทำไม Real-LLM Main มีเพียง 10 seeds

Real-LLM เป็นการยืนยันภายนอกที่มีต้นทุนและ provider variability สูง จึงใช้ paired seeds, frozen cases, validators และ Holm correction เพื่อเพิ่มประสิทธิภาพของการเปรียบเทียบ อย่างไรก็ตาม n=10 ยังเป็นข้อจำกัดและต้องรายงาน confidence intervals กับ effect sizes ไม่อ้าง generalization เกินขอบเขต

## 22. ผล Real-LLM Main ที่สำคัญที่สุดคืออะไร

เทียบ Static S3, CF-Fit เร็วกว่าและใช้ทรัพยากรสูงกว่าอย่างชัดเจน แต่ completion ต่ำกว่าและ cost per verified task สูงกว่า เป็นหลักฐานตรงว่ากลไกสร้าง speed–utilization versus completion–cost trade-off

## 23. ทำไมผล Simulation กับ Real-LLM ไม่เหมือนกันทั้งหมด

Simulation ควบคุม distributions และ resource mappings ตามสมมติฐาน ส่วน Real-LLM มีพฤติกรรมโมเดลจริง เช่น formatting error, validator failure, latency และ workload fit ความต่างจึงเป็นผลที่ควรวิเคราะห์ ไม่ใช่สิ่งที่ต้องปกปิด และช่วยกำหนด external-validity boundary

## 24. Timing ของ Real-LLM Extension เชื่อถือได้แค่ไหน

Completion และ cost มี n=10 ครบทุกเงื่อนไข แต่ timing-valid counts คือ 10/10/8/9 เนื่องจากสาม runs เกิน frozen provider-gap threshold จึงตัดออกเฉพาะ timing analysis และกำหนด time, throughput, utilization ข้าม execution windows เป็น exploratory

## 25. ทำไมตัด provider-gap runs ออกจาก timing แต่ยังใช้ใน completion/cost

เพราะ provider gap ทำให้ wall-clock ไม่สะท้อนกลไก scheduling แต่ output, validator result และ token cost ยังเป็นผลที่สังเกตได้จริง การตัดแบบ metric-specific ถูกกำหนดและบันทึกไว้เพื่อไม่ทิ้งข้อมูล primary outcome โดยไม่มีเหตุผล

## 26. Radar chart ใช้พิสูจน์ว่าใครดีที่สุดหรือไม่

ไม่ใช้ Radar เป็น descriptive visualization ที่ทำ min–max normalization รายแกน พื้นที่รูปหลายเหลี่ยมขึ้นกับ scaling และไม่ใช่ inferential statistic ข้อสรุปต้องมาจาก metric-level contrasts, intervals และ multiplicity-adjusted tests

## 27. ทำไมทีมไม่เกิน 4 Agent

เป็น scope ที่ freeze เพื่อควบคุม factorial design, cost และการตีความ composition ให้ชัด Scalability มากกว่าสี่ Agent เป็น future work และไม่ควรอ้างว่าได้รับการพิสูจน์แล้ว

## 28. Model จริงใช้แล้วหรือยัง

ใช้แล้วครับ Real-LLM Main มี 10 paired seeds × 60 tasks × 3 policies และ Extension มี 10 validated runs ต่อเงื่อนไขหลัก ผลถูกแยกจาก mock/infrastructure audit อย่างชัดเจน

## 29. `research_results=false` ในไฟล์เก่าหมายถึงอะไร

เป็นสถานะของ pre-execution readiness หรือ mock/oracle audit ณ เวลานั้น ไม่ใช่ผล Real-LLM ภายหลัง ผลวิจัยจริงต้องอ้างจาก aggregated Main และ Extension artifacts ที่ผ่าน validation แล้วเท่านั้น

## 30. Paper พร้อมส่ง Journal หรือยัง

พร้อมให้อาจารย์ตรวจ scientific story, methodology, Simulation และ Real-LLM evidence แล้ว แต่ก่อน submission ต้องเลือก target journal และ template, เติม metadata/DOI ที่ขาด, ทำ human-expert validation ตามแผน และตรวจ reproducibility package กับข้อกำหนด ethics/data-use ของวารสาร

## 31. Claim ที่ปลอดภัยที่สุดคืออะไร

ภายใต้ workloads, teams และราคาโมเดลที่กำหนด ConveyorFlow เปลี่ยนเวกเตอร์ของ completion–cost–time–throughput–utilization เมื่อเทียบกับ static allocation และให้ผลใกล้ matched Central-Fit ใน Real-LLM Main โดย Fit และ Aging เป็นองค์ประกอบที่มีผลชัดกว่า Stand-down

## 32. ถ้าอาจารย์ถามว่า “สุดท้ายงานนี้ดีกว่าไหม”

ตอบว่าไม่มีคำตอบเดียวครับ CF-Fit เหมาะเมื่อให้ความสำคัญกับความเร็ว การใช้ capacity และการลดการรอของสายพาน แต่ Static อาจเหมาะเมื่อเน้นต้นทุนหรือ completion ใน workload นี้ ส่วน Central-Fit เป็น benchmark ที่แข็งแรงแต่ต้องมีผู้ตัดสินใจส่วนกลาง งานวิจัยนี้ทำให้ trade-off เหล่านี้วัดและอธิบายได้

## 33. Baseline ยังมี Conveyor belt หรือไม่

มีครับ เราตรึง DAG, dependency rule, READY belt, one-task-per-agent limit และ execution semantics ให้เหมือนกัน ความต่างคือ Static ใช้ routing table ล่วงหน้า ส่วน ConveyorFlow ให้ Agent ว่างประเมินและ volunteer จาก READY set

## 34. ข้อเสนอแนะครั้งก่อนถูกแก้ครบหรือยัง

แก้แกนหลักแล้ว: RQ1 ใช้ผลต่อหลาย objectives, RQ2 แยก heterogeneity, contribution เน้น decentralized self-selection + fit + stand-down/aging, policies เป็น experimental evidence, มี ablation, baseline ใช้สายพานเดียวกัน และมี Real-LLM evidence จุดที่ยังรอคือ human-expert validation และการเลือก journal/template

## คำตอบสั้น 20 วินาทีสำหรับปิดการซักถาม

ConveyorFlow แสดงให้เห็นว่า Agent ที่ต่างกันสามารถเลือกงานเองบนสายพานเดียวกันโดยไม่ต้องมี global matcher ผล Simulation และ Real-LLM ไม่ได้ชี้ว่ากลไกนี้ชนะทุกด้าน แต่ชี้ trade-off ที่วัดได้ระหว่างความเร็ว การใช้ทรัพยากร completion และต้นทุน พร้อมแยก contribution ของ Fit, Aging และ Stand-down อย่างโปร่งใสครับ
