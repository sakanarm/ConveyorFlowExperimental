# Scrapy source eligibility ก่อน Real-LLM

วันที่ 13 ตุลาคม 2026 — ตรวจคิว BugsInPy/Scrapy ที่ตรึง hash order ไว้ก่อนเรียก LLM โดยทดสอบ public `python -m unittest -q` **ทุกคำสั่ง** บน buggy และ fixed validator แยกกันภายใน Podman. ขั้นนี้ใช้ provider calls = 0 และยังไม่ใช่ผลซ่อมบั๊กของ AI

## เหตุผลที่มีสอง environment profile

`scrapy_public_preflight_v1` ใช้ Python 3.8.20 และ core dependency pins จาก public requirements แทน Python 3.8.3/full requirements ที่มีแพ็กเกจ Windows-only. Image build สำเร็จ แต่เคสแรก `scrapy_39` import public test ไม่ได้ทั้ง buggy/fixed เพราะขาด `testfixtures`. ผล v1 ถูกเก็บเป็น `environment_excluded` ไม่ลบหรือเปลี่ยนย้อนหลัง

ก่อนมี Scrapy LLM call ใด ๆ ได้ตรึง `scrapy_public_preflight_v1b` ซึ่งเพิ่ม `testfixtures==6.14.1` ตาม public requirements โดยไม่เปลี่ยนคิว/คำสั่งทดสอบหรือผ่อนเกณฑ์ผ่าน. Lock SHA-256 ของ v1b คือ `a1a16443d02e8d8b5c7464d899b96e771525f3dd531cd56023f15558c4fb4a80`. การเบี่ยงจาก full requirements บันทึกไว้ใน config และ record ของแต่ละเคส; จึงเป็น environment amendment ก่อน outcome ของ LLM ไม่ใช่การคัดเคสตามความสามารถโมเดล

| คิว | เคส | Public commands | Buggy | Fixed | ผล |
|---:|---|---:|---:|---:|---|
| 0 | `scrapy_39` | 1 | 1/1 ล้มตามบั๊ก | 1/1 ผ่าน | reproducible |
| 1 | `scrapy_34` | 3 | 3/3 ล้มตามบั๊ก | 3/3 ผ่าน | reproducible |

`audit_scrapy_public_preflight_v1b.py` ตรวจ SHA-256 ของ lock, config, queue, Dockerfile, build report, execution record และ record ต่อเคส รวมทั้งตรวจ transcript รายคำสั่งว่าไม่ใช่ import error หรือ missing module; ผ่านด้วยสถานะ `TWO_INDEPENDENTLY_AUDITED_PUBLIC_CONTRASTS`. Raw evidence อยู่ที่ `D:\ConveyorFlowRuntime\v2_6\scrapy_public_preflight_v1` และ `...\scrapy_public_preflight_v1b`. ไฟล์ lock/config/ledger/code อยู่ใน Git workspace ที่ `v2/major_revision_v2_6/`

ข้อจำกัด: สองเคสนี้เพิ่มได้เพียงหนึ่ง repository project (`scrapy`); ยังไม่เติมเป้าหมาย 12 distinct repositories/6 ML corpora ของ prospective v2.6 main protocol และยังไม่พิสูจน์ว่า LLM ซ่อมสำเร็จ. ขั้นต่อไปต้อง freeze prompt/allowed-edit scope จาก buggy trace และ public API โดยไม่ดู gold fix, ตั้ง output cap และ verifier ให้เหมือนกันทุก arm, แล้วรัน clean first attempts. ห้ามนับ preflight เป็น API sample หรือสรุปว่า Major Revision ปิดแล้ว
