from functools import lru_cache

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import Farm, WeatherRecord
from rag.ragflow_client import RAGFlowClient
from rag.retriever import AgriKnowledgeRAG


router = APIRouter(prefix="/api/assistant", tags=["AI农技助手"], dependencies=[Depends(get_current_user)])


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


@lru_cache
def get_rag_client() -> RAGFlowClient:
    local_rag = AgriKnowledgeRAG(settings.knowledge_base_dir)
    return RAGFlowClient(settings, local_rag)


@router.get("/status")
def status() -> dict:
    return get_rag_client().status()


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> dict:
    high_farms = db.query(Farm).filter(Farm.risk_level == "高").order_by(Farm.current_risk_score.desc()).limit(8).all()
    latest_weather = db.query(WeatherRecord).order_by(WeatherRecord.record_date.desc()).first()
    weather_hint = ""
    if latest_weather:
        weather_hint = f"{latest_weather.town} {latest_weather.weather_type}，湿度 {latest_weather.humidity:.0f}%、降雨 {latest_weather.rainfall:.1f}mm"
    answer = get_rag_client().answer(
        payload.question,
        {
            "high_risk_farms": [f"{farm.town}-{farm.name}({farm.risk_level}{farm.current_risk_score:.0f})" for farm in high_farms],
            "weather_hint": weather_hint,
        },
    )
    return {"question": payload.question, **answer}
