# Role-Conditioned LLM Annotation Packet

- legacy merged-template filename: `expert_label_packet.csv`
- items: 304
- public-corpus variants: 48 (16 per workload)
- protocol: `../docs/EXPERT_LABEL_PROTOCOL.md`
- claim boundary: `../docs/LLM_ANNOTATION_CLAIM.md`

ใช้ blinded packets สามไฟล์สำหรับ ML Methodologist, Software Reliability Reviewer
และ Workflow/Resource Reviewer ใน isolated context ห้ามให้ pass ใดเห็น label ของ pass อื่น,
provisional difficulty หรือ simulation outcomes ทั้งสาม pass มาจาก model เดียวกัน
จึงห้ามอ้างว่าเป็น independent experts

หลังกรอกครบให้รัน:

`python scripts/merge_expert_labels.py`

`python scripts/analyze_expert_labels.py`

ห้ามเปลี่ยนสถานะ Main เป็น FROZEN จนกว่า agreement gate, adjudication,
alternate-mapping sensitivity plan และ frozen hash จะครบ
