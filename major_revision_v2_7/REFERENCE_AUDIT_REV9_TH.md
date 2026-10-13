# Reference audit — ConveyorFlow v2.7 Rev9 (13 October 2026)

## ผลตรวจและเกณฑ์ที่ใช้

ตรวจต้นฉบับ IEEE, AJSTR blind และ AJSTR unblind ฉบับ `Rev9_ReferencesVerified` เทียบกับหน้าผู้จัดพิมพ์/คลังประชุม/เจ้าของชุดข้อมูล ไม่ใช้รายการที่ส่งมาเป็นหลักฐานในตัวเอง. อ้างอิงในต้นฉบับทั้ง 26 รายการมีผลงานจริงและมีแหล่งตรวจสอบได้; ไม่พบรายการที่แต่งขึ้นใน **รายการที่ใส่ใน Rev9**. การตรวจนี้ยืนยันตัวตนของงานและ metadata บรรณานุกรม ไม่ได้ยืนยันผลเชิงประจักษ์ของ ConveyorFlow เพิ่มเติม.

AJSTR [Author Guidelines](https://ph02.tci-thaijo.org/index.php/tsujournal/Author) กำหนดเลขอ้างอิงตามลำดับปรากฏ, `[n]` ก่อนเครื่องหมายวรรคตอน, รายการแบบ ACS, DOI เมื่อมี. Rev9 ผ่านการตรวจเชิงโครงสร้างเหล่านี้: [1]–[26] ปรากฏในเนื้อหาตามลำดับและมีรายการครบ, ไม่พบ citation วางหลังเครื่องหมายจบประโยค, เติม DOI ที่ขาดให้ Cohen/Wilcoxon/Efron, และแก้รายการที่มีผู้แต่งเกิน 10 คนให้ระบุ 10 คนแรกก่อน `et al.` ตาม [ACS guidance](https://researcher-resources.acs.org/publish/author_guidelines/pdf?coden=aelccp). ภาพฝังทุกภาพมี hash ตรงกับ Rev7; จำนวนรูป/สมการ/ตารางไม่เปลี่ยน.

**ความขัดกันของคำแนะนำวารสาร:** หน้า [Submission](https://ph02.tci-thaijo.org/index.php/tsujournal/Submission) ระบุ APA7 แต่หน้า Author Guidelines และ [ตัวอย่าง AJSTR](https://ph02.tci-thaijo.org/index.php/tsujournal/Author) ใช้ ACS/เลขอ้างอิง. Rev9 ยึด Author Guidelines และตัวอย่างบทความ; ก่อนส่งจริงควรขอคำยืนยันจาก editorial office. หน้า Submission ยังระบุ research article ไม่เกิน 8,000 คำรวม references; Rev9 AJSTR มีประมาณ 13,655 คำ (blind) และ 13,727 คำ (unblind) เมื่อรวมคำในตาราง จึง **ยังไม่ผ่านข้อกำหนดความยาว**. ต้องย่อบทความ/ย้ายรายละเอียดบางส่วนไป Supplementary Materials โดยรักษารูปที่ผู้เขียนต้องการ และเปิดตรวจทุกหน้าใน Microsoft Word. ไม่ได้อ้างว่า Rev9 ผ่าน page-layout QA.

## หลักฐานแหล่งจริงของรายการใน Rev9

| เลข | งาน (ย่อ) | แหล่งที่ตรวจ |
|---|---|---|
| 1 | AutoGen (2024) | [COLM/OpenReview paper](https://openreview.net/pdf?id=BAakY1hNKS) |
| 2 | MetaGPT (2024) | [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/6507b115562bb0a305f1958ccc87355a-Abstract-Conference.html) |
| 3 | ChatDev (2024) | [ACL Anthology](https://aclanthology.org/2024.acl-long.810/) |
| 4 | CAMEL (2023) | [NeurIPS proceedings](https://proceedings.neurips.cc/paper/2023/hash/a3621ee907def47c1b952ade25c67698-Abstract-Conference.html) |
| 5 | AgentVerse (2024) | [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/578e65cdee35d00c708d4c64bce32971-Abstract-Conference.html) |
| 6 | Guo et al., multi-agent survey (2024) | [IJCAI proceedings](https://www.ijcai.org/proceedings/2024/890) |
| 7 | Contract Net (1980) | [IEEE Xplore](https://ieeexplore.ieee.org/document/1675516) |
| 8 | Gerkey–Matarić taxonomy (2004) | [SAGE](https://journals.sagepub.com/doi/10.1177/0278364904045564) |
| 9 | Korsah et al. taxonomy (2013) | [SAGE](https://journals.sagepub.com/doi/10.1177/0278364913496484) |
| 10 | Choi et al. auction (2009) | [IEEE Xplore](https://ieeexplore.ieee.org/document/5072249/) |
| 11 | G-Eval (2023) | [ACL Anthology](https://aclanthology.org/2023.emnlp-main.153/) |
| 12 | Chiang–Lee evaluation (2023) | [ACL Anthology](https://aclanthology.org/2023.findings-emnlp.599/) |
| 13 | Chen et al. judge bias (2024) | [ACL Anthology](https://aclanthology.org/2024.emnlp-main.474/) |
| 14 | UCI Adult (1996) | [UCI data record](https://archive.ics.uci.edu/dataset/2/adult) |
| 15 | UCI Beijing Multi-Site Air Quality (2017) | [UCI data record](https://archive.ics.uci.edu/dataset/501/beijing) |
| 16 | CodeXGLUE (2021) | [NeurIPS Datasets and Benchmarks](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/c16a5320fa475530d9583c34fd356ef5-Abstract-round1.html) |
| 17 | Cohen weighted kappa (1968) | [PubMed/DOI](https://pubmed.ncbi.nlm.nih.gov/19673146/) |
| 18 | Wilcoxon rank method (1945) | [JSTOR issue record](https://www.jstor.org/stable/i350470) |
| 19 | Efron bootstrap (1979) | [Project Euclid/DOI](https://doi.org/10.1214/aos/1176344552) |
| 20 | Holm sequential testing (1979) | [JSTOR issue record](https://www.jstor.org/stable/i412579) |
| 21 | BugsInPy (2020) | [SMU institutional record with ACM DOI](https://smusg.elsevierpure.com/en/publications/bugsinpy-a-database-of-existing-bugs-in-python-programs-to-enable/) |
| 22 | Abuhaimed–Sen allocation (2022) | [SAGE/IOS Press record](https://journals.sagepub.com/doi/abs/10.3233/FAIA220197) |
| 23 | MasRouter (2025) | [ACL Anthology](https://aclanthology.org/2025.acl-long.757/) |
| 24 | ReSo (2025) | [ACL Anthology](https://aclanthology.org/2025.emnlp-main.808/) |
| 25 | MLAgentBench (2024) | [PMLR/ICML proceedings](https://proceedings.mlr.press/v235/huang24y.html) |
| 26 | SWE-bench (2024) | [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/edac78c3e300629acfe6cbe9ca88fb84-Abstract-Conference.html) |

## การคัดจาก `References.docx` ที่ผู้เขียนส่งมา

- **เพิ่มหลังแก้ข้อมูล:** Abuhaimed–Sen เป็นงาน HHAI **2022**, DOI `10.3233/FAIA220197`, ไม่ใช่ 2024/`10.3233/FAIA240115`. DOI เดิมในไฟล์ชี้ไปบทความเรื่องอาคารประหยัดพลังงาน [ดูหน้าผู้จัดพิมพ์](https://journals.sagepub.com/doi/abs/10.3233/FAIA240115). ใช้เป็นหลักฐานว่า *ตัวผู้จัดสรรงาน* สำคัญในทีมมนุษย์–agent เท่านั้น ไม่อ้างว่าเป็นผลของทีม LLM.
- **มีอยู่แล้วและแก้ metadata:** AutoGen ใช้บทความหลัก COLM 2024 ชื่อจบด้วย **Conversations** (พหูพจน์) ไม่ใช่ workshop/Conversation ในไฟล์ส่งมา. Contract Net มีอยู่แล้ว; ชื่อฉบับ IEEE จริงคือ “...Distributed Problem Solver” ไม่ใช่ “...Processor Architecture”.
- **ตรวจพบว่ามีจริงแต่ไม่เพิ่มเพราะไม่ตรงคำถามหลักหรือซ้ำ:** Wang et al. survey (2024) ซ้ำบทบาทกับ survey [6]; Javadpour et al. (2024) เป็น blockchain/cloud IoT ไม่ใช่ LLM volunteer allocation; Wu–Schranz (2026) เป็น edge–fog–cloud resource scheduling. การไม่เพิ่มช่วยให้ Related Work ไม่กลบ contribution เรื่อง local choice + fit + stand-down.
- **ไม่เพิ่มเพราะข้อมูล DOI/ชื่อ/ปีที่ให้มาตรวจไม่ลงตัวหรือยังยืนยันกับแหล่งหลักไม่ได้:** Ding–Fan, Kim et al., Zhou et al., Asani et al., TickIt และรายการ 2026 ที่เหลือ. ไม่ถือว่าทุกชิ้นเป็นงานปลอม แต่ห้ามคัดลอก citation จากไฟล์นั้นเข้าต้นฉบับโดยไม่ตรวจใหม่.
- **ไม่เพิ่มเพราะเป็นคนละโจทย์หรือเก่ากว่า 5 ปี:** FinQA, TriviaQA, JFLEG, HotpotQA, Q-learning, network scaling, epidemic algorithms, cloud load balancing และอื่น ๆ. งานคลาสสิกที่จำเป็นต่อทฤษฎียังอยู่ในอ้างอิงเดิม [7]–[10], [17]–[20].

งานใหม่จากการค้นเพิ่ม [23]–[26] ใช้เพื่อเปรียบขอบเขตกับงาน routing/self-organization และชี้ข้อจำกัดเรื่อง ML/repository task แบบ executable; **ไม่ได้ใช้เป็น baseline ที่รันทดลองโดย ConveyorFlow**. งานทั้ง 5 ที่เพิ่มอยู่ในช่วงปี 2022–2025.

## สิ่งที่ต้องตรวจต่อก่อนส่ง

1. ยืนยัน ACS เทียบ APA7 กับ AJSTR editorial office เพราะสองหน้าทางการไม่ตรงกัน.
2. ย่อ AJSTR ให้ผ่าน 8,000 คำโดยไม่ทิ้งรูปสำคัญ และตรวจว่ารูป/ตาราง/สมการ/อ้างอิงยังตรงกันหลังย่อ.
3. ตรวจเลย์เอาต์และ hyperlink ทุกหน้าใน Microsoft Word; Rev9 ยังไม่ได้ page QA.
4. ให้ผู้เขียนทุกคนตรวจและอนุมัติฉบับสุดท้าย รวมทั้ง funding/contributions และอัปเดต GitHub frozen commit เมื่อ code/diagram ล่าสุด push แล้ว.
