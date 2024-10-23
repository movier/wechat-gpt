#!/bin/bash

docker run -it --rm \
  --name wechatgpt-dev \
  -p 8000:8000 \
  -v $(pwd):/app \
  movier/wechat-gpt \
  uvicorn 'main:app' --host=0.0.0.0 --port=8000 --reload
