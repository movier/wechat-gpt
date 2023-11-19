from sqlalchemy import Boolean, Column, Integer, String, DateTime

from database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, unique=True)
    req_times=Column(Integer, default=1)
    is_fulfilled = Column(Boolean, default=False)
    content=Column(String)
    reply=Column(String)
    source = Column(String, index=True)
    target = Column(String, index=True)
    create_time = Column(DateTime)    
