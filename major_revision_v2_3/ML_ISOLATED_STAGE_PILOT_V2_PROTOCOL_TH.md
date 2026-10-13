# ML isolated-stage pilot v2

แก้ exposure accounting ก่อน provider call แรก วันที่5ตุลาคม2026. **Feasibility บน reused specifications ไม่ใช่ held-out calibration/main**.

Protocol v1 ถูก freezeแต่ไม่ได้ส่ง36planned requests. การตรวจเพิ่มพบ legacy `dag_provider_*.json` และ `dag_summary.json` สำหรับ ADULT_P1/GPT, ADULT_P2/GLM และ BEIJING_P1/GPT แม้บางรุ่นไม่มี request-started file. V1 scan request-only จึงไม่พอ. เก็บ protocol/lock/preparation v1 ไว้ทั้งหมด และห้าม execute v1. V2 เก็บ exposure inventory แยกพร้อม hashes ก่อน calls. ไม่แก้หรือเรียกซ้ำผล legacy.

ใช้ ADULT_P1, BEIJING_P1, ADULT_P2 ×4stages ×3aliases =36 operational first attempts ภายใต้ **protocol v2 นี้**. ไม่มี model retry และไม่เรียกว่า first-ever attempt บน specification. การเห็น case/interface รุ่นเก่าสามารถมีผลต่อ generalization; unknown provider caching/pretraining contamination ยังเป็น limitation. Provider requests ใช้ stateless prompt ไม่มี chat history แต่ไม่พิสูจน์ว่าไม่เคยเห็นโจทย์มาก่อน.

นำ trusted reference preparation12probes ที่ผ่านของ v1 มาใช้ด้วย provenance reference ไม่ rerun/นับเป็น12observationsใหม่. ทุก model ทำทุกstageจากinput/trusted predecessorsเดียวกัน ไม่ถูก censorเมื่อstageก่อนล้ม. Public ordinal artifact interface, current-stage-only source generation, semantic preprocessing check, fresh-process train/package quality gates และ clean replay ใช้ implementation v1ที่ไม่แก้. ไม่ส่ง current/future trusted solutionหรือhidden labels/scores. สองcorporaใช้rowsetsร่วมกับpilot; Adultสองvariants/Beijingหนึ่งvariantไม่ใช่datasetsอิสระ.

ตรึงเหมือนกันทุกalias: temperature0, outputcap32,768, provider720s; sandbox360s/gate,2CPUs/4GiB/no-network/read-only/UID65534; OMP/OpenBLAS/MKL/NumExpr threads2. Serialize container gatesผ่านfilelockแต่provider workers concurrent. Timeout stop/removeเฉพาะชื่อที่สร้างแล้วตรวจabsence. API keyรับstdin/tัดออกจากcontainerenv. No automatic paid retries; unresolvedcostไม่เป็นศูนย์และcurrencyยังไม่ยืนยัน.

ทุกรายการอยู่ในplanned operational denominator36. Per deployment-stageมี3specificationsจาก2corpus clusters รายงานcounts/outcomesและunresolvedแยก; ไม่ใช้เป็นindependentbinomial precision ไม่fitdifficulty/Ability Rank/simulationprobability. ไม่poolกับDAGv3/legacy/microtasks. วิเคราะห์ความสามารถในการทำstageตามinterfaceและสาเหตุfailures ไม่สรุปvendorrankingหรือallocationadvantage.

Implementation v2 reuse shared frozen v1 functions โดยเปลี่ยนเฉพาะ output root, lock path, protocol/exposure dependency recordsผ่าน wrapper ที่อยู่ในlock. Shared functions/source v1ไม่ถูกเขียนทับ. V2 auditตรวจdependenciesทั้งสองรุ่น, commoninputs/predecessors, unchangedcandidate source, actualgatesและreplay.

หลังชุดนี้ ยังต้องสร้างheld-out task specificationsที่แยกจากexposed inventory และกำหนดprecisionก่อนcalibration/main. ความสำเร็จของfeasibilityชุดนี้ไม่ปิดMajor Revisionทั้งหมด.
