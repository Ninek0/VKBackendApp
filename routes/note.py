from datetime import date, datetime, timedelta
import json
import os
from typing import Annotated
from fastapi import APIRouter, Query, Request, Depends, Response
from jose import jwt, ExpiredSignatureError
from pydantic import BaseModel
from starlette import status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database.database import SessionLocal
from database.models import Note, User

from dotenv import load_dotenv

load_dotenv()

# Рут заметок
router = APIRouter(
    prefix='/note',
    tags=['note']
)

# Класс который описывает данные запроса связанных с заметками
class NoteRequest(BaseModel):
    title: str
    content: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Инъекция бд
db_dependency = Annotated[Session, Depends(get_db)]

# Создание заметки
@router.post('/create')
def CreateNote(
    db: db_dependency,
    request: Request, 
    noteRequest: NoteRequest):

    # берем токен из хэдера
    token = request.headers.get('access_token')
    
    # Если токен есть то делаем дела
    if token:
        userInfo: dict
        # пробуем его декодировать
        try:
            userInfo = jwt.decode(token,  os.getenv('SECRET_KEY'))
        except ExpiredSignatureError:
            # в случае если он просрочен то уведоляем пользователя об этом
            return Response(
                content=json.dumps({
                    'message':'Access token has expired, please log in again'
                }),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        # проверяем ограничения названия и контента
        if 0 < len(noteRequest.title) < 25 and 0 < len(noteRequest.content) < 50:
            # проверяем есть ли заметки от пользователя с такими же названием
            if db.query(Note).filter(
                and_(Note.title == noteRequest.title,
                Note.author_id == userInfo['user_id'])).first():
                return Response(
                content=json.dumps({
                    'message':'Note with this title already exists',
                }),
                status_code=status.HTTP_409_CONFLICT
            )
            # дубликатов нет
            # создаем новую заметку
            createdNote = Note(
                title=noteRequest.title,
                content=noteRequest.content,
                author_id=userInfo['user_id']
            )
            # добавлем ее в бд и обновляем переменную
            db.add(createdNote)
            db.commit()
            db.refresh(createdNote)
            # уведомляем о том, что заметка создана
            return Response(
                content=json.dumps({
                    'message':'Note created',
                    'note title': createdNote.title,
                    'note content': createdNote.content,
                    'created at': str(createdNote.created_at),
                    'author id': createdNote.author_id
                }),
                status_code=status.HTTP_201_CREATED
            )
        # Ограничения на название и контент не выполнены
        else:
            return Response(
                        content=json.dumps({
                            'message':'Incorrect note title or content',
                        }),
                status_code=status.HTTP_400_BAD_REQUEST
            )
    # а токена то нет, значит не можено создать заметку 
    else:
        return Response(
                content=json.dumps({
                    'message':'Unauthorized user request'
                }),
                status_code=status.HTTP_401_UNAUTHORIZED
            )

# Изменение заметки
@router.post('/change')
def UpdateNote(
    db: db_dependency,
    request: Request, 
    noteRequest: NoteRequest):

    token = request.headers.get('access_token')
    
    if token:
        userInfo: dict
        try:
            userInfo = jwt.decode(token, os.getenv('SECRET_KEY'))
        except ExpiredSignatureError:
            return Response(
                content=json.dumps({
                    'message':'Access token has expired, please log in again'
                }),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        if 0 < len(noteRequest.title) < 25 and 0 < len(noteRequest.content) < 50:
            noteChange = db.query(Note).filter(
                and_(Note.title == noteRequest.title,        
                Note.author_id == userInfo['user_id'])
            ).first()
            # мы попытались найти заметку с указанным нзванием за авторством пользователя
            if noteChange:
                # проверям по времени
                if datetime.now() - noteChange.created_at >= timedelta(hours=24):
                    return Response(
                        content=json.dumps({
                            'message':'Time for note editing has expired',
                        }),
                        status_code=status.HTTP_403_FORBIDDEN
                    )
                # изменяем заметку
                else:
                    noteChange.content = noteRequest.content
                    noteChange.title = noteRequest.title
                    db.commit()
                    db.refresh(noteChange)
                    return Response(
                        content=json.dumps({
                            'message':'Note created',
                            'note title': noteChange.title,
                            'note content': noteChange.content,
                            'created at': str(noteChange.created_at),
                            'author id': noteChange.author_id
                        }),
                status_code=status.HTTP_202_ACCEPTED
            )
            else:
                return Response(
                    content=json.dumps({
                        'message':'Note not found',
                    }),
                    status_code=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                        content=json.dumps({
                            'message':'Incorrect note title or content',
                        }),
                status_code=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
                content=json.dumps({
                    'message':'Unauthorized user request'
                }),
                status_code=status.HTTP_401_UNAUTHORIZED
            )

# Поиск заметок
@router.get('/search')
def search_notes(
    db: db_dependency,
    request: Request,
    user_login: int = Query(None), 
    start_date: date = Query(None), 
    end_date: date = Query(None), 
    limit: int = Query(10, ge=1), 
    offset: int = Query(0)):

    token = request.headers.get('access_token')
    
    isUserAuth = False
    userInfo = {}
    if token:
        try:
            userInfo = jwt.decode(token, os.getenv('SECRET_KEY'))
        except ExpiredSignatureError:
           isUserAuth = False
        finally:
            if userInfo:
                isUserAuth = True
    else:
        isUserAuth = False

    query = db.query(Note)
    # каскадно фильруем все заметки
    if user_login:
        searche_user_id = db.query(User).filter(User.login == user_login).first()
        if searche_user_id:
            query = query.filter(Note.id == searche_user_id)
    if start_date and end_date:
        query = query.filter(start_date <= Note.created_at <= end_date)
    # получаем необходимое количество с применением лимита и сдвига для постраничного отображения
    notes = query.limit(limit=limit).offset(offset=offset).all()

    # переведем заметки в удобный формат для отображения в дальнейшем
    response_notes = []

    for note in notes:
        # тут магия, если пользователь авторизован и его id совпадает с id автора то изменяем автора в отображении на то, что можно заметить
        author_login = db.query(User).filter(User.id == note.author_id).first().login
        if isUserAuth:
            if author_login == userInfo['user_login']:
                author_login = 'Ohh thats me'

        response_notes.append({
            'title': note.title,
            'content': note.content,
            'author': author_login
        })

    return Response(
                content=json.dumps(response_notes),
                status_code=status.HTTP_200_OK
            )

# удаление заметки
@router.delete('/remove')
def remove_note(
    db: db_dependency,
    request: Request,
    note_id: int = Query(None),):

    token = request.headers.get('access_token')

    if token:
        userInfo: dict
        try:
            userInfo = jwt.decode(token, os.getenv('SECRET_KEY'))
        except ExpiredSignatureError:
            return Response(
                content=json.dumps({
                    'message':'Access token has expired, please log in again'
                }),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        if note_id:
            # ищем заметку с данным id и проверям 
            noteDelete = db.query(Note).filter(
                and_(Note.id == note_id,      
                Note.author_id == userInfo['user_id'])
            ).first()
            # если нашли то удаляем ее, если нет, то уведомляем о том, что заметка не найдена
            if noteDelete:
                db.delete(noteDelete)
                db.commit()
                return Response(
                    content=json.dumps({
                        'message':f'Note with id {note_id} have been deleted',
                    }),
                    status_code=status.HTTP_202_ACCEPTED
                )
            else:
                return Response(
                    content=json.dumps({
                        'message':f'Note with id {note_id} not found',
                    }),
                    status_code=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                    content=json.dumps({
                        'message':'note id undefined',
                    }),
                    status_code=status.HTTP_404_NOT_FOUND
                )
    else:
        return Response(
                content=json.dumps({
                    'message':'Unauthorized user request'
                }),
                status_code=status.HTTP_401_UNAUTHORIZED
            )