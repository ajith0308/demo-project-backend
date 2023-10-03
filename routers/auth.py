from datetime import timedelta, datetime
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Users
from passlib.context import CryptContext
from starlette import status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from cryptography.fernet import Fernet

router = APIRouter(
    prefix='/login',
    tags=['registration']
)

SECRET_KEY = '197b2c37c391bed93fe80344fe73b806947a65e36206e05a1a23c2fa12702fe3'
ALGORITHM = 'HS256'

ACCESS_TOKEN_EXPIRE_MINUTES = 5
REFRESH_TOKEN_EXPIRE_DAYS = 1

refresh_tokens = {}

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

revoked_tokens = set()

secret_key = Fernet.generate_key()
cipher_suite = Fernet(secret_key)

class CreateUserRequest(BaseModel):
    name: str
    age: int
    email: EmailStr
    gender: str
    phone_number: str
    username: str
    password: str

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

    @validator('password', pre=True, check_fields=False)
    def password_must_be_strong(cls, value):
        if not (8 <= len(value) <= 50):
            raise ValueError('Password must be between 8 and 50 characters long')
        return value

class Login(BaseModel):
    username_or_email: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class PasswordUpdate(BaseModel):
    username_or_email: str = Field(..., alias="username_or_email")
    new_password: str = Field(..., alias="newPassword")
    confirm_password: str = Field(..., alias="confirmPassword")

    @validator('username_or_email')
    def username_or_email_must_valid(cls, value):
        if '@' in value:
            email = EmailStr(value)
            return email
        else:
            if not (4 <= len(value) <= 50):
                raise ValueError('Username must be between 4 and 20 characters long')
            return value

    @validator('new_password')
    def password_must_be_strong(cls, value):
        if not (8 <= len(value) <= 20):
            raise ValueError('Password must be between 8 and 50 characters long')
        return value

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def authenticate_user(username_or_email: str, password: str, db):
    user = db.query(Users).filter(
        (Users.username == username_or_email) | (Users.email == username_or_email)
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or email")
    if not bcrypt_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    return user


def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='could not validate user.')
        return {'username': username, 'id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='could not validate user.')

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):

    if db.query(Users).filter(Users.username == create_user_request.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(Users).filter(Users.email == create_user_request.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
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
            phone_number=create_user_request.phone_number,
            username=create_user_request.username,
            hashed_password=bcrypt_context.hash(create_user_request.password)

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

@router.post("/token")
def login_for_access_token(login_request: Login,
                           db: db_dependency):
    user = authenticate_user(login_request.username_or_email, login_request.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"sub": user.username}, access_token_expires)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_access_token({"sub": user.username}, refresh_token_expires)
    return {"access_token": access_token, "refresh_token": refresh_token}


@router.put("/forget_password")
async def update_user_password(update_password: PasswordUpdate,
                               db: db_dependency):
    user = db.query(Users).filter(
        (Users.email == update_password.username_or_email) |
        (Users.username == update_password.username_or_email)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if update_password.new_password != update_password.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="New password and confirm password should be same")

    new_hashed_password = bcrypt_context.hash(update_password.new_password)
    user.hashed_password = new_hashed_password
    db.commit()
    return {'message': 'Password changed Successfully'}

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
    
@router.delete('/{user_id}', response_model=SuccessResponse)
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

        return response_data
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete user: {str(e)}",
        )

@router.post("/logout")
def logout(token: str):
    revoked_tokens.add(token)
    return {"message": "Logged out successfully"}