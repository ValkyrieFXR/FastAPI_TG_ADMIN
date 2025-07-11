from sqlalchemy import Column, Integer, String, Text, JSON, DateTime  # Импортируем DateTime
from sqlalchemy.ext.declarative import declarative_base

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
    timer_time = Column(DateTime)  # Теперь тип DateTime импортирован
    created_at = Column(DateTime)
