# v2.3 ML DAG feasibility: ประวัติ prompt และผลลบ

เอกสารนี้ใช้กับ pilot เพื่อทดสอบความพร้อมของ harness เท่านั้น; ไม่มีผลใน manuscript v2.2, simulation หลัก หรือ real-LLM policy comparison. ห้ามนับผลหลาย prompt revision เป็นการทดลอง confirmatory ชุดเดียว

| Revision / case | สิ่งที่เกิดขึ้น | การตัดสินใจ |
|---|---|---|
| initial prompt / ADULT_P0 / `gpt-5-mini` | 2 MFEC calls; ingest verified, preprocess failed (`pd.NA` in sklearn `SimpleImputer`); job DEAD_LETTER | เก็บ source, response, validator report และค่าใช้จ่ายเดิม ไม่ซ่อมคำตอบโมเดลย้อนหลัง |
| initial prompt / BEIJING_P0 / `gpt-5-mini` | 2 MFEC calls; ingest verified, preprocess failedด้วย `pd.NA`/`SimpleImputer`; job DEAD_LETTER | เก็บเป็น negative feasibility result แยกจาก Adult; ไม่อนุมานอัตราสำเร็จจากสองเคส |
| `v2_missing_values_20261004` / case ใหม่เท่านั้น | เพิ่ม contract ทั่วไปให้จัดการ pandas nullable dtypes/missing values ให้ใช้กับ sklearn และ inference ใน environment ที่ pin ไว้ | เปลี่ยน prompt ระหว่าง feasibility เพื่อแก้ความกำกวมของ interface; prompt SHA-256 และ revision จะอยู่ใน ledger. ไม่ใช้เคส P0 ใหม่เพื่อหลีกเลี่ยงการทับหรือเลือกผล |

อีกการแก้ harness ก่อนรันเคสใหม่: `run_ml_dag_llm_feasibility.py` ตรวจ Docker daemon และ immutable image ID **ก่อน** billable provider call; หากไม่พร้อมต้องหยุดโดยไม่มี MFEC call. ไม่มีการเปลี่ยน validator หรือ image. ก่อน main ต้อง freeze prompt revision, case manifest, retry rule และทุก setting แล้วใช้ main cases ที่ไม่ปะปนกับ pilot

วันที่ 4 ตุลาคม 2026 `ADULT_P1` ถูก materialize/dry-run ด้วย prompt revision ใหม่ แต่การ execute หยุดที่ Docker preflight (`Internal Server Error`/daemon unavailable) ก่อน provider call. ไม่มี `dag_prompt_*`, `dag_response_*` หรือ `dag_summary.json` ของ P1 จึงไม่ใช่ model attempt. หลังผู้ใช้อนุญาตให้กระทบ Docker containers อื่นได้ มีการ graceful shutdown/เปิด Docker Desktop ใหม่และหยุด Docker Desktop/backend process ที่ค้าง; engine ยังตอบ 500. ไม่มีการลบ image, volume, container หรือแก้ ledger เดิม. การ restart WSL ทั้งระบบต้องแยกการอนุมัติเพราะอาจกระทบ Ubuntu ด้วย

## อัปเดต 5 ตุลาคม 2026

เปลี่ยนไปใช้ Podman 3.4.4 ใน Ubuntu WSL หลังผู้ใช้อนุญาต runtime recovery. Pin base/packages เดิมแต่ image ID ใหม่และมี lock แยก. Trusted reference ผ่าน 8 variants / 32 stages ก่อน calls. Saved Tencent ingest replay ผ่านทั้ง Adult/Beijing โดยไม่มี API calls ใหม่; ไม่นับเป็น full pipelines

Third prompt revision reuse P0 อย่างเปิดเผย สอง corpus × สาม aliases รวม 6 exploratory jobs ไม่ใช่ independent datasets. ทุก model ใช้ 16,384 completion tokens, temperature 0 และไม่เกินสอง attempts/stage; validator เดิม. จบ 20 provider attempts: VERIFIED 1, DEAD_LETTER 3, unresolved 2. Tencent Adult ผ่านครบ 4 stages และ clean replay ได้ prediction/model hashes เดิม. Provider timeout มี unknown billable outcome ดังนั้น reported cost sum เป็น partial ไม่ใช่ total billed cost. ไม่ pool revisions หรือใช้ conditional stage counts เป็น simulation probabilities

Repository recovery เพิ่ม nose==1.3.7 ตาม historical requirements สำหรับ luigi และเปลี่ยน matplotlib เป็น serial build (-j1 แทน -j2) โดยไม่แก้ source/commits/tests. Serial build ทำให้ test contrast ผ่าน แต่ยังไม่พิสูจน์สาเหตุทั่วไปของ build failure. Python3.7 thefuck ติด signed official APT downloads 404 ทั้ง original/HTTPS mirror recovery; เก็บ exclusion ไม่ฝืนใช้ Python3.8

Gate v1 ปฏิเสธ JUnit skipped ทั้งหมด จึง reject pandas #88 ที่มี 8 passes และ 2 historical pytest.xfail บนทั้ง buggy/fixed. Gate v2 แก้ accounting อย่างเปิดเผยก่อน repair-model calls: ไม่เปลี่ยน selected tests/marks, ไม่แทน xfails และไม่นับเป็น passes. เก็บ v1 summary เดิม; audit v2 แยกกัน
