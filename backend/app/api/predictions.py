import json

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import Farm, ModelMetric, PestDiseaseReport, SensorRecord, WeatherRecord
from ml.risk_model import RiskScoringModel
from ml.yield_forecast import YieldForecastModel


router = APIRouter(prefix="/api", tags=["模型预测"], dependencies=[Depends(get_current_user)])


class PredictionRequest(BaseModel):
    farm_id: int | None = None
    crop: str | None = None
    town: str | None = None
    days: int = 7
    temperature: float | None = None
    humidity: float | None = None
    rainfall: float | None = None
    soil_moisture: float | None = None


@router.post("/predictions/risk")
def predict_risk(payload: PredictionRequest, db: Session = Depends(get_db)) -> dict:
    features = _features_from_payload(db, payload)
    model = RiskScoringModel(settings.model_dir / "risk_model.joblib")
    result = model.predict(features)
    return {
        "farm_id": payload.farm_id,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "top_factors": result.top_factors,
        "model_version": result.model_version,
        "features": features,
    }


@router.post("/predictions/yield")
def predict_yield(payload: PredictionRequest, db: Session = Depends(get_db)) -> dict:
    features = _features_from_payload(db, payload)
    risk_model = RiskScoringModel(settings.model_dir / "risk_model.joblib")
    risk = risk_model.predict(features)
    model = YieldForecastModel(settings.model_dir / "yield_model.joblib")
    result = model.forecast(features | {"risk_score": risk.risk_score}, days=max(1, min(payload.days, 30)))
    return {
        "farm_id": payload.farm_id,
        "points": result.points,
        "metrics": result.metrics,
        "top_factors": result.top_factors,
        "model_version": result.model_version,
        "suggestions": [
            "未来三天优先安排高湿地块巡检，关注叶面结露和中心病株。",
            "对风险评分超过 78 的地块提前准备药剂与无人机植保排班。",
            "降雨后及时排水，避免土壤墒情长期高位造成根系胁迫。",
        ],
    }


@router.get("/model/metrics")
def model_metrics(db: Session = Depends(get_db)) -> dict:
    rows = db.query(ModelMetric).order_by(ModelMetric.model_name, ModelMetric.metric_name).all()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.model_name, []).append(
            {
                "task": row.task,
                "metric_name": row.metric_name,
                "metric_value": round(row.metric_value, 4),
                "dataset_version": row.dataset_version,
                "created_at": row.created_at,
            }
        )
    return {"items": grouped}


def _features_from_payload(db: Session, payload: PredictionRequest) -> dict:
    farm = db.query(Farm).filter(Farm.id == payload.farm_id).first() if payload.farm_id else None
    if payload.farm_id and farm is None:
        raise HTTPException(status_code=404, detail="地块不存在")
    town = payload.town or (farm.town if farm else "东湖镇")
    crop = payload.crop or (farm.crop.name if farm and farm.crop else "水稻")
    weather = db.query(WeatherRecord).filter(WeatherRecord.town == town).order_by(WeatherRecord.record_date.desc()).first()
    sensor = db.query(SensorRecord).filter(SensorRecord.farm_id == farm.id).order_by(SensorRecord.recorded_at.desc()).first() if farm else None
    history = db.query(PestDiseaseReport).filter(PestDiseaseReport.farm_id == farm.id).count() if farm else 3
    return {
        "temperature": payload.temperature if payload.temperature is not None else (weather.temperature if weather else 28),
        "humidity": payload.humidity if payload.humidity is not None else (weather.humidity if weather else 76),
        "rainfall": payload.rainfall if payload.rainfall is not None else (weather.rainfall if weather else 10),
        "soil_moisture": payload.soil_moisture if payload.soil_moisture is not None else (sensor.soil_moisture if sensor else 48),
        "history_disease_count": history,
        "area_mu": farm.area_mu if farm else 120,
        "crop_type": crop,
        "town": town,
        "year": 2026,
    }
