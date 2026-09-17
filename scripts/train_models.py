from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Farm, ModelMetric, RiskPrediction, SensorRecord, WeatherRecord, YieldRecord  # noqa: E402
from ml.anomaly_detector import SensorAnomalyDetector  # noqa: E402
from ml.risk_model import RiskScoringModel  # noqa: E402
from ml.yield_forecast import YieldForecastModel  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        risk_frame = build_risk_frame(db)
        yield_frame = build_yield_frame(db)
        sensor_frame = pd.DataFrame([record_to_dict(r) for r in db.query(SensorRecord).limit(6000).all()])

        risk_model = RiskScoringModel()
        risk_metrics = risk_model.train(risk_frame)
        risk_model.save(settings.model_dir / "risk_model.joblib")

        yield_model = YieldForecastModel()
        yield_metrics = yield_model.train(yield_frame)
        yield_model.save(settings.model_dir / "yield_model.joblib")

        detector = SensorAnomalyDetector()
        anomaly_metrics = detector.train(sensor_frame)
        detector.save(settings.model_dir / "anomaly_detector.joblib")

        persist_metrics(db, "risk_model", "risk_regression", risk_metrics)
        persist_metrics(db, "yield_forecast", "yield_regression", yield_metrics)
        persist_metrics(db, "anomaly_detector", "sensor_anomaly", anomaly_metrics)
        db.commit()
        print({"risk_model": risk_metrics, "yield_model": yield_metrics, "anomaly_detector": anomaly_metrics})
    finally:
        db.close()


def build_risk_frame(db) -> pd.DataFrame:
    rows = []
    weather_cache = {(w.town, w.record_date): w for w in db.query(WeatherRecord).all()}
    for risk in db.query(RiskPrediction).limit(5000).all():
        farm = db.query(Farm).filter(Farm.id == risk.farm_id).first()
        weather = weather_cache.get((farm.town, risk.prediction_date))
        rows.append(
            {
                "temperature": weather.temperature if weather else 27,
                "humidity": weather.humidity if weather else 74,
                "rainfall": weather.rainfall if weather else 8,
                "soil_moisture": 45 + (weather.rainfall if weather else 8) * 1.2,
                "history_disease_count": int(farm.current_risk_score // 14),
                "area_mu": farm.area_mu,
                "crop_type": farm.crop.name,
                "town": farm.town,
                "risk_score": risk.risk_score,
            }
        )
    return pd.DataFrame(rows)


def build_yield_frame(db) -> pd.DataFrame:
    rows = []
    latest_weather = {}
    for w in db.query(WeatherRecord).all():
        latest_weather[w.town] = w
    for item in db.query(YieldRecord).all():
        farm = db.query(Farm).filter(Farm.id == item.farm_id).first()
        weather = latest_weather.get(farm.town)
        rows.append(
            {
                "year": item.year,
                "risk_score": farm.current_risk_score,
                "rainfall": weather.rainfall if weather else 8,
                "temperature": weather.temperature if weather else 27,
                "humidity": weather.humidity if weather else 74,
                "area_mu": farm.area_mu,
                "crop_type": farm.crop.name,
                "town": farm.town,
                "yield_kg_per_mu": item.yield_kg_per_mu,
            }
        )
    return pd.DataFrame(rows)


def record_to_dict(r: SensorRecord) -> dict:
    return {
        "soil_moisture": r.soil_moisture,
        "soil_temperature": r.soil_temperature,
        "ph": r.ph,
        "light_intensity": r.light_intensity,
        "nitrogen": r.nitrogen,
        "phosphorus": r.phosphorus,
        "potassium": r.potassium,
    }


def persist_metrics(db, model_name: str, task: str, metrics: dict) -> None:
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            db.add(ModelMetric(model_name=model_name, task=task, metric_name=key, metric_value=float(value)))


if __name__ == "__main__":
    main()
