import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "submission_artifacts";
const QA = `${OUT}/pptx_qa`;
const W = 1280;
const H = 720;
const C = {
  ink: "#10241F",
  green: "#0B7A5A",
  green2: "#12B886",
  cyan: "#0EA5A5",
  pale: "#EAF8F1",
  surface: "#F7FBF8",
  line: "#CBE7D8",
  text: "#23332D",
  muted: "#5C7168",
  amber: "#D98B1E",
  red: "#C94C4C",
  blue: "#2279B5",
};

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

function addBox(slide, left, top, width, height, fill = "none", line = "none", radius = "rounded-xl") {
  const config = {
    geometry: radius === "none" ? "rect" : "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
  };
  if (radius !== "none") config.borderRadius = radius;
  return slide.shapes.add(config);
}

function addText(slide, text, left, top, width, height, style = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    fontSize: 20,
    color: C.text,
    fontFamily: "Microsoft YaHei",
    ...style,
  };
  return box;
}

function addFooter(slide, number, label = "农智云瞰 · 大数据与人工智能行业应用开发") {
  addText(slide, label, 64, 682, 760, 18, { fontSize: 10, color: C.muted });
  addText(slide, String(number).padStart(2, "0"), 1160, 680, 56, 20, { fontSize: 11, bold: true, color: C.green, alignment: "right" });
}

function addHeader(slide, number, kicker, title, subtitle = "") {
  addText(slide, kicker.toUpperCase(), 64, 42, 640, 18, { fontSize: 11, bold: true, color: C.green2 });
  addText(slide, title, 64, 74, 1000, 48, { fontSize: 31, bold: true, color: C.ink });
  if (subtitle) addText(slide, subtitle, 64, 126, 1060, 28, { fontSize: 14, color: C.muted });
  addBox(slide, 64, 168, 1152, 1, C.line, "none", "none");
  addFooter(slide, number);
}

function addMetric(slide, left, top, width, value, label, accent = C.green) {
  addBox(slide, left, top, width, 108, "white", C.line);
  addBox(slide, left, top, 5, 108, accent, "none", "none");
  addText(slide, value, left + 24, top + 21, width - 42, 35, { fontSize: 28, bold: true, color: C.ink });
  addText(slide, label, left + 24, top + 67, width - 42, 22, { fontSize: 12, color: C.muted });
}

function addBulletList(slide, items, left, top, width, lineHeight = 34, color = C.text) {
  items.forEach((item, i) => {
    addBox(slide, left, top + i * lineHeight + 7, 9, 9, C.green2, "none", "rounded-full");
    addText(slide, item, left + 22, top + i * lineHeight, width - 22, lineHeight, { fontSize: 16, color });
  });
}

function addPill(slide, text, left, top, width, color = C.pale, textColor = C.green) {
  addBox(slide, left, top, width, 30, color, "none", "rounded-full");
  addText(slide, text, left, top + 6, width, 18, { fontSize: 11, bold: true, color: textColor, alignment: "center" });
}

function addArchitectureNode(slide, label, detail, left, top, width, accent) {
  addBox(slide, left, top, width, 112, "white", C.line);
  addBox(slide, left + 18, top + 20, 44, 44, accent, "none", "rounded-xl");
  addText(slide, label.slice(0, 1), left + 18, top + 27, 44, 28, { fontSize: 22, bold: true, color: "white", alignment: "center" });
  addText(slide, label, left + 78, top + 20, width - 92, 25, { fontSize: 17, bold: true, color: C.ink });
  addText(slide, detail, left + 78, top + 50, width - 92, 45, { fontSize: 11, color: C.muted });
}

async function main() {
  await fs.mkdir(OUT, { recursive: true });
  await fs.mkdir(QA, { recursive: true });
  const p = Presentation.create({ slideSize: { width: W, height: H } });

  // 1. Cover
  {
    const s = p.slides.add();
    s.background.fill = C.ink;
    addBox(s, 0, 0, W, H, C.ink, "none", "none");
    addBox(s, 0, 0, 24, H, C.green2, "none", "none");
    addText(s, "县域农业智能决策平台", 86, 78, 630, 30, { fontSize: 17, bold: true, color: C.green2 });
    addText(s, "农智云瞰", 82, 145, 640, 90, { fontSize: 66, bold: true, color: "white" });
    addText(s, "面向县域农业的病虫害识别、产量风险预测与农情决策大数据平台", 88, 248, 640, 70, { fontSize: 22, color: "#D6F4E7" });
    addPill(s, "大数据 × 人工智能 × 行业应用", 88, 354, 250, "#163C34", C.green2);
    addText(s, "项目简介PPT · 参赛材料初稿", 88, 614, 400, 22, { fontSize: 14, color: "#A9C9BC" });
    addText(s, "待替换：学校 / 团队名称 / 团队编号 / 成员信息", 88, 646, 580, 20, { fontSize: 11, color: "#77988B" });
    addBox(s, 806, 116, 340, 420, "#102E29", "#2B6857");
    addText(s, "农情指挥中心", 846, 150, 230, 26, { fontSize: 17, bold: true, color: "white" });
    addText(s, "实时态势", 846, 200, 120, 18, { fontSize: 11, color: "#8ECFBA" });
    addText(s, "80", 846, 228, 110, 52, { fontSize: 44, bold: true, color: "white" });
    addText(s, "监测地块", 956, 248, 130, 20, { fontSize: 13, color: "#BEE7D7" });
    addBox(s, 846, 316, 260, 1, "#2B6857", "none", "none");
    addText(s, "风险闭环", 846, 344, 120, 18, { fontSize: 11, color: "#8ECFBA" });
    addText(s, "发现 → 研判 → 巡检 → 处置", 846, 380, 250, 24, { fontSize: 17, bold: true, color: "white" });
    addText(s, "展示版本 / 2026", 846, 482, 220, 20, { fontSize: 12, color: "#8ECFBA" });
    addText(s, "01", 1160, 680, 56, 20, { fontSize: 11, bold: true, color: C.green2, alignment: "right" });
  }

  // 2. Background
  {
    const s = p.slides.add();
    addHeader(s, 2, "01 / 行业背景", "农业治理的关键矛盾：信息分散，响应滞后", "县域农业需要把分散的数据转化为可执行的治理动作。");
    addMetric(s, 64, 212, 260, "多源", "地块 / 天气 / 传感器 / 影像 / 业务记录", C.green);
    addMetric(s, 354, 212, 260, "提前", "从事后统计转向风险预测与主动巡检", C.cyan);
    addMetric(s, 644, 212, 260, "闭环", "预警、任务、处置、报告统一留痕", C.amber);
    addMetric(s, 934, 212, 282, "可推广", "适配县域、乡镇、合作社多层级角色", C.blue);
    addBox(s, 64, 365, 1152, 220, C.pale, C.line);
    addText(s, "真实业务痛点", 96, 394, 220, 26, { fontSize: 20, bold: true, color: C.ink });
    addBulletList(s, [
      "病虫害发现主要依赖人工经验，巡检覆盖不稳定，早期信号容易错过。",
      "天气、传感器、地块和产量数据缺乏统一关联，难以解释风险来源。",
      "预警之后缺少任务派发与处置回访，管理动作难以量化考核。",
    ], 98, 442, 1040, 39);
  }

  // 3. Goal
  {
    const s = p.slides.add();
    addHeader(s, 3, "02 / 目标定义", "让每一次农情判断，都能落到下一步动作", "面向县域主管部门、农技站、合作社和种植大户构建协同平台。");
    addBox(s, 64, 212, 520, 330, C.ink, "none");
    addText(s, "核心目标", 100, 254, 160, 26, { fontSize: 20, bold: true, color: C.green2 });
    addText(s, "提前发现风险\n辅助精准巡检\n减少减产损失", 100, 306, 360, 150, { fontSize: 32, bold: true, color: "white" });
    addText(s, "把数据、算法与农技经验组织成可解释、可追踪、可复盘的县域农业治理工具。", 100, 478, 390, 46, { fontSize: 14, color: "#B8D9CC" });
    addBox(s, 632, 212, 584, 330, "white", C.line);
    addText(s, "应用对象", 670, 250, 160, 25, { fontSize: 19, bold: true, color: C.ink });
    addBulletList(s, ["县域农业主管部门：看全局、调资源、出日报", "农技专家：看风险因子、做识别、给建议", "合作社与种植大户：看地块、接任务、报处置"], 670, 306, 480, 52);
    addPill(s, "价值链：数据 → 模型 → 决策 → 行动 → 复盘", 670, 480, 400, C.pale, C.green);
  }

  // 4. Architecture
  {
    const s = p.slides.add();
    addHeader(s, 4, "03 / 总体方案", "一套面向真实业务的前后端分离架构", "数据层、算法层、业务层、展示层相互解耦，支持本地演示与云端部署。");
    addArchitectureNode(s, "数据接入", "CSV、天气、传感器、影像、业务记录", 64, 220, 220, C.blue);
    addArchitectureNode(s, "数据处理", "清洗、聚合、特征工程、批处理任务", 312, 220, 220, C.cyan);
    addArchitectureNode(s, "智能模型", "CV、风险评分、产量预测、异常检测、RAG", 560, 220, 250, C.green);
    addArchitectureNode(s, "业务服务", "FastAPI、权限、预警、巡检、报告", 840, 220, 220, C.amber);
    addArchitectureNode(s, "可视化应用", "Next.js、地图、图表、问答、驾驶舱", 1090, 220, 126, C.green2);
    addText(s, "数据流向", 66, 384, 120, 20, { fontSize: 12, bold: true, color: C.muted });
    addBox(s, 64, 420, 1152, 116, C.pale, C.line);
    addText(s, "采集", 120, 462, 110, 22, { fontSize: 17, bold: true, color: C.blue, alignment: "center" });
    addText(s, "→", 244, 457, 45, 30, { fontSize: 24, bold: true, color: C.green });
    addText(s, "清洗与特征", 304, 462, 150, 22, { fontSize: 17, bold: true, color: C.cyan, alignment: "center" });
    addText(s, "→", 480, 457, 45, 30, { fontSize: 24, bold: true, color: C.green });
    addText(s, "风险研判", 544, 462, 130, 22, { fontSize: 17, bold: true, color: C.green, alignment: "center" });
    addText(s, "→", 704, 457, 45, 30, { fontSize: 24, bold: true, color: C.green });
    addText(s, "预警与任务", 764, 462, 150, 22, { fontSize: 17, bold: true, color: C.amber, alignment: "center" });
    addText(s, "→", 944, 457, 45, 30, { fontSize: 24, bold: true, color: C.green });
    addText(s, "治理复盘", 1000, 462, 130, 22, { fontSize: 17, bold: true, color: C.ink, alignment: "center" });
  }

  // 5. Data
  {
    const s = p.slides.add();
    addHeader(s, 5, "04 / 数据底座", "用一套可复现的仿真数据支撑全链路验证", "固定随机种子生成演示数据，字段结构与真实接入边界保持一致。");
    addMetric(s, 64, 212, 220, "6", "乡镇", C.green);
    addMetric(s, 306, 212, 220, "80", "监测地块", C.cyan);
    addMetric(s, 548, 212, 220, "180 天", "天气记录", C.blue);
    addMetric(s, 790, 212, 220, "5,200+", "传感器记录", C.amber);
    addMetric(s, 1032, 212, 184, "1,000+", "业务记录", C.red);
    addBox(s, 64, 366, 1152, 192, "white", C.line);
    addText(s, "实体关系", 96, 398, 170, 24, { fontSize: 19, bold: true, color: C.ink });
    addBulletList(s, ["地块是业务主线：关联作物、乡镇、天气、传感器、风险与巡检任务。", "风险预测同时服务 Dashboard、地图、预警中心、预测页与 AI 助手。", "批处理输出乡镇排名、作物风险、7日趋势、产量预测、任务优先级和农资建议。"], 96, 442, 1030, 35);
  }

  // 6. Algorithms
  {
    const s = p.slides.add();
    addHeader(s, 6, "05 / 算法体系", "多模型协同：识别、预测、解释与问答", "至少覆盖视觉识别、机器学习风险评分、时序/回归预测与知识增强问答。");
    addBox(s, 64, 212, 530, 350, "white", C.line);
    addText(s, "模型矩阵", 96, 244, 170, 25, { fontSize: 19, bold: true, color: C.ink });
    addBulletList(s, ["CV：病虫害识别接口，支持 mock 与真实模型替换", "RandomForest：风险评分、特征重要性、风险等级", "RandomForestRegressor：产量预测、MAE / RMSE / R²", "IsolationForest：传感器和天气异常检测", "RAGFlow + 本地 TF-IDF：知识库问答与引用来源"], 96, 296, 450, 43);
    addBox(s, 636, 212, 580, 350, C.pale, C.line);
    addText(s, "评估与可解释性", 670, 244, 240, 25, { fontSize: 19, bold: true, color: C.ink });
    s.charts.add("bar", {
      position: { left: 676, top: 304, width: 480, height: 190 },
      categories: ["Accuracy", "Precision", "Recall", "F1"],
      series: [{ name: "演示基线", values: [0.91, 0.88, 0.86, 0.87], fill: "accent1" }],
      hasLegend: false,
      dataLabels: { showValue: true, position: "outEnd" },
      yAxis: { min: 0, max: 1, majorGridlines: { style: "solid", fill: "#CBE7D8", width: 1 } },
    });
    addText(s, "指标在演示数据上计算；真实部署需用标注集重新训练与评估。", 674, 512, 480, 24, { fontSize: 11, color: C.muted });
  }

  // 7. Dashboard
  {
    const s = p.slides.add();
    addHeader(s, 7, "06 / 系统展示", "农情驾驶舱：把县域全局态势压缩到一屏", "KPI、趋势、乡镇排名、地图入口和最新预警形成管理者的第一视图。");
    addMetric(s, 64, 208, 205, "12,680 亩", "全县种植面积", C.green);
    addMetric(s, 287, 208, 205, "14 个", "高风险地块", C.red);
    addMetric(s, 510, 208, 205, "36 条", "今日新增上报", C.amber);
    addMetric(s, 733, 208, 205, "17.5%", "预测减产风险", C.blue);
    addMetric(s, 956, 208, 260, "91.2%", "AI识别准确率", C.cyan);
    addBox(s, 64, 354, 720, 218, "white", C.line);
    addText(s, "未来7天农情风险趋势（风险指数）", 92, 380, 350, 24, { fontSize: 17, bold: true, color: C.ink });
    s.charts.add("line", {
      position: { left: 96, top: 426, width: 650, height: 112 },
      categories: ["今日", "+1", "+2", "+3", "+4", "+5", "+6"],
      series: [{ name: "风险指数", values: [58, 61, 65, 69, 66, 63, 60], fill: "accent1" }],
      hasLegend: true,
      yAxis: { min: 0, max: 100, majorGridlines: { style: "solid", fill: "#E1EFE8", width: 1 } },
    });
    addBox(s, 812, 354, 404, 218, C.ink, "none");
    addText(s, "重点预警", 842, 380, 140, 24, { fontSize: 17, bold: true, color: "white" });
    addPill(s, "高风险 · 14", 842, 430, 130, "#4A2529", "#FF9F9F");
    addText(s, "东岭镇 · 番茄早疫病风险升高", 842, 480, 310, 22, { fontSize: 14, color: "#E2F1EA" });
    addText(s, "建议：今日 18:00 前完成复核巡检", 842, 516, 320, 20, { fontSize: 12, color: "#9FCBBA" });
  }

  // 8. Map
  {
    const s = p.slides.add();
    addHeader(s, 8, "07 / 地图风控", "地图风险监测：从乡镇下钻到地块", "风险颜色、地块边界、天气摘要和巡检建议叠加在同一业务视图。");
    addBox(s, 64, 214, 790, 360, "#163B32", "#3B806B");
    addText(s, "县域风险热力图 · 演示截图位", 94, 240, 300, 25, { fontSize: 17, bold: true, color: "white" });
    const cells = [
      ["#1A8F68", 110, 304, 155, 72], ["#D18B20", 290, 292, 122, 92], ["#C65050", 442, 316, 176, 70],
      ["#247BAA", 638, 282, 132, 84], ["#35A978", 178, 408, 190, 84], ["#C65050", 420, 418, 125, 84], ["#D18B20", 586, 408, 146, 78],
    ];
    cells.forEach(([fill, left, top, width, height]) => addBox(s, left, top, width, height, fill, "#A7E4C7", "rounded-lg"));
    addPill(s, "高风险", 98, 526, 82, "#4A2529", "#FFB0A6");
    addPill(s, "中风险", 194, 526, 82, "#4A3A1D", "#FFD18A");
    addPill(s, "低风险", 290, 526, 82, "#183F36", "#A9E7CB");
    addBox(s, 884, 214, 332, 360, "white", C.line);
    addText(s, "地块详情浮层", 916, 244, 190, 25, { fontSize: 19, bold: true, color: C.ink });
    addText(s, "东岭镇 · F-023", 916, 298, 230, 24, { fontSize: 18, bold: true, color: C.green });
    addText(s, "作物：番茄    面积：86.4 亩", 916, 337, 250, 20, { fontSize: 13, color: C.text });
    addPill(s, "高风险 78 / 100", 916, 376, 148, "#FCE8E8", C.red);
    addText(s, "主要因子", 916, 432, 120, 18, { fontSize: 12, bold: true, color: C.muted });
    addText(s, "高湿 + 历史病害 + 连续降雨", 916, 458, 250, 22, { fontSize: 14, color: C.text });
    addText(s, "建议巡检：今日 18:00 前", 916, 506, 240, 20, { fontSize: 13, bold: true, color: C.amber });
  }

  // 9. Disease
  {
    const s = p.slides.add();
    addHeader(s, 9, "08 / 视觉识别", "病虫害识别：上传一张叶片，得到可解释的处置建议", "拖拽上传、预览、识别进度、结果置信度、病斑说明和人工复核建议形成完整交互。");
    addBox(s, 64, 214, 490, 342, C.pale, C.line);
    addText(s, "叶片图像上传区", 98, 248, 240, 25, { fontSize: 19, bold: true, color: C.ink });
    addBox(s, 98, 304, 420, 174, "white", C.green, "rounded-2xl");
    addText(s, "拖拽图片到这里", 168, 348, 280, 28, { fontSize: 23, bold: true, color: C.green, alignment: "center" });
    addText(s, "或点击选择 JPG / PNG · 最大 10MB", 138, 394, 340, 20, { fontSize: 12, color: C.muted, alignment: "center" });
    addPill(s, "识别进度 100%", 226, 504, 164, "#DFF5E9", C.green);
    addBox(s, 594, 214, 622, 342, "white", C.line);
    addText(s, "识别结果", 626, 248, 170, 25, { fontSize: 19, bold: true, color: C.ink });
    addText(s, "番茄早疫病", 626, 304, 260, 34, { fontSize: 29, bold: true, color: C.red });
    addPill(s, "置信度 92.4%", 626, 356, 136, "#FCE8E8", C.red);
    addText(s, "疑似病斑区域：叶片下部褐色同心轮纹", 626, 414, 440, 24, { fontSize: 14, color: C.text });
    addBox(s, 626, 464, 528, 1, C.line, "none", "none");
    addText(s, "建议：隔离疑似植株，优先复核东岭镇 F-023；按农技规范进行药剂轮换。", 626, 490, 520, 45, { fontSize: 13, color: C.muted });
  }

  // 10. Forecast
  {
    const s = p.slides.add();
    addHeader(s, 10, "09 / 预测决策", "产量与风险预测：提前看见减产风险的方向", "选择作物、乡镇和时间范围，联动显示产量曲线、风险曲线、误差指标与建议。");
    addBox(s, 64, 214, 730, 340, "white", C.line);
    addText(s, "未来30天产量预测（吨）", 96, 244, 280, 24, { fontSize: 18, bold: true, color: C.ink });
    s.charts.add("line", {
      position: { left: 96, top: 300, width: 650, height: 200 },
      categories: ["第1周", "第2周", "第3周", "第4周", "第5周"],
      series: [
        { name: "预测产量", values: [112, 118, 126, 121, 130], fill: "accent1" },
        { name: "风险指数", values: [54, 52, 48, 56, 50], fill: "accent2" },
      ],
      hasLegend: true,
      yAxis: { majorGridlines: { style: "solid", fill: "#E1EFE8", width: 1 } },
    });
    addBox(s, 830, 214, 386, 340, C.ink, "none");
    addText(s, "模型评估与建议", 864, 244, 220, 25, { fontSize: 19, bold: true, color: "white" });
    addText(s, "MAE", 864, 306, 100, 18, { fontSize: 12, color: "#9FCBBA" });
    addText(s, "4.8 吨", 864, 332, 140, 30, { fontSize: 24, bold: true, color: "white" });
    addText(s, "RMSE 6.2 吨   R² 0.86", 864, 376, 260, 20, { fontSize: 13, color: "#B8D9CC" });
    addBox(s, 864, 420, 286, 1, "#2B6857", "none", "none");
    addText(s, "决策建议", 864, 446, 100, 18, { fontSize: 12, color: "#9FCBBA" });
    addText(s, "储备药剂；高湿天气前完成重点地块巡检。", 864, 474, 280, 42, { fontSize: 14, color: "white" });
  }

  // 11. Alert / task
  {
    const s = p.slides.add();
    addHeader(s, 11, "10 / 业务闭环", "预警不是终点：系统自动生成可执行巡检任务", "每条预警都包含原因、负责人、状态和下一步动作，支持处理记录留痕。");
    addBox(s, 64, 214, 1152, 338, "white", C.line);
    addText(s, "预警中心", 96, 246, 160, 25, { fontSize: 19, bold: true, color: C.ink });
    addText(s, "风险等级", 96, 304, 100, 18, { fontSize: 11, bold: true, color: C.muted });
    addText(s, "触发原因", 250, 304, 220, 18, { fontSize: 11, bold: true, color: C.muted });
    addText(s, "处置建议", 594, 304, 260, 18, { fontSize: 11, bold: true, color: C.muted });
    addText(s, "状态", 1000, 304, 100, 18, { fontSize: 11, bold: true, color: C.muted });
    const rows = [
      ["高风险", "高湿 + 历史病害", "今日18:00前复核", "待处理", "#FCE8E8", C.red],
      ["中风险", "传感器叶面湿度异常", "现场校验设备", "处理中", "#FFF4D6", C.amber],
      ["低风险", "连续降雨后风险回落", "保持常规巡检", "已完成", "#DFF5E9", C.green],
    ];
    rows.forEach((row, i) => {
      const y = 340 + i * 64;
      addBox(s, 88, y, 1080, 48, i === 1 ? "#F7FBF8" : "white", "#E2EFE8");
      addPill(s, row[0], 96, y + 9, 80, row[4], row[5]);
      addText(s, row[1], 250, y + 14, 260, 20, { fontSize: 13, color: C.text });
      addText(s, row[2], 594, y + 14, 300, 20, { fontSize: 13, color: C.text });
      addPill(s, row[3], 986, y + 9, 90, row[4], row[5]);
      addText(s, "→ 生成任务", 1088, y + 14, 80, 20, { fontSize: 11, bold: true, color: C.green });
    });
    addPill(s, "巡检任务：优先级 P1 / 负责人 / 截止时间 / 处理记录", 96, 514, 440, C.pale, C.green);
  }

  // 12. Assistant
  {
    const s = p.slides.add();
    addHeader(s, 12, "11 / 智能助手", "AI 农技助手：回答问题，也给出依据和行动建议", "RAGFlow 远程知识库优先，本地 Markdown TF-IDF 作为可用兜底，并引用当前系统风险数据。");
    addBox(s, 64, 214, 718, 350, "white", C.line);
    addText(s, "用户提问", 96, 246, 140, 22, { fontSize: 14, bold: true, color: C.blue });
    addText(s, "番茄早疫病怎么防治？", 96, 286, 520, 34, { fontSize: 28, bold: true, color: C.ink });
    addBox(s, 96, 352, 650, 1, C.line, "none", "none");
    addText(s, "结合当前数据", 96, 384, 150, 20, { fontSize: 12, bold: true, color: C.muted });
    addText(s, "东岭镇 F-023 当前风险 78 / 100，高湿与历史病害为主要贡献因子。", 96, 418, 590, 25, { fontSize: 15, color: C.text });
    addBox(s, 96, 478, 650, 1, C.line, "none", "none");
    addText(s, "建议操作：今日 18:00 前完成现场复核，并记录病斑照片。", 96, 506, 600, 24, { fontSize: 14, bold: true, color: C.green });
    addBox(s, 820, 214, 396, 350, C.ink, "none");
    addText(s, "回答依据", 854, 246, 160, 22, { fontSize: 17, bold: true, color: "white" });
    addPill(s, "RAGFlow / 远程知识库", 854, 294, 190, "#163C34", C.green2);
    addText(s, "引用来源", 854, 350, 120, 18, { fontSize: 12, color: "#9FCBBA" });
    addText(s, "knowledge_base/tomato_disease.md", 854, 378, 300, 20, { fontSize: 13, color: "#D6F4E7" });
    addText(s, "weather_risk.md", 854, 410, 240, 20, { fontSize: 13, color: "#D6F4E7" });
    addText(s, "风险数据：F-023 · 78 / 100", 854, 474, 260, 20, { fontSize: 13, color: "#A9DCCA" });
  }

  // 13. Report
  {
    const s = p.slides.add();
    addHeader(s, 13, "12 / 报告生成", "一键生成县域农情风险日报", "把 KPI、风险地块、模型预测、处置建议与数据来源沉淀为可交付报告。");
    addBox(s, 64, 214, 470, 342, C.ink, "none");
    addText(s, "日报生成器", 98, 246, 180, 25, { fontSize: 20, bold: true, color: "white" });
    addText(s, "2026-08-20", 98, 304, 240, 32, { fontSize: 29, bold: true, color: C.green2 });
    addText(s, "县域农情风险日报", 98, 348, 280, 27, { fontSize: 20, color: "white" });
    addPill(s, "数据已更新", 98, 414, 110, "#163C34", C.green2);
    addText(s, "Markdown / HTML 可导出 · PDF 可打印归档", 98, 474, 320, 20, { fontSize: 13, color: "#A9CDBE" });
    addBox(s, 574, 214, 642, 342, "white", C.line);
    addText(s, "报告摘要预览", 608, 246, 190, 25, { fontSize: 19, bold: true, color: C.ink });
    addMetric(s, 608, 298, 160, "14", "高风险地块", C.red);
    addMetric(s, 786, 298, 160, "28", "待处理预警", C.amber);
    addMetric(s, 964, 298, 216, "17.5%", "预测减产风险", C.blue);
    addText(s, "结论：东岭镇、南河镇为本周期重点关注区域；建议优先安排叶片复核、药剂储备和灌溉调度。", 608, 442, 536, 48, { fontSize: 14, color: C.text });
    addPill(s, "生成报告", 608, 508, 118, C.green2, "white");
    addPill(s, "导出 HTML", 742, 508, 118, C.pale, C.green);
  }

  // 14. Innovation
  {
    const s = p.slides.add();
    addHeader(s, 14, "13 / 竞赛亮点", "从“展示数据”走向“驱动治理”", "创新不只在模型本身，更在多源融合、可解释决策和业务闭环的组合。");
    const cards = [
      ["多源融合", "地块、天气、传感器、影像、产量和业务记录统一关联", C.blue],
      ["可解释模型", "风险因子贡献、病斑区域说明、误差指标同步展示", C.green],
      ["人机协同", "AI 给出建议，农技专家负责复核，任务系统承接执行", C.cyan],
      ["可推广架构", "SQLite fallback + PostgreSQL、pandas + Spark 可选、RAGFlow 可插拔", C.amber],
    ];
    cards.forEach((card, i) => {
      const left = 64 + (i % 2) * 586;
      const top = 218 + Math.floor(i / 2) * 166;
      addBox(s, left, top, 540, 132, "white", C.line);
      addBox(s, left + 26, top + 28, 54, 54, card[2], "none", "rounded-xl");
      addText(s, String(i + 1).padStart(2, "0"), left + 26, top + 42, 54, 22, { fontSize: 17, bold: true, color: "white", alignment: "center" });
      addText(s, card[0], left + 106, top + 26, 250, 24, { fontSize: 19, bold: true, color: C.ink });
      addText(s, card[1], left + 106, top + 62, 390, 40, { fontSize: 13, color: C.muted });
    });
    addBox(s, 64, 560, 1152, 1, C.line, "none", "none");
    addText(s, "评分对齐：行业应用价值 25% · 技术创新性 25% · 工程实现质量 30% · 文档与展示 20%", 64, 592, 1060, 24, { fontSize: 15, bold: true, color: C.green });
  }

  // 15. Close / demo plan
  {
    const s = p.slides.add();
    s.background.fill = C.ink;
    addText(s, "现场演示建议", 86, 74, 350, 28, { fontSize: 17, bold: true, color: C.green2 });
    addText(s, "8 分钟，把一条风险讲完整", 82, 128, 700, 62, { fontSize: 44, bold: true, color: "white" });
    addText(s, "登录 → 驾驶舱 → 地图下钻 → 叶片识别 → 预测 → AI问答 → 生成日报", 88, 216, 920, 30, { fontSize: 18, color: "#D6F4E7" });
    addBox(s, 88, 320, 1080, 100, "#102E29", "#2B6857");
    addText(s, "必须在最终提交前补齐", 120, 350, 260, 22, { fontSize: 16, bold: true, color: C.green2 });
    addText(s, "学校 / 赛题编号 / 团队编号 / 团队名称 / 成员信息 / 实机截图 / MP4演示视频 / 最终部署地址", 410, 350, 700, 22, { fontSize: 14, color: "#E2F1EA" });
    addText(s, "谢谢", 88, 520, 220, 60, { fontSize: 42, bold: true, color: "white" });
    addText(s, "农智云瞰 · 让农情判断有据可依，让治理行动有迹可循", 88, 594, 720, 24, { fontSize: 17, color: "#A9CDBE" });
    addText(s, "15", 1160, 680, 56, 20, { fontSize: 11, bold: true, color: C.green2, alignment: "right" });
  }

  for (const [index, slide] of p.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(`${QA}/${stem}.png`, await p.export({ slide, format: "png", scale: 1 }));
    await fs.writeFile(`${QA}/${stem}.layout.json`, await (await slide.export({ format: "layout" })).text());
  }
  await writeBlob(`${QA}/deck-montage.webp`, await p.export({ format: "webp", montage: true, scale: 1 }));
  const pptx = await PresentationFile.exportPptx(p);
  await pptx.save(`${OUT}/待填写_待填写_待定团队_项目简介PPT.pptx`);
  console.log(`created ${p.slides.items.length} slides`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
