"""ADS 指标口径的 pandas 参考实现（回归基线）。

用途不是替代 Spark 主链路，而是给 Spark 作业提供一份可在纯 Python 环境运行的
**口径基准**：两者读同一份 ODS 数据、用同一套清洗规则与风险评分公式，
结果应当逐字段一致。测试环节用 ``scripts/compare_ads_outputs.py`` 做差异比对，
任何一侧改动口径都会被立刻发现。

因为要在单机内存中完成，本脚本默认按分区流式读取并逐月聚合，
不把百万级明细一次性载入内存。

用法::

    python batch_jobs/pandas_jobs/ads_reference_job.py --lake data/lake --out data/lake/ads_reference
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 与 Spark 主链路保持同一套阈值：高 ≈ P96、中 ≈ P80 分位标定
RISK_HIGH = 52.0
RISK_MID = 36.0

CROP_SUSCEPTIBILITY = {"水稻": 1.15, "小麦": 0.95, "玉米": 0.90, "番茄": 1.20, "黄瓜": 1.10}
VALID_RANGES = {
    "soil_moisture": (0.02, 0.98),
    "soil_temp": (-25.0, 60.0),
    "soil_ph": (3.0, 10.0),
    "nitrogen": (0.0, 400.0),
    "phosphorus": (0.0, 300.0),
    "potassium": (0.0, 600.0),
    "temperature": (-35.0, 50.0),
    "humidity": (0.0, 100.0),
    "rainfall_mm": (0.0, 400.0),
}


def clip_range(series: pd.Series, name: str) -> pd.Series:
    lo, hi = VALID_RANGES[name]
    return series.where(series.between(lo, hi))


def read_table(lake: Path, table: str) -> pd.DataFrame:
    files = sorted((lake / "ods" / table).rglob("*.csv.gz"))
    if not files:
        raise FileNotFoundError(f"未找到 ODS 分区：{lake / 'ods' / table}，请先运行 scripts/generate_bigdata_layer.py")
    return pd.concat((pd.read_csv(f) for f in files), ignore_index=True)


def clean_weather(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    raw = len(df)
    df = df.drop_duplicates(subset=["record_id"])
    after_dedup = len(df)
    df["obs_time"] = pd.to_datetime(df["obs_time"], errors="coerce")
    df["stat_date"] = df["obs_time"].dt.date
    df["temperature"] = clip_range(df["temperature"], "temperature")
    df["humidity"] = clip_range(df["humidity"], "humidity")
    df["rainfall_mm"] = clip_range(df["rainfall_mm"], "rainfall_mm").fillna(0.0)
    df = df[df["obs_time"].notna() & df["town_code"].notna()]
    for col in ("temperature", "humidity"):
        df[col] = df[col].fillna(df.groupby("town_code")[col].transform("mean"))
    df["wind_speed"] = df["wind_speed"].fillna(0.0)
    kept = len(df)
    return df, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def clean_sensor(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    raw = len(df)
    df = df.drop_duplicates(subset=["record_id"])
    after_dedup = len(df)
    df["collect_time"] = pd.to_datetime(df["collect_time"], errors="coerce")
    df["stat_date"] = df["collect_time"].dt.date
    df["is_outlier"] = (~df["soil_moisture"].between(*VALID_RANGES["soil_moisture"])).astype(int)
    for col in ("soil_moisture", "soil_temp", "soil_ph", "nitrogen", "phosphorus", "potassium"):
        df[col] = clip_range(df[col], col)
    df = df[df["collect_time"].notna() & df["farm_id"].notna() & df["soil_moisture"].notna()]
    kept = len(df)
    return df, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def clean_scout(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    raw = len(df)
    df = df.drop_duplicates(subset=["record_id"])
    after_dedup = len(df)
    df["scout_time"] = pd.to_datetime(df["scout_time"], errors="coerce")
    df["stat_date"] = df["scout_time"].dt.date
    df = df[df["scout_time"].notna() & df["incidence_rate"].between(0, 100)]
    df["affected_mu"] = df["affected_mu"].where(df["affected_mu"] >= 0, 0.0)
    kept = len(df)
    return df, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def clean_yield(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    raw = len(df)
    df = df.drop_duplicates(subset=["record_id"])
    after_dedup = len(df)
    df = df[
        (df["actual_yield_kg_per_mu"] > 0)
        & (df["actual_yield_kg_per_mu"] < 20000)
        & df["loss_rate"].between(0, 1)
    ]
    kept = len(df)
    return df, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def build_dws(weather: pd.DataFrame, sensor: pd.DataFrame, scout: pd.DataFrame) -> pd.DataFrame:
    weather_daily = (
        weather.groupby(["town_code", "town", "stat_date"])
        .agg(
            avg_temp=("temperature", "mean"),
            max_temp=("temperature", "max"),
            avg_humidity=("humidity", "mean"),
            rainfall_mm=("rainfall_mm", "sum"),
            avg_wind=("wind_speed", "mean"),
            high_humid_hours=("humidity", lambda s: int((s >= 85).sum())),
        )
        .reset_index()
        .round({"avg_temp": 2, "max_temp": 2, "avg_humidity": 2, "rainfall_mm": 2, "avg_wind": 2})
    )

    sensor_daily = (
        sensor.groupby(["farm_id", "farm_code", "town_code", "town", "crop", "stat_date"])
        .agg(
            avg_soil_moisture=("soil_moisture", "mean"),
            std_soil_moisture=("soil_moisture", lambda s: s.std(ddof=0)),
            avg_soil_temp=("soil_temp", "mean"),
            avg_soil_ph=("soil_ph", "mean"),
            avg_nitrogen=("nitrogen", "mean"),
            avg_potassium=("potassium", "mean"),
            reading_cnt=("soil_moisture", "size"),
            outlier_cnt=("is_outlier", "sum"),
        )
        .reset_index()
        .round({"avg_soil_moisture": 4, "std_soil_moisture": 4, "avg_soil_temp": 2,
                "avg_soil_ph": 2, "avg_nitrogen": 1, "avg_potassium": 1})
    )

    scout_daily = (
        scout.groupby(["farm_id", "stat_date"])
        .agg(
            avg_incidence=("incidence_rate", "mean"),
            max_incidence=("incidence_rate", "max"),
            affected_mu=("affected_mu", "sum"),
            scout_cnt=("incidence_rate", "size"),
        )
        .reset_index()
        .round({"avg_incidence": 2, "max_incidence": 2, "affected_mu": 2})
    )

    wide = sensor_daily.merge(weather_daily, on=["town_code", "town", "stat_date"], how="left")
    wide = wide.merge(scout_daily, on=["farm_id", "stat_date"], how="left")
    wide[["avg_incidence", "max_incidence", "affected_mu"]] = wide[["avg_incidence", "max_incidence", "affected_mu"]].fillna(0.0)
    wide["scout_cnt"] = wide["scout_cnt"].fillna(0).astype(int)
    wide["susceptibility"] = wide["crop"].map(CROP_SUSCEPTIBILITY).fillna(1.0)

    # 近 14 日历史病害压力（不含当日），与 Spark 的 rangeBetween 窗口口径一致
    wide = wide.sort_values(["farm_id", "stat_date"]).reset_index(drop=True)
    wide["_d"] = pd.to_datetime(wide["stat_date"])
    hist = (
        wide.set_index("_d")
        .groupby("farm_id")["avg_incidence"]
        .apply(lambda s: s.shift(1).rolling("14D").mean())
        .reset_index(level=0, drop=True)
        .sort_index(kind="stable")
    )
    wide["hist_incidence_14d"] = hist.to_numpy()
    wide["hist_incidence_14d"] = wide["hist_incidence_14d"].fillna(0.0).round(3)
    wide = wide.drop(columns=["_d"])

    wide["humid_score"] = np.clip((wide["avg_humidity"] - 60) / 35 * 34, 0, 34).round(2)
    wide["rain_score"] = np.clip(wide["rainfall_mm"] / 30 * 18, None, 18).round(2)
    wide["moist_score"] = np.clip((wide["avg_soil_moisture"] - 0.32) / 0.35 * 16, 0, 16).round(2)
    wide["hist_score"] = np.clip(wide["hist_incidence_14d"] / 20 * 22, None, 22).round(2)
    wide["temp_score"] = np.clip((wide["avg_temp"] - 18) / 14 * 10, 0, 10).round(2)

    parts = ["humid_score", "rain_score", "moist_score", "hist_score", "temp_score"]
    wide["risk_score"] = np.minimum(wide[parts].sum(axis=1) * wide["susceptibility"], 100.0).round(2)
    wide["risk_level"] = np.select(
        [wide["risk_score"] >= RISK_HIGH, wide["risk_score"] >= RISK_MID], ["高", "中"], default="低"
    )
    labels = np.array(["空气湿度", "降雨量", "土壤墒情", "历史病害", "积温条件"])
    wide["top_factor"] = labels[wide[parts].to_numpy().argmax(axis=1)]
    return wide


def build_ads(dws: pd.DataFrame, yields: pd.DataFrame) -> dict[str, list[dict]]:
    latest = max(dws["stat_date"])
    today = dws[dws["stat_date"] == latest]

    town_ranking = (
        today.groupby("town")
        .agg(
            avg_risk=("risk_score", "mean"),
            high_risk_farms=("risk_level", lambda s: int((s == "高").sum())),
            farm_count=("farm_id", "nunique"),
            affected_mu=("affected_mu", "sum"),
        )
        .reset_index()
        .round({"avg_risk": 2, "affected_mu": 1})
        .sort_values("avg_risk", ascending=False)
    )

    crop_distribution = (
        today.groupby(["crop", "risk_level"])
        .agg(farm_count=("farm_id", "size"), avg_risk=("risk_score", "mean"))
        .reset_index()
        .round({"avg_risk": 2})
        .sort_values(["crop", "risk_level"])
    )

    trend_start = pd.Timestamp(latest) - pd.Timedelta(days=30)
    trend_src = dws[pd.to_datetime(dws["stat_date"]) > trend_start]
    risk_trend = (
        trend_src.groupby("stat_date")
        .agg(risk_score=("risk_score", "mean"), high_risk_farms=("risk_level", lambda s: int((s == "高").sum())))
        .reset_index()
        .round({"risk_score": 2})
        .sort_values("stat_date")
    )

    yield_summary = (
        yields.groupby(["crop", "year"])
        .agg(
            avg_yield_kg_per_mu=("actual_yield_kg_per_mu", "mean"),
            avg_loss_pct=("loss_rate", lambda s: s.mean() * 100),
            plot_cnt=("loss_rate", "size"),
        )
        .reset_index()
        .round({"avg_yield_kg_per_mu": 2, "avg_loss_pct": 2})
        .sort_values(["crop", "year"])
    )

    inspection = (
        today.sort_values("risk_score", ascending=False)
        .head(30)[["farm_code", "town", "crop", "risk_score", "risk_level", "top_factor",
                   "avg_soil_moisture", "avg_humidity", "affected_mu"]]
        .copy()
    )
    inspection["priority"] = np.select(
        [inspection["risk_score"] >= RISK_HIGH, inspection["risk_score"] >= RISK_MID], ["高", "中"], default="低"
    )

    dispatch = (
        today.groupby("town")
        .agg(avg_risk=("risk_score", "mean"), affected_mu=("affected_mu", "sum"))
        .reset_index()
    )
    dispatch["drone_sorties"] = np.ceil(dispatch["affected_mu"] / 300.0).astype(int)
    dispatch["agronomist_needed"] = np.ceil(dispatch["affected_mu"] / 500.0).astype(int)
    dispatch["pesticide_kg"] = (dispatch["affected_mu"] * 0.12).round(1)
    dispatch = dispatch.round({"avg_risk": 2, "affected_mu": 1}).sort_values("avg_risk", ascending=False)

    return {
        "latest_stat_date": str(latest),
        "ads_town_risk_ranking": town_ranking.to_dict("records"),
        "ads_crop_risk_distribution": crop_distribution.to_dict("records"),
        "ads_risk_trend_30d": risk_trend.assign(stat_date=lambda d: d["stat_date"].astype(str)).to_dict("records"),
        "ads_yield_summary": yield_summary.to_dict("records"),
        "ads_inspection_priority": inspection.to_dict("records"),
        "ads_material_dispatch": dispatch.to_dict("records"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ADS 指标 pandas 参考实现")
    parser.add_argument("--lake", default="data/lake")
    parser.add_argument("--out", default="data/lake/ads_reference")
    args = parser.parse_args()

    lake = Path(args.lake) if Path(args.lake).is_absolute() else PROJECT_ROOT / args.lake
    out = Path(args.out) if Path(args.out).is_absolute() else PROJECT_ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    started = time.time()
    quality: dict[str, dict] = {}
    weather, quality["ods_weather_raw"] = clean_weather(read_table(lake, "ods_weather_raw"))
    sensor, quality["ods_sensor_raw"] = clean_sensor(read_table(lake, "ods_sensor_raw"))
    scout, quality["ods_pest_scout_raw"] = clean_scout(read_table(lake, "ods_pest_scout_raw"))
    yields, quality["ods_yield_plot_raw"] = clean_yield(read_table(lake, "ods_yield_plot_raw"))

    dws = build_dws(weather, sensor, scout)
    ads = build_ads(dws, yields)

    for name, rows in ads.items():
        if name == "latest_stat_date":
            continue
        (out / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    report = {
        "engine": "pandas reference",
        "layers": {
            "ods_rows": sum(v["raw"] for v in quality.values()),
            "dwd_rows": sum(v["kept"] for v in quality.values()),
            "dws_rows": int(len(dws)),
            "ads_tables": {k: len(v) for k, v in ads.items() if k != "latest_stat_date"},
        },
        "data_quality": quality,
        "timings_seconds": {"total": round(time.time() - started, 2)},
        "latest_stat_date": ads["latest_stat_date"],
    }
    (out / "_run_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
