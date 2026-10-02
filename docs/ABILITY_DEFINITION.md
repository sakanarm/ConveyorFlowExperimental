# Ability Level Definition

Ability วัดแยกตาม workload family เป็น `A[i,w]` ไม่ใช้ชื่อรุ่น ราคา ความเร็ว หรือ token consumption เป็นตัวแทน

| Level | Latent theta | Behavioral envelope |
|---|---:|---|
| L1 Basic | -1 | reliable mainly on D1 |
| L2 Intermediate | 0 | reliable on D1-D2 |
| L3 Advanced | +1 | retains useful success probability on D3 |

Simulation หลัง Pilot calibration รอบแรกใช้ monotonic logistic curve
`logit(P(pass)) = alpha_w + 0.85*theta - 1.2*(difficulty-2)` โดย
`alpha_adult=0.88`, `alpha_beijing=0.86` และ `alpha_bugs2fix=0.86`
ค่าชุดนี้ถูกเลือกก่อน validation pilot รอบสุดท้ายเพื่อแก้ ceiling effect ของ L3-D1
โดยไม่ใช้ผลเปรียบเทียบระหว่าง allocation policies เป็นเกณฑ์ปรับค่า

Real-LLM phase ต้องใช้ held-out capability probe และ assign level จาก lower bound ของ 95% confidence interval หากไม่ผ่าน L1 ให้เป็น L0/Unqualified

Assessment bias/noise, price, speed และ token factor เป็นคนละตัวแปรกับ Ability
