import asyncio, sys, logging

from typing import Union
from functools import lru_cache

from fastapi import FastAPI, Body, Response, Depends

from wechatpy import parse_message, WeChatClient
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from pydantic_settings import BaseSettings, SettingsConfigDict

from sqlalchemy.orm import Session

from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

import crud
import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

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
    wechat_app_id: str
    wechat_app_secret: str

    tencent_cloud_secret_id: str
    tencent_cloud_secret_key: str
    tencent_cloud_bucket_region: str
    tencent_cloud_bucket_name: str

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()

app = FastAPI()
llm = ChatOpenAI(openai_api_key=settings.openai_api_key)

wechat_token = settings.wechat_token
wechat_app_id = settings.wechat_app_id
wechat_app_secret = settings.wechat_app_secret
wechat_client = WeChatClient(wechat_app_id, wechat_app_secret)

tencent_cloud_secret_id = settings.tencent_cloud_secret_id
tencent_cloud_secret_key = settings.tencent_cloud_secret_key
tencent_cloud_bucket_region = settings.tencent_cloud_bucket_region
tencent_cloud_bucket_name = settings.tencent_cloud_bucket_name
tencent_cloud_config = CosConfig(Region=tencent_cloud_bucket_region, SecretId=tencent_cloud_secret_id, SecretKey=tencent_cloud_secret_key)
tencent_cloud_client = CosS3Client(tencent_cloud_config)

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
        msg_model = crud.create_message(db, msg)
        asyncio.create_task(ainvoke_and_update(db, msg_model))
        return Response("success")
    except InvalidSignatureException:
        # 处理异常情况或忽略
        return {"detail": "Not Found"}

async def ainvoke_and_update(db, msg_model):
    all_messages = crud.get_all_messages(db)
    from_messages = [("system", "You are a helpful assistant.")]
    for message in all_messages:
        if message.content:
            from_messages.append(("human", message.content))
        if message.reply:
            from_messages.append(("ai", message.reply))
    chat_template = ChatPromptTemplate.from_messages(from_messages)
    messages = chat_template.format_messages()
    print("Messages:", messages)
    ai_message = await llm.ainvoke(messages)
    print("AI:", ai_message)
    msg_model.reply = ai_message.content
    crud.update_message(db, msg_model)

    if (tencent_cloud_text_auditing_service(ai_message.content)):
        res = wechat_client.message.send_text(msg_model.source, ai_message.content)
        print("res", res)
        msg_model.is_fulfilled = True
        crud.update_message(db, msg_model)
    else:
        res = wechat_client.message.send_text(msg_model.source, "这个话题我暂时无法与您讨论，请联系系统管理员。")
        print("res", res)

def tencent_cloud_text_auditing_service(text):
    response = tencent_cloud_client.ci_auditing_text_submit(
        Bucket=tencent_cloud_bucket_name,
        Content=text.encode("utf-8"),
    )
    result = response["JobsDetail"]["Result"]
    print("tencent_cloud_text_auditing_service", result)
    if result == "0":
        return True
    return False
