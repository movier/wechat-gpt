ARG PYTHON_VERSION=3.8.18
FROM python:${PYTHON_VERSION}-slim as base
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD uvicorn 'main:app' --host=0.0.0.0 --port=8000