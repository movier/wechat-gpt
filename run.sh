#!/bin/bash

docker run -it --rm \
  --name wechat-gpt \
  -p 8000:8000 \
  -v $(pwd):/app \
  movier/wechat-gpt \
  uvicorn 'main:app' --host=0.0.0.0 --port=8000 --reload
