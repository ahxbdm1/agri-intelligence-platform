from datetime import timedelta
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models import Farm, RiskPrediction, SensorRecord, WeatherRecord


router = APIRouter(prefix="/api/farms", tags=["地块地图"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_farms(
    crop: str | None = Query(default=None),
    town: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Farm).options(joinedload(Farm.crop))
    if town:
        query = query.filter(Farm.town == town)
    if risk_level:
        query = query.filter(Farm.risk_level == risk_level)
    if crop:
        query = query.join(Farm.crop).filter_by(name=crop)
    farms = query.order_by(Farm.current_risk_score.desc()).all()
    return {
        "items": [_serialize_farm(db, farm) for farm in farms],
        "filters": {
            "towns": sorted({f.town for f in db.query(Farm).all()}),
            "risk_levels": ["高", "中", "低"],
        },
    }


@router.get("/{farm_id}")
def get_farm(farm_id: int, db: Session = Depends(get_db)) -> dict:
    farm = db.query(Farm).options(joinedload(Farm.crop)).filter(Farm.id == farm_id).first()
    if farm is None:
        raise HTTPException(status_code=404, detail="地块不存在")
    return _serialize_farm(db, farm, detail=True)


@router.get("/{farm_id}/risk")
def get_farm_risk(farm_id: int, db: Session = Depends(get_db)) -> dict:
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if farm is None:
        raise HTTPException(status_code=404, detail="地块不存在")
    risks = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.farm_id == farm_id)
        .order_by(RiskPrediction.prediction_date.desc())
        .limit(14)
        .all()
    )
    return {
        "farm_id": farm.id,
        "farm_name": farm.name,
        "risk_level": farm.risk_level,
        "current_risk_score": farm.current_risk_score,
        "trend": [
            {
                "date": str(r.prediction_date),
                "risk_score": r.risk_score,
                "risk_level": r.risk_level,
                "top_factors": json.loads(r.top_factors or "[]"),
            }
            for r in reversed(risks)
        ],
    }


def _serialize_farm(db: Session, farm: Farm, detail: bool = False) -> dict:
    latest_weather = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.town == farm.town)
        .order_by(WeatherRecord.record_date.desc())
        .first()
    )
    latest_sensor = (
        db.query(SensorRecord)
        .filter(SensorRecord.farm_id == farm.id)
        .order_by(SensorRecord.recorded_at.desc())
        .first()
    )
    latest_risk = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.farm_id == farm.id)
        .order_by(RiskPrediction.prediction_date.desc())
        .first()
    )
    payload = {
        "id": farm.id,
        "name": farm.name,
        "town": farm.town,
        "crop": farm.crop.name if farm.crop else "",
        "area_mu": farm.area_mu,
        "lat": farm.lat,
        "lng": farm.lng,
        "polygon": json.loads(farm.polygon_json),
        "soil_type": farm.soil_type,
        "irrigation_level": farm.irrigation_level,
        "owner": farm.owner,
        "risk_level": farm.risk_level,
        "current_risk_score": farm.current_risk_score,
        "top_factors": json.loads(latest_risk.top_factors or "[]") if latest_risk else [],
        "recent_weather": {
            "temperature": latest_weather.temperature if latest_weather else None,
            "humidity": latest_weather.humidity if latest_weather else None,
            "rainfall": latest_weather.rainfall if latest_weather else None,
            "weather_type": latest_weather.weather_type if latest_weather else None,
        },
        "suggested_inspection_time": str((latest_weather.record_date if latest_weather else None) or ""),
    }
    if detail and latest_sensor:
        payload["latest_sensor"] = {
            "soil_moisture": latest_sensor.soil_moisture,
            "soil_temperature": latest_sensor.soil_temperature,
            "ph": latest_sensor.ph,
            "nitrogen": latest_sensor.nitrogen,
            "phosphorus": latest_sensor.phosphorus,
            "potassium": latest_sensor.potassium,
        }
    return payload
