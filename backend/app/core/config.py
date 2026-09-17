from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "农智云瞰"
    environment: str = "development"
    database_url: str = "sqlite:///./agri_intelligence.db"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    frontend_origin: str = "http://localhost:3000"
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    qwen_api_key: str | None = None
    ragflow_enabled: bool = False
    ragflow_base_url: str = ""
    ragflow_api_key: str = ""
    ragflow_dataset_ids: str = ""
    ragflow_chat_id: str = ""
    # RAGFlow may need several seconds for retrieval plus LLM generation on a small server.
    ragflow_timeout_seconds: float = 35.0
    ragflow_status_timeout_seconds: float = 12.0
    ragflow_verify_ssl: bool = True
    mock_disease_model: bool = True
    disease_model_provider: str = "rf"
    disease_yolo_model_path: Path = ROOT_DIR / "data" / "generated" / "models" / "plantdoc_yolo_best.pt"
    pest_yolo_model_path: Path = ROOT_DIR / "data" / "generated" / "models" / "ip102_pest_yolo_best.pt"
    seed_demo_data_on_startup: bool = False
    model_dir: Path = ROOT_DIR / "data" / "generated" / "models"
    reports_dir: Path = ROOT_DIR / "data" / "generated" / "reports"
    knowledge_base_dir: Path = ROOT_DIR / "knowledge_base"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        configured = [item.strip().rstrip("/") for item in self.frontend_origin.split(",") if item.strip()]
        return list(dict.fromkeys(configured + ["http://127.0.0.1:3000", "http://localhost:3001"]))

    @property
    def ragflow_dataset_id_list(self) -> list[str]:
        return [item.strip() for item in self.ragflow_dataset_ids.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
