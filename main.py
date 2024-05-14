import asyncio, sys, logging, requests

from typing import Union
from functools import lru_cache

from fastapi import FastAPI, Body, Response, Depends

from wechatpy import parse_message, WeChatClient
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException, WeChatClientException

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

# set_debug(True)

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

    enable_tencent_cloud_tas: bool
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

wechat_token = settings.wechat_token
wechat_app_id = settings.wechat_app_id
wechat_app_secret = settings.wechat_app_secret
wechat_client = WeChatClient(wechat_app_id, wechat_app_secret)

enable_tencent_cloud_tas = settings.enable_tencent_cloud_tas
if enable_tencent_cloud_tas:
    tencent_cloud_secret_id = settings.tencent_cloud_secret_id
    tencent_cloud_secret_key = settings.tencent_cloud_secret_key
    tencent_cloud_bucket_region = settings.tencent_cloud_bucket_region
    tencent_cloud_bucket_name = settings.tencent_cloud_bucket_name
    tencent_cloud_config = CosConfig(Region=tencent_cloud_bucket_region, SecretId=tencent_cloud_secret_id, SecretKey=tencent_cloud_secret_key)
    tencent_cloud_client = CosS3Client(tencent_cloud_config)

@app.get("/")
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
    
@app.post("/")
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
            msg_id=wechat_msg.id,
            source=wechat_msg.source,
            target=wechat_msg.target,
            create_time=int(wechat_msg.create_time.timestamp()),
            content=wechat_msg.content
        )
        msg_model = crud.create_message(db, msg)
        asyncio.create_task(ainvoke_and_update(db, msg_model))
        return Response("success")
    except InvalidSignatureException:
        # 处理异常情况或忽略
        return {"detail": "Not Found"}

async def ainvoke_and_update(db, msg_model):
    all_messages = crud.get_all_messages(db, msg_model)
    from_messages = []
    for message in all_messages:
        if message.content:
            from_messages.append({"role": "user", "content": message.content.replace('{', '{{').replace('}', '}}')})
        if message.reply:
            from_messages.append({"role": "assistant", "content": message.reply.replace('{', '{{').replace('}', '}}')})
    messages = from_messages
    print(messages)
    ai_message = await asyncio.to_thread(request_openai, messages)
    print(ai_message)
    ai_message_content = ai_message['choices'][0]['message']['content']
    msg_model.reply = ai_message_content
    crud.update_message(db, msg_model)

    if enable_tencent_cloud_tas and not tencent_cloud_text_auditing_service(ai_message_content):
        wechat_client.message.send_text(msg_model.source, "很抱歉，我暂时无法与您讨论这个话题。如有需要，请联系系统管理员。")
    else:
        try:
            wechat_client.message.send_text(msg_model.source, ai_message_content)
            msg_model.is_fulfilled = True
            crud.update_message(db, msg_model)
        except WeChatClientException as e:
            print(e)
            wechat_client.message.send_text(msg_model.source, "很抱歉，我在回复消息的时候遇到了点儿问题。如有需要，请联系系统管理员。")

def request_openai(messages):
    headers = {
        'Authorization': f'Bearer {settings.openai_api_key}',
        'Content-Type': 'application/json',
    }
    data = {
        'model': 'gpt-4o',
        'messages': messages,
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    return response.json()

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
