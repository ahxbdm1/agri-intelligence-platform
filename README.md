# 农智云瞰：面向县域农业的农情大数据分析与病虫害风险挖掘平台

> 山东省大学生软件设计大赛 · **大数据与人工智能行业应用开发**赛道

## 项目简介

“农智云瞰”面向县域农业主管部门、农技站、合作社和种植大户，构建从多源农情数据采集、清洗、建模、预测、预警、巡检到报告生成的完整业务闭环。系统围绕病虫害防控、产量风险管理和农业资源调度三个核心场景，提供农情驾驶舱、县域地图风险监测、病虫害图像识别、产量与风险预测、预警中心、巡检任务管理、RAG 农技助手、数据管理和日报生成能力。

## 系统架构

- 前端：Next.js + TypeScript + Tailwind CSS + Recharts + Leaflet + GSAP，深色大屏驾驶舱风格。
- 后端：FastAPI + SQLAlchemy，默认 SQLite fallback，Docker Compose 可切换 PostgreSQL。
- AI 模型：病虫害识别接口、RandomForest 风险评分、RandomForest 产量预测、IsolationForest 异常检测、RAGFlow 远程知识库与 TF-IDF 本地降级。
- 数据模块：`scripts/generate_demo_data.py` 生成固定种子演示数据，`batch_jobs/pandas_jobs/risk_aggregation_job.py` 生成离线统计结果。
- 部署：Docker Compose 一键启动 PostgreSQL、FastAPI、Next.js。

## 功能模块

1. 登录页：演示账号、角色入口、JWT 结构化认证。
2. 农情驾驶舱：KPI、风险趋势、作物结构、乡镇排名、最新预警。
3. 地图风险监测：县域地块 polygon、风险颜色、点击地块画像、筛选。
4. 病虫害识别：图片上传、识别结果、置信度、复核建议、模拟 Grad-CAM 区域。
5. 产量与风险预测：地块选择、风险评分、未来 7 天产量曲线、模型误差和因子贡献。
6. 预警中心：状态切换、一键生成巡检任务。
7. 巡检任务：任务优先级、负责人、截止时间、处理状态。
8. AI 农技助手：优先检索 RAGFlow 农业知识库，结合当前高风险地块和天气上下文回答；远程异常时自动切换本地 Markdown 知识库。
9. 数据管理：农田、天气、传感器、病虫害、产量数据统计，CSV 导入预览。
10. 报告生成：县域农情风险日报 Markdown/HTML 输出。
11. 农情调度工作流：按风险评分和天气因子编排高风险地块、去重生成巡检任务，并输出农资调度建议。

## 快速启动

Windows PowerShell 推荐使用 Python 3.11 隔离环境，避免本机已有科学计算库互相污染：

```powershell
git clone https://github.com/ahxbdm1/agri-intelligence-platform.git
cd agri-intelligence-platform
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
.\.venv\Scripts\python.exe scripts/generate_demo_data.py
.\.venv\Scripts\python.exe scripts/train_models.py
```

启动后端：

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

启动前端：

```powershell
cd frontend
npm run dev
```

访问地址：

- 前端系统：http://localhost:3000
- 后端 API：http://localhost:8000
- Swagger/OpenAPI：http://localhost:8000/docs

## Docker 启动

```bash
cp .env.example .env
docker compose up --build
```

Docker 环境默认使用 PostgreSQL；本地开发默认使用 SQLite fallback。

Docker Compose 默认会在 PostgreSQL 为空时自动生成演示数据，检测到已有用户后会跳过，不会覆盖已有业务数据。生产环境请设置 `SEED_DEMO_DATA_ON_STARTUP=false`。

## RAGFlow 接入

AI 农技助手支持“RAGFlow 远程优先、本地 TF-IDF 降级”。复制 `.env.example` 为 `.env` 后配置以下变量：

```env
RAGFLOW_ENABLED=true
RAGFLOW_BASE_URL=http://your-ragflow-host
RAGFLOW_API_KEY=your-api-key
RAGFLOW_DATASET_IDS=your-dataset-id
RAGFLOW_CHAT_ID=your-chat-id
```

`GET /api/assistant/status` 返回远程知识库状态；`POST /api/assistant/chat` 的 `mode` 字段明确标识 `ragflow` 或 `local`，避免将本地降级误判为远程调用成功。真实密钥只允许写入已被 `.gitignore` 排除的 `.env`。

远程 RAGFlow 默认 8 秒超时；超时后自动返回本地知识库答案，并在 60 秒内临时熔断远程重试，保证现场演示不会因为远程服务无响应而卡住。

驾驶舱的“执行今日调度”按钮调用 `POST /api/workflows/daily-dispatch`，请求体支持 `max_tasks` 和 `dry_run`，返回优先队列、新建/复用任务数量、农资计划和下一步处置动作。

## 演示账号

| 角色 | 账号 | 密码 | 适用场景 |
| --- | --- | --- | --- |
| 县域管理员 | admin | admin123 | 全县驾驶舱、预警调度、报告生成 |
| 农技专家 | expert | expert123 | 病虫害识别、模型解释、巡检复核 |
| 合作社用户 | coop | coop123 | 地块查看、任务处理、农情反馈 |

## 数据与分析链路

项目的数据分两层，职责严格分离：**明细数据只在数据湖与 Spark 链路中流动，在线业务库只消费分析产出**。

### 1. 生成大数据明细层（ODS）

```powershell
.\.venv\Scripts\python.exe scripts/generate_bigdata_layer.py
```

固定随机种子，双核环境实测约 35 秒，生成 **1,591,545 条**明细记录，按 `dt=YYYY-MM` 月分区 + 乡镇分文件落为 438 个 gzip CSV（合计 39.0 MB）：

| 明细表 | 粒度 | 记录数 |
| --- | --- | --- |
| `ods_sensor_raw` | 地块 × 2 终端 × 730 天 × 每日 12 次 | 1,405,790 |
| `ods_weather_raw` | 乡镇 × 730 天 × 逐小时 | 105,422 |
| `ods_pest_scout_raw` | 每日约 90 条田间踏查 | 65,890 |
| `ods_yield_plot_raw` | 地块 × 年 × 两季 × 30 小区 | 14,443 |

脚本内置总量断言，不足 100 万条会直接以非零退出码失败。

### 2. 运行 Spark ETL 主链路

```powershell
docker compose -f docker-compose.bigdata.yml run --rm spark-local
```

四层加工 ODS → DWD → DWS → ADS：清洗后保留 1,583,486 条（有效率 99.49%），DWS 地块-日风险特征宽表 58,400 行，ADS 产出 6 张应用结果表。运行报告写入 `data/lake/_run_report.json`。另提供 `batch_jobs/spark_jobs/hive_ddl.sql` 用于在 Hive Metastore 中注册四层外部表。

### 3. 校验分析口径

```powershell
.\.venv\Scripts\python.exe batch_jobs/pandas_jobs/ads_reference_job.py
.\.venv\Scripts\python.exe scripts/compare_ads_outputs.py
```

参考实现与 Spark 主链路读同一份 ODS、用同一套清洗规则与评分公式，比对脚本逐表逐字段校验。

### 4. 初始化在线业务库

```powershell
.\.venv\Scripts\python.exe scripts/generate_demo_data.py
```

生成 6 个乡镇、80 个地块、5 类作物的业务数据与预警、巡检记录，规模保持在页面可直接查询的量级。示范县域为山东省济宁市鱼台县，乡镇名称与经纬度取自真实行政区划。

## 模型训练

```powershell
.\.venv\Scripts\python.exe scripts/train_models.py
.\.venv\Scripts\python.exe backend/ml/train/train_disease_model.py
```

若本机有 NVIDIA GPU，可按 [安装部署说明](docs/安装部署说明.md) 安装 CUDA 版 PyTorch 和 Ultralytics，并运行 `\.venv\Scripts\python.exe backend/ml/train/train_yolo_plantdoc_model.py`。该脚本读取公开 PlantDoc 真实图像与 XML 检测框，转换为 YOLO 格式后训练 29 类病害检测模型；当前权重已保存到 `data/generated/models/plantdoc_yolo_best.pt`。

训练脚本会保存风险评分、产量预测、异常检测和病虫害识别模型到 `data/generated/models/`，并写入模型评估指标。RandomForest 分类模型仍使用可复现的合成叶片样本；当前默认识别接口使用 PlantDoc YOLO 权重。PlantDoc 指标只代表公开验证集表现，不代表山东本地田间泛化能力，上线前仍需补充本地数据和农技专家复核。

## 截图占位说明

建议在演示前截取以下页面作为申报材料：登录页、农情驾驶舱、地图风险监测、病虫害识别、预测模型、AI 助手、报告生成。

## 竞赛亮点

- **数仓分层真正落地**：Spark 是唯一的明细加工路径，明细不进 ORM、不入业务库，业务库只消费 ADS 产出。
- **数据治理可度量**：按固定比例注入缺失、重复与越界读数，逐表统计剔除量，有效率 99.49% 可现场核对。
- **阈值按分布标定**：风险分级阈值来自全量 58,400 条记录的分位数统计（P96 / P80）并经主汛期校核，可解释、可复标定。
- **风险归因到因子**：输出主导风险因子而非只给分数，把结论转化为农技员能执行的动作。
- **双实现口径互校**：Spark 主链路与 pandas 参考实现逐字段比对，分析正确性成为可自动验证的命题。
- **分析直达调度**：从风险分一路推到乡镇的无人机架次、农技员人数与药剂用量。
- **指标边界写在明处**：图像模型指标标注为公开数据集结果，不表述为本地田间准确率。

## 参赛提交物

源代码、数据、模型和文档骨架的检查命令为：

```powershell
.\.venv\Scripts\python.exe scripts/competition_readiness.py
.\.venv\Scripts\python.exe -m pytest -q
```

正式报名仍需根据本届赛题通知制作 Word/PDF、PPT/PPTX 与演示视频（**时长上限以通知为准**），并填写作品地址、备用地址与源代码网盘提取码，具体见 [docs/参赛提交清单.md](docs/参赛提交清单.md)。

本仓库已提供一套可编辑的参赛材料初稿生成器：

```powershell
$py = ".\.venv\Scripts\python.exe"
& $py scripts/build_submission_artifacts.py
```

PPT 由 `scripts/build_pptx.py` 单独生成：

```powershell
& $py scripts/build_pptx.py
```

生成结果位于 `submission_artifacts/`，包括概要介绍 Word/PDF、详细方案 Word/PDF、15 份说明书 DOCX（含竞赛承诺书）以及 20 页项目简介 PPTX。文件名按赛题通知规定使用 `云穗智擎_山东建筑大学_张衡_材料名` 格式。

需要人工完成的正式提交工作有五类：补录赛题与团队信息并批量重命名文件、部署到评审期可持续访问的地址并填写作品地址与备用地址、上传源代码到网盘并填写提取码、替换 PPT 中的现场截图、按本届通知规定的时长录制 MP4。详见 [docs/正式提交材料准备说明.md](docs/正式提交材料准备说明.md)。
