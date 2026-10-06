# การเดินหน้าคู่ ML ที่ยังไม่เริ่มหลังตรวจ backend

วันที่ 6 ตุลาคม 2026 ผู้วิจัยอนุญาตงบเท่าที่จำเป็น รอบเดิมมี 288 first-attempt pairs ไม่ใช่การเรียกซ้ำจนผ่าน

Continuation 1 จบที่ 22 คู่: VERIFIED 16, STAGE_CONTRACT_FAILED 2, PROVIDER_UNRESOLVED 3 และ REPLAY_UNRESOLVED 1 คู่ คู่ Tencent / CAL_BEIJING_01 / train ผ่านครั้งแรก แต่ fresh replay เกิน 360 วินาที มี artifact hash ตรงกันและยืนยันการเก็บ container แล้ว ข้อมูลนี้ไม่พิสูจน์สาเหตุ และไม่เพียงพอเปลี่ยนผลเป็น VERIFIED

ก่อน continuation 2 ใช้ trusted train ของ specification เดิมตรวจระบบใน container ใหม่ โดยใช้ image, input, verifier, hidden labels และเพดาน 360 วินาทีเดิม หากไม่ผ่าน ห้ามเรียก LLM เพิ่ม การตรวจนี้ไม่ใช่ผลของ LLM และไม่รวมใน calibration

การเปลี่ยนแปลงเฉพาะกติกาหยุด batch: timeout ของงานที่ถูกเก็บ container ครบไม่จำเป็นต้องเป็นความเสียหายทั้ง backend เก็บผลคู่เดิมเป็น unresolved ไม่เรียกคู่เดิมซ้ำ แล้วตรวจ trusted backend health ในที่เก็บใหม่ก่อนเดินต่อคู่ที่ยังไม่เริ่ม หาก health ไม่ผ่านหรือ cleanup ไม่ยืนยัน ให้หยุด batch; launch exit 125/126/127, mapping drift, credential 401/403 และ hash/input drift ยังหยุดทันที ไม่เปลี่ยน source, prompt, gate, generation setting หรือ execution cap ของงานทดลอง

การตรวจ health หลัง timeout ใช้สคริปต์ trusted เดิมใน container ใหม่ ชื่อที่เก็บเป็น unique ไม่มีการเขียนทับ แต่ละ probe เก็บ lock ก่อน outcome และ summary หลัง outcome การตรวจนี้ทำหลังจบ run_pair เมื่อไม่มี candidate execution ของ worker อื่น (execution lock เดียวกัน) ไม่ให้ resource competition ทำให้ผลยิ่งกำกวม

คงกติกา provider circuit เดิม: deployment ที่มี PROVIDER_UNRESOLVED ติดต่อกันสามครั้งใน continuation นี้จะหยุดส่งงานใหม่ deployment อื่นอาจทำคู่ที่ยังไม่เริ่มต่อ ทุก unresolved อยู่ใน denominator และแจ้ง billable outcome unknown ค่าใช้จ่ายไม่มี currency ยืนยัน ไม่ระบุเป็น USD

Frozen continuation 2 ระบุคู่ที่ยังไม่เริ่มทั้งหมดและ hash ของหลักฐาน 22 คู่เดิม ไม่มีการแทน case ตามคะแนน ไม่มี investigator repair ของ code และไม่มีการเปลี่ยนผลเพื่อให้ Major Revision ผ่าน เปรียบเทียบ allocation main ต้องรอ calibration เสร็จและ freeze profiles แยก
