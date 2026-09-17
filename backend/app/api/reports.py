from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.services.report_service import generate_daily_report, get_report


router = APIRouter(prefix="/api/reports", tags=["报告生成"], dependencies=[Depends(get_current_user)])


class DailyReportRequest(BaseModel):
    town: str | None = None


@router.post("/daily")
def daily_report(payload: DailyReportRequest, db: Session = Depends(get_db)) -> dict:
    return generate_daily_report(db, payload.town)


@router.get("/{report_id}")
def read_report(report_id: str) -> dict:
    try:
        return get_report(report_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="报告不存在") from exc
