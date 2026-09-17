from fastapi.testclient import TestClient

from main import app
from ml.train.train_disease_model import make_leaf_image


client = TestClient(app)


def auth_headers() -> dict:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123", "role": "县域管理员"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_dashboard_summary() -> None:
    response = client.get("/api/dashboard/summary", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["farm_count"] >= 80


def test_disease_predict() -> None:
    response = client.post("/api/disease/predict", headers=auth_headers())
    assert response.status_code == 200
    assert "disease_name" in response.json()


def test_disease_predict_with_image() -> None:
    response = client.post(
        "/api/disease/predict",
        headers=auth_headers(),
        files={"file": ("demo-leaf.png", make_leaf_image(0, 1), "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] in {"rf-leaf-v1", "yolo-disease-v1", "yolo-plantdoc-v1", "yolo-ip102-v1", "mock-cnn-compatible-v1"}
    assert 0 <= payload["confidence"] <= 1
    assert "lesion_region" in payload["explainability"]


def test_daily_dispatch_workflow_dry_run() -> None:
    response = client.post(
        "/api/workflows/daily-dispatch",
        headers=auth_headers(),
        json={"max_tasks": 5, "dry_run": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "county-daily-agri-dispatch"
    assert payload["queue_count"] <= 5
    assert "material_plan" in payload
