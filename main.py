from fastapi import FastAPI, Depends

from typing import Annotated
from sqlalchemy.orm import Session

from database.models import Base

from database.database import SessionLocal, engine
from routes import user, note
from dotenv import load_dotenv

load_dotenv()

db = SessionLocal()

# Создание приложения и добавление рутов
app = FastAPI()
app.include_router(user.router)
app.include_router(note.router)

# Создание бд и сущностей
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Создание инъекции бд
db_dependency = Annotated[Session, Depends(get_db)]
