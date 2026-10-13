# การกู้ระบบรันทดลอง v2.3 ด้วย Podman

อัปเดต 5 ตุลาคม 2026. Docker Desktop กลับมาทำงานได้ชั่วคราว แต่ Linux engine ล้มเหลวระหว่างเริ่ม container และตอบ HTTP 500 จึงเปลี่ยน backend ของ evaluator เป็น Podman 3.4.4 ใน Ubuntu WSL แทน ไม่ได้ย้ายโค้ดที่ LLM เขียนไป execute บน Windows หรือ Ubuntu host

## สิ่งที่คงเดิมและสิ่งที่เปลี่ยน

- ใช้ Python base digest และแพ็กเกจที่ pin ไว้เดิม: Python 3.12.8, NumPy 1.26.4, pandas 2.3.3, scikit-learn 1.7.1 และ joblib 1.5.1
- Image ID ใหม่เป็น `sha256:d1dd86e9ef7bb249f3468e90214f3ceb3a9e8ff1ed84b0b7e1926458f423a37e` ไม่อ้างว่าเป็น image byte-identical กับ Docker เดิม
- Candidate อยู่ใน container แบบ UID 65534, network none, root filesystem read-only, capabilities ถูกถอดทั้งหมด, no-new-privileges, 2 CPUs, memory 4 GiB และจำกัดจำนวน process พร้อม bounded tmpfs
- Podman runtime เป็น rootful เช่นเดียวกับ Docker engine เดิม แต่ process ที่รัน candidate ไม่ได้ใช้ root; กลไกนี้ไม่ใช่การรับรองว่า container ปลอดภัยจากช่องโหว่ทุกชนิด
- Working directory ภายใน Podman เปลี่ยนจาก `/work` เป็น `/tmp` เพราะ Buildah รุ่นนี้ไม่สร้าง `/work` แม้มี WORKDIR metadata; input/source/predecessor mounts ยังคง read-only
- Trusted host validator ใช้ Python 3.10 และ NumPy ของ Ubuntu อ่าน CSV และคำนวณ AUC/MAE เท่านั้น ไม่ import candidate และไม่โหลด candidate joblib บน host เวอร์ชัน host ถูกบันทึกแยกจาก runtime ของ candidate

## หลักฐานที่ทวนสอบแล้ว

`verify_podman_evaluator.py --label podmanr02` ผ่าน trusted reference ทั้ง 8 case variants (Adult 4, Beijing 4) โดยทุกเคสผ่าน 4 DAG stages และ hidden quality validator รวม 32 stage executions; **ไม่มี LLM call** ในการตรวจนี้

Lock อยู่ใน `ml_eval_image_lock_podman_v1.json` และมี SHA-256 `5f592a1d33f8a791940b67f31bbb4bad50f7bd8ddb013dbcd74f6572e5f4027b`. บันทึก build/package check/attempt ที่ล้มเหลวยังคงอยู่ใน `runtime_podman_v1` ไม่ได้ทับหรือลบทิ้ง

โค้ด ingest ของ Tencent จาก ADULT_P3 และ BEIJING_P3 ที่เคยเจอ Docker exit 125 ถูก replay โดย **ไม่เรียก provider ใหม่** และผ่านทั้งสองเคส หลักฐานอยู่ใน `candidate_workspaces/*_environment_replay_r01/replay_summary.json`. นี่เป็นการตรวจ ingest เท่านั้น ไม่ใช่ full-job success และไม่เปลี่ยนบันทึกผลเดิม

## ขอบเขตของการตีความ

การผ่าน reference แสดงว่า harness ทำงานใน backend ใหม่ได้ ไม่ใช่ผลของ LLM. การเปลี่ยน backend ต้องเปิดเผยในวิธีการและ deviation log; อย่าเปรียบเทียบ container wall time ข้าม backend เป็นผลของ allocation policy. การทดลอง main ในอนาคตต้องใช้ backend และ resource limits เดียวกันทุก arm

Credential สำหรับ MFEC ถูกส่งจาก process environment ผ่าน stdin ให้ trusted bridge ไม่อยู่ใน argv/file. Bridge ไม่ส่ง credential เข้า candidate container. Script ไม่บันทึกหรือพิมพ์คีย์
