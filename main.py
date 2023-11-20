import asyncio
from asyncio.exceptions import TimeoutError

from typing import Union
from functools import lru_cache

from fastapi import FastAPI, Body, Response, Depends, BackgroundTasks

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
        print("Human:", wechat_msg.content)
        msg = schemas.MessageCreate(
            id=wechat_msg.id,
            source=wechat_msg.source,
            target=wechat_msg.target,
            create_time=wechat_msg.create_time,
            content=wechat_msg.content
        )
        unhandled_msg = crud.get_unhandled_message(db, msg)
        reply_content = ''
        
        if not unhandled_msg:
            msg_model = crud.create_message(db, msg)
            asyncio.create_task(ainvoke_and_update(db, msg_model))
        
        await asyncio.sleep(4.8)
        reply_content = check_unhandled_message(db, msg)
        if reply_content == None:
            reply_content = "服务器繁忙，请稍后再试"

        reply = create_reply(reply_content, message=wechat_msg)
        xml = reply.render()
        return Response(xml)
    except InvalidSignatureException:
        # 处理异常情况或忽略
        return {"detail": "Not Found"}

async def ainvoke_and_update(db, msg_model):
    ai_message = await llm.ainvoke(msg_model.content)
    print("AI:", ai_message.content)
    msg_model.reply = ai_message.content
    crud.update_message(db, msg_model)

def check_unhandled_message(db, msg):
    unhandled_msg = crud.get_unhandled_message(db, msg)
    if unhandled_msg.reply:
        unhandled_msg.is_fulfilled = True
        crud.update_message(db, unhandled_msg)
        return unhandled_msg.reply
    else:
        return None        
