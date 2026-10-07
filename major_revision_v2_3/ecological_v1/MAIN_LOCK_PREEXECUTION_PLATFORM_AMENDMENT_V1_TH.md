# บันทึกแก้ไขล็อกก่อนเริ่ม main experiment

ไฟล์ `main_allocation_execution_lock_v1_preexecution_platform_failed.json` เป็นล็อกครั้งแรก
(SHA-256 `0f372fac008dd194626a43fc206ae2d755214dc8733018df2c30f700eb4e1b57`)
ซึ่งสร้างบน Windows วันที่ 7 ตุลาคม 2026 ก่อนมีการเรียก provider สำหรับ main experiment
ตัวตรวจบน Linux ปฏิเสธล็อก เพราะ `runtime_root` ใช้ backslash ตามพฤติกรรม
`pathlib.Path` บน Windows แทนค่าคงที่ `/mnt/d/...` ของ Linux

เก็บไฟล์เดิมไว้เพื่อให้ตรวจสอบความผิดพลาดได้ แล้วแก้เฉพาะการ serialise
`runtime_root` ให้เป็นค่าข้อความ POSIX คงที่ พร้อมให้ runner ตรวจค่าเดียวกัน
จากนั้นสร้างล็อก canonical `main_allocation_execution_lock_v1.json` ใหม่
ก่อนเริ่มบล็อกแรก ไม่มีการเปลี่ยน case, model, policy, arm order,
parameter, metric หรือผลทดลองย้อนหลัง และไม่มี main provider call
ภายใต้ล็อกฉบับที่ไม่ผ่านนี้
