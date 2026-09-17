from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
import math

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Farm, InspectionTask, WeatherRecord


router = APIRouter(prefix="/api/workflows", tags=["农情调度工作流"], dependencies=[Depends(get_current_user)])


class DispatchRequest(BaseModel):
    max_tasks: int = Field(default=12, ge=1, le=50)
    dry_run: bool = False


@router.post("/daily-dispatch")
def daily_dispatch(payload: DispatchRequest, db: Session = Depends(get_db)) -> dict:
    """Run the county's risk-to-inspection-to-resource dispatch workflow."""
    farms = (
        db.query(Farm)
        .filter((Farm.risk_level == "高") | (Farm.current_risk_score >= 62))
        .order_by(Farm.current_risk_score.desc())
        .all()
    )
    latest_weather: dict[str, WeatherRecord] = {}
    for record in db.query(WeatherRecord).order_by(WeatherRecord.record_date.desc()).all():
        latest_weather.setdefault(record.town, record)

    active_statuses = ("待处理", "处理中")
    queue = []
    for farm in farms:
        weather = latest_weather.get(farm.town)
        weather_risk = (weather.humidity >= 82 if weather else False) or (weather.rainfall >= 12 if weather else False)
        priority = "高" if farm.current_risk_score >= 78 or weather_risk else "中"
        queue.append({
            "farm_id": farm.id,
            "farm_name": farm.name,
            "town": farm.town,
            "crop": farm.crop.name if farm.crop else "未知作物",
            "risk_score": round(farm.current_risk_score, 2),
            "risk_level": farm.risk_level,
            "priority": priority,
            "weather_hint": _weather_hint(weather),
        })
    queue.sort(key=lambda item: (0 if item["priority"] == "高" else 1, -item["risk_score"]))
    queue = queue[: payload.max_tasks]

    generated = []
    existing_count = 0
    due_date = date.today() + timedelta(days=1)
    for item in queue:
        existing = (
            db.query(InspectionTask)
            .filter(
                InspectionTask.farm_id == item["farm_id"],
                InspectionTask.status.in_(active_statuses),
                InspectionTask.title.like("智能调度%"),
            )
            .first()
        )
        if existing:
            existing_count += 1
            continue
        task = InspectionTask(
            farm_id=item["farm_id"],
            title=f"智能调度：{item['farm_name']}风险复核",
            priority=item["priority"],
            assignee="县域农技调度组",
            due_date=due_date,
            status="待处理",
            description=(
                f"风险评分 {item['risk_score']}，主要关注{item['crop']}病虫害。"
                f"{item['weather_hint']}完成叶片图像、田间湿度和病斑扩散情况复核。"
            ),
        )
        if not payload.dry_run:
            db.add(task)
        generated.append({**item, "due_date": str(due_date)})

    if not payload.dry_run:
        db.commit()

    crop_counts = Counter(item["crop"] for item in queue if item["priority"] == "高")
    material_plan = [
        {
            "material": f"{crop}病害防治药剂",
            "quantity": max(1, math.ceil(count * 0.8)),
            "unit": "箱",
            "reason": f"{count} 个高优先级{crop}地块进入调度队列",
        }
        for crop, count in crop_counts.most_common()
    ]
    if any(item["weather_hint"].find("高湿") >= 0 for item in queue):
        material_plan.append({"material": "排水与通风巡检工单", "quantity": 1, "unit": "批", "reason": "近期存在高湿或降雨风险"})

    return {
        "workflow": "county-daily-agri-dispatch",
        "executed_at": datetime.utcnow(),
        "dry_run": payload.dry_run,
        "high_risk_farm_count": len(farms),
        "queue_count": len(queue),
        "generated_task_count": len(generated),
        "existing_task_count": existing_count,
        "priority_queue": queue,
        "generated_tasks": generated,
        "material_plan": material_plan,
        "next_actions": ["优先完成高优先级地块现场复核", "补充叶片图像和病斑面积", "在巡检任务中回填处置效果并生成日报"],
    }


def _weather_hint(record: WeatherRecord | None) -> str:
    if record is None:
        return "暂无最新天气记录。"
    if record.humidity >= 82:
        return f"{record.town}近期高湿（湿度 {record.humidity:.0f}%），注意叶面结露。"
    if record.rainfall >= 12:
        return f"{record.town}近期降雨 {record.rainfall:.1f}mm，注意排水。"
    return f"{record.town}近期天气{record.weather_type}，保持常规巡检。"
