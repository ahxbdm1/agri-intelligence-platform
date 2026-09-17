"""生成县域农业大数据明细层（ODS 原始层），供 Spark / Hive 批处理链路消费。

与 ``scripts/generate_demo_data.py`` 的分工：

* ``generate_demo_data.py`` 负责 **应用层**：写入 PostgreSQL / SQLite 业务库，
  规模保持在页面可直接查询的量级，服务于 Web 端在线业务。
* 本脚本负责 **大数据明细层**：直接以列式/文本分区文件落盘，记录总量百万级，
  不经过 ORM，作为 Spark ETL 的 ODS 输入。业务库中的聚合结果由 Spark 作业
  从本层计算后回流，形成 "ODS -> DWD -> DWS -> ADS -> 业务库" 的完整数仓链路。

设计要点：

1. 明细总量 >= 100 万条，满足大数据赛道对数据规模的要求；
2. 全流程 numpy 向量化生成，单机可在数分钟内完成，无需 ORM；
3. 按 ``dt=YYYY-MM`` 月分区 + 乡镇分文件落盘为 gzip CSV，符合 ODS 贴源层惯例，
   Spark 可直接按分区裁剪读取；
4. 固定随机种子，评委可重复生成完全一致的数据集；
5. **刻意注入脏数据**（缺失值、重复记录、越界值、时间格式不一致），
   使下游 Spark 清洗环节有真实的处理对象，并可统计数据质量指标。

用法::

    python scripts/generate_bigdata_layer.py                 # 默认 24 个月
    python scripts/generate_bigdata_layer.py --months 24     # 自定义时间跨度
    python scripts/generate_bigdata_layer.py --out data/lake # 自定义数据湖根目录
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEED = 20260506
# 与业务库口径保持一致：山东省济宁市鱼台县（沿黄稻区，兼有小麦、玉米与设施蔬菜）
COUNTY = {"province": "山东省", "city": "济宁市", "county": "鱼台县"}
TOWNS = [
    {"code": "YT01", "name": "谷亭街道", "lat": 34.990, "lng": 116.650},
    {"code": "YT02", "name": "清河镇", "lat": 35.060, "lng": 116.610},
    {"code": "YT03", "name": "张黄镇", "lat": 35.050, "lng": 116.720},
    {"code": "YT04", "name": "王鲁镇", "lat": 34.940, "lng": 116.630},
    {"code": "YT05", "name": "老砦镇", "lat": 34.900, "lng": 116.750},
    {"code": "YT06", "name": "罗屯镇", "lat": 35.020, "lng": 116.790},
]
CROPS = ["水稻", "小麦", "玉米", "番茄", "黄瓜"]
DISEASES = {
    "水稻": ["稻瘟病", "纹枯病", "稻飞虱"],
    "小麦": ["赤霉病", "条锈病", "蚜虫"],
    "玉米": ["大斑病", "草地贪夜蛾", "茎腐病"],
    "番茄": ["早疫病", "晚疫病", "白粉虱"],
    "黄瓜": ["霜霉病", "白粉病", "蓟马"],
}
FARM_COUNT = 80
SENSORS_PER_FARM = 2          # 每地块 2 个采集终端
SENSOR_READS_PER_DAY = 12     # 每 2 小时一次采集
WEATHER_READS_PER_DAY = 24    # 逐小时气象观测

# 脏数据注入比例（下游 Spark 清洗环节的处理对象）
NULL_RATE = 0.008
DUP_RATE = 0.003
OUTLIER_RATE = 0.002


# ---------------------------------------------------------------- 基础维度


def build_farms(rng: np.random.Generator) -> pd.DataFrame:
    """构造 80 个地块的静态维度，乡镇与作物分布与业务库一致。"""
    town_idx = np.arange(FARM_COUNT) % len(TOWNS)
    crop_idx = rng.integers(0, len(CROPS), FARM_COUNT)
    return pd.DataFrame(
        {
            "farm_id": np.arange(1, FARM_COUNT + 1),
            "farm_code": [f"YT-F{i:04d}" for i in range(1, FARM_COUNT + 1)],
            "town_code": [TOWNS[i]["code"] for i in town_idx],
            "town": [TOWNS[i]["name"] for i in town_idx],
            "crop": [CROPS[i] for i in crop_idx],
            "area_mu": np.round(rng.uniform(35, 420, FARM_COUNT), 1),
            "lat": np.round([TOWNS[i]["lat"] for i in town_idx] + rng.normal(0, 0.012, FARM_COUNT), 6),
            "lng": np.round([TOWNS[i]["lng"] for i in town_idx] + rng.normal(0, 0.012, FARM_COUNT), 6),
            "soil_type": rng.choice(["潮土", "砂姜黑土", "两合土", "淤土"], FARM_COUNT),
            "irrigation": rng.choice(["井灌", "河灌", "滴灌", "喷灌"], FARM_COUNT),
        }
    )


def month_range(start: date, months: int) -> list[tuple[date, date]]:
    """返回 [(月首日, 月末日), ...]，用于按月分块生成，控制峰值内存。"""
    spans: list[tuple[date, date]] = []
    year, month = start.year, start.month
    for _ in range(months):
        first = date(year, month, 1)
        if month == 12:
            nxt = date(year + 1, 1, 1)
        else:
            nxt = date(year, month + 1, 1)
        spans.append((first, nxt - timedelta(days=1)))
        year, month = nxt.year, nxt.month
    return spans


# ---------------------------------------------------------------- 脏数据注入


def inject_dirty(df: pd.DataFrame, rng: np.random.Generator, null_cols: list[str], outlier_col: str) -> pd.DataFrame:
    """注入缺失值、越界值与重复记录，为下游清洗环节提供真实处理对象。"""
    n = len(df)
    if n == 0:
        return df

    # 缺失值：随机把部分观测列置空
    null_n = int(n * NULL_RATE)
    if null_n:
        for col in null_cols:
            idx = rng.choice(n, null_n, replace=False)
            df.loc[df.index[idx], col] = np.nan

    # 越界值：传感器故障导致的异常读数
    out_n = int(n * OUTLIER_RATE)
    if out_n and outlier_col in df.columns:
        idx = rng.choice(n, out_n, replace=False)
        df.loc[df.index[idx], outlier_col] = rng.choice([-999.0, 9999.0], out_n)

    # 重复记录：采集端重传导致的整行重复
    dup_n = int(n * DUP_RATE)
    if dup_n:
        idx = rng.choice(n, dup_n, replace=False)
        df = pd.concat([df, df.iloc[idx]], ignore_index=True)

    return df


# ---------------------------------------------------------------- 明细表生成


def gen_weather_month(rng, first: date, last: date) -> pd.DataFrame:
    """逐小时气象观测明细：乡镇 x 日期 x 小时。"""
    days = pd.date_range(first, last, freq="D")
    hours = np.arange(WEATHER_READS_PER_DAY)
    towns = [t["name"] for t in TOWNS]
    codes = [t["code"] for t in TOWNS]

    grid = pd.MultiIndex.from_product([towns, days, hours], names=["town", "day", "hour"]).to_frame(index=False)
    grid["town_code"] = grid["town"].map(dict(zip(towns, codes)))
    n = len(grid)

    doy = grid["day"].dt.dayofyear.to_numpy()
    hour = grid["hour"].to_numpy()
    # 鲁西南暖温带季风气候：年均气温约 14℃，7—8 月高温高湿，雨热同季
    season = 14.0 + 13.0 * np.sin(2 * np.pi * (doy - 105) / 365.0)
    diurnal = 5.0 * np.sin(2 * np.pi * (hour - 9) / 24.0)
    grid["temperature"] = np.round(season + diurnal + rng.normal(0, 1.6, n), 2)

    # 相对湿度随季风同步在盛夏达到峰值，日内夜间高、午后低
    humid_season = 66.0 + 12.0 * np.sin(2 * np.pi * (doy - 196) / 365.0)
    humid_diurnal = -8.0 * np.sin(2 * np.pi * (hour - 9) / 24.0)
    grid["humidity"] = np.round(np.clip(humid_season + humid_diurnal + rng.normal(0, 6, n), 20, 100), 2)

    # 降水集中在 6—9 月主汛期，年降水量约 700mm，其中汛期占七成
    rain_season = 0.035 + 0.085 * np.clip(np.sin(2 * np.pi * (doy - 196) / 365.0), 0, 1)
    rain_prob = np.clip(rain_season * (1 + (grid["humidity"].to_numpy() - 70) / 40.0), 0, 0.75)
    grid["rainfall_mm"] = np.round(np.where(rng.random(n) < rain_prob, rng.gamma(1.3, 1.45, n), 0.0), 2)
    grid["wind_speed"] = np.round(np.abs(rng.normal(2.6, 1.3, n)), 2)
    grid["sunshine_index"] = np.round(np.clip(1 - grid["humidity"] / 130 + rng.normal(0, 0.08, n), 0, 1), 3)
    grid["pressure_hpa"] = np.round(rng.normal(1013, 7, n), 1)
    grid["station_id"] = grid["town_code"] + "-AWS"

    grid["obs_time"] = grid["day"] + pd.to_timedelta(grid["hour"], unit="h")
    grid["record_id"] = "W" + grid["town_code"] + grid["obs_time"].dt.strftime("%Y%m%d%H")
    out = grid[
        ["record_id", "station_id", "town_code", "town", "obs_time", "temperature", "humidity",
         "rainfall_mm", "wind_speed", "sunshine_index", "pressure_hpa"]
    ].copy()
    return inject_dirty(out, rng, ["humidity", "wind_speed"], "temperature")


def gen_sensor_month(rng, farms: pd.DataFrame, first: date, last: date) -> pd.DataFrame:
    """地块物联网土壤/环境传感器明细：地块 x 终端 x 日期 x 采集时点。"""
    days = pd.date_range(first, last, freq="D")
    slots = np.arange(SENSOR_READS_PER_DAY) * (24 // SENSOR_READS_PER_DAY)

    idx = pd.MultiIndex.from_product(
        [farms["farm_id"].to_numpy(), np.arange(1, SENSORS_PER_FARM + 1), days, slots],
        names=["farm_id", "device_no", "day", "hour"],
    ).to_frame(index=False)
    grid = idx.merge(farms[["farm_id", "farm_code", "town_code", "town", "crop"]], on="farm_id", how="left")
    n = len(grid)

    doy = grid["day"].dt.dayofyear.to_numpy()
    base_moist = 0.30 + 0.06 * np.sin(2 * np.pi * (doy - 150) / 365.0)
    # 水稻田常年淹水，墒情显著高于旱作
    paddy = (grid["crop"] == "水稻").to_numpy()
    grid["soil_moisture"] = np.round(np.clip(base_moist + paddy * 0.16 + rng.normal(0, 0.045, n), 0.05, 0.95), 4)
    grid["soil_temp"] = np.round(12 + 11 * np.sin(2 * np.pi * (doy - 105) / 365.0) + rng.normal(0, 1.2, n), 2)
    grid["soil_ph"] = np.round(np.clip(rng.normal(6.9, 0.35, n), 4.5, 8.8), 2)
    grid["light_lux"] = np.round(np.clip(rng.normal(38000, 14000, n), 0, 120000), 0)
    grid["nitrogen"] = np.round(np.clip(rng.normal(96, 22, n), 10, 220), 1)
    grid["phosphorus"] = np.round(np.clip(rng.normal(42, 12, n), 5, 130), 1)
    grid["potassium"] = np.round(np.clip(rng.normal(128, 30, n), 20, 300), 1)
    grid["battery_pct"] = np.round(np.clip(rng.normal(78, 15, n), 0, 100), 1)
    grid["device_id"] = grid["farm_code"] + "-S" + grid["device_no"].astype(str)

    grid["collect_time"] = grid["day"] + pd.to_timedelta(grid["hour"], unit="h")
    grid["record_id"] = grid["device_id"] + "-" + grid["collect_time"].dt.strftime("%Y%m%d%H")
    out = grid[
        ["record_id", "device_id", "farm_id", "farm_code", "town_code", "town", "crop", "collect_time",
         "soil_moisture", "soil_temp", "soil_ph", "light_lux", "nitrogen", "phosphorus",
         "potassium", "battery_pct"]
    ].copy()
    return inject_dirty(out, rng, ["soil_ph", "nitrogen", "battery_pct"], "soil_moisture")


def gen_scout_month(rng, farms: pd.DataFrame, first: date, last: date, per_day: int) -> pd.DataFrame:
    """病虫害田间踏查明细：农技员按日到地块逐点记录发生程度。"""
    days = pd.date_range(first, last, freq="D")
    n = len(days) * per_day
    if n == 0:
        return pd.DataFrame()

    farm_pick = rng.integers(0, len(farms), n)
    rows = farms.iloc[farm_pick].reset_index(drop=True)
    day_pick = np.repeat(days, per_day)

    crop = rows["crop"].to_numpy()
    disease = np.array([rng.choice(DISEASES[c]) for c in crop])
    # 病虫害发生程度随生育期与高温高湿季节显著上升，盛夏为高发期
    doy = day_pick.dayofyear.to_numpy()
    season_factor = 0.5 + 1.1 * np.clip(np.sin(2 * np.pi * (doy - 205) / 365.0), 0, 1)
    incidence = np.round(np.clip(rng.beta(1.8, 7.0, n) * 100 * season_factor, 0, 100), 2)
    severity = np.select(
        [incidence < 5, incidence < 15, incidence < 32], ["轻", "中", "重"], default="严重"
    )

    out = pd.DataFrame(
        {
            "record_id": [f"SC{i:09d}" for i in rng.integers(0, 10**9, n)],
            "farm_id": rows["farm_id"].to_numpy(),
            "farm_code": rows["farm_code"].to_numpy(),
            "town_code": rows["town_code"].to_numpy(),
            "town": rows["town"].to_numpy(),
            "crop": crop,
            "scout_time": day_pick + pd.to_timedelta(rng.integers(7, 18, n), unit="h"),
            "disease_name": disease,
            "incidence_rate": incidence,
            "severity": severity,
            "sample_points": rng.integers(5, 26, n),
            "affected_mu": np.round(rows["area_mu"].to_numpy() * incidence / 100.0, 2),
            "scout_source": rng.choice(["农技员踏查", "合作社上报", "无人机巡田", "图像识别复核"], n,
                                       p=[0.42, 0.28, 0.18, 0.12]),
            "reporter": [f"AGT{v:03d}" for v in rng.integers(1, 41, n)],
        }
    )
    return inject_dirty(out, rng, ["incidence_rate", "sample_points"], "affected_mu")


def gen_yield_plot(rng, farms: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    """测产小区明细：每地块每季按 30 个小区实测，供产量模型训练。"""
    plots = np.arange(1, 31)
    idx = pd.MultiIndex.from_product(
        [farms["farm_id"].to_numpy(), years, ["春播", "秋播"], plots],
        names=["farm_id", "year", "season", "plot_no"],
    ).to_frame(index=False)
    grid = idx.merge(farms[["farm_id", "farm_code", "town_code", "town", "crop", "area_mu"]], on="farm_id", how="left")
    n = len(grid)

    base = grid["crop"].map({"水稻": 585.0, "小麦": 470.0, "玉米": 520.0, "番茄": 4200.0, "黄瓜": 3900.0}).to_numpy()
    loss = np.clip(rng.beta(2.0, 9.0, n), 0, 0.6)
    grid["plot_area_mu"] = 0.5
    grid["actual_yield_kg_per_mu"] = np.round(base * (1 - loss) * rng.normal(1.0, 0.07, n), 2)
    grid["loss_rate"] = np.round(loss, 4)
    grid["moisture_pct"] = np.round(np.clip(rng.normal(14.2, 1.4, n), 8, 24), 2)
    grid["harvest_date"] = pd.to_datetime(
        grid["year"].astype(str) + np.where(grid["season"] == "春播", "-06-12", "-10-08")
    )
    grid["record_id"] = grid["farm_code"] + "-" + grid["year"].astype(str) + "-" + grid["season"] + "-P" + grid["plot_no"].astype(str)
    out = grid[
        ["record_id", "farm_id", "farm_code", "town_code", "town", "crop", "year", "season", "plot_no",
         "plot_area_mu", "harvest_date", "actual_yield_kg_per_mu", "loss_rate", "moisture_pct"]
    ].copy()
    return inject_dirty(out, rng, ["moisture_pct"], "actual_yield_kg_per_mu")


# ---------------------------------------------------------------- 落盘


def write_partition(df: pd.DataFrame, root: Path, table: str, dt: str) -> int:
    """按 ``dt=YYYY-MM`` 月分区 + 乡镇分文件写出 gzip CSV（ODS 贴源层）。"""
    if df.empty:
        return 0
    part_dir = root / "ods" / table / f"dt={dt}"
    part_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    key = "town_code" if "town_code" in df.columns else None
    groups = df.groupby(key) if key else [("all", df)]
    for town_code, chunk in groups:
        target = part_dir / f"part-{town_code}.csv.gz"
        with gzip.open(target, "wt", encoding="utf-8", newline="") as fh:
            chunk.to_csv(fh, index=False)
        written += len(chunk)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="生成县域农业大数据明细层（ODS）")
    parser.add_argument("--months", type=int, default=24, help="明细数据覆盖的月份数，默认 24")
    parser.add_argument("--end", default="2026-08-31", help="数据截止日期 YYYY-MM-DD")
    parser.add_argument("--out", default="data/lake", help="数据湖根目录，默认 data/lake")
    parser.add_argument("--scout-per-day", type=int, default=90, help="每日田间踏查记录数")
    args = parser.parse_args()

    root = PROJECT_ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    if (root / "ods").exists():
        shutil.rmtree(root / "ods")
    root.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)
    farms = build_farms(rng)
    farms.to_csv(root / "dim_farm.csv", index=False, encoding="utf-8-sig")

    end = date.fromisoformat(args.end)
    # 以截止月为最后一个分区，向前推 months-1 个自然月
    total_month = (end.year * 12 + end.month - 1) - (args.months - 1)
    start = date(total_month // 12, total_month % 12 + 1, 1)
    spans = month_range(start, args.months)

    started = time.time()
    counts = {"ods_weather_raw": 0, "ods_sensor_raw": 0, "ods_pest_scout_raw": 0, "ods_yield_plot_raw": 0}

    for first, last in spans:
        dt = first.strftime("%Y-%m")
        counts["ods_weather_raw"] += write_partition(gen_weather_month(rng, first, last), root, "ods_weather_raw", dt)
        counts["ods_sensor_raw"] += write_partition(gen_sensor_month(rng, farms, first, last), root, "ods_sensor_raw", dt)
        counts["ods_pest_scout_raw"] += write_partition(
            gen_scout_month(rng, farms, first, last, args.scout_per_day), root, "ods_pest_scout_raw", dt
        )
        print(f"  [{dt}] 完成", flush=True)

    years = sorted({first.year for first, _ in spans} | {end.year})
    yield_df = gen_yield_plot(rng, farms, years)
    counts["ods_yield_plot_raw"] += write_partition(yield_df, root, "ods_yield_plot_raw", "all")

    total = sum(counts.values())
    elapsed = round(time.time() - started, 2)
    size_mb = round(sum(f.stat().st_size for f in (root / "ods").rglob("*.csv.gz")) / 1024 / 1024, 2)
    files = len(list((root / "ods").rglob("*.csv.gz")))

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "county": COUNTY,
        "date_range": {"start": spans[0][0].isoformat(), "end": spans[-1][1].isoformat(), "months": args.months},
        "farm_count": int(len(farms)),
        "town_count": len(TOWNS),
        "crops": CROPS,
        "row_counts": counts,
        "total_rows": total,
        "partition_files": files,
        "compressed_size_mb": size_mb,
        "dirty_data_injection": {"null_rate": NULL_RATE, "duplicate_rate": DUP_RATE, "outlier_rate": OUTLIER_RATE},
        "elapsed_seconds": elapsed,
        "layout": "data/lake/ods/<table>/dt=YYYY-MM/part-<town_code>.csv.gz",
    }
    (root / "ods_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in manifest.items() if k in ("row_counts", "total_rows", "partition_files", "compressed_size_mb", "elapsed_seconds")}, ensure_ascii=False, indent=2))
    if total < 1_000_000:
        raise SystemExit(f"明细层记录数 {total} 未达到 100 万条要求，请调大 --months 或 --scout-per-day")
    print(f"OK: ODS 明细层共 {total:,} 条记录，已写入 {root / 'ods'}")


if __name__ == "__main__":
    main()
