from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    organization: Mapped[str] = mapped_column(String(128), default="云澜县农业农村局")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    variety: Mapped[str] = mapped_column(String(64), default="")
    growth_days: Mapped[int] = mapped_column(Integer, default=120)
    optimal_temp_min: Mapped[float] = mapped_column(Float, default=18)
    optimal_temp_max: Mapped[float] = mapped_column(Float, default=28)

    farms: Mapped[list["Farm"]] = relationship(back_populates="crop")


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    town: Mapped[str] = mapped_column(String(64), index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"))
    area_mu: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    polygon_json: Mapped[str] = mapped_column(Text)
    soil_type: Mapped[str] = mapped_column(String(64), default="壤土")
    irrigation_level: Mapped[str] = mapped_column(String(32), default="中")
    owner: Mapped[str] = mapped_column(String(128), default="")
    current_risk_score: Mapped[float] = mapped_column(Float, default=0)
    risk_level: Mapped[str] = mapped_column(String(16), default="低")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    crop: Mapped[Crop] = relationship(back_populates="farms")
    weather_records: Mapped[list["WeatherRecord"]] = relationship(back_populates="farm")
    sensor_records: Mapped[list["SensorRecord"]] = relationship(back_populates="farm")
    reports: Mapped[list["PestDiseaseReport"]] = relationship(back_populates="farm")
    risks: Mapped[list["RiskPrediction"]] = relationship(back_populates="farm")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="farm")
    tasks: Mapped[list["InspectionTask"]] = relationship(back_populates="farm")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int | None] = mapped_column(ForeignKey("farms.id"), nullable=True, index=True)
    town: Mapped[str] = mapped_column(String(64), index=True)
    record_date: Mapped[datetime] = mapped_column(Date, index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    rainfall: Mapped[float] = mapped_column(Float)
    wind_speed: Mapped[float] = mapped_column(Float)
    sunshine_hours: Mapped[float] = mapped_column(Float)
    weather_type: Mapped[str] = mapped_column(String(32), default="多云")

    farm: Mapped[Farm | None] = relationship(back_populates="weather_records")


class SensorRecord(Base):
    __tablename__ = "sensor_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    soil_moisture: Mapped[float] = mapped_column(Float)
    soil_temperature: Mapped[float] = mapped_column(Float)
    ph: Mapped[float] = mapped_column(Float)
    light_intensity: Mapped[float] = mapped_column(Float)
    nitrogen: Mapped[float] = mapped_column(Float)
    phosphorus: Mapped[float] = mapped_column(Float)
    potassium: Mapped[float] = mapped_column(Float)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    farm: Mapped[Farm] = relationship(back_populates="sensor_records")


class PestDiseaseReport(Base):
    __tablename__ = "pest_disease_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    report_date: Mapped[datetime] = mapped_column(Date, index=True)
    disease_name: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16), default="轻")
    affected_area_mu: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    source: Mapped[str] = mapped_column(String(32), default="巡检上报")
    status: Mapped[str] = mapped_column(String(32), default="待复核")
    treatment_suggestion: Mapped[str] = mapped_column(Text, default="")

    farm: Mapped[Farm] = relationship(back_populates="reports")


class YieldRecord(Base):
    __tablename__ = "yield_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    crop_id: Mapped[int] = mapped_column(ForeignKey("crops.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[str] = mapped_column(String(16), default="夏")
    yield_kg_per_mu: Mapped[float] = mapped_column(Float)
    predicted_yield_kg_per_mu: Mapped[float] = mapped_column(Float)
    loss_rate: Mapped[float] = mapped_column(Float, default=0)


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    prediction_date: Mapped[datetime] = mapped_column(Date, index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    risk_level: Mapped[str] = mapped_column(String(16), default="低")
    top_factors: Mapped[str] = mapped_column(Text, default="[]")
    model_version: Mapped[str] = mapped_column(String(32), default="rf-demo-v1")

    farm: Mapped[Farm] = relationship(back_populates="risks")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    trigger_reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="待处理", index=True)
    owner: Mapped[str] = mapped_column(String(64), default="农技站")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm: Mapped[Farm] = relationship(back_populates="alerts")
    tasks: Mapped[list["InspectionTask"]] = relationship(back_populates="alert")


class InspectionTask(Base):
    __tablename__ = "inspection_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    priority: Mapped[str] = mapped_column(String(16), default="中", index=True)
    assignee: Mapped[str] = mapped_column(String(64), default="农技员A")
    due_date: Mapped[datetime] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="待处理")
    description: Mapped[str] = mapped_column(Text, default="")
    record: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm: Mapped[Farm] = relationship(back_populates="tasks")
    alert: Mapped[Alert | None] = relationship(back_populates="tasks")


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(64), index=True)
    task: Mapped[str] = mapped_column(String(64))
    metric_name: Mapped[str] = mapped_column(String(32))
    metric_value: Mapped[float] = mapped_column(Float)
    dataset_version: Mapped[str] = mapped_column(String(32), default="demo-seed-2026")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(160), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
