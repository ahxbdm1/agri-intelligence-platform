from datetime import datetime, timedelta

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Alert, Farm, InspectionTask


router = APIRouter(prefix="/api/alerts", tags=["预警中心"], dependencies=[Depends(get_current_user)])


class AlertCreate(BaseModel):
    farm_id: int
    title: str
    risk_level: str
    trigger_reason: str
    owner: str = "农技站"
    suggestion: str = ""


class AlertPatch(BaseModel):
    status: str | None = None
    owner: str | None = None
    suggestion: str | None = None


@router.get("")
def list_alerts(status: str | None = None, risk_level: str | None = None, db: Session = Depends(get_db)) -> dict:
    query = db.query(Alert).join(Farm, Farm.id == Alert.farm_id)
    if status:
        query = query.filter(Alert.status == status)
    if risk_level:
        query = query.filter(Alert.risk_level == risk_level)
    alerts = query.order_by(Alert.created_at.desc()).limit(200).all()
    return {"items": [_serialize_alert(a) for a in alerts]}


@router.post("")
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)) -> dict:
    farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
    if farm is None:
        raise HTTPException(status_code=404, detail="地块不存在")
    alert = Alert(**payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _serialize_alert(alert)


@router.patch("/{alert_id}")
def patch_alert(alert_id: int, payload: AlertPatch, db: Session = Depends(get_db)) -> dict:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="预警不存在")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(alert, key, value)
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return _serialize_alert(alert)


@router.post("/{alert_id}/inspection-task")
def create_task_from_alert(alert_id: int, db: Session = Depends(get_db)) -> dict:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="预警不存在")
    task = InspectionTask(
        farm_id=alert.farm_id,
        alert_id=alert.id,
        title=f"复核处置：{alert.title}",
        priority="高" if alert.risk_level == "高" else "中",
        assignee=alert.owner,
        due_date=(datetime.utcnow() + timedelta(days=1)).date(),
        description=f"触发原因：{alert.trigger_reason}\n处置建议：{alert.suggestion}",
    )
    alert.status = "处理中"
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"task_id": task.id, "status": "created"}


def _serialize_alert(alert: Alert) -> dict:
    return {
        "id": alert.id,
        "farm_id": alert.farm_id,
        "farm_name": alert.farm.name if alert.farm else "",
        "town": alert.farm.town if alert.farm else "",
        "title": alert.title,
        "risk_level": alert.risk_level,
        "trigger_reason": alert.trigger_reason,
        "status": alert.status,
        "owner": alert.owner,
        "suggestion": alert.suggestion,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
    }
