from datetime import datetime, timedelta
import os
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Response
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel
from starlette import status
from sqlalchemy.orm import Session
from database.database import SessionLocal
from database.models import Note

router = APIRouter(
    prefix='/note',
    tags=['note']
)

class CreateNoteRequest(BaseModel):
    title: str
    content: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.post('/create')
def CreateNote(
    db: db_dependency,
    request: Request, 
    noteRequest: CreateNoteRequest):

    token = request.headers.get('access_token')
    
    if token:
        userInfo: dict
        try:
            userInfo = jwt.decode(token, os.environ.get('SECRET_KEY'))
        except ExpiredSignatureError:
            return Response(
                content={
                    'message':'Access token has expired, please log in again'
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        if 0 < len(noteRequest.title) < 25 and 0 < len(noteRequest.content) < 50:
            
            if db.query(Note).filter(
                Note.title == noteRequest.title and
                Note.author_id == userInfo['id']).first():
                return Response(
                content={
                    'message':'Note with this title already exists',
                },
                status_code=status.HTTP_409_CONFLICT
            )
            
            createdNote = Note(
                title=noteRequest.title,
                content=noteRequest.content,
                author_id=userInfo['id']
            )
            
            db.add(createdNote)
            db.commit()
            db.refresh(createdNote)
            
            return Response(
                content={
                    'message':'Note created',
                    'note title': createdNote.title,
                    'note content': createdNote.content,
                    'created at': createdNote.created_at,
                    'author id': createdNote.author_id
                },
                status_code=status.HTTP_201_CREATED
            )
    else:
        return Response(
                content={
                    'message':'Unauthorized user request'
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
    
@router.post('/change')
def UpdateNote(
    db: db_dependency,
    request: Request, 
    noteRequest: CreateNoteRequest):

    token = request.headers.get('access_token')
    
    if token:
        userInfo: dict
        try:
            userInfo = jwt.decode(token, os.environ.get('SECRET_KEY'))
        except ExpiredSignatureError:
            return Response(
                content={
                    'message':'Access token has expired, please log in again'
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        if 0 < len(noteRequest.title) < 25 and 0 < len(noteRequest.content) < 50:
            
            noteChange = db.query(Note).filter(
                (Note.title == noteRequest.title or
                Note.content == noteRequest.content) and
                Note.author_id == userInfo['id']
            ).first()
            if noteChange:
                if datetime.now() - noteChange.created_at >= timedelta(hours=24):
                    return Response(
                        content={
                            'message':'Time for note editing has expired',
                        },
                        status_code=status.HTTP_403_FORBIDDEN
                    )
                else:
                    noteChange.content = noteRequest.content
                    noteChange.title = noteRequest.title
                    db.commit()
                    db.refresh(noteChange)
                    return Response(
                        content={
                            'message':'Note created',
                            'note title': noteChange.title,
                            'note content': noteChange.content,
                            'created at': noteChange.created_at,
                            'author id': noteChange.author_id
                        },
                status_code=status.HTTP_202_ACCEPTED
            )
            else:
                return Response(
                    content={
                        'message':'Note not found',
                    },
                    status_code=status.HTTP_404_NOT_FOUND
                )
    else:
        return Response(
                content={
                    'message':'Unauthorized user request'
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
    
