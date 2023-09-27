from datetime import timedelta, datetime, date
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Users
from starlette import status

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

class CreateUserRequest(BaseModel):
    name: str
    age: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    try:
        create_user_model = Users(
            name=create_user_request.name,
            age=create_user_request.age
        )
        db.add(create_user_model)
        db.commit()
        return create_user_model  # Return the created user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )

@router.get("/users", status_code=status.HTTP_200_OK)
async def get_users(db: Session = Depends(get_db)):
    users = db.query(Users).all()
    return users
