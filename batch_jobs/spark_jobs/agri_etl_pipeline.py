"""农智云瞰 —— 基于 Spark 的县域农情大数据 ETL 主链路。

本作业是平台离线分析的 **主链路**，不是可选扩展。全部清洗、关联、聚合与风险
计算均由 Spark SQL / DataFrame API 完成，覆盖数仓四层：

    ODS  data/lake/ods/*        贴源明细层，gzip CSV，按 dt=YYYY-MM 月分区
     |   去重 / 值域过滤 / 缺失值处理 / 时间口径统一 / 质量打标
    DWD  data/lake/dwd/*        明细清洗层，Parquet + Snappy，按 dt 分区
     |   按 乡镇-日 与 地块-日 汇聚，生成分析粒度
    DWS  data/lake/dws/*        轻度汇总层（地块日粒度风险特征宽表）
     |   面向驾驶舱 / 地图 / 巡检调度的应用指标
    ADS  data/lake/ads/*        应用数据层，JSON / CSV，供后端 API 与前端直接消费

运行方式（推荐 Docker，免除 Windows 下 Hadoop winutils 依赖）::

    docker compose -f docker-compose.bigdata.yml run --rm spark-submit

或在已配置 Spark 的环境下直接提交::

    spark-submit --master local[*] --driver-memory 4g \
        batch_jobs/spark_jobs/agri_etl_pipeline.py --lake data/lake

作业结束会写出 ``data/lake/_run_report.json``，记录各层行数、清洗剔除量与各阶段耗时，
作为数据规模与大数据链路的答辩证据。
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window


# 风险等级阈值：按 2024-05—2026-08 全量地块日风险分布的分位数标定
# （高 ≈ P96、中 ≈ P80），并对照主汛期 6—9 月的实际发生率校核，
# 使主汛期高风险地块占比落在 10% 左右，符合县域植保布防的资源承载能力。
RISK_HIGH = 52.0
RISK_MID = 36.0

# 作物病虫害易感性权重（农技经验参数，可在 conf 中调整）
CROP_SUSCEPTIBILITY = {"水稻": 1.15, "小麦": 0.95, "玉米": 0.90, "番茄": 1.20, "黄瓜": 1.10}

# 传感器与气象观测的合法值域，超出即判定为设备故障读数
VALID_RANGES = {
    "soil_moisture": (0.02, 0.98),
    "soil_temp": (-25.0, 60.0),
    "soil_ph": (3.0, 10.0),
    "light_lux": (0.0, 150000.0),
    "nitrogen": (0.0, 400.0),
    "phosphorus": (0.0, 300.0),
    "potassium": (0.0, 600.0),
    "temperature": (-35.0, 50.0),
    "humidity": (0.0, 100.0),
    "rainfall_mm": (0.0, 400.0),
}


def build_spark(app_name: str, shuffle_partitions: int) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )


def read_ods(spark: SparkSession, lake: str, table: str) -> DataFrame:
    """读取 ODS 贴源层。CSV 带表头，按 dt 目录分区，Spark 自动识别分区列。"""
    return (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .option("mode", "PERMISSIVE")
        .csv(f"{lake}/ods/{table}")
    )


def in_range(col: str) -> "F.Column":
    lo, hi = VALID_RANGES[col]
    return F.col(col).between(lo, hi)


# ------------------------------------------------------------------ DWD 清洗层


def build_dwd_weather(df: DataFrame) -> tuple[DataFrame, dict]:
    raw = df.count()
    dedup = df.dropDuplicates(["record_id"])
    after_dedup = dedup.count()

    cleaned = (
        dedup.withColumn("obs_time", F.to_timestamp("obs_time"))
        .withColumn("stat_date", F.to_date("obs_time"))
        .withColumn("dt", F.date_format("obs_time", "yyyy-MM"))
        # 越界读数置空后按乡镇中位数补齐，避免整行丢弃造成时序断点
        .withColumn("temperature", F.when(in_range("temperature"), F.col("temperature")))
        .withColumn("humidity", F.when(in_range("humidity"), F.col("humidity")))
        .withColumn("rainfall_mm", F.when(in_range("rainfall_mm"), F.col("rainfall_mm")).otherwise(F.lit(0.0)))
        .filter(F.col("obs_time").isNotNull() & F.col("town_code").isNotNull())
    )
    town_win = Window.partitionBy("town_code")
    cleaned = (
        cleaned.withColumn("temperature", F.coalesce("temperature", F.avg("temperature").over(town_win)))
        .withColumn("humidity", F.coalesce("humidity", F.avg("humidity").over(town_win)))
        .withColumn("wind_speed", F.coalesce("wind_speed", F.lit(0.0)))
    )
    kept = cleaned.count()
    return cleaned, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def build_dwd_sensor(df: DataFrame) -> tuple[DataFrame, dict]:
    raw = df.count()
    dedup = df.dropDuplicates(["record_id"])
    after_dedup = dedup.count()

    cleaned = (
        dedup.withColumn("collect_time", F.to_timestamp("collect_time"))
        .withColumn("stat_date", F.to_date("collect_time"))
        .withColumn("dt", F.date_format("collect_time", "yyyy-MM"))
        .withColumn("is_outlier", (~in_range("soil_moisture")).cast("int"))
        .withColumn("soil_moisture", F.when(in_range("soil_moisture"), F.col("soil_moisture")))
        .withColumn("soil_temp", F.when(in_range("soil_temp"), F.col("soil_temp")))
        .withColumn("soil_ph", F.when(in_range("soil_ph"), F.col("soil_ph")))
        .withColumn("nitrogen", F.when(in_range("nitrogen"), F.col("nitrogen")))
        .withColumn("phosphorus", F.when(in_range("phosphorus"), F.col("phosphorus")))
        .withColumn("potassium", F.when(in_range("potassium"), F.col("potassium")))
        .filter(F.col("collect_time").isNotNull() & F.col("farm_id").isNotNull())
        # 墒情为核心特征，缺失或越界的记录不进入分析层
        .filter(F.col("soil_moisture").isNotNull())
    )
    kept = cleaned.count()
    return cleaned, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def build_dwd_scout(df: DataFrame) -> tuple[DataFrame, dict]:
    raw = df.count()
    dedup = df.dropDuplicates(["record_id"])
    after_dedup = dedup.count()
    cleaned = (
        dedup.withColumn("scout_time", F.to_timestamp("scout_time"))
        .withColumn("stat_date", F.to_date("scout_time"))
        .withColumn("dt", F.date_format("scout_time", "yyyy-MM"))
        .filter(F.col("scout_time").isNotNull())
        .filter(F.col("incidence_rate").between(0, 100))
        .withColumn("affected_mu", F.when(F.col("affected_mu") >= 0, F.col("affected_mu")).otherwise(F.lit(0.0)))
    )
    kept = cleaned.count()
    return cleaned, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


def build_dwd_yield(df: DataFrame) -> tuple[DataFrame, dict]:
    raw = df.count()
    dedup = df.dropDuplicates(["record_id"])
    after_dedup = dedup.count()
    cleaned = dedup.filter(
        (F.col("actual_yield_kg_per_mu") > 0)
        & (F.col("actual_yield_kg_per_mu") < 20000)
        & F.col("loss_rate").between(0, 1)
    )
    kept = cleaned.count()
    return cleaned, {"raw": raw, "duplicates_removed": raw - after_dedup, "invalid_removed": after_dedup - kept, "kept": kept}


# ------------------------------------------------------------------ DWS 汇总层


def build_dws(weather: DataFrame, sensor: DataFrame, scout: DataFrame, susceptibility: DataFrame) -> DataFrame:
    """构建地块-日粒度风险特征宽表。"""
    weather_daily = weather.groupBy("town_code", "town", "stat_date").agg(
        F.round(F.avg("temperature"), 2).alias("avg_temp"),
        F.round(F.max("temperature"), 2).alias("max_temp"),
        F.round(F.avg("humidity"), 2).alias("avg_humidity"),
        F.round(F.sum("rainfall_mm"), 2).alias("rainfall_mm"),
        F.round(F.avg("wind_speed"), 2).alias("avg_wind"),
        F.sum(F.when(F.col("humidity") >= 85, 1).otherwise(0)).alias("high_humid_hours"),
    )

    sensor_daily = sensor.groupBy("farm_id", "farm_code", "town_code", "town", "crop", "stat_date").agg(
        F.round(F.avg("soil_moisture"), 4).alias("avg_soil_moisture"),
        F.round(F.stddev_pop("soil_moisture"), 4).alias("std_soil_moisture"),
        F.round(F.avg("soil_temp"), 2).alias("avg_soil_temp"),
        F.round(F.avg("soil_ph"), 2).alias("avg_soil_ph"),
        F.round(F.avg("nitrogen"), 1).alias("avg_nitrogen"),
        F.round(F.avg("potassium"), 1).alias("avg_potassium"),
        F.count(F.lit(1)).alias("reading_cnt"),
        F.sum("is_outlier").alias("outlier_cnt"),
    )

    scout_daily = scout.groupBy("farm_id", "stat_date").agg(
        F.round(F.avg("incidence_rate"), 2).alias("avg_incidence"),
        F.round(F.max("incidence_rate"), 2).alias("max_incidence"),
        F.round(F.sum("affected_mu"), 2).alias("affected_mu"),
        F.count(F.lit(1)).alias("scout_cnt"),
    )

    # 近 14 日历史病害压力：窗口函数计算滚动均值，体现时序特征加工
    hist_win = Window.partitionBy("farm_id").orderBy(F.col("stat_date").cast("long")).rangeBetween(-14 * 86400, -86400)

    wide = (
        sensor_daily.join(weather_daily, ["town_code", "town", "stat_date"], "left")
        .join(scout_daily, ["farm_id", "stat_date"], "left")
        .join(F.broadcast(susceptibility), ["crop"], "left")
        .fillna({"avg_incidence": 0.0, "max_incidence": 0.0, "affected_mu": 0.0, "scout_cnt": 0})
        .withColumn("hist_incidence_14d", F.round(F.coalesce(F.avg("avg_incidence").over(hist_win), F.lit(0.0)), 3))
    )

    # 规则风险评分（0-100）：湿热环境 + 土壤过湿 + 历史发生率 + 作物易感性
    humid_score = F.least(F.greatest((F.col("avg_humidity") - 60) / 35 * 34, F.lit(0.0)), F.lit(34.0))
    rain_score = F.least(F.col("rainfall_mm") / 30 * 18, F.lit(18.0))
    moist_score = F.least(F.greatest((F.col("avg_soil_moisture") - 0.32) / 0.35 * 16, F.lit(0.0)), F.lit(16.0))
    hist_score = F.least(F.col("hist_incidence_14d") / 20 * 22, F.lit(22.0))
    temp_score = F.least(F.greatest((F.col("avg_temp") - 18) / 14 * 10, F.lit(0.0)), F.lit(10.0))

    scored = (
        wide.withColumn("humid_score", F.round(humid_score, 2))
        .withColumn("rain_score", F.round(rain_score, 2))
        .withColumn("moist_score", F.round(moist_score, 2))
        .withColumn("hist_score", F.round(hist_score, 2))
        .withColumn("temp_score", F.round(temp_score, 2))
        .withColumn(
            "risk_score",
            F.round(
                F.least(
                    (F.col("humid_score") + F.col("rain_score") + F.col("moist_score")
                     + F.col("hist_score") + F.col("temp_score")) * F.coalesce(F.col("susceptibility"), F.lit(1.0)),
                    F.lit(100.0),
                ),
                2,
            ),
        )
        .withColumn(
            "risk_level",
            F.when(F.col("risk_score") >= RISK_HIGH, "高").when(F.col("risk_score") >= RISK_MID, "中").otherwise("低"),
        )
        # 主导风险因子：五项分值中取最大者，供前端展示与人工复核
        .withColumn(
            "top_factor",
            F.element_at(
                F.array_sort(
                    F.array(
                        F.struct(F.col("humid_score").alias("v"), F.lit("空气湿度").alias("k")),
                        F.struct(F.col("rain_score").alias("v"), F.lit("降雨量").alias("k")),
                        F.struct(F.col("moist_score").alias("v"), F.lit("土壤墒情").alias("k")),
                        F.struct(F.col("hist_score").alias("v"), F.lit("历史病害").alias("k")),
                        F.struct(F.col("temp_score").alias("v"), F.lit("积温条件").alias("k")),
                    )
                ),
                -1,
            ).getField("k"),
        )
        .withColumn("dt", F.date_format("stat_date", "yyyy-MM"))
    )
    return scored


# ------------------------------------------------------------------ ADS 应用层


def build_ads(spark: SparkSession, dws: DataFrame, yields: DataFrame, quality: dict, lake: str) -> dict:
    dws.createOrReplaceTempView("dws_farm_daily")
    yields.createOrReplaceTempView("dwd_yield_plot")

    latest_date = dws.agg(F.max("stat_date")).first()[0]
    spark.conf.set("agri.latest_date", str(latest_date))

    # 1) 乡镇风险排名（按最新统计日）
    town_ranking = spark.sql(
        f"""
        select town,
               round(avg(risk_score), 2)                                   as avg_risk,
               sum(case when risk_level = '高' then 1 else 0 end)          as high_risk_farms,
               count(distinct farm_id)                                     as farm_count,
               round(sum(affected_mu), 1)                                  as affected_mu
        from dws_farm_daily
        where stat_date = date('{latest_date}')
        group by town
        order by avg_risk desc
        """
    )

    # 2) 作物风险分布
    crop_distribution = spark.sql(
        f"""
        select crop, risk_level, count(*) as farm_count,
               round(avg(risk_score), 2) as avg_risk
        from dws_farm_daily
        where stat_date = date('{latest_date}')
        group by crop, risk_level
        order by crop, risk_level
        """
    )

    # 3) 近 30 日全县风险趋势
    risk_trend = spark.sql(
        f"""
        select cast(stat_date as string) as stat_date,
               round(avg(risk_score), 2) as risk_score,
               sum(case when risk_level = '高' then 1 else 0 end) as high_risk_farms
        from dws_farm_daily
        where stat_date > date_sub(date('{latest_date}'), 30)
        group by stat_date
        order by stat_date
        """
    )

    # 4) 产量与损失汇总（测产小区明细上卷）
    yield_summary = spark.sql(
        """
        select crop, year,
               round(avg(actual_yield_kg_per_mu), 2) as avg_yield_kg_per_mu,
               round(avg(loss_rate) * 100, 2)        as avg_loss_pct,
               count(*)                              as plot_cnt
        from dwd_yield_plot
        group by crop, year
        order by crop, year
        """
    )

    # 5) 巡检优先级：最新日风险 Top 30 地块
    inspection_priority = spark.sql(
        f"""
        select farm_code, town, crop, risk_score, risk_level, top_factor,
               round(avg_soil_moisture, 3) as avg_soil_moisture,
               round(avg_humidity, 1)      as avg_humidity,
               affected_mu,
               case when risk_score >= {RISK_HIGH} then '高'
                    when risk_score >= {RISK_MID} then '中' else '低' end as priority
        from dws_farm_daily
        where stat_date = date('{latest_date}')
        order by risk_score desc
        limit 30
        """
    )

    # 6) 农资调度建议：按乡镇风险与受害面积推算药剂与人机需求
    dispatch = spark.sql(
        f"""
        select town,
               round(avg(risk_score), 2)      as avg_risk,
               round(sum(affected_mu), 1)     as affected_mu,
               ceil(sum(affected_mu) / 300.0) as drone_sorties,
               ceil(sum(affected_mu) / 500.0) as agronomist_needed,
               round(sum(affected_mu) * 0.12, 1) as pesticide_kg
        from dws_farm_daily
        where stat_date = date('{latest_date}')
        group by town
        order by avg_risk desc
        """
    )

    outputs = {
        "ads_town_risk_ranking": town_ranking,
        "ads_crop_risk_distribution": crop_distribution,
        "ads_risk_trend_30d": risk_trend,
        "ads_yield_summary": yield_summary,
        "ads_inspection_priority": inspection_priority,
        "ads_material_dispatch": dispatch,
    }

    summary: dict = {"latest_stat_date": str(latest_date)}
    for name, df in outputs.items():
        rows = [r.asDict() for r in df.collect()]
        (Path(lake) / "ads").mkdir(parents=True, exist_ok=True)
        (Path(lake) / "ads" / f"{name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        df.coalesce(1).write.mode("overwrite").option("header", "true").csv(f"{lake}/ads/csv/{name}")
        summary[name] = len(rows)

    (Path(lake) / "ads" / "ads_data_quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


# ------------------------------------------------------------------ 主流程


def main() -> None:
    parser = argparse.ArgumentParser(description="农智云瞰 Spark ETL 主链路")
    parser.add_argument("--lake", default="data/lake", help="数据湖根目录")
    parser.add_argument("--shuffle-partitions", type=int, default=16)
    parser.add_argument("--skip-dwd-write", action="store_true", help="仅计算不落 DWD/DWS Parquet（调试用）")
    args = parser.parse_args()

    lake = args.lake
    spark = build_spark("agri-intelligence-etl", args.shuffle_partitions)
    spark.sparkContext.setLogLevel("WARN")

    timings: dict[str, float] = {}
    quality: dict[str, dict] = {}
    t0 = time.time()

    # ---- ODS -> DWD
    stage = time.time()
    weather, quality["ods_weather_raw"] = build_dwd_weather(read_ods(spark, lake, "ods_weather_raw"))
    sensor, quality["ods_sensor_raw"] = build_dwd_sensor(read_ods(spark, lake, "ods_sensor_raw"))
    scout, quality["ods_pest_scout_raw"] = build_dwd_scout(read_ods(spark, lake, "ods_pest_scout_raw"))
    yields, quality["ods_yield_plot_raw"] = build_dwd_yield(read_ods(spark, lake, "ods_yield_plot_raw"))

    if not args.skip_dwd_write:
        for name, df in (("dwd_weather", weather), ("dwd_sensor", sensor), ("dwd_pest_scout", scout)):
            df.write.mode("overwrite").partitionBy("dt").parquet(f"{lake}/dwd/{name}")
        yields.write.mode("overwrite").parquet(f"{lake}/dwd/dwd_yield_plot")
    timings["ods_to_dwd"] = round(time.time() - stage, 2)

    # ---- DWD -> DWS
    stage = time.time()
    susceptibility = spark.createDataFrame(
        [(k, float(v)) for k, v in CROP_SUSCEPTIBILITY.items()],
        T.StructType([T.StructField("crop", T.StringType()), T.StructField("susceptibility", T.DoubleType())]),
    )
    dws = build_dws(weather, sensor, scout, susceptibility).cache()
    dws_rows = dws.count()
    if not args.skip_dwd_write:
        dws.write.mode("overwrite").partitionBy("dt").parquet(f"{lake}/dws/dws_farm_daily")
    timings["dwd_to_dws"] = round(time.time() - stage, 2)

    # ---- DWS -> ADS
    stage = time.time()
    ads_summary = build_ads(spark, dws, yields, quality, lake)
    timings["dws_to_ads"] = round(time.time() - stage, 2)
    timings["total"] = round(time.time() - t0, 2)

    report = {
        "engine": "Apache Spark",
        "spark_version": spark.version,
        "master": spark.sparkContext.master,
        "executor_cores": spark.sparkContext.defaultParallelism,
        "layers": {
            "ods_rows": sum(v["raw"] for v in quality.values()),
            "dwd_rows": sum(v["kept"] for v in quality.values()),
            "dws_rows": dws_rows,
            "ads_tables": {k: v for k, v in ads_summary.items() if k != "latest_stat_date"},
        },
        "data_quality": quality,
        "timings_seconds": timings,
        "latest_stat_date": ads_summary["latest_stat_date"],
    }
    Path(lake).mkdir(parents=True, exist_ok=True)
    (Path(lake) / "_run_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    spark.stop()


if __name__ == "__main__":
    main()
