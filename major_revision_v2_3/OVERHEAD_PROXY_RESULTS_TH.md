# v2.3: ผลวัด overhead ของเส้นทาง claim แบบต้นแบบ

วันที่ 4 ตุลาคม 2026. การวัดนี้ตอบคำถามแคบ ๆ ว่า **ถ้า proposal และ claim store เหมือนกัน แต่เส้นทาง Central-Matched ต้องผ่าน relay/coordinator เพิ่มหนึ่ง process จะมีเวลารอเพิ่มเท่าไรบนเครื่องเดียว** ไม่ได้วัด MFEC API, ระยะเวลาที่ LLM คิด/สร้างโค้ด, network ข้ามเครื่อง หรือความล้มเหลวของ coordinator จริง จึงยังไม่ใช่ G3 ทั้งหมด และยังไม่ใช้เป็น empirical distribution ของ E1 ในผลหลัก

## วิธีวัดที่ล็อกก่อนรัน

`config_overhead_proxy_v1.json` ล็อก seed 20261004, warm-up 100 คู่ และคู่หลัก 1,000 คู่ ก่อนเก็บผล. ภายในแต่ละคู่สลับลำดับ local/central ด้วย seed ที่กำหนด แล้ววัดตั้งแต่ส่ง request จนได้รับผลด้วย monotonic clock. ทั้งสองทางใช้ payload และ claim-store process เดียวกัน. Local ส่งถึง store โดยตรง; central ส่งผ่าน coordinator relay ที่ไม่มีสิทธิ re-rank หรือเปลี่ยน candidate ก่อนถึง store. ใช้ request ID ใหม่ทุกครั้งเพื่อไม่ให้การชนกันของ claim กลายเป็นตัวแปรแทรก. วัดแบบ serial บน Windows host เดียว เพื่อแยกต้นทุน relay ขั้นต่ำ; ไม่มี parallel load หรือ provider calls.

ผลดิบคู่ต่อคู่และ manifest อยู่ใน `results/overhead_proxy_v1/main/`. Manifest ล็อก SHA-256 ของ config, runner และ CSV. `verify_overhead_proxy_v1.py` ตรวจ hash, จำนวนคู่ และคำนวณสรุปใหม่โดยไม่แก้ผล. คำสั่งตรวจซ้ำ:

```powershell
& 'v2/REPRODUCE_V2_3.ps1' -Stage OverheadVerify
```

## ผล

| Metric | Local claim | Coordinator relay |
|---|---:|---:|
| Median round-trip | 0.10570 ms | 0.20875 ms |
| P95 round-trip | 0.15445 ms | 0.30832 ms |

Paired mean ของ `central − local` = **0.11037 ms**; paired bootstrap 95% CI **[0.10825, 0.11238] ms** จาก 2,000 bootstrap resamples; 1/1,000 คู่มีผลต่างติดลบ. CI นี้บอกความไม่แน่นอนในการสุ่มคู่ของ **ต้นแบบนี้เท่านั้น** ไม่ครอบคลุมเครื่องอื่น, concurrent load, network, provider tail latency หรือ outage.

## Load sensitivity บนเครื่องเดียว

การทดลองแยก `config_overhead_load_v1.json` ถูกล็อกก่อนรัน: client พร้อมกัน 1, 2, 4, 8 ตัว; ระดับละ 3 คู่ session; 20 warm-up และ 200 requests ต่อ client ต่อ session. ในแต่ละคู่สุ่มลำดับ local/central ด้วย seed เดิม, เปิด process ใหม่ให้แต่ละ session, ใช้ claim store เดียวต่อ session และให้ client มี outstanding request ได้หนึ่งรายการ. Central มี relay process เดียวซึ่งส่งต่อแบบ serial; local ส่งตรง. ทั้งหมด **24 sessions / 18,000 measured requests**. ผลดิบและ hash อยู่ที่ `results/overhead_load_v1/main/`; `verify_overhead_load_v1.py` ตรวจซ้ำผ่าน.

| Concurrent clients | Local median of session medians | Central median of session medians | Median paired session difference |
|---:|---:|---:|---:|
| 1 | 0.08050 ms | 0.17605 ms | 0.09555 ms |
| 2 | 0.11745 ms | 0.27775 ms | 0.15295 ms |
| 4 | 0.27400 ms | 0.58210 ms | 0.35625 ms |
| 8 | 0.46165 ms | 1.17550 ms | 0.71385 ms |

ค่าเพิ่มโตตามจำนวน client ใน **implementation ของ relay แบบ serial นี้**. มีเพียง 3 session pairs ต่อระดับ จึงรายงาน descriptive ไม่ตีความเป็น CI ทั่วไปหรือเป็นผลของทุก centralized scheduler. การวัดนี้ยังไม่แยก queue wait จาก service time และไม่มี network/provider latency. ตรวจซ้ำด้วย `-Stage OverheadLoadVerify`.

## ขอบเขตการอ้างและงานต่อ

ผลแสดงว่า relay เพิ่มหนึ่ง hopมีค่าใช้จ่ายที่วัดได้ใน implementation นี้ แต่ **ไม่พิสูจน์ว่า CF-Fit ทำงานเร็วกว่า Central-Matched ในระบบ Real-LLM**; เวลาระดับเศษเสี้ยวมิลลิวินาทีเล็กมากเมื่อเทียบกับงาน LLM. แม้วัด concurrent clients แล้ว ก็ยังเป็น single-host, one-outstanding-request, serial-relay proxy. ก่อนเปิด E1 ตาม preregistration ต้องแยก queue/claim/relay time, lock distribution ก่อนรัน simulation และทำ sensitivity ต่อ hardware/network หรือแสดงชัดว่าเป็น local-only scenario. การทดสอบ coordinator, shared-belt และ agent outage ต้องแยก fault domains; ผล E2 ที่มีอยู่ยังเป็น synthetic stress test. หากไม่ทำครบ ให้รายงานผล proxy นี้เฉพาะ feasibility/limitations ไม่ยกระดับเป็น main architecture effect.
