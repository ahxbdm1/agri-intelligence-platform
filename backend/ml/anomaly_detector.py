from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class SensorAnomalyDetector:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.scaler = StandardScaler()
        self.model = IsolationForest(contamination=0.035, random_state=2026)
        self.fitted = False
        if self.model_path and self.model_path.exists():
            payload = joblib.load(self.model_path)
            self.scaler = payload["scaler"]
            self.model = payload["model"]
            self.fitted = True

    def train(self, df: pd.DataFrame) -> dict:
        cols = ["soil_moisture", "soil_temperature", "ph", "light_intensity", "nitrogen", "phosphorus", "potassium"]
        X = self.scaler.fit_transform(df[cols])
        preds = self.model.fit_predict(X)
        self.fitted = True
        return {"anomaly_rate": float((preds == -1).mean()), "samples": int(len(df))}

    def detect(self, records: list[dict]) -> list[dict]:
        if not records:
            return []
        cols = ["soil_moisture", "soil_temperature", "ph", "light_intensity", "nitrogen", "phosphorus", "potassium"]
        df = pd.DataFrame(records)
        if self.fitted:
            preds = self.model.predict(self.scaler.transform(df[cols]))
            scores = self.model.decision_function(self.scaler.transform(df[cols]))
        else:
            preds = np.where((df["soil_moisture"] > 72) | (df["ph"].lt(5.5)) | (df["ph"].gt(8.2)), -1, 1)
            scores = np.where(preds == -1, -0.12, 0.08)
        output = []
        for record, pred, score in zip(records, preds, scores, strict=False):
            if pred == -1:
                reason = "墒情过高或酸碱度异常，需核查传感器与田间排水"
                output.append({"record": record, "anomaly_score": round(float(score), 4), "reason": reason})
        return output

    def save(self, model_path: str | Path | None = None) -> None:
        path = Path(model_path or self.model_path or "anomaly_detector.joblib")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"scaler": self.scaler, "model": self.model}, path)
