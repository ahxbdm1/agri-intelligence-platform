from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


RISK_FACTORS = {
    "humidity": "空气湿度偏高",
    "rainfall": "近日报雨量偏高",
    "temperature": "温度偏离作物适宜区间",
    "history_disease_count": "历史病虫害记录较多",
    "soil_moisture": "土壤墒情偏高",
    "crop_type": "作物易感性",
    "area_mu": "地块面积与连片传播风险",
}


def risk_level(score: float) -> str:
    if score >= 78:
        return "高"
    if score >= 55:
        return "中"
    return "低"


@dataclass
class RiskModelResult:
    risk_score: float
    risk_level: str
    top_factors: list[dict]
    model_version: str


class RiskScoringModel:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.pipeline: Pipeline | None = None
        self.feature_names: list[str] = []
        if self.model_path and self.model_path.exists():
            payload = joblib.load(self.model_path)
            self.pipeline = payload["pipeline"]
            self.feature_names = payload.get("feature_names", [])

    def train(self, df: pd.DataFrame, target_col: str = "risk_score") -> dict:
        features = [
            "temperature",
            "humidity",
            "rainfall",
            "soil_moisture",
            "history_disease_count",
            "area_mu",
            "crop_type",
            "town",
        ]
        X = df[features]
        y = df[target_col].clip(0, 100)
        numeric_features = [c for c in features if c not in {"crop_type", "town"}]
        categorical_features = ["crop_type", "town"]
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_features),
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ]
        )
        model = RandomForestRegressor(n_estimators=160, random_state=2026, min_samples_leaf=3)
        self.pipeline = Pipeline([("preprocess", preprocessor), ("model", model)])
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.22, random_state=2026)
        self.pipeline.fit(X_train, y_train)
        preds = self.pipeline.predict(X_test)
        self.feature_names = self._feature_names(numeric_features)
        metrics = {
            "mae": float(mean_absolute_error(y_test, preds)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
            "r2": float(r2_score(y_test, preds)),
        }
        return metrics

    def save(self, model_path: str | Path | None = None) -> None:
        if self.pipeline is None:
            raise RuntimeError("模型尚未训练，不能保存")
        path = Path(model_path or self.model_path or "risk_model.joblib")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "feature_names": self.feature_names}, path)

    def predict(self, features: dict) -> RiskModelResult:
        frame = pd.DataFrame([self._normalize_features(features)])
        if self.pipeline is not None:
            score = float(np.clip(self.pipeline.predict(frame)[0], 0, 100))
            factors = self.explain(frame.iloc[0].to_dict())
            version = "random-forest-v1"
        else:
            score, factors = self._heuristic_score(frame.iloc[0].to_dict())
            version = "heuristic-fallback-v1"
        return RiskModelResult(
            risk_score=round(score, 2),
            risk_level=risk_level(score),
            top_factors=factors,
            model_version=version,
        )

    def explain(self, features: dict) -> list[dict]:
        if self.pipeline is None:
            return self._heuristic_score(features)[1]
        model = self.pipeline.named_steps["model"]
        preprocessor = self.pipeline.named_steps["preprocess"]
        names = list(preprocessor.get_feature_names_out())
        importances = model.feature_importances_
        pairs = sorted(zip(names, importances, strict=False), key=lambda x: x[1], reverse=True)[:5]
        readable = []
        for raw_name, value in pairs:
            key = raw_name.split("__")[-1].split("_")[0]
            label = RISK_FACTORS.get(key, raw_name.replace("num__", "").replace("cat__", ""))
            readable.append({"factor": label, "contribution": round(float(value) * 100, 2)})
        return readable

    def _normalize_features(self, features: dict) -> dict:
        return {
            "temperature": float(features.get("temperature", 28)),
            "humidity": float(features.get("humidity", 76)),
            "rainfall": float(features.get("rainfall", 12)),
            "soil_moisture": float(features.get("soil_moisture", 48)),
            "history_disease_count": float(features.get("history_disease_count", 3)),
            "area_mu": float(features.get("area_mu", 120)),
            "crop_type": str(features.get("crop_type", "水稻")),
            "town": str(features.get("town", "东湖镇")),
        }

    def _heuristic_score(self, features: dict) -> tuple[float, list[dict]]:
        humidity = features["humidity"]
        rainfall = features["rainfall"]
        temp = features["temperature"]
        soil = features["soil_moisture"]
        history = features["history_disease_count"]
        crop_risk = {"番茄": 11, "小麦": 8, "水稻": 12, "玉米": 7, "黄瓜": 10}.get(features["crop_type"], 6)
        score = 18 + humidity * 0.28 + rainfall * 0.72 + max(0, temp - 30) * 2.2 + soil * 0.18 + history * 4.5 + crop_risk
        factors = [
            {"factor": "空气湿度偏高", "contribution": round(min(30, humidity * 0.28), 2)},
            {"factor": "降雨量诱发病害传播", "contribution": round(min(26, rainfall * 0.72), 2)},
            {"factor": "历史病虫害记录较多", "contribution": round(history * 4.5, 2)},
            {"factor": "作物易感性", "contribution": crop_risk},
            {"factor": "土壤墒情偏高", "contribution": round(soil * 0.18, 2)},
        ]
        return float(np.clip(score, 0, 100)), sorted(factors, key=lambda x: x["contribution"], reverse=True)[:5]

    def _feature_names(self, numeric_features: list[str]) -> list[str]:
        if self.pipeline is None:
            return numeric_features
        return list(self.pipeline.named_steps["preprocess"].get_feature_names_out())
