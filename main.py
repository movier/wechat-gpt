import asyncio
from asyncio.exceptions import TimeoutError

from typing import Union
from functools import lru_cache

from fastapi import FastAPI, Body, Response

from wechatpy import parse_message
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.replies import create_reply

from langchain.chat_models import ChatOpenAI

from pydantic_settings import BaseSettings, SettingsConfigDict

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
                body: str = Body(...)):
    try:
        check_signature(wechat_token, signature, timestamp, nonce)
        msg = parse_message(body)
        print("User:", msg.content)
        reply_content = ''
        try:
            ai = await asyncio.wait_for(asyncio.shield(ainvoke_and_print(msg.content)), timeout=4.9)
            reply_content = ai.content
        except TimeoutError:
            reply_content = "请求超时"
        reply = create_reply(reply_content, message=msg)
        xml = reply.render()
        return Response(xml)
    except InvalidSignatureException:
        # 处理异常情况或忽略
        return {"detail": "Not Found"}

async def ainvoke_and_print(msg):
    reply = await llm.ainvoke(msg)
    print('AI:', reply.content)
    return reply
