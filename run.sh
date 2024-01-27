#!/bin/bash

docker run -it --rm \
  -p 8000:8000 \
  -v $(pwd):/app \
  movier/wechat-ai \
  uvicorn 'main:app' --reload --host=0.0.0.0 --port=8000
