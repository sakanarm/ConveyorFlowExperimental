# ConveyorFlow v2 Research Protocol

## Scope

Phase แรกทดสอบ Simulation เท่านั้น งานประกอบด้วย ML Build และ Fix Bug ซึ่งถูกแตกเป็น DAG แล้วปล่อย task ที่ dependency ครบเข้าสู่ READY belt Agent ว่างประเมินงานจากข้อมูลที่ตนมองเห็น อาสา และ claim ด้วย atomic compare-and-swap

## Scientific claims

- RQ1 วัดผลของ decentralized self-selection ต่อ cost per verified task, verified throughput, terminal flow time และ utilization เมื่อเทียบกับ static allocation
- RQ2 วัดผลของ capability heterogeneity โดยคุม mean latent ability และ team size
- RQ3 วัด contribution ของ self-assessment, fit, stand-down และ aging ด้วย ablation

## Experimental unit

หนึ่ง run/seed ภายใน workload-load-team-resource cell เป็นหน่วยวิเคราะห์ Task ภายใน run ไม่ใช่ independent replicates ทุก paired strategy ใช้ Job stream, arrival schedule และ keyed potential outcomes เดียวกัน

## Evidence boundary

ผล Phase นี้เป็น simulation evidence ไม่ใช่ผลของ Model หรือ vendor จริง CodeXGLUE/Bugs2Fix ใช้สร้าง workload distribution ไม่ใช่ executable bug benchmark

## Execution authorization

เอกสารชุดนี้อนุญาตให้พัฒนา engine, tests และรัน Pilot 20 paired seeds ห้ามรัน Main E1–E4 จนกว่า pilot, power analysis, LLM-annotation gate และ preregistration จะได้รับการตรวจอีกครั้ง
