"""Build the competition demonstration video from verified project assets.

Run from the project root:
    .venv\Scripts\python.exe scripts\build_demo_video.py

The script intentionally keeps narration, evidence images and subtitles together so
the submitted MP4 can be regenerated after screenshots or figures are updated.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "submission_artifacts" / "video_work"
FRAME_DIR = WORK / "frames"
AUDIO_DIR = WORK / "audio"
CLIP_DIR = WORK / "clips"
OUTPUT = ROOT / "submission_artifacts" / "云穗智擎_山东建筑大学_张衡_项目演示视频.mp4"
WIDTH, HEIGHT, FPS = 1920, 1080, 25

FONT_REGULAR = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")

COLORS = {
    "bg": "#06120f",
    "panel": "#0c201b",
    "line": "#1d4b3d",
    "green": "#20d69b",
    "cyan": "#3bc7df",
    "blue": "#58a6ff",
    "yellow": "#f2c94c",
    "red": "#ff6b6b",
    "white": "#f4fbf8",
    "muted": "#91aaa1",
}


SEGMENTS = [
    {
        "id": "01_problem",
        "title": "问题与选题",
        "target_duration": 25,
        "narration": "县域农业的病虫害防控有四个老问题：发现滞后、数据分散、研判靠经验、植保资源平均分配。农智云瞰以山东省济宁市鱼台县为示范县域，把这四个问题变成可度量的数据问题。",
        "visuals": ["cover", "problem", "login"],
    },
    {
        "id": "02_data",
        "title": "数据基础与清洗",
        "target_duration": 55,
        "narration": "平台的数据底座是县域农情数据湖。明细层覆盖二十四个月、六个乡镇、八十个地块、五类作物，包含传感器逐时采集一百四十万条、气象站逐小时观测十万条、田间踏查六点六万条、测产小区实测一点四万条，合计一百五十九万条明细记录，按月分区、乡镇分文件落盘。真实采集必然有脏数据，我们按固定比例注入了丢包缺失、重传重复和传感器故障读数，让清洗环节有真实处理对象。Spark 清洗后剔除重复四千七百二十七条、越界与关键字段缺失三千三百三十二条，保留一百五十八万条，有效率百分之九十九点四九，每一张表的剔除量都可以逐条核对。",
        "visuals": ["data_scale", "data_quality", "data_partition"],
    },
    {
        "id": "03_spark",
        "title": "Spark 四层分析链路",
        "target_duration": 60,
        "narration": "离线分析以 Apache Spark 为主链路，不是可选扩展。明细层不进 ORM、不入业务库，业务库只消费 Spark 的产出。DWD 层做去重、值域过滤、缺失分级处理和时间口径统一；DWS 层按乡镇日和地块日两级汇聚，并用窗口函数计算近十四日历史病害压力的滚动均值，这是单点观测表达不了的累积效应，形成五万八千四百行地块日风险特征宽表；ADS 层用 Spark SQL 产出六张应用结果表。项目同时提供 Hive 四层建表脚本，可在有 Metastore 的环境里用同一套口径访问。",
        "visuals": ["architecture", "dws", "ads"],
    },
    {
        "id": "04_risk",
        "title": "风险挖掘与可解释归因",
        "target_duration": 50,
        "narration": "风险评分由空气湿度、降雨、土壤墒情、历史病害和积温五项因子加权，再乘以作物易感性系数。分级阈值不是拍出来的：我们对全量五万八千四百条地块日记录做分位数统计，取高风险五十二分、中风险三十六分，再对照主汛期实际发生率校核，让汛期高风险地块占比落在百分之十左右，与县域植保的资源承载能力匹配。以八月三十一日为例，全县高风险十四个地块、中风险三十六个，高风险集中在水稻和番茄。这与两者易感性高、又正处在稻瘟病和纹枯病高发期的农技规律一致。系统还会输出主导风险因子，回答这块地为什么风险高，并把结论一路推到各乡镇需要多少架次无人机、多少农技员、多少公斤药剂。",
        "visuals": ["risk_formula", "risk_threshold", "dispatch"],
    },
    {
        "id": "05_system",
        "title": "系统承载与业务闭环",
        "target_duration": 60,
        "narration": "在线系统把分析结论落到业务动作上。驾驶舱展示全县态势，地图按风险等级为地块着色并给出主导因子，病虫害识别返回病害名称、置信度、严重度、检测框和人工复核标记，预警可一键生成巡检任务并回收现场反馈，农技助手优先调用 RAGFlow 知识库并标注引用来源，最后归档为农情日报。需要说明的是：识别模型基于公开数据集 PlantDoc 和 IP102 训练，验证集 mAP50 分别为零点六五和零点四一，这些指标只代表公开数据集，不代表山东本地田间准确率，正式应用要补充本地样本并由农技专家复核。",
        "visuals": ["dashboard", "map", "disease", "model_evidence", "assistant", "report"],
    },
    {
        "id": "06_engineering",
        "title": "工程化与可复现",
        "target_duration": 25,
        "narration": "为了让分析结果可复核而不是一次性跑数，项目提供了与 Spark 同口径的 pandas 参考实现，比对脚本逐表逐字段校验两者结果。造数脚本固定随机种子，并对记录总量做断言，不足一百万条直接失败退出。全系统 Docker 一键部署。",
        "visuals": ["reproducible", "deployment"],
    },
    {
        "id": "07_close",
        "title": "从被动上报到主动决策",
        "target_duration": 15,
        "narration": "农智云瞰把县域农业的病虫害防控，从被动上报推进到数据驱动的主动预警和资源调度。",
        "visuals": ["closing", "dashboard"],
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def rounded(draw: ImageDraw.ImageDraw, xy, radius=18, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def fit_text(draw, text, box_width, size, bold=False):
    while size > 18 and draw.textbbox((0, 0), text, font=font(size, bold))[2] > box_width:
        size -= 2
    return font(size, bold)


def base_canvas(kicker: str, title: str, section: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg"])
    draw = ImageDraw.Draw(img)
    for x in range(0, WIDTH, 80):
        draw.line((x, 0, x, HEIGHT), fill="#0a211b", width=1)
    for y in range(0, HEIGHT, 80):
        draw.line((0, y, WIDTH, y), fill="#0a211b", width=1)
    draw.rectangle((0, 0, 18, HEIGHT), fill=COLORS["green"])
    draw.text((72, 55), kicker, font=font(25, True), fill=COLORS["green"])
    draw.text((72, 101), title, font=fit_text(draw, title, 1500, 58, True), fill=COLORS["white"])
    draw.text((1660, 66), section, font=font(23, True), fill=COLORS["muted"])
    draw.line((72, 185, 1848, 185), fill=COLORS["line"], width=2)
    draw.text((72, 1020), "农智云瞰 · 云穗智擎 · 山东建筑大学", font=font(20), fill=COLORS["muted"])
    return img, draw


def cover_frame() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), "#04100d")
    draw = ImageDraw.Draw(img)
    for i in range(13):
        y = 150 + i * 58
        draw.line((80, y, 1840, y), fill=(8, 47 + i * 2, 37 + i), width=1)
    draw.rectangle((0, 0, 22, HEIGHT), fill=COLORS["green"])
    draw.text((96, 132), "大数据与人工智能行业应用开发", font=font(30, True), fill=COLORS["green"])
    draw.text((96, 245), "农智云瞰", font=font(108, True), fill=COLORS["white"])
    draw.text((102, 385), "面向县域农业的病虫害识别、产量风险预测与农情决策大数据平台", font=font(38), fill="#c7ddd5")
    for i, (value, label) in enumerate([("159 万", "多源农情明细"), ("4 层", "Spark 数仓"), ("5 类", "AI 模型能力")]):
        x = 100 + i * 390
        rounded(draw, (x, 560, x + 340, 745), fill="#0b261f", outline=COLORS["line"], width=2)
        draw.text((x + 30, 595), value, font=font(54, True), fill=COLORS["green"] if i == 0 else COLORS["cyan"])
        draw.text((x + 30, 675), label, font=font(24), fill=COLORS["muted"])
    draw.text((100, 900), "参赛团队：云穗智擎  |  山东建筑大学 计算机与人工智能学院", font=font(26), fill=COLORS["white"])
    return img


def metric_frame(key: str, title: str, cards: list[tuple[str, str, str]], note: str) -> Image.Image:
    img, draw = base_canvas("县域农业数据资产", title, key)
    cols = 2 if len(cards) <= 4 else 3
    gap, left, top = 28, 72, 255
    card_w = (1776 - gap * (cols - 1)) // cols
    rows = math.ceil(len(cards) / cols)
    card_h = min(270, (680 - gap * (rows - 1)) // rows)
    for i, (value, label, accent) in enumerate(cards):
        row, col = divmod(i, cols)
        x, y = left + col * (card_w + gap), top + row * (card_h + gap)
        rounded(draw, (x, y, x + card_w, y + card_h), fill=COLORS["panel"], outline=COLORS["line"], width=2)
        draw.rectangle((x, y, x + 8, y + card_h), fill=accent)
        draw.text((x + 42, y + 42), value, font=font(54, True), fill=accent)
        draw.text((x + 42, y + 125), label, font=font(27), fill=COLORS["white"])
    draw.text((72, 948), note, font=font(24), fill=COLORS["muted"])
    return img


def architecture_frame() -> Image.Image:
    img, draw = base_canvas("Spark 主链路", "ODS → DWD → DWS → ADS → 业务闭环", "03 / 数据链路")
    stages = [
        ("ODS", "159 万条贴源明细", COLORS["cyan"]),
        ("DWD", "去重 · 校验 · 统一", COLORS["blue"]),
        ("DWS", "58,400 行特征宽表", COLORS["green"]),
        ("ADS", "六类应用结果表", COLORS["yellow"]),
        ("APP", "预警 · 巡检 · 调度", COLORS["red"]),
    ]
    for i, (name, desc, color) in enumerate(stages):
        x = 80 + i * 360
        rounded(draw, (x, 380, x + 280, 650), fill=COLORS["panel"], outline=color, width=3)
        draw.text((x + 30, 422), name, font=font(54, True), fill=color)
        draw.text((x + 30, 525), desc, font=font(23), fill=COLORS["white"])
        if i < len(stages) - 1:
            draw.line((x + 292, 515, x + 340, 515), fill=COLORS["muted"], width=4)
            draw.polygon([(x + 340, 503), (x + 360, 515), (x + 340, 527)], fill=COLORS["muted"])
    draw.text((80, 760), "明细数据不进入 ORM；业务库只消费 Spark 产出的 ADS 结果", font=font(31, True), fill=COLORS["green"])
    draw.text((80, 825), "同口径 pandas 参考实现用于逐表逐字段复核", font=font(26), fill=COLORS["muted"])
    return img


def risk_formula_frame() -> Image.Image:
    img, draw = base_canvas("可解释风险评分", "风险不是一个黑箱数字", "04 / 风险挖掘")
    rounded(draw, (78, 250, 1842, 445), fill="#0b251e", outline=COLORS["green"], width=2)
    formula = "风险分 =（湿度 + 降雨 + 土壤墒情 + 历史病害 + 积温）× 作物易感性"
    draw.text((130, 310), formula, font=fit_text(draw, formula, 1660, 40, True), fill=COLORS["white"])
    factors = [("空气湿度", "高湿放大病害压力"), ("降雨量", "连续降雨提高侵染概率"), ("土壤墒情", "过湿与涝害关联"), ("历史病害", "14 日窗口累积效应"), ("积温", "作物生育期约束")]
    for i, (name, desc) in enumerate(factors):
        x = 78 + i * 352
        rounded(draw, (x, 520, x + 320, 750), fill=COLORS["panel"], outline=COLORS["line"], width=2)
        draw.text((x + 25, 560), f"0{i + 1}", font=font(22, True), fill=COLORS["cyan"])
        draw.text((x + 25, 610), name, font=font(31, True), fill=COLORS["white"])
        draw.text((x + 25, 680), desc, font=font(20), fill=COLORS["muted"])
    draw.text((78, 850), "每个高风险地块同步返回 Top 风险因子，支持农技人员追溯判断依据。", font=font(29, True), fill=COLORS["green"])
    return img


def screenshot_frame(source: Path, kicker: str, title: str, section: str, note: str) -> Image.Image:
    img, draw = base_canvas(kicker, title, section)
    src = Image.open(source).convert("RGB")
    src = ImageEnhance.Contrast(src).enhance(1.04)
    box = (72, 225, 1848, 950)
    bw, bh = box[2] - box[0], box[3] - box[1]
    src.thumbnail((bw, bh), Image.Resampling.LANCZOS)
    x, y = box[0] + (bw - src.width) // 2, box[1] + (bh - src.height) // 2
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((x - 12, y - 12, x + src.width + 12, y + src.height + 12), 24, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    img.paste(src, (x, y))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((x - 2, y - 2, x + src.width + 2, y + src.height + 2), 10, outline=COLORS["line"], width=3)
    draw.text((72, 970), note, font=font(22), fill=COLORS["muted"])
    return img


def side_by_side_evidence() -> Image.Image:
    img, draw = base_canvas("真实训练证据", "公开数据集模型评估与边界说明", "05 / AI 模型")
    entries = [
        (ROOT / "data/generated/plantdoc_yolo_runs/plantdoc_v1/val_batch0_pred.jpg", "PlantDoc", "29 类病害 · mAP50 0.6542", COLORS["green"]),
        (ROOT / "data/generated/ip102_yolo_runs/ip102_yolo11n_v1/val_batch0_pred.jpg", "IP102", "102 类害虫 · mAP50 0.4133", COLORS["cyan"]),
    ]
    for i, (path, name, metric, accent) in enumerate(entries):
        x = 72 + i * 888
        rounded(draw, (x, 235, x + 850, 820), fill=COLORS["panel"], outline=COLORS["line"], width=2)
        src = Image.open(path).convert("RGB")
        src.thumbnail((790, 430), Image.Resampling.LANCZOS)
        px = x + (850 - src.width) // 2
        img.paste(src, (px, 275))
        draw = ImageDraw.Draw(img)
        draw.text((x + 30, 720), name, font=font(32, True), fill=accent)
        draw.text((x + 30, 770), metric, font=font(23), fill=COLORS["white"])
    rounded(draw, (72, 850, 1848, 955), fill="#251b12", outline=COLORS["yellow"], width=2)
    draw.text((105, 883), "指标仅代表公开验证集；山东本地田间部署前须补充本地样本并由农技专家复核。", font=font(28, True), fill=COLORS["yellow"])
    return img


def build_frames() -> dict[str, Path]:
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = ROOT / "artifacts"
    frames: dict[str, Image.Image] = {
        "cover": cover_frame(),
        "problem": metric_frame("01 / 行业痛点", "把农业治理难题变成可度量的数据问题", [("01", "发现滞后", COLORS["red"]), ("02", "数据分散", COLORS["cyan"]), ("03", "研判靠经验", COLORS["yellow"]), ("04", "资源平均分配", COLORS["blue"])], "示范场景：山东省济宁市鱼台县县域农业治理"),
        "data_scale": metric_frame("02 / 数据底座", "24 个月多源农情明细", [("140 万", "传感器逐时采集", COLORS["green"]), ("10 万", "气象站逐时观测", COLORS["cyan"]), ("6.6 万", "田间踏查记录", COLORS["yellow"]), ("1.4 万", "测产小区实测", COLORS["blue"])], "6 个乡镇 · 80 个地块 · 5 类作物 · 固定随机种子可复现"),
        "data_quality": metric_frame("02 / 清洗质量", "让脏数据成为可核验的处理对象", [("4,727", "重传重复记录剔除", COLORS["yellow"]), ("3,332", "越界与关键缺失剔除", COLORS["red"]), ("158 万", "清洗后有效记录", COLORS["green"]), ("99.49%", "总体数据有效率", COLORS["cyan"])], "每张表均保留输入量、剔除量与输出量统计，支持逐项审计。"),
        "data_partition": metric_frame("02 / 数据组织", "按月分区、按乡镇分文件", [("24", "月份分区", COLORS["green"]), ("6", "乡镇文件域", COLORS["cyan"]), ("4", "传感器 / 气象 / 踏查 / 测产", COLORS["blue"]), ("Parquet", "列式存储与分区裁剪", COLORS["yellow"])], "数据湖承担大规模明细处理，业务数据库只接收可直接服务页面的结果。"),
        "architecture": architecture_frame(),
        "dws": metric_frame("03 / DWS 特征层", "窗口计算表达累积病害压力", [("58,400", "地块-日风险特征记录", COLORS["green"]), ("14 日", "历史病害滚动窗口", COLORS["cyan"]), ("2 级", "乡镇-日 / 地块-日汇聚", COLORS["blue"]), ("5 因子", "天气、土壤与病害特征", COLORS["yellow"])], "单点观测无法表达累积效应，窗口函数将时间上下文写入特征。"),
        "ads": metric_frame("03 / ADS 应用层", "六类结果直接服务业务", [("风险排名", "各乡镇病虫害风险", COLORS["green"]), ("作物分布", "作物类型风险结构", COLORS["cyan"]), ("7 日趋势", "短期风险变化", COLORS["blue"]), ("产量预测", "产量与减产风险", COLORS["yellow"]), ("巡检优先级", "任务排序与负责人", COLORS["red"]), ("农资调度", "无人机、人员与药剂", COLORS["green"])], "Spark SQL 统一产出，FastAPI 读取并对前端提供稳定接口。"),
        "risk_formula": risk_formula_frame(),
        "risk_threshold": metric_frame("04 / 阈值标定", "从数据分布中确定风险等级", [("36 分", "中风险阈值 · 约 P80", COLORS["yellow"]), ("52 分", "高风险阈值 · 约 P96", COLORS["red"]), ("10.5%", "主汛期高风险占比", COLORS["green"]), ("58,400", "全量标定样本", COLORS["cyan"])], "分位数标定后再用主汛期发生率校核，使预警规模匹配县域植保承载能力。"),
        "dispatch": metric_frame("04 / 结果落地", "2026-08-31 风险研判与资源调度", [("14 个", "高风险地块", COLORS["red"]), ("36 个", "中风险地块", COLORS["yellow"]), ("水稻 / 番茄", "主要高风险作物", COLORS["cyan"]), ("架次 + 人员 + 药剂", "量化调度建议", COLORS["green"])], "分析结果不仅说明哪里风险高，还说明为什么高、下一步如何处置。"),
        "login": screenshot_frame(artifacts / "desktop-login.png", "角色化访问", "县域智慧农业指挥中心", "01 / 系统入口", "县域管理员、农技专家与合作社用户按职责进入业务空间。"),
        "dashboard": screenshot_frame(artifacts / "desktop-dashboard.png", "态势总览", "县域农情风险一屏统览", "05 / 驾驶舱", "KPI、趋势、作物结构与待办调度在同一工作面完成研判。"),
        "map": screenshot_frame(artifacts / "desktop-map.png", "空间研判", "地块级风险地图与画像", "05 / 风险地图", "按乡镇、作物和风险等级筛选，点击地块查看主导因子与巡检建议。"),
        "disease": screenshot_frame(artifacts / "desktop-disease.png", "计算机视觉", "叶片图像识别与人工复核", "05 / 病虫害识别", "检测结果同时返回置信度、严重度、疑似区域和处置建议。"),
        "assistant": screenshot_frame(artifacts / "desktop-assistant-ragflow.png", "知识增强问答", "RAGFlow 农技助手", "05 / AI 助手", "回答同时引用农技知识文档与当前系统风险数据，不做无来源闲聊。"),
        "report": screenshot_frame(artifacts / "desktop-reports.png", "成果归档", "县域农情风险日报", "05 / 报告生成", "KPI、风险地块、模型预测与处置建议一键汇总并导出。"),
        "model_evidence": side_by_side_evidence(),
        "reproducible": metric_frame("06 / 可复现分析", "Spark 与 pandas 双实现口径互校", [("逐表", "六类 ADS 结果表", COLORS["green"]), ("逐字段", "键、数值与排序", COLORS["cyan"]), ("固定种子", "数据可重复生成", COLORS["blue"]), (">100 万", "规模断言不通过即退出", COLORS["yellow"])], "双实现不是两套口径，而是生产链路与参考链路的相互校验。"),
        "deployment": metric_frame("06 / 工程部署", "前后端分离与容器化交付", [("Next.js", "可视化与业务交互", COLORS["green"]), ("FastAPI", "REST API 与 OpenAPI", COLORS["cyan"]), ("PostgreSQL", "业务数据与状态持久化", COLORS["blue"]), ("Docker", "一键启动与环境一致性", COLORS["yellow"])], "日志、错误处理、环境变量、初始化脚本与测试数据均随项目交付。"),
        "closing": metric_frame("07 / 项目价值", "县域农业风险治理闭环", [("发现", "多源数据持续感知", COLORS["cyan"]), ("研判", "模型预测与风险归因", COLORS["green"]), ("巡检", "预警转为责任任务", COLORS["yellow"]), ("处置", "资源调度与结果回写", COLORS["red"])], "从被动上报走向主动预警，让每一次植保资源投入都有数据依据。"),
    }
    paths = {}
    for name, image in frames.items():
        path = FRAME_DIR / f"{name}.png"
        image.save(path, quality=95)
        paths[name] = path
    return paths


def _ps_b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


async def synthesize_audio() -> list[Path]:
    """Create deterministic offline narration with the installed Chinese voice."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    for segment in SEGMENTS:
        path = AUDIO_DIR / f"{segment['id']}.wav"
        text64 = _ps_b64(segment["narration"])
        path64 = _ps_b64(str(path.resolve()))
        script = (
            "Add-Type -AssemblyName System.Speech;"
            f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text64}'));"
            f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path64}'));"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.SelectVoice('Microsoft Huihui Desktop');$s.Rate=-1;$s.Volume=100;"
            "$s.SetOutputToWaveFile($p);$s.Speak($t);$s.Dispose();"
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        subprocess.run(["powershell", "-NoProfile", "-EncodedCommand", encoded], check=True)
        outputs.append(path)
    return outputs


def ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("Missing imageio-ffmpeg. Run: .venv\\Scripts\\python.exe -m pip install imageio-ffmpeg") from exc


def run(command: list[str]) -> None:
    print(" ".join(command[:8]), "...")
    subprocess.run(command, cwd=ROOT, check=True)


def duration(ffmpeg: str, path: Path) -> float:
    result = subprocess.run([ffmpeg, "-i", str(path), "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise RuntimeError(f"Cannot read duration: {path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def ts(seconds: float) -> str:
    ms = round((seconds - int(seconds)) * 1000)
    whole = int(seconds)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d},{ms:03d}"


def subtitle_chunks(text: str) -> list[str]:
    chunks = [item.strip() for item in re.split(r"(?<=[。；！])", text) if item.strip()]
    result = []
    for chunk in chunks:
        if len(chunk) <= 34:
            result.append(chunk)
            continue
        parts = [part for part in re.split(r"(?<=[，、])", chunk) if part]
        buffer = ""
        for part in parts:
            if buffer and len(buffer + part) > 34:
                result.append(buffer)
                buffer = part
            else:
                buffer += part
        if buffer:
            result.append(buffer)
    return result


def write_subtitles(durations: list[float]) -> Path:
    lines, index, offset = [], 1, 0.0
    for segment, seg_duration in zip(SEGMENTS, durations):
        chunks = subtitle_chunks(segment["narration"])
        total_weight = sum(max(4, len(chunk)) for chunk in chunks)
        cursor = offset + 0.2
        usable = max(1.0, seg_duration - 0.4)
        for chunk in chunks:
            span = usable * max(4, len(chunk)) / total_weight
            end = min(offset + seg_duration - 0.05, cursor + span)
            lines.extend([str(index), f"{ts(cursor)} --> {ts(end)}", chunk, ""])
            cursor = end
            index += 1
        offset += seg_duration
    path = WORK / "演示视频字幕.srt"
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return path


def build_video(frames: dict[str, Path], audio_files: list[Path]) -> None:
    ffmpeg = ffmpeg_path()
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    durations = [float(segment["target_duration"]) for segment in SEGMENTS]
    subtitle = write_subtitles(durations)
    clips = []
    for seg_index, (segment, seg_duration) in enumerate(zip(SEGMENTS, durations)):
        visuals = segment["visuals"]
        each = seg_duration / len(visuals)
        for visual_index, visual in enumerate(visuals):
            clip = CLIP_DIR / f"{seg_index:02d}_{visual_index:02d}.mp4"
            fade_out = max(0.2, each - 0.45)
            vf = (
                f"scale={WIDTH}:{HEIGHT},"
                f"zoompan=z='min(pzoom+0.00009,1.035)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d=1:s={WIDTH}x{HEIGHT}:fps={FPS},"
                f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out:.3f}:d=0.35,format=yuv420p"
            )
            run([ffmpeg, "-y", "-loop", "1", "-i", str(frames[visual]), "-t", f"{each:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", str(clip)])
            clips.append(clip)

    video_list = WORK / "video_concat.txt"
    video_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    visual_video = WORK / "visual.mp4"
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(video_list), "-c", "copy", str(visual_video)])

    timed_audio_dir = WORK / "audio_timed"
    timed_audio_dir.mkdir(parents=True, exist_ok=True)
    timed_audio = []
    for segment, source, target in zip(SEGMENTS, audio_files, durations):
        raw_duration = duration(ffmpeg, source)
        # Leave a brief visual pause at the start and end of each chapter.
        speech_target = max(1.0, target - 1.4)
        tempo = max(0.5, min(2.0, raw_duration / speech_target))
        timed = timed_audio_dir / f"{segment['id']}.m4a"
        run([ffmpeg, "-y", "-i", str(source), "-af", f"atempo={tempo:.6f},apad=pad_dur=2", "-t", f"{target:.3f}", "-c:a", "aac", "-b:a", "144k", str(timed)])
        timed_audio.append(timed)

    audio_list = WORK / "audio_concat.txt"
    audio_list.write_text("\n".join(f"file '{p.as_posix()}'" for p in timed_audio), encoding="utf-8")
    narration = WORK / "narration.m4a"
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list), "-c:a", "aac", "-b:a", "144k", str(narration)])

    subtitle_filter = "subtitles='" + subtitle.relative_to(ROOT).as_posix() + "':force_style='FontName=Microsoft YaHei,FontSize=17,PrimaryColour=&H00FFFFFF,OutlineColour=&HAA000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=40,Alignment=2'"
    run([ffmpeg, "-y", "-i", str(visual_video), "-i", str(narration), "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "144k", "-movflags", "+faststart", "-shortest", str(OUTPUT)])

    report = {
        "output": str(OUTPUT),
        "duration_seconds": round(duration(ffmpeg, OUTPUT), 2),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "video_codec": "H.264",
        "audio_codec": "AAC",
        "size_mb": round(OUTPUT.stat().st_size / 1024 / 1024, 2),
        "subtitle": str(subtitle),
        "narration_voice": "Microsoft Huihui Desktop",
    }
    (WORK / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    frames = build_frames()
    audio_files = asyncio.run(synthesize_audio())
    build_video(frames, audio_files)


if __name__ == "__main__":
    main()
