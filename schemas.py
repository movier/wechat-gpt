from typing import Union
from datetime import datetime

from pydantic import BaseModel


class MessageBase(BaseModel):
    id: int
    source: str
    target: str
    content: str
    create_time: datetime
    reply: Union[str, None] = None
    req_times: int = 1
    is_fulfilled: bool = False


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    class Config:
        orm_mode = True
