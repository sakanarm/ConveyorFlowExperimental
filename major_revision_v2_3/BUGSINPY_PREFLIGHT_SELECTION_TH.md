# BugsInPy v2.3: กติกา preflight และการเลือก pilot cases

กติกานี้ตรึงเมื่อ 4 ตุลาคม 2026 ก่อน preflight รายการแรก. อัปเดต 5 ตุลาคม: เลือก 6 reproducible cases จาก 3 repositories ได้แล้วตามกติกาเดิม: pandas #88/#76/#128/#27, matplotlib #15, luigi #19. Metadata 501 candidates ใน `bugsinpy_candidate_manifest.json` ไม่ถูกแก้ย้อนหลัง; สถานะปัจจุบันอยู่ใน ledger

## เหตุผล

ถ้าเลือก bugs ที่ Docker รันง่ายหรือที่ LLM ซ่อมได้ภายหลัง จะเกิด selection bias. จึงตรวจ candidate ตาม `selection_hash` จากน้อยไปมาก. ทุก candidate ที่ตรวจต้องมีหนึ่งบรรทัดใน append-only `results/bugsinpy_preflight_ledger.jsonl` ตามลำดับติดกัน; ห้ามข้าม candidate เงียบ ๆ

## Preflight ก่อนเรียก LLM

ทำใน isolated container ของ repository/version นั้น: buggy checkout ต้อง fail ที่ relevant test; fixed checkout ต้อง pass ภายใต้ environment และ test contract เดียวกัน. บันทึก image digest, logs, report hashes, timeout และเหตุผล environment exclusion. ไม่ให้ model เห็น fixed source/gold patch. สถานะที่รับได้:

- `reproducible`: `buggy_test_failed=true`, `fixed_test_passed=true`, `container_image_id=sha256:<64 hex>`, `buggy_test_report_sha256` และ `fixed_test_report_sha256` อย่างละ 64 hex
- `environment_excluded`: มีเหตุผลเฉพาะที่ตรวจได้ เช่น dependency/build/timeout ซึ่งเกิดก่อน LLM; ห้ามใช้เหตุผลว่า model ทำไม่ได้

`select_bugsinpy_pilot.py` ตรวจลำดับและ field เหล่านี้จาก ledger. **Hash ใน ledger ยังต้องตรวจเทียบไฟล์ test report จริงในขั้น preflight audit**; selector เพียงอย่างเดียวไม่พิสูจน์ว่า container test ผ่าน. ห้ามเรียก pilot selected ว่า evidence ของ LLM repair

## กติกาเลือกแบบ deterministic

หยุดที่ prefix แรกของรายการ reproducible ที่มีอย่างน้อย 6 cases และอย่างน้อย 3 repositories. จาก prefix นั้นเลือก subsequence 6 รายการที่เรียงตาม hash และเร็วที่สุดแบบ lexicographic แต่ยังคง ≥3 repositories. นโยบายนี้ทำให้ไม่ย้อนเลือก cases หลังเห็นผลโมเดล; เมื่อเลือกครบให้ freeze hashes ของ manifest/ledger และ selected-case reports ก่อน API call แรก

ถ้าหา 6 cases/3 repositories ไม่ได้ภายใต้งบ preflight ที่กำหนดไว้ก่อน ให้รายงาน shortfall และจำนวน/เหตุผลคัดออก ไม่ลดเกณฑ์เงียบ ๆ. Main case set ต้องแยกจาก pilot และกำหนดก่อนเปิด policy outcomes

## งานที่ยังขาด

Environment และ source-report hashes ตรวจผ่านครบ 6 cases/3 repos. Combined prefix อยู่ที่ `results/bugsinpy_serial_build_recovery_v6_protocol/combined_prefix_ledger.jsonl`; เก็บ thefuck #32 ที่ติด APT 404 เป็น exclusion รายการที่ 7 และ failed profiles เดิม. Four pandas successes ถูก carry ด้วย provenance ไม่ได้ reexecute หกครั้งใหม่ทั้งหมด

Candidate/verifier images ผ่าน isolation และ protected public-regression baseline แล้ว (`results/repository_baseline_gate_v2/audit.json`). จาก 60 selected items มี 58 active passes และ 2 historical expected failures ที่ต้องรายงานแยกกัน. ยังต้อง evaluator identity smoke, MFEC localized patches และ clean replay. Test-tampering guard ไม่พิสูจน์ว่าป้องกัน adversarial evasion ทุกชนิด และ withheld public tests ไม่ใช่ novel hidden tests
