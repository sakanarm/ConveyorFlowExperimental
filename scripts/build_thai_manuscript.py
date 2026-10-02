from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ConveyorFlow_IEEE_Manuscript.docx"
OUTPUT = ROOT / "ConveyorFlow_IEEE_Manuscript_TH.docx"
THAI_FONT = "Leelawadee UI"


# The Thai manuscript is a faithful, advisor-facing translation of the locked
# English manuscript.  Paragraph indices are intentional: they make a changed
# English source fail loudly instead of silently producing a mixed-version file.
THAI_PARAGRAPHS = {
    0: "ConveyorFlow: กลไกเลือกงานด้วยตนเองแบบกระจายศูนย์ตามความเหมาะสมของความสามารถ สำหรับทีม LLM Agent ที่มีความหลากหลาย",
    1: "Sakan Punyanon",
    2: "สังกัดและอีเมลผู้เขียนสำหรับติดต่อจะยืนยันก่อนส่งตีพิมพ์",
    3: (
        "บทคัดย่อ—LLM Agent ที่ทำงานร่วมกันมีความสามารถ เวลาแฝง การใช้โทเคน และต้นทุนแตกต่างกัน แต่ระบบส่วนใหญ่มักกำหนดผู้รับงานไว้ล่วงหน้าหรือใช้ตัวกลางจัดสรรงาน บทความนี้นำเสนอ ConveyorFlow กลไกจัดสรรงานแบบกระจายศูนย์ซึ่งให้งานที่พร้อมทำเคลื่อนอยู่บนสายพานร่วม และให้ Agent ที่ว่างประเมินความเหมาะสมของงานแล้วอาสารับงานด้วยตนเอง กลไก CF-Fit เชื่อมการประเมินเฉพาะที่ ความเหมาะสมระหว่างความสามารถกับความยาก การชะลอรับงานชั่วคราวเมื่อ Agent เก่งเกินความจำเป็น และการผ่อนเงื่อนไขตามอายุงาน งานวิจัยประเมินผลเป็นเวกเตอร์ trade-off แทนการบังคับให้วิธีเดียวชนะทุกตัวชี้วัด การจำลองแบบ discrete-event ที่กำหนดแผนล่วงหน้า 22,500 รอบ ใช้ workload จากข้อมูลสาธารณะและเปรียบเทียบกับ static และ centralized controls รวมทั้ง ablation และ fallback stress tests ผลชี้ว่า CF-Fit ให้ความเร็วและการปิดสถานะงานที่ต่างจากวิธีคงที่ แต่ไม่ได้ลดต้นทุนในทุกกรณี และผลขึ้นกับการจับคู่ความสามารถกับทรัพยากร การทดลอง Real LLM เพิ่มเติมบน 60 กรณี 10 paired seeds แสดง trade-off ที่ชัดเจนระหว่างความเร็ว/การใช้ทรัพยากรกับ completion/ต้นทุนเมื่อเทียบกับ static round robin ขณะที่ CF-Fit และ Central-Fit ยังไม่พบความแตกต่างอย่างมีนัยสำคัญภายใต้ขนาดตัวอย่างนี้ ผลทั้งหมดสนับสนุนการตีความ ConveyorFlow เป็นกลไกจัดสรรงานที่ปรับ trade-off ได้ มิใช่วิธีที่เหนือกว่าทุก baseline ในทุกมิติ"
    ),
    4: "คำสำคัญ—การจัดสรรงานแบบกระจายศูนย์, Agent ที่มีความหลากหลาย, แบบจำลองภาษาขนาดใหญ่, การเลือกงานด้วยตนเอง, การจำลองแบบเหตุการณ์ไม่ต่อเนื่อง",
    6: "I. บทนำ",
    7: "ทีม LLM Agent แบ่งงานซับซ้อนออกเป็นบทบาทเฉพาะทางมากขึ้น กรอบงานเดิมแสดงประโยชน์ของบทสนทนาที่มีโครงสร้างและ workflow ตามบทบาท [1]–[3] แต่การมอบหมายงานมักถูกกำหนดล่วงหน้าหรือควบคุมโดยตัวกลาง สมมติฐานนี้มีผลสำคัญเมื่อ Agent ต่างกันทั้งความสามารถ เวลาให้บริการ ปริมาณโทเคน และราคา เพราะการส่งทุกงานให้ Agent ที่เก่งที่สุดอาจแม่นยำแต่แพง ขณะที่การส่งให้ Agent ราคาถูกทั้งหมดอาจเพิ่ม retry และ tail latency",
    8: "ConveyorFlow มองการจัดสรรเป็นกระแสของงานที่ dependency พร้อมแล้วบนสายพานร่วม Agent ที่ว่างจะตรวจหน้าต่างงานขนาดจำกัด ประเมินงานที่เห็นจากข้อมูลเฉพาะที่ และอาสารับงาน การตัดสินใจจัดสรรของ CF-Fit จึงเป็นแบบกระจายศูนย์ โดยไม่มีองค์ประกอบใดจัดอันดับ Agent ทั้งหมดจากส่วนกลาง อย่างไรก็ตาม สายพาน READY กลไก atomic claim และ event ledger ยังเป็นโครงสร้างประสานงานร่วม ข้อนี้ทำให้งานไม่อ้างเกินจริงว่าระบบทั้งหมดเป็น distributed โดยสมบูรณ์",
    9: "Contribution เชิงวิทยาศาสตร์จึงไม่ใช่รายชื่อนโยบายจำนวนมาก แต่เป็นกลไกที่เชื่อมกัน: ความหลากหลายของความสามารถทำให้การเลือกงานเฉพาะที่มีเหตุผล capability–task fit กำกับการอาสา Agent ที่เก่งเกินงานสามารถ stand down ชั่วคราว และ aging จะผ่อนความลังเลเพื่อไม่ให้งานที่ fit ต่ำรอไม่สิ้นสุด การศึกษาจึงถามว่ากลไกนี้เปลี่ยนเวกเตอร์ของต้นทุน throughput เวลา completion utilization และ failure อย่างไร โดยไม่ตั้งเงื่อนไขว่าต้องชนะทุกตัวชี้วัด",
    10: "Contribution มีสามส่วน ได้แก่ (1) กลไก self-selection แบบกระจายศูนย์ที่ทำซ้ำได้และระบุ fit, stand-down, aging และพฤติกรรมเมื่อไม่มีผู้รับงานอย่างชัดเจน (2) การออกแบบควบคุมที่เปลี่ยนความแปรปรวนของความสามารถโดยคงขนาดทีมและค่าเฉลี่ย latent ability และ (3) การจำลองจาก event ledger ที่ freeze ก่อนรัน ใช้ workload จากข้อมูลสาธารณะ มี static/centralized controls, component ablations, fallback stress tests และ robustness ต่อ annotation/resource mapping",
    11: "II. งานที่เกี่ยวข้อง",
    12: "งานจัดสรรภารกิจแบบกระจายศูนย์ดั้งเดิมครอบคลุม Contract Net [7] อนุกรมวิธานการจัดสรรงาน [8], [9] และ consensus-based decentralized auctions [10] งานเหล่านี้ชี้ว่าการตัดสินใจเฉพาะที่หรือแบบตลาดลดการพึ่งพาตัวควบคุมกลางได้ แต่สมมติฐานด้านการสื่อสาร การประมูล และวัตถุประสงค์ต่างจากสถาปัตยกรรมสายพาน READY ร่วมสำหรับงานของ LLM Agent",
    13: "ระบบ LLM multi-agent เช่น AutoGen, MetaGPT, ChatDev, CAMEL และ AgentVerse ประสาน Agent เฉพาะทางผ่านบทสนทนา role play หรือ workflow มาตรฐาน [1]–[5] ขณะที่งานสำรวจล่าสุดจัดหมวดหมู่ด้าน environment interface, profiling, communication และ capability acquisition [6] ConveyorFlow เป็นส่วนเสริมที่แยกศึกษาว่าใครเลือกงานที่พร้อมและเลือกเพราะอะไร โดยใช้ capability fit และ bounded stand-down แทนการกำหนดกระบวนการพัฒนาซอฟต์แวร์ผ่านบทสนทนาทั้งหมด การจำลองที่ควบคุมเป็นหลักฐานเชิงสาเหตุหลัก ส่วน Real LLM เป็นหลักฐานระดับ implementation ที่แคบกว่า",
    14: "ขั้นตอนกำหนดความยากอ้างอิงแนวคิด LLM-based evaluation [11] และกำหนดขอบเขต validity อย่างเคร่งครัดตามข้อค้นพบเรื่อง prompt และ judge bias [12], [13] การประเมินสามรอบด้วยโมเดลพื้นฐานเดียวกันแต่ต่างบทบาทวัด procedural stability ไม่ใช่ความสอดคล้องของผู้เชี่ยวชาญมนุษย์อิสระหรือ external ground truth ข้อจำกัดนี้ถูกนำไปใช้ในการออกแบบ robustness และการเขียน claim",
    15: "III. แบบจำลองระบบและวัตถุประสงค์",
    16: "หนึ่ง job เป็นกราฟมีทิศทางแบบไม่มีวงจร (DAG) งานจะเข้าสู่ READY frontier ตามลำดับเมื่อ dependency ทั้งหมดผ่านการตรวจสอบแล้ว ระบบมี Agent ไม่เกินสี่ตัว แต่ละ Agent มี latent ability θ แยกตาม workload พร้อม speed factor, token factor และ price factor โดยจงใจแยกความสามารถออกจากต้นทุนทรัพยากร",
    17: "วัตถุประสงค์หลักคือทำให้ cost per verified task ต่ำลงภายใต้ข้อจำกัดคุณภาพ completion ที่กำหนดล่วงหน้า เกณฑ์ non-inferiority ของ completion กำหนดให้ขอบล่างของช่วงความเชื่อมั่นของ CF-Fit ลบ comparator ไม่น้อยกว่า −0.03 ส่วน dead-letter และ unsettled กำหนดให้ขอบบนไม่เกิน +0.03 ตัวชี้วัดรองสำคัญคือ verified throughput และ P95 terminal flow time ขณะที่ utilization ใช้อธิบายพฤติกรรมและไม่ถือว่าสูงกว่าแปลว่าดีกว่าโดยอัตโนมัติ",
    18: "งานไม่สร้างคะแนนถ่วงน้ำหนักภายหลังเห็นผลเพื่อรวมทุก outcome นโยบายหนึ่งอาจถูกกว่าแต่ช้ากว่า เร็วกว่าแต่ completion ต่ำกว่า หรือเหมาะเฉพาะบาง resource regime ดังนั้น estimand คือเวกเตอร์ trade-off ภายใต้ workload, load, team composition และ resource mapping ที่ระบุ",
    21: "รูปที่ 1 สถาปัตยกรรมระบบ ConveyorFlow: workload, allocation rule และ ability/resource profile ที่ freeze แล้วป้อนเข้า state-machine core เดียวกัน ส่วน assessor, executor และ verifier ถูกใช้งานทั้งใน simulation 22,500 รอบและ Real LLM 60 กรณี โดยทั้งสองชั้นเขียน append-only ledger เข้าสู่ metric และ analysis pipeline เดียวกัน",
    23: "IV. กลไก CONVEYORFLOW",
    24: "A. การสังเกตเฉพาะที่และเงื่อนไขรับงาน",
    25: "Agent ที่ว่างแต่ละตัวสแกนงาน READY ที่มองเห็นได้ไม่เกิน K_scan=8 งาน แล้วประมาณค่าความยาก d-hat, โอกาสผ่าน p-hat, effort และ confidence งานจะ eligible เมื่อผ่าน skill constraint และ retry-diversity rule และ p-hat สูงกว่า threshold τ(age) โดยค่าเริ่มต้นลดจาก 0.60 เป็น 0.50 และ 0.35 ตามเวลารอ",
    26: "B. Capability Fit และ Stand-Down",
    27: "สำหรับงานที่ eligible เวลาหน่วงก่อน claim รวม capability mismatch, overqualification, urgency และ deterministic keyed jitter ดังสมการ backoff = |level−d-hat| + 0.8·max(0, level−d-hat)·(1−urgency) − 0.5·urgency + jitter Agent ที่เก่งเกินงานจึงลังเลในช่วงต้นเพื่อสำรองความสามารถสูงให้งานยาก แต่ไม่ใช่การปฏิเสธถาวร เพราะ penalty ลดลงตามอายุงานและถูกยกเลิกเมื่อถึง aging threshold ที่สอง",
    28: "C. Atomic Claim และการจัดการเมื่อไม่มีผู้รับงาน",
    29: "Agent แต่ละตัวเลือก candidate ได้ไม่เกินหนึ่งงาน Claim ถูกเรียงตามเวลาที่คำนวณเฉพาะที่และตัดสินด้วย atomic compare-and-swap ผู้แพ้กลับเข้าสู่รอบตัดสินใจถัดไป กลไก F2 จะเสนอซ้ำ ย้ายงานไปท้ายสายพานที่ W1=8 และ W2=20 พร้อมผ่อน threshold และ stand-down เมื่อถึง W3=50 หรือ requeue ครบแปดครั้ง งานจะเป็น DEAD_LETTER และงานที่พึ่งพาถูกนับ terminal ส่วน F3 บังคับ rescue โดยตัวกลางและรายงานเป็น hybrid reference เท่านั้น",
    30: "D. สถาปัตยกรรมกระบวนการตั้งแต่ต้นจนจบ",
    31: "รูปที่ 2 ติดตามงานหนึ่งชิ้นตั้งแต่เข้าสายพาน การประเมินตนเอง การอาสาหรือ stand down การ claim การ execute การตรวจแบบ deterministic การเผยแพร่ artifact การ retry และ terminal accounting ขอบเขตการตัดสินใจถูกระบุชัด: สายพานกระจายเฉพาะงาน READY แต่ละ Agent ประเมิน can-do ความยาก และ confidence อย่างอิสระ และ atomic claim มีหน้าที่แก้ race โดยไม่เลือก Agent ที่ต้องการ ถ้าทำไม่ผ่าน งานกลับเข้าสายพานเมื่อยังเหลือ retry และเมื่อครบขอบเขตจะเป็น ABANDONED/DEAD_LETTER Job เสร็จเมื่อทุก task เป็น verified DONE",
    34: "รูปที่ 2 สถาปัตยกรรมกระบวนการ ConveyorFlow: Agent Ability Rank 1/2/3 เห็นสายพาน READY เดียวกัน ประเมินตนเอง อาสาหรือ stand down และแข่งขันผ่าน atomic claim ผล execute/verify ส่งกลับ blackboard และจบ job หรือเข้าสู่ bounded retry แหล่งแก้ไขได้: หน้า ‘ConveyorFlow - Process Architecture’ ใน ConveyorFlow_diagrams_en_working.drawio",
    36: "E. การเปรียบเทียบสายพานแบบควบคุมและความหมายของหนึ่ง Tick",
    37: "รูปที่ 3 และ 4 ทำให้ experimental control ชัดเจน ทั้ง CF-Fit และ static baseline รับงานที่ dependency ปลดล็อกเหมือนกัน วางบนสายพาน READY เดียวกัน ใช้กติกา execute/verify, retry และ terminal accounting เดียวกัน สิ่งที่เปลี่ยนคืออำนาจการจัดสรร ภายใต้ CF-Fit Agent ว่างทุกตัวมองหน้าต่างสายพาน ประเมิน capability-task fit เฉพาะที่ และอาจอาสาหรือ stand down ส่วน atomic claim ใช้แก้ simultaneous claim เท่านั้น ไม่ได้จัดอันดับคู่ Agent-task จากส่วนกลาง",
    40: "รูปที่ 3 การไหลของงาน CF-Fit: งานที่ dependency พร้อมแล้วเคลื่อนบนสายพานร่วม Agent ที่ว่างประเมินงานที่เห็นอย่างอิสระ อาสาเมื่อ eligible และใช้ atomic claim เฉพาะแก้ collision แหล่งแก้ไขได้: หน้า ‘Belt - CF-Fit (P3)’",
    42: "รูปที่ 4 Static-allocation control บนสายพานเดียวกัน: กำหนดกติกา task-to-agent ก่อนรัน Agent จึงไม่เลือกงานเองขณะทำงาน ขณะที่ arrival, readiness, execute, verify และ failure accounting ถูกควบคุมให้เหมือนกัน แหล่งแก้ไขได้: หน้า ‘Baseline - Static assignment (P0_FIXED)’",
    44: "ใน static control ตาราง ownership หรือ routing ที่ freeze แล้วกำหนดเจ้าของของแต่ละ task class ก่อนเริ่มรัน Agent ที่ว่างเพียงทำงานที่ถูกแมปไว้ ความต่างที่พบจึงไม่เกิดจาก queue, workload, dependency rule หรือ verifier ที่ต่างกัน แต่ประมาณผลของการเปลี่ยนจาก predetermined allocation เป็น decentralized self-selection ภายใต้ simulation ที่จับคู่เงื่อนไข ส่วน Central-Fit เป็น comparator แบบรวมศูนย์ที่ใช้ assessment/fit ใกล้เคียงกันแต่ให้ global matcher เลือกคู่",
    45: "รูปที่ 5 นิยามหนึ่ง simulation tick เพื่อให้ลำดับเชิงสาเหตุไม่กำกวม ระบบใช้ churn ตามกำหนด รับ arrival เปิด task ที่ dependency ผ่าน และปรับ belt order/age จากนั้น Agent ว่างสแกน ประเมิน และส่ง claim ได้ไม่เกินหนึ่งรายการ atomic resolution เริ่มงานของผู้ชนะที่ไม่ชนกัน แล้วบันทึก execution, verification, cost, token, busy time, retry และ terminal state ลง event ledger งานที่ไม่ผ่านถูกเสนอใหม่ถ้ายังมี attempt หากไม่มี volunteer F2 จะคงงานบนสายพาน เพิ่มอายุและ requeue พร้อมผ่อนเงื่อนไข ก่อนส่ง DEAD_LETTER เมื่อถึงขอบเขต Run จบเมื่อสายพานว่าง ไม่มี Agent ทำงาน และไม่มี arrival หรือ dependency release ในอนาคต",
    48: "รูปที่ 5 หนึ่ง simulation tick แบบ deterministic ตามลำดับดำเนินการ ทุก policy ใช้โครง tick เดียวกันและเปลี่ยนเฉพาะ allocation-decision block แหล่งแก้ไขได้: หน้า ‘One tick of the conveyor, in order’",
    50: "V. ระเบียบวิธีวิจัย",
    51: "A. แหล่งข้อมูล workload สาธารณะ",
    52: "สร้างการกระจาย workload จาก UCI Adult 48,842 ระเบียน [14], UCI Beijing Multi-Site Air Quality 420,768 ระเบียน [15] และ CodeXGLUE Bugs2Fix small training corpus 46,680 คู่ฟังก์ชัน buggy/fixed [16] Adult และ Beijing สร้าง DAG งาน ML-build เจ็ดขั้น ส่วน Bugs2Fix สร้าง DAG ห้าขั้น reproduce–localize–repair–regression-test–report คู่ Bugs2Fix ใช้ลักษณะการกระจายเท่านั้น ไม่อ้างว่าเป็น repository test ที่ execute ได้ URL, license, byte count และ SHA-256 ถูก freeze ใน data manifest",
    53: "B. นิยามเชิงปฏิบัติการของความยากงาน",
    54: "กำหนดความยากจาก stage-by-stratum specification 304 รายการที่มาจาก deterministic variants 48 แบบ การประเมินแบบปกปิดสามรอบใช้ LLM พื้นฐานตัวเดียวในบทบาท ML Methodologist, Software Reliability Reviewer และ Workflow/Resource Reviewer ให้คะแนน rubric 5 มิติ มิติละ 0–2 รวม 0–3 เป็น D1, 4–6 เป็น D2 และ 7–10 เป็น D3 ค่า exact agreement รายคู่ 0.770–0.829, quadratic-weighted κ 0.793–0.823 และ adjacent agreement 1.000 รายการไม่เป็นเอกฉันท์ 94 รายการถูก adjudicate แยก ผลสุดท้าย D1=52, D2=113 และ D3=139 โดย 17 รายการต่างจาก mechanical consensus",
    55: "การประเมินสามรอบไม่ใช่ผู้เชี่ยวชาญมนุษย์อิสระ ค่า agreement จึงเป็นหลักฐาน procedural stability ของโมเดลเดียวเท่านั้น ค่า κ ต่ำสุดใน subgroup คือ 0.628 สำหรับผู้ประเมินคู่หนึ่งของ Beijing จึงเก็บ lower/upper vote mappings ซึ่งเปลี่ยน 47 labels ไว้เป็น sensitivity bounds",
    56: "C. Ability Rank และองค์ประกอบทีม",
    57: "Ability แทนด้วย behavioral rank สามระดับ ไม่ใช้ชื่อโมเดล Ability Rank 1, 2 และ 3 (AR1–AR3) กำหนด θ=−1, 0 และ +1 ใน logit[P(pass)] = α_w + 0.85θ − 1.2(d−2) โดย α_Adult=0.88 และ α_Beijing=α_Bugs2Fix=0.86 ทีม H0=(2,2,2,2), H1=(1,2,2,3) และ H2=(1,1,3,3) มี Agent สี่ตัวและ mean rank=2 เท่ากัน แต่ variance เท่ากับ 0, 0.5 และ 1 จึงเป็น boundary compositions ที่แยกผลของ capability variance ส่วน AR1×4 ใช้เฉพาะ fallback stress test",
    58: "D. Controls, Ablations และ Resource Regimes",
    59: "Static controls ได้แก่ fixed skill ownership (S1), precomputed difficulty-level routing (S2) และ precomputed round robin (S3) Central-Fit ใช้ assessment/fit ใกล้เคียงกันแต่จับคู่ free agent กับ task แบบ global Ablation ตัด assessment (A1), fit (A2), stand-down (A3) หรือ aging (A4) R0 ทำให้ speed/token/price เท่ากัน ส่วน R1 จับ AR1/AR2/AR3 กับ speed 0.90/1.00/1.15, token factor 0.80/1.00/1.30 และ price factor 0.50/1.00/3.00 พร้อม reversed/permuted mappings เพื่อตรวจ resource confounding",
    61: "ตารางที่ I การออกแบบการทดลองเชิงยืนยัน",
    62: "ยอด membership ซ้อนกันได้เมื่อหนึ่ง run อยู่ในหลายขอบเขต โดย frozen design มี 22,500 unique runs",
    64: "E. หน่วยทดลองและสถิติ",
    65: "หน่วยทดลองคือ run/seed สมบูรณ์ภายใน matched workload–load–team–resource cell ไม่ถือ task ภายใน run เป็น replicate อิสระ Policy ใน cell เดียวกันใช้ arrival, task attribute และ keyed potential outcome ร่วมกัน รายงาน paired median difference และ paired seed-cluster bootstrap 95% CI จาก 10,000 resamples ใช้ Wilcoxon signed-rank และ Holm correction ภายในแต่ละ RQ/metric family",
    66: "การรันเสร็จ 22,500 unique runs โดยไม่มี duplicate ID และไม่มี zero-success run Event ledger แบบบีบอัดทั้ง 22,500 ไฟล์ตรงกับ hash ที่บันทึก และ execution source hash ตรงกับ simulation source ปัจจุบัน snapshot ก่อนรันทำให้ audit ได้ว่าไม่ได้แก้ scientific code ระหว่างรัน",
    67: "ระบบหยุดจากโครงสร้างพื้นฐานหลัง 9,654 runs และกลับมาทำต่อจาก checkpoint เดิมโดยไม่เปลี่ยน seed หรือ configuration ก่อนรันเสร็จและก่อนคำนวณ comparative effect มีการแก้ implementation ของการวิเคราะห์ให้ CI ใช้ seed-cluster resampling จริงและ Holm family ตรงกับแผน การเปลี่ยนแปลงถูกบันทึกและไม่แก้ simulator, raw output หรือ hypothesis",
    68: "หลังล็อก confirmatory results เพิ่ม secondary descriptive analysis สองแบบ ได้แก่ two-objective Pareto frontier จาก descriptive median ของ RQ1 โดยไม่สร้าง weighted score และ competing-risk curve ที่ใช้เวลาสร้าง task เป็น time zero พร้อม verified/dead-letter เป็น competing events และ unresolved task ถูก right-censor ที่ horizon การวิเคราะห์นี้ช่วยตีความเท่านั้น ไม่ได้เพิ่ม confirmatory claim",
    69: "F. การรัน Simulation และการสร้าง Outcome",
    70: "ทุก paired policy run ใช้ observation horizon H, arrival schedule, task attribute, churn schedule และ keyed potential outcomes เดียวกัน Task ถูกเสนอเมื่อ job เข้าระบบและ dependency อนุญาต แต่ละ tick ใช้ลำดับเดียวกันสำหรับทุก policy ความต่างเกิดเฉพาะ allocation block Event ทุกชนิดเขียนเป็น append-only ledger ที่ใช้สร้าง summary metric และ hash audit",
    71: "Task completion rate คือจำนวน verified task หารด้วย offered task ทั้งหมด ส่วน dead-letter และ unsettled ใช้ denominator เดียวกัน Verified throughput คือ verified task หารด้วย H Productive utilization คือ productive busy ticks หารด้วย available agent ticks Cost รวม execution, assessment และ coordination tokens ตาม frozen resource mapping และ cost per verified task กำหนดเป็นอนันต์เมื่อไม่เกิดความสำเร็จ",
    72: "G. วิธีรันและตรวจสอบ Real LLM",
    73: "ชั้น Real LLM freeze executable cases 60 กรณี แบ่งเป็น Adult-derived ML 20, Beijing-derived ML 20 และ Bugs2Fix-derived repair 20 ทีมสาม Agent ที่เลือกไว้ถูกประเมินด้วย CF-Fit, Static S3 และ Central-Fit จำนวน 10 paired seeds ใช้ case bundle, eligibility rule, retry limit และ deterministic validator เดียวกัน Agent หนึ่งตัวทำได้ครั้งละหนึ่งงาน แต่ Agent ต่างตัวเรียก provider พร้อมกันโดยไม่มี global round barrier API call ที่สำเร็จจะนับ verified เมื่อ validator ของ task ผ่านเท่านั้น ดังนั้น pass=false คือ functional validation failure ไม่ใช่ provider failure โดยอัตโนมัติ Provider failure ที่เกิน retry ทำให้ policy run ไม่สมบูรณ์ แทนการนับเป็น task-quality failure",
    74: "สำหรับ valid run completion คือ verified cases หาร 60 ต้นทุนคำนวณจาก input/output token ที่บันทึกกับราคา observed ที่ freeze Cost per verified task หาร total cost ด้วย verified cases Throughput หาร verified cases ด้วย wall-clock time ของ run และ utilization รวม busy interval ต่อ Agent หารด้วยเวลาที่ Agent พร้อมใช้งาน Pairwise inference ใช้ seed เดียวกันและ Holm correction หก metric timing validity ใช้ frozen provider-gap rule แยกจาก functional validity",
    75: "VI. ผลการทดลอง",
    76: "A. RQ1: Trade-off ของการจัดสรรงาน",
    77: "ตารางที่ II แสดง CF-Fit ลบ control แต่ละแบบ แยก R0 และ R1 ค่าเปอร์เซ็นต์เทียบกับ median ของ comparator เครื่องหมายดอกจันคือ Holm-adjusted p<0.05 ต้องอ่านคอลัมน์ non-inferiority ร่วมกับต้นทุนและความเร็ว เพราะวิธีที่ถูกหรือเร็วกว่าอาจไม่ยอมรับหาก completion หรือ terminal failure ข้าม margin ที่กำหนด",
    79: "ตารางที่ II ผลต่าง paired median ของ CF-Fit ลบ comparator และผล non-inferiority",
    80: "* Holm-adjusted p<0.05 ค่าเปอร์เซ็นต์เป็น paired median difference เทียบกับ median ของ comparator",
    82: "จาก 8 resource-stratified contrasts ที่กำหนดล่วงหน้า CF-Fit มีต้นทุนต่ำกว่า 0/8 กรณี (มีนัยสำคัญ 0), throughput สูงกว่า 6/8 (มีนัยสำคัญ 6) และ P95 terminal time ต่ำกว่า 7/8 (มีนัยสำคัญ 6) เกณฑ์ non-inferiority ผ่านด้าน completion 8/8, dead-letter 2/8 และ unsettled 8/8",
    83: "เมื่อเทียบ static controls CF-Fit เพิ่ม completion 4.49–16.39 จุดเปอร์เซ็นต์และลด unsettled 26.15–57.39 จุด แต่เพิ่ม explicit dead-letter 17.50–35.84 จุด การไม่ผ่าน dead-letter margin จึงไม่ได้แปลว่าคุณภาพแย่ลงเพียงมิติเดียว เพราะ static หลายแบบปล่อยงานค้างที่ horizon ขณะที่ CF-Fit ทำให้งานเข้าสู่ terminal state มากขึ้น เมื่อเทียบ Central-Fit ผลต่างมีขนาดเล็กและผ่าน quality non-inferiority ทั้งหมด",
    85: "รูปที่ 6 ผลต่าง paired median ของ cost per verified task ใน RQ1 พร้อม seed-cluster bootstrap 95% CI ค่าติดลบเอื้อ CF-Fit",
    88: "รูปที่ 7 โปรไฟล์ trade-off เชิงพรรณนาของ RQ1 ทุกแกน normalize ภายใน resource regime เดียวให้ค่าสูงหมายถึงดีกว่า รูปนี้ไม่ใช่ composite score เชิงอนุมาน",
    90: "Radar chart ใช้ช่วยมองรูปแบบเท่านั้นและแสดงเหตุผลที่ไม่ควรประกาศผู้ชนะเพียงตัวเดียว CF-Fit และ Central-Fit ใกล้กันด้าน throughput, terminal time, completion และ unsettled ขณะที่ static controls แต่ละแบบเด่นคนละด้าน เช่น ต้นทุนหรือ dead-letter พื้นที่รูปหลายเหลี่ยมจึงไม่ใช้ทดสอบสมมติฐาน",
    91: "B. RQ2: ความหลากหลายของความสามารถ",
    92: "ตารางที่ III เปลี่ยน capability variance โดยไม่เปลี่ยน team size หรือ mean level H2−H0 เป็น boundary contrast ที่กำหนดล่วงหน้า ส่วน H1 ใช้ตรวจว่าผลค่อยเป็นค่อยไปหรือเกิดเฉพาะองค์ประกอบสุดขอบ R0 แยกผลของ capability composition และ R1 ทดสอบเมื่อ ability เชื่อมกับ speed/token/price",
    94: "ตารางที่ III ผลของ capability heterogeneity ภายใต้ CF-Fit",
    95: "* Holm-adjusted p<0.05 ค่าเปอร์เซ็นต์เป็น paired median difference เทียบกับ median ของ comparator",
    97: "จาก 6 contrasts CF-Fit ภายใต้ทีมด้านซ้ายมีต้นทุนต่ำกว่า 3/6 กรณี (มีนัยสำคัญ 2), throughput สูงกว่า 3/6 (มีนัยสำคัญ 3) และ P95 ต่ำกว่า 6/6 (มีนัยสำคัญ 6) เนื่องจากทิศทางเปลี่ยนตาม resource regime จึงไม่สามารถอ้างว่า heterogeneity มีผลดีแบบสากล",
    98: "P95 ที่ลดมากมีคำอธิบายแบบ competing risk: H0 มี median unsettled 0.342 ขณะที่ H1/H2 ไม่มี unsettled แต่มี explicit dead-letter สูงกว่า ใน R0 heterogeneity ลดต้นทุนประมาณ 5% แต่ throughput ลดเล็กน้อย ส่วน R1 ต้นทุนเพิ่ม 40–82% แลกกับ throughput เพิ่ม 2–5% Resource mapping จึงเป็น moderator สำคัญ",
    100: "รูปที่ 8 ผลของ controlled capability heterogeneity ต่อ verified throughput ใน RQ2",
    101: "C. RQ3: Contribution ขององค์ประกอบกลไก",
    102: "ผล full-minus-ablation ระบุว่าองค์ประกอบใดเปลี่ยน outcome ผล A3 ที่เล็กหรือไม่ significant ถูกเก็บและตีความว่า stand-down เป็น bounded refinement ไม่ใช่ต้นเหตุเพียงส่วนเดียวของพฤติกรรม ConveyorFlow",
    104: "ตารางที่ IV Mechanism ablations โดยทิศทางเป็น Full ลบ Ablation",
    105: "* Holm-adjusted p<0.05 ค่าเปอร์เซ็นต์เป็น paired median difference เทียบกับ median ของ comparator",
    107: "จาก 8 contrasts ระบบเต็มมีต้นทุนต่ำกว่า ablation 4/8 กรณี (มีนัยสำคัญ 4), throughput สูงกว่า 7/8 (มีนัยสำคัญ 6) และ P95 ต่ำกว่า 4/8 (มีนัยสำคัญ 4) ทิศทางของ full-minus-ablation ต้องตีความตามองค์ประกอบ ไม่ใช่รวมเป็นคะแนนเดียว",
    108: "Assessment เพิ่มต้นทุน 4.6–6.7% แต่เพิ่ม throughput และ completion พร้อมเปลี่ยน backlog ที่ horizon ราว 35–37 จุดให้มี terminal outcome Fit ลดต้นทุน 3.5–3.7% เพิ่ม throughput ราว 2.2% และลด P95 ราว 12% Stand-down แทบไม่เปลี่ยนต้นทุนหรือ throughput และทำให้ P95 แย่ลงเล็กน้อย Aging เพิ่ม completion 10.4–10.8 จุดและลด dead-letter ราว 12.4 จุด แต่เพิ่ม P95 77–86%",
    110: "รูปที่ 9 ผลด้านต้นทุนของ RQ3 ทิศทางเป็น full CF-Fit ลบแต่ละ ablation",
    111: "D. E4: Fallback เมื่อไม่มีผู้รับงาน",
    112: "การวิเคราะห์ fallback รวม mixed และ D3-heavy profiles และใช้ทั้ง H1 กับ AR1×4 stress team ต้องอ่าน terminal time ร่วมกับ dead-letter และ unsettled เพื่อหลีกเลี่ยง survivorship bias ส่วน F3 ใช้ central rescue จึงเป็น hybrid reference ไม่ใช่ decentralized baseline",
    114: "ตารางที่ V ผลของ fallback เริ่มต้น F2 ลบทางเลือก",
    115: "* Holm-adjusted p<0.05 ค่าเปอร์เซ็นต์เป็น paired median difference เทียบกับ median ของ comparator",
    117: "จาก 6 contrasts F2 มีต้นทุนต่ำกว่า 5/6 กรณี (มีนัยสำคัญ 4), throughput สูงกว่า 4/6 (มีนัยสำคัญ 4) และ P95 ต่ำกว่า 0/6 ผลจึงขึ้นกับว่าจะให้น้ำหนักการปิดสถานะและต้นทุน หรือความเร็วของ terminal disposition มากกว่า",
    118: "เมื่อเทียบ F0/F1 กลไก F2 ใช้เวลาปิดสถานะนานกว่า แต่ลดต้นทุนและ dead-letter อย่างมากพร้อมเพิ่ม verified throughput เมื่อเทียบ hybrid F3, F2 มีต้นทุนใกล้เคียงแต่ throughput ต่ำกว่า 3.7–5.7%, P95 สูงกว่า 9.6–12.2% และ dead-letter สูงกว่า 1.1–1.7 จุด นี่คือราคาที่วัดได้ของการรักษา decentralized no-volunteer handling",
    120: "รูปที่ 10 ผลต่าง dead-letter ของ F2 ลบทางเลือกภายใต้ no-volunteer stress",
    121: "E. การตรวจสอบความทนทาน",
    122: "คำนวณ resource-mapping effects ใหม่ภายใต้ reversed และ permuted R1 assignments พบ 10/14 metric-level effects มีนัยสำคัญหลัง Holm Annotation sensitivity รัน CF-Fit, S2 และ Central-Fit ใหม่ด้วย lower/upper role-vote mappings บน medium/high load แม้ absolute level เปลี่ยน แต่ทิศทางหลักของ policy contrasts ไม่กลับขั้ว จึงควรรายงาน mapping เป็น moderator ไม่ใช่อ้าง invariance",
    123: "F. มุมมอง Pareto และ Competing Risk แบบ Secondary",
    124: "Pareto frontier ด้าน cost-throughput มี Central-Fit, Static AR1-only และ Static round-robin ใน R0 และ Central-Fit, Static AR3-only กับ Static round-robin ใน R1 CF-Fit ไม่อยู่บน economic frontier เพราะ Central-Fit มีต้นทุนต่ำกว่าและ throughput สูงกว่าเล็กน้อย สำหรับ P95-completion, Central-Fit เป็น frontier เดียวใน R0 ขณะที่ R1 มีทั้ง CF-Fit และ Central-Fit เพราะ CF-Fit เร็วกว่าเล็กน้อยแต่ completion ต่ำกว่าเล็กน้อย Frontier จึงเปลี่ยนตาม objective pair",
    127: "รูปที่ 11 Pareto frontier เชิงพรรณนาสองวัตถุประสงค์ของ RQ1 จุดทึบคือ nondominated ภายในคู่ metric ที่แสดง โดยไม่มีการถ่วงน้ำหนักข้าม metric",
    129: "รูปที่ 12 Run-level Aalen–Johansen cumulative incidence ของ verified และ dead-letter เส้นคือ median จาก 450 runs และพื้นที่เงาคือช่วงเปอร์เซ็นไทล์ 2.5–97.5 ของ runs ไม่ใช่ confidence interval",
    131: "ที่ 1,000 ticks ค่า median verified cumulative incidence ของ CF-Fit เทียบ Central-Fit เท่ากับ 0.590 ต่อ 0.602 ใน R0 และ 0.615 ต่อ 0.621 ใน R1 ส่วน dead-letter เท่ากับ 0.410 ต่อ 0.396 และ 0.382 ต่อ 0.378 ตามลำดับ Static policies อาจมี terminal flow time สั้นแต่มี unresolved mass สูงกว่า จึงต้องอ่าน speed ร่วมกับ event probability",
    132: "G. การปรับเทียบ Ability ก่อนการทดลอง Real LLM",
    133: "การ calibration ก่อน Main เรียก MFEC deployment aliases ด้วย held-out probes 30 รายการต่อโมเดลที่คัดกรอง ขั้นนี้ไม่ได้รันหรือเปรียบเทียบ allocation policy Ability ถูกจัดแยกตาม workload ด้วย Wilson lower-95% gates ที่ประกาศก่อน ภายใต้ completion-token budget 4,096 เท่ากัน โดยไม่ใช้ชื่อโมเดล ราคา latency หรือ token use ในการจัด rank Stopping rule เลือกทีมสาม Agent ที่ profile ต่างกันก่อนรันนโยบาย ได้แก่ Tencent HY3 (ML Rank 3/Fix Rank 1), GPT-5 mini (ML Rank 2/Fix Rank 3) และ GLM 5.3 Flash (ML Rank 3/Fix Rank 3) Rank เหล่านี้เป็น operational rank ของ MFEC aliases ณ เวลาทดลอง ไม่ใช่อันดับสากลของ model family",
    136: "รูปที่ 13 โปรไฟล์ pass rate เชิงพรรณนาที่ใช้เลือกทีมก่อน Main พื้นที่ radar ไม่ใช่ composite score และ ordinal rank ใช้ confidence-bound gates ที่กำหนดล่วงหน้า",
    138: "การแก้เครื่องมือ calibration ถูกบันทึกครบ: แทน exact-match repair ที่ execute ไม่ได้ด้วย hidden executable tests และแก้ adapter cap 1,024 token โดยรันซ้ำเฉพาะ cell ที่จบเพราะความยาวภายใต้ budget 4,096 เดิม การแก้เกิดก่อนเลือกทีมและไม่เปลี่ยน gate หรือ probe ที่ผ่านแล้ว",
    139: "H. การตรวจสอบการจัดสรรด้วย Real LLM เพิ่มเติม",
    140: "การศึกษา Real LLM ใช้ทีมสาม Agent ที่เลือกไว้ executable cases 60 กรณี deterministic validators และ 10 paired seeds ผู้ชนะ atomic claim ถูก execute ครั้งละหนึ่งงานต่อ Agent แต่ Agent ต่างตัวรันพร้อมกันโดยไม่มี round barrier Provider failure ที่เกิน retry ทำให้ policy run ไม่สมบูรณ์ ไม่ถูกนับเป็น task-quality failure การศึกษานี้เป็น supplementary validation ส่วน simulation 22,500 runs ยังคงเป็น confirmatory causal analysis",
    142: "ตารางที่ VI ผล Real LLM เชิงพรรณนาจาก 10 paired seeds",
    144: "จาก 10 paired seeds CF-Fit ทำสำเร็จ 41.17% ใช้ wall time เฉลี่ย 284.58 วินาที verified throughput 0.08855 งาน/วินาที utilization 89.88% และ cost per verified task $0.005095 Static S3 ทำสำเร็จ 54.67% ที่ 0.04440 งาน/วินาทีและ $0.003143 ต่อ verified task ส่วน Central-Fit ทำสำเร็จ 41.83% ที่ 0.08966 งาน/วินาทีและ $0.004972 ต่อ verified task ค่าดังกล่าวแสดงระดับเชิงปฏิบัติการก่อน paired inference",
    145: "เมื่อเทียบ static round robin, CF-Fit เปลี่ยน completion −13.50 จุดเปอร์เซ็นต์และ cost per verified task +62.08% ขณะที่ wall time −62.10%, throughput +99.45% และ utilization +63.57% การเปรียบเทียบ metric ทั้งหกมีนัยสำคัญหลัง Holm (adjusted p=0.005859) ผลนี้คือ trade-off ระหว่าง speed/utilization กับ completion/cost ไม่ใช่ Pareto superiority",
    146: "CF-Fit และ Central-Fit ให้ค่าพรรณนาใกล้กันภายใต้ทีมที่เลือก และไม่มีการเปรียบเทียบทั้งหก metric ที่ถึง Holm-adjusted p<0.05 (ค่าต่ำสุด 0.105469) ผลนี้ไม่พิสูจน์ equivalence แต่ระบุเพียงว่าการศึกษาเสริม 10 seeds ยังตรวจไม่พบความแตกต่างที่เกณฑ์กำหนด",
    149: "รูปที่ 14 โปรไฟล์ Real LLM เชิงพรรณนา แต่ละแกน min-max normalize ภายในสาม policy ให้ค่าสูงหมายถึงดีกว่า Radar ไม่ใช่ composite score เชิงอนุมาน",
    151: "I. Real LLM Extension: Stand-Down และองค์ประกอบทีม",
    152: "Extension ที่ freeze แยกต่างหากเพิ่ม single-component ablation หนึ่งแบบและ homogeneous boundary conditions สองแบบ HET_NO_STANDDOWN คง decentralized self-selection, eligibility, fit, aging, retry และ requeue แต่ตัด stand-down HOM_GLM_GENERALIST ทำซ้ำโปรไฟล์ GLM Rank-3/Rank-3 ทั้งสาม slot และ HOM_GPT_PROFILE ทำซ้ำ GPT ML-Rank-2/Fix-Rank-3 ทีม homogeneous เหล่านี้เป็น ecological boundaries ไม่ใช่ causal controls ที่คุม mean ability หลักฐาน RQ2 แบบคุม mean ability จึงยังอยู่ที่ simulation",
    154: "ตารางที่ VII ผล Real LLM ของ Stand-Down Ablation และ Homogeneous Boundary",
    156: "สำหรับ primary extension outcomes, HET_FULL และ HET_NO_STANDDOWN ทำสำเร็จ 41.17% เท่ากัน โดย cost per verified task เฉลี่ย $0.005095 และ $0.005159 ตามลำดับ HOM_GLM_GENERALIST ทำสำเร็จ 86.67% ที่ $0.000889 ต่อ verified task ขณะที่ HOM_GPT_PROFILE ทำสำเร็จ 28.83% ที่ $0.007305 ผลของ homogeneous สองแบบที่ตรงข้ามกันแสดง model-specific boundary behavior แต่ไม่ระบุ causal effect ของ team homogeneity",
    157: "เมื่อตัด stand-down completion เปลี่ยน −0.00 จุดเปอร์เซ็นต์และ cost per verified task +1.25% ส่วน wall time, throughput และ utilization ข้าม execution window เปลี่ยน +6.70%, −5.40% และ −0.98% ตามลำดับ หลัง Holm ไม่มี outcome ใดมีนัยสำคัญ",
    158: "Homogeneous GLM boundary เปลี่ยน completion +45.50 จุดเปอร์เซ็นต์และ cost per verified task −82.55% ส่วน wall time, throughput และ utilization ข้าม window เปลี่ยน +144.45%, −9.83% และ −28.43% ตามลำดับ หลัง Holm ผลที่มีนัยสำคัญคือ completion, total cost, cost per verified task และ utilization",
    159: "Homogeneous GPT boundary เปลี่ยน completion −12.33 จุดเปอร์เซ็นต์และ cost per verified task +43.39% ส่วน wall time, throughput และ utilization ข้าม window เปลี่ยน −54.91%, +51.22% และ +5.78% ตามลำดับ หลัง Holm completion, total cost, cost per verified task, wall time และ throughput มีนัยสำคัญ",
    160: "Extension รันหลัง HET_FULL จึงไม่ได้สุ่ม provider load และ network condition ข้าม execution windows หลักฐานเสริมหลักคือ completion, cost และ allocation events ซึ่งมี 10 paired seeds ต่อ condition ส่วน wall time, throughput และ utilization เป็น exploratory โดย timing-valid sample เท่ากับ 10 สำหรับ HET_FULL/HET_NO_STANDDOWN, 8 สำหรับ HOM_GLM และ 9 สำหรับ HOM_GPT หลังใช้ frozen provider-gap rule การตัด timing สามรายการไม่ตัดข้อมูล completion/cost ความล้มเหลวจาก Windows path length และการหยุดตามคำขอผู้ใช้ถูกเก็บเป็น infrastructure-invalid/partial ledger และรันใหม่ด้วย scientific parameter เดิม",
    163: "รูปที่ 15 โปรไฟล์ sensitivity ของ Real LLM สำหรับ stand-down ablation และ homogeneous boundary การ normalize ต่อแกนใช้เพื่อการมองภาพเท่านั้น และ timing axes ที่เปรียบเทียบข้าม window เป็น exploratory",
    165: "VII. อภิปรายผล",
    166: "ผลควรถูกอ่านเป็นแผนที่ trade-off แบบ Pareto ConveyorFlow ได้รับการสนับสนุนเมื่อ local self-selection ให้ส่วนผสม cost–throughput–time ที่ใช้ได้จริงโดยยังอยู่ใน completion และ terminal-failure margins ไม่จำเป็นต้องชนะ centralized หรือ static control ทุกด้าน การรายงานแยก resource regime จำเป็น เพราะกลไกที่สำรอง Agent ความสามารถสูงอาจให้ผลเศรษฐศาสตร์ต่างกันเมื่อความสามารถมีหรือไม่มีต้นทุนสูง",
    167: "การทดลอง heterogeneity แยก diversity ออกจาก average team strength เพราะ H0, H1 และ H2 มี mean latent ability เท่ากัน ความต่างจึงเกิดจาก composition และ task matching ไม่ใช่เพียงเพิ่ม Agent ที่เก่งกว่า Ablation ยังแยก contribution ของ noisy local assessment, fit ranking, temporary overqualification stand-down และ task aging",
    168: "ในเชิงปฏิบัติ stand-down ไม่ควรถูกอธิบายว่าเป็นการปฏิเสธงาน แต่เป็น backoff ที่ลดลงตามเวลา เพื่อสำรอง scarce capability ช่วงต้นและหายไปเมื่องานเร่งด่วน Aging กับ bounded dead-letter จึงเป็นส่วนของ safety story ที่ป้องกันไม่ให้งานง่ายถูกเลื่อนตลอดเมื่อ Agent ระดับต่ำไม่พร้อม",
    169: "การรัน MFEC เป็น implementation check เสริม ไม่แทนที่ simulation ที่ควบคุม เมื่อเทียบ Static S3, CF-Fit ทำสำเร็จน้อยกว่าและจ่ายต่อ verified task มากกว่า แต่จบ workload window เร็วกว่าและมี throughput/utilization สูงกว่า เมื่อเทียบ Central-Fit ยังไม่พบ metric-level contrast ที่มีนัยสำคัญใน 10 seeds ซึ่งเป็น absence of detected difference ไม่ใช่ equivalence Extension ตรวจ sensitivity ต่อการตัด stand-down และ homogeneous deployments สองแบบ แต่เนื่องจากโมเดลเปลี่ยนทั้ง capability profile และ provider behavior เงื่อนไขเหล่านี้จึงเป็น deployment boundary ไม่ใช่การแยก causal effect ของ heterogeneity ที่สะอาดเท่า simulation",
    170: "Pareto และ competing-risk views ช่วยทำให้ข้อสรุปเดิมคมขึ้นโดยไม่ขยาย claim ทั้งสองแสดงว่าการจัดอันดับเดียวไม่คงที่เมื่อเปลี่ยน objective pair และ terminal latency ต้องอ่านร่วมกับโอกาส verified, dead letter และ censoring เนื่องจากเพิ่มหลังดู confirmatory result จึงเป็นหลักฐานเพื่อการตีความและการ preregister ในอนาคต ไม่ใช่ confirmatory claim ใหม่",
    171: "VIII. ภัยคุกคามต่อความเที่ยงตรง",
    172: "Construct validity ถูกจำกัดด้วยฟังก์ชันจำลอง success, time, token, assessment และ cost Ability rank แทน behavioral envelope ที่ปรับเทียบ ไม่ใช่ model version เฉพาะ ข้อมูลสาธารณะกำหนดการกระจาย workload แต่ simulation task ไม่เท่ากับการทำโครงการ ML หรือซ่อม repository จริง และ CodeXGLUE pairs ไม่ได้ execute เป็น repository tests ในงานนี้",
    173: "Difficulty labels มาจากสาม role-conditioned passes ของ LLM พื้นฐานตัวเดียวและ adjudication หนึ่งรอบ วิธีนี้เพิ่ม reproducibility แต่ไม่สร้าง human-expert validity หรือ rater independence ค่า Beijing subgroup κ=0.628 เป็นข้อจำกัดเฉพาะที่ Alternate mappings ช่วยกำหนดขอบ sensitivity แต่ไม่กำจัดข้อกังวลนี้",
    174: "Internal validity แข็งแรงขึ้นจาก frozen seeds, common random numbers, keyed potential outcomes, immutable event ledger, source/artifact hashes และไม่มี outcome-based exclusion อย่างไรก็ตาม logistic ability curve, load process, scan window, aging thresholds, retry limit และขีดจำกัดสี่ Agent อาจมีปฏิสัมพันธ์กัน External validity จำกัดอยู่ในสถาปัตยกรรมและช่วงที่ทดสอบ หลักฐาน Real LLM ใช้ 10 paired seeds, 60 task bundles, endpoint เดียว และ dated provider aliases ไม่ใช่ immutable model versions ที่ตรวจสอบอิสระ Provider latency/load เปลี่ยนได้ และ main กับ extension ไม่ได้สุ่มข้ามเวลา จึงถือ timing contrast ข้าม window เป็น exploratory Homogeneous teams ยังปะปน composition กับ model-specific behavior งานอนาคตคือ human validation, providers/team sizes เพิ่มเติม และ communication-failure sensitivity",
    175: "Live validators ยืนยัน task-specific functional success สำหรับ ML-build และ bug-fix bundles ที่เลือก แต่ไม่ครอบคลุม semantic, security, maintainability หรือ production-quality ทุกด้าน จำนวน 10 seeds ให้ paired sensitivity evidence ที่มีประโยชน์แต่ไม่ใช่ population estimate ขั้นเด็ดขาด ความล้มเหลวจาก path length ก่อนเกิด summary ถูกเก็บเป็น infrastructure-invalid และรันใหม่หลังแก้ wrapper เฉพาะ path โดยไม่เปลี่ยน parameter, seed, model, task, validator หรือ analysis rule",
    176: "Competing-risk envelopes สรุปความกระจายระหว่าง runs ไม่ใช่ sampling uncertainty และ right-censoring ที่ fixed horizon สมมติว่าจะไม่จัดประเภท unresolved work ใหม่หลังจบการสังเกต Pareto frontier ขึ้นกับวัตถุประสงค์สองแกนที่เลือกและจะเปลี่ยนเมื่อ objective set เปลี่ยน ทั้งสองการวิเคราะห์จึงระบุเป็น secondary อย่างชัดเจน",
    177: "IX. สรุป",
    178: "ConveyorFlow ปรับกรอบการจัดสรรงานของทีม LLM Agent ที่มีความหลากหลายให้เป็น decentralized capability-aware self-selection บนสายพาน READY เรื่องราวเชิงวิทยาศาสตร์เชื่อม local decision authority, capability heterogeneity, fit, temporary stand-down และ aging การจำลองที่กำหนดล่วงหน้า 22,500 unique runs ประเมิน trade-off เทียบ static และ centralized controls โดยไม่อ้าง universal dominance Real LLM ที่รันเสร็จและ safety-lock แล้วเพิ่มหลักฐานระดับ implementation โดยพบ trade-off ที่ชัดเจนระหว่าง speed/utilization กับ completion/cost เทียบ static ขณะที่ decentralized และ centralized fit ยังแยกไม่ออกด้วย 10 paired seeds Extension ของ stand-down และ homogeneous teams เป็น sensitivity/deployment-boundary evidence ไม่ได้แทน controlled causal comparison ของ simulation ส่วน human validation ของ task difficulty ยังแยกไว้และรอดำเนินการ",
    179: "การเข้าถึงข้อมูลและโค้ด",
    180: "แพ็กเกจวิจัย v2 มี source code, frozen configurations, public-data manifests, annotation packets/prompts, event-ledger hashes, analysis scripts, secondary outputs, pre-execution source snapshot และ protocol/harness ของ Real LLM ที่ไม่ผูก vendor ไฟล์ ConveyorFlow_diagrams_en_working.drawio มี source ที่แก้ไขได้ของรูป 1–5 พร้อม calibration/execution ledgers, team-selection evidence, immutable config/case hashes, validated manifests, statistical summaries, figures และบันทึก path-only deviation ของ extension Provider aliases และราคาเป็น observed metadata ณ เวลาทดลอง ไม่ควรตีความว่าเป็น model lineage ที่ตรวจสอบอิสระ Raw CodeXGLUE files ยังอยู่ภายใต้ upstream license และควรเพิ่ม public archival DOI หลังอาจารย์อนุมัติและเผยแพร่ repository",
    181: "เอกสารอ้างอิง",
}


CELL_TRANSLATIONS = {
    "Block": "ส่วนทดลอง",
    "Policies / factors": "นโยบาย / ปัจจัย",
    "Team": "ทีม",
    "Load": "โหลด",
    "Resource": "ทรัพยากร",
    "Memberships": "จำนวนสมาชิก",
    "controlled mean": "คุมค่าเฉลี่ย",
    "low/med/high": "ต่ำ/กลาง/สูง",
    "med/high": "กลาง/สูง",
    "specified": "ตามที่กำหนด",
    "Sensitivity": "Sensitivity",
    "Regime": "เงื่อนไข",
    "Comparator": "ตัวเปรียบเทียบ",
    "Cost": "ต้นทุน",
    "Throughput": "Throughput",
    "P95 time": "เวลา P95",
    "Completion NI": "Completion NI",
    "Dead NI": "Dead-letter NI",
    "Unsettled NI": "Unsettled NI",
    "Yes": "ผ่าน",
    "No": "ไม่ผ่าน",
    "Contrast": "คู่เปรียบเทียบ",
    "Completion delta": "ผลต่าง Completion",
    "95% CI (completion)": "95% CI (Completion)",
    "Full-ablation": "Full–Ablation",
    "Cost 95% CI": "95% CI (ต้นทุน)",
    "Dead-letter delta": "ผลต่าง Dead-letter",
    "Unsettled delta": "ผลต่าง Unsettled",
    "MFEC alias": "MFEC alias",
    "ML Build": "ML Build",
    "Fix Bug": "Fix Bug",
    "Operational role": "บทบาทเชิงปฏิบัติการ",
    "Rank 3": "Rank 3",
    "Rank 2": "Rank 2",
    "Rank 1": "Rank 1",
    "ML specialist / basic repair": "เชี่ยวชาญ ML / ซ่อมพื้นฐาน",
    "Intermediate ML / advanced repair": "ML ระดับกลาง / ซ่อมขั้นสูง",
    "Advanced generalist": "Generalist ขั้นสูง",
    "Condition": "เงื่อนไข",
    "N (primary/timing)": "N (primary/timing)",
    "Completion": "Completion",
    "Cost / verified": "ต้นทุน / verified",
    "Wall time (s)": "Wall time (วินาที)",
    "Throughput / s": "Throughput / วินาที",
    "Utilization": "Utilization",
    "Static round robin": "Static round robin",
    "Heterogeneous full CF-Fit": "ทีมต่างระดับ: CF-Fit เต็ม",
    "Heterogeneous without stand-down": "ทีมต่างระดับ: ไม่มี stand-down",
    "Homogeneous GLM": "ทีมเหมือนกัน: GLM",
    "Homogeneous GPT": "ทีมเหมือนกัน: GPT",
}


def replace_paragraph_text(paragraph, text: str, font_size: float | None = None) -> None:
    old_runs = list(paragraph.runs)
    old_size = next((run.font.size for run in old_runs if run.font.size), None)
    old_bold = next((run.bold for run in old_runs if run.bold is not None), None)
    old_italic = next((run.italic for run in old_runs if run.italic is not None), None)
    for run in old_runs:
        paragraph._p.remove(run._r)
    run = paragraph.add_run(text)
    run.font.name = THAI_FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), THAI_FONT)
    run.font.size = Pt(font_size) if font_size else old_size
    run.bold = old_bold
    run.italic = old_italic


def format_labeled_paragraph(paragraph, label: str, body: str) -> None:
    for run in list(paragraph.runs):
        paragraph._p.remove(run._r)
    label_run = paragraph.add_run(label)
    body_run = paragraph.add_run(body)
    for run in (label_run, body_run):
        run.font.name = THAI_FONT
        run._element.rPr.rFonts.set(qn("w:eastAsia"), THAI_FONT)
        run.font.size = Pt(9)
    label_run.bold = True
    label_run.italic = True


def translate_table_cell(cell) -> None:
    text = " ".join(cell.text.split())
    translated = CELL_TRANSLATIONS.get(text, text)
    if not cell.paragraphs:
        return
    replace_paragraph_text(cell.paragraphs[0], translated, 7.5)
    for paragraph in cell.paragraphs[1:]:
        replace_paragraph_text(paragraph, "", 7.5)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(deepcopy(tc_pr[-1])) if False else None


def main() -> int:
    if not SOURCE.exists():
        raise SystemExit(f"missing source manuscript: {SOURCE}")
    doc = Document(SOURCE)
    expected_nonempty = {i for i, p in enumerate(doc.paragraphs) if p.text.strip() and i < 182}
    missing = sorted(expected_nonempty - set(THAI_PARAGRAPHS))
    unexpected = sorted(set(THAI_PARAGRAPHS) - set(range(len(doc.paragraphs))))
    if missing or unexpected:
        raise SystemExit(f"translation/source mismatch: missing={missing}, unexpected={unexpected}")

    for index, text in THAI_PARAGRAPHS.items():
        paragraph = doc.paragraphs[index]
        size = 18 if index == 0 else None
        replace_paragraph_text(paragraph, text, size)

    abstract_label, abstract_body = THAI_PARAGRAPHS[3].split("—", 1)
    format_labeled_paragraph(doc.paragraphs[3], abstract_label + "—", abstract_body)
    keyword_label, keyword_body = THAI_PARAGRAPHS[4].split("—", 1)
    format_labeled_paragraph(doc.paragraphs[4], keyword_label + "—", keyword_body)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                translate_table_cell(cell)

    for section in doc.sections:
        for container in (section.header, section.footer):
            for paragraph in container.paragraphs:
                for run in paragraph.runs:
                    run.font.name = THAI_FONT
                    run._element.rPr.rFonts.set(qn("w:eastAsia"), THAI_FONT)

    doc.core_properties.title = "ConveyorFlow — Manuscript ฉบับภาษาไทย"
    doc.core_properties.author = "Sakan Punyanon"
    doc.core_properties.subject = "ฉบับภาษาไทยสำหรับอาจารย์ตรวจเนื้อหา; ผลและโครงสร้างตรงกับ manuscript ภาษาอังกฤษ"
    doc.core_properties.comments = (
        "ฉบับภาษาไทยใช้สำหรับการตรวจและนำเสนอภายใน ส่วนฉบับภาษาอังกฤษเป็นต้นฉบับสำหรับส่งวารสาร"
    )
    doc.save(OUTPUT)
    print(f"created {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
