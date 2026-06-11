print("USER ROUTER LOADED")

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role
from app.schemas import UserCreate, UserResponse

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.username == user.username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    role = db.query(Role).filter(
        Role.role_id == user.role_id
    ).first()

    if not role:
        raise HTTPException(
            status_code=400,
            detail="Invalid Role ID"
        )

    new_user = User(
        username=user.username,
        password=user.password,
        role_id=user.role_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db)
):
    users = db.query(User).all()

    return users