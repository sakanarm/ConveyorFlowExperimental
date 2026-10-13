# v2.4 การทดสอบตำแหน่งผู้ตัดสินใจภายใต้ fault แบบควบคุม

สถานะ: รันและตรวจอิสระครบ **160 trials** = 20 paired seeds × 4 fault scenarios × 2 architectures; ไม่เรียก LLM/API เลย (`provider_calls = 0`). แต่ละ trial มีงาน 3 ชิ้นอยู่บน READY belt เดียวกัน ใช้ทีม Ability Rank 1/2/3, กฎ fit/stand-down, SQLite atomic claim, ผล verification แบบ fixture และระยะบริการที่ตรึงเท่ากัน ต่างกันเฉพาะตำแหน่งการตัดสินใจ: agent-local ของ CF-Fit กับ process ผู้ประสานงานของ Central-Rule-Matched. การทดสอบนี้ไม่ใช่ผล throughput, latency หรือ cost ของ real LLM.

| สถานการณ์ | CF-Fit: งานที่ verified ระหว่าง fault | Central-Rule-Matched: งานที่ verified ระหว่าง fault | หลังฟื้นตัว |
|---|---:|---:|---|
| ไม่มี fault | 3/3 | 3/3 | ทั้งสอง 3/3 |
| ฆ่า coordinator process ที่ขอบก่อนตัดสินใจ | 3/3 | 0/3 | ทั้งสอง 3/3 |
| ทำให้ shared belt/claim-store path ใช้ไม่ได้ | 0/3 | 0/3 | ทั้งสอง 3/3 |
| ฆ่า agent A2 | 2/3 | 2/3 | ทั้งสอง 3/3 |

ทุกค่าข้างต้นเกิดซ้ำใน 20 seeds และ audit ตรวจ no-fault proposal/claim parity, PID/exit code ของ process ที่ถูกฆ่า, hash-chain ledger, CAS claim ไม่ซ้ำ, terminal outcome และการกลับมาทำงานหลังคืน process/store. ความต่าง 3 ต่อ 0 ใน coordinator-only outage จึงรองรับข้ออ้างจำกัดว่า **CF-Fit ไม่ต้องพึ่ง process ผู้ตัดสินใจส่วนกลางใน fault window นี้**; ไม่รองรับข้ออ้างว่าไม่มี single point of failure ทั้งระบบ เพราะ shared belt/claim store ยังเป็น failure domain ร่วม และไม่ได้ประมาณอัตราเสียของระบบ production. 20 seeds เปลี่ยน tie-breaking jitter บน task stream เดียว ไม่ใช่ตัวอย่างงานอิสระ 20 ชุด จึงไม่ใช้ช่วงความเชื่อมั่นเพื่ออ้าง generalization.

Lock SHA-256: `4ac2ec66c150db40e89d435203bbe21de8615ea3e8e0e9887140919fa9efdb14`. Audited result SHA-256: `cf730048c348126edea76c7c7490c146ebb87e9e5149aa3453f8a78d40a32438`. Raw local evidence lives under `results/decision_fault_v1b/` and is excluded from Git; run `python major_revision_v2_4/audit_decision_fault_v1.py` in the v2 checkout to verify a retained evidence tree. The earlier `decision_fault_v1` lock was stopped before any trial because of a tuple/list serialization comparison bug and is documented separately in `DECISION_FAULT_INSTRUMENT_AMENDMENT_TH.md`.
