import asyncio
from asyncio.exceptions import TimeoutError

from typing import Union
from functools import lru_cache

from fastapi import FastAPI, Body, Response, Depends

from wechatpy import parse_message
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.replies import create_reply

from langchain.chat_models import ChatOpenAI

from pydantic_settings import BaseSettings, SettingsConfigDict

from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Settings(BaseSettings):
    openai_api_key: str
    wechat_token: str
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()

app = FastAPI()
llm = ChatOpenAI(openai_api_key=settings.openai_api_key)
wechat_token = settings.wechat_token

@app.get("/wechat/")
def read_wechat(signature: Union[str, None] = None,
                timestamp: Union[str, None] = None,
                nonce: Union[str, None] = None,
                echostr: Union[str, None] = None):
    try:
        check_signature(wechat_token, signature, timestamp, nonce)
        return Response(echostr)
    except InvalidSignatureException:
        # 处理异常情况或忽略
        return {"detail": "Not Found"}
    
@app.post("/wechat/")
async def post_wechat(signature: Union[str, None] = None,
                timestamp: Union[str, None] = None,
                nonce: Union[str, None] = None,
                body: str = Body(...),
                db: Session = Depends(get_db)):
    try:
        check_signature(wechat_token, signature, timestamp, nonce)
        wechat_msg = parse_message(body)
        msg = schemas.MessageCreate(
            id=wechat_msg.id,
            source=wechat_msg.source,
            target=wechat_msg.target,
            create_time=wechat_msg.create_time,
            content=wechat_msg.content
        )
        unhandled_msg = crud.get_unhandled_message(db, msg)
        reply_content = ''
        if unhandled_msg:
            if unhandled_msg.reply:
                reply_content = unhandled_msg.reply
                unhandled_msg.is_fulfilled = True
                crud.update_message(db, unhandled_msg)
            else:
                reply_content = "请稍后再试"
        else:
            msg = crud.get_or_create_message(db, msg)
            try:
                ai = await asyncio.wait_for(asyncio.shield(ainvoke_and_print(db, msg)), timeout=4.8)
                reply_content = ai.reply
                msg.is_fulfilled = True
                crud.update_message(db, msg)
            except TimeoutError:
                reply_content = "请求超时"
        reply = create_reply(reply_content, message=wechat_msg)
        xml = reply.render()
        return Response(xml)
    except InvalidSignatureException:
        # 处理异常情况或忽略
        return {"detail": "Not Found"}

async def ainvoke_and_print(db, msg):
    print("Human:", msg.content)
    reply = await llm.ainvoke(msg.content)
    print("AI:", reply.content)
    msg.reply = reply.content
    crud.update_message(db, msg)
    return msg
