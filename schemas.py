from typing import Union
from datetime import datetime

from pydantic import BaseModel


class MessageBase(BaseModel):
    id: int = None
    is_fulfilled: bool = False
    content: str
    reply: Union[str, None] = None
    msg_id: int
    source: str
    target: str
    create_time: int
    time_elapsed: int = None

class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    class Config:
        orm_mode = True
