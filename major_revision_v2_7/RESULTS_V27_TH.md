# v2.7: ผลการทดลอง Scrapy repair แบบมีขอบเขต

สถานะ ณ 13 ตุลาคม 2026: รัน Real-LLM ครบ 6/6 arms, independent audit seal ผ่าน และ replay patch ที่นับว่า verified ผ่านซ้ำใน Podman. ชุดนี้เป็น **ส่วนขยายเชิงสำรวจ** ไม่ใช่ main mixed ML/repair experiment และไม่ควรนำไปบวกกับจำนวน independent projects ของชุดก่อน

## ทำไมทดลองชุดนี้

การทดลองก่อนหน้าทำ repository repair จริงกับโครงการจำนวนน้อย จึงเลือก public Scrapy repository อีกหนึ่งแห่ง เพื่อทดสอบเส้นทาง READY belt → การตัดสินใจจัดสรร → provider → patch → container verifier บนงานใหม่ ภายใต้ CF-Fit, Central-Rule-Matched และ Static-Owners. คิว `scrapy_39`, `scrapy_34` และลำดับ arm ถูกตรึงก่อนยิง provider; buggy/fixed public test contrast และ regression gate ผ่านก่อนเริ่ม. Prompt เห็น buggy source และ public failure trace เท่านั้น ไม่เห็น fixed source. Task required rank 2 เป็นค่าคงที่เพื่อทดลองการจัดสรร ไม่ใช่ difficulty label จากผู้เชี่ยวชาญ.

ทั้งสาม arm ใช้ task/prompt/validator/model roster/seed/horizon เดียวกันในแต่ละ case. CF-Fit ให้ agent เลือกและ claim งานเอง; Central-Rule-Matched ใช้กติกา fit/stand-down เดียวกันแต่มี coordinator ตัดสิน; Static-Owners กำหนด A1 ล่วงหน้า. มีหนึ่ง provider request ต่อ arm ไม่มีการ retry เพื่อเลือกผลดี. ขีดจำกัด output 32,768 tokens, provider timeout 720 วินาที, observation horizon 1,800 วินาที. จึงเปรียบเทียบโครงสร้างการตัดสินใจได้ในเชิงการทำงาน แต่ผล provider สุ่มและทุก arm เลือก A1 เหมือนกันในสอง case นี้ ทำให้ยังระบุ causal effect ของ decentralization, heterogeneity หรือ stand-down จากผลสำเร็จไม่ได้.

## ผลที่ audit แล้ว

| Arm | Verified / 2 | Throughput ตาม fixed horizon (jobs/h) | Mean restricted completion (s) | Mean busy fraction ของ 3 agents | Input / output tokens |
|---|---:|---:|---:|---:|---:|
| CF-Fit | 1/2 | 1.0 | 973.8 | 3.70% | 3,255 / 46,707 |
| Central-Rule-Matched | 1/2 | 1.0 | 985.3 | 4.05% | 3,255 / 49,730 |
| Static-Owners | 1/2 | 1.0 | 971.6 | 3.63% | 3,255 / 45,175 |

`scrapy_39` ผ่าน visible test 1 และ regression tests 5 ทั้งสาม arm รวมทั้ง independent replay. เวลาจาก READY ถึง verified: CF-Fit 147.5 s, Central 170.6 s, Static 143.1 s. `scrapy_34` ไม่ผ่านทั้งสาม arm: CF-Fit และ Central คืนคำตอบไม่สมบูรณ์/ว่างหลังชน output cap; Static ส่ง patch ที่ไม่ผ่าน test/replay. ทุกความล้มเหลวยังคงอยู่ใน denominator และกำหนด restricted time = 1,800 s; conditional completion time ของความล้มเหลวเป็น missing ไม่ใช่ศูนย์.

Throughput ใช้จำนวนงาน verified หาร observation horizon รวมสอง case-arm (2 × 1,800 s). Busy fraction ใช้เวลาทำงานจริงหารด้วย 3 agents × 1,800 s ต่อ case-arm โดยรวมเวลาว่างหลังจบงานไว้ใน denominator. ตัวเลขนี้จึง **ไม่ใช่** throughput หรือ utilization ของการติดตั้งระบบต่อเนื่องขนาดใหญ่. Output tokens เป็นการใช้ทรัพยากรที่วัดได้; `response_cost` ที่ provider ส่งกลับยังไม่ยืนยันหน่วยเงินหรือ reconcile กับใบแจ้งหนี้ จึงยังไม่มี billed cost per verified job.

สามารถแสดง **ประมาณการจาก gateway** แยกต่างหากได้: ผลรวม `response_cost` ของสอง requests ต่อ arm คือ CF-Fit 0.024945, Central-Rule-Matched 0.026529 และ Static-Owners 0.023978 *gateway-reported units*. ทุก arm verified หนึ่งงาน จึงมีหน่วย proxy ต่อ verified repair เท่ากับผลรวมนั้น แต่ตัวเลขนี้รวมค่า attempt ที่ล้มเหลวด้วย. [LiteLLM อธิบาย](https://docs.litellm.ai/docs/proxy/cost_tracking) ว่า proxy คำนวณ response cost และบันทึก spend logs; อย่างไรก็ตาม endpoint MFEC ไม่เปิดเผยราคา/สกุลเงินของ alias `tencent-hy3` ผ่าน metadata ที่ key นี้เข้าถึงได้ และยังไม่มี invoice มาตรวจเทียบ. ดังนั้นห้ามเปลี่ยนหน่วย proxy นี้เป็น USD หรือบาทโดยอัตโนมัติ. ราคามาตรฐานของ `gpt-5-mini` บนเว็บผู้ผลิตก็ใช้แทนไม่ได้ เพราะทั้ง 6 requests ของ v2.7 ใช้ `tencent-hy3` ผ่าน MFEC gateway.

## ขอบเขตคำกล่าวสำหรับ manuscript และ reviewer

ผลนี้แสดงว่าเส้นทาง end-to-end ทำงานได้และบันทึก failure อย่างตรงไปตรงมา แต่ **ไม่แสดงว่า CF-Fit เหนือกว่า**, ไม่แสดงความเทียบเท่าทางสถิติ, ไม่ยืนยัน fault tolerance ทั้งระบบ และยังไม่ปิด Major Revision ทั้งหมด. สองบั๊กมาจาก Scrapy **repository เดียว**; 6 provider calls ไม่ใช่ 6 ตัวอย่างอิสระ. จึงไม่มี p-value หรือ population CI จากชุดนี้. ไม่มี ML pipeline ใหม่ใน v2.7. ผลของ policy bundles ต้องรายงานเป็น trade-off และแยกจาก main/earlier executable cohorts.

## หลักฐานและการทำซ้ำ

- Frozen candidate: `scrapy_pair_v1b/candidate_lock.json` SHA-256 `1b3737a9d8045d7ade3047fb986c9ca0a5cd675b8ff6fdd0419073f2633c887d`.
- Frozen live lock: `scrapy_live_pair_v1/lock.json` SHA-256 `cf25faa1f16a466e992b93b8ab6ba96a9e3de10b231c4961d492b373747a58b7`.
- Independent sealed audit: `scrapy_live_pair_v1/audit_capsule_v1.json`; descriptive derivation: `scrapy_live_pair_v1/analysis_v1.json`.
- Commands: `REPRODUCE_V27.ps1` (freeze, smoke, audit, run remaining), `audit_scrapy_live_pair_v1.py --seal`, `analyze_scrapy_live_pair_v1.py`. ห้าม `--seal` ซ้ำเมื่อ capsule มีอยู่แล้ว และห้ามลบ request marker แล้วยิงซ้ำ.
- Raw response, patch, verifier reports และ ledgers อยู่ที่ `D:\ConveyorFlowRuntime\v2_7\scrapy_live_pair_v1`; Git เก็บเฉพาะโค้ด, locks, capsule, analysis และคำอธิบายที่ไม่เปิดเผย API key. Aborted partial v1 ก่อน provider ยังเก็บไว้เพื่อ audit provenance.

ขั้นต่อไปสำหรับการตอบ reviewer แบบเต็มคือ main preregistered cohort ที่มีหลาย **independent repository projects** และหลาย **public ML corpora**, paired blocks ตาม project/corpus, rank contrast ที่ประเมินล่วงหน้า, และค่าเงินจริงที่ตรวจใบแจ้งหนี้ได้. การเพิ่ม calls ใน Scrapy เดิมอย่างเดียวไม่เพิ่มจำนวน independent projects และไม่แก้ปัญหา generalizability.
