from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
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
    email: EmailStr
    gender: str
    phone_number: str

class UpdateUserRequest(BaseModel):
    name: str
    age: int
    email: str
    gender: str
    phone_number: str

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "Success : True"
    data: dict = None

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
        # Check if the email already exists
        existing_user = db.query(Users).filter(Users.email == create_user_request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

        # Check phone number length
        if len(create_user_request.phone_number) != 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number should be exactly 10 digits",
            )

        create_user_model = Users(
            name=create_user_request.name,
            age=create_user_request.age,
            email=create_user_request.email,
            gender=create_user_request.gender,
            phone_number=create_user_request.phone_number
        )
        db.add(create_user_model)
        db.commit()
        db.refresh(create_user_model)

        user_data = {
            "id": create_user_model.id,
            "name": create_user_model.name,
            "age": create_user_model.age,
            "email": create_user_model.email,
            "gender": create_user_model.gender,
            "phone_number": create_user_model.phone_number
        }

        response_data = SuccessResponse(data=user_data, message="User created successfully")

        if response_data.success:
            print("Success Response (Create User):", response_data.json())
        else:
            print("Success Response (Create User): False")

        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create user: {str(e)}",
        )

@router.get("/users", status_code=status.HTTP_200_OK)
async def get_users(db: Session = Depends(get_db)):
    try:
        users = db.query(Users).all()

        users_data = [{"id": user.id, "name": user.name, "age": user.age, "email": user.email, "gender": user.gender, "phone_number": user.phone_number} for user in users]
        
        response_data = SuccessResponse(data={"users": users_data}, message="Users retrieved successfully")

        if response_data.success:
            print("Success Response (Get Users):", response_data.json())
        else:
            print("Success Response (Get Users): False")

        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve users: {str(e)}",
        )

@router.put('/update_user/{user_id}')
def update_user(user_id: int, update_data: UpdateUserRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found",
            )

        for field, value in update_data.dict().items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        updated_user_data = {
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "email": user.email,
            "gender": user.gender,
            "phone_number": user.phone_number
        }

        response_data = SuccessResponse(data=updated_user_data, message="User updated successfully")

        if response_data.success:
            print("Success Response (Update User):", response_data.json())
        else:
            print("Success Response (Update User): False")

        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update user: {str(e)}",
        )
    
@router.delete('/delete_user/{user_id}')
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found",
            )

        db.delete(user)
        db.commit()

        response_data = SuccessResponse(success=True, message="User deleted successfully")

        if response_data.success:
            print("Success Response (Delete User):", response_data.json())
        else:
            print("Success Response (Delete User): False")

        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete user: {str(e)}",
        )
