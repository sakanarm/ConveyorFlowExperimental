# v2.7: Scrapy live repair extension ที่ตรึงก่อนเรียก MFEC

วันที่ 13 ตุลาคม 2026. งานนี้เป็น **bounded repository-repair extension** เพื่อทดสอบเส้นทางงานจริงบน repository ใหม่จาก FastAPI และความคงเส้นคงวาของ CF-Fit / Central-Rule-Matched / Static-Owners ภายใต้เครื่องมือเดียวกัน ไม่ใช่ main mixed ML + repair cohort ของ v2.6 และไม่ใช่หลักฐาน generalization ข้าม 12 repository projects.

## เหตุผลที่เลือกและ gate ก่อนเสียค่า API

คิว `scrapy_39`, `scrapy_34` มาจาก hash order ของ BugsInPy/Scrapy ที่ตรึงใน v2.6 โดยไม่ดูผล LLM. Public source preflight v1b ใช้ Python 3.8.20/Linux พร้อม dependency pins ที่เปิดเผยไว้: buggy fail/fixed pass ทั้ง 1 และ 3 public commands ตามลำดับ. v1 ที่ขาด `testfixtures` ถูกเก็บเป็น environment exclusion; v1b เพิ่ม public pin ก่อน LLM call ใด ๆ. ใน v2.7 candidate gate เก็บ prompt เฉพาะ source จาก `/buggy` (`scrapy/spiders/__init__.py` หรือ `scrapy/item.py`) และ public failure trace; fixed tree ไม่อยู่ใน prompt. คัด 5 public regression nodes ต่อเคสจาก module เดียวกันด้วย hash order และต้องผ่านทั้ง buggy/fixed ก่อน provider. Candidate lock SHA-256 `1b3737a9d8045d7ade3047fb986c9ca0a5cd675b8ff6fdd0419073f2633c887d`; provider calls ณ gate = 0.

Smoke verifier ใช้ patch ที่เพิ่ม comment ซึ่ง **ไม่ได้แก้บั๊ก**: apply ใน Podman สำเร็จแต่ visible test ยังคง fail ตามเดิม. นี่ตรวจว่า verifier รันบน buggy checkout และ mount patch ได้; ไม่ใช่ LLM outcome. การแก้ image-ID format จาก `sha256:<hex>` เทียบ `<hex>` ก่อน candidate gate เสร็จทำเป็น v1b และเก็บ partial directory ของ v1 ไว้ ไม่ overwrite ผลใด.

## การเปรียบเทียบที่ freeze

- งานแต่ละเคสขึ้น shared READY belt หนึ่ง task; agents A1/A2/A3 (≤3 โมเดล) มี Ability Rank ด้าน repair จาก profile เดิม. Task required rank 2, ไม่ปรับตามผลหรือ gold fix. CF-Fit ให้อิสระแต่ละ agent assess/volunteer/stand down, Central-Rule-Matched ใช้ fit/stand-down กติกาเดียวกันแต่ตัดสินใจใน coordinator process, Static-Owners กำหนด A1 เป็นเจ้าของก่อนรัน. CAS/claim store, verifier, seed และ horizon เหมือนกันในแต่ละเคส.
- ลำดับ `scrapy_39`: CF-Fit → Central → Static; `scrapy_34`: Central → Static → CF-Fit. ลำดับนี้ตรึงก่อน provider ไม่เลือกจากผล. คำถามหลักคือผล operational ของ policy bundles ในสองเคส ไม่อ้าง causal effect บริสุทธิ์ของ decentralization จาก LLM latency.
- ทั้ง 6 arms ใช้ prompt ที่ hash ตรึง, model/version mapping, `temperature=0`, `max_output_tokens=32768`, timeout 720 s และ verifier เดียวกัน. เพดาน output เลือกหลัง instrument pilot บน FastAPI **ที่เคยเปิดเผย** แต่ก่อน Scrapy call; ผล FastAPI pilot ไม่ถูก pool หรือเรียก first attempt. หนึ่ง provider request ต่อ arm, ไม่มี automatic retry เมื่อ request marker ถูกเขียนแล้ว.
- Patch ต้องเป็น exact-edit JSON แก้เฉพาะ production file ที่อนุญาต. Verified เฉพาะเมื่อ visible, regression, replay visible และ replay regression ผ่านทั้งหมดบน isolated Podman. Unfinished, malformed, test-failed และ unresolved ต้องคงใน denominator และแสดงแยก.
- รายงาน verified jobs, completion/terminal time, busy utilization, input/output tokens และจำนวน unknown cost. Provider `response_cost` เป็น units ที่ยังไม่ตรวจสกุลเงิน/ใบแจ้งหนี้; ห้ามเรียกเป็นเงินหรือคำนวณ cost per verified job จริง. สองบั๊กใน **Scrapy repository เดียว** เป็น nested observations; 6 calls ไม่ใช่ n=6 อิสระ. ไม่ใช้ p-value/CI แบบ population หรือคำว่า equivalent/superior.

Live lock SHA-256 `cf25faa1f16a466e992b93b8ab6ba96a9e3de10b231c4961d492b373747a58b7`. Raw evidence บน `D:\ConveyorFlowRuntime\v2_7`, code/locks ใน `v2/major_revision_v2_7`; `REPRODUCE_V27.ps1` มีคำสั่ง audit, freeze และ resume แบบไม่ยิงซ้ำ arm ที่จบ. ต้องรัน `audit_scrapy_live_pair_v1.py --seal` หลังครบทุก arm ก่อนนำตัวเลขไป manuscript.

## สิ่งที่ยังไม่ปิด

v2.7 รอบนี้ไม่มี full ML DAG และมี project ใหม่เพียงหนึ่งแห่ง; จึงไม่แทน protocol v2.6 ที่ตั้งเป้า 12 distinct repositories × 2 bugs และ 6 public ML corpora. Controlled decision-layer fault evidence เดิมจำกัดที่ stream/fixture ที่ทดสอบ ไม่พิสูจน์ reliability ทั้งระบบ. แม้ 6 arms ผ่านทั้งหมดก็เป็น bounded feasibility เท่านั้น. หาก eligibility source frame ไม่ถึงเป้า ต้องเขียน limitation ตรง ๆ ไม่เติม API calls ใน repo เดิมเพื่อทำให้ N ดูมากขึ้น. ต้นฉบับ IEEE/AJSTR จะอัปเดตผลนี้แยก cohort หลัง independent audit และยังต้องตรวจ layout ใน Microsoft Word ก่อนส่ง.
