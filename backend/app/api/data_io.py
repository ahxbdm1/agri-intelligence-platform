from __future__ import annotations

from datetime import date, datetime
from io import BytesIO, StringIO
from pathlib import Path
import re
import uuid

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import ROOT_DIR
from app.models import Crop, Farm, PestDiseaseReport, SensorRecord, WeatherRecord, YieldRecord


router = APIRouter(prefix="/api/data", tags=["数据管理"], dependencies=[Depends(get_current_user)])

MAX_IMPORT_BYTES = 10 * 1024 * 1024
DATASETS = {
    "farms": ["name", "town", "crop", "area_mu", "lat", "lng"],
    "weather_records": ["town", "record_date", "temperature", "humidity", "rainfall"],
    "sensor_records": ["farm_id", "recorded_at", "soil_moisture", "soil_temperature", "ph"],
    "pest_disease_reports": ["farm_id", "crop_id", "report_date", "disease_name"],
    "yield_records": ["farm_id", "crop_id", "year", "yield_kg_per_mu"],
}


@router.post("/import")
async def import_csv(
    dataset: str = Query(default="custom"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    if dataset != "custom" and dataset not in DATASETS:
        raise HTTPException(status_code=400, detail=f"不支持的数据集类型：{dataset}")
    filename = _safe_filename(file.filename or "upload.csv")
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="当前版本仅支持 CSV 文件")
    content = await file.read()
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="CSV 文件不能超过 10MB")
    try:
        frame = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV 解析失败：{exc}") from exc
    if frame.empty:
        raise HTTPException(status_code=400, detail="CSV 不包含任何数据行")
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = [column for column in DATASETS.get(dataset, []) if column not in frame.columns]
    if missing:
        raise HTTPException(status_code=400, detail={"message": "缺少必要字段", "missing": missing, "dataset": dataset})

    raw_dir = ROOT_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    saved_path = raw_dir / f"{uuid.uuid4().hex[:12]}-{filename}"
    saved_path.write_bytes(content)
    result = {
        "dataset": dataset,
        "filename": filename,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "preview": frame.head(5).fillna("").to_dict(orient="records"),
        "saved_file": str(saved_path.relative_to(ROOT_DIR)),
        "inserted": 0,
        "updated": 0,
        "rejected": 0,
        "errors": [],
    }
    if dataset != "custom":
        _persist_dataset(dataset, frame, db, result)
        db.commit()
    result["note"] = "文件已完成校验并落盘；命名数据集已写入对应业务表，可继续运行批处理与模型训练。"
    return result


@router.get("/export", response_model=None)
def export_data(
    dataset: str = Query(default="summary"),
    format: str = Query(default="summary"),
    db: Session = Depends(get_db),
) -> dict | StreamingResponse:
    summary = {
        "farms": db.query(Farm).count(),
        "weather_records": db.query(WeatherRecord).count(),
        "sensor_records": db.query(SensorRecord).count(),
        "pest_disease_reports": db.query(PestDiseaseReport).count(),
        "yield_records": db.query(YieldRecord).count(),
    }
    if format == "summary" or dataset == "summary":
        return {
            "summary": summary,
            "formats": ["JSON", "CSV", "Markdown Report", "HTML Report"],
            "datasets": list(DATASETS),
            "note": "可按数据集导出 CSV，也可生成正式 Markdown/HTML 农情日报。",
        }
    if format != "csv" or dataset not in DATASETS:
        raise HTTPException(status_code=400, detail="导出格式仅支持 csv，数据集必须是已登记类型")

    frame = _export_frame(dataset, db)
    stream = StringIO()
    frame.to_csv(stream, index=False)
    headers = {"Content-Disposition": f'attachment; filename="{dataset}.csv"'}
    return StreamingResponse(iter([stream.getvalue().encode("utf-8-sig")]), media_type="text/csv; charset=utf-8", headers=headers)


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", name)
    return name[:120] or "upload.csv"


def _persist_dataset(dataset: str, frame: pd.DataFrame, db: Session, result: dict) -> None:
    for index, row in frame.iterrows():
        try:
            if dataset == "farms":
                crop = db.query(Crop).filter(Crop.name == _text(row, "crop")).first()
                if crop is None:
                    raise ValueError(f"第 {index + 2} 行作物不存在")
                farm = db.query(Farm).filter(Farm.name == _text(row, "name")).first()
                values = {
                    "name": _text(row, "name"),
                    "town": _text(row, "town"),
                    "crop_id": crop.id,
                    "area_mu": _number(row, "area_mu"),
                    "lat": _number(row, "lat"),
                    "lng": _number(row, "lng"),
                    "polygon_json": _text(row, "polygon_json", "[]"),
                    "soil_type": _text(row, "soil_type", "壤土"),
                    "irrigation_level": _text(row, "irrigation_level", "中"),
                    "owner": _text(row, "owner", "导入数据"),
                    "current_risk_score": _number(row, "risk_score", 0),
                    "risk_level": _text(row, "risk_level", "低"),
                }
                if farm:
                    for key, value in values.items():
                        setattr(farm, key, value)
                    result["updated"] += 1
                else:
                    db.add(Farm(**values))
                    result["inserted"] += 1
            elif dataset == "weather_records":
                db.add(WeatherRecord(
                    town=_text(row, "town"),
                    record_date=_date(row, "record_date"),
                    temperature=_number(row, "temperature"),
                    humidity=_number(row, "humidity"),
                    rainfall=_number(row, "rainfall"),
                    wind_speed=_number(row, "wind_speed", 0),
                    sunshine_hours=_number(row, "sunshine_hours", 0),
                    weather_type=_text(row, "weather_type", "多云"),
                ))
                result["inserted"] += 1
            elif dataset == "sensor_records":
                _require_farm(db, row, index)
                db.add(SensorRecord(
                    farm_id=int(_number(row, "farm_id")),
                    recorded_at=_datetime(row, "recorded_at"),
                    soil_moisture=_number(row, "soil_moisture"),
                    soil_temperature=_number(row, "soil_temperature", 25),
                    ph=_number(row, "ph", 6.8),
                    light_intensity=_number(row, "light_intensity", 1000),
                    nitrogen=_number(row, "nitrogen", 80),
                    phosphorus=_number(row, "phosphorus", 40),
                    potassium=_number(row, "potassium", 90),
                    anomaly_flag=bool(_number(row, "anomaly_flag", 0)),
                ))
                result["inserted"] += 1
            elif dataset == "pest_disease_reports":
                _require_farm(db, row, index)
                db.add(PestDiseaseReport(
                    farm_id=int(_number(row, "farm_id")),
                    crop_id=int(_number(row, "crop_id")),
                    report_date=_date(row, "report_date"),
                    disease_name=_text(row, "disease_name"),
                    severity=_text(row, "severity", "轻"),
                    affected_area_mu=_number(row, "affected_area_mu", 0),
                    confidence=_number(row, "confidence", 0.8),
                    source=_text(row, "source", "导入数据"),
                    status=_text(row, "status", "待复核"),
                    treatment_suggestion=_text(row, "treatment_suggestion", ""),
                ))
                result["inserted"] += 1
            elif dataset == "yield_records":
                _require_farm(db, row, index)
                yield_value = _number(row, "yield_kg_per_mu")
                db.add(YieldRecord(
                    farm_id=int(_number(row, "farm_id")),
                    crop_id=int(_number(row, "crop_id")),
                    year=int(_number(row, "year")),
                    season=_text(row, "season", "夏"),
                    yield_kg_per_mu=yield_value,
                    predicted_yield_kg_per_mu=_number(row, "predicted_yield_kg_per_mu", yield_value),
                    loss_rate=_number(row, "loss_rate", 0),
                ))
                result["inserted"] += 1
        except (TypeError, ValueError, KeyError) as exc:
            result["rejected"] += 1
            if len(result["errors"]) < 20:
                result["errors"].append(str(exc))


def _export_frame(dataset: str, db: Session) -> pd.DataFrame:
    if dataset == "farms":
        rows = db.query(Farm).all()
        return pd.DataFrame([{"id": row.id, "name": row.name, "town": row.town, "crop": row.crop.name if row.crop else "", "area_mu": row.area_mu, "lat": row.lat, "lng": row.lng, "risk_level": row.risk_level, "risk_score": row.current_risk_score} for row in rows])
    if dataset == "weather_records":
        return pd.read_sql_query("select town, record_date, temperature, humidity, rainfall, wind_speed, sunshine_hours, weather_type from weather_records", db.get_bind())
    if dataset == "sensor_records":
        return pd.read_sql_query("select farm_id, recorded_at, soil_moisture, soil_temperature, ph, light_intensity, nitrogen, phosphorus, potassium, anomaly_flag from sensor_records", db.get_bind())
    if dataset == "pest_disease_reports":
        return pd.read_sql_query("select farm_id, crop_id, report_date, disease_name, severity, affected_area_mu, confidence, source, status from pest_disease_reports", db.get_bind())
    return pd.read_sql_query("select farm_id, crop_id, year, season, yield_kg_per_mu, predicted_yield_kg_per_mu, loss_rate from yield_records", db.get_bind())


def _text(row: pd.Series, key: str, default: str = "") -> str:
    value = row.get(key, default)
    return default if pd.isna(value) else str(value).strip()


def _number(row: pd.Series, key: str, default: float | None = None) -> float:
    value = row.get(key, default)
    if pd.isna(value) or value is None:
        if default is None:
            raise ValueError(f"字段 {key} 不能为空")
        return float(default)
    return float(value)


def _date(row: pd.Series, key: str) -> date:
    value = pd.to_datetime(_text(row, key), errors="coerce")
    if pd.isna(value):
        raise ValueError(f"字段 {key} 不是有效日期")
    return value.date()


def _datetime(row: pd.Series, key: str) -> datetime:
    value = pd.to_datetime(_text(row, key), errors="coerce")
    if pd.isna(value):
        raise ValueError(f"字段 {key} 不是有效时间")
    return value.to_pydatetime()


def _require_farm(db: Session, row: pd.Series, index: int) -> None:
    farm_id = int(_number(row, "farm_id"))
    if db.query(Farm).filter(Farm.id == farm_id).first() is None:
        raise ValueError(f"第 {index + 2} 行地块 {farm_id} 不存在")
