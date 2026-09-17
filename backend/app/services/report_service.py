from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, Farm, PestDiseaseReport, RiskPrediction, YieldRecord


def generate_daily_report(db: Session, town: str | None = None) -> dict:
    query_farms = db.query(Farm)
    if town:
        query_farms = query_farms.filter(Farm.town == town)
    farms = query_farms.all()
    farm_ids = [f.id for f in farms]
    total_area = sum(f.area_mu for f in farms)
    high_farms = [f for f in farms if f.risk_level == "高"]
    latest_alerts = (
        db.query(Alert)
        .filter(Alert.farm_id.in_(farm_ids) if farm_ids else True)
        .order_by(Alert.created_at.desc())
        .limit(8)
        .all()
    )
    avg_risk = db.query(func.avg(RiskPrediction.risk_score)).filter(RiskPrediction.farm_id.in_(farm_ids) if farm_ids else True).scalar() or 0
    avg_yield = db.query(func.avg(YieldRecord.predicted_yield_kg_per_mu)).filter(YieldRecord.farm_id.in_(farm_ids) if farm_ids else True).scalar() or 0
    report_count = db.query(PestDiseaseReport).filter(PestDiseaseReport.farm_id.in_(farm_ids) if farm_ids else True).count()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_id = f"daily-{town or 'county'}-{timestamp}".replace("/", "-")
    title = f"{town or '云澜县'}农情风险日报"
    markdown = _build_markdown(title, total_area, farms, high_farms, avg_risk, avg_yield, report_count, latest_alerts)
    html = _markdown_to_html(title, markdown)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = settings.reports_dir / f"{report_id}.md"
    html_path = settings.reports_dir / f"{report_id}.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return {
        "report_id": report_id,
        "title": title,
        "markdown": markdown,
        "html": html,
        "paths": {"markdown": str(md_path), "html": str(html_path)},
    }


def get_report(report_id: str) -> dict:
    if not re.fullmatch(r"daily-[A-Za-z0-9_-]+", report_id):
        raise FileNotFoundError(report_id)
    md_path = settings.reports_dir / f"{report_id}.md"
    html_path = settings.reports_dir / f"{report_id}.html"
    if not md_path.exists():
        raise FileNotFoundError(report_id)
    return {
        "report_id": report_id,
        "markdown": md_path.read_text(encoding="utf-8"),
        "html": html_path.read_text(encoding="utf-8") if html_path.exists() else "",
        "paths": {"markdown": str(md_path), "html": str(html_path)},
    }


def _build_markdown(title: str, total_area: float, farms: list[Farm], high_farms: list[Farm], avg_risk: float, avg_yield: float, report_count: int, alerts: list[Alert]) -> str:
    high_names = "、".join(f.name for f in high_farms[:8]) or "暂无高风险地块"
    alert_lines = "\n".join(
        f"- [{a.risk_level}] {a.title}：{a.trigger_reason}，负责人：{a.owner}，状态：{a.status}" for a in alerts
    ) or "- 今日暂无新增预警"
    suggestion = (
        "1. 高湿连阴天气下，优先巡检水稻、番茄、黄瓜等易感作物地块。\n"
        "2. 对高风险连片区域执行分级处置：先复核、再防治、后回访。\n"
        "3. 农资储备建议向高风险乡镇倾斜，保持药剂、无人机植保和农技员排班联动。\n"
        "4. 将人工复核结果回填系统，用于风险模型和病害识别模型再训练。"
    )
    return f"""# {title}

生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 一、核心指标

- 监测地块数量：{len(farms)} 个
- 监测种植面积：{total_area:.1f} 亩
- 高风险地块数量：{len(high_farms)} 个
- 综合平均风险评分：{avg_risk:.1f}
- 预测平均亩产：{avg_yield:.1f} kg/亩
- 累计病虫害/巡检相关记录：{report_count} 条

## 二、高风险地块

{high_names}

## 三、最新预警

{alert_lines}

## 四、模型研判

风险评分模型综合了温度、空气湿度、降雨、土壤墒情、历史病害、作物类型和地块面积等因子。当前平均风险处于{"高" if avg_risk >= 78 else "中" if avg_risk >= 55 else "低"}等级，建议结合天气变化和病虫害识别结果动态调整巡检优先级。

## 五、处置建议

{suggestion}
"""


def _markdown_to_html(title: str, markdown: str) -> str:
    body = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = []
    for line in body.splitlines():
        if line.startswith("# "):
            lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            lines.append(f"<p>{line}</p>")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 42px; color: #14332b; line-height: 1.72; }}
    h1 {{ color: #0b6b53; border-bottom: 3px solid #18b58f; padding-bottom: 10px; }}
    h2 {{ color: #0c7f8a; margin-top: 28px; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>{''.join(lines)}</body>
</html>"""
