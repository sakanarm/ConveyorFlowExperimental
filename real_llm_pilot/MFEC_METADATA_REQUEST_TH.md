# ข้อมูลที่ต้องขอจาก MFEC ก่อนรัน Main Real-LLM

ขอข้อมูลสำหรับ deployment aliases ต่อไปนี้ ณ ช่วงเวลาที่จะเก็บข้อมูล:

- `tencent-hy3`
- `gpt-5-mini`
- `glm-5.3-flash`

สำหรับแต่ละ alias ขอรายการต่อไปนี้:

1. ชื่อผู้ให้บริการและ immutable underlying model/version หรือ deployment ID
2. วันที่และเวลาที่ mapping เริ่มและสิ้นสุดการใช้งาน
3. ราคา input และ output ต่อหนึ่งล้าน tokens ที่บัญชีนี้ถูกคิดจริง
4. สกุลเงิน ภาษี/ส่วนเพิ่ม และเงื่อนไข cache หรือ reasoning tokens
5. วิธีตรวจจับการเปลี่ยน deployment ระหว่างการทดลอง เช่น response header,
   model ID หรือ endpoint สำหรับตรวจ metadata

เหตุผล: งานวิจัยต้องตรึง experimental treatment และคำนวณ cost per verified
task จากราคาที่เกิดขึ้นจริง ห้ามแทนค่าด้วยราคาสาธารณะของ model family หาก MFEC
มี routing หรือ markup ต่างออกไป

หากระบบไม่เปิด metadata endpoint สามารถส่งเอกสารรับรองหรือข้อความจากผู้ดูแลระบบ
ที่ระบุ alias mapping, effective date และราคาได้ โดยจะเก็บ hash ของหลักฐานไว้ใน
execution manifest และไม่เผยแพร่ข้อมูลลับของระบบ

## คำสั่งตรวจ endpoint แบบไม่บันทึก API key

```powershell
python v2/real_llm_pilot/probe_mfec_metadata.py
```

สคริปต์รับ key แบบ hidden input และเขียนเฉพาะ allowlisted metadata fields ไม่เขียน
credential, raw response หรือ internal API base ลงไฟล์
