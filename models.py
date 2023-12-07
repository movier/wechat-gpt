from sqlalchemy import Boolean, Column, Integer, String, DateTime

from database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_fulfilled = Column(Boolean, default=False)
    content=Column(String)
    reply=Column(String)
    msg_id=Column(Integer)
    source = Column(String, index=True)
    target = Column(String, index=True)
    create_time = Column(Integer, index=True)
    time_elapsed=Column(Integer)
