from datetime import timedelta, datetime
import json
import os
from fastapi import APIRouter
from jose import jwt
from pydantic import BaseModel
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from database.database import SessionLocal
from fastapi import Response, Depends
from jose import jwt
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session
from starlette import status
from database.models import User
from sqlalchemy import and_
from dotenv import load_dotenv

load_dotenv()

bcrypt_context = CryptContext(
    schemes=['bcrypt'], 
    deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

# рут пользвоателя
router = APIRouter(
    prefix='/user',
    tags=['user']
)

# тип данных для запроса
class UserRequest(BaseModel):
    login: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# внедряем бд
db_dependency = Annotated[Session, Depends(get_db)]

# регистрация пользователя 
@router.post('/registration', status_code=status.HTTP_201_CREATED)
async def registration(
    db: db_dependency,
    newUser: UserRequest):
    # проверяем логин пользователя и его пароль
    if len(newUser.login) < 5 or len(newUser.login) > 50:
        return Response(
            content=json.dumps({'error': 'Login length is incorrect'}),
            status_code=status.HTTP_400_BAD_REQUEST)
    
    if len(newUser.password) < 5 or len(newUser.password) > 25:
        return Response(
            content=json.dumps({'error': 'Password length is incorrect'}),
            status_code=status.HTTP_400_BAD_REQUEST)
    
    # проверяем существует ли пользователь с таким же логином
    alreadyExit = True if len(db.query(User).filter(User.login == newUser.login).all()) > 0 else False
    if alreadyExit:
        return Response(
            content=json.dumps({'error': 'Login already exists'}),
            status_code=status.HTTP_409_CONFLICT)
    
    # создаем нового пользователя
    createNewUser = User(
        login=newUser.login, 
        # пароль (хэшируется)
        password=bcrypt_context.hash(newUser.password))
    # добавляем его в дл
    db.add(createNewUser)
    db.commit()
    db.refresh(createNewUser)

    # создаем для нового пользователя токен
    token = create_access_token(
        login=createNewUser.login, 
        user_id=createNewUser.id, 
        expires_delta=timedelta(minutes=30))
    
    return Response(
        content=json.dumps(
            {
                'User created with: ': f'{createNewUser.id}',
                'access_token: ': f'{token}',
                'token_type': 'bearer'
                }
            )
        )

# авторизация пользователя
@router.post('/authorization')
async def authorization(
    db: db_dependency,
    authUser: UserRequest):

    # получаем данные пользователя для авторизации
    # хэшируем введенный пароль пользователем
    hashedPassword = bcrypt_context.hash(authUser.password)
    # находим его в бд
    userInDB = db.query(User).filter(
            and_(User.login == authUser.login,
            User.password == hashedPassword)).first()
    # если нашелся
    if userInDB:
        # создаем токен
        token = create_access_token(login=userInDB.login, user_id=userInDB.id, expires_delta=timedelta(minutes=30))
        return Response(content=json.dumps({
                            'message': 'Authorization successful',
                            'access_token: ': f'{token}',
                            'token_type': 'bearer'}),
                        status_code=status.HTTP_200_OK)
    # не нашелся (((
    else:
        return Response(content=json.dumps({
                            'error': 'Unauthorized',
                            'message': 'Authorization failed. Please check your credentials'}),
                        status_code=status.HTTP_401_UNAUTHORIZED)

# функция которая генерирует токен
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