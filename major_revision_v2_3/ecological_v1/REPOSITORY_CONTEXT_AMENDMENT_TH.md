# เพิ่ม public formatter context ก่อน model calls

Context preparation v1 ผ่าน source hash, no-op และ import-sentinel สำหรับห้า case แล้ว แต่ matplotlib_10 หยุดก่อน prompt freeze เพราะ `ticker.py` เป็นไฟล์ยาวที่ไม่มี function ในชื่อที่ประกาศไว้ การหยุดครั้งนี้เป็น instrument error และไม่มี LLM call สำหรับชุดนี้

v2 เพิ่มเฉพาะ public formatter methods `get_offset`, `set_useOffset` และ `_set_format` ที่เกี่ยวกับ offset text ของ visible test เข้ากฎ AST excerpt เดิม ไม่อ่าน gold diff ไม่เปลี่ยน allowed files หรือ buggy source ไม่เพิ่ม token cap และไม่เปลี่ยน regression identities เก็บ context v1 ที่ยังไม่ครบไว้ แล้วทำ matplotlib_10 ใน directory ใหม่ ห้า case ที่ผ่านแล้วใช้ hashes และหลักฐานเดิม ไม่รันทดสอบเพื่อคัดเลือกตาม model outcomes

แต่ละ case ระบุ preparation_root และ baseline_root ชัดเจน การซ่อมภายหลังเป็น investigator-localized repair ภายใต้ excerpts เหล่านี้ ไม่ใช่ model localization แบบอิสระทั้ง repository
