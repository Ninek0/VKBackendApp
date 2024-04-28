import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    os.getenv('SQLALCHEMY_DATABASE_URL'), 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autoflush=False, 
    bind=engine)

