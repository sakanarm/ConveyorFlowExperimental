# แผนขยายหลักฐาน Real-LLM หลังรอบ v2.4 (ฉบับร่าง ยังไม่ใช่ execution lock)

สถานะ: ร่างระหว่างที่ `main_v2` 12 paired blocks กำลังทำงาน ห้ามนำร่างนี้ไปเปลี่ยน case, arm, prompt, model, validator หรือ analysis ของรอบที่ตรึงไว้แล้ว และห้ามเริ่ม paid extension จนกว่าจะ freeze protocol ใหม่ก่อนดูผลของ extension

## เหตุผล

รอบปัจจุบันมี 12 paired blocks; แต่ละ block รันโจทย์เดียวกันภายใต้ CF-Fit, Central-Rule-Matched และ Static-Owners. ฝั่ง repository repair มี 3 bugs ต่อ 4 source repositories; ฝั่ง ML ใช้ Adult และ Beijing ซ้ำ. ดังนั้น 36 arm-runs, 180 stage-level calls โดยประมาณ, หรือจำนวน token **ไม่ใช่** 36 หรือ 180 ตัวอย่างอิสระ. รอบนี้เป็นหลักฐานว่ากลไกทำงานกับ ML DAG และ repository repair จริง และใช้ประเมิน effect/ความแปรปรวนเบื้องต้นได้ แต่ไม่เพียงพอโดยตัวมันเองสำหรับอ้างความเหนือกว่า/เทียบเท่าโดยทั่วไป. สคริปต์วิเคราะห์ปัจจุบันระบุ repository-cluster bootstrap เป็น descriptive เท่านั้น เพราะมีเพียง 4 repository clusters.

## สิ่งที่ต้องรายงานจาก 12 blocks โดยไม่คัดผล

1. Independent audit ต้องผ่านทุก block; นับทุก provider attempt, failure, timeout และ unknown cost ตาม denominator ที่ตรึงไว้. แยก operational overhead จาก instrument incident เดิม.
2. แสดงค่าแต่ละ arm และ paired difference ของ CF-Fit ลบ Central-Rule-Matched และ CF-Fit ลบ Static-Owners สำหรับ throughput, completion time ของงานที่ verified, busy/productive utilization และ cost per verified job (เฉพาะเมื่อค่า cost ครบ). แสดง verified/arrived job counts และ failure reasons ประกอบเสมอ เพื่อไม่ให้ completion time แบบเฉพาะงานที่สำเร็จกลบงานล้มเหลว.
3. แสดง plot ของ paired differences ราย block, distribution ตาม repository/ML dataset, uncertainty แบบ descriptive และ sensitivity ที่ตัด BLOCK_01 ซึ่งเคยมี partial v1 exposure. ไม่ใช้ `p > .05` เป็นหลักฐานว่า CF-Fit และ Central-Rule-Matched เทียบเท่ากัน.
4. แยก no-fault allocation comparison จาก fault-domain/recovery experiment. ถ้าจะอ้างลด single point of failure ให้จำกัดไว้ที่ **allocation-decision layer** และรายงาน failure injection/control ที่จับคู่กติกา ไม่ขยายเป็นความทนทานของระบบทั้งหมด.

## รอบขยายที่ต้องตรึงก่อนเรียก LLM

1. ตรึง claim และ estimand ก่อน: RQ1 เป็นเวกเตอร์ trade-off ไม่ใช่คำว่า “ดีกว่าทุกด้าน”. Contrast หลักสำหรับ isolation คือ CF-Fit เทียบ Central-Rule-Matched ด้วย case, roster, ability profile, fit rule, prompt, model version, executor, verifier, horizon และ cost accounting เดียวกัน; เปลี่ยนเฉพาะที่อยู่ของผู้ตัดสินใจเลือกงาน. Static-Owners เป็น control สำหรับ no-volunteering. RQ2 (heterogeneity) และ stand-down ablation เป็นคำถามแยก ไม่อนุมานจาก RQ1 อย่างเดียว.
2. เลือก outcome หลักจำนวนน้อยเพื่อวางขนาดตัวอย่าง/precision ก่อน (เช่น verified-job throughput และ provider cost per verified job ถ้า cost ครบ) และยังรายงาน outcome อื่นทั้งหมดโดยไม่คัดเลือก. กำหนด smallest effect of interest หรือความกว้าง CI ที่ยอมรับได้ **ตามความหมายเชิงระบบ/ค่าใช้จ่าย** ก่อนดูผล extension. ค่า threshold นี้ต้องให้ผู้วิจัยกับที่ปรึกษารับรอง; ไม่สร้างจากขนาดผลที่บังเอิญเห็นใน pilot. หากต้องทดสอบหลายสมมติฐาน confirmatory ให้ระบุ family และวิธีควบคุม multiplicity ไว้ก่อน; ทางเลือกคือประกาศทั้งหมดเป็น estimation/exploratory และไม่ใช้ภาษายืนยันสมมติฐาน.
3. ใช้ 12 blocks เป็น pilot เพื่อประมาณ variance/correlation แบบระมัดระวัง แล้วทำ simulation-based sample-size/precision analysis ที่รักษา hierarchy: source repository หรือ ML dataset → case → paired arms → repeated stochastic run. กำหนดจำนวน independent source projects/datasets/cases จากเกณฑ์ข้อ 2; ไม่เพิ่มเพียง seeds หรือ stages เพื่อทำให้ n ดูใหญ่. ระบุ sensitivity ต่อค่า variance ที่สูงกว่าค่าจาก pilot และต่อ missing/unknown cost.
4. คัด public repository cases ใหม่แบบ pre-outcome-blind จาก project/bug metadata. เสนอ diversity floor เชิงออกแบบ: อย่างน้อย 8 source repositories และอย่างน้อย 4 public ML datasets ที่มี ≥20,000 rows; **นี่ไม่ใช่ power guarantee** และ final N อาจสูงกว่า. ตรวจ buggy-fail/fixed-pass, container image, visible test, public regression, fresh replay และ gold-free prompt ก่อน freeze. เก็บรายการทุก case ที่คัดออกพร้อมเหตุผล; ห้ามแทน case หลังเห็น LLM outcome. ไม่ปน prior-exposed v2.3/v2.4 cases เป็น independent new cases.
5. ใช้ทีมไม่เกิน 4 model ต่อ run และ profile เดิมหรือรุ่นที่ประกาศล่วงหน้า; ไม่เปลี่ยนรุ่นในกลาง paired block. Balance arm order และ model assignment; บันทึก provider model ID, token, latency, pricing provenance, request/response hashes, container digest และ code commit. หากราคาจาก provider ไม่ครบ ให้ cost เป็น missing ไม่แทนด้วยค่าคาดเดา; token เป็น metric แยก.
6. Freeze execution lock, analysis plan และ stopping rule ก่อน extension call แรก. ห้ามดูผลระหว่างทางแล้วเพิ่ม N จนมีนัยสำคัญ; ถ้าต้องการ adaptive/sequential design ต้องระบุ alpha/coverage control ไว้ตั้งแต่ต้น. Audit ทุก block โดย verifier ที่ไม่อาศัย LLM output self-report.

## เกณฑ์ตัดสินการเขียน paper

- หาก 12-block pilot เป็นหลักฐานทั้งหมด: เขียนว่า bounded ecological evaluation / feasibility และรายงาน uncertainty; ไม่อ้าง population-level superiority, equivalence หรือ statistical power ที่ไม่ได้วางแผน.
- หาก extension ผ่าน qualification, audit และ precision/power gate: สรุปเฉพาะ contrast/outcome ที่ CI รองรับ พร้อมข้อจำกัดด้าน project/dataset/model coverage. ผลที่ไม่ชนะหรือ cost เพิ่มต้องรายงานตรง ๆ.
- ไม่อ้างว่า publication/Q2 acceptance ถูกการันตีโดย p-value หรือจำนวน API calls. เป้าหมายคือ manuscript ที่ตรวจสอบและทดลองซ้ำได้ พร้อม claim ไม่เกินหลักฐาน.

ที่มาด้านวิธีวิจัย: [Lakens, *Sample Size Justification* (2022)](https://doi.org/10.1525/collabra.33267); [Leyrat et al., *Cluster randomized trials with a small number of clusters: which analyses should be used?* (2018)](https://academic.oup.com/ije/article/47/1/321/4091562). งานเหล่านี้เป็นหลักเกณฑ์การวางขนาดตัวอย่าง/การระวัง small clusters; ไม่ได้กำหนดจำนวนขั้นต่ำเฉพาะ ConveyorFlow.
