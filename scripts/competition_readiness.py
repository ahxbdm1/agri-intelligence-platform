"""Print a reproducible readiness checklist for the competition submission."""

from __future__ import annotations

from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Alert,
    Farm,
    InspectionTask,
    PestDiseaseReport,
    RiskPrediction,
    SensorRecord,
    WeatherRecord,
    YieldRecord,
)


REQUIRED_DOCS = [
    "README.md",
    "docs/项目概要介绍.md",
    "docs/项目详细方案.md",
    "docs/安装部署说明.md",
    "docs/使用说明.md",
    "docs/数据集说明.md",
    "docs/开源组件与协议说明.md",
    "docs/演示视频脚本.md",
    "docs/PPT大纲.md",
    "docs/答辩问题准备.md",
    "docs/参赛提交清单.md",
    "docs/项目简介_300-500字.md",
    "docs/正式提交材料准备说明.md",
    "docs/现场演示与部署核验清单.md",
]


def main() -> None:
    db = SessionLocal()
    try:
        counts = {
            "farms": db.query(Farm).count(),
            "weather_records": db.query(WeatherRecord).count(),
            "sensor_records": db.query(SensorRecord).count(),
            "pest_disease_reports": db.query(PestDiseaseReport).count(),
            "yield_records": db.query(YieldRecord).count(),
            "risk_predictions": db.query(RiskPrediction).count(),
            "alerts": db.query(Alert).count(),
            "inspection_tasks": db.query(InspectionTask).count(),
        }
    finally:
        db.close()

    model_files = {
        name: (PROJECT_ROOT / "data" / "generated" / "models" / name).exists()
        for name in ["risk_model.joblib", "yield_model.joblib", "anomaly_detector.joblib", "disease_model.joblib", "disease_yolo_best.pt"]
    }
    docs = {path: (PROJECT_ROOT / path).exists() for path in REQUIRED_DOCS}
    artifact_files = {
        "overview_docx": any((PROJECT_ROOT / "submission_artifacts").glob("*_项目概要介绍.docx")),
        "overview_pdf": any((PROJECT_ROOT / "submission_artifacts").glob("*_项目概要介绍.pdf")),
        "detail_docx": any((PROJECT_ROOT / "submission_artifacts").glob("*_项目详细方案.docx")),
        "detail_pdf": any((PROJECT_ROOT / "submission_artifacts").glob("*_项目详细方案.pdf")),
        "presentation_pptx": any((PROJECT_ROOT / "submission_artifacts").glob("*_项目简介PPT.pptx")),
    }
    checks = {
        "six_towns_and_80_farms": counts["farms"] >= 80,
        "180_days_weather": counts["weather_records"] >= 180 * 6,
        "5000_sensor_records": counts["sensor_records"] >= 5000,
        "1000_business_records": sum(counts[key] for key in ["pest_disease_reports", "yield_records", "alerts", "inspection_tasks"]) >= 1000,
        "trained_models": all(model_files.values()),
        "required_docs": all(docs.values()),
        "official_document_artifacts": all(artifact_files.values()),
    }
    result = {
        "project": "农智云瞰",
        "counts": counts,
        "model_files": model_files,
        "required_docs": docs,
        "artifact_files": artifact_files,
        "checks": checks,
        "ready_for_source_package": all(checks.values()),
        "remaining_official_artifacts": [
            "补录团队名称、学校名称、队长姓名、全部成员与指导教师",
            "替换PPT中的现场截图与最终实测指标",
            "录制不超过8分钟的演示视频MP4",
            "在目标机器完成Docker/本地启动、RAGFlow连通和浏览器实机核验",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
