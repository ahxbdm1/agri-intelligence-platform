from __future__ import annotations

from io import BytesIO
from pathlib import Path
import json

from PIL import Image

from ml.disease_classifier import DISEASE_LIBRARY, DiseasePrediction


class YoloDiseaseClassifier:
    """YOLO detection adapter with the same response contract as the baseline model."""

    def __init__(self, model_path: str | Path, mock: bool = True, classes_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path)
        self.model = None
        self.model_version = "yolo-unavailable"
        self.class_names = [item["disease_name"] for item in DISEASE_LIBRARY]
        resolved_classes_path = Path(classes_path) if classes_path else self.model_path.with_suffix(".classes.json")
        if resolved_classes_path.exists():
            try:
                loaded_classes = json.loads(resolved_classes_path.read_text(encoding="utf-8"))
                if isinstance(loaded_classes, list) and loaded_classes:
                    self.class_names = [str(item) for item in loaded_classes]
            except (OSError, json.JSONDecodeError):
                pass
        if not mock and self.model_path.exists():
            try:
                from ultralytics import YOLO

                self.model = YOLO(str(self.model_path))
                model_name = self.model_path.name.lower()
                self.model_version = (
                    "yolo-ip102-v1"
                    if "ip102" in model_name
                    else "yolo-plantdoc-v1"
                    if "plantdoc" in model_name
                    else "yolo-disease-v1"
                )
            except Exception:
                self.model = None

    def predict(self, image_bytes: bytes | None) -> DiseasePrediction:
        if self.model is None or not image_bytes:
            from ml.disease_classifier import PestDiseaseClassifier

            return PestDiseaseClassifier(mock=True).predict(image_bytes)

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        import torch

        device = 0 if torch.cuda.is_available() else "cpu"
        result = self.model.predict(source=image, verbose=False, device=device)[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return DiseasePrediction(
                disease_name="未检出明确病斑",
                confidence=0.0,
                severity="轻",
                suggestion="建议补充清晰叶片图像，检查叶片正反面和田间环境，并由农技人员进行人工复核。",
                need_review=True,
                model_version=self.model_version,
                explainability={
                    "method": "YOLO 检测框",
                    "lesion_region": None,
                    "detections": [],
                    "explanation": "未检测到置信度足够的病斑或害虫区域。",
                },
            )

        confidences = boxes.conf.detach().cpu().tolist()
        classes = boxes.cls.detach().cpu().tolist()
        coordinates = boxes.xyxy.detach().cpu().tolist()
        best = max(range(len(confidences)), key=lambda index: confidences[index])
        class_index = int(classes[best])
        disease_name = self.class_names[class_index % len(self.class_names)]
        suggestion = self._suggestion(disease_name)
        confidence = round(float(confidences[best]), 3)
        best_box = coordinates[best]
        width, height = image.size
        box_area = max(0.0, (best_box[2] - best_box[0]) * (best_box[3] - best_box[1])) / max(width * height, 1)
        severity = "重" if box_area >= 0.18 else "中" if box_area >= 0.07 else "轻"
        detections = [
            {
                "class_id": int(classes[index]),
                "disease_name": self.class_names[int(classes[index]) % len(self.class_names)],
                "confidence": round(float(confidences[index]), 3),
                "box": [round(float(value), 1) for value in coordinates[index]],
            }
            for index in range(len(confidences))
        ]
        return DiseasePrediction(
            disease_name=disease_name,
            confidence=confidence,
            severity=severity,
            suggestion=suggestion,
            need_review=confidence < 0.72 or severity == "重",
            model_version=self.model_version,
            explainability={
                "method": "YOLO 检测框",
                "lesion_region": {"x": round(best_box[0] / width, 3), "y": round(best_box[1] / height, 3), "width": round((best_box[2] - best_box[0]) / width, 3), "height": round((best_box[3] - best_box[1]) / height, 3)},
                "detections": detections,
                "explanation": (
                    "检测框表示模型识别到的疑似害虫目标；当前模型基于 IP102 公开标注数据训练，正式应用仍需使用山东本地田间数据复测。"
                    if self.model_version.startswith("yolo-ip102-")
                    else "检测框表示模型识别到的疑似病斑区域；当前模型基于公开 PlantDoc 标注数据训练，正式应用仍需使用本地田间数据复测。"
                ),
            },
        )

    @staticmethod
    def _suggestion(disease_name: str) -> str:
        lowered = disease_name.lower()
        if "tomato" in lowered or "番茄" in disease_name:
            return "建议清除病叶、降低棚内湿度并加强通风；药剂使用需结合当地植保指导，避免连续使用同一作用机制。"
        if "corn" in lowered or "maize" in lowered or "玉米" in disease_name:
            return "建议优先巡检密植和低洼地块，清除中心病株并改善通风；发病田块按植保规范开展药剂防治。"
        if "rice" in lowered or "水稻" in disease_name:
            return "建议关注高湿寡照、氮肥偏高田块，及时排水通风；疑似暴发时联系农技人员复核。"
        if "wheat" in lowered or "小麦" in disease_name:
            return "建议在抽穗扬花期关注连续阴雨天气，优先巡检低洼高湿麦田并按当地植保建议开展预防。"
        return "建议隔离观察并补充近距离、自然光下的叶片图像，结合天气、作物生育期和农技人员意见制定防治措施。"
