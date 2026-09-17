import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import alerts, assistant, auth, dashboard, data_io, disease, farms, inspections, predictions, reports, workflows
from app.core.config import settings
from app.db.session import Base, engine
from app.db.session import SessionLocal
from app.models import User


logger = logging.getLogger("agri-intelligence")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data_on_startup:
        seed_demo_data_if_empty()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="农智云瞰 API",
        description="县域农业病虫害识别、产量风险预测与农情决策大数据平台",
        version="1.0.0",
        lifespan=app_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging(request, call_next):
        request_id = uuid4().hex[:12]
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "服务器内部错误", "request_id": request_id})
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            round((perf_counter() - started) * 1000),
        )
        return response

    @app.get("/health")
    def health() -> dict:
        db_ok = False
        db_error = None
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:  # pragma: no cover - exercised by deployment failures
            db_error = str(exc)[:160]
        model_files = {
            name: (settings.model_dir / name).exists()
            for name in ("risk_model.joblib", "yield_model.joblib", "anomaly_detector.joblib")
        }
        return {
            "status": "ok" if db_ok else "degraded",
            "service": "agri-intelligence-platform",
            "database": {"ok": db_ok, "error": db_error},
            "models": model_files,
            "ragflow": {"configured": bool(settings.ragflow_enabled and settings.ragflow_chat_id)},
        }

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(farms.router)
    app.include_router(disease.router)
    app.include_router(predictions.router)
    app.include_router(alerts.router)
    app.include_router(inspections.router)
    app.include_router(assistant.router)
    app.include_router(data_io.router)
    app.include_router(reports.router)
    app.include_router(workflows.router)
    return app


def seed_demo_data_if_empty() -> None:
    """Seed only a brand-new demo database; never overwrite existing data."""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            logger.info("demo_seed_skipped reason=database_not_empty")
            return
    finally:
        db.close()
    try:
        from scripts.generate_demo_data import main as generate_demo_data

        generate_demo_data()
        logger.info("demo_seed_completed")
    except Exception:
        logger.exception("demo_seed_failed")


app = create_app()
