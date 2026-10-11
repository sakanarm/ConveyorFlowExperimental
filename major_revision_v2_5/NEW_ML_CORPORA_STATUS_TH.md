# v2.5: ข้อมูล ML ใหม่ (ยังไม่ใช่ผล Real-LLM)

วันที่ 11 ตุลาคม 2026 ได้เพิ่ม **แหล่งข้อมูลอิสระระดับ corpus** อีกสองชุด เพื่อแก้ข้อจำกัดเดิมที่ทดสอบ ML บน Adult และ Beijing ซ้ำหลาย task specification เท่านั้น การเพิ่ม task ย่อยบน corpus เดิมไม่นับเป็นแหล่งข้อมูลอิสระใหม่ การเตรียมครั้งนี้ไม่มี API call และยังไม่อนุญาตให้ใช้ตัวเลขนี้เป็นผลของ CF-Fit

| Corpus | แหล่งสาธารณะ | ขนาดต้นฉบับ | Task | สถานะ |
|---|---|---:|---|---|
| Bank Marketing (`bank-full.csv`) | [UCI, DOI 10.24432/C5K306](https://archive.ics.uci.edu/dataset/222/bank%2Bmarket) | 45,211 แถว | binary classification | split, row-level audit และ trusted reference gate ใน container ผ่าน; **ยังไม่มี paid LLM result** |
| Covertype | [UCI, DOI 10.24432/C50K5N](https://archive.ics.uci.edu/dataset/31/covertype*) | 581,012 แถว | 7-class classification | split และ row-level audit ผ่าน; verifier ปัจจุบันรองรับแค่ binary classification/regression จึง **ยังเข้า experiment ไม่ได้** |

ดาวน์โหลดจาก URL ทางการใน [`source_manifest.json`](new_ml_corpora_v1/source_manifest.json) และตรวจ SHA-256 ของ ZIP ทั้งสองชุด (`bank`: `e0bf5f5de5b846e2f18e9d90606637267d46dfa260e0f17bb12e605db5efbeb4`; `covertype`: `89a975c2457cd48e824238ae43c5a3cb762e42c4b4078d9b44a4514055105f6d`) raw archives ไม่ขึ้น Git แต่สคริปต์ [`acquire_ml_sources_v1.py`](acquire_ml_sources_v1.py) โหลดซ้ำได้

วิธีแบ่งข้อมูลถูกกำหนดใน [`prepare_ml_splits_v1.py`](prepare_ml_splits_v1.py) และล็อก hash/จำนวนแถวใน [`split_manifest.json`](new_ml_corpora_v1/split_manifest.json):

- Bank: ใช้ลำดับแถวต้นฉบับซึ่ง UCI ระบุว่าเรียงตามวันที่ แบ่ง 31,647/6,782/6,782 สำหรับ train/validation/test โดยไม่ shuffle ตัด `duration` ซึ่งรู้ได้หลังจบการโทรก่อนสร้าง public input ทุกไฟล์ ข้อมูลไม่มี client ID หรือ timestamp ละเอียด จึง **อ้างไม่ได้ว่าแยกตามลูกค้าหรือเป็น prospective validation จริง**
- Covertype: ใช้ deterministic hash ของ feature ทั้ง 54 ตัว (ไม่ใช้ target) แบ่ง 407,058/86,698/87,256 แถว feature vector ที่เหมือนกันทุกประการอยู่ split เดียวกัน; ไม่มีลำดับเวลาให้ทดสอบ temporal generalization
- test labels อยู่ใน `hidden/` แยกจาก `public/` และต้องไม่ mount เข้า candidate container

[`audit_ml_splits_v1.py`](audit_ml_splits_v1.py) อ่านไฟล์ผลจริงซ้ำและยืนยันจำนวนแถว, class counts, row IDs ไม่ซ้ำข้าม split, hidden labels ตรงกับ test IDs, ไม่มี `duration` ใน public Bank และไม่มี exact feature-group overlap ข้าม split ทั้งสอง corpus ผล audit ผ่าน แต่ **Bank มี temporal class shift สูง**: สัดส่วน positive ใน train/validation/test ประมาณ 5.8%/11.5%/39.3% ดังนั้นต้องใช้ baseline/reference gate ที่กำหนดล่วงหน้าและวิเคราะห์เปรียบเทียบแบบ paired *ภายใน corpus* ไม่เปรียบเทียบ raw accuracy ข้าม corpus

Bank reference ใช้ scikit-learn dependency lock เดิมใน rootless, network-isolated, read-only Podman image ID `c303e2440992fc0c745aa442cb2467cfbe80b36a9adaa25002d5960cc1da5c58` ครั้งแรก container ยังไม่เริ่ม Python เพราะ `--pids-limit` ใช้ร่วมกับ disabled cgroups ไม่ได้ จึงเก็บ failure report ไว้และรัน recovery ด้วย image/code/data เดิมโดยตัดเฉพาะ flag นี้ ก่อนเปิด hidden test reference แบบ train-only ได้ validation ROC-AUC **0.6681**; ล็อกเกณฑ์ตามกฎเดิมของ Adult คือ `0.5 + 0.5 × (reference_validation_AUC − 0.5)` = **0.584065** จากนั้นจึงเปิด hidden test *เฉพาะ trusted verifier* ได้ ROC-AUC **0.6368** ซึ่งผ่านเกณฑ์ที่ล็อกไว้แล้ว ลำดับเวลาและ hash ของหลักฐานตรวจได้ด้วย [`audit_bank_gate_v1.py`](audit_bank_gate_v1.py) นี่เป็นการคัดเลือกความพร้อมของ benchmark ไม่ใช่ผล CF-Fit หรือผล LLM; เกณฑ์ 0.584 ต่ำเพราะโจทย์ temporal/no-duration ยาก จึงต้องรายงาน AUC ต่อเนื่องและ confidence/uncertainty เพิ่ม ไม่ตีความ binary pass อย่างเดียว

ก่อน paid LLM ต้องทำต่อ: (1) หากจะใช้ Covertype ต้องเพิ่ม multiclass prediction schema/metric (เช่น macro-F1) พร้อม unit tests และ reference gate ก่อน freeze, มิฉะนั้นตัดออกพร้อมบันทึกเหตุผล; (2) freeze Bank case DAG และ balanced arms โดยคง assessor/executor/verifier เท่ากันทุก arm; (3) เพิ่ม repository อิสระและแผน precision ระดับ corpus/repository; (4) จัดการ cost missingness โดยไม่แทนค่าไม่ทราบด้วยศูนย์ ผลเตรียมข้อมูลชุดนี้ยังไม่ปิด Major Revision gap

Runtime note: Ubuntu WSL เปิดได้และ rootless Podman ว่าง แต่ `rootful podman system df` ตอบว่า image ID `be917ce...` ใน local storage อาจเสียหาย ยังไม่ลบ image หรือ container ใด ๆ และยังไม่ได้ใช้ rootful container ในงานต่อจากจุดนี้
