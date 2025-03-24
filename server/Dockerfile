# Dockerfile

FROM python:3.9-alpine

ENV PYTONDONOTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "gunicorn server.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${GATEWAY_PORT}"]

