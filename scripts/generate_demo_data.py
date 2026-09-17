from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import json
import os
import random
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    Alert,
    Crop,
    Farm,
    InspectionTask,
    KnowledgeDoc,
    ModelMetric,
    PestDiseaseReport,
    RiskPrediction,
    SensorRecord,
    User,
    WeatherRecord,
    YieldRecord,
)
from ml.risk_model import risk_level  # noqa: E402


SEED = 20260506
BASE_DATE = date.fromisoformat(os.getenv("AGRI_DEMO_BASE_DATE", "2026-05-06"))
RNG = random.Random(SEED)
np.random.seed(SEED)


# 示范县域：山东省济宁市鱼台县（沿黄稻区，兼有小麦、玉米与设施蔬菜）
# 乡镇名称与经纬度取自真实行政区划，与大数据明细层
# scripts/generate_bigdata_layer.py 中的 TOWNS 保持一致。
TOWNS = [
    {"name": "谷亭街道", "lat": 34.990, "lng": 116.650},
    {"name": "清河镇", "lat": 35.060, "lng": 116.610},
    {"name": "张黄镇", "lat": 35.050, "lng": 116.720},
    {"name": "王鲁镇", "lat": 34.940, "lng": 116.630},
    {"name": "老砦镇", "lat": 34.900, "lng": 116.750},
    {"name": "罗屯镇", "lat": 35.020, "lng": 116.790},
]

CROPS = [
    {"name": "水稻", "variety": "甬优1540", "growth_days": 135, "optimal_temp_min": 22, "optimal_temp_max": 31},
    {"name": "小麦", "variety": "扬麦25", "growth_days": 220, "optimal_temp_min": 12, "optimal_temp_max": 24},
    {"name": "玉米", "variety": "登海605", "growth_days": 118, "optimal_temp_min": 20, "optimal_temp_max": 32},
    {"name": "番茄", "variety": "粉冠3号", "growth_days": 100, "optimal_temp_min": 18, "optimal_temp_max": 28},
    {"name": "黄瓜", "variety": "津优35", "growth_days": 85, "optimal_temp_min": 20, "optimal_temp_max": 30},
]

DISEASES = {
    "水稻": ["稻瘟病", "纹枯病", "稻飞虱"],
    "小麦": ["赤霉病", "条锈病", "蚜虫"],
    "玉米": ["大斑病", "草地贪夜蛾", "茎腐病"],
    "番茄": ["早疫病", "晚疫病", "白粉虱"],
    "黄瓜": ["霜霉病", "白粉病", "蓟马"],
}


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_users(db)
        crops = create_crops(db)
        farms = create_farms(db, crops)
        weather_by_town = create_weather(db)
        create_sensors(db, farms, weather_by_town)
        create_risk_predictions(db, farms, weather_by_town)
        create_pest_reports(db, farms)
        create_yields(db, farms, weather_by_town)
        create_alerts_and_tasks(db, farms)
        create_model_metrics(db)
        index_knowledge_docs(db)
        db.commit()
        export_demo_csv(db)
        print(
            "Demo data generated: "
            f"farms={db.query(Farm).count()}, "
            f"weather={db.query(WeatherRecord).count()}, "
            f"sensors={db.query(SensorRecord).count()}, "
            f"pest_reports={db.query(PestDiseaseReport).count()}, "
            f"yield_records={db.query(YieldRecord).count()}, "
            f"alerts={db.query(Alert).count()}, "
            f"tasks={db.query(InspectionTask).count()}"
        )
    finally:
        db.close()


def create_users(db) -> None:
    users = [
        ("admin", "admin123", "县域管理员", "县农业农村局管理员", "云澜县农业农村局"),
        ("expert", "expert123", "农技专家", "植保农技专家", "云澜县农技推广中心"),
        ("coop", "coop123", "合作社用户", "青禾合作社负责人", "青禾现代农业合作社"),
    ]
    for username, password, role, display_name, org in users:
        db.add(User(username=username, password_hash=hash_password(password), role=role, display_name=display_name, organization=org))


def create_crops(db) -> dict[str, Crop]:
    result = {}
    for item in CROPS:
        crop = Crop(**item)
        db.add(crop)
        result[item["name"]] = crop
    db.flush()
    return result


def create_farms(db, crops: dict[str, Crop]) -> list[Farm]:
    farms = []
    for idx in range(80):
        town = TOWNS[idx % len(TOWNS)]
        crop_name = CROPS[(idx * 7 + RNG.randint(0, 4)) % len(CROPS)]["name"]
        lat = town["lat"] + RNG.uniform(-0.026, 0.026)
        lng = town["lng"] + RNG.uniform(-0.032, 0.032)
        area = round(RNG.uniform(38, 260), 1)
        polygon = rectangle_polygon(lat, lng, RNG.uniform(0.006, 0.014), RNG.uniform(0.006, 0.016))
        farm = Farm(
            name=f"{town['name']}{crop_name}示范地块{idx + 1:02d}",
            town=town["name"],
            crop_id=crops[crop_name].id,
            area_mu=area,
            lat=lat,
            lng=lng,
            polygon_json=json.dumps(polygon, ensure_ascii=False),
            soil_type=RNG.choice(["壤土", "黏壤土", "砂壤土", "水稻土", "潮土"]),
            irrigation_level=RNG.choice(["高", "中", "中", "低"]),
            owner=RNG.choice(["青禾合作社", "金穗家庭农场", "云溪农服中心", "稻香种植大户联盟", "北岭农机合作社"]),
        )
        db.add(farm)
        farms.append(farm)
    db.flush()
    return farms


def create_weather(db) -> dict[str, list[WeatherRecord]]:
    weather_by_town: dict[str, list[WeatherRecord]] = {}
    for town in TOWNS:
        rows = []
        town_bias = RNG.uniform(-1.4, 1.4)
        for day_offset in range(180):
            day = BASE_DATE - timedelta(days=179 - day_offset)
            # Convert NumPy scalars before handing values to SQLAlchemy. Some
            # PostgreSQL drivers otherwise serialize np.float64 as an identifier.
            seasonal = float(np.sin(day_offset / 180 * np.pi) * 7)
            rainfall = max(0, RNG.gauss(5.5, 6.5) + (8 if day_offset % 19 in {0, 1, 2} else 0))
            humidity = min(98, max(48, RNG.gauss(70 + rainfall * 0.8, 8)))
            temp = 17 + seasonal + town_bias + RNG.gauss(0, 2.4)
            weather = WeatherRecord(
                farm_id=None,
                town=town["name"],
                record_date=day,
                temperature=round(temp, 1),
                humidity=round(humidity, 1),
                rainfall=round(rainfall, 1),
                wind_speed=round(max(0.4, RNG.gauss(2.6, 1.0)), 1),
                sunshine_hours=round(max(0.2, 9.5 - rainfall * 0.35 + RNG.gauss(0, 1.2)), 1),
                weather_type="雨" if rainfall > 12 else "阴" if humidity > 82 else "晴" if rainfall < 1 else "多云",
            )
            db.add(weather)
            rows.append(weather)
        weather_by_town[town["name"]] = rows
    db.flush()
    return weather_by_town


def create_sensors(db, farms: list[Farm], weather_by_town: dict[str, list[WeatherRecord]]) -> None:
    for farm in farms:
        records_per_farm = 65
        crop_factor = {"水稻": 10, "黄瓜": 6, "番茄": 4, "玉米": 1, "小麦": -2}.get(farm.crop.name, 0)
        for i in range(records_per_farm):
            day = BASE_DATE - timedelta(days=records_per_farm - i)
            weather = weather_by_town[farm.town][-(records_per_farm - i)]
            moisture = min(92, max(22, 38 + weather.rainfall * 1.5 + crop_factor + RNG.gauss(0, 7)))
            anomaly = moisture > 80 or RNG.random() < 0.018
            db.add(
                SensorRecord(
                    farm_id=farm.id,
                    recorded_at=datetime.combine(day, datetime.min.time()) + timedelta(hours=RNG.choice([6, 12, 18])),
                    soil_moisture=round(moisture, 1),
                    soil_temperature=round(weather.temperature + RNG.gauss(-1.2, 1.8), 1),
                    ph=round(min(8.4, max(5.2, RNG.gauss(6.7, 0.45))), 2),
                    light_intensity=round(max(800, weather.sunshine_hours * 1200 + RNG.gauss(0, 600)), 1),
                    nitrogen=round(max(20, RNG.gauss(80, 18)), 1),
                    phosphorus=round(max(10, RNG.gauss(42, 10)), 1),
                    potassium=round(max(20, RNG.gauss(95, 22)), 1),
                    anomaly_flag=anomaly,
                )
            )


def create_risk_predictions(db, farms: list[Farm], weather_by_town: dict[str, list[WeatherRecord]]) -> None:
    for farm in farms:
        history = RNG.randint(0, 9)
        latest_score = 0.0
        latest_level = "低"
        for offset in range(45):
            day = BASE_DATE - timedelta(days=44 - offset)
            weather = weather_by_town[farm.town][-(45 - offset)]
            crop_risk = {"水稻": 14, "番茄": 13, "黄瓜": 12, "小麦": 9, "玉米": 8}.get(farm.crop.name, 7)
            score = 16 + weather.humidity * 0.25 + weather.rainfall * 0.9 + history * 2.8 + crop_risk + RNG.gauss(0, 5)
            score = float(np.clip(score, 12, 98))
            level = risk_level(score)
            factors = [
                {"factor": "空气湿度偏高", "contribution": round(weather.humidity * 0.25, 2)},
                {"factor": "降雨诱发病害传播", "contribution": round(weather.rainfall * 0.9, 2)},
                {"factor": "作物易感性", "contribution": crop_risk},
                {"factor": "历史病害基线", "contribution": round(history * 2.8, 2)},
            ]
            db.add(
                RiskPrediction(
                    farm_id=farm.id,
                    prediction_date=day,
                    risk_score=round(score, 2),
                    risk_level=level,
                    top_factors=json.dumps(sorted(factors, key=lambda x: x["contribution"], reverse=True), ensure_ascii=False),
                )
            )
            latest_score = score
            latest_level = level
        farm.current_risk_score = round(latest_score, 2)
        farm.risk_level = latest_level


def create_pest_reports(db, farms: list[Farm]) -> None:
    for _ in range(650):
        farm = RNG.choice(farms)
        day = BASE_DATE - timedelta(days=RNG.randint(0, 150))
        crop_name = farm.crop.name
        disease = RNG.choice(DISEASES[crop_name])
        severity = RNG.choices(["轻", "中", "重"], weights=[0.54, 0.34, 0.12])[0]
        affected = farm.area_mu * RNG.uniform(0.01, 0.08 if severity == "轻" else 0.18 if severity == "中" else 0.32)
        db.add(
            PestDiseaseReport(
                farm_id=farm.id,
                crop_id=farm.crop_id,
                report_date=day,
                disease_name=f"{crop_name}{disease}",
                severity=severity,
                affected_area_mu=round(affected, 2),
                confidence=round(RNG.uniform(0.72, 0.96), 3),
                source=RNG.choice(["AI识别", "巡检上报", "合作社上报", "无人机巡查"]),
                status=RNG.choice(["待复核", "已确认", "已处置"]),
                treatment_suggestion="建议现场复核病斑扩展情况，按分区防控方案开展药剂或农艺处置。",
            )
        )


def create_yields(db, farms: list[Farm], weather_by_town: dict[str, list[WeatherRecord]]) -> None:
    baselines = {"水稻": 620, "小麦": 470, "玉米": 540, "番茄": 3800, "黄瓜": 4200}
    for farm in farms:
        for year in range(2022, 2027):
            risk_penalty = farm.current_risk_score * RNG.uniform(0.0018, 0.0035)
            weather_bonus = RNG.uniform(-0.05, 0.06)
            base = baselines.get(farm.crop.name, 600)
            predicted = base * (1 - risk_penalty + weather_bonus)
            actual = predicted * RNG.uniform(0.92, 1.05)
            loss_rate = max(0.0, min(0.36, 1 - actual / base))
            db.add(
                YieldRecord(
                    farm_id=farm.id,
                    crop_id=farm.crop_id,
                    year=year,
                    season="秋" if farm.crop.name in {"水稻", "玉米"} else "春",
                    yield_kg_per_mu=round(actual, 1),
                    predicted_yield_kg_per_mu=round(predicted, 1),
                    loss_rate=round(loss_rate, 4),
                )
            )


def create_alerts_and_tasks(db, farms: list[Farm]) -> None:
    high_or_mid = [f for f in farms if f.risk_level in {"高", "中"}]
    for i in range(120):
        farm = RNG.choice(high_or_mid)
        created_at = datetime.combine(BASE_DATE - timedelta(days=RNG.randint(0, 28)), datetime.min.time()) + timedelta(hours=RNG.randint(7, 19))
        alert = Alert(
            farm_id=farm.id,
            title=f"{farm.crop.name}病虫害{farm.risk_level}风险预警",
            risk_level=farm.risk_level,
            trigger_reason=f"{farm.town}{farm.name}风险评分 {farm.current_risk_score:.1f}，叠加高湿/降雨/历史病害因子。",
            status=RNG.choices(["待处理", "处理中", "已完成"], weights=[0.34, 0.31, 0.35])[0],
            owner=RNG.choice(["农技员王敏", "农技员李强", "植保专家陈工", "合作社管理员"]),
            suggestion="建议24小时内完成现场巡检，必要时开展统防统治并记录回访结果。",
            created_at=created_at,
            updated_at=created_at + timedelta(hours=RNG.randint(1, 24)),
        )
        db.add(alert)
        db.flush()
        if i < 90 or alert.risk_level == "高":
            db.add(
                InspectionTask(
                    farm_id=farm.id,
                    alert_id=alert.id,
                    title=f"{farm.name}风险复核巡检",
                    priority="高" if farm.risk_level == "高" else "中",
                    assignee=alert.owner,
                    due_date=(created_at + timedelta(days=RNG.randint(1, 4))).date(),
                    status=RNG.choices(["待处理", "处理中", "已完成"], weights=[0.3, 0.36, 0.34])[0],
                    description=f"核查{farm.crop.name}叶片病斑、虫口密度、田间湿度和排水情况。",
                    record=RNG.choice(["", "已完成样方调查，建议三日后回访。", "发现中心病株，已通知合作社处理。"]),
                    created_at=created_at,
                    updated_at=created_at + timedelta(hours=RNG.randint(1, 28)),
                )
            )
    for _ in range(110):
        farm = RNG.choice(farms)
        db.add(
            InspectionTask(
                farm_id=farm.id,
                title=f"{farm.name}常规农情巡检",
                priority=RNG.choice(["低", "中", "中", "高"]),
                assignee=RNG.choice(["农技员王敏", "农技员李强", "合作社管理员"]),
                due_date=BASE_DATE + timedelta(days=RNG.randint(0, 12)),
                status=RNG.choice(["待处理", "处理中", "已完成"]),
                description="采集叶片图像、土壤墒情和病虫害发生情况，补充模型训练样本。",
            )
        )


def create_model_metrics(db) -> None:
    metrics = [
        ("disease_classifier", "image_classification", "accuracy", 0.918),
        ("disease_classifier", "image_classification", "precision", 0.904),
        ("disease_classifier", "image_classification", "recall", 0.887),
        ("disease_classifier", "image_classification", "f1", 0.895),
        ("risk_model", "risk_regression", "mae", 4.82),
        ("risk_model", "risk_regression", "rmse", 6.37),
        ("risk_model", "risk_regression", "r2", 0.861),
        ("yield_forecast", "yield_regression", "mae", 19.4),
        ("yield_forecast", "yield_regression", "rmse", 27.8),
        ("yield_forecast", "yield_regression", "r2", 0.842),
        ("anomaly_detector", "sensor_anomaly", "precision", 0.873),
        ("anomaly_detector", "sensor_anomaly", "recall", 0.824),
    ]
    for model_name, task, metric, value in metrics:
        db.add(ModelMetric(model_name=model_name, task=task, metric_name=metric, metric_value=value))


def index_knowledge_docs(db) -> None:
    kb_dir = PROJECT_ROOT / "knowledge_base"
    for path in sorted(kb_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = next((line.lstrip("#").strip() for line in content.splitlines() if line.startswith("#")), path.stem)
        db.add(KnowledgeDoc(source=f"knowledge_base/{path.name}", title=title, content=content))


def export_demo_csv(db) -> None:
    out_dir = PROJECT_ROOT / "data" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    farms = db.query(Farm).all()
    pd.DataFrame(
        [
            {
                "id": f.id,
                "name": f.name,
                "town": f.town,
                "crop": f.crop.name,
                "area_mu": f.area_mu,
                "risk_level": f.risk_level,
                "risk_score": f.current_risk_score,
                "lat": f.lat,
                "lng": f.lng,
            }
            for f in farms
        ]
    ).to_csv(out_dir / "farms.csv", index=False, encoding="utf-8-sig")


def rectangle_polygon(lat: float, lng: float, height: float, width: float) -> list[list[float]]:
    return [
        [lat - height / 2, lng - width / 2],
        [lat - height / 2, lng + width / 2],
        [lat + height / 2, lng + width / 2],
        [lat + height / 2, lng - width / 2],
    ]


if __name__ == "__main__":
    main()
