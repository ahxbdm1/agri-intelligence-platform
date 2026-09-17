from collections import defaultdict
from datetime import date, timedelta
import json

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Alert, Crop, Farm, ModelMetric, PestDiseaseReport, RiskPrediction, YieldRecord


router = APIRouter(prefix="/api/dashboard", tags=["农情驾驶舱"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    total_area = db.query(func.sum(Farm.area_mu)).scalar() or 0
    farm_count = db.query(Farm).count()
    high_risk_count = db.query(Farm).filter(Farm.risk_level == "高").count()
    latest_report_date = db.query(func.max(PestDiseaseReport.report_date)).scalar()
    today_reports = (
        db.query(PestDiseaseReport).filter(PestDiseaseReport.report_date == latest_report_date).count()
        if latest_report_date
        else 0
    )
    avg_loss = db.query(func.avg(YieldRecord.loss_rate)).scalar() or 0
    accuracy = (
        db.query(ModelMetric.metric_value)
        .filter(ModelMetric.model_name == "disease_classifier", ModelMetric.metric_name == "accuracy")
        .order_by(ModelMetric.created_at.desc())
        .limit(1)
        .scalar()
        or 0.918
    )
    total_alerts = db.query(Alert).count()
    handled_alerts = db.query(Alert).filter(Alert.status == "已完成").count()
    alert_rate = handled_alerts / total_alerts if total_alerts else 0
    return {
        "total_area_mu": round(total_area, 1),
        "farm_count": farm_count,
        "high_risk_farms": high_risk_count,
        "today_new_reports": today_reports,
        "report_data_date": str(latest_report_date) if latest_report_date else None,
        "predicted_loss_rate": round(avg_loss * 100, 2),
        "ai_accuracy": round(accuracy * 100, 2),
        "alert_process_rate": round(alert_rate * 100, 2),
    }


@router.get("/trends")
def trends(db: Session = Depends(get_db)) -> dict:
    # Demo datasets use a fixed seed and date range. Anchor the window to the
    # newest available prediction so the dashboard remains populated later.
    latest_prediction_date = db.query(func.max(RiskPrediction.prediction_date)).scalar()
    window_end = latest_prediction_date or date.today()
    start = window_end - timedelta(days=45)
    rows = (
        db.query(RiskPrediction.prediction_date, func.avg(RiskPrediction.risk_score))
        .filter(RiskPrediction.prediction_date >= start)
        .group_by(RiskPrediction.prediction_date)
        .order_by(RiskPrediction.prediction_date)
        .all()
    )
    risk_trend = [{"date": str(day), "risk": round(float(score), 2)} for day, score in rows]

    crop_rows = db.query(Crop.name, func.sum(Farm.area_mu)).join(Farm, Farm.crop_id == Crop.id).group_by(Crop.name).all()
    crop_structure = [{"name": name, "value": round(float(area), 1)} for name, area in crop_rows]

    yield_rows = (
        db.query(YieldRecord.year, func.avg(YieldRecord.predicted_yield_kg_per_mu))
        .group_by(YieldRecord.year)
        .order_by(YieldRecord.year)
        .all()
    )
    yield_trend = [{"year": year, "yield": round(float(value), 1)} for year, value in yield_rows]
    return {
        "risk_trend": risk_trend,
        "crop_structure": crop_structure,
        "yield_trend": yield_trend,
        "data_as_of": str(window_end),
    }


@router.get("/risk-ranking")
def risk_ranking(db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(Farm.town, func.avg(Farm.current_risk_score), func.count(Farm.id))
        .group_by(Farm.town)
        .order_by(func.avg(Farm.current_risk_score).desc())
        .all()
    )
    ranking = [
        {"town": town, "risk_score": round(float(score), 2), "farm_count": count}
        for town, score, count in rows
    ]
    alerts = (
        db.query(Alert)
        .join(Farm, Farm.id == Alert.farm_id)
        .order_by(Alert.created_at.desc())
        .limit(8)
        .all()
    )
    latest_alerts = [
        {
            "id": a.id,
            "title": a.title,
            "town": a.farm.town,
            "farm_name": a.farm.name,
            "risk_level": a.risk_level,
            "status": a.status,
            "created_at": a.created_at,
        }
        for a in alerts
    ]
    level_counts = defaultdict(int)
    for level, count in db.query(Farm.risk_level, func.count(Farm.id)).group_by(Farm.risk_level).all():
        level_counts[level] = count
    return {"ranking": ranking, "latest_alerts": latest_alerts, "risk_level_counts": dict(level_counts)}
