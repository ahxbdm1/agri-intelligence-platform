from __future__ import annotations

from io import BytesIO
from pathlib import Path
import json
import random
import sys

import joblib
import numpy as np
from PIL import Image, ImageDraw
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import ModelMetric  # noqa: E402
from ml.disease_classifier import DISEASE_LIBRARY, FEATURE_VERSION, extract_visual_features  # noqa: E402

SEED = 20260506


def make_leaf_image(label: int, sample: int) -> bytes:
    rng = random.Random(SEED + label * 1000 + sample)
    image = Image.new("RGB", (96, 96), (35 + rng.randrange(15), 105 + rng.randrange(30), 48 + rng.randrange(18)))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((8, 8, 88, 88), fill=(54, 150 + rng.randrange(25), 65, 255), outline=(160, 215, 120, 220), width=2)
    if label == 0:
        for _ in range(12):
            x, y, radius = rng.randrange(22, 72), rng.randrange(20, 74), rng.randrange(3, 8)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(70, 42, 28, 210))
    elif label == 1:
        for _ in range(15):
            x, y = rng.randrange(20, 76), rng.randrange(18, 78)
            draw.ellipse((x, y, x + 4, y + 7), fill=(219, 136, 92, 205))
    elif label == 2:
        for _ in range(10):
            x, y = rng.randrange(20, 74), rng.randrange(18, 74)
            draw.polygon([(x, y + 8), (x + 3, y), (x + 9, y - 3), (x + 7, y + 6)], fill=(100, 45, 34, 210))
    elif label == 3:
        for _ in range(9):
            x, y = rng.randrange(18, 70), rng.randrange(20, 72)
            draw.rounded_rectangle((x, y, x + rng.randrange(10, 18), y + 4), radius=2, fill=(90, 44, 28, 215))
    else:
        for _ in range(14):
            x, y = rng.randrange(18, 74), rng.randrange(18, 74)
            draw.ellipse((x, y, x + 7, y + 5), fill=(228, 205, 63, 190))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    features, labels = [], []
    for label in range(len(DISEASE_LIBRARY)):
        for sample in range(80):
            features.append(extract_visual_features(make_leaf_image(label, sample))[0])
            labels.append(label)
    x_train, x_test, y_train, y_test = train_test_split(
        np.asarray(features), np.asarray(labels), test_size=0.25, random_state=SEED, stratify=labels
    )
    model = RandomForestClassifier(n_estimators=140, max_depth=18, random_state=SEED, n_jobs=-1, class_weight="balanced")
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, average="macro", zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, average="macro", zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, predictions, average="macro", zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "train_samples": int(len(y_train)),
        "test_samples": int(len(y_test)),
    }
    model_dir = PROJECT_ROOT / "data" / "generated" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "disease_model.joblib"
    joblib.dump({
        "model": model,
        "labels": [item["disease_name"] for item in DISEASE_LIBRARY],
        "feature_version": FEATURE_VERSION,
        "model_version": "rf-leaf-v1",
        "metrics": metrics,
    }, model_path)
    (model_dir / "disease_model_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    persist_metrics(metrics)
    print({"model": str(model_path), **metrics})


def persist_metrics(metrics: dict) -> None:
    db = SessionLocal()
    try:
        for name in ("accuracy", "precision", "recall", "f1"):
            db.add(ModelMetric(model_name="disease_classifier", task="image_classification", metric_name=name, metric_value=metrics[name], dataset_version="synthetic-leaf-v1"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
