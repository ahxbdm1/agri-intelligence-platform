-- 农智云瞰县域农情数仓 Hive 建表脚本（ODS / DWD / DWS / ADS 四层）
--
-- 用途：在具备 Hive Metastore 的环境中，把数据湖目录注册为外部表，
-- 使 Spark SQL、Hive CLI 与 BI 工具可以用统一的 SQL 口径访问同一份数据。
-- 表全部建为 EXTERNAL，删除表不会删数据文件，便于反复演示与复现。
--
-- 执行：
--   hive -f batch_jobs/spark_jobs/hive_ddl.sql
--   或在 spark-sql 中： spark-sql --database agri_dw -f batch_jobs/spark_jobs/hive_ddl.sql
--
-- 注意：${LAKE} 请替换为数据湖根路径，例如 hdfs:///user/agri/lake 或 file:///opt/agri/data/lake

CREATE DATABASE IF NOT EXISTS agri_dw
  COMMENT '农智云瞰县域农情数据仓库'
  LOCATION '${LAKE}/warehouse';

USE agri_dw;

-- ============================================================ ODS 贴源层
-- 直接映射采集落地的 gzip CSV，按 dt=YYYY-MM 月分区，不做任何加工

CREATE EXTERNAL TABLE IF NOT EXISTS ods_sensor_raw (
    record_id      STRING  COMMENT '采集记录唯一键',
    device_id      STRING  COMMENT '传感器终端编号',
    farm_id        BIGINT  COMMENT '地块ID',
    farm_code      STRING  COMMENT '地块编码',
    town_code      STRING  COMMENT '乡镇编码',
    town           STRING  COMMENT '乡镇名称',
    crop           STRING  COMMENT '当季作物',
    collect_time   STRING  COMMENT '采集时间',
    soil_moisture  DOUBLE  COMMENT '土壤体积含水量',
    soil_temp      DOUBLE  COMMENT '土壤温度(℃)',
    soil_ph        DOUBLE  COMMENT '土壤pH',
    light_lux      DOUBLE  COMMENT '光照强度(lux)',
    nitrogen       DOUBLE  COMMENT '速效氮(mg/kg)',
    phosphorus     DOUBLE  COMMENT '速效磷(mg/kg)',
    potassium      DOUBLE  COMMENT '速效钾(mg/kg)',
    battery_pct    DOUBLE  COMMENT '终端电量百分比'
)
COMMENT '物联网土壤环境传感器原始明细'
PARTITIONED BY (dt STRING COMMENT '统计月份 yyyy-MM')
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${LAKE}/ods/ods_sensor_raw'
TBLPROPERTIES ('skip.header.line.count' = '1');

CREATE EXTERNAL TABLE IF NOT EXISTS ods_weather_raw (
    record_id       STRING,
    station_id      STRING  COMMENT '自动气象站编号',
    town_code       STRING,
    town            STRING,
    obs_time        STRING  COMMENT '观测时间(逐小时)',
    temperature     DOUBLE  COMMENT '气温(℃)',
    humidity        DOUBLE  COMMENT '相对湿度(%)',
    rainfall_mm     DOUBLE  COMMENT '小时降水量(mm)',
    wind_speed      DOUBLE  COMMENT '风速(m/s)',
    sunshine_index  DOUBLE  COMMENT '日照指数',
    pressure_hpa    DOUBLE  COMMENT '气压(hPa)'
)
COMMENT '乡镇自动气象站逐小时观测原始明细'
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${LAKE}/ods/ods_weather_raw'
TBLPROPERTIES ('skip.header.line.count' = '1');

CREATE EXTERNAL TABLE IF NOT EXISTS ods_pest_scout_raw (
    record_id       STRING,
    farm_id         BIGINT,
    farm_code       STRING,
    town_code       STRING,
    town            STRING,
    crop            STRING,
    scout_time      STRING  COMMENT '踏查时间',
    disease_name    STRING  COMMENT '病虫害名称',
    incidence_rate  DOUBLE  COMMENT '病株率(%)',
    severity        STRING  COMMENT '发生程度',
    sample_points   INT     COMMENT '取样点数',
    affected_mu     DOUBLE  COMMENT '受害面积(亩)',
    scout_source    STRING  COMMENT '数据来源',
    reporter        STRING  COMMENT '填报人编号'
)
COMMENT '病虫害田间踏查原始明细'
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${LAKE}/ods/ods_pest_scout_raw'
TBLPROPERTIES ('skip.header.line.count' = '1');

CREATE EXTERNAL TABLE IF NOT EXISTS ods_yield_plot_raw (
    record_id               STRING,
    farm_id                 BIGINT,
    farm_code               STRING,
    town_code               STRING,
    town                    STRING,
    crop                    STRING,
    year                    INT,
    season                  STRING,
    plot_no                 INT     COMMENT '测产小区编号',
    plot_area_mu            DOUBLE,
    harvest_date            STRING,
    actual_yield_kg_per_mu  DOUBLE  COMMENT '实测亩产(kg/亩)',
    loss_rate               DOUBLE  COMMENT '损失率',
    moisture_pct            DOUBLE  COMMENT '籽粒含水率(%)'
)
COMMENT '测产小区实测原始明细'
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${LAKE}/ods/ods_yield_plot_raw'
TBLPROPERTIES ('skip.header.line.count' = '1');

-- ============================================================ DWD 明细清洗层
-- 由 Spark ETL 写出 Parquet，已完成去重、值域过滤、缺失值处理与时间口径统一

CREATE EXTERNAL TABLE IF NOT EXISTS dwd_sensor (
    record_id      STRING,
    device_id      STRING,
    farm_id        BIGINT,
    farm_code      STRING,
    town_code      STRING,
    town           STRING,
    crop           STRING,
    collect_time   TIMESTAMP,
    stat_date      DATE,
    soil_moisture  DOUBLE,
    soil_temp      DOUBLE,
    soil_ph        DOUBLE,
    light_lux      DOUBLE,
    nitrogen       DOUBLE,
    phosphorus     DOUBLE,
    potassium      DOUBLE,
    battery_pct    DOUBLE,
    is_outlier     INT     COMMENT '1=原始读数越界，已在清洗阶段打标'
)
COMMENT '传感器明细清洗层'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '${LAKE}/dwd/dwd_sensor';

CREATE EXTERNAL TABLE IF NOT EXISTS dwd_weather (
    record_id       STRING,
    station_id      STRING,
    town_code       STRING,
    town            STRING,
    obs_time        TIMESTAMP,
    stat_date       DATE,
    temperature     DOUBLE,
    humidity        DOUBLE,
    rainfall_mm     DOUBLE,
    wind_speed      DOUBLE,
    sunshine_index  DOUBLE,
    pressure_hpa    DOUBLE
)
COMMENT '气象明细清洗层'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '${LAKE}/dwd/dwd_weather';

CREATE EXTERNAL TABLE IF NOT EXISTS dwd_pest_scout (
    record_id       STRING,
    farm_id         BIGINT,
    farm_code       STRING,
    town_code       STRING,
    town            STRING,
    crop            STRING,
    scout_time      TIMESTAMP,
    stat_date       DATE,
    disease_name    STRING,
    incidence_rate  DOUBLE,
    severity        STRING,
    sample_points   INT,
    affected_mu     DOUBLE,
    scout_source    STRING,
    reporter        STRING
)
COMMENT '病虫害踏查明细清洗层'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '${LAKE}/dwd/dwd_pest_scout';

-- ============================================================ DWS 汇总层
-- 地块-日粒度风险特征宽表，是风险评分、地图着色与巡检排序的唯一事实来源

CREATE EXTERNAL TABLE IF NOT EXISTS dws_farm_daily (
    farm_id             BIGINT,
    farm_code           STRING,
    town_code           STRING,
    town                STRING,
    crop                STRING,
    stat_date           DATE,
    avg_soil_moisture   DOUBLE  COMMENT '日均土壤墒情',
    std_soil_moisture   DOUBLE  COMMENT '墒情日内标准差',
    avg_soil_temp       DOUBLE,
    avg_soil_ph         DOUBLE,
    avg_nitrogen        DOUBLE,
    avg_potassium       DOUBLE,
    reading_cnt         BIGINT  COMMENT '当日有效采集条数',
    outlier_cnt         BIGINT  COMMENT '当日异常读数条数',
    avg_temp            DOUBLE,
    max_temp            DOUBLE,
    avg_humidity        DOUBLE,
    rainfall_mm         DOUBLE  COMMENT '日累计降水',
    avg_wind            DOUBLE,
    high_humid_hours    BIGINT  COMMENT '当日相对湿度≥85%的小时数',
    avg_incidence       DOUBLE  COMMENT '当日踏查平均病株率',
    max_incidence       DOUBLE,
    affected_mu         DOUBLE,
    scout_cnt           BIGINT,
    susceptibility      DOUBLE  COMMENT '作物易感性权重',
    hist_incidence_14d  DOUBLE  COMMENT '近14日历史病害压力(滚动均值)',
    humid_score         DOUBLE,
    rain_score          DOUBLE,
    moist_score         DOUBLE,
    hist_score          DOUBLE,
    temp_score          DOUBLE,
    risk_score          DOUBLE  COMMENT '综合风险评分 0-100',
    risk_level          STRING  COMMENT '高/中/低，阈值 52/36',
    top_factor          STRING  COMMENT '主导风险因子'
)
COMMENT '地块-日粒度农情风险特征宽表'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '${LAKE}/dws/dws_farm_daily';

-- ============================================================ ADS 应用层
-- 由 Spark 作业直接落 JSON/CSV 供 API 读取；如需 SQL 访问可建以下外部表

CREATE EXTERNAL TABLE IF NOT EXISTS ads_town_risk_ranking (
    town             STRING,
    avg_risk         DOUBLE,
    high_risk_farms  BIGINT,
    farm_count       BIGINT,
    affected_mu      DOUBLE
)
COMMENT '乡镇风险排名（最新统计日）'
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${LAKE}/ads/csv/ads_town_risk_ranking'
TBLPROPERTIES ('skip.header.line.count' = '1');

CREATE EXTERNAL TABLE IF NOT EXISTS ads_material_dispatch (
    town               STRING,
    avg_risk           DOUBLE,
    affected_mu        DOUBLE,
    drone_sorties      BIGINT,
    agronomist_needed  BIGINT,
    pesticide_kg       DOUBLE
)
COMMENT '农资与人机调度建议'
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${LAKE}/ads/csv/ads_material_dispatch'
TBLPROPERTIES ('skip.header.line.count' = '1');

-- 新增分区后需刷新元数据
MSCK REPAIR TABLE ods_sensor_raw;
MSCK REPAIR TABLE ods_weather_raw;
MSCK REPAIR TABLE ods_pest_scout_raw;
MSCK REPAIR TABLE ods_yield_plot_raw;
MSCK REPAIR TABLE dwd_sensor;
MSCK REPAIR TABLE dwd_weather;
MSCK REPAIR TABLE dwd_pest_scout;
MSCK REPAIR TABLE dws_farm_daily;
