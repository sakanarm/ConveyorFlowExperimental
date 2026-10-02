# Pilot Experimental Matrix

Calibration รอบแรกใช้ seeds 0-19 ส่วน validation หลังปรับ curve ใช้ seeds 20-39
ทั้งสองชุดไม่รวมใน confirmatory analysis ตารางด้านล่างเป็น validation matrix รอบสุดท้าย

## RQ1 calibration cells

- strategies CF-Fit, S1, S2, S3, Central-Fit
- team H1
- workloads Adult ML, Beijing ML, Bugs2Fix
- loads low, medium, high
- resource regimes R0, R1

รวม 1,800 runs

## RQ2 calibration cells

- strategy CF-Fit
- teams H0, H1, H2
- workloads 3 ชุด
- loads 3 ระดับ
- resource regime R0
- ตัด H1 cells ที่ซ้ำกับ RQ1

เพิ่ม 360 runs รวม Pilot 2,160 runs

หนึ่ง ML run มี 200 jobs หรือ 1,400 offered tasks หนึ่ง Fix Bug runมี 200 jobsหรือ 1,000 offered tasks
