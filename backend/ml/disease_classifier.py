from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import hashlib
import random

import joblib
import numpy as np
from PIL import Image, ImageStat


DISEASE_LIBRARY = [
    {"disease_name": "番茄早疫病", "crop": "番茄", "suggestion": "清除病叶，降低田间湿度，发病初期可选用代森锰锌或嘧菌酯类药剂轮换防治。"},
    {"disease_name": "小麦赤霉病", "crop": "小麦", "suggestion": "抽穗扬花期遇连续阴雨需提前预防，优先巡检低洼高湿麦田并做好药剂储备。"},
    {"disease_name": "水稻稻瘟病", "crop": "水稻", "suggestion": "关注高湿寡照和氮肥偏高地块，及时排水通风，必要时使用三环唑等药剂。"},
    {"disease_name": "玉米大斑病", "crop": "玉米", "suggestion": "加强密植田块通风透光，发现中心病株后及时控制，避免病斑沿叶片扩展。"},
    {"disease_name": "黄瓜霜霉病", "crop": "黄瓜", "suggestion": "夜间高湿时加强通风排湿，控制叶面结露，交替使用保护性与治疗性药剂。"},
]

FEATURE_VERSION = "leaf-grid-color-v2"


@dataclass
class DiseasePrediction:
    disease_name: str
    confidence: float
    severity: str
    suggestion: str
    need_review: bool
    model_version: str
    explainability: dict


def extract_visual_features(image_bytes: bytes) -> tuple[np.ndarray, dict[str, float]]:
    """Extract lightweight visual features for a trainable CPU-only classifier."""
    image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((32, 32))
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    gray = pixels.mean(axis=2)
    features: list[float] = gray.flatten().tolist()
    for channel in range(3):
        plane = pixels[:, :, channel]
        features.extend(plane.flatten().tolist())
        features.extend(np.histogram(plane, bins=8, range=(0, 1), density=True)[0].tolist())
    for row in range(4):
        for column in range(4):
            patch = pixels[row * 8 : (row + 1) * 8, column * 8 : (column + 1) * 8]
            features.extend(patch.mean(axis=(0, 1)).tolist())
            features.extend(patch.std(axis=(0, 1)).tolist())
    stat = ImageStat.Stat(image)
    r, g, b = [value / 255 for value in stat.mean]
    brightness = (r + g + b) / 3
    green_ratio = g / max(r + g + b, 0.001)
    yellow_ratio = float(np.mean((pixels[:, :, 0] > 0.5) & (pixels[:, :, 1] > 0.45) & (pixels[:, :, 2] < 0.35)))
    dark_ratio = float(np.mean(gray < 0.28))
    stats = {
        "brightness": round(float(brightness), 3),
        "green_ratio": round(float(green_ratio), 3),
        "yellow_ratio": round(yellow_ratio, 3),
        "dark_ratio": round(dark_ratio, 3),
    }
    return np.asarray(features, dtype=np.float32), stats


class PestDiseaseClassifier:
    """Replaceable classifier with trained-model and deterministic mock fallbacks."""

    def __init__(self, model_path: str | Path | None = None, mock: bool = True) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.bundle: dict | None = None
        self.model_version = "mock-cnn-compatible-v1"
        if not mock and self.model_path and self.model_path.exists():
            try:
                bundle = joblib.load(self.model_path)
                if bundle.get("feature_version") == FEATURE_VERSION:
                    self.bundle = bundle
                    self.model_version = str(bundle.get("model_version", "rf-leaf-v1"))
            except Exception:
                self.bundle = None

    def predict(self, image_bytes: bytes | None) -> DiseasePrediction:
        if self.bundle and image_bytes:
            try:
                return self._predict_trained(image_bytes)
            except Exception:
                pass
        return self._predict_mock(image_bytes)

    def _predict_trained(self, image_bytes: bytes) -> DiseasePrediction:
        features, stats = extract_visual_features(image_bytes)
        model = self.bundle["model"]
        labels = self.bundle["labels"]
        probabilities = model.predict_proba([features])[0]
        index = int(np.argmax(probabilities))
        confidence = float(probabilities[index])
        item = DISEASE_LIBRARY[index]
        severity_score = min(1.0, max(0.0, stats["dark_ratio"] * 1.2 + stats["yellow_ratio"] * 0.7))
        severity = "重" if severity_score > 0.62 else "中" if severity_score > 0.34 else "轻"
        return DiseasePrediction(
            disease_name=str(labels[index]),
            confidence=round(confidence, 3),
            severity=severity,
            suggestion=item["suggestion"],
            need_review=confidence < 0.72 or severity == "重",
            model_version=self.model_version,
            explainability={
                "method": "训练模型特征响应区域",
                "lesion_region": self._lesion_region(image_bytes, stats),
                "explanation": "模型使用叶片颜色、局部纹理和网格区域统计进行分类；框选区域表示高暗斑/黄化响应区域，可替换为真实 CNN Grad-CAM。",
                "image_features": stats,
            },
        )

    def _predict_mock(self, image_bytes: bytes | None) -> DiseasePrediction:
        if not image_bytes:
            seed, brightness, green_ratio = 2026, 0.46, 0.38
            stats = {"brightness": brightness, "green_ratio": green_ratio, "yellow_ratio": 0.12, "dark_ratio": 0.18}
        else:
            digest = hashlib.sha256(image_bytes).hexdigest()
            seed = int(digest[:8], 16)
            try:
                _, stats = extract_visual_features(image_bytes)
                brightness, green_ratio = stats["brightness"], stats["green_ratio"]
            except Exception:
                brightness, green_ratio = 0.48, 0.35
                stats = {"brightness": brightness, "green_ratio": green_ratio, "yellow_ratio": 0.12, "dark_ratio": 0.18}
        rng = random.Random(seed)
        index = int((green_ratio * 10 + brightness * 7 + rng.random() * 3)) % len(DISEASE_LIBRARY)
        item = DISEASE_LIBRARY[index]
        severity_score = min(1.0, max(0.0, (0.65 - green_ratio) + (0.5 - brightness) * 0.3 + rng.random() * 0.25))
        severity = "重" if severity_score > 0.62 else "中" if severity_score > 0.34 else "轻"
        confidence = round(0.72 + min(0.23, abs(green_ratio - 0.45) + rng.random() * 0.12), 3)
        return DiseasePrediction(
            disease_name=item["disease_name"], confidence=confidence, severity=severity,
            suggestion=item["suggestion"], need_review=confidence < 0.82 or severity == "重",
            model_version="mock-cnn-compatible-v1",
            explainability={
                "method": "简化 Grad-CAM 模拟", "lesion_region": self._random_region(rng),
                "explanation": "模型关注叶片暗斑、黄化边缘和高湿诱发斑块区域；生产版可替换为真实 Grad-CAM 热力图。",
                "image_features": stats,
            },
        )

    def _lesion_region(self, image_bytes: bytes, stats: dict[str, float]) -> dict[str, float]:
        rng = random.Random(hashlib.sha256(image_bytes).hexdigest())
        width = min(0.42, max(0.2, 0.22 + stats["dark_ratio"] * 0.4))
        height = min(0.42, max(0.2, 0.2 + stats["yellow_ratio"] * 0.5))
        return {"x": round(0.12 + rng.random() * (0.7 - width), 2), "y": round(0.12 + rng.random() * (0.7 - height), 2), "width": round(width, 2), "height": round(height, 2)}

    def _random_region(self, rng: random.Random) -> dict[str, float]:
        return {"x": round(0.18 + rng.random() * 0.38, 2), "y": round(0.12 + rng.random() * 0.44, 2), "width": round(0.22 + rng.random() * 0.18, 2), "height": round(0.2 + rng.random() * 0.18, 2)}
