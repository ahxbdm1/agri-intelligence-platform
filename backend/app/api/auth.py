from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, verify_password
from app.models import User


router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str | None = None


VALID_ROLES = {"县域管理员", "农技专家", "合作社用户"}


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "organization": user.organization,
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    if payload.role and payload.role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的用户角色")
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if payload.role and payload.role != user.role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="演示身份与账号不匹配")
    token = create_access_token(user.username, user.role)
    return {"access_token": token, "token_type": "bearer", "user": user_payload(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_payload(user)
