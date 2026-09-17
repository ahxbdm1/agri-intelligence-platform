# 大数据批处理模块

本目录承载平台的**离线分析主链路**。赛道明确要求"必须采用大数据存储与分析相关技术来构建系统，不能因为参赛要求的数据规模较小而使用非大数据技术"，因此这里不是"可迁移到 Spark 的 pandas 脚本"，而是以 Apache Spark 为唯一明细加工路径的四层数仓。

```
data/lake/ods/     贴源层  gzip CSV，dt=YYYY-MM 月分区 + 乡镇分文件   1,591,545 条
   │   Spark：去重 / 值域过滤 / 缺失分级处理 / 时间口径统一 / 质量打标
data/lake/dwd/     清洗层  Parquet + Snappy，dt 分区                 1,583,486 条
   │   Spark：乡镇-日、地块-日两级汇聚 + 14 日滚动窗口特征
data/lake/dws/     汇总层  地块-日风险特征宽表                        58,400 行
   │   Spark SQL：风险评分、分级、排名、归因、资源测算
data/lake/ads/     应用层  JSON + CSV，供后端 API 与前端直读          6 张结果表
```

## 目录内容

| 文件 | 作用 |
| --- | --- |
| `spark_jobs/agri_etl_pipeline.py` | **ETL 主链路**。四层加工全部由 Spark SQL / DataFrame 完成，结束时写出 `data/lake/_run_report.json` |
| `spark_jobs/hive_ddl.sql` | ODS / DWD / DWS / ADS 四层 Hive 外部表建表脚本，可在 Metastore 环境注册后用 SQL 访问 |
| `pandas_jobs/ads_reference_job.py` | 同口径的 pandas 参考实现，作为回归基线；与主链路读同一份 ODS、用同一套清洗规则与评分公式 |
| `pandas_jobs/risk_aggregation_job.py` | 早期版本的业务库轻量聚合，保留用于业务库侧小规模统计，**不参与明细层计算** |

## 运行

前置：先生成明细层。

```bash
python scripts/generate_bigdata_layer.py
```

运行 Spark 主链路（推荐 Docker，免除 Windows 下 Hadoop winutils 依赖）：

```bash
# 单容器本地模式，一条命令跑完整链路
docker compose -f docker-compose.bigdata.yml run --rm spark-local

# 或起 Standalone 集群后提交，可在 http://localhost:8080 观察 Spark UI
docker compose -f docker-compose.bigdata.yml up -d spark-master spark-worker
docker compose -f docker-compose.bigdata.yml run --rm spark-submit
```

已有 Spark 环境时可直接提交：

```bash
spark-submit --master local[*] --driver-memory 4g \
  batch_jobs/spark_jobs/agri_etl_pipeline.py --lake data/lake
```

## 口径一致性校验

```bash
python batch_jobs/pandas_jobs/ads_reference_job.py
python scripts/compare_ads_outputs.py
```

比对脚本逐表逐字段校验 Spark 产出与参考产出，数值容差 0.02，字符串严格相等。任何一侧改动口径都会立即暴露并以退出码 1 失败。

## ADS 结果表

| 表 | 内容 | 消费方 |
| --- | --- | --- |
| `ads_town_risk_ranking` | 乡镇平均风险、高风险地块数、受害面积 | 驾驶舱乡镇排名 |
| `ads_crop_risk_distribution` | 作物 × 风险等级的地块分布 | 作物结构风险分析 |
| `ads_risk_trend_30d` | 近 30 日全县风险走势 | 驾驶舱趋势图 |
| `ads_yield_summary` | 作物 × 年份平均亩产与损失率 | 产量预测基线 |
| `ads_inspection_priority` | 风险 Top 30 地块及主导因子 | 巡检排序与派单 |
| `ads_material_dispatch` | 各乡镇无人机架次、农技员人数、药剂用量 | 日调度工作流 |

另有 `ads_data_quality.json` 记录逐表的原始量、去重量、无效量与保留量，是数据治理的举证材料。

## 风险评分口径

评分公式、因子权重、作物易感性系数与分级阈值的完整说明见 `docs/详细设计说明书.md` 第〇章。阈值 `RISK_HIGH = 52`、`RISK_MID = 36` 集中定义为模块级常量，Spark 与参考实现共享，修改即整链生效。
