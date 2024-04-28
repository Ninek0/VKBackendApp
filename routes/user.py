from datetime import timedelta, datetime
import os
from fastapi import APIRouter
from jose import jwt
from pydantic import BaseModel
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from database.database import SessionLocal
from fastapi import FastAPI, Response, Request, Depends
from jose import jwt
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session
from starlette import status
from database.models import User
from dotenv import load_dotenv

load_dotenv()

bcrypt_context = CryptContext(
    schemes=['bcrypt'], 
    deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

router = APIRouter(
    prefix='/user',
    tags=['user']
)

class UserRequest(BaseModel):
    login: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.post('/registration', status_code=status.HTTP_201_CREATED)
async def registration(
    db: db_dependency,
    newUser: UserRequest):

    if len(newUser.login) < 5 or len(newUser.login) > 50:
        return Response(
            content={'error': 'Login length is incorrect'},
            status_code=status.HTTP_400_BAD_REQUEST)
    
    if len(newUser.password) < 5 or len(newUser.password) > 25:
        return Response(
            content={'error': 'Password length is incorrect'},
            status_code=status.HTTP_400_BAD_REQUEST)
    
    alreadyExit = True if len(db.query(User).filter(User.login == newUser.login).all()) > 0 else False
    if alreadyExit:
        return Response(
            content={'error': 'Login already exists'},
            status_code=status.HTTP_409_CONFLICT)
    
    createNewUser = User(
        login=newUser.login, 
        password=bcrypt_context.hash(newUser.password))
    db.add(createNewUser)
    db.commit()
    db.refresh(createNewUser)

    token = create_access_token(
        login=createNewUser.login, 
        user_id=createNewUser.id, 
        expires_delta=timedelta(minutes=30))
    
    return Response(content={'User created with: ': f'{createNewUser.id}',
                             'access_token: ': f'{token}',
                             'token_type': 'bearer'})

@router.post('/authorization')
async def authorization(
    db: db_dependency,
    authUser: UserRequest):

    hashedPassword = bcrypt_context.hash(authUser.password)
    userInDB = db.query(User).filter(
            User.login == authUser.login and
            User.password == hashedPassword).first()
    if userInDB:
        token = create_access_token(login=userInDB.login, user_id=userInDB.id, expires_delta=timedelta(minutes=20))
        return Response(content={
                            'message': 'Authorization successful',
                            'access_token: ': f'{token}',
                            'token_type': 'bearer'},
                        status_code=status.HTTP_200_OK)
    else:
        return Response(content={
                            'error': 'Unauthorized',
                            'message': 'Authorization failed. Please check your credentials'},
                        status_code=status.HTTP_401_UNAUTHORIZED)
    
def create_access_token(login: str, user_id: int, expires_delta: timedelta):
    encode = {
        'user_login':login, 
        'user_id':user_id}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp':expires})
    return jwt.encode(
        encode, 
        os.getenv('SECRET_KEY'), 
        algorithm=os.getenv('ALGORITHM'))