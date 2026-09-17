from datetime import date, datetime

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Farm, InspectionTask


router = APIRouter(prefix="/api/inspection-tasks", tags=["巡检任务"], dependencies=[Depends(get_current_user)])


class TaskCreate(BaseModel):
    farm_id: int
    title: str
    priority: str = "中"
    assignee: str = "农技员A"
    due_date: date
    description: str = ""


class TaskPatch(BaseModel):
    title: str | None = None
    priority: str | None = None
    assignee: str | None = None
    due_date: date | None = None
    status: str | None = None
    record: str | None = None


@router.get("")
def list_tasks(status: str | None = None, priority: str | None = None, db: Session = Depends(get_db)) -> dict:
    query = db.query(InspectionTask).join(Farm, Farm.id == InspectionTask.farm_id)
    if status:
        query = query.filter(InspectionTask.status == status)
    if priority:
        query = query.filter(InspectionTask.priority == priority)
    tasks = query.order_by(InspectionTask.due_date.asc(), InspectionTask.priority.desc()).limit(300).all()
    return {"items": [_serialize_task(t) for t in tasks]}


@router.post("")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> dict:
    farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
    if farm is None:
        raise HTTPException(status_code=404, detail="地块不存在")
    task = InspectionTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


@router.patch("/{task_id}")
def patch_task(task_id: int, payload: TaskPatch, db: Session = Depends(get_db)) -> dict:
    task = db.query(InspectionTask).filter(InspectionTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(task, key, value)
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return _serialize_task(task)


def _serialize_task(task: InspectionTask) -> dict:
    return {
        "id": task.id,
        "farm_id": task.farm_id,
        "farm_name": task.farm.name if task.farm else "",
        "town": task.farm.town if task.farm else "",
        "crop": task.farm.crop.name if task.farm and task.farm.crop else "",
        "title": task.title,
        "priority": task.priority,
        "assignee": task.assignee,
        "due_date": task.due_date,
        "status": task.status,
        "description": task.description,
        "record": task.record,
        "created_at": task.created_at,
    }
