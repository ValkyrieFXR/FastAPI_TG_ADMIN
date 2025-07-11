# database.py
import os
from sqlalchemy import MetaData, Table, Column, Integer, String, Text, JSON, Boolean, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class Menu(Base):
    __tablename__ = "menus"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    text = Column(Text)
    buttons = Column(JSON)
    photo = Column(String, nullable=True)
    button_groups = Column(JSON)
    timers = Column(JSON, default={})

class TimerLog(Base):
    __tablename__ = "timers_log"
    id = Column(String, primary_key=True)
    menu_key = Column(String)
    button_text = Column(String)
    timer_time = Column(DateTime)
    created_at = Column(DateTime)
