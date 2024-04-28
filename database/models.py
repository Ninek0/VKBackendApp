from sqlalchemy import  Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Базовая модель
class Base(DeclarativeBase): pass

# Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, index = True)
    login = Column(String)
    password = Column(String)
    notes = relationship("Note", back_populates="author")

# Модель заметки
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key = True, index = True)
    title = Column(String)
    content = Column(String)
    created_at = Column(DateTime, default=func.now())
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="notes")