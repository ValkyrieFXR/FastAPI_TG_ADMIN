from sqlalchemy import Column, Integer, String, Text, JSON
from database import Base

class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = {"extend_existing": True}  # 👈 Добавь это

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    text = Column(Text)
    photo = Column(String, nullable=True)
    buttons = Column(JSON)
    button_groups = Column(JSON)
    timers = Column(JSON, nullable=True)

