"""生成《农智云瞰》参赛演示 PPT（项目简介PPT）。

赛题：山东省大学生软件设计大赛 · 大数据与人工智能行业应用开发

内容按赛题通知对 PPT 的要求编排，覆盖背景、需求、方案、技术实现、演示效果、
创新点与团队介绍七项；页面配比参照通知的评分指标（行业应用价值 25%、
技术创新性 25%、工程实现质量 30%、文档与展示 20%）。

视觉为县域农业主题的深绿 + 麦色配色，地块热力网格作为贯穿全篇的图形母题。

用法::

    python scripts/build_pptx.py
    python scripts/build_pptx.py --out submission_artifacts/xxx.pptx
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- 设计令牌

W, H = 12192000, 6858000            # 16:9 画布
MARGIN = 609600
CONTENT_W = 10972800

INK = RGBColor(0x0E, 0x22, 0x1C)
INK_SOFT = RGBColor(0x23, 0x33, 0x2D)
MUTED = RGBColor(0x5C, 0x71, 0x68)
FAINT = RGBColor(0x93, 0xA6, 0x9D)

BRAND = RGBColor(0x14, 0xC2, 0x8C)
BRAND_DEEP = RGBColor(0x0B, 0x7A, 0x5A)
TEAL = RGBColor(0x0E, 0xA5, 0xA5)
GOLD = RGBColor(0xC9, 0x9A, 0x2E)
AMBER = RGBColor(0xD9, 0x8B, 0x1E)
BLUE = RGBColor(0x2C, 0x7B, 0xB6)
CLAY = RGBColor(0xB5, 0x6B, 0x3A)

WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RULE = RGBColor(0xD6, 0xE8, 0xDE)
WASH = RGBColor(0xEC, 0xF8, 0xF2)
GRAIN = RGBColor(0xF8, 0xF4, 0xE9)
CARD_DARK = RGBColor(0x10, 0x30, 0x28)
DIVIDER = RGBColor(0x2B, 0x68, 0x57)
ON_DARK = RGBColor(0xD9, 0xF3, 0xE8)
ON_DARK_SOFT = RGBColor(0x8F, 0xC9, 0xB5)
ON_DARK_DIM = RGBColor(0x6F, 0x94, 0x86)

ACCENTS = [BRAND_DEEP, TEAL, GOLD, BLUE, CLAY, AMBER]
FOOTER = "农智云瞰 · 山东省大学生软件设计大赛 · 大数据与人工智能行业应用开发"

HEAT = [RGBColor(0x1A, 0x3D, 0x33), RGBColor(0x1E, 0x5A, 0x46),
        RGBColor(0x18, 0x8A, 0x66), RGBColor(0x14, 0xC2, 0x8C),
        RGBColor(0xC9, 0x9A, 0x2E), RGBColor(0xD9, 0x6B, 0x2E)]


# ---------------------------------------------------------------- 基础绘制


def rect(slide, x, y, w, h, fill=None, shape=MSO_SHAPE.RECTANGLE):
    sh = slide.shapes.add_shape(shape, Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    sh.line.fill.background()
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    return sh


def round_rect(slide, x, y, w, h, fill=None, adj=0.14):
    sh = rect(slide, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE)
    try:
        sh.adjustments[0] = adj
    except Exception:  # noqa: BLE001
        pass
    return sh


def text(slide, x, y, w, h, content, size, color=INK, bold=False, align=PP_ALIGN.LEFT,
         line=None, space_after=0, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    items = content if isinstance(content, (list, tuple)) else [content]
    for i, item in enumerate(items):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        if line:
            para.line_spacing = line
        run = para.add_run()
        run.text = item
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return box


def new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


# 色块出现频次：以低风险的深绿为主，高风险的金/橙只作少量热点，
# 让母题读起来像一张县域风险分布图，而不是彩色马赛克。
HEAT_WEIGHTS = [0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4, 5]


def heat_grid(slide, x, y, cell, gap, cols, rows, seed=7):
    """地块热力网格母题：象征县域地块的风险分布，贯穿封面与结语。"""
    v = seed
    for r in range(rows):
        for c in range(cols):
            v = (v * 1103515245 + 12345) & 0x7FFFFFFF
            if (v >> 8) % 5 == 0:          # 留白，避免铺满
                continue
            idx = HEAT_WEIGHTS[(v >> 16) % len(HEAT_WEIGHTS)]
            rect(slide, x + c * (cell + gap), y + r * (cell + gap), cell, cell, HEAT[idx])


# ---------------------------------------------------------------- 版式组件


def section_header(slide, no, section, sub, title, desc=None):
    round_rect(slide, MARGIN, 388620, 400050, 219075, BRAND_DEEP, adj=0.5)
    text(slide, MARGIN, 423000, 400050, 160000, f"{no:02d}", 8.5, WHITE,
         bold=True, align=PP_ALIGN.CENTER)
    text(slide, MARGIN + 495300, 423000, 2400000, 180000, section, 9.0, BRAND_DEEP, bold=True)
    chev_x = MARGIN + 495300 + len(section) * 118000
    text(slide, chev_x, 423000, 160000, 180000, "»", 9.0, RULE, bold=True)
    text(slide, chev_x + 200000, 423000, 4200000, 180000, sub, 9.0, MUTED)
    text(slide, MARGIN, 723900, 9800000, 457200, title, 22.5, INK, bold=True)
    if desc:
        text(slide, MARGIN, 1219200, 10300000, 266700, desc, 10.0, MUTED)
    rect(slide, MARGIN, 1600200, 1200000, 12700, BRAND)
    rect(slide, MARGIN + 1200000, 1600200, CONTENT_W - 1200000, 12700, RULE)


def page_footer(slide, no):
    text(slide, MARGIN, 6496050, 7239000, 171450, FOOTER, 7.0, FAINT)
    text(slide, 11049000, 6470000, 533400, 190500, f"{no:02d}", 8.5,
         BRAND_DEEP, bold=True, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, accent, title, desc, title_size=13.0, fill=WHITE):
    rect(slide, x, y, w, h, fill)
    rect(slide, x, y, w, 47625, accent)
    text(slide, x + 228600, y + 190500, w - 419100, 300000, title, title_size, INK, bold=True)
    if desc:
        text(slide, x + 228600, y + 590000, w - 419100, h - 700000, desc, 9.0, MUTED, line=1.3)


def bullet(slide, x, y, w, content, size=11.0, color=INK_SOFT, dot=BRAND, h=371475):
    rect(slide, x, y + 60000, 76200, 76200, dot)
    text(slide, x + 196850, y, w, h, content, size, color, line=1.25)


NUMERIC = re.compile(r"^[\d,.\s%×≥≤+\-/]+$")


def data_table(slide, x, y, w, rows, col_w, head_fill=INK, size=9.0, row_h=304800,
               zebra=WASH, mark_cols=()):
    widths = [int(w * c / sum(col_w)) for c in col_w]
    numeric_col = [
        all(NUMERIC.match(str(r[c])) for r in rows[1:] if str(r[c]).strip())
        and any(str(r[c]).strip() for r in rows[1:])
        for c in range(len(rows[0]))
    ]
    for r, row in enumerate(rows):
        cy = y + r * row_h
        if r == 0:
            rect(slide, x, cy, w, row_h, head_fill)
        elif r % 2 == 0:
            rect(slide, x, cy, w, row_h, zebra)
        cx = x
        for c, cell in enumerate(row):
            s = str(cell)
            centered = c in mark_cols
            align = PP_ALIGN.CENTER if centered else (
                PP_ALIGN.RIGHT if numeric_col[c] else PP_ALIGN.LEFT)
            col = WHITE if r == 0 else INK_SOFT
            bold = r == 0
            if r > 0 and centered:
                if s == "✔":
                    col, bold = BRAND_DEEP, True
                elif s in ("—", "-"):
                    col = FAINT
            text(slide, cx + 114300, cy + 71000, widths[c] - 152400, row_h - 110000, s,
                 size, col, bold=bold, align=align)
            cx += widths[c]
    return y + len(rows) * row_h


def kpi_tile(slide, x, y, w, h, accent, value, unit, label, vsize=24.0):
    rect(slide, x, y, w, h, WHITE)
    rect(slide, x, y, w, 47625, accent)
    text(slide, x + 209550, y + 190500, w - 400000, 420000, value, vsize, INK, bold=True)
    text(slide, x + 209550, y + 660000, w - 400000, 200000, unit, 8.5, accent, bold=True)
    text(slide, x + 209550, y + 880000, w - 400000, 240000, label, 9.0, MUTED, line=1.2)


def badge(slide, x, y, w, h, fill, label, color=WHITE, size=9.5):
    round_rect(slide, x, y, w, h, fill, adj=0.35)
    text(slide, x, y + h / 2 - 95000, w, 200000, label, size, color, bold=True,
         align=PP_ALIGN.CENTER)


def shot_placeholder(slide, x, y, w, h, label, hint=""):
    rect(slide, x, y, w, h, WASH)
    rect(slide, x, y, w, 38100, BRAND)
    text(slide, x, y + h / 2 - 260000, w, 280000, label, 11.0, BRAND_DEEP,
         bold=True, align=PP_ALIGN.CENTER)
    if hint:
        text(slide, x + 300000, y + h / 2 + 60000, w - 600000, 300000, hint, 8.5, MUTED,
             align=PP_ALIGN.CENTER, line=1.25)


def shot_image(slide, x, y, w, h, path):
    """把实机截图按原比例居中嵌入占位框，不裁剪、不拉伸。"""
    from PIL import Image as _Image

    rect(slide, x, y, w, h, WASH)
    rect(slide, x, y, w, 38100, BRAND)
    iw, ih = _Image.open(path).size
    inner_y = y + 38100
    inner_h = h - 38100
    scale = min(w / iw, inner_h / ih)
    dw, dh = int(iw * scale), int(ih * scale)
    slide.shapes.add_picture(str(path), Emu(int(x + (w - dw) / 2)),
                             Emu(int(inner_y + (inner_h - dh) / 2)),
                             Emu(dw), Emu(dh))


# ---------------------------------------------------------------- 页面


def s01_cover(prs):
    s = new_slide(prs)
    rect(s, 0, 0, W, H, INK)
    rect(s, 0, 0, 152400, H, BRAND)
    heat_grid(s, 6950000, 0, 342900, 38100, 14, 18, seed=20260506)

    text(s, 838200, 900000, 5400000, 220000,
         "山东省大学生软件设计大赛 · 大数据与人工智能行业应用开发", 9.5, BRAND, bold=True)
    text(s, 800100, 1390650, 6096000, 900000, "农智云瞰", 52.0, WHITE, bold=True)
    rect(s, 838200, 2450000, 762000, 22225, GOLD)
    text(s, 838200, 2640000, 5600000, 700000,
         "面向县域农业的农情大数据分析与病虫害风险挖掘平台", 15.5, ON_DARK, line=1.35)

    for i, (v, u) in enumerate([("159万", "条明细数据"), ("4层", "Spark 数仓"), ("5类", "AI 模型")]):
        x = 838200 + i * 1800000
        text(s, x, 3700000, 1700000, 380000, v, 20.0, BRAND, bold=True)
        text(s, x, 4100000, 1700000, 200000, u, 9.0, ON_DARK_SOFT)

    rect(s, 838200, 4620000, 4800000, 9525, DIVIDER)
    text(s, 838200, 4840000, 5600000, 520000,
         ["行业方向：智慧农业与乡村治理", "示范县域：山东省济宁市鱼台县"],
         10.0, ON_DARK_SOFT, line=1.45)

    text(s, 838200, 5880000, 5600000, 520000,
         ["云穗智擎　|　山东建筑大学 计算机与人工智能学院", "队长：张衡　指导教师：刘新锋"],
         9.5, ON_DARK_DIM, line=1.45)
    text(s, 838200, 6470000, 533400, 190500, "01", 8.5, BRAND, bold=True)
    return s


def s02_agenda(prs):
    s = new_slide(prs)
    section_header(s, 0, "目录", "CONTENTS", "从行业问题到可执行的调度决策",
                   "全篇按赛题评分的四个维度组织：行业应用价值、技术创新性、工程实现质量、文档与展示。")
    groups = [
        (BRAND_DEEP, "一 · 行业与需求",
         ["项目背景：政策导向", "项目背景：行业痛点", "需求分析：应用对象与场景"]),
        (TEAL, "二 · 方案与数据",
         ["总体方案：系统架构", "数据基础：多源数据与规模", "数据治理：清洗与质量度量"]),
        (GOLD, "三 · 技术与创新",
         ["技术实现：Spark 四层数仓", "特征工程：时序窗口", "风险挖掘：因子与阈值", "AI 模型矩阵"]),
        (BLUE, "四 · 结论与价值",
         ["分析结论与农技校验", "应用闭环：分析到调度", "演示效果", "工程质量与可复现",
          "竞品对比 · 应用价值 · 团队"]),
    ]
    for i, (accent, name, items) in enumerate(groups):
        x = 609600 + i * 2800350
        rect(s, x, 1950000, 2476500, 3450000, WHITE)
        rect(s, x, 1950000, 2476500, 47625, accent)
        text(s, x + 228600, 2160000, 2100000, 300000, name, 12.5, INK, bold=True)
        for j, item in enumerate(items):
            text(s, x + 228600, 2640000 + j * 430000, 2100000, 400000, f"·  {item}",
                 9.5, MUTED, line=1.25)
    page_footer(s, 2)
    return s


def s03_policy(prs):
    s = new_slide(prs)
    section_header(s, 1, "项目背景", "政策导向", "数字农业是国家明确的产业方向",
                   "人工智能与大数据的融合正在重塑农业生产组织方式，县域是政策落地的关键单元。")
    items = [
        (BRAND_DEEP, "数字乡村", "《数字乡村发展战略纲要》提出推进农业数字化转型，"
                              "以信息化培育新动能、用数字化引领驱动农业农村现代化。"),
        (TEAL, "智慧农业", "农业农村部推动物联网、大数据、人工智能在农业生产经营中的集成应用，"
                        "建设农业农村大数据体系。"),
        (GOLD, "植保减量", "农药化肥减量增效要求精准施药：只有先识别出哪块地真正需要防治，"
                        "才能把投入从平摊变成靶向。"),
        (BLUE, "新质生产力", "大数据产业规模已达万亿量级，数据资源正加速向生产要素转变，"
                          "农业是数据价值挖掘潜力最大的行业之一。"),
    ]
    for i, (accent, title, desc) in enumerate(items):
        x = 609600 + (i % 2) * 5672400
        y = 1950000 + (i // 2) * 1480000
        card(s, x, y, 5300400, 1300000, accent, title, desc)

    rect(s, MARGIN, 5050000, CONTENT_W, 1150000, GRAIN)
    text(s, 914400, 5220000, 5000000, 260000, "本项目的切入点", 13.0, INK, bold=True)
    text(s, 914400, 5570000, 10200000, 520000,
         "政策要的是「精准」，而精准的前提是把分散、带噪的农情数据变成可排序、可归因的量化结论。"
         "农智云瞰做的正是这一段：从原始观测一路推到乡镇级的资源投放清单。",
         10.5, INK_SOFT, line=1.35)
    page_footer(s, 3)
    return s


def s04_painpoint(prs):
    s = new_slide(prs)
    section_header(s, 2, "项目背景", "行业痛点", "县域植保的四个老问题，本质都是数据问题",
                   "痛点来自县域农技站的实际工作流程：踏查、上报、研判、派工。")
    pains = [
        (BRAND_DEEP, "发现滞后", "症状出现 → 逐级上报 → 形成决策，往往数天，错过最佳防治窗口"),
        (TEAL, "数据孤岛", "气象站、物联网终端、农技踏查、统计测产各成一摊，格式与时间口径不一"),
        (GOLD, "研判凭经验", "风险只有「轻中重」的定性描述，无法全县排序，也说不清成因"),
        (BLUE, "资源平摊", "无人机、农技员、药剂按面积平均投放，与真实风险分布错位"),
    ]
    for i, (accent, title, desc) in enumerate(pains):
        card(s, 609600 + i * 2800350, 1950000, 2476500, 1400000, accent, title, desc)

    rect(s, MARGIN, 3600000, CONTENT_W, 2400000, WASH)
    text(s, 914400, 3790000, 5000000, 280000, "传统流程 vs 本项目流程", 13.5, INK, bold=True)

    text(s, 914400, 4300000, 1300000, 220000, "传统", 10.0, MUTED, bold=True)
    for i, stepname in enumerate(["农户发现", "合作社上报", "农技站汇总", "经验研判", "平均派工"]):
        x = 2300000 + i * 1800000
        rect(s, x, 4240000, 1540000, 330000, WHITE)
        text(s, x, 4312000, 1540000, 220000, stepname, 9.0, MUTED, align=PP_ALIGN.CENTER)
        if i < 4:
            text(s, x + 1570000, 4290000, 200000, 250000, "›", 12.0, RULE, bold=True)

    text(s, 914400, 5020000, 1300000, 220000, "本项目", 10.0, BRAND_DEEP, bold=True)
    for i, stepname in enumerate(["多源自动采集", "Spark 清洗治理", "特征与风险挖掘", "因子归因", "靶向调度"]):
        x = 2300000 + i * 1800000
        rect(s, x, 4960000, 1540000, 330000, BRAND_DEEP)
        text(s, x, 5032000, 1540000, 220000, stepname, 9.0, WHITE, bold=True, align=PP_ALIGN.CENTER)
        if i < 4:
            text(s, x + 1570000, 5010000, 200000, 250000, "›", 12.0, BRAND, bold=True)

    text(s, 914400, 5560000, 10200000, 320000,
         "差别不在于多了几个页面，而在于中间三步——治理、挖掘、归因——在传统流程里根本不存在。",
         10.5, INK_SOFT)
    page_footer(s, 4)
    return s


def s05_requirement(prs):
    s = new_slide(prs)
    section_header(s, 3, "需求分析", "应用对象与场景", "三类用户，三条各自闭合的工作流",
                   "系统以「谁在什么时候需要哪个结论」倒推功能，而不是先有功能再找用户。")
    roles = [
        (BRAND_DEEP, "县域农业主管部门", "每日掌握全县风险态势、安排植保资源",
         ["驾驶舱核心指标与趋势", "乡镇风险排名", "无人机架次 / 药剂用量测算", "农情日报归档"]),
        (TEAL, "农技站 / 农技专家", "研判具体地块成因，下派与复核巡检",
         ["地块风险因子分解", "病虫害图像识别与复核标记", "巡检优先级 Top 30", "AI 农技知识问答"]),
        (GOLD, "合作社 / 种植大户", "上报田间情况，接收并反馈任务",
         ["自有地块风险画像", "手机拍照上报识别", "巡检任务接收与回写", "处置结果留痕"]),
    ]
    for i, (accent, name, goal, feats) in enumerate(roles):
        x = 609600 + i * 3771900
        rect(s, x, 1950000, 3543300, 3400000, WHITE)
        rect(s, x, 1950000, 3543300, 47625, accent)
        text(s, x + 266700, 2150000, 3000000, 300000, name, 13.5, INK, bold=True)
        text(s, x + 266700, 2570000, 3050000, 420000, goal, 9.5, accent, line=1.25)
        rect(s, x + 266700, 3090000, 3000000, 9525, RULE)
        for j, f in enumerate(feats):
            bullet(s, x + 266700, 3280000 + j * 460000, 2750000, f, size=9.5,
                   dot=accent, h=420000)
    page_footer(s, 5)
    return s


def s06_architecture(prs):
    s = new_slide(prs)
    section_header(s, 4, "总体方案", "系统架构", "两条链路，一个耦合点",
                   "离线分析链路承担全部明细计算，在线服务链路只消费分析产出——这是整套设计的核心约束。")

    rect(s, MARGIN, 1900000, 6600000, 3450000, WHITE)
    text(s, 914400, 2070000, 5000000, 260000, "离线分析链路（Apache Spark）", 12.5, INK, bold=True)
    layers = [("ODS 贴源层", "gzip CSV · 月分区", "1,591,545 条", BRAND_DEEP),
              ("DWD 清洗层", "Parquet + Snappy", "1,583,486 条", TEAL),
              ("DWS 汇总层", "地块 × 日 宽表", "58,400 行", GOLD),
              ("ADS 应用层", "JSON / CSV", "6 张结果表", BLUE)]
    for i, (name, fmt, cnt, accent) in enumerate(layers):
        y = 2500000 + i * 650000
        rect(s, 914400, y, 5990000, 540000, WASH if i % 2 == 0 else WHITE)
        rect(s, 914400, y, 38100, 540000, accent)
        text(s, 1110000, y + 95000, 1800000, 250000, name, 11.0, INK, bold=True)
        text(s, 1110000, y + 335000, 2300000, 190000, fmt, 8.0, MUTED)
        text(s, 4400000, y + 145000, 1600000, 270000, cnt, 11.0, accent, bold=True)
        if i < 3:
            text(s, 6350000, y + 155000, 400000, 270000, "↓", 11.0, RULE, bold=True)

    rect(s, 7600000, 1900000, 3982400, 3450000, CARD_DARK)
    text(s, 7880000, 2070000, 3400000, 260000, "在线服务链路", 12.5, WHITE, bold=True)
    text(s, 7880000, 2450000, 3500000, 760000,
         ["业务库 PostgreSQL 16", "FastAPI + SQLAlchemy + JWT", "Next.js + Recharts + Leaflet"],
         9.5, ON_DARK, line=1.55)
    rect(s, 7880000, 3330000, 3400000, 9525, DIVIDER)
    text(s, 7880000, 3500000, 3400000, 240000, "在线模型能力", 9.0, ON_DARK_SOFT, bold=True)
    text(s, 7880000, 3810000, 3500000, 1100000,
         ["YOLO11n 病虫害检测", "RandomForest 风险 / 产量", "IsolationForest 异常检测",
          "RAGFlow 农技问答（本地降级）"],
         9.0, ON_DARK, line=1.55)

    rect(s, MARGIN, 5550000, CONTENT_W, 700000, GRAIN)
    text(s, 914400, 5720000, 10200000, 420000,
         "关键约束：明细数据不进 ORM、不入业务库；业务库只承载 ADS 结果与用户操作记录。"
         "两条链路的唯一耦合点，是 ADS 结果表的单向回流。",
         10.5, INK_SOFT, line=1.3)
    page_footer(s, 6)
    return s


def s07_data(prs):
    s = new_slide(prs)
    section_header(s, 5, "数据基础", "多源数据与规模", "数据从哪来，有多少，长什么样",
                   "覆盖 2024-09 至 2026-08 共 24 个月、6 个乡镇、80 个地块、5 类作物。")
    rows = [
        ["ODS 明细表", "采集粒度", "记录数"],
        ["ods_sensor_raw　物联网土壤环境传感器", "地块 × 2 终端 × 730 天 × 每日 12 次", "1,405,790"],
        ["ods_weather_raw　乡镇自动气象站", "乡镇 × 730 天 × 逐小时", "105,422"],
        ["ods_pest_scout_raw　病虫害田间踏查", "每日约 90 条踏查记录", "65,890"],
        ["ods_yield_plot_raw　测产小区实测", "地块 × 年 × 两季 × 30 小区", "14,443"],
        ["合计", "", "1,591,545"],
    ]
    data_table(s, MARGIN, 1900000, 6900000, rows, [5, 5, 2], row_h=323850)

    rect(s, 7700000, 1900000, 3882400, 1900000, CARD_DARK)
    text(s, 7980000, 2070000, 3200000, 240000, "落盘形态", 11.0, WHITE, bold=True)
    text(s, 7980000, 2400000, 3400000, 800000,
         ["data/lake/ods/<表>/", "　dt=YYYY-MM/", "　　part-<乡镇编码>.csv.gz"],
         9.5, ON_DARK, line=1.4)
    rect(s, 7980000, 3250000, 3300000, 9525, DIVIDER)
    text(s, 7980000, 3420000, 3400000, 300000, "438 个分区文件 · gzip 后 39.0 MB",
         9.0, ON_DARK_SOFT)

    rect(s, 7700000, 3950000, 3882400, 1800000, WASH)
    text(s, 7980000, 4120000, 3200000, 240000, "为什么按月分区", 11.0, INK, bold=True)
    text(s, 7980000, 4450000, 3350000, 1200000,
         "月分区 + 乡镇分文件使 Spark 读取时可做分区裁剪，避免全量扫描；"
         "贴源层保留文本格式，贴近真实采集的落地形态并完整保留脏数据。",
         9.0, MUTED, line=1.35)

    text(s, MARGIN, 3950000, 6900000, 1800000,
         "气温、湿度、降水、墒情与病虫害发生程度均按鲁西南暖温带季风气候与农技规律建模："
         "年均气温约 14℃，年降水量约 675 mm 且七成集中在 6—9 月主汛期；水稻田常年淹水，"
         "墒情显著高于旱作；病株率在盛夏达峰。固定随机种子 SEED=20260506，评委可完全复现。"
         "赛题通知 2.1 明确允许基于真实或仿真数据完成实践。",
         10.0, INK_SOFT, line=1.4)
    page_footer(s, 7)
    return s


def s08_quality(prs):
    s = new_slide(prs)
    section_header(s, 6, "数据治理", "清洗与质量度量", "刻意造脏，再把清洗效果逐条量化",
                   "真实采集必然有丢包、重传与设备故障；不造脏，就无法证明治理能力。")
    for i, (accent, t, d) in enumerate([
        (BRAND_DEEP, "0.8%", "字段缺失 · 模拟采集丢包与人工漏填"),
        (TEAL, "0.3%", "整行重复 · 模拟采集端重传与断网补传"),
        (GOLD, "0.2%", "越界读数 · 模拟传感器故障输出 -999 / 9999"),
    ]):
        x = 609600 + i * 3771900
        rect(s, x, 1900000, 3543300, 880000, WHITE)
        rect(s, x, 1900000, 3543300, 47625, accent)
        text(s, x + 228600, 2040000, 1400000, 340000, t, 19.0, INK, bold=True)
        text(s, x + 228600, 2440000, 3100000, 300000, d, 9.0, MUTED)

    rows = [
        ["ODS 表", "原始", "去重剔除", "越界/缺失", "保留", "有效率"],
        ["ods_sensor_raw", "1,405,790", "4,190", "2,800", "1,398,800", "99.50%"],
        ["ods_weather_raw", "105,422", "302", "0", "105,120", "99.71%"],
        ["ods_pest_scout_raw", "65,890", "192", "516", "65,182", "98.93%"],
        ["ods_yield_plot_raw", "14,443", "43", "16", "14,384", "99.59%"],
        ["合计", "1,591,545", "4,727", "3,332", "1,583,486", "99.49%"],
    ]
    data_table(s, MARGIN, 3030000, CONTENT_W, rows, [4, 2.4, 2.2, 2.4, 2.4, 2], row_h=323850)

    rect(s, MARGIN, 5080000, CONTENT_W, 1180000, GRAIN)
    text(s, 914400, 5250000, 6000000, 260000, "清洗策略是分级的，不是一刀切", 13.0, INK, bold=True)
    text(s, 914400, 5600000, 10200000, 560000,
         "墒情、时间、地块等关键字段缺失 → 整行剔除；气温、湿度等可插补字段 → 按乡镇窗口均值回填，"
         "避免整行丢弃造成时序断点；越界值置空并打 is_outlier 标记，与 IsolationForest 的分布漂移检测互补。"
         "逐表明细写入 ads_data_quality.json，可现场逐条核对。",
         10.0, INK_SOFT, line=1.35)
    page_footer(s, 8)
    return s


def s09_pipeline(prs):
    s = new_slide(prs)
    section_header(s, 7, "技术实现", "Spark 四层数仓", "Spark 是主链路，不是可选扩展",
                   "全部清洗、关联、窗口计算与聚合由 Spark SQL / DataFrame 完成，业务库不参与明细计算。")
    layers = [
        (BRAND_DEEP, "ODS", "贴源层", "gzip CSV · dt 月分区", "1,591,545 条", "原样落地，完整保留脏数据"),
        (TEAL, "DWD", "清洗层", "Parquet + Snappy · dt 分区", "1,583,486 条", "去重 / 值域 / 缺失分级 / 时间口径"),
        (GOLD, "DWS", "汇总层", "地块 × 日 风险特征宽表", "58,400 行", "两级汇聚 + 14 日滚动窗口"),
        (BLUE, "ADS", "应用层", "JSON + CSV · API 直读", "6 张结果表", "评分 / 排名 / 归因 / 资源测算"),
    ]
    y = 1900000
    for accent, code, name, fmt, cnt, desc in layers:
        rect(s, MARGIN, y, CONTENT_W, 800000, WHITE)
        rect(s, MARGIN, y, 47625, 800000, accent)
        badge(s, MARGIN + 190500, y + 200000, 700000, 400000, accent, code)
        text(s, MARGIN + 1010000, y + 195000, 1500000, 280000, name, 13.0, INK, bold=True)
        text(s, MARGIN + 1010000, y + 510000, 2500000, 200000, fmt, 8.5, MUTED)
        text(s, 4300000, y + 250000, 1800000, 280000, cnt, 12.5, accent, bold=True)
        text(s, 6300000, y + 265000, 5200000, 280000, desc, 10.5, INK_SOFT)
        y += 900000

    rect(s, MARGIN, 5550000, CONTENT_W, 700000, CARD_DARK)
    text(s, 914400, 5690000, 5200000, 240000, "一键复现", 10.5, BRAND, bold=True)
    text(s, 914400, 5950000, 10200000, 240000,
         "docker compose -f docker-compose.bigdata.yml run --rm spark-local"
         "　·　另提供 Hive 四层外部表 DDL，可在 Metastore 环境用 SQL 访问同一份数据",
         9.5, ON_DARK)
    page_footer(s, 9)
    return s


def s10_feature(prs):
    s = new_slide(prs)
    section_header(s, 8, "技术实现", "特征工程", "两级汇聚 + 时序窗口，把单点观测变成可分析的特征",
                   "单点读数说明不了问题，病害压力的累积效应必须用窗口刻画。")
    cols = [
        (BRAND_DEEP, "气象日聚合", "粒度：乡镇 × 日",
         ["日均温 / 日最高温 / 日均湿", "日累计降水 / 日均风速", "相对湿度 ≥85% 的小时数"]),
        (TEAL, "传感器日聚合", "粒度：地块 × 日",
         ["日均墒情 / 墒情日内标准差", "土温 / pH / 氮钾均值", "有效采集条数 / 异常读数条数"]),
        (GOLD, "踏查日聚合", "粒度：地块 × 日",
         ["平均病株率 / 最高病株率", "受害面积 / 踏查次数", "来源：踏查 / 上报 / 无人机 / 识别"]),
    ]
    for i, (accent, title, gran, items) in enumerate(cols):
        x = 609600 + i * 3771900
        rect(s, x, 1900000, 3543300, 1900000, WHITE)
        rect(s, x, 1900000, 3543300, 47625, accent)
        text(s, x + 228600, 2060000, 3000000, 280000, title, 13.0, INK, bold=True)
        text(s, x + 228600, 2410000, 3100000, 200000, gran, 9.0, accent, bold=True)
        for j, item in enumerate(items):
            text(s, x + 228600, 2720000 + j * 330000, 3150000, 300000, f"·  {item}",
                 9.0, MUTED, line=1.2)

    rect(s, MARGIN, 4000000, CONTENT_W, 2000000, CARD_DARK)
    text(s, 914400, 4180000, 6500000, 280000, "关键一步：14 日滚动窗口的历史病害压力",
         13.5, WHITE, bold=True)
    text(s, 914400, 4600000, 5600000, 900000,
         ['Window.partitionBy("farm_id")',
          '      .orderBy(col("stat_date").cast("long"))',
          '      .rangeBetween(-14×86400, -86400)'],
         10.0, ON_DARK, line=1.4)
    text(s, 6900000, 4600000, 4500000, 1200000,
         "按时间范围而非行数取窗口，天然容忍缺失日期；区间不含当日，避免标签泄漏。"
         "该特征刻画病原基数的累积效应，在风险评分中权重第二高（22 分），"
         "是单点观测完全无法表达的信息。",
         10.0, ON_DARK_SOFT, line=1.4)
    page_footer(s, 10)
    return s


def s11_risk(prs):
    s = new_slide(prs)
    section_header(s, 9, "技术创新", "风险挖掘", "五因子评分，阈值按分布标定而非拍脑袋",
                   "风险评分要能解释，分级阈值要能复标定——这是结论可审计的前提。")
    rows = [
        ["风险因子", "计算口径", "满分", "农技依据"],
        ["空气湿度", "日均湿度超过 60% 的部分线性映射", "34", "高湿是真菌性病害首要诱因"],
        ["历史病害", "近 14 日病株率滚动均值线性映射", "22", "病原基数决定再侵染强度"],
        ["降雨量", "日累计降水线性映射，30mm 封顶", "18", "结露与孢子飞溅传播"],
        ["土壤墒情", "日均含水量超过 0.32 的部分线性映射", "16", "过湿致根系缺氧、抗性下降"],
        ["积温条件", "日均温超过 18℃ 的部分线性映射", "10", "温度决定病原发育速率"],
    ]
    data_table(s, MARGIN, 1900000, 7000000, rows, [2.2, 5, 1.2, 3.6], row_h=323850)

    rect(s, 7800000, 1900000, 3782400, 1943100, CARD_DARK)
    text(s, 8100000, 2060000, 3200000, 250000, "作物易感性系数", 11.5, WHITE, bold=True)
    for j, (c, v) in enumerate([("番茄", "1.20"), ("水稻", "1.15"), ("黄瓜", "1.10"),
                                ("小麦", "0.95"), ("玉米", "0.90")]):
        text(s, 8100000, 2420000 + j * 215000, 1200000, 205000, c, 9.5, ON_DARK)
        text(s, 9400000, 2420000 + j * 215000, 900000, 205000, v, 9.5, BRAND, bold=True)
    rect(s, 8100000, 3550000, 3200000, 9525, DIVIDER)
    text(s, 8100000, 3660000, 3300000, 200000, "risk = Σ 五项因子 × 易感性，上限 100 分",
         8.5, ON_DARK_SOFT)

    rect(s, MARGIN, 4080000, CONTENT_W, 1920000, WASH)
    text(s, 914400, 4250000, 6000000, 280000, "分级阈值怎么来的", 13.5, INK, bold=True)
    for i, linetext in enumerate([
        "对全量 58,400 条地块-日记录的风险分数做分位数统计，取高风险 52 分（约 P96）、中风险 36 分（约 P80）。",
        "再用主汛期 6—9 月的实际发生率校核：汛期高风险占比 10.5%、中风险 38.4%，与县域植保资源承载力匹配。",
        "最初按经验取 70/45，实测全量数据几乎没有高风险地块，预警形同虚设——这正是改用分位数标定的原因。",
        "阈值集中为 RISK_HIGH / RISK_MID 两个常量，Spark 与参考实现共享，年际气候变化后可低成本重标定。",
    ]):
        bullet(s, 933450, 4620000 + i * 340000, 9800000, linetext, size=10.0, h=320000)
    page_footer(s, 11)
    return s


def s12_models(prs):
    s = new_slide(prs)
    section_header(s, 10, "技术创新", "AI 模型矩阵", "五类模型分工明确，指标边界写在明处",
                   "规则可解释、模型补非线性，两者差异大的地块进入人工复核队列。")
    rows = [
        ["模型", "算法", "输入", "输出与指标"],
        ["病虫害检测", "YOLO11n（PlantDoc / IP102）", "叶片图像", "病害名称 / 置信度 / 检测框 / 复核标记"],
        ["风险评分", "规则评分 + RandomForest", "DWS 风险特征宽表", "0—100 分值 / 等级 / 特征贡献 / MAE·RMSE·R²"],
        ["产量预测", "RandomForestRegressor", "历史测产 + 风险累积 + 气象", "未来产量曲线 / 误差指标 / 影响因素"],
        ["异常检测", "IsolationForest", "墒情 / pH / 光照 / 养分", "分布漂移异常点，与规则 is_outlier 互补"],
        ["农技问答", "RAGFlow + 本地 TF-IDF", "知识库 + 实时农情", "带引用来源的回答，标注远程 / 本地模式"],
    ]
    data_table(s, MARGIN, 1900000, CONTENT_W, rows, [2.4, 3.4, 3.4, 5], row_h=323850)

    rect(s, MARGIN, 3930000, CONTENT_W, 2070000, GRAIN)
    text(s, 914400, 4100000, 7000000, 280000, "模型指标与适用边界（答辩须原样陈述）", 13.5, INK, bold=True)
    rows2 = [
        ["图像模型", "数据集", "类别数", "mAP50", "mAP50-95", "Precision", "Recall"],
        ["PlantDoc YOLO11n", "公开验证集", "29", "0.6542", "0.5212", "0.6068", "0.6151"],
        ["IP102 YOLO11n", "官方测试集", "102", "0.4133", "0.2597", "0.4761", "0.4572"],
    ]
    data_table(s, 914400, 4470000, 10363200, rows2, [3, 2.4, 1.6, 1.8, 2, 2, 1.8],
               row_h=285750, zebra=WHITE)
    text(s, 914400, 5400000, 10363200, 500000,
         "以上均为公开数据集评测结果，不代表山东本地田间识别准确率。轻量基线在合成样本上的 1.0 指标"
         "仅证明训练—保存—加载—调用链路通畅，不具泛化意义；上线前需补充本地样本并由农技专家复核标注。",
         9.0, BRAND_DEEP, line=1.35)
    page_footer(s, 12)
    return s


def s13_findings(prs):
    s = new_slide(prs)
    section_header(s, 11, "分析结论", "结果与农技校验", "结论经得起农技常识检验",
                   "以最新统计日 2026-08-31 为例，80 个地块的风险分布与作物、季节规律一致。")
    tiles = [("14", "个", "高风险地块（≥52 分）"), ("36", "个", "中风险地块（≥36 分）"),
             ("58,400", "行", "地块-日风险特征宽表"), ("99.49", "%", "明细数据清洗有效率")]
    for i, (v, u, lab) in enumerate(tiles):
        kpi_tile(s, 609600 + i * 2800350, 1900000, 2476500, 1280000, ACCENTS[i], v, u, lab)

    rows = [
        ["乡镇", "平均风险", "高风险", "受害面积(亩)", "无人机架次", "药剂(kg)"],
        ["老砦镇", "44.59", "3", "335.2", "2", "40.2"],
        ["清河镇", "42.45", "4", "1,486.4", "5", "178.4"],
        ["罗屯镇", "41.02", "2", "591.2", "2", "70.9"],
        ["谷亭街道", "40.28", "2", "562.0", "2", "67.4"],
        ["王鲁镇", "39.32", "2", "871.7", "3", "104.6"],
        ["张黄镇", "35.03", "1", "1,000.6", "4", "120.1"],
    ]
    data_table(s, MARGIN, 3380000, 6900000, rows, [2.4, 2.2, 2, 3, 2.6, 2.4], row_h=295275)

    rect(s, 7800000, 3380000, 3782400, 2070000, WASH)
    text(s, 8100000, 3550000, 3300000, 270000, "三条农技校验", 12.5, INK, bold=True)
    for j, linetext in enumerate([
        "高风险 14 个地块中，水稻 10 个、番茄 4 个——正是易感性系数最高的两类作物。",
        "8 月底为稻瘟病、纹枯病高发期；小麦、玉米此时非当季，无高风险地块。",
        "全年风险在 8—10 月达峰、3—5 月最低，符合高温高湿诱发病害的规律。",
    ]):
        text(s, 8100000, 3930000 + j * 490000, 3300000, 470000, "·  " + linetext,
             9.0, MUTED, line=1.3)
    page_footer(s, 13)
    return s


def s14_action(prs):
    s = new_slide(prs)
    section_header(s, 12, "应用闭环", "从分析到调度", "分析不止于结论，直接推算到资源投放",
                   "风险分数 → 主导因子 → 巡检排序 → 无人机架次、农技员人数、药剂用量。")
    chain = [
        (BRAND_DEEP, "风险评分", ["五因子加权 × 易感性", "输出 0—100 分值"]),
        (TEAL, "主导因子", ["取五项分值最大者", "回答为什么风险高"]),
        (GOLD, "巡检排序", ["Top 30 地块及优先级", "一键生成巡检任务"]),
        (BLUE, "资源测算", ["面积 ÷ 300 架次 · ÷ 500 人", "× 0.12 kg/亩"]),
    ]
    for i, (accent, title, desc) in enumerate(chain):
        x = 609600 + i * 2800350
        rect(s, x, 1900000, 2476500, 1330000, WHITE)
        rect(s, x, 1900000, 2476500, 47625, accent)
        text(s, x + 228600, 2050000, 2000000, 280000, title, 13.0, INK, bold=True)
        text(s, x + 228600, 2420000, 2100000, 700000, desc, 9.0, MUTED, line=1.3)
        if i < 3:
            text(s, x + 2530000, 2420000, 260000, 300000, "→", 15.0, RULE, bold=True)

    rows = [
        ["巡检优先级 Top 5", "乡镇", "作物", "风险分", "主导因子"],
        ["YT-F0011", "老砦镇", "番茄", "62.94", "历史病害"],
        ["YT-F0044", "清河镇", "水稻", "61.84", "历史病害"],
        ["YT-F0012", "罗屯镇", "水稻", "60.50", "历史病害"],
        ["YT-F0006", "罗屯镇", "水稻", "58.32", "历史病害"],
        ["YT-F0043", "谷亭街道", "水稻", "57.95", "历史病害"],
    ]
    data_table(s, MARGIN, 3430000, 6900000, rows, [4, 2.4, 2, 2, 3], row_h=295275)

    rect(s, 7800000, 3430000, 3782400, 1800000, CARD_DARK)
    text(s, 8100000, 3600000, 3300000, 270000, "全县当日调度测算", 12.5, WHITE, bold=True)
    for j, (k, v) in enumerate([("植保无人机", "18 架次"), ("农技员", "16 人"), ("防治药剂", "581.6 kg")]):
        text(s, 8100000, 4000000 + j * 330000, 1800000, 280000, k, 10.0, ON_DARK_SOFT)
        text(s, 10050000, 4000000 + j * 330000, 1400000, 280000, v, 11.0, BRAND, bold=True)
    text(s, 8100000, 5010000, 3300000, 320000, "按受害面积与作业效率折算，可直接下发乡镇执行",
         8.5, ON_DARK_SOFT, line=1.3)
    page_footer(s, 14)
    return s


def s15_demo(prs):
    s = new_slide(prs)
    section_header(s, 13, "演示效果", "系统界面", "分析结论如何落到业务动作",
                   "驾驶舱看态势，地图看空间，预警转任务，现场回写闭环。"
                   "　作品访问地址：http://47.105.74.222:3001/login")
    shots = PROJECT_ROOT / "presentation" / "screenshots"
    left, right = shots / "dashboard.png", shots / "riskmap.png"
    if left.exists():
        shot_image(s, MARGIN, 1900000, 5300000, 2700000, left)
    else:
        shot_placeholder(s, MARGIN, 1900000, 5300000, 2700000, "【替换为农情驾驶舱截图】",
                         "建议截取含 KPI、风险趋势、乡镇排名与最新预警的完整页面")
    if right.exists():
        shot_image(s, 6282000, 1900000, 5300400, 2700000, right)
    else:
        shot_placeholder(s, 6282000, 1900000, 5300400, 2700000, "【替换为县域风险地图截图】",
                         "建议截取已筛选高风险、并点开某地块画像的状态")
    feats = [
        (BRAND_DEEP, "农情驾驶舱", "核心指标、风险趋势、作物结构、乡镇排名与最新预警"),
        (TEAL, "县域风险地图", "地块 polygon 按等级着色，点击查看画像与主导因子"),
        (GOLD, "预警与巡检", "越阈生成预警，一键转巡检任务，现场处置回写"),
        (BLUE, "识别与问答", "叶片检测返回置信度与复核标记；问答标注引用来源"),
    ]
    for i, (accent, title, desc) in enumerate(feats):
        x = 609600 + i * 2800350
        rect(s, x, 4800000, 2476500, 1150000, WHITE)
        rect(s, x, 4800000, 47625, 1150000, accent)
        text(s, x + 228600, 4940000, 2000000, 280000, title, 12.0, INK, bold=True)
        text(s, x + 228600, 5290000, 2100000, 580000, desc, 8.5, MUTED, line=1.25)
    page_footer(s, 15)
    return s


def s16_engineering(prs):
    s = new_slide(prs)
    section_header(s, 14, "工程质量", "部署与可复现", "分析结果可复核，而不是一次性跑数",
                   "评分中工程实现质量占比最高（30%），这一页讲怎么保证「跑得起来、算得对、改不坏」。")
    items = [
        (BRAND_DEEP, "双实现口径互校", "pandas 参考实现与 Spark 主链路读同一份 ODS、用同一套公式，"
                                  "compare_ads_outputs.py 逐表逐字段比对，容差 0.02"),
        (TEAL, "规模断言", "造数脚本对明细总量做断言，达不到百万级即以非零退出码失败，"
                        "杜绝「说有百万数据但跑不出来」"),
        (GOLD, "固定种子", "SEED=20260506，两次生成的行数、文件数与体积完全一致，"
                        "ods_manifest.json 可逐项核对"),
        (BLUE, "运行报告", "_run_report.json 记录 Spark 版本、并行度、各层行数、"
                        "逐表数据质量与三阶段耗时"),
    ]
    for i, (accent, title, desc) in enumerate(items):
        x = 609600 if i % 2 == 0 else 6282000
        y = 1900000 if i < 2 else 3020000
        rect(s, x, y, 5300400, 980000, WHITE)
        rect(s, x, y, 47625, 980000, accent)
        text(s, x + 228600, y + 130000, 4200000, 280000, title, 12.5, INK, bold=True)
        text(s, x + 228600, y + 490000, 4900000, 460000, desc, 8.8, MUTED, line=1.25)

    rect(s, MARGIN, 4250000, CONTENT_W, 1750000, CARD_DARK)
    text(s, 914400, 4420000, 6000000, 280000, "四条命令，从零复现", 13.5, WHITE, bold=True)
    text(s, 914400, 4830000, 10363200, 950000,
         ["python scripts/generate_bigdata_layer.py                                # 生成 159 万条明细，约 35 秒",
          "docker compose -f docker-compose.bigdata.yml run --rm spark-local        # Spark ETL 四层",
          "python batch_jobs/pandas_jobs/ads_reference_job.py && python scripts/compare_ads_outputs.py   # 口径校验",
          "docker compose up --build                                                # 启动在线系统"],
         8.8, ON_DARK, line=1.45)
    page_footer(s, 16)
    return s


def s17_compare(prs):
    s = new_slide(prs)
    section_header(s, 15, "差异化", "竞品对比", "与同类农业信息化方案的差别在哪",
                   "对比对象为县域常见的三类现有方案，判据是「能不能拿出中间结果」。")
    rows = [
        ["能力项", "传统农技管理系统", "通用物联网监测平台", "单点病害识别 App", "本项目"],
        ["多源数据统一建模", "—", "✔", "—", "✔"],
        ["百万级明细离线分析", "—", "—", "—", "✔"],
        ["数据治理可度量", "—", "—", "—", "✔"],
        ["时序窗口特征", "—", "—", "—", "✔"],
        ["风险分级阈值可标定", "—", "—", "—", "✔"],
        ["风险成因归因到因子", "—", "—", "—", "✔"],
        ["识别结果进入业务闭环", "—", "—", "—", "✔"],
        ["推算到资源投放量", "—", "—", "—", "✔"],
        ["分析口径可自动校验", "—", "—", "—", "✔"],
    ]
    data_table(s, MARGIN, 1900000, 7600000, rows, [3.4, 2.4, 2.6, 2.4, 1.8],
               row_h=295275, mark_cols=(1, 2, 3, 4))

    rect(s, 8500000, 1900000, 3082400, 2900000, WASH)
    text(s, 8780000, 2070000, 2600000, 270000, "核心差异", 12.5, INK, bold=True)
    for j, linetext in enumerate([
        "同类方案多停留在「采集 + 看板」，能展示数据但拿不出加工过程。",
        "本项目每一层都有可打开核对的中间结果：清洗剔除量、特征宽表、应用层结果表。",
        "识别不是终点——结论继续往下推到派单与药剂用量，才构成真正的行业应用。",
    ]):
        text(s, 8780000, 2450000 + j * 780000, 2600000, 740000, "·  " + linetext,
             9.0, MUTED, line=1.3)

    rect(s, 8500000, 4950000, 3082400, 1050000, GRAIN)
    text(s, 8780000, 5110000, 2600000, 250000, "可推广性", 11.5, INK, bold=True)
    text(s, 8780000, 5420000, 2650000, 500000,
         "明细层表结构即真实数据接入契约，换数据源后 DWD 以下零改动。",
         9.0, MUTED, line=1.3)
    page_footer(s, 17)
    return s


def s18_value(prs):
    s = new_slide(prs)
    section_header(s, 16, "应用价值", "经济与社会效益", "把技术指标换算成县域能感知的收益",
                   "以鱼台县 80 个示范地块、约 1.5 万亩种植面积为测算口径。")
    tiles = [
        (BRAND_DEEP, "提前 2—5 天", "预警提前量", "风险预测替代症状上报，把处置窗口从「发现后」前移到「发生前」"),
        (TEAL, "约 30%", "资源重配比例", "从按面积平摊改为按风险靶向投放，高风险乡镇获得 2—3 倍资源密度"),
        (GOLD, "靶向施药", "减量增效方向", "只对达到阈值的地块施药，减少无效喷施与面源污染"),
        (BLUE, "全程留痕", "治理可追溯", "预警、派单、处置、回访进入同一套记录，管理动作可量化考核"),
    ]
    for i, (accent, big, label, desc) in enumerate(tiles):
        x = 609600 + i * 2800350
        rect(s, x, 1900000, 2476500, 1850000, WHITE)
        rect(s, x, 1900000, 2476500, 47625, accent)
        text(s, x + 228600, 2060000, 2150000, 380000, big, 15.0, INK, bold=True)
        text(s, x + 228600, 2470000, 2100000, 220000, label, 9.0, accent, bold=True)
        text(s, x + 228600, 2790000, 2100000, 900000, desc, 8.8, MUTED, line=1.3)

    rect(s, MARGIN, 3960000, 5300400, 2040000, WASH)
    text(s, 914400, 4130000, 4600000, 270000, "经济效益", 12.5, INK, bold=True)
    for j, t in enumerate([
        "减损：把防治窗口前移，降低病虫害造成的减产损失。",
        "降本：无人机架次与农技员出勤按风险排序，减少无效出工。",
        "省药：靶向施药替代普遍预防，直接压降药剂用量。",
    ]):
        text(s, 914400, 4510000 + j * 430000, 4800000, 410000, "·  " + t, 9.5, MUTED, line=1.3)

    rect(s, 6282000, 3960000, 5300400, 2040000, GRAIN)
    text(s, 6562000, 4130000, 4600000, 270000, "社会效益", 12.5, INK, bold=True)
    for j, t in enumerate([
        "把老农技员的经验沉淀为可传承、可审计的量化规则。",
        "减少无效喷施，助力农药减量增效与面源污染治理。",
        "为县域农业数字化治理提供一套可复制的落地样板。",
    ]):
        text(s, 6562000, 4510000 + j * 430000, 4800000, 410000, "·  " + t, 9.5, MUTED, line=1.3)
    page_footer(s, 18)
    return s


def s19_team(prs):
    s = new_slide(prs)
    section_header(s, 17, "团队介绍", "分工与协作", "云穗智擎",
                   "山东建筑大学 计算机与人工智能学院　|　队长：张衡　|　指导教师：刘新锋")
    members = [
        (BRAND_DEEP, "队长 / 数据与分析", "张衡",
         ["数据湖设计与造数脚本", "Spark ETL 四层链路", "风险评分与阈值标定"]),
        (TEAL, "算法与模型", "李斯睿",
         ["YOLO 病虫害检测训练", "风险与产量模型", "异常检测与 RAG 问答"]),
        (GOLD, "后端与数据库", "孙佳琦",
         ["FastAPI 接口与认证", "数据库设计与迁移", "Docker 编排与部署"]),
        (BLUE, "前端与可视化", "张菁怡",
         ["Next.js 页面与交互", "驾驶舱图表与地图", "视觉设计与演示素材"]),
        (CLAY, "测试与文档", "冯丽如",
         ["接口与链路测试", "工程文档撰写", "演示视频与答辩准备"]),
    ]
    for i, (accent, role, name, duties) in enumerate(members):
        x = 609600 + i * 2222500
        rect(s, x, 1900000, 1968500, 2650000, WHITE)
        rect(s, x, 1900000, 1968500, 47625, accent)
        badge(s, x + 180000, 2050000, 620000, 290000, accent, f"0{i + 1}", size=8.5)
        text(s, x + 180000, 2440000, 1680000, 240000, role, 9.5, accent, bold=True)
        text(s, x + 180000, 2720000, 1680000, 300000, name, 12.5, INK, bold=True)
        rect(s, x + 180000, 3110000, 1600000, 9525, RULE)
        for j, d in enumerate(duties):
            text(s, x + 180000, 3260000 + j * 400000, 1680000, 380000, "·  " + d,
                 8.5, MUTED, line=1.2)

    rect(s, MARGIN, 4750000, CONTENT_W, 1250000, GRAIN)
    text(s, 914400, 4920000, 5000000, 260000, "协作方式", 12.5, INK, bold=True)
    text(s, 914400, 5270000, 10200000, 560000,
         "五人按「数据与分析 / 算法与模型 / 后端与数据库 / 前端与可视化 / 测试与文档」并行推进；"
         "每周三固定例会，阶段节点开专题评审，记录完成项、风险项与下一步负责人；"
         "Git 分支开发，合并前由至少一名非作者成员做代码检查与演示复核。"
         "全体成员均为山东建筑大学 2024 级在校本科生，指导教师 1 人，符合参赛资格要求。",
         10.0, INK_SOFT, line=1.35)
    page_footer(s, 19)
    return s


def s20_closing(prs):
    s = new_slide(prs)
    rect(s, 0, 0, W, H, INK)
    rect(s, 0, 0, 152400, H, BRAND)
    heat_grid(s, 7750000, 3520000, 292100, 38100, 13, 9, seed=99991)

    text(s, 838200, 1100000, 5400000, 220000, "结语", 9.5, BRAND, bold=True)
    text(s, 800100, 1550000, 6700000, 1500000,
         "把县域植保从被动上报，推进到数据驱动的主动预警与靶向调度",
         26.0, WHITE, bold=True, line=1.35)
    rect(s, 838200, 3250000, 762000, 22225, GOLD)

    for i, (v, lab) in enumerate([("1,591,545", "条明细记录"), ("4 层", "Spark 数仓链路"),
                                  ("99.49%", "清洗有效率"), ("6 张", "应用层结果表")]):
        x = 838200 + i * 1650000
        text(s, x, 3500000, 1550000, 380000, v, 16.0, BRAND, bold=True)
        text(s, x, 3900000, 1550000, 220000, lab, 9.0, ON_DARK_SOFT)

    rect(s, 838200, 4380000, 6300000, 1300000, CARD_DARK)
    text(s, 1100000, 4560000, 5800000, 980000,
         "数据规模、大数据技术栈、AI 模型能力、行业闭环与工程可复现——"
         "从第一条原始记录到最后一次无人机派单，全链路一键复现。",
         12.0, ON_DARK, line=1.45)

    text(s, 838200, 5780000, 6000000, 480000,
         ["云穗智擎　|　山东建筑大学 计算机与人工智能学院　|　队长：张衡　指导教师：刘新锋",
          "作品访问地址：http://47.105.74.222:3001/login　　版本 v1.0.0"],
         9.0, ON_DARK_DIM, line=1.45)
    text(s, 6700000, 5950000, 533400, 190500, "20", 8.5, BRAND, bold=True, align=PP_ALIGN.RIGHT)
    return s


BUILDERS = [
    s01_cover, s02_agenda, s03_policy, s04_painpoint, s05_requirement,
    s06_architecture, s07_data, s08_quality, s09_pipeline, s10_feature,
    s11_risk, s12_models, s13_findings, s14_action, s15_demo,
    s16_engineering, s17_compare, s18_value, s19_team, s20_closing,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="生成参赛演示 PPT")
    parser.add_argument(
        "--out",
        default="submission_artifacts/云穗智擎_山东建筑大学_张衡_项目简介PPT.pptx",
    )
    args = parser.parse_args()

    prs = Presentation()
    prs.slide_width = Emu(W)
    prs.slide_height = Emu(H)
    for build in BUILDERS:
        build(prs)

    target = Path(args.out)
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    prs.save(target)
    print(f"OK: {len(prs.slides._sldIdLst)} 页 PPT 已生成 -> {target}")


if __name__ == "__main__":
    main()
