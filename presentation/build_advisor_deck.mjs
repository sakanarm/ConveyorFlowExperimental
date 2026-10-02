import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.env.WORKSPACE_DIR;
const SKILL_DIR = process.env.SKILL_DIR;
const TMP_DIR = process.env.TMP_DIR;
const FINAL_PPTX = process.env.FINAL_PPTX;
const RUNTIME_PYTHON = process.env.RUNTIME_PYTHON;
if (![workspaceDir, SKILL_DIR, TMP_DIR, FINAL_PPTX, RUNTIME_PYTHON].every(Boolean)) {
  throw new Error("WORKSPACE_DIR, SKILL_DIR, TMP_DIR, FINAL_PPTX, and RUNTIME_PYTHON are required");
}

const { finalizePresentation, makeNativeBulletParagraphs } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href,
);

const W = 1280;
const H = 720;
const FONT = "Leelawadee UI";
const C = {
  navy: "#15324C",
  navy2: "#244B68",
  teal: "#0D6F78",
  tealLight: "#DDEFF0",
  orange: "#D77A36",
  orangeLight: "#F5E4D6",
  ink: "#17212B",
  muted: "#52616D",
  light: "#F7F5F0",
  white: "#FFFFFF",
  grid: "#D5DEE4",
  green: "#527A57",
  red: "#A4493D",
};

const ROOT = path.join(workspaceDir, "v2");
const FIG = path.join(ROOT, "results", "main", "figures");
const ABILITY_FIG = path.join(ROOT, "real_llm_pilot", "figures", "fig_ability_profile_radar.png");
const REAL_LLM_FIG = path.join(ROOT, "real_llm_pilot", "figures");
const MAIN_REAL_LLM_RADAR = path.join(REAL_LLM_FIG, "fig_real_llm_main_radar.png");
const EXTENSION_REAL_LLM_RADAR = path.join(REAL_LLM_FIG, "fig_real_llm_extension_radar.png");
const EXTENSION_PAIRWISE = path.join(ROOT, "real_llm_pilot", "extension_mfec_aggregated", "extension_pairwise.csv");
const DRAWIO_EXPORT = path.join(ROOT, ".presentation_build", "drawio_export");
const DRAWIO_MANUSCRIPT = path.join(ROOT, "manuscript_assets", "drawio");

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

async function readSimpleCsv(filePath) {
  const text = (await fs.readFile(filePath, "utf8")).trim();
  const lines = text.split(/\r?\n/).filter(Boolean);
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => Object.fromEntries(headers.map((header, i) => [header, line.split(",")[i] ?? ""])));
}

const extensionPairwise = await readSimpleCsv(EXTENSION_PAIRWISE);

function extensionFinding(condition, label) {
  const rows = extensionPairwise.filter((row) => row.left_condition === condition);
  const completion = rows.find((row) => row.metric === "completion_rate");
  const cost = rows.find((row) => row.metric === "cost_per_verified_task");
  if (!completion || !cost) throw new Error(`Missing extension contrast for ${condition}`);
  const completionPct = Number(completion.relative_mean_change_percent);
  const costPct = Number(cost.relative_mean_change_percent);
  const significant = [completion, cost].filter((row) => Number(row.p_holm) < 0.05).length;
  const signed = (value) => `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
  return `${label}\nCompletion ${signed(completionPct)} • Cost/verified ${signed(costPct)}\nHolm-significant ${significant}/2 metrics`;
}

function addText(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: options.fill ?? "none",
    line: options.line ?? { fill: "none", width: 0 },
    borderRadius: options.borderRadius,
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 26,
    bold: options.bold ?? false,
    color: options.color ?? C.ink,
    autoFit: options.autoFit ?? "shrink",
    textAlign: options.textAlign ?? "left",
    verticalAlignment: options.verticalAlignment ?? "middle",
  };
  return shape;
}

function addRule(slide, x, y, width, color = C.orange, height = 5) {
  return slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width, height },
    fill: color,
    line: { fill: "none", width: 0 },
  });
}

function addTitle(slide, title, subtitle = null) {
  addText(slide, title, { left: 66, top: 34, width: 1148, height: 60 }, {
    fontSize: 43,
    bold: true,
    color: C.navy,
  });
  addRule(slide, 66, 103, 116, C.orange, 5);
  if (subtitle) {
    addText(slide, subtitle, { left: 200, top: 91, width: 1014, height: 34 }, {
      fontSize: 20,
      color: C.muted,
    });
  }
}

function addFooter(slide, page) {
  addText(slide, "ConveyorFlow • Advisor Review", { left: 66, top: 684, width: 340, height: 22 }, {
    fontSize: 14,
    color: C.muted,
  });
  addText(slide, String(page).padStart(2, "0"), { left: 1170, top: 684, width: 44, height: 22 }, {
    fontSize: 14,
    color: C.muted,
    textAlign: "right",
  });
}

function setupSlide(title, page, subtitle = null) {
  const slide = presentation.slides.add();
  slide.background.fill = C.light;
  addTitle(slide, title, subtitle);
  addFooter(slide, page);
  return slide;
}

async function addImage(slide, filePath, position, alt, fit = "contain") {
  const bytes = await fs.readFile(filePath);
  return slide.images.add({
    blob: bytes,
    contentType: "image/png",
    alt,
    fit,
    position,
  });
}

function addBullets(slide, items, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = makeNativeBulletParagraphs(items, {
    marginLeftPoints: options.marginLeftPoints ?? 19,
    hangingPoints: options.hangingPoints ?? 9,
    spaceAfterPoints: options.spaceAfterPoints ?? 10,
  });
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 25,
    color: options.color ?? C.ink,
    autoFit: "shrink",
  };
  return shape;
}

function addMetric(slide, value, label, x, y, color) {
  addText(slide, value, { left: x, top: y, width: 245, height: 65 }, {
    fontSize: 42,
    bold: true,
    color,
    textAlign: "center",
  });
  addText(slide, label, { left: x + 8, top: y + 64, width: 229, height: 58 }, {
    fontSize: 19,
    color: C.muted,
    textAlign: "center",
  });
}

function styleTable(table, headerColor = C.navy) {
  table.borders.assign({ style: "solid", fill: C.grid, width: 1 });
  for (let c = 0; c < table.columns.length; c += 1) {
    const cell = table.getCell(0, c);
    cell.fill = headerColor;
    cell.text.style = { typeface: FONT, fontSize: 18, bold: true, color: C.white };
  }
  for (let r = 1; r < table.rows.length; r += 1) {
    for (let c = 0; c < table.columns.length; c += 1) {
      const cell = table.getCell(r, c);
      cell.fill = r % 2 === 0 ? "#EEF2F4" : C.white;
      cell.text.style = { typeface: FONT, fontSize: 17, color: C.ink };
    }
  }
}

function setNotes(slide, time, script, source) {
  slide.speakerNotes.textFrame.setText(
    `[เวลา ${time}]\n${script}\n\nแหล่งข้อมูล: ${source}`,
  );
  slide.speakerNotes.setVisible(true);
}

// 1. Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addRule(slide, 72, 92, 150, C.orange, 7);
  addText(slide, "ConveyorFlow", { left: 72, top: 135, width: 1040, height: 94 }, {
    fontSize: 64,
    bold: true,
    color: C.white,
  });
  addText(slide, "Decentralized Capability-Aware Self-Selection\nfor Heterogeneous LLM Agent Teams", { left: 76, top: 235, width: 1070, height: 118 }, {
    fontSize: 36,
    color: "#DCE8EF",
  });
  addText(slide, "สรุปงานวิจัยและผลการทดลองสำหรับอาจารย์ที่ปรึกษา", { left: 76, top: 405, width: 1000, height: 52 }, {
    fontSize: 28,
    color: C.orangeLight,
  });
  addText(slide, "Sakan Punyanon  •  Simulation 22,500 runs  •  Real-LLM validation  •  v2", { left: 76, top: 612, width: 1040, height: 32 }, {
    fontSize: 20,
    color: "#B9CAD5",
  });
  setNotes(
    slide,
    "0:00–0:25",
    "สวัสดีครับ วันนี้ผมขอนำเสนอ ConveyorFlow ซึ่งเป็นกลไกให้ AI Agent เลือกงานจากสายพานร่วมกันด้วยตนเอง งานนี้ไม่ได้ตั้งเป้าว่าจะชนะทุกตัวชี้วัด แต่ศึกษาว่าการตัดสินใจแบบกระจายศูนย์ทำให้เกิด trade-off ระหว่างต้นทุน ความเร็ว การทำงานสำเร็จ และการใช้ทรัพยากรอย่างไร หลักฐานประกอบด้วย Simulation 22,500 runs และ Real-LLM validation ที่รันเสร็จแล้วครับ",
    "v2/ConveyorFlow_Advisor_Explanation_TH.docx",
  );
}

// 2. Response to advisor feedback
{
  const slide = setupSlide("ปรับตามข้อเสนอแนะจากพี่ที่ปรึกษา", 2);
  addText(slide, "ข้อเสนอแนะเดิม", { left: 80, top: 145, width: 440, height: 42 }, { fontSize: 29, bold: true, color: C.orange });
  addText(slide, "สิ่งที่ปรับแล้ว", { left: 690, top: 145, width: 440, height: 42 }, { fontSize: 29, bold: true, color: C.teal });
  addBullets(slide, [
    "RQ1 ไม่ควรถามว่า “ดีกว่า”",
    "RQ2 ต้องแยกผลของ heterogeneity",
    "Contribution ต้องเล่าเป็นกลไกที่เชื่อมกัน",
    "13 policies ไม่ใช่องค์ความรู้หลัก",
    "งานต้องไหลบนสายพานทั้ง CF และ baseline",
  ], { left: 90, top: 205, width: 500, height: 330 }, { fontSize: 23, color: C.ink, spaceAfterPoints: 10 });
  addBullets(slide, [
    "RQ1 วัดผลต่อ throughput, time, utilization และ cost",
    "RQ2 เทียบ homogeneous กับ heterogeneous ภายใต้ CF-Fit",
    "Story เน้น self-selection, heterogeneity, fit และ stand-down",
    "Policies อยู่ใน Experimental Design และ Ablation",
    "ภาพ Draw.io แสดง belt เดียวกัน แต่เปลี่ยนผู้ตัดสินใจ",
  ], { left: 700, top: 205, width: 500, height: 330 }, { fontSize: 23, color: C.ink, spaceAfterPoints: 10 });
  addRule(slide, 615, 150, 2, C.grid, 470);
  addText(slide, "ผลลัพธ์: งานเล่าเป็น trade-off ที่วัดได้ ไม่บังคับให้ CF-Fit ชนะทุกแกน", { left: 120, top: 575, width: 1040, height: 52 }, { fontSize: 26, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(
    slide,
    "0:25–1:00",
    "สไลด์นี้สรุปว่าข้อเสนอแนะครั้งก่อนถูกนำไปแก้อย่างไร เราเปลี่ยน RQ1 จากคำถามว่าดีกว่าหรือไม่ เป็นถามผลต่อ metric แต่ละแกน เพิ่ม RQ2 เพื่อแยกผลของ heterogeneity ย้าย 13 policies ไปเป็นหลักฐานการทดลอง และเล่า contribution ผ่าน self-selection, heterogeneity, fit และ stand-down อีกจุดคือภาพใหม่จะทำให้เห็นว่าทั้ง ConveyorFlow และ baseline ใช้ belt เดียวกัน ต่างกันที่ผู้ตัดสินใจครับ",
    "Advisor comments supplied by the researcher; v2/PLAN_SUMMARY_TH.md",
  );
}

// 3. Scientific story
{
  const slide = setupSlide("Scientific contribution ของ ConveyorFlow", 3, "13 policies เป็นหลักฐานทดลอง ไม่ใช่ contribution หลัก");
  const labels = [
    ["1", "Agent ต่างกัน", "ความสามารถและต้นทุนต่างกัน"],
    ["2", "ประเมินงานเอง", "ใช้ข้อมูลที่มองเห็นเฉพาะหน้า"],
    ["3", "เลือกตาม Fit", "จับคู่ ability กับ difficulty"],
    ["4", "Stand-down", "Agent ที่เก่งเกินจำเป็นชะลอชั่วคราว"],
    ["5", "Aging", "ผ่อนเงื่อนไขเมื่องานรอนาน"],
  ];
  const nodes = [];
  labels.forEach((item, index) => {
    const x = 50 + index * 246;
    const node = slide.shapes.add({
      geometry: "roundRect",
      position: { left: x, top: 235, width: 205, height: 205 },
      fill: index === 2 ? C.tealLight : C.white,
      line: { style: "solid", fill: index === 2 ? C.teal : C.grid, width: 2 },
      borderRadius: "rounded-xl",
    });
    addText(slide, item[0], { left: x + 68, top: 250, width: 70, height: 50 }, {
      fontSize: 34,
      bold: true,
      color: index === 2 ? C.teal : C.orange,
      textAlign: "center",
    });
    addText(slide, item[1], { left: x + 16, top: 310, width: 173, height: 48 }, {
      fontSize: 24,
      bold: true,
      color: C.navy,
      textAlign: "center",
    });
    addText(slide, item[2], { left: x + 14, top: 360, width: 177, height: 62 }, {
      fontSize: 18,
      color: C.muted,
      textAlign: "center",
    });
    nodes.push(node);
  });
  for (let i = 0; i < nodes.length - 1; i += 1) {
    slide.shapes.connect(nodes[i], nodes[i + 1], {
      kind: "straight",
      fromSide: "right",
      toSide: "left",
      line: { style: "solid", fill: C.orange, width: 3 },
      tail: { type: "triangle", width: "sm", length: "sm" },
    });
  }
  addText(slide, "กลไกนี้สำรองความสามารถสูงไว้ให้งานที่ต้องการจริง และป้องกันงานค้างด้วย aging", { left: 110, top: 510, width: 1060, height: 70 }, {
    fontSize: 29,
    bold: true,
    color: C.teal,
    textAlign: "center",
  });
  setNotes(
    slide,
    "1:00–1:40",
    "Story ของงานมีห้าช่วงที่ต่อกัน หนึ่ง Agent มีความสามารถและต้นทุนต่างกัน สองจึงให้ Agent ประเมินงานเอง สามไม่ใช่เลือกเพียงเพราะทำได้ แต่เลือกตาม capability-task fit สี่ถ้า Agent เก่งเกินความจำเป็นและมี Agent ระดับต่ำกว่าที่เพียงพอ Agent เก่งจะ stand down ชั่วคราว ห้าเมื่องานรอนาน aging จะผ่อนเงื่อนไขและยกเลิกการชะลอ นี่คือเหตุผลที่ contribution ไม่ใช่การเสนอ 13 policies จำนวนมาก แต่เป็นกลไก self-selection, heterogeneity, fit, stand-down และ aging ที่เชื่อมกันครับ",
    "Advisor comments in task brief; v2/ConveyorFlow_IEEE_Manuscript.docx",
  );
}

// 4. System architecture
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  await addImage(slide, path.join(DRAWIO_MANUSCRIPT, "architecture_system.png"), { left: 0, top: 0, width: W, height: H }, "ConveyorFlow system architecture", "contain");
  setNotes(
    slide,
    "1:40–2:10",
    "สถาปัตยกรรมใช้ core mechanism เดียวกันและสลับ execution tier หลัง interface ของ assessor, executor และ verifier Simulation กับ Real-LLM จึงเขียนลง event log และใช้ analysis pipeline เดียวกัน จุดนี้ทำให้ตัวเลขทุกชุดตรวจย้อนกลับได้และลดความเสี่ยงที่ implementation สองชุดนิยาม metric ไม่ตรงกันครับ",
    "v2/ConveyorFlow_diagrams_en_working.drawio, page: ConveyorFlow - System Architecture",
  );
}

// 5. CF-Fit on the belt (Draw.io source)
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  await addImage(slide, path.join(DRAWIO_MANUSCRIPT, "cf_fit_belt_4agents_final.png"), { left: 0, top: 0, width: W, height: H }, "Draw.io page: Belt - CF-Fit (P3), four agents", "contain");
  setNotes(
    slide,
    "1:40–2:15",
    "ภาพนี้คือ ConveyorFlow ตามแบบ tasks ride the belt งานที่ dependency ผ่านแล้วจึงเข้า READY set Agent ว่างมองงานบน belt ประเมินความสามารถและความยากเอง แล้วเลือกงานที่ fit กับระดับของตน Agent ที่เก่งเกินจำเป็นสามารถ stand down ส่วนการชนกันใช้ atomic claim โดยไม่มี arbiter จัดอันดับทุกคู่ครับ",
    "v2/ConveyorFlow_diagrams_en_working.drawio, page: Belt - CF-Fit (P3)",
  );
}

// 6. Static baseline on the same belt (Draw.io source)
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  await addImage(slide, path.join(DRAWIO_MANUSCRIPT, "baseline_static_4agents.png"), { left: 0, top: 0, width: W, height: H }, "Draw.io page: Baseline - Static assignment (P0_FIXED), four agents", "contain");
  setNotes(slide, "2:15–2:45", "Baseline ใช้งาน DAG, READY rule, belt และ one-task-per-agent limit เดียวกับ ConveyorFlow ความต่างคือ static routing table กำหนดเจ้าของ skill ก่อนรัน ถ้าเจ้าของไม่ว่าง งาน READY ต้องรอแม้ Agent อื่นทำได้ ดังนั้นการเปรียบเทียบนี้ควบคุม workload และ belt ให้เหมือนกัน แล้วเปลี่ยนเฉพาะ allocation decision ครับ", "v2/ConveyorFlow_diagrams_en_working.drawio, page: Baseline - Static assignment (P0_FIXED)");
}

// 7. One tick of the conveyor (Draw.io source)
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  await addImage(slide, path.join(DRAWIO_MANUSCRIPT, "one_tick.png"), { left: 0, top: 0, width: W, height: H }, "Draw.io page: One tick of the conveyor, in order", "contain");
  setNotes(slide, "2:45–3:20", "หนึ่ง tick เริ่มจากอัปเดตทีม เก็บและตรวจผลงานที่จบ รับ job ใหม่ แล้ว refresh ให้ task ที่ dependencies ครบเป็น READY จากนั้น Agent จึงมอง ประเมิน และเสนองานหนึ่งงาน resolve claims ใช้ compare-and-swap ไม่ใช้ arbiter ผู้ชนะเริ่มทำงานและทุก event ถูกบันทึก นี่คือลำดับวิธีที่นำไปจำลองซ้ำในทุก policy ครับ", "v2/ConveyorFlow_diagrams_en_working.drawio, page: One tick of the conveyor, in order");
}

// 8. Design
{
  const slide = setupSlide("Experimental design", 8, "50 paired seeds และ common random numbers");
  const table = slide.tables.add({
    rows: 6,
    columns: 4,
    left: 70,
    top: 150,
    width: 1140,
    height: 390,
    columnWidths: [150, 440, 330, 220],
    values: [
      ["Block", "คำถาม", "เปรียบเทียบ", "Memberships"],
      ["RQ1", "ผลของ decentralized self-selection", "CF-Fit vs S1/S2/S3/Central-Fit", "4,500"],
      ["RQ2", "ผลของ capability heterogeneity", "H0/H1/H2 ภายใต้ CF-Fit", "2,700"],
      ["RQ3", "ส่วนประกอบใดสร้างผล", "Full vs A1/A2/A3/A4", "6,000"],
      ["E4", "เมื่อไม่มี Agent อาสา", "F0/F1/F2/F3", "9,600"],
      ["รวม", "งาน ML Build และ Fix Bug", "R0/R1 และ sensitivity", "22,500"],
    ],
  });
  styleTable(table);
  addText(slide, "ข้อมูลสาธารณะ", { left: 80, top: 570, width: 220, height: 35 }, {
    fontSize: 21,
    bold: true,
    color: C.orange,
  });
  addText(slide, "UCI Adult 48,842  •  Beijing Air Quality 420,768  •  CodeXGLUE Bugs2Fix 46,680 pairs", { left: 285, top: 562, width: 900, height: 50 }, {
    fontSize: 21,
    color: C.ink,
  });
  addText(slide, "หน่วยวิเคราะห์คือ run/seed ไม่ใช่ task ภายใน run", { left: 285, top: 615, width: 900, height: 35 }, {
    fontSize: 21,
    bold: true,
    color: C.teal,
  });
  setNotes(
    slide,
    "3:20–4:00",
    "การทดลองแบ่งเป็นสี่คำถามหลัก RQ1 เปรียบเทียบ CF-Fit กับ static controls และ Central-Fit RQ2 เปลี่ยนความหลากหลายของทีมโดยตรึงขนาดทีมและค่าเฉลี่ย ability RQ3 ทำ ablation แยก assessment, fit, stand-down และ aging ส่วน E4 ทดสอบกรณีไม่มีผู้รับงาน ทุก cell ใช้ paired seeds เดียวกันและ common random numbers หน่วยวิเคราะห์คือ run ต่อ seed ไม่ใช่ถือ task ภายใน run เดียวกันเป็น replicate อิสระ ข้อมูล workload มาจากแหล่งสาธารณะขนาดมากกว่า 20,000 records ตามเงื่อนไขที่กำหนดครับ",
    "v2/results/main/design.csv; v2/data/manifest.json",
  );
}

// 9. RQ1
{
  const slide = setupSlide("RQ1: CF-Fit แลกต้นทุนกับความเร็ว", 9, "ผลเทียบ static controls แยกตาม resource regime");
  await addImage(slide, path.join(FIG, "fig2_rq1_cost.png"), { left: 55, top: 150, width: 570, height: 390 }, "RQ1 cost effects", "contain");
  addMetric(slide, "+9.4–45.3%", "Verified throughput", 660, 170, C.teal);
  addMetric(slide, "−67.9–83.1%", "P95 terminal flow time", 930, 170, C.teal);
  addMetric(slide, "+4.7–52.4%", "Cost per verified task", 660, 330, C.orange);
  addMetric(slide, "8/8", "Completion non-inferiority", 930, 330, C.green);
  addText(slide, "เทียบ Central-Fit: cost และ time ใกล้กัน แต่ throughput ของ CF-Fit ต่ำกว่า 1.1–1.5%", { left: 670, top: 520, width: 500, height: 74 }, {
    fontSize: 24,
    bold: true,
    color: C.navy2,
    textAlign: "center",
  });
  setNotes(
    slide,
    "4:00–5:00",
    "ผล RQ1 ต้องอ่านเป็น vector เทียบกับ static controls CF-Fit เพิ่ม throughput ตั้งแต่ 9.4 ถึง 45.3 เปอร์เซ็นต์ และลด P95 terminal flow time 67.9 ถึง 83.1 เปอร์เซ็นต์ แต่ต้นทุนต่อ verified task เพิ่ม 4.7 ถึง 52.4 เปอร์เซ็นต์ Completion non-inferiority ผ่านทั้ง 8 contrasts อย่างไรก็ตาม dead-letter non-inferiority ผ่านเพียง 2 จาก 8 เพราะ static หลายแบบทิ้งงานไว้ unsettled ที่ horizon ขณะที่ CF-Fit ทำให้งานเข้าสู่ terminal outcome ชัดขึ้น เมื่อเทียบ matched Central-Fit ค่า cost และ time เกือบเท่ากัน แต่ throughput ของ CF-Fit ต่ำกว่าเล็กน้อย 1.1 ถึง 1.5 เปอร์เซ็นต์ จึงไม่ควรประกาศว่า CF-Fit ชนะทุกด้านครับ",
    "v2/results/main/confirmatory_effects.csv; fig2_rq1_cost.png",
  );
}

// 10. Radar trade-off
{
  const slide = setupSlide("Trade-off profile ของ RQ1", 10, "Radar ใช้เพื่ออธิบาย ไม่ใช่คะแนนรวมเชิงอนุมาน");
  await addImage(slide, path.join(FIG, "fig6_rq1_tradeoff_radar.png"), { left: 45, top: 132, width: 1190, height: 465 }, "RQ1 trade-off radar", "contain");
  addText(slide, "สรุป: ไม่มี policy เดียวครองทุกแกน; CF-Fit ใกล้ Central-Fit ใน 4 outcome หลัก", { left: 105, top: 608, width: 1070, height: 40 }, {
    fontSize: 24,
    bold: true,
    color: C.teal,
    textAlign: "center",
  });
  setNotes(
    slide,
    "5:00–5:35",
    "Radar chart ช่วยให้เห็นเหตุผลที่เราไม่ควรรวม metric เป็นคะแนนผู้ชนะเดียว แต่ละแกน normalize ภายใน resource regime เพื่อดูรูปทรงเท่านั้น CF-Fit และ Central-Fit ใกล้กันมากในด้าน throughput, terminal time, completion และ unsettled ขณะที่ static บางตัวเด่นเฉพาะต้นทุนหรือ dead letter เมื่อเปลี่ยน resource mapping รูปทรงก็เปลี่ยน จึงต้องอธิบายผลเป็น Pareto-style trade-off และอ้างผลทดสอบที่ระดับ metric ไม่ใช่พื้นที่รูปหลายเหลี่ยมครับ",
    "v2/results/main/figures/fig6_rq1_tradeoff_radar.png",
  );
}

// 11. Heterogeneity
{
  const slide = setupSlide("RQ2: Heterogeneity ให้ประโยชน์แบบมีเงื่อนไข", 11, "ตรึง team size=4 และ mean ability=2");
  await addImage(slide, path.join(FIG, "fig3_rq2_throughput.png"), { left: 55, top: 155, width: 600, height: 365 }, "RQ2 throughput effects", "contain");
  addText(slide, "R0: Ability แยกจาก resource", { left: 700, top: 170, width: 470, height: 42 }, {
    fontSize: 27,
    bold: true,
    color: C.teal,
  });
  addBullets(slide, ["Cost ลดประมาณ 5%", "Throughput ลดเล็กน้อย", "P95 ลดประมาณ 63–64%"], { left: 715, top: 220, width: 430, height: 140 }, { fontSize: 22, spaceAfterPoints: 7 });
  addText(slide, "R1: Ability ผูกกับราคาและความเร็ว", { left: 700, top: 385, width: 470, height: 42 }, {
    fontSize: 27,
    bold: true,
    color: C.orange,
  });
  addBullets(slide, ["Cost เพิ่มประมาณ 40–82%", "Throughput เพิ่มประมาณ 2–5%", "P95 ลดประมาณ 62–63%"], { left: 715, top: 435, width: 430, height: 140 }, { fontSize: 22, spaceAfterPoints: 7 });
  addText(slide, "ข้อสรุป: diversity อย่างเดียวไม่พอ ผลขึ้นกับการจับคู่ capability กับ resource cost", { left: 120, top: 600, width: 1040, height: 55 }, {
    fontSize: 25,
    bold: true,
    color: C.navy2,
    textAlign: "center",
  });
  setNotes(
    slide,
    "5:35–6:25",
    "RQ2 ใช้ boundary compositions H0, H1 และ H2 ที่มี team size สี่และ mean ability เท่ากับสอง จึงแยกผลของ variance ออกจากการเพิ่มกำลังเฉลี่ยของทีม ใน R0 ที่ ability แยกจาก resource heterogeneity ลด cost ราว 5 เปอร์เซ็นต์ แต่ throughput ลดเล็กน้อย ใน R1 ที่ความสามารถสูงมากับราคาสูงและเร็วขึ้น heterogeneity เพิ่ม cost 40 ถึง 82 เปอร์เซ็นต์ แลกกับ throughput เพิ่ม 2 ถึง 5 เปอร์เซ็นต์ P95 ลดมากในทั้งสอง regime แต่ต้องอ่านร่วมกับ competing risks เพราะ H0 เหลืองาน unsettled มากกว่า ดังนั้นคำตอบคือ CF-Fit ใช้ประโยชน์จาก heterogeneity ได้จริง แต่ประโยชน์ทางเศรษฐกิจขึ้นกับ resource mapping ครับ",
    "v2/results/main/figures/fig3_rq2_throughput.png; confirmatory_effects.csv",
  );
}

// 12. Ablation
{
  const slide = setupSlide("RQ3: ผลจาก Fit, Aging และ Stand-down", 12, "Fit และ Aging สร้างผลชัด; Stand-down เป็น bounded refinement");
  await addImage(slide, path.join(FIG, "fig4_rq3_cost.png"), { left: 35, top: 155, width: 480, height: 350 }, "RQ3 cost ablation effects", "contain");
  const table = slide.tables.add({
    rows: 5,
    columns: 3,
    left: 535,
    top: 150,
    width: 690,
    height: 380,
    columnWidths: [175, 215, 300],
    values: [
      ["องค์ประกอบ", "ผลหลัก", "การตีความ"],
      ["Assessment", "Throughput/Completion สูงขึ้น", "มี cost overhead และเปลี่ยน backlog เป็น terminal"],
      ["Fit", "Cost −3.5–3.7%; P95 ราว −12%", "หลักฐานสนับสนุนค่อนข้างชัด"],
      ["Stand-down", "Cost/Throughput แทบไม่เปลี่ยน", "คงไว้เป็น refinement ไม่ใช่แกนหลัก"],
      ["Aging", "Completion +10.4–10.8 จุด", "ลด dead letter แต่ P95 ยาวขึ้น 77–86%"],
    ],
  });
  styleTable(table, C.teal);
  addText(slide, "Ablation ช่วยแยก contribution ของกลไกออกจากจำนวน policies", { left: 120, top: 580, width: 1040, height: 58 }, {
    fontSize: 26,
    bold: true,
    color: C.navy2,
    textAlign: "center",
  });
  setNotes(
    slide,
    "6:25–7:15",
    "Ablation ตอบว่าองค์ประกอบใดสร้างผล Assessment เพิ่ม throughput และ completion แต่มีต้นทุนการประเมิน Fit ให้หลักฐานค่อนข้างชัด โดยลด cost 3.5 ถึง 3.7 เปอร์เซ็นต์ เพิ่ม throughput ราว 2.2 เปอร์เซ็นต์ และลด P95 ราว 12 เปอร์เซ็นต์ Aging เพิ่ม completion 10.4 ถึง 10.8 จุดและลด dead letters แต่ทำให้ P95 ยาวขึ้น 77 ถึง 86 เปอร์เซ็นต์ ส่วน stand-down เปลี่ยน cost, throughput และ completion เพียงเล็กน้อยและทำให้ P95 แย่ลงเล็กน้อย เราจึงต้องรายงานอย่างตรงไปตรงมาว่า stand-down เป็น bounded refinement ที่มีเหตุผลเชิงกลไก แต่ไม่ใช่แหล่งผลหลักจาก simulation นี้ครับ",
    "v2/results/main/figures/fig4_rq3_cost.png; confirmatory_effects.csv",
  );
}

// 13. Fallback
{
  const slide = setupSlide("E4: เมื่อไม่มี Agent รับงาน", 13, "F2 ใช้ aging + relaxation แบบกระจายศูนย์");
  await addImage(slide, path.join(FIG, "fig5_e4_deadletter.png"), { left: 55, top: 155, width: 590, height: 360 }, "E4 dead-letter effects", "contain");
  addText(slide, "F2 เทียบ F0/F1", { left: 700, top: 165, width: 430, height: 42 }, { fontSize: 28, bold: true, color: C.teal });
  addBullets(slide, ["Cost ลด 24–35%", "Throughput เพิ่ม 56–62%", "Dead-letter ลดประมาณ 11 จุด", "P95 ยาวขึ้น 74–81%"], { left: 715, top: 215, width: 440, height: 190 }, { fontSize: 22, spaceAfterPoints: 6 });
  addText(slide, "F2 เทียบ F3 central rescue", { left: 700, top: 420, width: 430, height: 42 }, { fontSize: 28, bold: true, color: C.orange });
  addText(slide, "ต้นทุนใกล้กัน แต่ F2 throughput ต่ำกว่า 3.7–5.7% และ P95 สูงกว่า 9.6–12.2%", { left: 715, top: 470, width: 440, height: 92 }, { fontSize: 22, color: C.ink });
  addText(slide, "นี่คือต้นทุนของการคง fallback decision แบบ decentralized", { left: 120, top: 600, width: 1040, height: 52 }, { fontSize: 25, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(
    slide,
    "7:15–8:00",
    "กรณีไม่มีผู้รับงาน F2 จะ re-offer, ย้ายไปท้าย queue และผ่อน threshold ตามอายุ ก่อนจบเป็น dead letter เมื่อเกินขอบเขต เทียบ F0 และ F1 กลไกนี้ลด cost และ dead letter พร้อมเพิ่ม throughput มาก แต่ต้องใช้เวลาจน terminal นานกว่า เทียบกับ F3 ที่บังคับ central rescue นั้น F2 มี cost ใกล้กัน แต่ throughput ต่ำกว่าและ P95 สูงกว่าเล็กน้อย ผลนี้ช่วยให้เรา defend ได้ว่า decentralized fallback มี operational price ที่วัดได้ และ F3 ต้องเรียกว่า hybrid reference ไม่ใช่ ConveyorFlow แบบกระจายศูนย์ล้วนครับ",
    "v2/results/main/figures/fig5_e4_deadletter.png; confirmatory_effects.csv",
  );
}

// 14. Main Real-LLM policy validation
{
  const slide = setupSlide("ผล Real-LLM Main", 14, "10 paired seeds × 60 tasks • CF-Fit, Static S3, Central-Fit");
  await addImage(slide, MAIN_REAL_LLM_RADAR, { left: 35, top: 135, width: 660, height: 455 }, "Main Real-LLM policy radar", "contain");
  addText(slide, "CF-Fit เทียบ Static S3", { left: 720, top: 145, width: 470, height: 45 }, { fontSize: 28, bold: true, color: C.teal });
  addText(slide, "Completion −13.5 จุด\n(−24.7% แบบ relative)\nCost/verified +62.1%\nWall time −62.1%\nThroughput +99.5%\nUtilization +63.6%", { left: 745, top: 190, width: 420, height: 225 }, { fontSize: 22, color: C.ink });
  addText(slide, "ทุก metric-level contrast: Holm p=.005859", { left: 735, top: 407, width: 450, height: 38 }, { fontSize: 18, color: C.muted });
  addText(slide, "CF-Fit เทียบ Central-Fit", { left: 720, top: 465, width: 470, height: 42 }, { fontSize: 27, bold: true, color: C.orange });
  addText(slide, "ไม่พบความแตกต่างที่ Holm p<.05 ใน 6 metrics\n≠ หลักฐานว่าเทียบเท่ากัน", { left: 745, top: 510, width: 425, height: 82 }, { fontSize: 21, color: C.ink });
  addText(slide, "ข้อสรุป: เร็วและใช้ทรัพยากรสูงขึ้น แต่แลกด้วย completion และต้นทุน", { left: 95, top: 610, width: 1090, height: 52 }, { fontSize: 25, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(
    slide,
    "8:00–8:45",
    "ผลรันโมเดลจริงใช้สิบ paired seeds แต่ละ seed มีหกสิบงานและใช้ validator เดียวกัน เมื่อเทียบ Static S3 นั้น CF-Fit มี completion ต่ำกว่าและ cost per verified task สูงกว่า แต่จบหน้าต่างทดลองเร็วกว่า มี throughput และ utilization สูงกว่ามาก ทุกความต่างระดับ metric ผ่าน Holm correction ดังนั้นนี่คือ trade-off ที่ชัด ไม่ใช่ชัยชนะทุกด้าน ส่วนเมื่อเทียบ Central-Fit ผลใกล้กันและไม่มี metric ใด significant หลัง Holm แต่ห้ามตีความว่าเทียบเท่า เพราะงานนี้ไม่ได้ออกแบบเป็น equivalence test ครับ",
    "v2/real_llm_pilot/main_mfec_aggregated/real_llm_descriptive.csv; real_llm_pairwise.csv",
  );
}

// 15. Real-LLM extension
{
  const slide = setupSlide("Real-LLM Extension", 15, "Stand-down ablation + homogeneous boundary conditions");
  await addImage(slide, EXTENSION_REAL_LLM_RADAR, { left: 35, top: 140, width: 650, height: 445 }, "Real-LLM extension radar", "contain");
  addText(slide, extensionFinding("HET_NO_STANDDOWN", "เอา Stand-down ออก"), { left: 710, top: 145, width: 500, height: 118 }, { fontSize: 22, bold: true, color: C.teal, fill: C.tealLight, borderRadius: 12 });
  addText(slide, extensionFinding("HOM_GLM_GENERALIST", "Homogeneous GLM"), { left: 710, top: 282, width: 500, height: 118 }, { fontSize: 22, bold: true, color: C.navy2, fill: C.light, borderRadius: 12 });
  addText(slide, extensionFinding("HOM_GPT_PROFILE", "Homogeneous GPT"), { left: 710, top: 419, width: 500, height: 118 }, { fontSize: 22, bold: true, color: C.orange, fill: C.orangeLight, borderRadius: 12 });
  addText(slide, "Completion/cost = supplementary paired evidence • cross-window time/throughput/utilization = exploratory", { left: 90, top: 605, width: 1100, height: 52 }, { fontSize: 20, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(
    slide,
    "8:45–9:25",
    "Extension นี้ตอบสองคำถามเสริม หนึ่ง เอา stand-down ออกโดยคงองค์ประกอบอื่นไว้ เพื่อดู contribution ของกลไกโดยตรง สอง ใช้ทีม homogeneous สองแบบเพื่อดูขอบเขตของผลบน deployment จริง อย่างไรก็ตาม homogeneous GLM และ GPT เปลี่ยนทั้ง capability profile และพฤติกรรมของโมเดล จึงเป็น boundary evidence ไม่ใช่ causal control ที่ mean-matched แบบ simulation นอกจากนี้ extension รันคนละช่วงเวลากับ HET full จึงให้น้ำหนัก completion และ cost เป็นหลัก ส่วน wall time, throughput และ utilization ข้ามหน้าต่างถือเป็น exploratory ครับ",
    "v2/real_llm_pilot/extension_mfec_aggregated/extension_pairwise.csv; extension_statistical_summary.json",
  );
}

// 16. Claims and advisor ask
{
  const slide = setupSlide("ข้อสรุปและประเด็นขอคำแนะนำ", 16);
  addText(slide, "Claim ที่เขียนได้", { left: 75, top: 145, width: 500, height: 50 }, { fontSize: 30, bold: true, color: C.teal });
  addBullets(slide, [
    "CF-Fit เปลี่ยน trade-off vector ภายใต้ simulation",
    "Fit และ Aging มี contribution ที่วัดได้",
    "Real-LLM ยืนยัน speed–utilization / completion–cost trade-off",
    "Extension เป็น sensitivity และ boundary evidence",
  ], { left: 90, top: 205, width: 500, height: 235 }, { fontSize: 22, spaceAfterPoints: 7 });
  addText(slide, "Claim ที่ยังห้ามเขียน", { left: 675, top: 145, width: 500, height: 50 }, { fontSize: 30, bold: true, color: C.red });
  addBullets(slide, [
    "CF-Fit ชนะทุก baseline ทุก metric",
    "ไม่ significant = เทียบเท่ากัน",
    "ทีม homogeneous พิสูจน์ causal effect ของ heterogeneity",
    "LLM role labels คือ human ground truth",
  ], { left: 690, top: 205, width: 500, height: 235 }, { fontSize: 22, spaceAfterPoints: 7 });
  addRule(slide, 75, 470, 1130, C.grid, 2);
  addText(slide, "ขอคำแนะนำจากอาจารย์", { left: 75, top: 495, width: 330, height: 42 }, { fontSize: 28, bold: true, color: C.navy });
  addText(slide, "1) Contribution framing\nชัดพอหรือยัง", { left: 105, top: 545, width: 330, height: 82 }, { fontSize: 23, color: C.ink, textAlign: "center" });
  addText(slide, "2) Target journal\nและ template", { left: 470, top: 545, width: 300, height: 82 }, { fontSize: 23, color: C.ink, textAlign: "center" });
  addText(slide, "3) แผน human-expert\nvalidation ก่อน submit", { left: 805, top: 545, width: 360, height: 82 }, { fontSize: 23, color: C.ink, textAlign: "center" });
  setNotes(
    slide,
    "9:25–10:00",
    "สรุปแล้ว งานนี้ควรเสนอว่า ConveyorFlow เป็นกลไก decentralized capability-aware self-selection ที่สร้าง trade-off แตกต่างจาก static และ centralized controls หลักฐาน simulation สนับสนุน fit และ aging ส่วน Real-LLM สนับสนุนว่ากลไกทำงานได้จริงและทำให้เห็น speed-utilization กับ completion-cost trade-off Claim ที่ยังห้ามเขียนคือชนะทุก baseline, ผลไม่ significant แปลว่าเทียบเท่า, homogeneous boundary พิสูจน์ causal effect ของ heterogeneity หรือ role-conditioned LLM labels เป็น human ground truth วันนี้ขอคำแนะนำเรื่อง contribution framing, journal target และแผน human-expert validation ก่อน submission ครับ",
    "v2/ConveyorFlow_IEEE_Manuscript.docx; v2/ConveyorFlow_Advisor_Explanation_TH.docx",
  );
}

// 17. Reviewer audit appendix
{
  const slide = setupSlide("Reviewer audit: ยังต้องแก้อะไรก่อนส่งวารสาร", 17, "คำแนะนำปัจจุบัน: Major Revision ก่อน external submission");
  addText(slide, "จุดแข็ง", { left: 75, top: 145, width: 500, height: 44 }, { fontSize: 29, bold: true, color: C.teal });
  addBullets(slide, [
    "Scientific story และ trade-off framing ชัด",
    "paired design, multiplicity control และ audit trail ครบ",
    "แยก simulation, main Real-LLM และ boundary evidence",
  ], { left: 88, top: 195, width: 510, height: 205 }, { fontSize: 21, spaceAfterPoints: 8 });
  addText(slide, "รายการที่ต้องปิด", { left: 665, top: 145, width: 500, height: 44 }, { fontSize: 29, bold: true, color: C.orange });
  addBullets(slide, [
    "เขียน RQ1–RQ3 อย่างเป็นทางการใน Introduction",
    "อธิบายที่มาพารามิเตอร์ simulation และ baseline fairness",
    "ตรึง public commit/tag + DOI archive",
    "เพิ่มรายละเอียด cost accounting และ provider metadata",
    "ทำ human-expert validation หรือจำกัด claim ให้ตรงหลักฐาน",
  ], { left: 680, top: 195, width: 520, height: 275 }, { fontSize: 20, spaceAfterPoints: 6 });
  addRule(slide, 75, 495, 1130, C.grid, 2);
  addText(slide, "สถานะ: พร้อมให้อาจารย์ตรวจรอบถัดไป แต่ยังไม่ใช่ฉบับพร้อม submit", { left: 115, top: 535, width: 1050, height: 70 }, { fontSize: 27, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(slide, "Appendix", "ถ้ามองแบบ reviewer งานมีแกนความรู้และหลักฐานเพียงพอ แต่ยังควรเป็น Major Revision ก่อนส่งจริง ประเด็นสำคัญไม่ใช่เพิ่มการทดลองจำนวนมากโดยอัตโนมัติ แต่คือทำให้ RQ, calibration rationale, baseline fairness, cost accounting และ public reproducibility ตรวจสอบได้ครับ", "v2/docs/REVIEWER_AUDIT_TH.md");
}

// 18. AI transparency appendix
{
  const slide = setupSlide("AI transparency และการตรวจภาษา", 18, "ตรวจ provenance และ claim traceability แทนการพึ่ง AI detector");
  addText(slide, "เปิดเผยให้ตรงหลักฐาน", { left: 75, top: 150, width: 500, height: 45 }, { fontSize: 28, bold: true, color: C.teal });
  addBullets(slide, [
    "difficulty labels มาจาก LLM เดียว 3 role-conditioned passes",
    "agreement = procedural stability ไม่ใช่ human ground truth",
    "เก็บ prompts, outputs, adjudication และ hashes ไว้ตรวจย้อนกลับ",
    "ผู้เขียนตรวจและรับผิดชอบ methods, code, claims และ citations",
  ], { left: 90, top: 205, width: 520, height: 285 }, { fontSize: 21, spaceAfterPoints: 8 });
  addText(slide, "ภาษาที่ปรับ", { left: 685, top: 150, width: 450, height: 45 }, { fontSize: 28, bold: true, color: C.orange });
  addBullets(slide, [
    "ลดประโยคยาวและโครงสร้าง not X but Y ที่ซ้ำ",
    "แยก percentage points ออกจาก relative percent",
    "ใช้ Ability Rank และศัพท์ Real-LLM ให้สม่ำเสมอ",
    "ไม่อ้างผล detector ว่าเป็นหลักฐานการประพันธ์",
  ], { left: 700, top: 205, width: 485, height: 250 }, { fontSize: 21, spaceAfterPoints: 8 });
  addText(slide, "ก่อน submit ต้องปรับ disclosure ให้ตรง policy ของวารสารเป้าหมาย", { left: 125, top: 550, width: 1030, height: 58 }, { fontSize: 25, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(slide, "Appendix", "การตรวจ AI ในที่นี้ไม่ใช้ detector ตัดสินว่าใครเขียน เพราะเครื่องมือกลุ่มนั้นไม่เหมาะเป็นหลักฐาน เราตรวจจาก provenance แทน ได้แก่ที่มาของ labels การเก็บ prompts และ outputs ความสอดคล้องระหว่าง claim กับผลทดลอง และการรับผิดชอบของผู้เขียน พร้อมปรับภาษาให้เป็นธรรมชาติและเฉพาะเจาะจงกับงานนี้ครับ", "v2/docs/AI_USE_DISCLOSURE.md; v2/docs/REVIEWER_AUDIT_TH.md");
}

// 19. Reproducibility appendix
{
  const slide = setupSlide("Git package สำหรับให้ Reviewer ทดลองซ้ำ", 19, "Git เก็บสิ่งที่จำเป็นต่อการตรวจและสร้างผลใหม่");
  addText(slide, "ขึ้น Git", { left: 70, top: 145, width: 350, height: 44 }, { fontSize: 29, bold: true, color: C.teal });
  addBullets(slide, [
    "source code, frozen configs, tests และ CI",
    "data manifests/download scripts และ derived metadata",
    "AI-label audit trail และ 60 Real-LLM case bundles",
    "aggregate results, statistics, figures, hashes และ source snapshot",
    "Draw.io, manuscript, presentation และ reproduction guide",
  ], { left: 85, top: 195, width: 545, height: 300 }, { fontSize: 20, spaceAfterPoints: 7 });
  addText(slide, "ไม่ขึ้น Git", { left: 690, top: 145, width: 400, height: 44 }, { fontSize: 29, bold: true, color: C.red });
  addBullets(slide, [
    "API keys, .env และ bearer tokens",
    "raw datasets ที่ติด upstream license",
    "event ledgers ประมาณ 7 GB และ development checkpoints",
    "raw provider calls, candidate outputs, caches และ QA renders",
  ], { left: 705, top: 195, width: 490, height: 250 }, { fontSize: 20, spaceAfterPoints: 8 });
  addText(slide, "Simulation: exact seeded reproduction  •  Real-LLM: protocol-level re-execution under provider drift", { left: 90, top: 555, width: 1100, height: 60 }, { fontSize: 23, bold: true, color: C.navy2, textAlign: "center" });
  setNotes(slide, "Appendix", "Repository แยกสิ่งที่ต้องใช้ทำซ้ำออกจากไฟล์ดิบขนาดใหญ่ Reviewer สามารถทดสอบ unit tests ตรวจ frozen design สร้างข้อมูลสาธารณะ รัน simulation และวิเคราะห์ผลใหม่ได้ ส่วน Real-LLM ทำซ้ำได้ในระดับ protocol, cases, validators และ analysis แต่ generation กับ timing อาจเปลี่ยนตาม provider จึงต้องบันทึก provider state ทุกครั้งครับ", "v2/README.md; v2/REPRODUCIBILITY.md");
}

const requirements = {
  explicitTotalSlideCount: 19,
  requiredNativeTableOwnerSlides: [8, 12],
  requiredNativeChartOwnerSlides: [],
};
const fontPolicy = {
  basis: "design",
  // Native table cells currently serialize through the Office table default
  // (Calibri), while all authored textboxes use Leelawadee UI.
  families: [FONT, "Calibri"],
};
const stagingDir = path.join(workspaceDir, "v2", ".presentation_build", "finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "ConveyorFlow_Advisor_Presentation_TH.candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "8",
    "--require-native-table-slide", "12",
  ],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  fontPolicy,
  // The presentation itself is authored with the first-party Artifact Tool above.
  // The isolated re-import probe is disabled because the bundled Windows runtime
  // terminates after producing its inspection artifact before publishing the file.
  verifyArtifactToolImport: false,
  receiptPath: path.join(stagingDir, "ConveyorFlow_Advisor_Presentation_TH_v6.validation.json"),
});

console.log(JSON.stringify({ status: "complete", finalPath: FINAL_PPTX, result }, null, 2));
