from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.core.config import settings
from ml.disease_classifier import PestDiseaseClassifier
from ml.yolo_disease_classifier import YoloDiseaseClassifier


router = APIRouter(prefix="/api/disease", tags=["病虫害识别"], dependencies=[Depends(get_current_user)])


@router.post("/predict")
async def predict_disease(file: UploadFile | None = File(default=None)) -> dict:
    image_bytes = await file.read() if file else None
    provider = settings.disease_model_provider.lower()
    if provider in {"ip102", "yolo_ip102", "pest_yolo"}:
        classifier = YoloDiseaseClassifier(settings.pest_yolo_model_path, mock=settings.mock_disease_model)
    elif provider == "yolo":
        classifier = YoloDiseaseClassifier(settings.disease_yolo_model_path, mock=settings.mock_disease_model)
    else:
        classifier = PestDiseaseClassifier(settings.model_dir / "disease_model.joblib", mock=settings.mock_disease_model)
    result = classifier.predict(image_bytes)
    return {
        "disease_name": result.disease_name,
        "confidence": result.confidence,
        "severity": result.severity,
        "suggestion": result.suggestion,
        "need_review": result.need_review,
        "model_version": result.model_version,
        "model_note": (
            "当前使用基于 IP102 公开 VOC 标注数据训练的 102 类 YOLO 害虫检测模型；测试指标来自公开测试集，正式应用仍需使用山东本地田间样本复测。"
            if result.model_version.startswith("yolo-ip102-")
            else "当前使用基于公开 PlantDoc 真实标注数据训练的本地 YOLO 检测模型；正式应用仍需使用山东本地田间数据复测。"
            if result.model_version.startswith("yolo-plantdoc-")
            else "当前使用本地 YOLO 检测模型；正式应用需使用真实标注数据重新训练。"
            if result.model_version.startswith("yolo-")
            else "当前使用训练保存的轻量特征分类模型；训练 disease_model.joblib 后可切换为该模型。"
            if result.model_version.startswith("rf-")
            else "当前使用演示降级接口；训练并配置对应模型后可切换为本地模型。"
        ),
        "explainability": result.explainability,
    }
