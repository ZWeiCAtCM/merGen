# Dockerfile for ida-llama-agent Django project
FROM python:3.10-slim

# 不生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
# 不缓冲输出
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 复制项目代码
COPY . /app/

# 使用 gunicorn + uvicorn 运行 ASGI 服务（确保 settings.py 中 ALLOWED_HOSTS 配置正确）
CMD ["sh", "-c", "gunicorn ida_llama_agent.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${IDA_AGENT_PORT}"]

